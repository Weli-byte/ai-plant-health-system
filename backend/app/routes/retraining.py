"""
app/routes/retraining.py
=========================
Sprint 4 — Continual Learning API endpoints.

    POST /api/v2/submit_feedback       — submit user correction for a prediction.
    POST /api/v2/trigger_retraining    — evaluate triggers & start retraining.
    GET  /api/v2/model_versions        — list all model versions.
    GET  /api/v2/training_status       — current pipeline status.
    POST /api/v2/rollback_model        — rollback to a previous version.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.retraining_schemas import (
    FeedbackRequest,
    FeedbackResponse,
    FeedbackData,
    RetrainingTriggerRequest,
    RetrainingResponse,
    RetrainingJobData,
    TriggerEvaluation,
    ModelVersionsResponse,
    ModelVersionsData,
    ModelVersionEntry,
    TrainingStatusResponse,
    TrainingStatusData,
    BufferStats,
    RollbackRequest,
    RollbackResponse,
)
from app.services.retraining_service import retraining_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["Continual Learning — Sprint 4"],
)


# ──────────────────────────────────────────────────────────────────────────
# POST /submit_feedback
# ──────────────────────────────────────────────────────────────────────────

@router.post(
    "/submit_feedback",
    response_model=FeedbackResponse,
    summary="Submit user feedback (correction) for a prediction",
    responses={
        200: {"description": "Feedback accepted."},
        400: {"description": "Invalid input data."},
    },
)
async def submit_feedback_endpoint(
    request: FeedbackRequest,
) -> FeedbackResponse:
    """
    Accepts a user-verified correction for a model prediction.

    The sample is stored in both the **replay buffer** (for future
    experience-replay retraining) and the **persistent dataset** (for
    incremental dataset growth).
    """
    try:
        result = retraining_service.submit_feedback(request.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Feedback submission error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {exc}",
        )

    correct_str = "correct" if result["is_correct"] else "incorrect"

    return FeedbackResponse(
        success=True,
        data=FeedbackData(**result),
        message=(
            f"Feedback recorded (prediction was {correct_str}). "
            f"Pending samples: {result['pending_samples']}."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────
# POST /trigger_retraining
# ──────────────────────────────────────────────────────────────────────────

@router.post(
    "/trigger_retraining",
    response_model=RetrainingResponse,
    summary="Evaluate retraining triggers and start a training job",
    responses={
        200: {"description": "Trigger evaluation + job status."},
        409: {"description": "A training job is already running."},
    },
)
async def trigger_retraining_endpoint(
    request: RetrainingTriggerRequest,
) -> RetrainingResponse:
    """
    Evaluates whether retraining thresholds are met. If so (or if
    ``force=True``), queues a simulated retraining job that runs in a
    background thread.
    """
    try:
        result = retraining_service.trigger_retraining(
            force=request.force,
            replay_ratio=request.replay_ratio,
            notes=request.notes,
        )
    except Exception as exc:
        logger.error("Retraining trigger error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining trigger failed: {exc}",
        )

    trigger_eval = None
    if result.get("trigger_evaluation"):
        trigger_eval = TriggerEvaluation(**result["trigger_evaluation"])

    job_status = result.get("status", "skipped")
    msg_map = {
        "skipped": "Retraining thresholds not met — no action taken.",
        "queued": f"Retraining job queued (id={result.get('job_id', '')}).",
        "running": "A training job is already in progress.",
    }

    return RetrainingResponse(
        success=True,
        data=RetrainingJobData(
            job_id=result.get("job_id", ""),
            status=job_status,
            trigger_evaluation=trigger_eval,
            new_version=result.get("new_version"),
        ),
        message=msg_map.get(job_status, f"Retraining status: {job_status}"),
    )


# ──────────────────────────────────────────────────────────────────────────
# GET /model_versions
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/model_versions",
    response_model=ModelVersionsResponse,
    summary="List all model versions with active indicator",
)
async def model_versions_endpoint() -> ModelVersionsResponse:
    """Return the full version registry, newest first."""
    try:
        result = retraining_service.get_model_versions()
    except Exception as exc:
        logger.error("Model versions error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model versions: {exc}",
        )

    active_entry = None
    if result.get("active_version"):
        active_entry = ModelVersionEntry(**result["active_version"])

    version_entries = [
        ModelVersionEntry(**v) for v in result.get("versions", [])
    ]

    return ModelVersionsResponse(
        success=True,
        data=ModelVersionsData(
            total_versions=result["total_versions"],
            active_version=active_entry,
            versions=version_entries,
        ),
        message=f"{result['total_versions']} model version(s) registered.",
    )


# ──────────────────────────────────────────────────────────────────────────
# GET /training_status
# ──────────────────────────────────────────────────────────────────────────

@router.get(
    "/training_status",
    response_model=TrainingStatusResponse,
    summary="Current continual learning pipeline status",
)
async def training_status_endpoint() -> TrainingStatusResponse:
    """
    Returns live status of the training queue, replay buffer, pending
    samples, trigger evaluation, and active model version.
    """
    try:
        result = retraining_service.get_training_status()
    except Exception as exc:
        logger.error("Training status error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve training status: {exc}",
        )

    buf = result.get("buffer_stats")
    buf_model = BufferStats(**buf) if buf else None

    trig = result.get("trigger_evaluation")
    trig_model = TriggerEvaluation(**trig) if trig else None

    status_label = "training" if result["is_training"] else "idle"

    return TrainingStatusResponse(
        success=True,
        data=TrainingStatusData(
            is_training=result["is_training"],
            current_job_id=result.get("current_job_id"),
            pending_samples=result["pending_samples"],
            dataset_total=result["dataset_total"],
            buffer_stats=buf_model,
            trigger_evaluation=trig_model,
            active_model_version=result.get("active_model_version"),
            total_model_versions=result.get("total_model_versions", 0),
        ),
        message=f"Pipeline status: {status_label}.",
    )


# ──────────────────────────────────────────────────────────────────────────
# POST /rollback_model
# ──────────────────────────────────────────────────────────────────────────

@router.post(
    "/rollback_model",
    response_model=RollbackResponse,
    summary="Rollback to a previous model version",
    responses={
        200: {"description": "Rollback successful."},
        404: {"description": "Target version not found."},
    },
)
async def rollback_model_endpoint(
    request: RollbackRequest,
) -> RollbackResponse:
    """Activate a previous model version by its ``version_id``."""
    try:
        result = retraining_service.rollback_model(request.target_version_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Rollback error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {exc}",
        )

    return RollbackResponse(
        success=True,
        data=result,
        message=f"Rolled back to version {result.get('version_id', '')}.",
    )
