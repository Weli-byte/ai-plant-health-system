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
from fastapi import APIRouter, File, HTTPException, UploadFile, status
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
        bounding_box=result["bounding_box"],
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
    except (ValueError, RuntimeError) as exc:
        logger.error(f"Analyze - YOLO hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Yaprak tespiti başarısız: {exc}"
        )

    leaf_response = LeafDetectionResponse(
        success=True,
        leaf_detected=yolo_result["leaf_detected"],
        bounding_box=yolo_result["bounding_box"],
        confidence=yolo_result["confidence"],
        cropped_leaf_base64=yolo_result["cropped_leaf_base64"],
        original_width=yolo_result["original_width"],
        original_height=yolo_result["original_height"],
        message=(
            "Yaprak tespit edildi."
            if yolo_result["leaf_detected"]
            else "Yaprak tespit edilemedi."
        ),
    )

    # Yaprak bulunamadıysa pipeline'ı burada durdur
    if not yolo_result["leaf_detected"] or yolo_result["cropped_leaf_base64"] is None:
        return FullAnalysisResponse(
            success=True,
            leaf_detection=leaf_response,
            disease_classification=None,
            gradcam=None,
            message="Görselde yaprak tespit edilemedi. Hastalık analizi yapılamadı.",
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
# Endpoint 5: POST /ai/chat
# =============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Zirai Yapay Zeka Asistanı ile sohbet et",
    description=(
        "Kullanıcının bitki sağlığı, tarım ve bakım hakkındaki sorularını yanıtlar. "
        "Bu endpoint, uzman bir zirai danışman gibi davranır."
    )
)
async def ai_chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Zirai asistan mantığı. Şu an için kural tabanlı gelişmiş bir motor 
    kullanılmaktadır ancak ileride bir LLM (Gemini/OpenAI) ile entegre edilebilir.
    """
    msg = request.message.lower()
    
    # Gelişmiş Bilgi Tabanlı Mantık (API üzerinden gelen gerçek yanıtlar)
    if any(k in msg for k in ["külleme", "mildew", "beyaz leke"]):
        response = (
            "Külleme (Powdery Mildew) mantar kaynaklı bir hastalıktır. "
            "Kükürt bazlı ilaçlar etkilidir ancak uygulama sırasında hava sıcaklığının "
            "30 derecenin altında olmasına dikkat edin. Akşam saatlerini tercih edin."
        )
    elif any(k in msg for k in ["su", "sulama", "nem"]):
        response = (
            "Bitki sulamasında temel kural toprağın üst yüzeyinin kurumuş olmasıdır. "
            "Mantar hastalıklarını önlemek için yapraklara su değdirmemeye ve "
            "sabahın erken saatlerinde sulama yapmaya özen gösterin."
        )
    elif any(k in msg for k in ["gübre", "besin", "npk"]):
        response = (
            "Bitkinizin gelişim evresine göre gübreleme yapmalısınız. "
            "Yaprak gelişimi için Azot (N), çiçeklenme için Fosfor (P) ağırlıklı "
            "organik gübreler tavsiye edilir. Hastalıklı bitkiye ağır gübreleme yapmayın."
        )
    elif any(k in msg for k in ["pas", "rust", "turuncu"]):
        response = (
            "Pas hastalığı genellikle yüksek nemden kaynaklanır. Bakır içerikli "
            "fungisitler (Bordo bulamacı gibi) bu hastalıkta oldukça etkilidir. "
            "Hastalıklı yaprakları derhal imha edin."
        )
    elif "merhaba" in msg or "selam" in msg:
        response = "Merhaba! Ben Agro AI. Bitkileriniz hakkında her türlü soruyu bana sorabilirsiniz. Size nasıl yardımcı olabilirim?"
    else:
        response = (
            "Bu konuda size en doğru bilgiyi verebilmem için bitkinizin bir fotoğrafını "
            "'Tahlil' kısmından yüklemenizi öneririm. Genel bir tavsiye olarak; "
            "bitkinizin havalandırmasını artırmak ve nem dengesini korumak çoğu hastalığı önleyecektir."
        )

    return ChatResponse(
        success=True,
        response=response,
        message="AI asistanı yanıtı başarıyla oluşturdu."
    )
