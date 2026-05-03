"""
app/routes/digital_twin.py
===========================
Sprint 4 — Digital Twin forecast endpoint.

POST /api/v2/predict_future

Accepts a history window of daily observations and returns 3-day and
7-day risk forecasts.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.digital_twin_schemas import (
    DigitalTwinRequest,
    DigitalTwinResponse,
)
from app.services.digital_twin_service import (
    digital_twin_store,
    predict_future,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Digital Twin Forecast — Sprint 4"],
)


@router.post(
    "/predict_future",
    response_model=DigitalTwinResponse,
    summary="Forecast future plant risk using LSTM digital twin",
    responses={
        200: {"description": "Forecast computed successfully."},
        400: {"description": "Invalid observation data."},
        503: {"description": "Digital twin model not loaded."},
    },
)
async def predict_future_endpoint(
    request: DigitalTwinRequest,
) -> DigitalTwinResponse:
    """
    Given recent daily observations (risk, temperature, humidity, rainfall,
    wind_speed, soil_moisture, plant_health), forecast risk for day +3 and
    day +7.
    """
    if not digital_twin_store.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Digital twin model is not loaded. "
                "Train it via: python -m app.ml.digital_twin_model  "
                "then restart the server."
            ),
        )

    try:
        result = predict_future(request.observations)
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
        logger.error("Digital twin forecast error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {exc}",
        )

    return DigitalTwinResponse(
        success=True,
        data=result,
        message="Future risk forecast completed successfully.",
    )
