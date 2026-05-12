"""
app/schemas/analytics_schemas.py
=================================
Pydantic v2 schemas for the **Regional Analytics Engine** endpoints.

Endpoints:
    GET /api/v2/regional_statistics
    GET /api/v2/disease_heatmap
    GET /api/v2/top_risk_regions
    GET /api/v2/outbreak_trends

Sprint 4 — Regional Analytics Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / reusable
# ---------------------------------------------------------------------------

class DiseaseCount(BaseModel):
    """Disease name + occurrence count."""

    disease: str
    count: int
    percentage: float = Field(..., ge=0.0, le=100.0)


class EnvironmentalAverage(BaseModel):
    """Averaged environmental readings for a region."""

    avg_humidity: float
    avg_temperature: float
    avg_rainfall: float


# ---------------------------------------------------------------------------
# Regional Statistics
# ---------------------------------------------------------------------------

class RegionSummary(BaseModel):
    """Per-region digest in the regional statistics response."""

    region: str
    latitude: float
    longitude: float
    total_reports: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity_index: float = Field(..., ge=0.0, le=1.0)
    dominant_disease: str
    dominant_crop: str
    disease_distribution: List[DiseaseCount] = Field(default_factory=list)
    environment: Optional[EnvironmentalAverage] = None


class RegionalStatisticsData(BaseModel):
    """Inner ``data`` block for the regional_statistics endpoint."""

    total_regions: int
    total_reports: int
    overall_avg_risk: float
    overall_avg_severity: float
    regions: List[RegionSummary] = Field(default_factory=list)
    disease_overview: List[DiseaseCount] = Field(default_factory=list)


class RegionalStatisticsResponse(BaseModel):
    """Envelope for GET /regional_statistics."""

    success: bool = True
    data: Optional[RegionalStatisticsData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

class HeatmapPoint(BaseModel):
    """Single point in the heatmap output — map-visualisation-ready."""

    region: str
    latitude: float
    longitude: float
    heat_score: float = Field(..., ge=0.0, le=100.0)
    outbreak_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    report_count: int
    dominant_disease: str


class HeatmapData(BaseModel):
    """Inner ``data`` block for the disease_heatmap endpoint."""

    total_points: int
    max_heat_score: float
    min_heat_score: float
    points: List[HeatmapPoint] = Field(default_factory=list)


class HeatmapResponse(BaseModel):
    """Envelope for GET /disease_heatmap."""

    success: bool = True
    data: Optional[HeatmapData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Top Risk Regions
# ---------------------------------------------------------------------------

class RankedRegion(BaseModel):
    """A region entry in the ranked risk list."""

    rank: int
    region: str
    latitude: float
    longitude: float
    risk_score: float = Field(..., ge=0.0, le=100.0)
    disease_count: int
    outbreak_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    top_diseases: List[str] = Field(default_factory=list)


class TopRiskRegionsData(BaseModel):
    """Inner ``data`` block for the top_risk_regions endpoint."""

    total_regions_analysed: int
    top_regions: List[RankedRegion] = Field(default_factory=list)


class TopRiskRegionsResponse(BaseModel):
    """Envelope for GET /top_risk_regions."""

    success: bool = True
    data: Optional[TopRiskRegionsData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Outbreak Trends
# ---------------------------------------------------------------------------

class TrendPoint(BaseModel):
    """One data point in an outbreak trend timeline."""

    date: str
    report_count: int
    avg_severity: float
    avg_risk_score: float


class DiseaseTrend(BaseModel):
    """Per-disease trend with direction indicator."""

    disease: str
    total_reports: int
    trend_direction: Literal["increasing", "stable", "decreasing"]
    change_pct: float
    timeline: List[TrendPoint] = Field(default_factory=list)


class RegionTrend(BaseModel):
    """Per-region outbreak trend."""

    region: str
    total_reports: int
    trend_direction: Literal["increasing", "stable", "decreasing"]
    change_pct: float
    timeline: List[TrendPoint] = Field(default_factory=list)


class OutbreakTrendsData(BaseModel):
    """Inner ``data`` block for the outbreak_trends endpoint."""

    analysis_period_days: int
    overall_trend: Literal["increasing", "stable", "decreasing"]
    overall_change_pct: float
    disease_trends: List[DiseaseTrend] = Field(default_factory=list)
    region_trends: List[RegionTrend] = Field(default_factory=list)


class OutbreakTrendsResponse(BaseModel):
    """Envelope for GET /outbreak_trends."""

    success: bool = True
    data: Optional[OutbreakTrendsData] = None
    message: str = ""
