# =============================================================================
# services/leaf_detection_service.py
#
# Bu servis, Weli'nin eğittiği YOLOv8 modelini kullanarak bir görseldeki
# yaprakları tespit eder (nesne tespiti / bounding box).
#
# Sorumluluklar:
#   - Ham görsel baytını alıp PIL Image'a çevirmek
#   - önceden belleğe yüklenmiş YOLO modelini kullanarak inference çalıştırmak
#   - Bounding box koordinatlarını döndürmek
#   - Tespit edilen yaprağı kırpıp (crop) base64 string olarak döndürmek
# =============================================================================

import io
import base64
import logging
from typing import Optional

import numpy as np
from PIL import Image

# Type hint amacıyla — gerçek YOLO nesnesi lifespan'de yüklenir
from ultralytics import YOLO  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def _image_to_base64(image: Image.Image, fmt: str = "JPEG") -> str:
    """
    PIL Image nesnesini base64 kodlu string'e dönüştürür.
    Frontend'e görsel göndermek için kullanılır.

    Args:
        image: Gönderilecek PIL Image.
        fmt:   Resim formatı (varsayılan: "JPEG").

    Returns:
        Base64 string (data URI olmadan, sadece ham base64).
    """
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _bytes_to_pil(image_bytes: bytes) -> Image.Image:
    """
    Ham bayt dizisini PIL Image'a çevirir ve RGB moduna dönüştürür.
    PNG → JPEG dönüşümü gibi mod uyumsuzluklarını önlemek için RGB'ye normalize edilir.

    Args:
        image_bytes: HTTP isteğiyle gelen ham görsel verisi.

    Returns:
        RGB modlu PIL Image nesnesi.
    """
    image = Image.open(io.BytesIO(image_bytes))
    return image.convert("RGB")


# ---------------------------------------------------------------------------
# Ana Servis Fonksiyonu
# ---------------------------------------------------------------------------

def detect_leaf(
    image_bytes: bytes,
    yolo_model: YOLO,
    confidence_threshold: float = 0.25,
) -> dict:
    """
    Verilen görselde YOLOv8 modeliyle yaprak tespiti yapar.

    İşlem Adımları:
        1. Ham baytı PIL Image'a çevir.
        2. YOLO inference çalıştır.
        3. En yüksek güven skorlu bounding box'ı seç.
        4. Yaprağı bounding box'a göre kırp.
        5. Sonuçları (koordinatlar + kırpılmış görsel) döndür.

    Args:
        image_bytes:          HTTP isteğinden gelen ham görsel baytları.
        yolo_model:           Lifespan sırasında belleğe yüklenmiş YOLO nesnesi.
        confidence_threshold: Bu değerin altındaki tespitleri görmezden gel.

    Returns:
        Şu anahtarları içeren sözlük:
            - leaf_detected (bool):     Yaprak bulundu mu?
            - bounding_box (dict|None): x1, y1, x2, y2 koordinatları.
            - confidence (float|None):  Model güven skoru (0.0 – 1.0).
            - cropped_leaf_base64 (str|None): Kırpılmış yaprak görseli (base64).
            - original_width (int):     Orijinal görsel genişliği.
            - original_height (int):    Orijinal görsel yüksekliği.

    Raises:
        ValueError: Görsel çözümlenemiyorsa veya YOLO çıktısı beklenmedikse.
        RuntimeError: YOLO model inference sırasında kritik hata oluşursa.
    """
    # --- Adım 1: Görseli hazırla ---
    try:
        pil_image = _bytes_to_pil(image_bytes)
        original_width, original_height = pil_image.size
        logger.info(f"Görsel yüklendi: {original_width}x{original_height} px")
    except Exception as exc:
        raise ValueError(f"Görsel baytları çözümlenemedi: {exc}") from exc

    # --- Adım 2: YOLO Inference ---
    try:
        # verbose=False → terminale aşırı çıktı bastır
        results = yolo_model(pil_image, conf=confidence_threshold, verbose=False)
    except Exception as exc:
        raise RuntimeError(f"YOLO inference hatası: {exc}") from exc

    # --- Adım 3: En iyi tespiti seç ---
    # YOLO birden fazla nesne tespit edebilir; en yüksek güvenli ilk kutuyu alırız.
    best_box: Optional[dict] = None
    best_conf: float = 0.0
    cropped_leaf_b64: Optional[str] = None

    for result in results:
        if result.boxes is None or len(result.boxes) == 0:
            continue  # Bu frame'de hiç tespit yok

        # Her bounding box'ı gez
        for box in result.boxes:
            conf = float(box.conf[0])  # Güven skoru
            if conf > best_conf:
                best_conf = conf
                # xyxy formatı: [x1, y1, x2, y2] piksel koordinatları
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                best_box = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    # --- Adım 4: Yaprağı kırp ---
    if best_box is not None:
        try:
            cropped = pil_image.crop((
                best_box["x1"],
                best_box["y1"],
                best_box["x2"],
                best_box["y2"],
            ))
            cropped_leaf_b64 = _image_to_base64(cropped)
            logger.info(
                f"Yaprak tespit edildi. Güven: {best_conf:.2f}, "
                f"Box: {best_box}"
            )
        except Exception as exc:
            logger.warning(f"Yaprak kırpma hatası: {exc}")
            # Kırpma başarısız olsa bile bounding box'ı döndürmeye devam et
            cropped_leaf_b64 = None
    else:
        logger.info("Görselde yaprak tespit edilemedi.")

    # --- Adım 5: Sonucu döndür ---
    return {
        "leaf_detected": best_box is not None,
        "bounding_box": best_box,
        "confidence": round(best_conf, 4) if best_box else None,
        "cropped_leaf_base64": cropped_leaf_b64,
        "original_width": original_width,
        "original_height": original_height,
    }
