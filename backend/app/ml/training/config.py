"""
app/ml/training/config.py
=========================
Hyperparameter schemas and configurations for the AI Training Pipeline.
"""

from typing import Optional
from pydantic import BaseModel, Field

class TrainingConfig(BaseModel):
    model_name: str = Field(..., description="efficientnet or yolov8")
    epochs: int = Field(10, ge=1, le=500)
    batch_size: int = Field(32, ge=1, le=256)
    learning_rate: float = Field(0.001, gt=0, le=1.0)
    mixed_precision: bool = Field(True, description="Use AMP if available")
    device: str = Field("auto", description="cpu, cuda, or auto")
    val_split: float = Field(0.2, ge=0.05, le=0.5)
    
    # EfficientNet specific
    num_classes: Optional[int] = None
    
    # YOLO specific
    yolo_img_size: int = Field(640, description="Image size for YOLO training")
