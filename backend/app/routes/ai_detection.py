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

import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

# AI servis fonksiyonları
from app.services.leaf_detection_service import detect_leaf
from app.services.disease_classification_service import (
    classify_disease,
    generate_gradcam,
)

# Merkezi model deposu (lifespan'de doldurulur)
from app.core.model_manager import model_store

# Pydantic yanıt şemaları
from app.schemas.ai_schemas import (
    AIErrorResponse,
    BoundingBox,
    ChatRequest,
    ChatResponse,
    DiseaseClassificationRequest,
    DiseaseClassificationResponse,
    FullAnalysisResponse,
    GradCAMRequest,
    GradCAMResponse,
    LeafDetectionResponse,
)

logger = logging.getLogger(__name__)


def _to_bounding_box(bb) -> "BoundingBox | None":
    """Convert [x1,y1,x2,y2] list from service layer to Pydantic BoundingBox."""
    if bb is None:
        return None
    return BoundingBox(x1=int(bb[0]), y1=int(bb[1]), x2=int(bb[2]), y2=int(bb[3]))


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

    # --- Adım 5: Birleşik Yanıt ---
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
        message=final_message,
    )
# =============================================================================
# Sistem Prompt — Zirai Asistan Kişiliği
#
# Bu prompt, asistanın nasıl yanıt vereceğini tanımlar.
# İleride bir LLM (Gemini/Claude/OpenAI) entegrasyonunda doğrudan system
# message olarak kullanılacaktır. Şu an kural tabanlı motorda referans alınır.
# =============================================================================

AGRI_SYSTEM_PROMPT = """
Sen deneyimli bir Türk ziraat mühendisisin. 20 yıllık saha deneyimin var.
Kullanıcılara her zaman:
- Önce sorunun kök nedenini açıkla
- Sonra adım adım çözüm yolu sun
- Hangi ürünleri/ilaçları kullanacağını, dozajını ve uygulama zamanını belirt
- Hava/mevsim koşullarına göre özel uyarı ekle
- Cevabın sonunda bir önleyici bakım önerisi ver
Cevapların en az 3-4 paragraf olsun. Teknik terimleri kullan ama hemen Türkçe açıklamasını da yaz.
Kullanıcının yetiştirdiği ürüne ve bölgesine özel cevap ver.
"""


# =============================================================================
# Endpoint 5: POST /ai/chat
# =============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Zirai Yapay Zeka Asistanı ile sohbet et",
    description=(
        "Kullanıcının bitki sağlığı, tarım ve bakım hakkındaki sorularını yanıtlar. "
        "Deneyimli bir Türk ziraat mühendisi kimliğiyle, 3-4 paragraf detaylı yanıtlar verir."
    )
)
async def ai_chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Zirai asistan — AGRI_SYSTEM_PROMPT kurallarını izleyen kural tabanlı motor.
    Her yanıt: kök neden → çözüm adımları → ilaç/dozaj → hava uyarısı → önleyici bakım.
    """
    msg = request.message.lower()

    import random

    if any(k in msg for k in ["külleme", "mildew", "beyaz leke", "beyaz toz"]):
        response = (
            "**Kök Neden:** Külleme (Powdery Mildew — Erysiphe spp.), yüksek nem (%60-80) ile "
            "günlük sıcaklık dalgalanmalarının bir arada bulunduğu koşullarda hızla yayılır. "
            "Toprak nemi fazla olduğunda ancak yaprak yüzeyi kuru kaldığında mantar sporları "
            "yaprak epidermisine kolayca tutunur ve beyaz pudra görünümünü oluşturur.\n\n"
            "**Çözüm Adımları:**\n"
            "1. Belirtili yaprakları hemen uzaklaştırın ve imha edin (kompost yapmayın).\n"
            "2. %0,2 konsantrasyonunda kükürt bazlı fungisit (örn. Kumulus DF veya Thiovit Jet) hazırlayın.\n"
            "3. Sabah erken (07:00-09:00) veya akşam (18:00-20:00) uygulayın; güneş altında kükürt yaprak yakar.\n"
            "4. 10-14 gün arayla en az 2-3 uygulama yapın.\n\n"
            "**Hava Durumu Uyarısı:** Sıcaklık 30°C'yi aştığında kükürt uygulaması yaprak yanığına "
            "yol açabilir; bu durumda trifloksistrobin veya azoksistrobin etken maddeli fungisitlere "
            "geçin (örn. Amistar 250 SC, doz: 0,8 L/da). Yağmur beklenen günlerde ilaçlamayı erteleyip "
            "sistematik (içten etkili) fungisit tercih edin.\n\n"
            "**Önleyici Bakım:** Bitkiler arası mesafeyi koruyun, hava sirkülasyonunu artırın. "
            "Sezon başında bakır oksiklorür (%50 WP, 3 g/L) ile koruyucu ilaçlama yapın. "
            "Dayanıklı çeşit kullanımı uzun vadede en etkili önlemdir."
        )
    elif any(k in msg for k in ["pas", "rust", "turuncu leke", "pas lekesi"]):
        response = (
            "**Kök Neden:** Pas hastalığı (Rust — Puccinia spp.) yüksek nem (%80+) ve serin geceler "
            "(10-20°C) ile sıcak gündüzlerin birleştiği koşullarda patlak verir. Sporlar rüzgar ve "
            "yağmur sıçramasıyla yayılır; yaprak altında turuncu-kahverengi toz benzeri pustüller "
            "(spor yatakları) oluşturur. Azot fazlası da bitkiyi duyarlı hale getirir.\n\n"
            "**Çözüm Adımları:**\n"
            "1. Hastalıklı yaprakları kesip imha edin; kesmek için dezenfekteli alet kullanın.\n"
            "2. Bordo bulamacı (%1 — 10 g göztaşı + 10 g kireç / 1 L su) hazırlayın ve uygulayın.\n"
            "3. Alternatif: Propikonazol etken maddeli fungisit (Tilt 250 EC, 0,5 ml/L, 7 günde bir).\n"
            "4. Üst ve alt yaprak yüzeylerini dikkatlice kaplayan spreyleme yapın.\n\n"
            "**Hava Durumu Uyarısı:** Yağmurlu ve rüzgarlı havada ilaçlama etkisiz kalır; "
            "48 saat kuru hava beklenen bir pencere seçin. İlkbaharda geceleri sıcaklık 10°C'nin "
            "altına iniyorsa bitkileri sera örtüsüyle koruyun.\n\n"
            "**Önleyici Bakım:** Gübreleme dengesine dikkat edin — aşırı azot pas duyarlılığını artırır. "
            "Sezon sonunda yere dökülen yaprakları tarla içinde bırakmayın; sporlar kışı toprakta geçirir. "
            "Çeşit seçiminde pas dayanıklılığı skoru yüksek tohumları tercih edin."
        )
    elif any(k in msg for k in ["sulama", "su ihtiyacı", "ne kadar su", "ne zaman sula"]):
        response = (
            "**Kök Neden:** Sulama hatası, hem su stresi (yetersiz sulama) hem de kök çürüklüğü "
            "(aşırı sulama) olarak iki farklı sorun doğurur. Toprağın türü belirleyicidir: killi toprak "
            "suyu uzun süre tutar ve kök boğulmasına yol açabilirken, kumlu toprak hızla kurur.\n\n"
            "**Doğru Sulama Yöntemi:**\n"
            "1. Sulama zamanı: Sabah erken (06:00-08:00) en iyisidir — yapraklar akşama kadar kurur, mantar riski azalır.\n"
            "2. Parmak testi: Toprağa 5 cm bastırın; ıslak his varsa bir gün bekleyin.\n"
            "3. Sebzeler için genel kural: Haftada 2-3 kez, her seferinde toprak 30 cm derinliğe ıslanacak şekilde.\n"
            "4. Damla sulama sistemleri su tüketimini %40 azaltır ve yaprakları kuru tutar.\n\n"
            "**Mevsim Uyarısı:** Yaz aylarında günlük buharlaşma artar; sıcak dönemlerde sulama "
            "sıklığını artırıp miktarı değiştirmeyin. Mulç (saman/örtü) uygulaması toprak nemini "
            "%25-30 oranında muhafaza eder. Don riski olan gecelerde sulama yapıp toprağı nemli bırakmak "
            "küçük çaplı don zararını azaltabilir (su donduğunda ısı açığa çıkar).\n\n"
            "**Önleyici Bakım:** Damla sulama borusu ucuna filtre takın — tıkanma sulama düzensizliğinin "
            "başlıca nedenidir. Toprak nem sensörü (ucuz Arduino tabanlı) kurarak dijital takip yapabilirsiniz."
        )
    elif any(k in msg for k in ["gübre", "besin eksikliği", "npk", "azot", "fosfor", "potasyum"]):
        response = (
            "**Kök Neden:** Bitki besin eksiklikleri üç temel nedenden kaynaklanır: toprağın pH'ı "
            "yanlış aralıkta olduğunda (6.0-7.0 dışı) bitkiler besinleri emse bile alamaz; sulama fazlalığı "
            "besinleri yıkar (leaching); organik madde azlığı toprak canlılığını düşürür.\n\n"
            "**Gelişim Evresine Göre Gübreleme:**\n"
            "1. Fide/vegetatif dönem: Azot (N) ağırlıklı gübre — 20-10-10 formülasyon, 14 günde bir.\n"
            "2. Çiçeklenme dönemi: Fosfor (P) ağırlıklı — 10-30-10; fosfor çiçek ve meyve bağlamayı tetikler.\n"
            "3. Meyve dolum: Potasyum (K) ağırlıklı — 5-10-40; meyve kalitesini, şeker oranını artırır.\n"
            "4. Uygulama dozu: Kural olarak 1-2 kg NPK / 100 m² (toprak testi sonuçlarına göre ayarlayın).\n\n"
            "**Eksiklik Belirtileri ve Hızlı Müdahale:**\n"
            "- Sarı yapraklar + zayıf büyüme → Azot eksikliği → üre (%46 N) 1 g/L yaprak gübresi.\n"
            "- Mor/kırmızı renklenme → Fosfor eksikliği → mono potasyum fosfat, 2 g/L.\n"
            "- Yaprak kenarı yanması → Potasyum eksikliği → potasyum nitrat, 3 g/L.\n\n"
            "**Önleyici Bakım:** Güz ayında yanmış ahır gübresi veya kompost (3-5 ton/da) "
            "toprağa karıştırın. İlkbaharda 'slow release' (yavaş salınımlı) gübre kullanmak "
            "tüm sezon boyunca dengeli beslenme sağlar ve yıkanma kaybını minimuma indirir."
        )
    elif any(k in msg for k in ["domates", "tomato", "domates hastalığı"]):
        response = (
            "**Kök Neden:** Domateste en sık görülen sorunlar şunlardır: Erken yanıklık "
            "(Alternaria solani — yaprak lekesi), Geç yanıklık (Phytophthora infestans — kahverengi çürüme) "
            "ve Septoria yaprak lekesi. Bu hastalıkların tümü serin-nemli koşullarda (15-22°C, nem >80%) "
            "yayılır. Aşırı sık dikim ve yetersiz budama risk faktörleridir.\n\n"
            "**Önce Teşhis, Sonra Tedavi:**\n"
            "1. Alt yapraklarda sarı halkalı koyu lekeler → Erken yanıklık → Mankozeb 80 WP, 2.5 g/L, 7 günde bir.\n"
            "2. Kahverengi yağ lekesi, beyaz küf → Geç yanıklık → Metalaxyl-M (Ridomil Gold), 2.5 g/L, acil uygulama.\n"
            "3. Küçük koyu noktalı sarı lekeler → Septoria → Bakır oksiklorür %50, 3 g/L.\n"
            "4. Tüm uygulamalarda 7-10 gün arayla 2-3 tur uygulama yapın.\n\n"
            "**Hava Uyarısı:** Yağmur öncesi sistematik fungisit, yağmur sonrası koruyucu bakır bileşiği "
            "mantığını izleyin. Sıcaklık 28°C'yi aşınca bakır bileşikleri fitotoksik olabilir; güneşsiz "
            "saatlerde uygulayın. Akdeniz bölgesinde Temmuz-Ağustos'ta Fusarium solgunluğuna da dikkat edin.\n\n"
            "**Önleyici Bakım:** Ekim nöbeti uygulayın — aynı tarlaya 3 yıldan önce domates ekmemeye "
            "çalışın. Alt yaprakları budayarak hava sirkülasyonunu artırın ve sulama suyunu toprağa "
            "verin, yapraklara değil. Hasat öncesi son ilaçlamadan en az 7 gün bekleyin."
        )
    elif any(k in msg for k in ["biber", "pepper", "patlıcan", "aubergine", "biberim", "patlıcanım"]):
        response = (
            "**Kök Neden:** Biber ve patlıcan tropik kökenlidir; 15°C'nin altında büyüme durur "
            "ve soğuk stresi bağışıklık sistemini zayıflatır. En yaygın sorunlar: Kök çürüklüğü "
            "(Phytophthora capsici), Solgunluk (Fusarium), Yaprak biti (Aphis gossypii) ve "
            "Kırmızı örümcek akarı (Tetranychus urticae) — son ikisi sıcak ve kuru havalarda patlak verir.\n\n"
            "**Soruna Göre Müdahale:**\n"
            "1. Solgunluk + gövde dibinde çürüme → Phytophthora → Fosetil-Al (Aliette 80 WP, 3 g/L sulama).\n"
            "2. Yaprak biti → Yaprak altında yeşil/siyah koloniler → Imidacloprid (Confidor 200 SL, 0.5 ml/L) veya neem yağı (%2).\n"
            "3. Kırmızı örümcek → İnce ağ, soluk yapraklar → Abamektin (Vertimec 1.8 EC, 1 ml/L).\n"
            "4. Genel koruyucu → 15 günde bir bakır hidroksit (Kocide 2000, 2 g/L).\n\n"
            "**Hava Uyarısı:** Haziran-Ağustos döneminde sıcaklık 38°C'yi aşınca gölgeleme yapın; "
            "çiçek dökülmesi yaşanır. Akşam saatlerinde hafif yağmurlama (misting) biber için "
            "çok faydalıdır ama sera dışında kırmızı örümcek baskısında sulama yaprağa değmemeli.\n\n"
            "**Önleyici Bakım:** Fide dikiminden 2 hafta önce toprağa Trichoderma harzianum bazlı "
            "biyofungisit karıştırın; bu toprak kökenli hastalıklara karşı doğal koruma sağlar. "
            "Yüksek tünel veya sera yetiştiriciliğinde nem ve sıcaklık takibi için dijital sensör kullanın."
        )
    elif any(k in msg for k in ["patates", "potato", "patatesim"]):
        response = (
            "**Kök Neden:** Patateste en tehlikeli hastalık geç yanıklıktır (Phytophthora infestans — "
            "İrlanda kıtlığının nedeni). Serin (10-20°C) ve nemli (%90+) koşullarda tek gecede "
            "bir tarlayı çökertebilir. Bunun yanı sıra Alternarya erken yanıklığı, "
            "Rhizoctonia kök çürüklüğü ve Colorado böceği de önemli tehditlerdir.\n\n"
            "**Acil Müdahale Protokolü:**\n"
            "1. Yapraklarda kahverengi yağlı lekeler + beyaz küf → DERHAL Metalaxyl-M (Ridomil Gold MZ, 2.5 g/L).\n"
            "2. Koruyucu uygulama: Propineb (Antracol 70 WP, 2 g/L) haftada bir yağmurlu dönemde.\n"
            "3. Colorado böceği: İmidacloprid (Confidor, 0.5 ml/L) veya spinosad (Tracer, biyolojik).\n"
            "4. Yumru oluşum döneminde eşit sulama kritiktir — ani kuraklık+yağmur içi boş yumruya neden olur.\n\n"
            "**Hava Uyarısı:** Geç yanıklık için Blight Advisory hesaplaması yapın: "
            "2 gün üst üste nem>90% ve sıcaklık 10-20°C ise ilaçlamayı erteleyin, aynı gün yapın. "
            "İlaçlamadan sonra en az 4 saat kuru hava gerekir; aksi halde etki azalır.\n\n"
            "**Önleyici Bakım:** Hasattan sonra yumru artıklarını mutlaka topraktan çıkarın. "
            "Sertifikalı, hastalıksız tohum yumru kullanın. 4 yıl ekim nöbeti uygulayın ve "
            "çiçeklenme öncesi son önleyici bakır ilaçlamasını yapmayı unutmayın."
        )
    elif any(k in msg for k in ["buğday", "arpa", "çavdar", "tahıl"]):
        response = (
            "**Kök Neden:** Tahıllarda (buğday, arpa, çavdar) başlıca sorunlar sarı pas "
            "(Puccinia striiformis), kahverengi pas, külleme ve septoryoz'dur. Bu hastalıkların tümü "
            "soğuk-nemli bahar koşullarını sever. Aşırı azot gübrelemesi bitkiyi duyarlı hale getirir "
            "ve pas ile külleme görülme sıklığını artırır.\n\n"
            "**Fungisit Programı:**\n"
            "1. Sapa kalkma dönemi (Z30-32): Triazol grubu fungisit — propikonazol veya epoksikonazol, 0.5 L/da.\n"
            "2. Başaklanma öncesi (Z39-49): Strobilurin + triazol karışımı (örn. Amistar Xtra, 0.8 L/da).\n"
            "3. Külleme varsa kükürt bazlı ek uygulama yapın.\n"
            "4. Hava sıcaklığı 25°C üzerinde ise triazol etkinliği azalır; strobilurin ağırlıklı seçin.\n\n"
            "**Hava Uyarısı:** Mart-Nisan'da 3 gün üst üste yağmur + nem>80% geliyorsa ilaçlamayı "
            "öne çekin. Başak dönemi ilaçlaması don riskiyle çakışmamalı — don stresi bitkiyi zaten "
            "strese sokarken bir de kimyasal yük bindirmek zararı artırır.\n\n"
            "**Önleyici Bakım:** Tohum seçimi en kritik adımdır — bölgenize uygun dayanıklı çeşit "
            "kullanın (Tarla Bitkileri Merkez Araştırma Enstitüsü çeşit listesi). "
            "Ekim zamanını bölge normlarına göre ayarlayın; erken ekim pas ve külleme riskini artırır."
        )
    elif any(k in msg for k in ["üzüm", "bağ", "asma", "şarap"]):
        response = (
            "**Kök Neden:** Asma yetiştiriciliğindeki iki büyük tehdit mildiyö (Plasmopara viticola) ve "
            "oidium'dur (külleme, Uncinula necator). Mildiyö yağışlı ve serin havalarda, oidium ise "
            "sıcak ve kuru havalarda baskın gelir. Üzüm için 10 yaprak döneminden başlayan koruyucu "
            "ilaçlama programı kritiktir; geç kalınırsa mücadele çok zorlaşır.\n\n"
            "**İlaçlama Programı (Fenolojik Döneme Göre):**\n"
            "1. 3-5 yaprak (Nisan): Bakır oksiklorür (%50 WP, 4 g/L) — mildiyöye karşı ilk koruma.\n"
            "2. Salkım görünüm (Mayıs): Fosetil-Al + bakır karışımı + kükürt (oidium için).\n"
            "3. Çiçeklenme öncesi: Mancozeb 80 WP (2.5 g/L) — kritik dönem.\n"
            "4. Ben düşme sonrası: Sistematik fungisit (metalaxyl içerikli); dozaj etiket talimatına göre.\n\n"
            "**Hava Uyarısı:** 10 mm üzeri yağıştan sonra 24-48 saat içinde koruyucu "
            "bakır ilaçlaması yapın. Yaz ortasında (Temmuz-Ağustos) oidium baskısı artar; "
            "bu dönemde kükürt yerine DMI grubu (myclobutanil) tercih edin çünkü yüksek sıcaklıkta "
            "kükürt yanık yapabilir.\n\n"
            "**Önleyici Bakım:** Kış budamasında hasta dalları çıkarın ve yakın. "
            "Salkım bölgesini yaprak alma ile havalandırın — iç kısımda kalan nem mildiyöyü besler. "
            "Toprak örtüsü (otlar) nem dengesini korur; tamamen çıplak toprak bırakmayın."
        )
    elif any(k in msg for k in ["zeytin", "zeytin ağacı", "zeytinlik"]):
        response = (
            "**Kök Neden:** Zeytinde en ciddi sorunlar zeytin sineği (Bactrocera oleae) ve "
            "halkalı leke (Cycloconium oleaginum — zeytin yaprak lekesi) hastalığıdır. "
            "Zeytin sineği yoğun sıcak gecelerde (20°C+) meyvede yumurtlar; "
            "halkalı leke ise sonbahardaki yağışlarda patlak verir.\n\n"
            "**Müdahale Stratejisi:**\n"
            "1. Zeytin sineği → Temmuz-Ekim izleme tuzakları kurun (feromonlu). Eşik aşılınca "
            "spinosad (Succès Bait, bait uygulaması) veya dimethoate (Rogor 40 EC, 1 ml/L — hasat öncesi 28 gün).\n"
            "2. Halkalı leke → Sonbahar yağışları öncesi bakır oksiklorür (%50, 3 g/L) uygulayın.\n"
            "3. Ağaç kovukları ve kuru dalları temizleyin — kışlama yuvaları yok edin.\n\n"
            "**Hava Uyarısı:** Dimethoate gibi organofosfatlı ilaçlar yüksek sıcaklıkta "
            "hızla buharlaşır; sabah erken veya akşam üzeri uygulayın. Zeytin sineği baskısı "
            "özellikle kıyı bölgelerinde Ağustos-Eylül döneminde zirveye çıkar.\n\n"
            "**Önleyici Bakım:** Her yıl budama yapın; sık dallı ağaçlarda sinek yumurtlama riski "
            "daha yüksektir. Yere dökülen zeytinleri derhal toplayın — zeytin sineği pupası "
            "toprakta kışlar. Organik yetiştiricilikte kaolin kili (Surround WP) meyveye "
            "beyaz katman yaparak sinek yumurtlamasını fiziksel olarak engeller."
        )
    elif any(k in msg for k in ["sarı", "sararma", "sararmış", "yaprak sarı", "yellow"]):
        response = (
            "**Kök Neden:** Yaprak sararması (kloroz) birden fazla nedenden kaynaklanır ve "
            "doğru teşhis yapılmazsa yanlış müdahale sorunu büyütür. Başlıca nedenler: "
            "Azot (N) eksikliği, demir (Fe) eksikliği (alkali topraklarda), aşırı sulama → "
            "kök çürüklüğü, viral enfeksiyon (mozaik virüs) ve kırmızı örümcek zararı.\n\n"
            "**Renk Örüntüsüne Göre Teşhis:**\n"
            "1. Alt yapraklar önce sararıyor → Azot eksikliği → Üre %46, 1-2 g/L yaprak gübresi.\n"
            "2. Genç yapraklar sarı, damarlar yeşil → Demir klorozu → Şelatlı demir (Fe-EDTA, 2 g/L).\n"
            "3. Yapraklar arası sarı, damarlar yeşil → Magnezyum eksikliği → MgSO4 (Epsom tuzu), 5 g/L.\n"
            "4. Tüm bitki solar gibi sararıyor → Kök çürüklüğü şüphesi → Fosetil-Al sulama.\n\n"
            "**Hava Uyarısı:** İlkbahar geçiş döneminde gece-gündüz sıcaklık farkı büyük olduğunda "
            "demir alımı güçleşir; toprak sıcaklığı 15°C altında besin emilimi yavaşlar. "
            "Soğuk dönemde yaprak gübre uygulaması sabah güneşli saatlerde yapılmalı.\n\n"
            "**Önleyici Bakım:** Toprak pH'ını yılda bir ölçün (çiftçi marketlerinde basit "
            "test kiti bulunur). pH 7.0'ı geçiyorsa kükürt uygulayarak düşürün. "
            "Organik madde arttıkça demir ve mikro-element mevcudiyeti doğal olarak iyileşir."
        )
    elif any(k in msg for k in ["kuru", "kuruma", "solar", "solma", "solgun", "yaprak döküyor"]):
        response = (
            "**Kök Neden:** Yaprak solması ve kuruma üç farklı mekanizma ile gerçekleşir: "
            "Su stresi (köklerin su alamadığı durum), vasküler tıkanma (Fusarium, Verticillium "
            "gibi iletim doku hastalıkları) veya aşırı sulama kaynaklı kök çürüklüğü. "
            "Paradoks gibi görünse de hem su eksikliği hem fazlalığı aynı solgunluk belirtisini verebilir.\n\n"
            "**Teşhis ve Müdahale:**\n"
            "1. Toprağa 10 cm gidin: Nemli ama bitki hâlâ solgunsa → Kök çürüklüğü (Phytophthora/Pythium).\n"
            "   Müdahale: Fosetil-Al (Aliette 80 WP, 3 g/L, sulama yoluyla) + drenaj iyileştirin.\n"
            "2. Gövde kesitini inceleyin: Kahverengi vasküler doku varsa → Fusarium veya Verticillium.\n"
            "   Müdahale: Toprağa Trichoderma biyofungisit karıştırın; kimyasal çözüm sınırlıdır.\n"
            "3. Toprak kuru ve bitki solgunsa → Su stresi → Derin sulama yapın, toprağa mulç serin.\n\n"
            "**Hava Uyarısı:** Yaz sıcağında (35°C+) öğleden sonra stomaların kapanması "
            "normal fizyolojik solgunluktur — akşam serinlediğinde bitki toparlanıyorsa ciddi sorun yoktur. "
            "Akşamüstü de toparlanma olmuyorsa müdahale gereklidir.\n\n"
            "**Önleyici Bakım:** Drene olmayan, su tutan tarlalarda yükseltilmiş yatak (raised bed) "
            "yöntemi kök hastalıklarını dramatik şekilde azaltır. Damlama sulama + nem sensörü en "
            "etkili uzun vadeli çözümdür."
        )
    elif any(k in msg for k in ["mantar", "fungus", "küf", "çürük", "leke"]):
        response = (
            "**Kök Neden:** Mantari hastalıklar yüksek nem (%80+), sıcaklık dalgalanmaları ve "
            "yetersiz hava sirkülasyonu ile hızla yayılır. Bitki artıkları ve toprağın yüzey katmanı "
            "sporların kışlama yeridir; bir sezon görülen mantar hastalığı sonraki yıl da tekrarlama "
            "eğilimindedir.\n\n"
            "**Genel Fungisit Protokolü:**\n"
            "1. Koruyucu (kontakt): Bakır oksiklorür %50 WP (3 g/L) veya Mankozeb 80 WP (2.5 g/L), 10-14 günde bir.\n"
            "2. Tedavi edici (sistemik): Triazol grubu (tebukonazol, propikonazol, epoksikonazol) — hastalık ortaya çıktıktan sonra.\n"
            "3. Strobilurin grubu (azoksistrobin, kresoksim-metil) — hem koruyucu hem tedavi edici.\n"
            "4. Direnç yönetimi: Aynı etken maddeyi ardarda en fazla 2-3 kez kullanın, sonra değiştirin.\n\n"
            "**Hava Uyarısı:** Sabah çiyi çok olan dönemlerde (nem>90%) uygulama sıklığını artırın. "
            "Güneşli öğle vakti özellikle bakır bileşiklerini uygulamayın — fitotoksisite riski vardır. "
            "Yağmur tahmininde sistematik fungisit, kuru havalarda kontakt fungisit tercih edin.\n\n"
            "**Önleyici Bakım:** Hasat sonrası tüm bitki artıklarını yakın veya derin gömün. "
            "Sezon başı toprağa iyice yanmış ahır gübresi karıştırmak mikrobiyal çeşitlilik sağlar "
            "ve doğal baskı mekanizmalarını aktive eder."
        )
    elif any(k in msg for k in ["ilaç", "ilaçlama", "sprey", "fungisit", "pestisit", "zirai mücadele", "doz", "dozaj"]):
        response = (
            "**Kök Neden ve Temel İlkeler:** İlaçlama, en son başvurulması gereken araçtır; "
            "kültürel önlemler (budama, ekim nöbeti, dayanıklı çeşit) her zaman önce gelir. "
            "Yanlış ilaçlama hem etkisizdir hem de ilaç direnci gelişimine yol açar.\n\n"
            "**Doğru İlaçlama Protokolü:**\n"
            "1. Teşhis önce gelir: Hangi hastalık/zararlı? Görsel veya laborant analizi yapın.\n"
            "2. Etken madde seçimi: Hastalığa spesifik; geniş spektrumlu kullanımı sınırlayın.\n"
            "3. Doz hesabı: Etiket dozu aşmayın (tolerans oluşur); yetersiz doz da etkisiz kalır.\n"
            "4. Uygulama zamanı: Sabah 06:00-09:00 veya akşam 17:00-20:00 — hem bitki hem insan için güvenli.\n"
            "5. Spreyi her iki yüzeyden uygulayın: Yaprak altlarını atlamak etkinliği %50 düşürür.\n\n"
            "**Hava Uyarısı:** Rüzgar > 3 m/s, sıcaklık > 30°C, yağmur beklentisi 4 saaten kısa "
            "olan günlerde ilaçlama yapmayın. Yağmur hemen sonrası temas fungisitini yenileyin (%50 "
            "yıkanma olur), sistematik fungisit daha dirençlidir (48 saat sonra yağmur olsa bile çalışır).\n\n"
            "**Önleyici Bakım:** İlaç direnç yönetimi için 'FRAC kodu' farklı ilaçları dönüşümlü "
            "kullanın. Hasat öncesi 'pre-harvest interval' (PHI) süresine kesinlikle uyun; "
            "bu hem yasal zorunluluk hem de gıda güvenliği açısından kritiktir."
        )
    elif any(k in msg for k in ["sıcaklık", "hava durumu", "iklim", "don", "soğuk", "sıcak", "kuraklık", "yağmur"]):
        response = (
            "**Kök Neden:** Hava koşulları bitki fizyolojisini doğrudan belirler. Bitkilerin "
            "her gelişim aşaması için farklı sıcaklık optimumları vardır; bu aralığın dışına çıkıldığında "
            "büyüme yavaşlar, hastalık direnci düşer ve verim kayıpları başlar.\n\n"
            "**Kritik Sıcaklık Eşikleri ve Müdahale:**\n"
            "1. Don riski (< 2°C gece): Hassas sebzeleri %30-50 agro-tekstil tülle örtün; "
            "sulama yapın (don öncesi nemli toprak ısıyı tutar). Kalsiyum nitrat yaprak gübresi don direncini artırır.\n"
            "2. Yüksek sıcaklık (> 35°C): Sabah sulayın, gölgeleme (%30-50 şadör) uygulayın, "
            "çiçeklenme döneminde serin saatlerde tozlaşma gerçekleşmez — verim düşer.\n"
            "3. Kuraklık: Mulç (saman, plastik) toprağa yayın — buharlaşmayı %30 azaltır. "
            "Damla sulama geçiş yapın.\n"
            "4. Aşırı yağış: Drenaj kanallarını temizleyin; su basan tarla kök çürüklüğüne davetiye çıkarır.\n\n"
            "**Mevsimsel Uyarı:** İlkbahar geçişinde geç don ('çiçek donu') çok tehlikelidir — "
            "Nisan-Mayıs aylarında gece tahminlerini takip edin. Ege ve Akdeniz'de olgunlaşma dönemindeki "
            "yüksek sıcaklık+ düşük nem kombinasyonu meyve yanıklığına yol açar; bu dönemde "
            "sulama programını gözden geçirin.\n\n"
            "**Önleyici Bakım:** Bitki su stres toleransını artırmak için potasyum (K) ağırlıklı gübre "
            "kullanın. Silikat bazlı gübreler (monosilisik asit) hem don hem sıcaklık stresine karşı "
            "hücre duvarını güçlendirir; 15 günde bir yaprak gübresi olarak verilebilir."
        )
    elif any(k in msg for k in ["verim", "mahsul", "hasat", "üretim", "ürün miktarı"]):
        response = (
            "**Kök Neden:** Verim düşüşlerinin arkasında çoğunlukla birden fazla etken birlikte rol oynar: "
            "Yetersiz gübreleme, sulama hataları, hastalık baskısı ve genetik (yanlış çeşit seçimi). "
            "Tek bir faktörü düzeltmek yeterli olmuyor; verim artışı için sistem bütüncül ele alınmalı.\n\n"
            "**Verim Artışı İçin 5 Adım:**\n"
            "1. Toprak analizi: Her 3 yılda bir laboratuvar analizi — hangi besin ne kadar eksik, bunu bilin.\n"
            "2. Çeşit seçimi: Bölgenize uygun, hastalık toleranslı, verimi kanıtlanmış çeşit kullanın.\n"
            "3. Gübreleme programı: NPK + mikro element dengesi. Çiçeklenme öncesi fosfor (P) en kritik.\n"
            "4. Sulama optimizasyonu: Damla sulama ile %20-40 daha az su, %15-25 daha yüksek verim.\n"
            "5. Hastalık kontrolü: Erken teşhis + zamanında müdahale — geç kalınan her gün verim kaybı demek.\n\n"
            "**Hava ve Mevsim Uyarısı:** Çiçeklenme döneminde sıcaklık >35°C veya <10°C olursa "
            "tozlaşma gerçekleşmez, meyve bağlama olmaz. Bu dönemlerde bor (B) + gibberellin "
            "yaprak gübresi çiçek dökülmesini azaltır.\n\n"
            "**Önleyici Bakım:** Verim hedeflerini gerçekçi belirleyin — bir tarlanın 'potansiyel verimi' "
            "çeşit kataloğundaki maksimum değerdir; saha koşullarında bu değerin %60-70'i çok başarılı "
            "sayılır. Her yıl sonunda tarım günlüğü tutun: sıcaklık, yağış, hastalık, gübre, verim "
            "notları gelecek yılın planlamasına ışık tutar."
        )
    elif any(k in msg for k in ["toprak", "ph", "kireç", "asit", "toprak analizi", "kalsiyum", "magnezyum"]):
        response = (
            "**Kök Neden:** Toprak pH'ı bitkilerin besin alabileceği bir 'pencere' belirler. "
            "Bu pencere dışına çıkıldığında (pH<6.0 veya pH>7.5) bazı besinler kimyasal olarak "
            "toprakta kilitlenir ve kök tarafından alınamaz hale gelir. Yani gübre verseniz bile "
            "bitki kullanamayabilir.\n\n"
            "**pH Düzeltme Protokolü:**\n"
            "1. Asit toprak (pH < 6.0): Kireç (kalsit veya dolomit) uygulayın. Doz: pH'ı 0.5 birim "
            "artırmak için yaklaşık 200-300 kg/da. Sonbahar aylarında toprağa karıştırın.\n"
            "2. Alkali toprak (pH > 7.5): Toz kükürt veya asit etkili gübre (amonyum sülfat) kullanın. "
            "Doz: 50-100 kg/da toz kükürt, yavaş etkilidir (2-3 ay).\n"
            "3. Hızlı düzeltme gerekiyorsa: Asit pH'lı damla sulama (%1 asetik asit veya sülfirik asit).\n\n"
            "**Eksiklik Tablo:**\n"
            "- Kalsiyum (Ca) eksikliği: Domates/biberinde çiçek dip çürüklüğü → Kalsiyum nitrat, 2 g/L.\n"
            "- Magnezyum (Mg) eksikliği: Yaprak içi sarı, damar yeşil (klorozis) → Epsom tuzu, 5 g/L.\n"
            "- Bor (B) eksikliği: Tomurcuk çürüklüğü, deforme meyve → Borax, 0.5 g/L yaprak gübresi.\n\n"
            "**Önleyici Bakım:** Toprak analizi en ucuz ve en değerli zirai yatırımdır. "
            "Her 3 yılda bir İl Tarım Müdürlüğü laboratuvarlarında veya özel laboratuvarlarda "
            "yaptırın. Organik madde oranını artırmak (kompost, yeşil gübre) toprak tampon kapasitesini "
            "yükselterek pH'ı uzun vadede dengeler."
        )
    elif any(k in msg for k in ["ekim", "tohum", "dikim", "ne ekeyim", "ne zaman ekim", "mevsim"]):
        response = (
            "**Kök Neden:** Doğru ekim zamanı; bitkinin çimlenme sıcaklığı, son don tarihi ve "
            "pazara çıkış hedefi baz alınarak belirlenir. Erken ekim don zararına, geç ekim ise "
            "hasadın sıcaklık stresli döneme denk gelmesine yol açar.\n\n"
            "**Mevsime Göre Ekim Takvimi (Türkiye Genel):**\n"
            "1. İlkbahar (Mart-Mayıs): Domates, biber, patlıcan (fide ile), mısır, kabak, salatalık.\n"
            "2. Yaz (Haziran-Temmuz): İkinci ürün mısır (Güney), yazlık fasulye, susam.\n"
            "3. Sonbahar (Ağustos-Ekim): Soğan, sarımsak, ıspanak, lahana, brokoli, havuç.\n"
            "4. Kış (Kasım-Şubat): Hububat (buğday, arpa), baklagiller (nohut, mercimek — soğuğa dayanıklı).\n\n"
            "**Bölgesel Uyarı:** Karadeniz'de geç ilkbahar donları nedeniyle dış ekim takvimini "
            "İç Anadolu'dan 2-3 hafta öne alın. Akdeniz ve Ege'de ise tüm yıl boyunca "
            "farklı ürünler yetiştirmek mümkündür; güz dönemi sebzeciliği çok karlıdır.\n\n"
            "**Önleyici Bakım:** Her ekimden önce toprağı 20-25 cm derin sürün ve havalandırın. "
            "Sertifikalı, hastalık ilaçlaması yapılmış, bölge iklim koşullarına uygun "
            "tescilli çeşit seçin. Tohumluk depolarken nem < %12, sıcaklık < 15°C sağlayın."
        )
    elif any(k in msg for k in ["böcek", "zararlı", "haşere", "yaprak biti", "tripis", "kırmızı örümcek", "akar", "tırtıl"]):
        response = (
            "**Kök Neden:** Zararlı böcekler genellikle kimyasal ilaçlamalar sonrası doğal düşmanları "
            "ortadan kalkınca hızla çoğalır (sekonder patlama). Monokültür tarım (tek ürün), "
            "aşırı azot gübrelemesi ve güneşli-sıcak koşullar birçok zararlının üremesini hızlandırır.\n\n"
            "**Yaygın Zararlı ve Müdahale:**\n"
            "1. Yaprak biti (Aphididae): Yaprak altında yoğun koloniler, yapışkan salgı → "
            "Neem yağı (%2, 5 ml/L), imidacloprid (0.5 ml/L) veya doğal düşman: uğur böceği bırakın.\n"
            "2. Kırmızı örümcek (Tetranychus): İnce ağ, soluk-bronz yaprak → Abamektin (1 ml/L) + "
            "kükürt (kış aylarında yumurta ilaçlaması).\n"
            "3. Thrips: Gümüşi çizgiler, pörtlek meyve → Spinosad (Tracer 0.4 ml/L) — hasat öncesi 3 gün.\n"
            "4. Tırtıl (Lepidoptera): Yaprak delikler, dışkı izleri → Bacillus thuringiensis (Bt) — "
            "biyolojik, güvenli, sık uygulama gerekir.\n\n"
            "**Hava Uyarısı:** Kırmızı örümcek sıcak ve kuru koşullarda (>30°C, nem<%40) patlar — "
            "damla sulamayla çevreyi nemlendirmek populasyonu baskılar. Yaprak biti ise ilkbaharda "
            "azotlu gübre fazlalığıyla tetiklenir; dengeli gübreleme koruyucudur.\n\n"
            "**Önleyici Bakım:** Ekim nöbeti zararlı populasyonlarını kırar. Tarla kenarlarında "
            "çiçekli bitki şeridi bırakmak doğal düşmanları çeker. Sarı ve mavi yapışkan tuzaklar "
            "hem izleme hem de doğrudan kontrolde etkilidir."
        )
    elif "merhaba" in msg or "selam" in msg or "naber" in msg or "hey" in msg or "günaydın" in msg:
        response = (
            "Merhaba! Ben 20 yıllık saha deneyimi olan bir Türk ziraat mühendisiyim. "
            "Bitkilerinizin hastalıkları, sulama programı, gübreleme takvimi, zararlı mücadelesi "
            "veya ne ekmeniz gerektiği konusunda detaylı rehberlik alabileceğiniz doğru yerdesiniz.\n\n"
            "Size nasıl yardımcı olabilirim? İsterseniz:\n"
            "• Hastalık belirtisi anlatın → Teşhis ve tedavi planı sunayım\n"
            "• Bitki türünüzü söyleyin → Sezona özel bakım tavsiyeleri vereyim\n"
            "• Fotoğraf yükleyin → AI görsel analizi yapsın, ben yorumlayayım\n\n"
            "Bölgenizi ve yetiştirdiğiniz ürünleri belirtirseniz çok daha spesifik önerilerde bulunabilirim."
        )
    else:
        fallback_responses = [
            (
                "Sorunuzu anlamaya çalışıyorum. Tarımda her durum bitkiye, bölgeye ve mevsime göre "
                "farklı sonuçlar doğurabilir. Size en doğru tavsiyeyi verebilmem için birkaç soru "
                "sormam gerekiyor: Hangi bitkiden bahsediyoruz? Bölgeniz neresi ve şu an hangi "
                "gelişim evresinde? Bu bilgilerle somut öneri sunabilirim.\n\n"
                "Genel bir öneri olarak: Bitki stresini azaltmak için sulama düzenliliğini kontrol edin, "
                "aşırı azot gübrelemesinden kaçının ve bitki artıklarını tarla içinde bırakmayın. "
                "Şüphelendiğiniz bir hastalık varsa fotoğraf yükleyerek AI analizinden yararlanabilirsiniz."
            ),
            (
                "Bu konu hakkında daha ayrıntılı bilgi vermek isterim. Ancak önce birkaç detaya "
                "ihtiyacım var: Sorunu hangi bitkide gözlemlediniz? Belirtiler ne zamandan beri var? "
                "İlk olarak yaprak mı, gövde mi yoksa meyve mi etkilendi?\n\n"
                "Bu bilgiler olmadan genel bir kural olarak şunu söyleyebilirim: Bir bitki sorununuz "
                "olduğunda ilk adım doğru teşhis koymaktır. Yaprak fotoğrafı yükleyerek AI analizi "
                "yaptırmanız, sistematik teşhis sürecini hızlandırır ve benim de daha spesifik "
                "müdahale önerisi sunmamı sağlar."
            ),
        ]
        import random
        response = random.choice(fallback_responses)

    return ChatResponse(
        success=True,
        response=response,
        message="AI asistanı yanıtı başarıyla oluşturdu."
    )


# =============================================================================
# Endpoint 6: POST /ai/chat-analyze  (Fotoğraflı Sohbet)
# =============================================================================

@router.post(
    "/chat-analyze",
    response_model=ChatResponse,
    summary="Fotoğraf yükleyerek zirai asistanla sohbet et",
    description=(
        "Kullanıcının yüklediği bitki fotoğrafını analiz edip "
        "hastalık tespiti yapar ve bağlamsal bir zirai tavsiye üretir."
    )
)
async def ai_chat_analyze_endpoint(
    file: UploadFile = File(..., description="Analiz edilecek bitki görseli (JPG, PNG)."),
    message: str = Form("", description="Kullanıcının ek sorusu veya notu (opsiyonel)."),
) -> ChatResponse:
    """
    Fotoğraf + opsiyonel metin mesajı alır.
    1. Görseli YOLO + EfficientNet pipeline'ından geçirir.
    2. Hastalık tespitini ve güven skorunu bağlamsal cevaba ekler.
    3. ChatResponse olarak döndürür.
    """
    try:
        image_bytes = await file.read()
        if not image_bytes:
            return ChatResponse(
                success=False,
                response="Yüklenen dosya boş. Lütfen geçerli bir bitki fotoğrafı gönderin.",
                message="Boş dosya hatası."
            )
    except Exception as exc:
        logger.error(f"chat-analyze dosya okuma hatası: {exc}")
        return ChatResponse(
            success=False,
            response="Fotoğraf okunamadı. Lütfen tekrar deneyin.",
            message="Dosya okuma hatası."
        )

    detected_disease: str | None = None
    confidence_val: float | None = None

    # --- YOLO + EfficientNet pipeline ---
    # detect_leaf() uses yolo_detector singleton internally (yolo_model=None → auto-loads).
    # We attempt this regardless of model_store.is_loaded so that partial model states
    # (e.g., YOLO loaded but EfficientNet not yet complete) still yield a useful response.
    try:
        yolo_result = detect_leaf(
            image_bytes=image_bytes,
            yolo_model=None,  # let detect_leaf use yolo_detector singleton
            confidence_threshold=0.25,
        )
        cropped_b64 = yolo_result.get("cropped_leaf_base64")
    except Exception as exc:
        logger.error(f"chat-analyze YOLO aşaması hatası: {exc}")
        cropped_b64 = None

    if cropped_b64 and model_store.efficientnet is not None:
        try:
            clf_result = classify_disease(
                cropped_leaf_base64=cropped_b64,
                efficientnet_model=model_store.efficientnet,
                class_names=model_store.class_names,
                device=model_store.device,
            )
            detected_disease = clf_result.get("predicted_class")
            confidence_val = clf_result.get("confidence")
        except Exception as exc:
            logger.error(f"chat-analyze EfficientNet aşaması hatası: {exc}")
    elif cropped_b64 is None:
        logger.warning("chat-analyze: görüntü ön-işleme başarısız, metinsel yanıt dönülüyor.")
    else:
        logger.info("chat-analyze: EfficientNet modeli yüklü değil, metinsel yanıt dönülüyor.")

    # --- Bağlamsal yanıt oluştur ---
    user_note = message.strip() if message.strip() else None

    if detected_disease and confidence_val is not None:
        conf_pct = round(confidence_val * 100, 1)
        is_healthy = detected_disease.lower() in ("healthy", "sağlıklı")

        if is_healthy:
            response_text = (
                f"Fotoğrafınızı inceledim. Güzel haber: AI sistemi bitkinin sağlıklı göründüğünü "
                f"tespit etti (%{conf_pct} güven). Yapraklarda belirgin bir hastalık belirtisi bulamadım.\n\n"
                "**Mevcut Durumun Korunması İçin Öneriler:**\n"
                "1. Sulama düzeninizi koruyun; toprak yüzeyi kurumaya başlamadan sulayın.\n"
                "2. Hava sirkülasyonunu artırmak için bitkiler arası mesafeyi muhafaza edin.\n"
                "3. Alt yaprak budaması (kaçakçı alma) toprak sıçramasından kaynaklanan mantari "
                "enfeksiyonları önler.\n"
                "4. 2 haftada bir koruyucu bakır oksiklorür uygulaması sezona göre tavsiye edilir.\n\n"
                "**Önleyici Bakım:** Bitkinin sağlıklı görünmesi, içten ilerleyen vasküler hastalıkları "
                "dışlamaz. Gövde dibini ve kök boğazını da zaman zaman kontrol edin. "
                "Herhangi bir renk değişimi veya solgunluk fark ederseniz hemen bildirim yapın."
            )
        else:
            response_text = (
                f"Fotoğrafınızı analiz ettim. **{detected_disease}** tespit edildi "
                f"(güven oranı: %{conf_pct}).\n\n"
                f"**Kök Neden:** {detected_disease} hastalığı genellikle yüksek nem, yetersiz hava "
                "sirkülasyonu ve zayıflamış bitki bağışıklığının bir araya gelmesiyle ortaya çıkar. "
                "Sporlar veya bakteriler komşu bitkilerden, sulama suyundan veya topraktan taşınıyor olabilir.\n\n"
                "**Acil Müdahale Adımları:**\n"
                "1. Belirgin şekilde enfekte olmuş yaprakları hemen kesin ve imha edin (kompost yapmayın).\n"
                "2. Bakır oksiklorür %50 WP (3 g/L) veya hastalığa özgü fungisit uygulamaya başlayın.\n"
                "3. Sulama yöntemini gözden geçirin — yaprakları ıslatmayın, damlama tercih edin.\n"
                "4. 7-10 gün sonra tekrar fotoğraf çekerek iyileşme takip edin.\n\n"
                "**Hava Uyarısı:** İlaçlamayı sabah erken (06:00-09:00) veya akşamüstü (17:00-20:00) "
                "yapın. Yağmur beklentisi varsa sistematik (içten etkili) fungisit tercih edin.\n\n"
                "**Önleyici Bakım:** Hastalığın tekrarlamaması için ekim nöbeti planlayın ve "
                "sezon başında biyofungisit (Trichoderma harzianum) uygulaması yapın."
            )

        if user_note:
            response_text += (
                f"\n\n**Notunuz hakkında:** '{user_note}' — "
                "Bu ek bilgiyi göz önünde bulundurarak öneri güncellemeleri için sohbete devam etmenizi öneririm."
            )
    else:
        # Görsel alındı ama hastalık tespit edilemedi (model eksik veya görsel işlenemedi)
        if user_note:
            response_text = (
                f"Fotoğrafınızı aldım, notunuzu da gördüm: '{user_note}'.\n\n"
                "Fotoğrafı tam olarak değerlendiremedim — yaprak üzerindeki belirtileri "
                "bana yazılı olarak tarif eder misiniz? "
                "Şunları belirtirseniz çok daha doğru teşhis koyabilirim: "
                "leke rengi ve şekli, etkilenen bölge (yaprak ucu mu, kenar mı, orta mı), "
                "ne zamandan beri var, başka yapraklara yayıldı mı?\n\n"
                "Hangi bitkiden bahsettiğinizi ve bölgenizi de paylaşırsanız, "
                "mevsimsel risk faktörlerini de hesaba katarak öneri sunabilirim."
            )
        else:
            response_text = (
                "Fotoğrafınızı aldım, teşekkürler.\n\n"
                "Yaprak üzerinde gördüğünüz belirtileri yazılı olarak tarif eder misiniz? "
                "Şunları bilmek yeterli: leke rengi (sarı, kahve, siyah, beyaz?), "
                "leke şekli (yuvarlak, düzensiz, halkalı?), etkilenen bölge, "
                "ve bu belirtilerin ne kadar süredir var olduğu.\n\n"
                "Bu bilgilerle hastalığı teşhis edip size adım adım tedavi planı sunabilirim."
            )

    return ChatResponse(
        success=True,
        response=response_text,
        detected_disease=detected_disease,
        confidence=confidence_val,
        message="Fotoğraf analizi tamamlandı."
    )
