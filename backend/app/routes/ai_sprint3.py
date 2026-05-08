# =============================================================================
# routes/ai_sprint3.py
#
# Sprint 3 — Tarım AI Karar Destek Sistemi Endpoint'leri
#
# Bu dosya Sprint 3'e özgü 3 yeni endpoint'i tanımlar. Mevcut route
# dosyalarına (ai_detection.py, risk.py vb.) dokunulmamıştır.
#
# Endpoint'ler:
#   POST /sprint3/predict_risk      → XGBoost + Kural Motoru Risk Skoru
#   POST /sprint3/get_plant_future  → LSTM Digital Twin (3 + 7 günlük tahmin)
#   POST /sprint3/get_farming_advice → Kural Motoru Tarım Danışma Raporu
#
# Bağımlılıklar:
#   - services/risk_prediction_service.py  (XGBoost)
#   - services/digital_twin_service.py     (LSTM)
#   - services/recommendation_service.py   (Kural motoru + pesticide DB)
#   - schemas/ai_schemas.py                (Sprint 3 şemaları)
#
# Çalıştırmak için main.py'ye ekleyin:
#   from app.routes import ai_sprint3
#   app.include_router(ai_sprint3.router)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas.ai_schemas import (
    ClimateDataRequest,
    DayForecast,
    FarmingAdviceRequest,
    FarmingAdviceResponse,
    PesticideRecommendation,
    PlantFutureRequest,
    PlantFutureResponse,
    RiskScoreResponse,
)
from app.services.recommendation_service import (
    get_farming_advice,
    get_pesticide_recommendations,
)

logger = logging.getLogger(__name__)

# Router tanımı — tüm Sprint 3 endpoint'leri /sprint3 prefix'i altında
router = APIRouter(
    prefix="/sprint3",
    tags=["Sprint 3 — Tarım Karar Destek Sistemi"],
)


# =============================================================================
# Yardımcı: Risk seviyesi → DayForecast nesnesi
# =============================================================================

def _risk_level_from_score(score_pct: float) -> str:
    """
    0-100 arasındaki risk yüzdesini etiket string'ine çevirir.

    Args:
        score_pct: 0-100 arası risk yüzdesi.

    Returns:
        'Low', 'Medium', 'High' veya 'Critical'.
    """
    if score_pct < 25.0:
        return "Low"
    if score_pct < 50.0:
        return "Medium"
    if score_pct < 75.0:
        return "High"
    return "Critical"


def _make_day_forecast(day: int, raw_score: float) -> DayForecast:
    """
    LSTM çıktısından (0-1 normalize skor) DayForecast nesnesi oluşturur.

    Args:
        day:       Tahmin ufku (3 veya 7 gün).
        raw_score: 0-1 arasında LSTM çıktısı.

    Returns:
        DayForecast Pydantic nesnesi.
    """
    pct = round(raw_score * 100.0, 2)
    return DayForecast(
        day=day,
        risk_score=round(raw_score, 4),
        risk_score_pct=pct,
        risk_level=_risk_level_from_score(pct),
    )


def _determine_trend(score_3d: float, score_7d: float) -> str:
    """
    3 gün ve 7 gün risk skorlarına bakarak trendi belirler.

    Args:
        score_3d: 3 günlük risk skoru (0-1).
        score_7d: 7 günlük risk skoru (0-1).

    Returns:
        'increasing', 'stable' veya 'decreasing'.
    """
    delta = score_7d - score_3d
    if delta > 0.05:
        return "increasing"
    if delta < -0.05:
        return "decreasing"
    return "stable"


# =============================================================================
# Endpoint 1: POST /sprint3/predict_risk
# =============================================================================

@router.post(
    "/predict_risk",
    response_model=RiskScoreResponse,
    summary="XGBoost ile hastalık risk skoru hesapla",
    description=(
        "İklim ve çevre verilerini (sıcaklık, nem, yağış, rüzgar, mevsim) alarak "
        "0-100 arasında bir **Hastalık Risk Skoru** hesaplar. "
        "XGBoost modeli yüklü değilse kural tabanlı hesaplama devreye girer."
    ),
    responses={
        200: {"description": "Risk skoru başarıyla hesaplandı."},
        400: {"description": "Geçersiz girdi verisi."},
        500: {"description": "Sunucu tarafı inference hatası."},
    },
)
async def predict_risk_endpoint(
    request: ClimateDataRequest,
) -> RiskScoreResponse:
    """
    **İşlem Akışı:**
    1. Pydantic gelen JSON'u doğrular (sıcaklık, nem aralıkları vb.).
    2. XGBoost `RiskPredictor` singleton'u predict() çağrısı yapar.
    3. Model yüklü değilse kural tabanlı fallback devreye girer.
    4. Risk seviyesi, renk ve öneriler hesaplanarak döndürülür.
    """
    logger.info(
        "POST /sprint3/predict_risk | sıc=%.1f nem=%.0f%% mevsim=%s",
        request.temperature,
        request.humidity,
        request.season,
    )

    # ── XGBoost inference (lazy load ile) ───────────────────────────────────
    try:
        from app.services.risk_prediction_service import predict_risk as xgb_predict

        result: dict[str, Any] = xgb_predict({
            "temperature": request.temperature,
            "humidity":    request.humidity,
            "rainfall":    request.rainfall,
            "wind_speed":  request.wind_speed,
            "season":      request.season,
        })

        model_used = "xgboost"
        risk_score: float = result["risk_score"]
        risk_level: str   = result["risk_level"]
        risk_label: str   = result["risk_label"]
        risk_color: str   = result["risk_color"]
        action: str       = result["action"]
        recommendations: list[str] = result["recommendations"]

    except FileNotFoundError:
        # Model dosyası yok → kural tabanlı fallback
        logger.warning(
            "XGBoost model dosyası bulunamadı. Kural tabanlı fallback devreye girdi."
        )
        advice_data = get_farming_advice(
            temperature=request.temperature,
            humidity=request.humidity,
            rainfall=request.rainfall,
            wind_speed=request.wind_speed,
            season=request.season,
            plant_health_status=request.plant_health_status or "healthy",
            disease_name=request.disease_name,
        )
        model_used    = "rule_based"
        risk_score    = advice_data["risk_score"]
        risk_level    = advice_data["risk_level"]
        risk_label    = advice_data["risk_label"]
        risk_color    = advice_data["risk_color"]
        action        = advice_data["general_notes"]
        recommendations = advice_data["farming_advice"]

    except (ValueError, TypeError) as exc:
        logger.warning("Geçersiz risk girdisi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Risk inference hatası: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk tahmini sırasında beklenmeyen hata: {exc}",
        )

    return RiskScoreResponse(
        success=True,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_label=risk_label,
        risk_color=risk_color,
        action=action,
        recommendations=recommendations,
        model_used=model_used,
        message="Hastalık risk skoru başarıyla hesaplandı.",
    )


# =============================================================================
# Endpoint 2: POST /sprint3/get_plant_future
# =============================================================================

@router.post(
    "/get_plant_future",
    response_model=PlantFutureResponse,
    summary="LSTM Digital Twin ile 3 ve 7 günlük risk tahmini",
    description=(
        "Geçmiş günlük gözlemleri (en az 3 satır, her satır 7 özellik) alarak "
        "LSTM tabanlı Digital Twin modeli ile **3 gün** ve **7 gün** sonrası "
        "için hastalık riski tahmin eder. "
        "Model yüklü değilse 503 döndürür."
    ),
    responses={
        200: {"description": "Tahmin başarıyla tamamlandı."},
        400: {"description": "Geçersiz gözlem verisi (eksik satır/sütun)."},
        503: {"description": "LSTM Digital Twin modeli yüklü değil."},
        500: {"description": "Beklenmeyen sunucu hatası."},
    },
)
async def get_plant_future_endpoint(
    request: PlantFutureRequest,
) -> PlantFutureResponse:
    """
    **İşlem Akışı:**
    1. Pydantic gözlem matrisini (N×7) doğrular.
    2. `digital_twin_service.predict_future()` fonksiyonu LSTM modelini çalıştırır.
    3. 3 ve 7 günlük çıktılar normalize edilerek DayForecast nesnelerine çevrilir.
    4. Trend (increasing/stable/decreasing) hesaplanır.
    5. Yanıt yapılandırılarak döndürülür.
    """
    logger.info(
        "POST /sprint3/get_plant_future | gözlem_satırı=%d konum=%s",
        len(request.observations),
        request.location_label,
    )

    # Gözlem boyutu doğrulama: her satır 7 özellik içermeli
    for idx, row in enumerate(request.observations):
        if len(row) != 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Satır {idx} geçersiz: beklenen 7 özellik, "
                    f"gelen {len(row)} özellik. "
                    "Format: [risk, temperature, humidity, rainfall, "
                    "wind_speed, soil_moisture, plant_health]"
                ),
            )

    # ── LSTM inference ───────────────────────────────────────────────────────
    try:
        from app.services.digital_twin_service import (
            digital_twin_store,
            predict_future,
        )

        if not digital_twin_store.is_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "LSTM Digital Twin modeli yüklü değil. "
                    "Modeli eğitmek için: python -m app.ml.digital_twin_model"
                ),
            )

        result = predict_future(request.observations)
        model_version: str = result.get("model_version", "unknown")

        # LSTM çıktısı: horizons_days=[3,7], risk_scores=[s3, s7]
        horizons: list[int]   = result.get("horizons_days", [3, 7])
        scores:   list[float] = result.get("risk_scores",  [0.0, 0.0])

        # 3 ve 7 günlük skorları güvenli biçimde al
        score_3d = float(scores[horizons.index(3)]) if 3 in horizons else float(scores[0])
        score_7d = float(scores[horizons.index(7)]) if 7 in horizons else float(scores[-1])

    except HTTPException:
        raise  # Üstten gelen HTTPException'ları yeniden fırlat
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Digital twin inference hatası: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tahmin sırasında beklenmeyen hata: {exc}",
        )

    forecast_3d = _make_day_forecast(3, score_3d)
    forecast_7d = _make_day_forecast(7, score_7d)
    trend        = _determine_trend(score_3d, score_7d)

    return PlantFutureResponse(
        success=True,
        location_label=request.location_label,
        forecast_3_day=forecast_3d,
        forecast_7_day=forecast_7d,
        trend=trend,
        model_version=model_version,
        message="Dijital ikiz simülasyonu başarıyla tamamlandı.",
    )


# =============================================================================
# Endpoint 3: POST /sprint3/get_farming_advice
# =============================================================================

@router.post(
    "/get_farming_advice",
    response_model=FarmingAdviceResponse,
    summary="Kural motoru ile tarım danışma raporu ve ilaç önerisi",
    description=(
        "İklim koşulları ve bitki sağlık durumuna göre **kural tabanlı** "
        "tarım önerileri üretir. Hastalık adı girilirse `pesticides.json` "
        "veritabanından uygun zirai ilaç önerileri eklenir. "
        "Bu endpoint hiçbir ML modeline ihtiyaç duymaz; her zaman çalışır."
    ),
    responses={
        200: {"description": "Tarım danışma raporu hazırlandı."},
        400: {"description": "Geçersiz girdi (bilinmeyen mevsim vb.)."},
        500: {"description": "Beklenmeyen sunucu hatası."},
    },
)
async def get_farming_advice_endpoint(
    request: FarmingAdviceRequest,
) -> FarmingAdviceResponse:
    """
    **İşlem Akışı:**
    1. Pydantic gelen JSON'u doğrular.
    2. `recommendation_service.get_farming_advice()` kural motorunu çalıştırır:
       - Nem > 80 → fungisit öner (Kural 1)
       - Sıcaklık 18-28°C → mantar riski uyarısı (Kural 2)
       - Yağış > 100mm → drenaj uyarısı (Kural 3)
       - Rüzgar > 40km/s → ilaçlama erteleme önerisi (Kural 4)
       - Mevsime özgü tavsiye (Kural 5)
       - Bitki sağlığı = diseased → acil müdahale (Kural 6)
    3. Hastalık adı verilmişse pesticide DB sorgulanır.
    4. Yanıt yapılandırılarak döndürülür.
    """
    logger.info(
        "POST /sprint3/get_farming_advice | nem=%.0f%% mevsim=%s sağlık=%s hastalık=%s",
        request.humidity,
        request.season,
        request.plant_health_status,
        request.disease_name,
    )

    # Mevsim doğrulaması
    valid_seasons = {"spring", "summer", "autumn", "winter"}
    if request.season.lower() not in valid_seasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Geçersiz mevsim: '{request.season}'. "
                f"Geçerli değerler: {sorted(valid_seasons)}"
            ),
        )

    try:
        advice_data = get_farming_advice(
            temperature=request.temperature,
            humidity=request.humidity,
            rainfall=request.rainfall,
            wind_speed=request.wind_speed,
            season=request.season,
            plant_health_status=request.plant_health_status,
            disease_name=request.disease_name,
            crop_type=request.crop_type,
        )
    except Exception as exc:
        logger.error("Öneri servisi hatası: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tarım önerisi üretilirken hata oluştu: {exc}",
        )

    # Pesticide sözlüklerini Pydantic modeline dönüştür
    pesticide_models: list[PesticideRecommendation] = [
        PesticideRecommendation(
            disease=p["disease"],
            product_type=p["product_type"],
            active_ingredient=p["active_ingredient"],
            product_name=p["product_name"],
            application_notes=p["application_notes"],
        )
        for p in advice_data["pesticide_recommendations"]
    ]

    return FarmingAdviceResponse(
        success=True,
        risk_level=advice_data["risk_level"],
        farming_advice=advice_data["farming_advice"],
        pesticide_recommendations=pesticide_models,
        irrigation_advice=advice_data["irrigation_advice"],
        general_notes=advice_data["general_notes"],
        message="Tarım danışma raporu başarıyla hazırlandı.",
    )
