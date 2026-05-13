# =============================================================================
# schemas/plant.py
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class PlantBase(BaseModel):
    plant_name: str = Field(..., min_length=1, max_length=100, description="Bitkinin tam adı")


class PlantCreate(PlantBase):
    user_id: int = Field(..., description="Bitkinin sahibi olan kullanıcının ID'si")
    plant_type: Optional[str] = None
    plant_emoji: Optional[str] = None
    planting_date: Optional[str] = None
    location: Optional[str] = None
    growth_stage: Optional[str] = None
    irrigation_method: Optional[str] = None
    irrigation_frequency: Optional[str] = None
    area_size: Optional[float] = None
    notes: Optional[str] = None


class PlantResponse(PlantBase):
    id: int
    user_id: int
    created_at: datetime
    plant_type: Optional[str] = None
    plant_emoji: Optional[str] = None
    planting_date: Optional[str] = None
    location: Optional[str] = None
    growth_stage: Optional[str] = None
    irrigation_method: Optional[str] = None
    irrigation_frequency: Optional[str] = None
    area_size: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
