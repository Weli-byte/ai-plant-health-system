# =============================================================================
# routes/ai_detection.py
#
# Sprint 2 — AI Endpoint'leri (Gerçek Implementasyon)
#
# Bu dosya üç adet AI endpoint'i ve bir tam pipeline endpoint'i tanımlar:
#
#   POST /ai/detect_leaf          → YOLOv8 yaprak tespiti
#   POST /ai/classify_disease     → EfficientNet-B3 hastalık sınıflandırma
#   POST /ai/explain_prediction   → Grad-CAM ısı haritası
#   POST /ai/analyze              → Tüm pipeline tek seferde (kolaylık için)
#
# Mimari Notlar:
#   - Modeller, main.py'nin lifespan event'inde belleğe yüklenir.
#   - Bu router, model_store singleton'ını import ederek hazır modelleri kullanır.
#   - Her endpoint bağımsız çalışabilir (modüler akış).
# =============================================================================

import asyncio
import logging
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from openai import AsyncOpenAI
import openai

# AI servis fonksiyonları
from app.services.leaf_detection_service import detect_leaf
from app.services.disease_classification_service import (
    classify_disease,
    generate_gradcam,
)

# Merkezi model deposu (lifespan'de doldurulur)
from app.core.model_manager import model_store

# Uygulama ayarları
from app.config.settings import settings

# Pydantic yanıt şemaları
from app.schemas.ai_schemas import (
    AIErrorResponse,
    BoundingBox,
    ChatRequest,
    ChatResponse,
    DiseaseClassificationRequest,
    DiseaseClassificationResponse,
    DiseaseEnrichment,
    FullAnalysisResponse,
    GradCAMRequest,
    GradCAMResponse,
    LeafDetectionResponse,
    TreatmentProduct,
)

logger = logging.getLogger(__name__)


def _to_bounding_box(bb) -> "BoundingBox | None":
    """Convert [x1,y1,x2,y2] list from service layer to Pydantic BoundingBox."""
    if bb is None:
        return None
    return BoundingBox(x1=int(bb[0]), y1=int(bb[1]), x2=int(bb[2]), y2=int(bb[3]))


# ---------------------------------------------------------------------------
# Hastalık Zenginleştirme Veritabanı
# ---------------------------------------------------------------------------

DISEASE_ENRICHMENT_DB: dict[str, dict] = {
    "Healthy": {
        "disease_name_tr": "Sağlıklı Bitki",
        "disease_name_en": "Healthy",
        "description": "Bitkide herhangi bir hastalık belirtisi tespit edilmedi. Mevcut bakım uygulamalarını sürdürün.",
        "pathogen_type": "none",
        "spread_speed": "none",
        "affected_parts": [],
        "risk_level": 1,
        "current_stage": "Hastalık yok",
        "spread_risk": "low",
        "estimated_timeline": "Belirsiz — bitki sağlıklı",
        "treatment_products": [],
        "cultural_measures": [
            "Düzenli sulama programını sürdürün",
            "Dengeli gübreleme yapın",
            "Hava sirkülasyonunu sağlamak için budama yapın",
            "Toprağın nem dengesini izleyin",
        ],
        "prognosis_with_treatment": "Bitki sağlıklı durumda kalmaya devam edecek.",
        "prognosis_without_treatment": "Önlem alınmazsa çevresel stres faktörlerine karşı savunmasız kalabilir.",
        "harvest_impact": "Hasatta herhangi bir olumsuz etki beklenmemektedir.",
        "next_season_prevention": "Sertifikalı tohumluk kullanın ve rotasyon uygulayın.",
    },
    "Powdery Mildew": {
        "disease_name_tr": "Külleme",
        "disease_name_en": "Powdery Mildew",
        "description": "Yaprak yüzeyinde beyaz unlu lekeler oluşturan fungal bir hastalık. Yüksek nem ve ılık havada hızla yayılır.",
        "pathogen_type": "fungal",
        "spread_speed": "fast",
        "affected_parts": ["Yapraklar", "Sürgünler", "Çiçekler", "Meyveler"],
        "risk_level": 3,
        "current_stage": "Aktif enfeksiyon",
        "spread_risk": "high",
        "estimated_timeline": "Tedavi edilmezse 7-14 gün içinde tüm bitkiye yayılabilir",
        "treatment_products": [
            TreatmentProduct(
                name="Thiovit Jet",
                active_ingredient="Kükürt (%80 WG)",
                dose="200-300 g / 100 L su",
                timing="Sabah erken veya akşam serinliğinde",
                frequency="7-10 günde bir",
                price_range_tl="150-250 TL/kg",
            ),
            TreatmentProduct(
                name="Topas 100 EC",
                active_ingredient="Penkonazol (%10 EC)",
                dose="10 ml / 100 L su",
                timing="İlk belirtilerde hemen",
                frequency="14 günde bir, max 3 uygulama",
                price_range_tl="200-350 TL/250 ml",
            ),
        ],
        "cultural_measures": [
            "Enfekte yaprakları hemen uzaklaştırın ve imha edin",
            "Bitki sıralarının arasındaki mesafeyi artırarak hava sirkülasyonu sağlayın",
            "Akşam saatlerinde sulamaktan kaçının",
            "Azotlu gübreyi aşırı kullanmayın",
        ],
        "prognosis_with_treatment": "Fungisit uygulaması ile 10-14 gün içinde yeni enfeksiyon durur ve mevcut lekeler kurur.",
        "prognosis_without_treatment": "Hastalık hızla yayılır, fotosentez kapasitesi düşer, ürün kaybı %30-50'ye ulaşabilir.",
        "harvest_impact": "Erken müdahale ile hasat kaybı %10 altında tutulabilir. Gecikme durumunda %30-50 kayıp riski.",
        "next_season_prevention": "Dayanıklı çeşitler seçin. İlkbahar başında kükürt bazlı koruyucu uygulama yapın.",
    },
    "Leaf Blight": {
        "disease_name_tr": "Yaprak Yanıklığı",
        "disease_name_en": "Leaf Blight",
        "description": "Yapraklarda kahverengi-siyah nekrotik lekeler oluşturan fungal/bakteriyel bir hastalık. Serin ve yağışlı havalarda hızlanır.",
        "pathogen_type": "fungal",
        "spread_speed": "medium",
        "affected_parts": ["Yapraklar", "Yaprak sapları", "Alt gövde"],
        "risk_level": 3,
        "current_stage": "Erken-orta evre enfeksiyon",
        "spread_risk": "medium",
        "estimated_timeline": "14-21 gün içinde ciddi doku kaybı oluşabilir",
        "treatment_products": [
            TreatmentProduct(
                name="Dithane M-45",
                active_ingredient="Mankozeb (%80 WP)",
                dose="200 g / 100 L su",
                timing="Yağmur öncesi ve sonrası",
                frequency="7-10 günde bir",
                price_range_tl="100-180 TL/kg",
            ),
            TreatmentProduct(
                name="Ridomil Gold",
                active_ingredient="Metalaksil + Mankozeb",
                dose="250 g / 100 L su",
                timing="Hastalık ilk görüldüğünde",
                frequency="10-14 günde bir",
                price_range_tl="300-450 TL/kg",
            ),
        ],
        "cultural_measures": [
            "Hasta yaprakları toplayarak yakın veya derin gömin",
            "Toprak sıçramasını önlemek için malç kullanın",
            "Sulamayı sabah saatlerinde yapın",
            "Rotasyon uygulayın — aynı aileyi arka arkaya dikmekten kaçının",
        ],
        "prognosis_with_treatment": "Erken müdahale ile 2-3 hafta içinde hastalık kontrol altına alınabilir.",
        "prognosis_without_treatment": "Yaprak kaybı artar, fotosentez düşer, verim %20-40 azalabilir.",
        "harvest_impact": "Orta düzeyde etki — erken müdahale ile %15 altında kayıp mümkün.",
        "next_season_prevention": "Sertifikalı tohumluk kullanın. Ekim öncesi toprak fungisit uygulaması yapın.",
    },
    "Rust": {
        "disease_name_tr": "Pas Hastalığı",
        "disease_name_en": "Rust",
        "description": "Yaprak altında turuncu-kahverengi spor yığınları oluşturan fungal hastalık. Rüzgarla kolayca yayılır.",
        "pathogen_type": "fungal",
        "spread_speed": "fast",
        "affected_parts": ["Yapraklar (alt yüzey)", "Yaprak sapları", "Gövde"],
        "risk_level": 4,
        "current_stage": "Aktif sporlanma evresi",
        "spread_risk": "high",
        "estimated_timeline": "Uygun koşullarda 5-10 gün içinde yeni enfeksiyonlar oluşur",
        "treatment_products": [
            TreatmentProduct(
                name="Tilt 250 EC",
                active_ingredient="Propikonazol (%25 EC)",
                dose="10-15 ml / 100 L su",
                timing="İlk pas lekeleri görüldüğünde derhal",
                frequency="14-21 günde bir",
                price_range_tl="180-280 TL/250 ml",
            ),
            TreatmentProduct(
                name="Folicur 250 EW",
                active_ingredient="Tebukonazol (%25 EW)",
                dose="10 ml / 100 L su",
                timing="Koruyucu veya tedavi amaçlı",
                frequency="14 günde bir, max 3 uygulama",
                price_range_tl="200-320 TL/500 ml",
            ),
        ],
        "cultural_measures": [
            "Enfekte bitki artıklarını tarladan uzaklaştırın",
            "Dayanıklı çeşitler tercih edin",
            "Bitki sıklığını azaltarak hava sirkülasyonunu iyileştirin",
            "Alternatif konakçı bitkileri yakın alanlarda yetiştirmeyin",
        ],
        "prognosis_with_treatment": "Sistemik fungisit ile 7-10 gün içinde sporlanma durur; yeni yapraklar sağlıklı çıkar.",
        "prognosis_without_treatment": "Sporlar rüzgarla yayılarak tüm tarlayı etkiler; verim kaybı %40-70'e ulaşabilir.",
        "harvest_impact": "Yüksek etki — gecikmeli müdahale ile %30-50 verim kaybı riski.",
        "next_season_prevention": "Hasat sonrası bitki artıklarını imha edin. İlkbaharda koruyucu triazol uygulaması yapın.",
    },
    "Leaf Spot": {
        "disease_name_tr": "Yaprak Leke Hastalığı",
        "disease_name_en": "Leaf Spot",
        "description": "Yapraklarda belirgin kenarlı koyu lekeler oluşturan fungal veya bakteriyel hastalık. Nemli koşullarda artar.",
        "pathogen_type": "fungal",
        "spread_speed": "medium",
        "affected_parts": ["Yapraklar", "Meyveler", "Sürgünler"],
        "risk_level": 2,
        "current_stage": "Başlangıç-orta evre",
        "spread_risk": "medium",
        "estimated_timeline": "2-4 hafta içinde lekeler büyür ve birleşebilir",
        "treatment_products": [
            TreatmentProduct(
                name="Captan 50 WP",
                active_ingredient="Kaptan (%50 WP)",
                dose="150-200 g / 100 L su",
                timing="Yağış öncesi koruyucu uygulama",
                frequency="10-14 günde bir",
                price_range_tl="80-140 TL/kg",
            ),
        ],
        "cultural_measures": [
            "Hasta yaprakları toplayıp imha edin",
            "Aşırı sulama ve üstten sulamadan kaçının",
            "Dayanıklı çeşit kullanın",
            "Bitkileri aşırı sık dikmekten kaçının",
        ],
        "prognosis_with_treatment": "Erken müdahale ile 2-3 hafta içinde kontrol sağlanır.",
        "prognosis_without_treatment": "Lekeler büyür, yaprak dökümü artar, kalite düşer.",
        "harvest_impact": "Hafif-orta etki. Meyve kalitesi düşebilir (%10-25 pazar değeri kaybı).",
        "next_season_prevention": "Toprak rotasyonu uygulayın. Ekim öncesi fide dezenfeksiyonu yapın.",
    },
    "Bacterial Wilt": {
        "disease_name_tr": "Bakteriyel Solgunluk",
        "disease_name_en": "Bacterial Wilt",
        "description": "İletim demetlerini tıkayan bakteri enfeksiyonu. Bitki aniden solar ve kurur. İklim değişiminden etkilenir.",
        "pathogen_type": "bacterial",
        "spread_speed": "fast",
        "affected_parts": ["İletim demetleri", "Gövde", "Yapraklar", "Kökler"],
        "risk_level": 5,
        "current_stage": "Aktif sistemik enfeksiyon",
        "spread_risk": "high",
        "estimated_timeline": "Semptomsuz dönem sonrası 3-7 günde hızlı çöküş",
        "treatment_products": [
            TreatmentProduct(
                name="Kocide 2000",
                active_ingredient="Bakır hidroksit (%53.8 WG)",
                dose="150-250 g / 100 L su",
                timing="Önleyici; hastalık görülmeden önce",
                frequency="7-10 günde bir",
                price_range_tl="250-400 TL/kg",
            ),
        ],
        "cultural_measures": [
            "Hasta bitkileri derhal söküp yakın — kompostlamayın",
            "Enfekte toprakta en az 3 yıl rotasyon uygulayın",
            "Sulama ekipmanlarını %10 çamaşır suyu ile dezenfekte edin",
            "Böcek vektörlerini (özellikle nematodları) kontrol edin",
        ],
        "prognosis_with_treatment": "Kimyasal tedavi sınırlı etkili; dayanıklı çeşit ve rotasyon esas çözümdür.",
        "prognosis_without_treatment": "Bitki kaybı kaçınılmaz. Enfeksiyon toprağa ve komşu bitkilere yayılır.",
        "harvest_impact": "Çok yüksek — enfekte bitkiler tamamen yitirilir (%80-100 kayıp).",
        "next_season_prevention": "Sadece sertifikalı ve dayanıklı çeşit kullanın. Toprak fumigasyonu değerlendirin.",
    },
    "Mosaic Virus": {
        "disease_name_tr": "Mozaik Virüsü",
        "disease_name_en": "Mosaic Virus",
        "description": "Yapraklarda sarı-yeşil mozaik desen, kıvırma ve bodurlaşmaya yol açan viral enfeksiyon. Yaprak bitleri ile taşınır.",
        "pathogen_type": "viral",
        "spread_speed": "medium",
        "affected_parts": ["Yapraklar", "Sürgünler", "Meyveler"],
        "risk_level": 4,
        "current_stage": "Sistemik viral enfeksiyon",
        "spread_risk": "high",
        "estimated_timeline": "Viral yayılım 2-4 hafta içinde tüm bitkiyi etkiler",
        "treatment_products": [
            TreatmentProduct(
                name="Confidor 200 OD",
                active_ingredient="İmidakloprid (%17.8 OD)",
                dose="5 ml / 100 L su",
                timing="Yaprak biti vektörlerine karşı",
                frequency="Gerektiğinde, max 2 uygulama",
                price_range_tl="120-200 TL/250 ml",
            ),
        ],
        "cultural_measures": [
            "Virüslü bitkileri söküp imha edin — tedavi mümkün değil",
            "Vektör böcekleri (yaprak bitleri, thrips) ilaçla kontrol edin",
            "Tarla çevresinde böcek bariyer sistemleri kullanın",
            "Ekipmanları bitki aralarında dezenfekte edin",
        ],
        "prognosis_with_treatment": "Virüse karşı doğrudan tedavi yoktur; vektör kontrolü ile yeni enfeksiyon yavaşlatılabilir.",
        "prognosis_without_treatment": "Tüm bitkiler etkilenebilir, verim %50-80 düşer.",
        "harvest_impact": "Yüksek — meyve kalitesi ve miktarı ciddi şekilde düşer.",
        "next_season_prevention": "Virüse dayanıklı çeşit seçin. Sertifikalı fide/tohumluk kullanın.",
    },
    "Anthracnose": {
        "disease_name_tr": "Antraknoz",
        "disease_name_en": "Anthracnose",
        "description": "Yaprak, dal ve meyvelerde koyu çöküntülü lekeler oluşturan fungal hastalık. Islak ve sıcak havalarda hızla yayılır.",
        "pathogen_type": "fungal",
        "spread_speed": "fast",
        "affected_parts": ["Meyveler", "Yapraklar", "Dallar", "Çiçekler"],
        "risk_level": 3,
        "current_stage": "Aktif enfeksiyon",
        "spread_risk": "high",
        "estimated_timeline": "Yağmurlu havalarda 3-5 günde hızlı yayılma",
        "treatment_products": [
            TreatmentProduct(
                name="Mancozeb 80 WP",
                active_ingredient="Mankozeb (%80 WP)",
                dose="200 g / 100 L su",
                timing="Yağmur öncesi ve çiçeklenme döneminde",
                frequency="7-10 günde bir",
                price_range_tl="90-150 TL/kg",
            ),
            TreatmentProduct(
                name="Switch 62.5 WG",
                active_ingredient="Siprodinil + Fludioksonil",
                dose="80 g / 100 L su",
                timing="Hastalık başlangıcında veya çiçeklenme öncesi",
                frequency="10-14 günde bir, max 2 uygulama",
                price_range_tl="350-500 TL/250 g",
            ),
        ],
        "cultural_measures": [
            "Hasta meyve ve dalları toplayıp imha edin",
            "Hasattan önce meyveler üstüne su değdirmeyin",
            "Budama aletlerini her kullanım sonrası dezenfekte edin",
            "Çiçeklenme döneminde koruyucu fungisit uygulaması yapın",
        ],
        "prognosis_with_treatment": "Erken müdahale ile 14-21 gün içinde hastalık baskılanır; yeni meyveler sağlıklı gelişir.",
        "prognosis_without_treatment": "Tüm hasadı tehdit eder — meyveler satılamaz hale gelir.",
        "harvest_impact": "Çok yüksek etki — pazar değeri sıfıra düşebilir (%60-90 kayıp).",
        "next_season_prevention": "Dayanıklı çeşit seçin. Çiçeklenme öncesi bakır bazlı koruyucu uygulayın.",
    },
}


def _get_disease_enrichment(predicted_class: str) -> "DiseaseEnrichment | None":
    """Tahmin edilen sınıfa göre hastalık zenginleştirme verisini döndür."""
    data = DISEASE_ENRICHMENT_DB.get(predicted_class)
    if data is None:
        return None
    return DiseaseEnrichment(**data)


# Router tanımı — prefix /ai, tüm endpoint'ler bu prefix altında
router = APIRouter(
    prefix="/ai",
    tags=["AI Detection - Sprint 2"],
)


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyon: Model Yüklü mü Kontrol Et
# ---------------------------------------------------------------------------

def _require_models_loaded() -> None:
    """
    Model deposunun dolu olup olmadığını kontrol eder.
    Yüklü değilse 503 Service Unavailable döndürür.

    Raises:
        HTTPException(503): Modeller henüz yüklenmemişse.
    """
    if not model_store.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI modelleri henüz yüklenmedi. "
                "Uygulama başlangıcını bekleyin veya sunucu loglarını kontrol edin."
            ),
        )


# =============================================================================
# Endpoint 1: POST /ai/detect_leaf
# =============================================================================

@router.post(
    "/detect_leaf",
    response_model=LeafDetectionResponse,
    summary="Görselde yaprak tespit et (YOLOv8)",
    description=(
        "Yüklenen görselde YOLOv8 modeli çalıştırır. "
        "Yaprağın bounding box koordinatlarını ve kırpılmış yaprak görselini (base64) döndürür. "
        "**Sonraki adım:** Dönen `cropped_leaf_base64` değerini `/ai/classify_disease` endpoint'ine gönderin."
    ),
    responses={
        200: {"description": "Yaprak tespiti tamamlandı (yaprak bulunamasa bile 200 döner)."},
        400: {"model": AIErrorResponse, "description": "Geçersiz görsel formatı."},
        503: {"model": AIErrorResponse, "description": "AI modelleri yüklenmemiş."},
    }
)
async def detect_leaf_endpoint(
    file: UploadFile = File(
        ...,
        description="Analiz edilecek bitki görseli (JPG, PNG, WEBP). Maksimum 10MB önerilir."
    )
) -> LeafDetectionResponse:
    """
    **İşlem Akışı:**
    1. Yüklenen görsel okunur.
    2. Belleğe yüklenmiş YOLOv8 modeli çalıştırılır.
    3. En yüksek güvenli bounding box seçilir.
    4. Yaprak kırpılır ve base64 string'e dönüştürülür.
    5. Sonuçlar döndürülür.

    **Desteklenen Formatlar:** JPEG, PNG, WEBP, BMP
    """
    _require_models_loaded()

    # --- Dosyayı oku ---
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yüklenen dosya boş. Lütfen geçerli bir görsel gönderin."
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Dosya okuma hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dosya okunamadı: {exc}"
        )

    # --- YOLOv8 inference ---
    try:
        result = detect_leaf(
            image_bytes=image_bytes,
            yolo_model=model_store.yolo,
            confidence_threshold=0.25,
        )
    except ValueError as exc:
        # Görsel çözümleme hatası
        logger.warning(f"Görsel işleme hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        # Model inference hatası
        logger.error(f"YOLOv8 inference hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YOLOv8 çalıştırma hatası: {exc}"
        )

    # --- Yanıt oluştur ---
    leaf_detected = result["leaf_detected"]
    message = (
        "Yaprak başarıyla tespit edildi."
        if leaf_detected
        else "Görselde yaprak tespit edilemedi. Daha net bir fotoğraf deneyin."
    )

    return LeafDetectionResponse(
        success=True,
        leaf_detected=leaf_detected,
        bounding_box=_to_bounding_box(result["bounding_box"]),
        confidence=result["confidence"],
        cropped_leaf_base64=result["cropped_leaf_base64"],
        original_width=result["original_width"],
        original_height=result["original_height"],
        message=message,
    )


# =============================================================================
# Endpoint 2: POST /ai/classify_disease
# =============================================================================

@router.post(
    "/classify_disease",
    response_model=DiseaseClassificationResponse,
    summary="Yaprak görselinden hastalık sınıflandır (EfficientNet-B3)",
    description=(
        "Kırpılmış yaprak görselini (base64) EfficientNet-B3 modeline gönderir. "
        "Hastalık sınıfı adı ve güven skoru döndürür. "
        "**Önce** `/ai/detect_leaf` çağrısı yaparak `cropped_leaf_base64` elde edin."
    ),
    responses={
        200: {"description": "Sınıflandırma tamamlandı."},
        400: {"model": AIErrorResponse, "description": "Geçersiz girdi."},
        503: {"model": AIErrorResponse, "description": "AI modelleri yüklenmemiş."},
    }
)
async def classify_disease_endpoint(
    request: DiseaseClassificationRequest,
) -> DiseaseClassificationResponse:
    """
    **İşlem Akışı:**
    1. Base64 kırpılmış yaprak görseli okunur.
    2. ImageNet normalize işlemi uygulanır.
    3. EfficientNet-B3 modeli çalıştırılır.
    4. Softmax ile olasılıklar hesaplanır.
    5. En yüksek olasılıklı sınıf ve tüm skorlar döndürülür.
    """
    _require_models_loaded()

    try:
        result = classify_disease(
            cropped_leaf_base64=request.cropped_leaf_base64,
            efficientnet_model=model_store.efficientnet,
            class_names=model_store.class_names,
            device=model_store.device,
        )
    except ValueError as exc:
        logger.warning(f"EfficientNet giriş hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        logger.error(f"EfficientNet inference hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EfficientNet çalıştırma hatası: {exc}"
        )

    return DiseaseClassificationResponse(
        success=True,
        predicted_class=result["predicted_class"],
        predicted_class_index=result["predicted_class_index"],
        confidence=result["confidence"],
        all_scores=result["all_scores"],
        message=(
            f"'{result['predicted_class']}' hastalığı "
            f"%{result['confidence'] * 100:.1f} güven ile tespit edildi."
        ),
    )


# =============================================================================
# Endpoint 3: POST /ai/explain_prediction
# =============================================================================

@router.post(
    "/explain_prediction",
    response_model=GradCAMResponse,
    summary="Grad-CAM ısı haritası üret (Açıklanabilir AI)",
    description=(
        "Modelin hangi görsel bölgeye odaklandığını Grad-CAM algoritmasıyla görselleştirir. "
        "Hem renklendirilmiş ısı haritası hem de orijinal görsel üzerine bindirme döndürülür. "
        "**Önce** `/ai/detect_leaf` → `/ai/classify_disease` zinciri çalıştırılmalıdır."
    ),
    responses={
        200: {"description": "Grad-CAM görseli oluşturuldu."},
        400: {"model": AIErrorResponse, "description": "Geçersiz girdi."},
        503: {"model": AIErrorResponse, "description": "AI modelleri yüklenmemiş."},
    }
)
async def explain_prediction_endpoint(
    request: GradCAMRequest,
) -> GradCAMResponse:
    """
    **İşlem Akışı:**
    1. Kırpılmış yaprak görseli hazırlanır.
    2. GradCAMHook hedef katmana bağlanır.
    3. Forward pass + backward pass çalıştırılır.
    4. Aktivasyon ağırlıkları hesaplanır.
    5. Jet colormap ile ısı haritası renklendirilir.
    6. Orijinal görsel üzerine bindirme yapılır.
    """
    _require_models_loaded()

    try:
        result = generate_gradcam(
            cropped_leaf_base64=request.cropped_leaf_base64,
            efficientnet_model=model_store.efficientnet,
            target_layer=model_store.gradcam_target_layer,
            class_names=model_store.class_names,
            device=model_store.device,
            target_class_index=request.target_class_index,
        )
    except ValueError as exc:
        logger.warning(f"Grad-CAM giriş hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except RuntimeError as exc:
        logger.error(f"Grad-CAM hesaplama hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grad-CAM oluşturma hatası: {exc}"
        )

    return GradCAMResponse(
        success=True,
        heatmap_base64=result["heatmap_base64"],
        overlay_base64=result["overlay_base64"],
        target_class=result["target_class"],
        target_class_index=result["target_class_index"],
        message=(
            f"'{result['target_class']}' sınıfı için Grad-CAM oluşturuldu. "
            "Kırmızı bölgeler modelin odaklandığı alanları gösterir."
        ),
    )


# =============================================================================
# Endpoint 4: POST /ai/analyze  (Tam Pipeline — Kolaylık Endpoint'i)
# =============================================================================

@router.post(
    "/analyze",
    response_model=FullAnalysisResponse,
    summary="Tam AI analizi: YOLO → EfficientNet → Grad-CAM",
    description=(
        "Tek bir fotoğraf yükleyerek tüm AI pipeline'ını çalıştırır: "
        "**1)** YOLOv8 yaprak tespiti → "
        "**2)** EfficientNet-B3 hastalık sınıflandırma → "
        "**3)** Grad-CAM açıklanabilirlik haritası. "
        "Ara adımların çıktılarını ayrı ayrı göndermek yerine bu endpoint kullanılabilir."
    ),
    responses={
        200: {"description": "Tam analiz tamamlandı."},
        400: {"model": AIErrorResponse, "description": "Geçersiz görsel."},
        503: {"model": AIErrorResponse, "description": "AI modelleri yüklenmemiş."},
    }
)
async def analyze_endpoint(
    file: UploadFile = File(
        ...,
        description="Analiz edilecek bitki görseli (JPG, PNG, WEBP)."
    )
) -> FullAnalysisResponse:
    """
    **Tam İşlem Akışı:**

    ```
    [Kullanıcı fotoğraf yükler]
          ↓
    [YOLOv8 yaprağı bulur → bounding box + kırpılmış görsel]
          ↓
    [EfficientNet-B3 hastalığı tahmin eder → sınıf + güven]
          ↓
    [Grad-CAM açıklama haritası üretilir]
          ↓
    [Tüm sonuçlar tek yanıtta döndürülür]
    ```

    **Not:** Yaprak tespit edilemezse `disease_classification` ve `gradcam` alanları `null` olur.
    """
    _require_models_loaded()

    # --- Adım 1: Görseli oku ---
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yüklenen dosya boş."
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dosya okunamadı: {exc}"
        )

    # --- Adım 2: YOLOv8 Yaprak Tespiti ---
    try:
        yolo_result = detect_leaf(
            image_bytes=image_bytes,
            yolo_model=model_store.yolo,
            confidence_threshold=0.25,
        )
    except ValueError as exc:
        # Görsel çözümleme hatası — geçersiz dosya
        logger.warning(f"Analyze - geçersiz görsel: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        # Beklenmeyen hata — pipeline'ı kırmak yerine kısmi yanıt döndür
        logger.error(f"Analyze - YOLO hatası, kısmi yanıt dönülüyor: {exc}")
        return FullAnalysisResponse(
            success=False,
            leaf_detection=LeafDetectionResponse(
                success=False,
                leaf_detected=False,
                bounding_box=None,
                confidence=0.0,
                cropped_leaf_base64=None,
                original_width=0,
                original_height=0,
                message="Yaprak tespiti geçici olarak kullanılamıyor.",
            ),
            disease_classification=None,
            gradcam=None,
            message="Yaprak tespiti başarısız. Lütfen farklı bir görsel deneyin.",
        )

    leaf_response = LeafDetectionResponse(
        success=True,
        leaf_detected=yolo_result["leaf_detected"],
        bounding_box=_to_bounding_box(yolo_result["bounding_box"]),
        confidence=yolo_result["confidence"],
        cropped_leaf_base64=yolo_result["cropped_leaf_base64"],
        original_width=yolo_result["original_width"],
        original_height=yolo_result["original_height"],
        message=(
            "Yaprak tespit edildi."
            if yolo_result["leaf_detected"]
            else "Yaprak tespit edilemedi, tüm görsel analiz ediliyor."
        ),
    )

    # Service katmanı her zaman cropped_leaf_base64 döndürür (full-image fallback).
    # Yalnızca gerçekten None ise (beklenmez) pipeline'ı durdur.
    if yolo_result["cropped_leaf_base64"] is None:
        return FullAnalysisResponse(
            success=True,
            leaf_detection=leaf_response,
            disease_classification=None,
            gradcam=None,
            message="Görsel işlenemedi. Hastalık analizi yapılamadı.",
        )

    cropped_b64 = yolo_result["cropped_leaf_base64"]

    # --- Adım 3: EfficientNet Hastalık Sınıflandırma ---
    disease_response = None
    target_class_idx = None

    try:
        clf_result = classify_disease(
            cropped_leaf_base64=cropped_b64,
            efficientnet_model=model_store.efficientnet,
            class_names=model_store.class_names,
            device=model_store.device,
        )
        disease_response = DiseaseClassificationResponse(
            success=True,
            predicted_class=clf_result["predicted_class"],
            predicted_class_index=clf_result["predicted_class_index"],
            confidence=clf_result["confidence"],
            all_scores=clf_result["all_scores"],
            message=(
                f"'{clf_result['predicted_class']}' hastalığı "
                f"%{clf_result['confidence'] * 100:.1f} güven ile tespit edildi."
            ),
        )
        target_class_idx = clf_result["predicted_class_index"]

    except Exception as exc:
        # Sınıflandırma başarısız olsa bile Grad-CAM'i tamamen atlamak yerine
        # partially başarılı yanıt döndür.
        logger.error(f"Analyze - EfficientNet hatası: {exc}")

    # --- Adım 4: Grad-CAM Açıklanabilirlik ---
    gradcam_response = None

    if target_class_idx is not None:
        try:
            gcam_result = generate_gradcam(
                cropped_leaf_base64=cropped_b64,
                efficientnet_model=model_store.efficientnet,
                target_layer=model_store.gradcam_target_layer,
                class_names=model_store.class_names,
                device=model_store.device,
                target_class_index=target_class_idx,
            )
            gradcam_response = GradCAMResponse(
                success=True,
                heatmap_base64=gcam_result["heatmap_base64"],
                overlay_base64=gcam_result["overlay_base64"],
                target_class=gcam_result["target_class"],
                target_class_index=gcam_result["target_class_index"],
                message=(
                    f"'{gcam_result['target_class']}' için Grad-CAM oluşturuldu."
                ),
            )
        except Exception as exc:
            logger.error(f"Analyze - Grad-CAM hatası: {exc}")
            # Grad-CAM başarısız olsa bile diğer sonuçları döndür

    # --- Adım 5: Hastalık Zenginleştirme ---
    enrichment = None
    if disease_response is not None:
        enrichment = _get_disease_enrichment(disease_response.predicted_class)

    # --- Adım 6: Birleşik Yanıt ---
    final_message = "Tam AI analizi tamamlandı."
    if disease_response is None:
        final_message = "Yaprak tespit edildi fakat hastalık sınıflandırması başarısız oldu."
    elif gradcam_response is None:
        final_message = "Yaprak ve hastalık tespit edildi fakat Grad-CAM oluşturulamadı."

    return FullAnalysisResponse(
        success=True,
        leaf_detection=leaf_response,
        disease_classification=disease_response,
        gradcam=gradcam_response,
        disease_enrichment=enrichment,
        message=final_message,
    )
# =============================================================================
# Sistem Prompt — Zirai Asistan Kişiliği
#
AGRI_SYSTEM_PROMPT = (
    "Sen Türkiye'nin deneyimli bir ziraat mühendisisin. "
    "25 yıl Ege ve Güneydoğu Anadolu'da çalıştın. "
    "Soruyu oku, direkt cevap ver. "
    "Somut ol: ilaç adı, doz, zamanlama yaz. "
    "Türkiye'de bulunabilen ürünleri öner. "
    "Maksimum 3 paragraf, sade dil. "
    "Robotik başlık kullanma."
)


# =============================================================================
# Endpoint 5: POST /ai/chat
# =============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Zirai Yapay Zeka Asistanı ile sohbet et",
    description=(
        "Kullanıcının bitki sağlığı, tarım ve bakım hakkındaki sorularını yanıtlar. "
        "OpenAI GPT-4o-mini modeli ile konuşma geçmişini dikkate alarak cevaplar verir."
    )
)
async def ai_chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Zirai asistan — OpenAI GPT-4o-mini ile gerçek LLM cevabı üretir."""
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API anahtarı yapılandırılmamış. .env dosyasına OPENAI_API_KEY ekleyin.",
        )

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history
    ]
    messages = [
        {"role": "system", "content": AGRI_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": request.message},
    ]

    async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        result = await asyncio.wait_for(
            async_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=800,
                messages=messages,
            ),
            timeout=25.0,
        )
        response_text = result.choices[0].message.content
    except asyncio.TimeoutError:
        logger.warning("OpenAI API 25 saniye içinde yanıt vermedi.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Şu an yoğunluk var, tekrar dener misiniz?",
        )
    except openai.AuthenticationError:
        logger.error("OpenAI API kimlik doğrulama hatası — geçersiz API anahtarı.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API anahtarı geçersiz.",
        )
    except openai.RateLimitError:
        logger.warning("OpenAI API hız limiti aşıldı.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Şu an yoğunluk var, tekrar dener misiniz?",
        )
    except Exception as exc:
        logger.error(f"OpenAI API hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI servisi geçici olarak kullanılamıyor.",
        )

    return ChatResponse(
        success=True,
        response=response_text,
        message="AI asistanı yanıtı başarıyla oluşturdu.",
    )
