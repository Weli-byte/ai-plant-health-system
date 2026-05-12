"""
app/schemas/global_risk_schemas.py
===================================
Pydantic v2 schemas for the **Global Disease Spread Analysis** endpoint.

Endpoint: ``POST /api/v2/global_risk_analysis``

Sprint 4 — Week 1.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.ml.global_gnn_model import CROP_TYPES, DISEASE_TYPES


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DiseaseReportInput(BaseModel):
    """A single geo-located disease observation from the field."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS latitude.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS longitude.")
    disease_type: str = Field(..., description="Detected disease name.")
    humidity: float = Field(50.0, ge=0.0, le=100.0, description="Relative humidity (%).")
    temperature: float = Field(20.0, ge=-30.0, le=60.0, description="Air temperature (°C).")
    rainfall: float = Field(0.0, ge=0.0, le=500.0, description="Daily rainfall (mm).")
    crop_type: str = Field("tomato", description="Crop species.")
    timestamp: str = Field("", description="ISO-8601 observation timestamp.")
    severity_score: float = Field(0.5, ge=0.0, le=1.0, description="Disease severity 0–1.")

    @field_validator("disease_type")
    @classmethod
    def _check_disease(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key not in DISEASE_TYPES:
            raise ValueError(f"Invalid disease_type '{v}'. Expected one of {DISEASE_TYPES}.")
        return key

    @field_validator("crop_type")
    @classmethod
    def _check_crop(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key not in CROP_TYPES:
            raise ValueError(f"Invalid crop_type '{v}'. Expected one of {CROP_TYPES}.")
        return key


class AnalysisConfig(BaseModel):
    """Optional tuning parameters for graph construction."""

    cluster_radius_km: float = Field(
        5.0, ge=0.5, le=100.0,
        description="DBSCAN epsilon radius in km for spatial clustering.",
    )
    min_reports_per_cluster: int = Field(
        2, ge=1, le=50,
        description="Minimum reports to form a region node.",
    )
    edge_distance_threshold_km: float = Field(
        15.0, ge=1.0, le=500.0,
        description="Max inter-centroid distance (km) to create an edge.",
    )


class GlobalRiskAnalysisRequest(BaseModel):
    """Top-level request payload."""

    reports: List[DiseaseReportInput] = Field(
        ..., min_length=1,
        description="List of disease report observations.",
    )
    analysis_config: Optional[AnalysisConfig] = Field(
        default=None,
        description="Optional graph-construction parameters.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "reports": [
                    {
                        "latitude": 39.92,
                        "longitude": 32.85,
                        "disease_type": "powdery_mildew",
                        "humidity": 78.5,
                        "temperature": 24.0,
                        "rainfall": 12.0,
                        "crop_type": "tomato",
                        "timestamp": "2026-05-10T14:30:00Z",
                        "severity_score": 0.72,
                    },
                    {
                        "latitude": 39.94,
                        "longitude": 32.87,
                        "disease_type": "leaf_blight",
                        "humidity": 82.0,
                        "temperature": 26.5,
                        "rainfall": 18.0,
                        "crop_type": "grape",
                        "timestamp": "2026-05-10T15:00:00Z",
                        "severity_score": 0.85,
                    },
                ],
                "analysis_config": {
                    "cluster_radius_km": 5.0,
                    "min_reports_per_cluster": 2,
                    "edge_distance_threshold_km": 15.0,
                },
            }
        }
    }


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class EnvironmentalSummary(BaseModel):
    """Aggregated weather / severity stats for a region."""

    avg_humidity: float = Field(..., ge=0.0, le=100.0)
    avg_temperature: float = Field(..., ge=-30.0, le=60.0)
    avg_rainfall: float = Field(..., ge=0.0)
    avg_severity: float = Field(..., ge=0.0, le=1.0)


class RegionResult(BaseModel):
    """Prediction output for a single geographic region (graph node)."""

    region_id: str
    center_lat: float
    center_lng: float
    num_reports: int
    dominant_disease: str
    dominant_crop: str
    regional_risk_score: float = Field(..., ge=0.0, le=100.0)
    outbreak_probability: float = Field(..., ge=0.0, le=1.0)
    disease_heat_level: Literal["low", "medium", "high", "critical"]
    nearby_regions_at_risk: List[str] = Field(default_factory=list)
    environmental_summary: EnvironmentalSummary


class GraphSummary(BaseModel):
    """High-level topology summary of the constructed graph."""

    num_nodes: int
    num_edges: int
    avg_node_degree: float


class GlobalRiskAnalysisData(BaseModel):
    """Inner ``data`` block of the success envelope."""

    analysis_id: str
    total_reports_processed: int
    total_regions_identified: int
    graph_summary: GraphSummary
    regions: List[RegionResult]
    model_version: str
    inference_device: str


class GlobalRiskAnalysisResponse(BaseModel):
    """Standard success envelope: ``{success, data, message}``."""

    success: bool = True
    data: Optional[GlobalRiskAnalysisData] = None
    message: str = ""


class GlobalRiskErrorEnvelope(BaseModel):
    """Standard error envelope."""

    success: bool = False
    data: Optional[Any] = None
    message: str
