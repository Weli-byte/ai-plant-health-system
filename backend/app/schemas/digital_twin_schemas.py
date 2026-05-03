"""
app/schemas/digital_twin_schemas.py
====================================
Pydantic schemas for the Digital Twin forecast endpoint (Sprint 4 — Task 7).

Endpoint: ``POST /predict_future``
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.ml.digital_twin_model import DEFAULT_SEQUENCE_LENGTH, FEATURE_NAMES


class DigitalTwinRequest(BaseModel):
    """
    Input payload for the digital-twin forecast endpoint.

    ``observations`` is a list of recent daily observation vectors.
    Each inner list must contain exactly 7 floats in the order:
        [risk_score, temperature, humidity, rainfall, wind_speed,
         soil_moisture, plant_health]

    At least 1 observation is required; if fewer than 14 are given,
    the model front-pads automatically.
    """

    observations: List[List[float]] = Field(
        ...,
        min_length=1,
        description=(
            f"Recent daily observations. Each inner list has "
            f"{len(FEATURE_NAMES)} floats: {FEATURE_NAMES}. "
            f"Ideal length: {DEFAULT_SEQUENCE_LENGTH} days."
        ),
    )

    @field_validator("observations")
    @classmethod
    def _check_feature_count(cls, v: List[List[float]]) -> List[List[float]]:
        expected = len(FEATURE_NAMES)
        for i, obs in enumerate(v):
            if len(obs) != expected:
                raise ValueError(
                    f"observation #{i} has {len(obs)} features; "
                    f"expected {expected} ({FEATURE_NAMES})."
                )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "observations": [
                    [0.45, 24.0, 72.0, 8.0, 10.0, 55.0, 0.80],
                    [0.50, 25.5, 75.0, 12.0, 8.0, 52.0, 0.75],
                    [0.55, 26.0, 80.0, 20.0, 6.0, 48.0, 0.70],
                ]
            }
        }
    }


class HorizonForecast(BaseModel):
    """A single forecast horizon result."""
    horizon_days: int
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]


class DigitalTwinResponse(BaseModel):
    """Success envelope for the digital-twin endpoint."""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = ""
