"""
app/routes/model_updates.py
============================
Sprint 4 — Automated Retraining Infrastructure REST endpoints.

    POST /api/v2/update_model     — queue / start a new model training job.
    GET  /api/v2/training_status  — live tracking of training pipeline.
    GET  /api/v2/training_history — history of all completed jobs.
    GET  /api/v2/model_versions   — list of all registered checkpoints.
    POST /api/v2/rollback_model   — revert active model to a previous version.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.model_update_schemas import (
    UpdateModelRequest,
    UpdateModelResponse,
    TrainingJobInfo,
    TrainingStatusResponse,
    LiveTrainingStatus,
    TrainingHistoryResponse,
    TrainingHistoryData,
    TrainingHistoryEntry,
    ModelVersionsResponse,
    ModelVersionsData,
    ModelVersionDetail,
    RollbackModelRequest,
    RollbackModelResponse,
    RollbackResult,
)
from app.services.model_update_service import model_update_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["MLOps Lifecycle — Sprint 4"],
)


@router.post(
    "/update_model",
    response_model=UpdateModelResponse,
    summary="Start an automated model retraining job",
)
async def update_model_endpoint(request: UpdateModelRequest) -> UpdateModelResponse:
    """Trigger a background training job for a specific model."""
    try:
        result = model_update_service.update_model(
            model_name=request.model_name,
            epochs=request.epochs,
            learning_rate=request.learning_rate,
            batch_size=request.batch_size,
            notes=request.notes,
            force=request.force,
        )
    except Exception as exc:
        logger.error("Update model error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training: {exc}",
        )

    job_info = TrainingJobInfo(
        job_id=result["job_id"],
        model_name=result["model_name"],
        status=result["status"],
        total_epochs=result.get("total_epochs", 0),
    )

    msg = "Training job queued/started." if result["status"] != "running" else "A job is already running."

    return UpdateModelResponse(
        success=True,
        data=job_info,
        message=msg,
    )


@router.get(
    "/training_status",
    response_model=TrainingStatusResponse,
    summary="Get live training status and queue info",
)
async def training_status_endpoint() -> TrainingStatusResponse:
    try:
        result = model_update_service.get_training_status()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status: {exc}",
        )

    job_model = TrainingJobInfo(**result["current_job"]) if result.get("current_job") else None

    return TrainingStatusResponse(
        success=True,
        data=LiveTrainingStatus(
            training_active=result["training_active"],
            current_job=job_model,
            queue_length=result["queue_length"],
            total_completed_jobs=result["total_completed_jobs"],
            total_model_versions=result["total_model_versions"],
            last_training_date=result["last_training_date"],
        ),
        message="Live status retrieved.",
    )


@router.get(
    "/training_history",
    response_model=TrainingHistoryResponse,
    summary="Get full history of model training runs",
)
async def training_history_endpoint() -> TrainingHistoryResponse:
    try:
        result = model_update_service.get_training_history()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {exc}",
        )

    entries = [TrainingHistoryEntry(**h) for h in result["history"]]

    return TrainingHistoryResponse(
        success=True,
        data=TrainingHistoryData(
            total_runs=result["total_runs"],
            history=entries,
        ),
        message=f"Retrieved {result['total_runs']} historical runs.",
    )


@router.get(
    "/model_versions",
    response_model=ModelVersionsResponse,
    summary="List all registered model versions",
)
async def model_versions_endpoint() -> ModelVersionsResponse:
    try:
        result = model_update_service.get_model_versions()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve versions: {exc}",
        )

    active = ModelVersionDetail(**result["active_version"]) if result.get("active_version") else None
    versions = [ModelVersionDetail(**v) for v in result["versions"]]

    return ModelVersionsResponse(
        success=True,
        data=ModelVersionsData(
            total_versions=result["total_versions"],
            active_version=active,
            versions=versions,
        ),
        message=f"Retrieved {result['total_versions']} versions.",
    )


@router.post(
    "/rollback_model",
    response_model=RollbackModelResponse,
    summary="Rollback to a previous model checkpoint",
)
async def rollback_model_endpoint(request: RollbackModelRequest) -> RollbackModelResponse:
    try:
        result = model_update_service.rollback_model(
            target_version_id=request.target_version_id,
            reason=request.reason,
        )
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

    return RollbackModelResponse(
        success=True,
        data=RollbackResult(**result),
        message=f"Rolled back to {result['new_active']}.",
    )
