"""
app/routes/multimodal.py
========================
Sprint 4 — Multimodal disease-risk endpoint.

POST /api/v2/multimodal_predict

Accepts a base64-encoded plant image + weather data + soil type and
returns a combined risk or disease prediction.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.multimodal_schemas import (
    MultimodalPredictRequest,
    MultimodalPredictResponse,
)
from app.services.multimodal_service import (
    multimodal_store,
    predict_multimodal,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Multimodal Prediction — Sprint 4"],
)


@router.post(
    "/multimodal_predict",
    response_model=MultimodalPredictResponse,
    summary="Multimodal risk/disease prediction (image + weather + soil)",
    responses={
        200: {"description": "Prediction computed successfully."},
        400: {"description": "Invalid input (bad image, bad soil_type, etc.)."},
        503: {"description": "Multimodal model not loaded."},
    },
)
async def multimodal_predict_endpoint(
    request: MultimodalPredictRequest,
) -> MultimodalPredictResponse:
    """
    Fuses a plant leaf image with environmental and soil data to produce
    either a risk score (regression mode) or disease classification.
    """
    if not multimodal_store.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Multimodal model is not loaded. "
                "Train it via: python -m app.ml.multimodal_model  "
                "then restart the server."
            ),
        )

    try:
        result = predict_multimodal(
            weather_vector=request.weather.to_vector(),
            soil_type=request.soil_type,
            image_base64=request.image_base64,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Multimodal inference error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimodal prediction failed: {exc}",
        )

    return MultimodalPredictResponse(
        success=True,
        data=result,
        message="Multimodal prediction completed successfully.",
    )
