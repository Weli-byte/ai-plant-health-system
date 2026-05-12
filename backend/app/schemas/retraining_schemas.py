"""
app/schemas/retraining_schemas.py
==================================
Pydantic v2 schemas for the **Continual Learning** endpoints.

Endpoints:
    POST /api/v2/submit_feedback
    POST /api/v2/trigger_retraining
    GET  /api/v2/model_versions
    GET  /api/v2/training_status

Sprint 4 — Continual Learning System.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Submit Feedback
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    """User-submitted correction for a prediction."""

    image_path: str = Field(
        ..., min_length=1,
        description="Path or identifier of the analysed image.",
    )
    predicted_class: str = Field(
        ..., min_length=1,
        description="The class the model predicted.",
    )
    corrected_class: str = Field(
        ..., min_length=1,
        description="The correct class label provided by the user.",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence for the original prediction.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra metadata (device, location, etc.).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_path": "uploads/leaf_001.jpg",
                "predicted_class": "powdery_mildew",
                "corrected_class": "leaf_blight",
                "confidence": 0.72,
                "metadata": {"source": "mobile_app"},
            }
        }
    }


class FeedbackData(BaseModel):
    """Inner data block for feedback response."""

    sample_id: str
    is_correct: bool
    buffer_size: int
    pending_samples: int
    dataset_total: int


class FeedbackResponse(BaseModel):
    """Standard envelope for submit_feedback."""

    success: bool = True
    data: Optional[FeedbackData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Trigger Retraining
# ---------------------------------------------------------------------------

class RetrainingTriggerRequest(BaseModel):
    """Optional parameters for triggering retraining."""

    force: bool = Field(
        False,
        description="If true, skip threshold checks and force retraining.",
    )
    replay_ratio: float = Field(
        0.3, ge=0.0, le=1.0,
        description="Fraction of replay samples in the training batch.",
    )
    notes: str = Field(
        "",
        description="Free-text note to attach to the new version.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "force": False,
                "replay_ratio": 0.3,
                "notes": "Weekly retrain cycle",
            }
        }
    }


class TriggerEvaluation(BaseModel):
    """Result of the trigger threshold evaluation."""

    should_retrain: bool
    reasons: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class RetrainingJobData(BaseModel):
    """Inner data block for retraining response."""

    job_id: str
    status: Literal["queued", "running", "completed", "skipped", "failed"]
    trigger_evaluation: Optional[TriggerEvaluation] = None
    new_version: Optional[Dict[str, Any]] = None


class RetrainingResponse(BaseModel):
    """Standard envelope for trigger_retraining."""

    success: bool = True
    data: Optional[RetrainingJobData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Model Versions
# ---------------------------------------------------------------------------

class ModelVersionEntry(BaseModel):
    """A single model version record."""

    version_id: str
    version_number: int
    training_date: str
    dataset_size: int
    accuracy: float
    loss: float
    replay_samples_used: int
    new_samples_used: int
    notes: str = ""
    is_active: bool = False
    checkpoint_path: str = ""


class ModelVersionsData(BaseModel):
    """Inner data block for model_versions response."""

    total_versions: int
    active_version: Optional[ModelVersionEntry] = None
    versions: List[ModelVersionEntry] = Field(default_factory=list)


class ModelVersionsResponse(BaseModel):
    """Standard envelope for model_versions."""

    success: bool = True
    data: Optional[ModelVersionsData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Training Status
# ---------------------------------------------------------------------------

class BufferStats(BaseModel):
    """Replay buffer statistics."""

    total_samples: int = 0
    capacity: int = 0
    utilization_pct: float = 0.0
    class_distribution: Dict[str, int] = Field(default_factory=dict)
    accuracy_in_buffer: float = 0.0


class TrainingStatusData(BaseModel):
    """Inner data block for training_status response."""

    is_training: bool = False
    current_job_id: Optional[str] = None
    pending_samples: int = 0
    dataset_total: int = 0
    buffer_stats: Optional[BufferStats] = None
    trigger_evaluation: Optional[TriggerEvaluation] = None
    active_model_version: Optional[str] = None
    total_model_versions: int = 0


class TrainingStatusResponse(BaseModel):
    """Standard envelope for training_status."""

    success: bool = True
    data: Optional[TrainingStatusData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

class RollbackRequest(BaseModel):
    """Request to rollback to a specific version."""

    target_version_id: str = Field(
        ..., min_length=1,
        description="Version ID to rollback to.",
    )


class RollbackResponse(BaseModel):
    """Standard envelope for rollback."""

    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = ""
