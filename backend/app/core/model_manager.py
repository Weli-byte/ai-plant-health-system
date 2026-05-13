# =============================================================================
# core/model_manager.py
#
# Bu modül, tüm AI modellerini (YOLOv8, EfficientNet-B3, Grad-CAM hedef katmanı)
# tek bir yerde yönetir.
#
# Neden bu yaklaşım?
#   - AI modelleri çok ağırdır (100MB – 1GB+). Her HTTP isteğinde yeniden
#     yüklemek hem yavaştır hem de belleği tüketir.
#   - Bu modül, modelleri uygulama başlangıcında BİR KEZ belleğe yükler
#     ve tüm süre boyunca aynı nesneleri kullanır (Singleton pattern).
#   - FastAPI lifespan event'iyle entegre çalışır.
#
# Kullanım (main.py'deki lifespan içinde):
#   await model_store.load_all()
#
# Kullanım (endpoint içinde):
#   yolo   = model_store.yolo
#   effnet = model_store.efficientnet
#   layer  = model_store.gradcam_target_layer
# =============================================================================

import logging
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Dosya Yolları — settings.py içine taşınabilir, şimdilik burada
# ---------------------------------------------------------------------------

# Projenin kök dizinine göreceli yollar.
# Weli modellerini kaydettiğinde bu yolları güncelleyebilur.
# Örnek: models/yolov8_leaf.pt, models/efficientnet_disease.pt
_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"

DEFAULT_YOLO_PATH        = _MODELS_DIR / "yolov8_leaf.pt"
DEFAULT_EFFICIENTNET_PATH= _MODELS_DIR / "efficientnet_disease.pt"

# EfficientNet sınıf listesi — Weli'nin eğitim sırasında belirlediği sırayla yazılmalı.
# Bu liste modelin çalıştığı ortamda güncellenmelidir.
DEFAULT_CLASS_NAMES: list[str] = [
    "Healthy",
    "Powdery Mildew",
    "Leaf Blight",
    "Rust",
    "Leaf Spot",
    "Bacterial Wilt",
    "Mosaic Virus",
    "Anthracnose",
]


# ---------------------------------------------------------------------------
# ModelStore — Merkezi Model Deposu
# ---------------------------------------------------------------------------

class ModelStore:
    """
    Tüm AI modellerini bellekte tutan merkezi depo.

    Attributes:
        yolo:                 YOLOv8 tespit modeli (ultralytics.YOLO).
        efficientnet:         EfficientNet-B3 sınıflandırma modeli (nn.Module).
        gradcam_target_layer: Grad-CAM için hedef conv katmanı (nn.Module).
        class_names:          Hastalık sınıf isimleri listesi.
        device:               Hesaplama cihazı (torch.device).
        is_loaded:            Modeller başarıyla yüklendi mi?
    """

    def __init__(self):
        self.yolo: Optional[object] = None                   # ultralytics.YOLO
        self.efficientnet: Optional[nn.Module] = None
        self.gradcam_target_layer: Optional[nn.Module] = None
        self.class_names: list[str] = DEFAULT_CLASS_NAMES
        self.device: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.is_loaded: bool = False

        # ------------------------------------------------------------------
        # Sprint 3 Model Referansları
        # Bu attribute'lar Sprint 3 servisleri tarafından kendi singleton
        # store'ları üzerinden yönetilir. Burada merkezi izleme için tutulur.
        # ------------------------------------------------------------------
        self.xgboost_predictor: Optional[object] = None   # RiskPredictor singleton
        self.lstm_twin_store:   Optional[object] = None   # DigitalTwinModelStore
        self.multimodal_store:  Optional[object] = None   # MultimodalModelStore
        self.sprint3_loaded: bool = False

        # ------------------------------------------------------------------
        # Sprint 4 (Son Aşama) Model Referansları
        #
        # global_gnn_store   : GNN tabanlı küresel hastalık yayılım modeli.
        #                      Bölgesel risk haritası (Eren'in frontend'i) için.
        # continual_learning : Continual Learning servis singleton'ı.
        #                      /update_model endpoint'i tarafından kullanılır.
        #
        # Her iki bileşen de kendi servis modülündeki Singleton nesnelerinden
        # referans alınır; burada ikinci kez yükleme yapılmaz.
        # ------------------------------------------------------------------
        self.sprint4_gnn_store:        Optional[object] = None  # GlobalGNNModelStore
        self.sprint4_retraining_svc:   Optional[object] = None  # RetrainingService
        self.sprint4_loaded: bool = False

    # ------------------------------------------------------------------
    # YOLOv8 Yükleme
    # ------------------------------------------------------------------

    def _load_yolo(self, model_path: Path) -> None:
        """
        YOLOv8 modelini ultralytics kütüphanesi aracılığıyla yükler.

        Args:
            model_path: .pt uzantılı model ağırlık dosyasının yolu.

        Raises:
            FileNotFoundError: Dosya bulunamazsa.
            RuntimeError:       ultralytics yükleme hatası.
        """
        if not model_path.exists():
            logger.warning(f"YOLOv8 custom model {model_path} not found. Falling back to base yolov8n.pt")
            try:
                from ultralytics import YOLO  # type: ignore
                self.yolo = YOLO("yolov8n.pt") # Base detection model for fallback
                logger.info("✅ YOLOv8 base model loaded.")
                return
            except Exception as exc:
                raise RuntimeError(f"YOLOv8 fallback failed: {exc}") from exc

        try:
            from ultralytics import YOLO  # type: ignore
            logger.info(f"YOLOv8 yükleniyor: {model_path}")
            self.yolo = YOLO(str(model_path))
            logger.info("✅ YOLOv8 başarıyla yüklendi.")
        except Exception as exc:
            raise RuntimeError(f"YOLOv8 yüklenemedi: {exc}") from exc

    # ------------------------------------------------------------------
    # EfficientNet-B3 Yükleme
    # ------------------------------------------------------------------

    def _load_efficientnet(self, model_path: Path) -> None:
        """
        EfficientNet-B3 modelini PyTorch ile yükler.

        Weli'nin kaydetme yöntemi ne olursa olsun iki strateji dener:
            1. torch.load() ile tam modeli yükle (model serileştirme).
            2. State dict yükleme (torchvision tabanlı mimari + ağırlıklar).

        Son katmanı (gradcam_target_layer) otomatik olarak tespit eder.

        Args:
            model_path: .pt uzantılı EfficientNet ağırlık dosyasının yolu.

        Raises:
            FileNotFoundError: Dosya bulunamazsa.
            RuntimeError:       Model yükleme hatası.
        """
        if not model_path.exists():
            logger.warning(f"EfficientNet custom model {model_path} not found. Falling back to base EfficientNet.")
            from torchvision.models import efficientnet_b3, EfficientNet_B3_Weights
            self.efficientnet = efficientnet_b3(weights=EfficientNet_B3_Weights.DEFAULT)
            self.efficientnet.to(self.device)
            self.efficientnet.eval()
            self.gradcam_target_layer = self._find_gradcam_layer(self.efficientnet)
            return

        logger.info(f"EfficientNet-B3 yükleniyor: {model_path}")
        try:
            # Strateji 1: Weli modeli tam nesne olarak kaydettiyse
            checkpoint = torch.load(
                str(model_path),
                map_location=self.device,
                weights_only=False,  # tam model nesnesi için
            )

            if isinstance(checkpoint, nn.Module):
                # torch.save(model, path) ile kaydedilmiş
                self.efficientnet = checkpoint

            elif isinstance(checkpoint, dict):
                # torch.save(model.state_dict(), path) ile kaydedilmiş
                # torchvision EfficientNet-B3'ü inşa et ve ağırlıkları yükle
                self.efficientnet = self._build_efficientnet_from_state_dict(checkpoint)

            else:
                raise RuntimeError(
                    f"Bilinmeyen checkpoint formatı: {type(checkpoint)}. "
                    "Weli'ye EfficientNet'i nasıl kaydettiğini sorun."
                )

        except Exception as exc:
            raise RuntimeError(f"EfficientNet yüklenemedi: {exc}") from exc

        self.efficientnet.to(self.device)
        self.efficientnet.eval()

        # Grad-CAM hedef katmanını otomatik bul
        self.gradcam_target_layer = self._find_gradcam_layer(self.efficientnet)
        logger.info(
            f"✅ EfficientNet-B3 başarıyla yüklendi. "
            f"Grad-CAM hedef katmanı: {self.gradcam_target_layer.__class__.__name__}"
        )

    def _build_efficientnet_from_state_dict(self, state_dict: dict) -> nn.Module:
        """
        State dict (sadece ağırlıklar) formatından EfficientNet-B3 inşa eder.
        torchvision kütüphanesi gerektirir.

        Args:
            state_dict: Model ağırlıklarını içeren sözlük.

        Returns:
            Ağırlıkları yüklenmiş EfficientNet-B3 modeli.
        """
        try:
            from torchvision.models import efficientnet_b3  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "torchvision yüklü değil. 'pip install torchvision' ile yükleyin."
            ) from exc

        num_classes = len(self.class_names)
        model = efficientnet_b3(weights=None)  # Boş mimariyi oluştur

        # Son classifier katmanını Weli'nin sınıf sayısına göre ayarla
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)

        # Ağırlıkları yükle (strict=False → hafif uyumsuzluklara toleranslı)
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing:
            logger.warning(f"Eksik ağırlıklar (yüklenmedi): {missing[:5]}")
        if unexpected:
            logger.warning(f"Beklenmeyen ağırlıklar (görmezden gelindi): {unexpected[:5]}")

        return model

    def _find_gradcam_layer(self, model: nn.Module) -> nn.Module:
        """
        EfficientNet modelinin Grad-CAM için uygun son konvolüsyon katmanını döndürür.

        Strateji:
            - torchvision EfficientNet → model.features[-1] (son feature bloğu)
            - timm EfficientNet         → model.conv_head veya model.blocks[-1]
            - Fallback                  → modeldeki son Conv2d katmanı

        Args:
            model: Yüklenmiş EfficientNet modeli.

        Returns:
            Grad-CAM hedef katmanı (nn.Module).
        """
        # torchvision EfficientNet-B3 için standart hedef
        if hasattr(model, "features"):
            logger.debug("torchvision EfficientNet tespit edildi → features[-1] kullanılıyor.")
            return model.features[-1]

        # timm tabanlı EfficientNet için
        if hasattr(model, "conv_head"):
            logger.debug("timm EfficientNet tespit edildi → conv_head kullanılıyor.")
            return model.conv_head

        # Genel fallback: son Conv2d katmanını bul
        last_conv = None
        for module in model.modules():
            if isinstance(module, nn.Conv2d):
                last_conv = module

        if last_conv is not None:
            logger.debug(f"Fallback: son Conv2d katmanı → {last_conv}")
            return last_conv

        raise RuntimeError(
            "Grad-CAM için uygun hedef katman bulunamadı. "
            "Model mimarisini kontrol edin."
        )

    # ------------------------------------------------------------------
    # Ana Yükleme Metodu
    # ------------------------------------------------------------------

    def load_all(
        self,
        yolo_path: Optional[Path] = None,
        efficientnet_path: Optional[Path] = None,
        class_names: Optional[list[str]] = None,
    ) -> None:
        """
        Tüm AI modellerini sırayla belleğe yükler.

        Bu metod FastAPI'nin lifespan event'inde çağrılır.
        Herhangi bir model yükleme başarısız olursa hata fırlatır,
        uygulama başlamaz (fail-fast prensibi).

        Args:
            yolo_path:         YOLOv8 .pt dosyası yolu (None → varsayılan).
            efficientnet_path: EfficientNet .pt dosyası yolu (None → varsayılan).
            class_names:       Özel sınıf listesi (None → DEFAULT_CLASS_NAMES).
        """
        yolo_path        = yolo_path or DEFAULT_YOLO_PATH
        efficientnet_path= efficientnet_path or DEFAULT_EFFICIENTNET_PATH

        if class_names:
            self.class_names = class_names

        logger.info(f"🚀 Model yükleme başlıyor. Cihaz: {self.device.type.upper()}")
        logger.info(f"   YOLO yolu:        {yolo_path}")
        logger.info(f"   EfficientNet yolu:{efficientnet_path}")
        logger.info(f"   Sınıf sayısı:     {len(self.class_names)}")

        self._load_yolo(yolo_path)
        self._load_efficientnet(efficientnet_path)

        self.is_loaded = True
        logger.info("✅ Sprint 2 modelleri başarıyla yüklendi (YOLO + EfficientNet).")

        # Sprint 3 model referanslarını bağla (bağımsız try-except bloklar ile)
        self._load_sprint3_models()

        # Sprint 4 model referanslarını bağla
        self._load_sprint4_models()

    def _load_sprint3_models(self) -> None:
        """
        Sprint 3 modellerini yükler veya referanslarını alır.

        XGBoost lazy-load ile çalışır: ilk predict() çağrısında diskten yüklenir.
        LSTM ve Multimodal kendi store singleton'ları üzerinden lifespan'de yüklenir;
        bu metod yalnızca referansları alır, ikinci kez yükleme yapmaz.

        Her sub-blok bağımsız try-except ile korunur:
        Biri başarısız olsa diğerleri ve Sprint 2 modelleri etkilenmez.
        """
        logger.info("📦 Sprint 3 model referansları bağlanıyor...")

        # XGBoost RiskPredictor — lazy-load; yalnızca singleton alınır
        try:
            from app.services.risk_prediction_service import get_risk_predictor
            self.xgboost_predictor = get_risk_predictor()
            logger.info("✅ Sprint 3 XGBoost: RiskPredictor singleton alındı (lazy-load).")
        except Exception as exc:
            logger.warning("⚠️  Sprint 3 XGBoost referansı alınamadı: %s", exc)

        # LSTM Digital Twin store referansı
        try:
            from app.services.digital_twin_service import digital_twin_store
            self.lstm_twin_store = digital_twin_store
            logger.info(
                "✅ Sprint 3 LSTM: DigitalTwinModelStore referansı alındı (yükleme=%s).",
                digital_twin_store.is_loaded,
            )
        except Exception as exc:
            logger.warning("⚠️  Sprint 3 LSTM referansı alınamadı: %s", exc)

        # Multimodal Transformer store referansı
        try:
            from app.services.multimodal_service import multimodal_store
            self.multimodal_store = multimodal_store
            logger.info(
                "✅ Sprint 3 Multimodal: MultimodalModelStore referansı alındı (yükleme=%s).",
                multimodal_store.is_loaded,
            )
        except Exception as exc:
            logger.warning("⚠️  Sprint 3 Multimodal referansı alınamadı: %s", exc)

        self.sprint3_loaded = True
        logger.info("✅ Sprint 3 model referansları bağlandı.")

    def _load_sprint4_models(self) -> None:
        """
        Sprint 4 (Son Aşama) model singleton referanslarını alır.

        GNN modeli (GlobalGNNModelStore) ve Continual Learning servisi
        (RetrainingService) kendi modüllerinde zaten lifespan'de başlatılmış
        olabilir. Bu metod yalnızca referansları alır; ikinci kez yükleme
        yapmaz.

        Her alt-blok bağımsız try-except ile korunur:
        Biri başarısız olsa diğerleri ve önceki sprint modelleri etkilenmez.
        """
        logger.info("📦 Sprint 4 model referansları bağlanıyor...")

        # ── GNN Küresel Risk Modeli ──────────────────────────────────────────
        try:
            from app.services.global_risk_service import global_gnn_store
            self.sprint4_gnn_store = global_gnn_store
            logger.info(
                "✅ Sprint 4 GNN: GlobalGNNModelStore referansı alındı (yüklü=%s).",
                global_gnn_store.is_loaded,
            )
        except Exception as exc:
            logger.warning("⚠️  Sprint 4 GNN referansı alınamadı: %s", exc)

        # ── Continual Learning Servisi ───────────────────────────────────────
        try:
            from app.services.retraining_service import retraining_service
            self.sprint4_retraining_svc = retraining_service
            logger.info(
                "✅ Sprint 4 Continual Learning: RetrainingService referansı alındı."
            )
        except Exception as exc:
            logger.warning(
                "⚠️  Sprint 4 Continual Learning referansı alınamadı: %s", exc
            )

        self.sprint4_loaded = True
        logger.info("✅ Sprint 4 model referansları bağlandı.")

    def unload_all(self) -> None:
        """
        Tüm modelleri bellekten temizler.
        FastAPI shutdown event'inde çağrılır.
        Sprint 2 (YOLO, EfficientNet) ve Sprint 3 referansları sıfırlanır.
        """
        # Sprint 2 modelleri
        self.yolo = None
        self.efficientnet = None
        self.gradcam_target_layer = None
        self.is_loaded = False

        # Sprint 3 referanslarını sıfırla (asil temizlik kendi store'larında yapılır)
        self.xgboost_predictor = None
        self.lstm_twin_store   = None
        self.multimodal_store  = None
        self.sprint3_loaded    = False

        # Sprint 4 referanslarını sıfırla
        self.sprint4_gnn_store       = None
        self.sprint4_retraining_svc  = None
        self.sprint4_loaded          = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("CUDA belleği temizlendi.")

        logger.info("♻️  Tüm AI modelleri bellekten kaldırıldı.")


# ---------------------------------------------------------------------------
# Global Singleton — Tüm uygulama bu nesneyi paylaşır
# ---------------------------------------------------------------------------

# Bu nesne main.py'deki lifespan event'inde doldurulur.
# Endpoint'ler bu nesneye erişerek modelleri kullanır.
model_store = ModelStore()
