"""
app/routes/risk_v2.py
=====================
Sprint 4 — Advanced Risk Prediction endpoint.

POST /api/v2/predict_risk

Uses the sklearn Pipeline (OneHot + StandardScaler + XGBoost) trained
in ``app.ml.risk_model``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.risk_v2_schemas import (
    RiskPredictRequestV2,
    RiskPredictResponseV2,
    RiskPredictDataV2,
)
from app.services.risk_v2_service import predict_risk_v2, risk_v2_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Risk Prediction v2 — Sprint 4"],
)


@router.post(
    "/predict_risk",
    response_model=RiskPredictResponseV2,
    summary="Advanced risk prediction (XGBoost pipeline with categorical features)",
    responses={
        200: {"description": "Risk prediction computed successfully."},
        400: {"description": "Invalid input data."},
        503: {"description": "Risk model not loaded."},
    },
)
async def predict_risk_v2_endpoint(
    request: RiskPredictRequestV2,
) -> RiskPredictResponseV2:
    """
    Accepts temperature, humidity, rainfall, soil_type, crop_type and
    returns a risk score (0–100) plus risk level (low/medium/high).
    """
    # Model loaded?
    if not risk_v2_store.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Risk v2 model is not loaded. "
                "Train it via: python -m app.ml.risk_model  "
                "then restart the server."
            ),
        )

    try:
        result = predict_risk_v2(request.model_dump())
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
        logger.error("Risk v2 inference error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk prediction failed: {exc}",
        )

    msg_map = {
        "low": "Low risk — conditions are favourable, continue standard care.",
        "medium": "Medium risk — monitor environmental parameters closely.",
        "high": "High risk — take protective action (ventilation, irrigation, treatment).",
    }

    return RiskPredictResponseV2(
        success=True,
        data=RiskPredictDataV2(
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            model_version=result["model_version"],
            metrics=result.get("metrics", {}),
        ),
        message=msg_map.get(result["risk_level"], ""),
    )
