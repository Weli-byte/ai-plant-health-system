"""
app/schemas/multimodal_schemas.py
=================================
Pydantic schemas for the multimodal endpoint (Sprint 4 — Task 6).

Endpoint: ``POST /multimodal_predict``

Image is provided as **base64-encoded bytes** so the request stays a single
JSON document (matches the tone of the legacy ``/ai/classify_disease``
endpoint, which already accepts base64). Multipart upload would also work
but is intentionally not used here to keep the schema purely declarative.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.ml.multimodal_model import SOIL_TYPES, WEATHER_FEATURES


class WeatherInput(BaseModel):
    """Five numeric weather features expected by the multimodal model."""
    temperature: float = Field(..., ge=-30.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    rainfall: float = Field(..., ge=0.0, le=500.0)
    wind_speed: float = Field(..., ge=0.0, le=200.0)
    soil_moisture: float = Field(..., ge=0.0, le=100.0)

    def to_vector(self) -> List[float]:
        """Return weather features in the order the model expects."""
        return [
            self.temperature,
            self.humidity,
            self.rainfall,
            self.wind_speed,
            self.soil_moisture,
        ]


class MultimodalPredictRequest(BaseModel):
    """Input payload for the multimodal endpoint."""

    image_base64: str = Field(
        ...,
        min_length=1,
        description="Base64-encoded plant leaf image (JPEG / PNG).",
    )
    weather: WeatherInput = Field(
        ...,
        description="Current environmental conditions.",
    )
    soil_type: str = Field(
        ...,
        description=f"One of: {SOIL_TYPES}",
    )

    @field_validator("soil_type")
    @classmethod
    def _check_soil(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key not in SOIL_TYPES:
            raise ValueError(
                f"Invalid soil_type '{v}'. Expected one of {SOIL_TYPES}."
            )
        return key

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_base64": "<base64-encoded-image>",
                "weather": {
                    "temperature": 24.5,
                    "humidity": 78.0,
                    "rainfall": 12.0,
                    "wind_speed": 8.0,
                    "soil_moisture": 55.0,
                },
                "soil_type": "loam",
            }
        }
    }


class MultimodalPredictResponse(BaseModel):
    """Success envelope for the multimodal endpoint."""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = ""
