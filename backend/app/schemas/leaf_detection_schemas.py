"""
app/schemas/leaf_detection_schemas.py
=====================================
Pydantic schemas for the /detect_leaf endpoint.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class LeafDetectionResponse(BaseModel):
    """Detection output schema for successful API response."""
    success: bool = Field(True, description="Indicates if the operation was successful")
    boxes: List[List[float]] = Field(
        ..., 
        description="List of [x1, y1, x2, y2] coordinates for each detected leaf"
    )
    scores: List[float] = Field(
        ..., 
        description="Confidence scores (0.0 to 1.0) for each detection"
    )
    classes: List[str] = Field(
        ..., 
        description="Class labels for each detection (usually 'leaf')"
    )
    count: int = Field(0, description="Total number of leaves detected in the image")
    message: Optional[str] = Field(None, description="Optional status or error message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "boxes": [[120.5, 200.1, 450.2, 600.8]],
                "scores": [0.94],
                "classes": ["leaf"],
                "count": 1,
                "message": "Detection completed successfully."
            }
        }
    }

class ErrorResponse(BaseModel):
    """Standard error schema for failed detection or missing model."""
    success: bool = Field(False, description="Always False for error responses")
    message: str = Field(..., description="Details about the failure")
