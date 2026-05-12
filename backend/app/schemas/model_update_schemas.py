"""
app/schemas/model_update_schemas.py
=====================================
Pydantic v2 schemas for the **Automated Retraining Infrastructure**.

Endpoints:
    POST /api/v2/update_model
    GET  /api/v2/training_status
    GET  /api/v2/training_history
    GET  /api/v2/model_versions
    POST /api/v2/rollback_model

Sprint 4 — MLOps Lifecycle Management.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Update Model (POST /update_model)
# ---------------------------------------------------------------------------

class UpdateModelRequest(BaseModel):
    """Request payload to start a model update / retraining job."""

    model_name: str = Field(
        "efficientnet",
        description="Target model identifier (efficientnet, risk, gnn).",
    )
    epochs: int = Field(20, ge=1, le=500, description="Number of training epochs.")
    learning_rate: float = Field(1e-4, gt=0, le=1.0, description="Learning rate.")
    batch_size: int = Field(32, ge=1, le=512, description="Training batch size.")
    notes: str = Field("", description="Free-text annotation for this training run.")
    force: bool = Field(False, description="Force start even if a job is running.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_name": "efficientnet",
                "epochs": 40,
                "learning_rate": 0.0001,
                "batch_size": 32,
                "notes": "Weekly scheduled retraining",
                "force": False,
            }
        }
    }


class EpochMetrics(BaseModel):
    """Metrics snapshot for a single training epoch."""

    epoch: int
    train_loss: float
    val_loss: float
    train_accuracy: float
    val_accuracy: float
    learning_rate: float
    timestamp: str


class TrainingJobInfo(BaseModel):
    """Summary of a launched / completed training job."""

    job_id: str
    model_name: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_epochs: int = 0
    current_epoch: int = 0
    current_loss: Optional[float] = None
    current_accuracy: Optional[float] = None
    model_version: Optional[str] = None


class UpdateModelResponse(BaseModel):
    """Envelope for POST /update_model."""

    success: bool = True
    data: Optional[TrainingJobInfo] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Training Status (GET /training_status)
# ---------------------------------------------------------------------------

class LiveTrainingStatus(BaseModel):
    """Real-time training pipeline status."""

    training_active: bool = False
    current_job: Optional[TrainingJobInfo] = None
    queue_length: int = 0
    total_completed_jobs: int = 0
    total_model_versions: int = 0
    last_training_date: Optional[str] = None


class TrainingStatusResponse(BaseModel):
    """Envelope for GET /training_status."""

    success: bool = True
    data: Optional[LiveTrainingStatus] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Training History (GET /training_history)
# ---------------------------------------------------------------------------

class TrainingHistoryEntry(BaseModel):
    """A single completed training run record."""

    job_id: str
    model_name: str
    model_version: str
    status: str
    started_at: str
    completed_at: str
    total_epochs: int
    final_train_loss: float
    final_val_loss: float
    final_accuracy: float
    best_accuracy: float
    best_epoch: int
    learning_rate: float
    batch_size: int
    dataset_size: int
    notes: str = ""
    epoch_metrics: List[EpochMetrics] = Field(default_factory=list)


class TrainingHistoryData(BaseModel):
    """Inner data block for training_history response."""

    total_runs: int
    history: List[TrainingHistoryEntry] = Field(default_factory=list)


class TrainingHistoryResponse(BaseModel):
    """Envelope for GET /training_history."""

    success: bool = True
    data: Optional[TrainingHistoryData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Model Versions (GET /model_versions)
# ---------------------------------------------------------------------------

class ModelVersionDetail(BaseModel):
    """Detailed model version record."""

    version_id: str
    model_version: str
    model_name: str
    created_at: str
    status: Literal["ACTIVE", "INACTIVE", "ROLLED_BACK"]
    accuracy: float
    loss: float
    epochs_trained: int
    checkpoint_path: str
    dataset_size: int
    training_job_id: str
    notes: str = ""


class ModelVersionsData(BaseModel):
    """Inner data block for model_versions response."""

    total_versions: int
    active_version: Optional[ModelVersionDetail] = None
    versions: List[ModelVersionDetail] = Field(default_factory=list)


class ModelVersionsResponse(BaseModel):
    """Envelope for GET /model_versions."""

    success: bool = True
    data: Optional[ModelVersionsData] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Rollback (POST /rollback_model)
# ---------------------------------------------------------------------------

class RollbackModelRequest(BaseModel):
    """Request to rollback to a specific model version."""

    target_version_id: str = Field(
        ..., min_length=1,
        description="Version ID to rollback to.",
    )
    reason: str = Field("", description="Reason for the rollback.")


class RollbackResult(BaseModel):
    """Rollback operation result."""

    previous_active: Optional[str] = None
    new_active: str
    rolled_back_at: str
    reason: str = ""


class RollbackModelResponse(BaseModel):
    """Envelope for POST /rollback_model."""

    success: bool = True
    data: Optional[RollbackResult] = None
    message: str = ""
