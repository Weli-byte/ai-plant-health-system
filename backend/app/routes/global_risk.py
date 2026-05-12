"""
app/routes/global_risk.py
==========================
Sprint 4 — Week 1: Global Disease Spread Analysis endpoint.

POST /api/v2/global_risk_analysis

Uses the GNN pipeline from ``app.ml.global_gnn_model`` to predict
regional disease spread risk from geo-located disease reports.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.global_risk_schemas import (
    GlobalRiskAnalysisRequest,
    GlobalRiskAnalysisResponse,
    GlobalRiskAnalysisData,
    GraphSummary,
    RegionResult,
    EnvironmentalSummary,
)
from app.services.global_risk_service import analyze_global_risk, global_gnn_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Global Risk Analysis — Sprint 4 Week 1"],
)


@router.post(
    "/global_risk_analysis",
    response_model=GlobalRiskAnalysisResponse,
    summary="Analyse regional disease spread risk via Graph Neural Network",
    responses={
        200: {"description": "Global risk analysis computed successfully."},
        400: {"description": "Invalid input data."},
        503: {"description": "GNN model not loaded."},
    },
)
async def global_risk_analysis_endpoint(
    request: GlobalRiskAnalysisRequest,
) -> GlobalRiskAnalysisResponse:
    """
    Accepts a list of geo-located disease reports and returns per-region
    outbreak risk predictions powered by a Graph Neural Network.
    """
    # ── Model readiness check ─────────────────────────────────────────────
    if not global_gnn_store.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Global GNN model is not loaded. "
                "Train it via: python -m app.ml.global_gnn_model  "
                "then restart the server."
            ),
        )

    # ── Prepare input ─────────────────────────────────────────────────────
    reports = [r.model_dump() for r in request.reports]
    config = request.analysis_config.model_dump() if request.analysis_config else {}

    # ── Run pipeline ──────────────────────────────────────────────────────
    try:
        result = analyze_global_risk(reports, config)
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
        logger.error("Global risk analysis error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Global risk analysis failed: {exc}",
        )

    # ── Build response envelope ───────────────────────────────────────────
    region_models = [
        RegionResult(
            region_id=r["region_id"],
            center_lat=r["center_lat"],
            center_lng=r["center_lng"],
            num_reports=r["num_reports"],
            dominant_disease=r["dominant_disease"],
            dominant_crop=r["dominant_crop"],
            regional_risk_score=r["regional_risk_score"],
            outbreak_probability=r["outbreak_probability"],
            disease_heat_level=r["disease_heat_level"],
            nearby_regions_at_risk=r.get("nearby_regions_at_risk", []),
            environmental_summary=EnvironmentalSummary(**r["environmental_summary"]),
        )
        for r in result["regions"]
    ]

    high_count = result.get("_high_risk_count", 0)
    n_regions = result["total_regions_identified"]

    data = GlobalRiskAnalysisData(
        analysis_id=result["analysis_id"],
        total_reports_processed=result["total_reports_processed"],
        total_regions_identified=n_regions,
        graph_summary=GraphSummary(**result["graph_summary"]),
        regions=region_models,
        model_version=result["model_version"],
        inference_device=result["inference_device"],
    )

    message = (
        f"Global risk analysis completed. "
        f"{n_regions} regions analyzed, "
        f"{high_count} region(s) at HIGH/CRITICAL risk."
    )

    return GlobalRiskAnalysisResponse(
        success=True,
        data=data,
        message=message,
    )
