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
# Endpoint: /ai/chat (Zirai Asistan)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Konuşma geçmişindeki tek bir mesaj."""
    role: str = Field(..., description="'user' veya 'assistant'")
    content: str = Field(..., description="Mesaj içeriği.")

class ChatRequest(BaseModel):
    """Chat asistanı için kullanıcı mesajını içeren şema."""
    message: str = Field(..., description="Kullanıcının sorduğu zirai soru.")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Önceki konuşma mesajları (Anthropic messages formatında)."
    )

class ChatResponse(BaseModel):
    """Chat asistanından dönen yanıt şeması."""
    success: bool = True
    response: str = Field(..., description="Yapay zeka asistanının cevabı.")
    message: str = "Asistan yanıtı hazır."


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


# =============================================================================
# Sprint 3 — Yeni Şemalar
# Aşağıdaki şemalar; risk tahmini, dijital ikiz simülasyonu ve tarım
# öneri endpoint'leri için kullanılır. Üsteki eski şemalara dokunulmamıştır.
# =============================================================================


# ---------------------------------------------------------------------------
# Endpoint: /sprint3/predict_risk
# XGBoost + Multimodal Transformer — Hastalık Risk Skoru (0-100)
# ---------------------------------------------------------------------------

class ClimateDataRequest(BaseModel):
    """
    /sprint3/predict_risk endpoint'inin istek gövdesi.

    İklim ve çevre verilerini alarak 0-100 arasında bir hastalık risk skoru
    döndürür. Hem XGBoost tabanlı tahmin hem de kural tabanlı düzeltmeler
    bu şema üzerinden beslenir.
    """
    temperature: float = Field(
        ...,
        ge=-10.0,
        le=50.0,
        description="Hava sıcaklığı (°C). Aralık: -10 ile 50.",
        examples=[24.5],
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Bağıl nem oranı (%). Aralık: 0 ile 100.",
        examples=[78.0],
    )
    rainfall: float = Field(
        ...,
        ge=0.0,
        le=400.0,
        description="Yağış miktarı (mm). Aralık: 0 ile 400.",
        examples=[55.0],
    )
    wind_speed: float = Field(
        ...,
        ge=0.0,
        le=120.0,
        description="Rüzgar hızı (km/s). Aralık: 0 ile 120.",
        examples=[12.0],
    )
    soil_moisture: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Toprak nemi (%). İsteğe bağlı; verilirse risk hesabına dahil edilir.",
        examples=[45.0],
    )
    season: str = Field(
        ...,
        description="Mevsim: 'spring', 'summer', 'autumn', 'winter'.",
        examples=["spring"],
    )
    plant_health_status: Optional[str] = Field(
        None,
        description="Bitkinin mevcut sağlık durumu: 'healthy', 'stressed', 'diseased'. "
                    "İsteğe bağlıdır; verilirse öneri motoru tarafından kullanılır.",
        examples=["healthy"],
    )
    disease_name: Optional[str] = Field(
        None,
        description="Tespit edilmiş hastalık adı (örn. 'Powdery Mildew'). "
                    "İsteğe bağlıdır; ilaç önerisi için kullanılır.",
        examples=["Powdery Mildew"],
    )

    model_config = {"json_schema_extra": {
        "example": {
            "temperature": 24.5,
            "humidity": 78.0,
            "rainfall": 55.0,
            "wind_speed": 12.0,
            "soil_moisture": 45.0,
            "season": "spring",
            "plant_health_status": "healthy",
            "disease_name": None,
        }
    }}


class RiskScoreResponse(BaseModel):
    """
    /sprint3/predict_risk endpoint'inin yanıt şeması.

    XGBoost modeli çıktısını alır, 0-100 arasında normalize eder ve
    çiftçiye yönelik risk seviyesi + açıklamasını döndürür.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Hesaplanan hastalık risk skoru (0=Risksiz, 100=Kritik).",
    )
    risk_level: str = Field(
        ...,
        description="Risk seviyesi: 'Low', 'Medium', 'High', 'Critical'.",
    )
    risk_label: str = Field(
        ...,
        description="Risk seviyesinin okunabilir etiketi (örn. 'High Risk').",
    )
    risk_color: str = Field(
        ...,
        description="UI'da kullanılmak üzere renk kodu (hex). "
                    "Örn: '#22c55e' (yeşil), '#ef4444' (kırmızı).",
    )
    action: str = Field(
        ...,
        description="Çiftçi için önerilen acil eylem açıklaması.",
    )
    recommendations: list[str] = Field(
        ...,
        description="İklim koşullarına göre üretilen önerilerin listesi.",
    )
    model_used: str = Field(
        ...,
        description="Tahminde kullanılan model: 'xgboost', 'rule_based' vb.",
    )
    message: str = Field(..., description="İnsan okunabilir durum mesajı.")

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "risk_score": 67.4,
            "risk_level": "High",
            "risk_label": "High Risk",
            "risk_color": "#f97316",
            "action": "Inspect plants daily. Consider preventive fungicide application.",
            "recommendations": [
                "🌫️ High humidity (78%). Improve air circulation.",
                "🌸 Spring: begin sulfur-based preventive treatment.",
            ],
            "model_used": "xgboost",
            "message": "Risk skoru başarıyla hesaplandı.",
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint: /sprint3/get_plant_future
# LSTM Digital Twin — 3 ve 7 Günlük Risk Tahmini
# ---------------------------------------------------------------------------

class PlantFutureRequest(BaseModel):
    """
    /sprint3/get_plant_future endpoint'inin istek gövdesi.

    LSTM tabanlı dijital ikiz modeline beslenen zaman serisi penceresi.
    Her gün için 7 özellik girilmesi gerekmektedir.
    """
    observations: list[list[float]] = Field(
        ...,
        min_length=3,
        description=(
            "Geçmiş günlük gözlem penceresi. Her iç liste 7 değer içermelidir: "
            "[risk_score, temperature, humidity, rainfall, wind_speed, soil_moisture, plant_health]. "
            "En az 3 gün, önerilen 7 gün."
        ),
        examples=[[[0.3, 22.0, 70.0, 30.0, 10.0, 50.0, 0.8]]],
    )
    location_label: Optional[str] = Field(
        None,
        description="İsteğe bağlı: Tarla veya konum etiketi (yanıtta iade edilir).",
        examples=["Tarla-A / İzmir"],
    )

    model_config = {"json_schema_extra": {
        "example": {
            "observations": [
                [0.2, 20.0, 65.0, 25.0, 8.0, 48.0, 0.9],
                [0.3, 22.0, 72.0, 40.0, 12.0, 52.0, 0.85],
                [0.4, 24.0, 78.0, 55.0, 15.0, 58.0, 0.75],
                [0.5, 25.0, 80.0, 60.0, 18.0, 60.0, 0.70],
                [0.6, 26.0, 82.0, 65.0, 20.0, 62.0, 0.65],
                [0.65, 24.5, 79.0, 58.0, 14.0, 57.0, 0.68],
                [0.7, 23.0, 76.0, 50.0, 11.0, 54.0, 0.72],
            ],
            "location_label": "Tarla-A / İzmir",
        }
    }}


class DayForecast(BaseModel):
    """Tek bir günün tahmin sonucu."""
    day: int = Field(..., description="Tahmin ufku (gün sayısı, örn. 3 veya 7).")
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Tahmin edilen risk skoru (0-1 aralığı, normalize).",
    )
    risk_score_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Yüzdelik risk skoru (0-100 aralığı).",
    )
    risk_level: str = Field(
        ...,
        description="Risk seviyesi etiketi: 'Low', 'Medium', 'High', 'Critical'.",
    )


class PlantFutureResponse(BaseModel):
    """
    /sprint3/get_plant_future endpoint'inin yanıt şeması.

    LSTM digital twin modelinden gelen 3 ve 7 günlük risk tahminlerini
    yapılandırılmış biçimde sunar.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    location_label: Optional[str] = Field(
        None,
        description="İstek ile birlikte gönderilen konum etiketi.",
    )
    forecast_3_day: DayForecast = Field(
        ...,
        description="3 gün sonrası için risk tahmini.",
    )
    forecast_7_day: DayForecast = Field(
        ...,
        description="7 gün sonrası için risk tahmini.",
    )
    trend: str = Field(
        ...,
        description="Risk trendi: 'increasing', 'stable', 'decreasing'.",
    )
    model_version: str = Field(
        ...,
        description="Kullanılan LSTM model sürümü.",
    )
    message: str = Field(..., description="İnsan okunabilir durum mesajı.")

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "location_label": "Tarla-A / İzmir",
            "forecast_3_day": {
                "day": 3,
                "risk_score": 0.72,
                "risk_score_pct": 72.0,
                "risk_level": "High",
            },
            "forecast_7_day": {
                "day": 7,
                "risk_score": 0.85,
                "risk_score_pct": 85.0,
                "risk_level": "Critical",
            },
            "trend": "increasing",
            "model_version": "1.0.0",
            "message": "Dijital ikiz simülasyonu tamamlandı.",
        }
    }}


# ---------------------------------------------------------------------------
# Endpoint: /sprint3/get_farming_advice
# Kural Tabanlı Tarım Danışma Sistemi + Zirai İlaç Önerisi
# ---------------------------------------------------------------------------

class FarmingAdviceRequest(BaseModel):
    """
    /sprint3/get_farming_advice endpoint'inin istek gövdesi.

    İklim koşulları ve bitki sağlık durumu girildiğinde kural motoru devreye
    girerek hem tarım tavsiyesi hem de ilaç önerisi üretir.
    """
    temperature: float = Field(
        ...,
        ge=-10.0,
        le=50.0,
        description="Hava sıcaklığı (°C).",
        examples=[26.0],
    )
    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Bağıl nem oranı (%).",
        examples=[83.0],
    )
    rainfall: float = Field(
        ...,
        ge=0.0,
        le=400.0,
        description="Yağış miktarı (mm).",
        examples=[60.0],
    )
    wind_speed: float = Field(
        ...,
        ge=0.0,
        le=120.0,
        description="Rüzgar hızı (km/s).",
        examples=[15.0],
    )
    season: str = Field(
        ...,
        description="Mevsim: 'spring', 'summer', 'autumn', 'winter'.",
        examples=["spring"],
    )
    plant_health_status: str = Field(
        ...,
        description="Bitkinin mevcut sağlık durumu: 'healthy', 'stressed', 'diseased'.",
        examples=["stressed"],
    )
    disease_name: Optional[str] = Field(
        None,
        description="Tespit edilmiş hastalık adı (örn. 'Powdery Mildew', 'Apple Scab'). "
                    "Belirtilirse ilaç veritabanından eşleşen ürün önerilir.",
        examples=["Powdery Mildew"],
    )
    crop_type: Optional[str] = Field(
        None,
        description="Bitki/ürün türü (örn. 'wheat', 'tomato', 'apple'). "
                    "Belirtilirse öneri içeriği zenginleştirilir.",
        examples=["apple"],
    )

    model_config = {"json_schema_extra": {
        "example": {
            "temperature": 26.0,
            "humidity": 83.0,
            "rainfall": 60.0,
            "wind_speed": 15.0,
            "season": "spring",
            "plant_health_status": "stressed",
            "disease_name": "Powdery Mildew",
            "crop_type": "apple",
        }
    }}


class PesticideRecommendation(BaseModel):
    """Tek bir zirai ilaç önerisi."""
    disease: str = Field(..., description="Eşleşen hastalık adı.")
    product_type: str = Field(
        ...,
        description="İlaç tipi (örn. 'fungicide', 'bactericide', 'insecticide').",
    )
    active_ingredient: str = Field(
        ...,
        description="Aktif madde adı (örn. 'sulfur', 'copper hydroxide').",
    )
    product_name: str = Field(
        ...,
        description="Ticari ürün adı veya jenerik ismi.",
    )
    application_notes: str = Field(
        ...,
        description="Uygulama notları (doz, zamanlama, güvenlik bilgisi).",
    )


class FarmingAdviceResponse(BaseModel):
    """
    /sprint3/get_farming_advice endpoint'inin yanıt şeması.

    Kural motorundan gelen tarım önerileri ve ilaç veritabanından
    eşleşen ürün bilgilerini birleştirerek çiftçiye kapsamlı tavsiye sunar.
    """
    success: bool = Field(..., description="İşlem başarılı mı?")
    risk_level: str = Field(
        ...,
        description="Hesaplanan risk seviyesi: 'Low', 'Medium', 'High', 'Critical'.",
    )
    farming_advice: list[str] = Field(
        ...,
        description="Kural motorundan üretilen tarım önerilerinin listesi.",
    )
    pesticide_recommendations: list[PesticideRecommendation] = Field(
        ...,
        description="Hastalık ve koşullara göre önerilen zirai ilaçlar.",
    )
    irrigation_advice: str = Field(
        ...,
        description="Sulama önerisi.",
    )
    general_notes: str = Field(
        ...,
        description="Genel gözlem notu veya uyarı.",
    )
    message: str = Field(..., description="İnsan okunabilir durum mesajı.")

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "risk_level": "High",
            "farming_advice": [
                "🌫️ Nem %83 — bitkilerin arasındaki hava sirkülasyonunu artırın.",
                "⚠️ Powdery Mildew risk altında. Kükürt bazlı fungisit uygulayın.",
            ],
            "pesticide_recommendations": [
                {
                    "disease": "Powdery Mildew",
                    "product_type": "fungicide",
                    "active_ingredient": "sulfur",
                    "product_name": "Thiovit Jet",
                    "application_notes": "7-10 günde bir, sabah erken saatlerde uygulayın.",
                }
            ],
            "irrigation_advice": "Sabah erken sulayın; akşam sulamaktan kaçının.",
            "general_notes": "Yüksek nem ve sıcaklık Powdery Mildew gelişimi için elverişli.",
            "message": "Tarım danışma raporu hazırlandı.",
        }
    }}
