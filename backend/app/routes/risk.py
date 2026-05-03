# =============================================================================
# routes/risk.py
#
# Sprint 3 — Plant Risk Prediction Endpoint
#
# Bu dosya /api/predict-risk endpoint'ini tanımlar.
#
# NOT (mimari): Spec'te bu dosyanın yolu `app/api/risk.py` olarak geçer.
# Bu projede mevcut endpoint'ler `app/routes/` altında toplanmıştır
# (users.py, plants.py, ai_detection.py vb.). Tutarlılığı korumak için
# dosyayı `routes/risk.py` olarak yerleştirdik; URL prefix'ini `/api`
# yaparak final endpoint yolunu spec ile birebir aynı tuttuk:
#   POST /api/predict-risk
# =============================================================================

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.risk_schemas import (
    RiskErrorResponse,
    RiskPredictionRequest,
    RiskPredictionResponse,
)
from app.services.risk_service import (
    RiskInputValidationError,
    RiskModelNotLoadedError,
    predict_risk,
    risk_model_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Risk Prediction - Sprint 3"],
)


@router.post(
    "/predict-risk",
    response_model=RiskPredictionResponse,
    summary="Çevresel verilerden bitki hastalık riski tahmin et",
    description=(
        "Yapısal çevre verilerini (sıcaklık, nem, yağış, rüzgar, toprak nemi, mevsim) "
        "alıp 0–1 arasında bir hastalık riski skoru ile birlikte ayrık risk seviyesi "
        "(low/medium/high) döndürür. **Görsel girdi kullanmaz** — XGBoost regressor."
    ),
    responses={
        200: {"description": "Risk tahmini başarıyla hesaplandı."},
        400: {"model": RiskErrorResponse, "description": "Geçersiz girdi."},
        422: {"model": RiskErrorResponse, "description": "Şema doğrulama hatası."},
        503: {"model": RiskErrorResponse, "description": "Risk modeli yüklenmemiş."},
    },
)
async def predict_risk_endpoint(
    request: RiskPredictionRequest,
) -> RiskPredictionResponse:
    """
    **İşlem Akışı:**
    1. Pydantic, gelen JSON'u tip ve aralık olarak doğrular.
    2. `risk_service.predict_risk()` çağrılır (singleton XGBoost modeli).
    3. Skor 0–1 arasına clip edilir; risk_level türetilir.
    4. Yanıt döndürülür.
    """
    # Model yüklü mü?
    if not risk_model_store.is_loaded:
        logger.warning("Risk modeli yüklü değil — 503 döndürülüyor.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Risk modeli henüz yüklenmedi. "
                "Önce 'python -m app.ml.train_risk_model' komutunu çalıştırın "
                "ve sunucuyu yeniden başlatın."
            ),
        )

    # Inference
    try:
        result = predict_risk(request.model_dump())
    except RiskInputValidationError as exc:
        logger.warning(f"Geçersiz risk girdisi: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RiskModelNotLoadedError as exc:
        # Yarış koşulu (race condition) — model unload edilmiş olabilir
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error(f"Risk inference hatası: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk tahmini sırasında hata: {exc}",
        )

    # Mesaj
    msg_map = {
        "low": "Düşük risk: koşullar uygun, mevcut bakım rutinine devam edin.",
        "medium": "Orta risk: çevresel parametreleri yakından izleyin.",
        "high": "Yüksek risk: koruyucu önlem alın (havalandırma, sulama düzeni, ilaçlama).",
    }

    return RiskPredictionResponse(
        success=True,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        model_version=result["model_version"],
        message=msg_map[result["risk_level"]],
    )
