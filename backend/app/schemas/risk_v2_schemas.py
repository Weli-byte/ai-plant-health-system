"""
app/schemas/risk_v2_schemas.py
==============================
Pydantic schemas for the **advanced** risk endpoint (Sprint 4).

Suffixed ``_v2`` to keep the legacy Sprint 3 ``risk_schemas.py`` untouched.

Endpoint: ``POST /predict_risk``
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.ml.risk_model import CROP_TYPES, SOIL_TYPES


class RiskPredictRequestV2(BaseModel):
    """Input payload for the advanced risk pipeline."""

    temperature: float = Field(..., ge=-30.0, le=60.0, description="Air temperature (°C).")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity (%).")
    rainfall: float = Field(..., ge=0.0, le=500.0, description="Daily rainfall (mm).")
    soil_type: str = Field(
        ...,
        description=f"One of: {SOIL_TYPES}",
    )
    crop_type: str = Field(
        ...,
        description=f"One of: {CROP_TYPES}",
    )

    @field_validator("soil_type")
    @classmethod
    def _check_soil(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key not in SOIL_TYPES:
            raise ValueError(f"Invalid soil_type '{v}'. Expected one of {SOIL_TYPES}.")
        return key

    @field_validator("crop_type")
    @classmethod
    def _check_crop(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key not in CROP_TYPES:
            raise ValueError(f"Invalid crop_type '{v}'. Expected one of {CROP_TYPES}.")
        return key

    model_config = {
        "json_schema_extra": {
            "example": {
                "temperature": 24.5,
                "humidity": 78.0,
                "rainfall": 12.0,
                "soil_type": "loam",
                "crop_type": "tomato",
            }
        }
    }


class RiskPredictDataV2(BaseModel):
    """Inner ``data`` block of the success envelope."""
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: Literal["low", "medium", "high"]
    model_version: str
    metrics: Dict[str, float] = Field(default_factory=dict)


class RiskPredictResponseV2(BaseModel):
    """Standard success envelope: ``{success, data, message}``."""
    success: bool = True
    data: Optional[RiskPredictDataV2] = None
    message: str = ""


class RiskErrorEnvelope(BaseModel):
    """Standard error envelope (returned via FastAPI ``HTTPException.detail``)."""
    success: bool = False
    data: Optional[Any] = None
    message: str
