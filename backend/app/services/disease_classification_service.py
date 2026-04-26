# =============================================================================
# services/disease_classification_service.py
#
# Bu servis iki ayrı görevi üstlenir:
#
#   1) EfficientNet-B3 Sınıflandırma:
#      Weli'nin eğittiği EfficientNet-B3 modeli ile kırpılmış yaprak görselinden
#      bitki hastalığını sınıflandırır ve güven skorunu döndürür.
#
#   2) Grad-CAM Açıklanabilir AI:
#      Modelin hangi bölgeye odaklandığını görselleştiren bir ısı haritası
#      (heatmap) üretir. Bu, tahminlerin neden yapıldığını anlamak için kullanılır.
#
# Bağımlılıklar:
#   - PyTorch (torch, torchvision)
#   - Pillow (PIL)
#   - OpenCV (cv2) — heatmap renklendirmesi için
#   - numpy
# =============================================================================

import io
import base64
import logging
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
import torchvision.transforms as transforms

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sabitler — Weli'nin eğitim sürecinde kullandığı normalize değerleri kullan
# ---------------------------------------------------------------------------

# ImageNet normalize değerleri (EfficientNet transfer learning için standart)
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD  = [0.229, 0.224, 0.225]

# EfficientNet-B3 girdi boyutu
_INPUT_SIZE = 300


# ---------------------------------------------------------------------------
# Görsel Ön İşleme
# ---------------------------------------------------------------------------

def _get_transform() -> transforms.Compose:
    """
    EfficientNet-B3 için standart ImageNet ön işleme pipeline'ı döndürür.

    Adımlar:
        1. 300x300'e yeniden boyutlandır (EfficientNet-B3 standart girdi)
        2. Tensor'a çevir (0-255 piksel → 0.0-1.0 float)
        3. ImageNet istatistikleriyle normalize et
    """
    return transforms.Compose([
        transforms.Resize((_INPUT_SIZE, _INPUT_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])


def _pil_from_bytes(image_bytes: bytes) -> Image.Image:
    """Ham bayt dizisini RGB PIL Image'a çevirir."""
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _pil_from_base64(b64_string: str) -> Image.Image:
    """
    Base64 kodlu görsel string'ini RGB PIL Image'a çevirir.
    Yaprak tespitinden gelen cropped_leaf_base64 değerini işlemek için kullanılır.
    """
    raw_bytes = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(raw_bytes)).convert("RGB")


def _image_to_base64(image: Image.Image, fmt: str = "JPEG") -> str:
    """PIL Image'ı base64 string'e kodlar (Grad-CAM çıktısı için)."""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Grad-CAM Yardımcı Sınıfı
# ---------------------------------------------------------------------------

class GradCAMHook:
    """
    Grad-CAM (Gradient-weighted Class Activation Mapping) hesaplamak için
    PyTorch hook mekanizmasını kullanan yardımcı sınıf.

    Kullanım:
        1. Hedef katmanı belirle (genellikle son conv katmanı).
        2. GradCAMHook(model, target_layer) oluştur.
        3. Forward pass çalıştır.
        4. generate_heatmap() ile ısı haritasını üret.
        5. Belleği temizlemek için remove() çağır.

    Attributes:
        gradients: Hedef katmana ait gradyanlar (backward pass sonrası).
        activations: Hedef katmanın özellik haritaları (forward pass sonrası).
    """

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None

        # Forward hook → aktivasyonları yakala
        self._fwd_hook = target_layer.register_forward_hook(self._save_activation)
        # Backward hook → gradyanları yakala
        self._bwd_hook = target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        """Forward pass sırasında özellik haritalarını kaydeder."""
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        """Backward pass sırasında gradyanları kaydeder."""
        self.gradients = grad_output[0].detach()

    def generate_heatmap(self, original_size: tuple[int, int]) -> np.ndarray:
        """
        Kaydedilen aktivasyon ve gradyanlardan Grad-CAM ısı haritası üretir.

        Algoritma:
            1. Global Average Pooling → her kanal için ağırlık hesapla.
            2. Ağırlıklı aktivasyon toplamı → ham Grad-CAM haritası.
            3. ReLU → negatif değerleri sıfırla (sadece pozitif etkiler).
            4. 0-255 aralığına normalize et.
            5. Orijinal görsel boyutuna yeniden ölçeklendir.

        Args:
            original_size: (genişlik, yükseklik) tuple — çıktı boyutu.

        Returns:
            uint8 numpy dizisi, şekil: (yükseklik, genişlik).

        Raises:
            RuntimeError: Hook'lar tetiklenmediyse (forward/backward çalışmadıysa).
        """
        if self.gradients is None or self.activations is None:
            raise RuntimeError(
                "Grad-CAM hook'ları tetiklenmedi. "
                "forward() ve backward() çağrıldığından emin ol."
            )

        # [B, C, H, W] → kanal boyutunda global ortalama al → [C]
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)  # [B, C, 1, 1]

        # Ağırlıklı aktivasyon toplamı: [B, C, H, W] → [H, W]
        cam = (weights * self.activations).sum(dim=1).squeeze(0)  # [H, W]

        # Negatif değerleri sıfırla (sınıf-dışı aktivasyonları bastır)
        cam = torch.relu(cam)

        # numpy'a çevir ve normalize et [0, 255]
        cam_np = cam.cpu().numpy()
        if cam_np.max() > 0:
            cam_np = (cam_np - cam_np.min()) / (cam_np.max() - cam_np.min())
        cam_np = (cam_np * 255).astype(np.uint8)

        # Orijinal görsel boyutuna yeniden ölçeklendir
        heatmap_pil = Image.fromarray(cam_np).resize(original_size, Image.BILINEAR)
        return np.array(heatmap_pil)

    def remove(self):
        """Hook'ları bellekten temizler. Her kullanımdan sonra çağrılmalı!"""
        self._fwd_hook.remove()
        self._bwd_hook.remove()


# ---------------------------------------------------------------------------
# Sınıflandırma Servisi
# ---------------------------------------------------------------------------

def classify_disease(
    cropped_leaf_base64: str,
    efficientnet_model: nn.Module,
    class_names: list[str],
    device: torch.device,
) -> dict:
    """
    EfficientNet-B3 modeli ile kırpılmış yaprak görselinden hastalık sınıflar.

    Args:
        cropped_leaf_base64: YOLOv8 servisinden gelen base64 kodlu kırpılmış yaprak.
        efficientnet_model:  Lifespan'de belleğe yüklenmiş EfficientNet modeli.
        class_names:         Modelin eğitildiği sınıf etiketleri listesi.
                             Örn: ["healthy", "leaf_blight", "powdery_mildew", ...]
        device:              Tensörlerin çalışacağı cihaz (CPU veya CUDA).

    Returns:
        Şu anahtarları içeren sözlük:
            - predicted_class (str):       Tahmin edilen hastalık sınıfı adı.
            - predicted_class_index (int): Sınıfın integer indeksi.
            - confidence (float):          En yüksek softmax skoru (0.0 – 1.0).
            - all_scores (dict):           Her sınıf için güven skoru.

    Raises:
        ValueError: Base64 dekodlama veya tensor dönüşümü başarısız olursa.
        RuntimeError: Model inference sırasında hata oluşursa.
    """
    # --- Adım 1: Base64 → PIL Image ---
    try:
        pil_image = _pil_from_base64(cropped_leaf_base64)
        original_size = pil_image.size  # (genişlik, yükseklik) — Grad-CAM için sakla
    except Exception as exc:
        raise ValueError(f"Base64 görsel çözümlenemedi: {exc}") from exc

    # --- Adım 2: Görsel ön işleme ---
    transform = _get_transform()
    try:
        tensor = transform(pil_image).unsqueeze(0).to(device)  # [1, 3, 300, 300]
    except Exception as exc:
        raise ValueError(f"Görsel tensor'a dönüştürülemedi: {exc}") from exc

    # --- Adım 3: EfficientNet Inference (gradient hesabı kapalı) ---
    efficientnet_model.eval()
    try:
        with torch.no_grad():
            logits = efficientnet_model(tensor)           # [1, num_classes]
            probabilities = torch.softmax(logits, dim=1)  # 0-1 aralığına sıkıştır
    except Exception as exc:
        raise RuntimeError(f"EfficientNet inference hatası: {exc}") from exc

    # --- Adım 4: En yüksek skoru seç ---
    probs_np = probabilities.squeeze(0).cpu().numpy()  # [num_classes]
    predicted_idx = int(np.argmax(probs_np))
    confidence = float(probs_np[predicted_idx])

    # Sınıf adlarını indeks ile eşleştir
    if predicted_idx >= len(class_names):
        logger.warning(
            f"Tahmin indeksi ({predicted_idx}) sınıf listesi sınırını aştı "
            f"({len(class_names)} sınıf var). 'unknown' döndürülüyor."
        )
        predicted_class = "unknown"
    else:
        predicted_class = class_names[predicted_idx]

    # Tüm sınıfların skorlarını sözlüğe dönüştür
    all_scores = {
        class_names[i]: round(float(probs_np[i]), 4)
        for i in range(len(class_names))
    }

    logger.info(
        f"Hastalık sınıflandırma tamamlandı. "
        f"Sınıf: '{predicted_class}', Güven: {confidence:.2%}"
    )

    return {
        "predicted_class": predicted_class,
        "predicted_class_index": predicted_idx,
        "confidence": round(confidence, 4),
        "all_scores": all_scores,
    }


# ---------------------------------------------------------------------------
# Grad-CAM Servisi
# ---------------------------------------------------------------------------

def generate_gradcam(
    cropped_leaf_base64: str,
    efficientnet_model: nn.Module,
    target_layer: nn.Module,
    class_names: list[str],
    device: torch.device,
    target_class_index: Optional[int] = None,
) -> dict:
    """
    Grad-CAM algoritmasıyla EfficientNet'in hangi bölgeye odaklandığını
    gösteren bir ısı haritası üretir.

    Args:
        cropped_leaf_base64: YOLOv8'den gelen kırpılmış yaprak (base64).
        efficientnet_model:  Lifespan'de yüklü EfficientNet modeli.
        target_layer:        Aktivasyonların yakalanacağı hedef katman
                             (genellikle son conv/features bloğu).
        class_names:         Sınıf isimleri listesi.
        device:              CPU veya CUDA.
        target_class_index:  Hangi sınıf için Grad-CAM üretileceği.
                             None ise modelin tahmin ettiği sınıf kullanılır.

    Returns:
        Şu anahtarları içeren sözlük:
            - heatmap_base64 (str):        Isı haritası görseli (base64, JPEG).
            - overlay_base64 (str):        Orijinal görsel üzerine bindirme (base64).
            - target_class (str):          Grad-CAM'in odaklandığı sınıf adı.
            - target_class_index (int):    Sınıfın integer indeksi.

    Raises:
        ValueError: Görsel işleme hatası.
        RuntimeError: Grad-CAM hesaplama hatası.
    """
    # --- Adım 1: Görseli hazırla ---
    try:
        pil_image = _pil_from_base64(cropped_leaf_base64)
        original_size = pil_image.size  # (genişlik, yükseklik)
    except Exception as exc:
        raise ValueError(f"Base64 görsel çözümlenemedi: {exc}") from exc

    transform = _get_transform()
    try:
        # gradient hesabı için requires_grad=True
        tensor = transform(pil_image).unsqueeze(0).to(device)
        tensor.requires_grad_(True)
    except Exception as exc:
        raise ValueError(f"Tensor dönüşümü başarısız: {exc}") from exc

    # --- Adım 2: Hook'ları kur ---
    hook = GradCAMHook(efficientnet_model, target_layer)

    # --- Adım 3: Forward pass (gradient hesabıyla) ---
    efficientnet_model.eval()
    try:
        logits = efficientnet_model(tensor)  # [1, num_classes]
    except Exception as exc:
        hook.remove()
        raise RuntimeError(f"Forward pass hatası: {exc}") from exc

    # --- Adım 4: Hedef sınıfı belirle ---
    if target_class_index is None:
        target_class_index = int(logits.argmax(dim=1).item())

    target_class_name = (
        class_names[target_class_index]
        if target_class_index < len(class_names)
        else "unknown"
    )

    # --- Adım 5: Backward pass (seçilen sınıf için) ---
    try:
        efficientnet_model.zero_grad()
        # Yalnızca hedef sınıfın skoru için geriye yayılım
        logits[0, target_class_index].backward()
    except Exception as exc:
        hook.remove()
        raise RuntimeError(f"Backward pass hatası: {exc}") from exc

    # --- Adım 6: Isı haritasını üret ---
    try:
        heatmap_np = hook.generate_heatmap(original_size)  # [H, W], uint8
    except Exception as exc:
        hook.remove()
        raise RuntimeError(f"Grad-CAM haritası üretilemedi: {exc}") from exc
    finally:
        hook.remove()  # Hook'ları temizle (bellek sızıntısını önle)

    # --- Adım 7: Isı haritasını renklendir (jet colormap) ---
    # Gri tonlamalı → renkli ısı haritası (kırmızı=yüksek aktivasyon, mavi=düşük)
    try:
        import cv2  # OpenCV — sadece bu adım için
        heatmap_colored = cv2.applyColorMap(heatmap_np, cv2.COLORMAP_JET)
        heatmap_colored_rgb = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
        heatmap_pil = Image.fromarray(heatmap_colored_rgb)
        heatmap_b64 = _image_to_base64(heatmap_pil)

        # Orijinal görsel üzerine ısı haritası y bindirme (alpha=0.4)
        original_np = np.array(pil_image.resize(original_size))
        overlay_np = cv2.addWeighted(original_np, 0.6, heatmap_colored_rgb, 0.4, 0)
        overlay_pil = Image.fromarray(overlay_np)
        overlay_b64 = _image_to_base64(overlay_pil)

    except ImportError:
        # OpenCV yoksa ham gri haritayı döndür
        logger.warning(
            "OpenCV bulunamadı. Renkli Grad-CAM yerine gri tonlamalı harita döndürülüyor. "
            "'pip install opencv-python' ile yükleyin."
        )
        heatmap_pil = Image.fromarray(heatmap_np).convert("RGB")
        heatmap_b64 = _image_to_base64(heatmap_pil)
        overlay_b64 = heatmap_b64  # fallback: sadece haritayı döndür

    logger.info(
        f"Grad-CAM oluşturuldu. "
        f"Hedef sınıf: '{target_class_name}' (indeks: {target_class_index})"
    )

    return {
        "heatmap_base64": heatmap_b64,
        "overlay_base64": overlay_b64,
        "target_class": target_class_name,
        "target_class_index": target_class_index,
    }
