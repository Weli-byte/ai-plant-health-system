# =============================================================================
# schemas/risk_schemas.py
#
# Sprint 3 — Plant Risk Prediction
#
# Bu dosya /api/predict-risk endpoint'inin Pydantic istek/yanıt şemalarını
# tanımlar. Şemalar otomatik FastAPI doğrulaması ve Swagger UI dökümanı sağlar.
# =============================================================================

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# İstek Şeması
# ---------------------------------------------------------------------------

# Pydantic v2 — case-insensitive mevsim girişi için Literal yerine string + validator.
_VALID_SEASONS = {"spring", "summer", "autumn", "winter"}


class RiskPredictionRequest(BaseModel):
    """
    /api/predict-risk endpoint'inin girdi şeması.

    Tüm alanlar zorunludur. Sayısal alanlar gerçekçi fiziksel
    aralıklarla doğrulanır.
    """

    temperature: float = Field(
        ...,
        ge=-20.0, le=60.0,
        description="Hava sıcaklığı (°C). Aralık: -20.0 – 60.0",
        examples=[24.5],
    )
    humidity: float = Field(
        ...,
        ge=0.0, le=100.0,
        description="Bağıl nem (%). Aralık: 0.0 – 100.0",
        examples=[78.0],
    )
    rainfall: float = Field(
        ...,
        ge=0.0, le=500.0,
        description="Günlük yağış miktarı (mm). Aralık: 0.0 – 500.0",
        examples=[12.0],
    )
    wind_speed: float = Field(
        ...,
        ge=0.0, le=200.0,
        description="Rüzgar hızı (km/sa). Aralık: 0.0 – 200.0",
        examples=[8.0],
    )
    soil_moisture: float = Field(
        ...,
        ge=0.0, le=100.0,
        description="Toprak nemi (%). Aralık: 0.0 – 100.0",
        examples=[55.0],
    )
    season: str = Field(
        ...,
        description="Mevsim. Geçerli değerler: 'spring', 'summer', 'autumn', 'winter'",
        examples=["summer"],
    )

    @field_validator("season")
    @classmethod
    def _normalize_season(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("season alanı string olmalıdır.")
        key = v.strip().lower()
        if key not in _VALID_SEASONS:
            raise ValueError(
                f"Geçersiz mevsim: '{v}'. Beklenen: {sorted(_VALID_SEASONS)}"
            )
        return key

    model_config = {
        "json_schema_extra": {
            "example": {
                "temperature": 24.5,
                "humidity": 78.0,
                "rainfall": 12.0,
                "wind_speed": 8.0,
                "soil_moisture": 55.0,
                "season": "summer",
            }
        }
    }


# ---------------------------------------------------------------------------
# Yanıt Şeması
# ---------------------------------------------------------------------------

class RiskPredictionResponse(BaseModel):
    """
    /api/predict-risk endpoint'inin başarılı yanıt şeması.
    """

    success: bool = Field(..., description="İşlem başarılı mı?")
    risk_score: float = Field(
        ...,
        ge=0.0, le=1.0,
        description="Bitki hastalık riski (0.0 = düşük, 1.0 = yüksek).",
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="risk_score'tan türetilen ayrık etiket.",
    )
    model_version: str = Field(..., description="Kullanılan risk modeli sürümü.")
    message: str = Field(..., description="Kullanıcıya gösterilecek özet mesaj.")


# ---------------------------------------------------------------------------
# Hata Şeması
# ---------------------------------------------------------------------------

class RiskErrorResponse(BaseModel):
    """Standart hata yanıtı."""
    success: bool = Field(default=False)
    detail: str = Field(..., description="Hata mesajı.")
