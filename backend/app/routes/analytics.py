"""
app/routes/analytics.py
========================
Sprint 4 — Regional Analytics Engine REST endpoints.

    GET /api/v2/regional_statistics  — aggregated per-region disease stats.
    GET /api/v2/disease_heatmap      — map-visualisation-ready heat points.
    GET /api/v2/top_risk_regions     — ranked highest-risk regions.
    GET /api/v2/outbreak_trends      — temporal trend analysis.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.analytics_schemas import (
    RegionalStatisticsResponse,
    RegionalStatisticsData,
    RegionSummary,
    DiseaseCount,
    EnvironmentalAverage,
    HeatmapResponse,
    HeatmapData,
    HeatmapPoint,
    TopRiskRegionsResponse,
    TopRiskRegionsData,
    RankedRegion,
    OutbreakTrendsResponse,
    OutbreakTrendsData,
    DiseaseTrend,
    RegionTrend,
    TrendPoint,
)
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Regional Analytics — Sprint 4"],
)


# ──────────────────────────────────────────────────────────────────────────
# GET /regional_statistics
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/regional_statistics",
    response_model=RegionalStatisticsResponse,
    summary="Aggregated disease statistics per region",
)
async def regional_statistics_endpoint() -> RegionalStatisticsResponse:
    """
    Returns per-region summaries including report counts, average risk,
    severity, dominant disease/crop, and disease distribution.
    """
    if not analytics_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics engine not initialised.",
        )

    try:
        result = analytics_service.get_regional_statistics()
    except Exception as exc:
        logger.error("Regional statistics error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute regional statistics: {exc}",
        )

    region_models = [
        RegionSummary(
            region=r["region"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            total_reports=r["total_reports"],
            risk_score=r["risk_score"],
            severity_index=r["severity_index"],
            dominant_disease=r["dominant_disease"],
            dominant_crop=r["dominant_crop"],
            disease_distribution=[DiseaseCount(**d) for d in r["disease_distribution"]],
            environment=EnvironmentalAverage(**r["environment"]) if r.get("environment") else None,
        )
        for r in result["regions"]
    ]

    return RegionalStatisticsResponse(
        success=True,
        data=RegionalStatisticsData(
            total_regions=result["total_regions"],
            total_reports=result["total_reports"],
            overall_avg_risk=result["overall_avg_risk"],
            overall_avg_severity=result["overall_avg_severity"],
            regions=region_models,
            disease_overview=[DiseaseCount(**d) for d in result["disease_overview"]],
        ),
        message=f"{result['total_regions']} regions analysed from {result['total_reports']} reports.",
    )


# ──────────────────────────────────────────────────────────────────────────
# GET /disease_heatmap
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/disease_heatmap",
    response_model=HeatmapResponse,
    summary="Heatmap-ready disease intensity data for map visualisation",
)
async def disease_heatmap_endpoint() -> HeatmapResponse:
    """
    Returns an array of ``{region, lat, lng, heat_score, outbreak_level}``
    objects suitable for direct use in a map heatmap layer.
    """
    if not analytics_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics engine not initialised.",
        )

    try:
        result = analytics_service.get_disease_heatmap()
    except Exception as exc:
        logger.error("Heatmap error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate heatmap: {exc}",
        )

    point_models = [HeatmapPoint(**p) for p in result["points"]]

    return HeatmapResponse(
        success=True,
        data=HeatmapData(
            total_points=result["total_points"],
            max_heat_score=result["max_heat_score"],
            min_heat_score=result["min_heat_score"],
            points=point_models,
        ),
        message=f"Heatmap generated with {result['total_points']} region points.",
    )


# ──────────────────────────────────────────────────────────────────────────
# GET /top_risk_regions
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/top_risk_regions",
    response_model=TopRiskRegionsResponse,
    summary="Ranked list of highest-risk agricultural regions",
)
async def top_risk_regions_endpoint(
    limit: int = Query(10, ge=1, le=100, description="Number of top regions to return."),
) -> TopRiskRegionsResponse:
    """
    Returns regions ranked by average risk score, with disease counts
    and top disease names.
    """
    if not analytics_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics engine not initialised.",
        )

    try:
        result = analytics_service.get_top_risk_regions(limit=limit)
    except Exception as exc:
        logger.error("Top risk regions error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rank regions: {exc}",
        )

    ranked_models = [RankedRegion(**r) for r in result["top_regions"]]

    return TopRiskRegionsResponse(
        success=True,
        data=TopRiskRegionsData(
            total_regions_analysed=result["total_regions_analysed"],
            top_regions=ranked_models,
        ),
        message=f"Top {len(ranked_models)} risk regions out of {result['total_regions_analysed']}.",
    )


# ──────────────────────────────────────────────────────────────────────────
# GET /outbreak_trends
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/outbreak_trends",
    response_model=OutbreakTrendsResponse,
    summary="Outbreak trend analysis over time",
)
async def outbreak_trends_endpoint(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyse."),
) -> OutbreakTrendsResponse:
    """
    Analyses outbreak patterns over the requested period, producing
    per-disease and per-region timelines with trend direction indicators.
    """
    if not analytics_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics engine not initialised.",
        )

    try:
        result = analytics_service.get_outbreak_trends(days=days)
    except Exception as exc:
        logger.error("Outbreak trends error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyse trends: {exc}",
        )

    disease_models = [
        DiseaseTrend(
            disease=d["disease"],
            total_reports=d["total_reports"],
            trend_direction=d["trend_direction"],
            change_pct=d["change_pct"],
            timeline=[TrendPoint(**t) for t in d["timeline"]],
        )
        for d in result["disease_trends"]
    ]

    region_models = [
        RegionTrend(
            region=r["region"],
            total_reports=r["total_reports"],
            trend_direction=r["trend_direction"],
            change_pct=r["change_pct"],
            timeline=[TrendPoint(**t) for t in r["timeline"]],
        )
        for r in result["region_trends"]
    ]

    return OutbreakTrendsResponse(
        success=True,
        data=OutbreakTrendsData(
            analysis_period_days=result["analysis_period_days"],
            overall_trend=result["overall_trend"],
            overall_change_pct=result["overall_change_pct"],
            disease_trends=disease_models,
            region_trends=region_models,
        ),
        message=(
            f"Trend analysis over {result['analysis_period_days']} days — "
            f"overall direction: {result['overall_trend']}."
        ),
    )
