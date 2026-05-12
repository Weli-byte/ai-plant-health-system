"""
app/schemas/dataset_schemas.py
==============================
Pydantic v2 schemas for the External Dataset Management System.

Endpoints:
    GET /dataset/sample_images
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class DatasetValidationDetail(BaseModel):
    """Details about dataset structure."""
    
    is_valid: bool
    path: str
    total_classes: int = 0
    total_images: int = 0
    classes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class SampleImage(BaseModel):
    """Details of a single sample image from the dataset."""

    class_name: str
    image_path: str


# ---------------------------------------------------------------------------
# Sample Images Endpoint
# ---------------------------------------------------------------------------

class SampleImagesData(BaseModel):
    """Inner data block for sample images endpoint."""

    validation: DatasetValidationDetail
    samples: List[SampleImage] = Field(default_factory=list)


class SampleImagesResponse(BaseModel):
    """Envelope for GET /dataset/sample_images."""

    success: bool = True
    data: Optional[SampleImagesData] = None
    message: str = ""
