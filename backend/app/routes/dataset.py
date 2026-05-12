"""
app/routes/dataset.py
=====================
Sprint 4 — External Dataset Management System REST endpoints.

    GET /api/v2/dataset/sample_images — Retrieves sample images from the external dataset.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.schemas.dataset_schemas import (
    DatasetValidationDetail,
    SampleImage,
    SampleImagesData,
    SampleImagesResponse,
)
from app.services.dataset_service import dataset_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2/dataset",
    tags=["Dataset Integration — Sprint 4"],
)


@router.get(
    "/sample_images",
    response_model=SampleImagesResponse,
    summary="Browse sample images from the external dataset",
    responses={
        200: {"description": "Sample images retrieved successfully."},
        500: {"description": "Dataset configuration error or missing files."},
    },
)
async def sample_images_endpoint(
    limit: int = Query(10, ge=1, le=50, description="Number of samples to retrieve."),
) -> SampleImagesResponse:
    """
    Validates the external dataset configuration and returns random sample 
    images across classes. 
    """
    try:
        validation_info = dataset_service.validate_dataset()
        
        if not validation_info["is_valid"]:
            error_msg = "; ".join(validation_info["errors"])
            raise ValueError(f"Dataset validation failed: {error_msg}")

        samples_raw = dataset_service.get_sample_images(n_samples=limit)
        
        # Convert to Pydantic models
        validation_detail = DatasetValidationDetail(**validation_info)
        sample_models = [SampleImage(**s) for s in samples_raw]

        return SampleImagesResponse(
            success=True,
            data=SampleImagesData(
                validation=validation_detail,
                samples=sample_models,
            ),
            message=f"Successfully retrieved {len(sample_models)} sample images.",
        )

    except ValueError as exc:
        logger.error("Dataset validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Dataset sampling error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dataset samples: {exc}",
        )

@router.get(
    "/image",
    summary="Serve a specific image from the dataset",
    responses={
        200: {"description": "Image served successfully."},
        404: {"description": "Image not found."},
        400: {"description": "Security error - invalid path."},
    },
)
async def get_dataset_image(
    path: str = Query(..., description="Absolute or relative path to the image in the dataset."),
):
    """
    Serves the actual image file to the frontend for demo purposes.
    Ensures the requested file is actually within the dataset directory to prevent path traversal.
    """
    import os
    from pathlib import Path

    try:
        requested_path = Path(path).resolve()
        dataset_path = dataset_service.get_path()

        if not dataset_path:
            raise HTTPException(status_code=500, detail="Dataset path not configured.")

        base_path = dataset_path.resolve()

        # Security check: Ensure requested path is a subpath of dataset base path
        if not str(requested_path).startswith(str(base_path)):
            logger.warning(f"Path traversal attempt: {requested_path}")
            raise HTTPException(status_code=400, detail="Invalid path access.")

        if not requested_path.exists() or not requested_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found.")

        return FileResponse(str(requested_path))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error serving image {path}: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error serving image.")
