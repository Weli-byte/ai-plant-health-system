# =============================================================================
# schemas/ai_schemas.py
#
# Bu dosya, AI endpoint'lerinin girdi/çıktı veri modellerini (Pydantic şemaları)
# tanımlar. Tüm API yanıtları bu şemalardan türetilir; bu sayede:
#   - Otomatik veri doğrulama (FastAPI)
#   - Swagger UI'da açık dökümanasyon
#   - Type safety (mypy uyumlu)
# =============================================================================

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ortak Yanıt Yapıları
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    """YOLO tarafından tespit edilen nesnenin piksel koordinatları."""
    x1: int = Field(..., description="Sol-üst köşe: X koordinatı (piksel)", ge=0)
    y1: int = Field(..., description="Sol-üst köşe: Y koordinatı (piksel)", ge=0)
    x2: int = Field(..., description="Sağ-alt köşe: X koordinatı (piksel)", ge=0)
    y2: int = Field(..., description="Sağ-alt köşe: Y koordinatı (piksel)", ge=0)

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


# ---------------------------------------------------------------------------
# Endpoint 1: /ai/detect_leaf
# ---------------------------------------------------------------------------

class LeafDetectionResponse(BaseModel):
    """
    /ai/detect_leaf endpoint'inin yanıt şeması.
    YOLOv8 modelinin yaprak tespiti sonuçlarını temsil eder.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    leaf_detected: bool = Field(
        ...,
        description="Görselde en az bir yaprak tespit edildi mi?"
    )
    bounding_box: Optional[BoundingBox] = Field(
        None,
        description="Tespit edilen yaprağın piksel koordinatları. "
                    "Yaprak bulunamazsa null."
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="YOLOv8 güven skoru (0.0 – 1.0). Yaprak bulunamazsa null."
    )
    cropped_leaf_base64: Optional[str] = Field(
        None,
        description="Kırpılmış yaprak görseli (base64 JPEG). "
                    "Sonraki endpoint'e bu değeri gönderin."
    )
    original_width: int  = Field(..., description="Yüklenen orijinal görselin genişliği (piksel).")
    original_height: int = Field(..., description="Yüklenen orijinal görselin yüksekliği (piksel).")
    message: str         = Field(..., description="İnsan okunabilir durum mesajı.")

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "leaf_detected": True,
            "bounding_box": {"x1": 42, "y1": 58, "x2": 310, "y2": 290},
            "confidence": 0.9231,
            "cropped_leaf_base64": "<base64_string>",
            "original_width": 640,
            "original_height": 480,
            "message": "Yaprak başarıyla tespit edildi."
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint 2: /ai/classify_disease
# ---------------------------------------------------------------------------

class DiseaseClassificationRequest(BaseModel):
    """
    /ai/classify_disease endpoint'inin istek gövdesi.
    detect_leaf'ten gelen kırpılmış yaprağı alır.
    """
    cropped_leaf_base64: str = Field(
        ...,
        description="detect_leaf yanıtındaki 'cropped_leaf_base64' değeri. "
                    "EfficientNet-B3 bu input üzerinde inference yapar."
    )

    model_config = {"json_schema_extra": {
        "example": {
            "cropped_leaf_base64": "<detect_leaf yanıtından alınan base64 string>"
        }
    }}


class DiseaseClassificationResponse(BaseModel):
    """
    /ai/classify_disease endpoint'inin yanıt şeması.
    EfficientNet-B3 sınıflandırma sonuçlarını temsil eder.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    predicted_class: str = Field(
        ...,
        description="Modelin tahmin ettiği hastalık sınıfının adı."
    )
    predicted_class_index: int = Field(
        ...,
        description="Tahmin edilen sınıfın integer indeksi."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="En yüksek sınıf için softmax güven skoru (0.0 – 1.0)."
    )
    all_scores: dict[str, float] = Field(
        ...,
        description="Tüm hastalık sınıfları için softmax güven skoru sözlüğü."
    )
    message: str = Field(..., description="İnsan okunabilir durum mesajı.")

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "predicted_class": "Powdery Mildew",
            "predicted_class_index": 1,
            "confidence": 0.8743,
            "all_scores": {
                "Healthy": 0.0412,
                "Powdery Mildew": 0.8743,
                "Leaf Blight": 0.0521,
                "Rust": 0.0324
            },
            "message": "Hastalık sınıflandırması tamamlandı."
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint 3: /ai/explain_prediction
# ---------------------------------------------------------------------------

class GradCAMRequest(BaseModel):
    """
    /ai/explain_prediction endpoint'inin istek gövdesi.
    Kırpılmış yaprak ve (isteğe bağlı) hedef sınıf indeksini alır.
    """
    cropped_leaf_base64: str = Field(
        ...,
        description="detect_leaf yanıtındaki 'cropped_leaf_base64' değeri."
    )
    target_class_index: Optional[int] = Field(
        None,
        description="Grad-CAM'in açıklayacağı sınıfın indeksi. "
                    "Belirtilmezse modelin tahmin ettiği sınıf kullanılır."
    )

    model_config = {"json_schema_extra": {
        "example": {
            "cropped_leaf_base64": "<base64 string>",
            "target_class_index": None
        }
    }}


class GradCAMResponse(BaseModel):
    """
    /ai/explain_prediction endpoint'inin yanıt şeması.
    Grad-CAM ısı haritası ve bindirme görselini içerir.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    heatmap_base64: str = Field(
        ...,
        description="Renkli Grad-CAM ısı haritası (base64 JPEG). "
                    "Kırmızı = yüksek aktivasyon, Mavi = düşük aktivasyon."
    )
    overlay_base64: str = Field(
        ...,
        description="Orijinal yaprak üzerine bindirilen ısı haritası (base64 JPEG)."
    )
    target_class: str = Field(
        ...,
        description="Grad-CAM'in odaklandığı hastalık sınıfının adı."
    )
    target_class_index: int = Field(
        ...,
        description="Hedef sınıfın integer indeksi."
    )
    message: str = Field(..., description="İnsan okunabilir durum mesajı.")


# ---------------------------------------------------------------------------
# Endpoint: /ai/analyze (Tam İşlem Akışı)
# ---------------------------------------------------------------------------

class FullAnalysisResponse(BaseModel):
    """
    /ai/analyze endpoint'inin yanıt şeması.
    Tek seferde tüm pipeline çalıştırır:
    YOLO → EfficientNet → Grad-CAM
    """
    success: bool
    leaf_detection: LeafDetectionResponse
    disease_classification: Optional[DiseaseClassificationResponse] = Field(
        None,
        description="Yaprak tespit edilirse doldurulur, yoksa null."
    )
    gradcam: Optional[GradCAMResponse] = Field(
        None,
        description="Sınıflandırma başarılıysa doldurulur, yoksa null."
    )
    message: str


# ---------------------------------------------------------------------------
# Hata Yanıtı
# ---------------------------------------------------------------------------

class AIErrorResponse(BaseModel):
    """Tüm AI endpoint'lerinde hata durumunda döndürülen şema."""
    success: bool = False
    error_type: str = Field(
        ...,
        description="Hata kategorisi: 'model_not_loaded', 'inference_error', vb."
    )
    detail: str  = Field(..., description="Hata açıklaması.")
    message: str = Field(
        "Bir hata oluştu. Lütfen tekrar deneyin.",
        description="Kullanıcıya gösterilecek mesaj."
    )
