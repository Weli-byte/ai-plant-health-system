# =============================================================================
# schemas/analysis_record.py
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AnalysisRecordCreate(BaseModel):
    user_email: str = Field(..., description="Kullanıcının e-posta adresi")
    disease_name_tr: str = Field(..., description="Hastalık adı Türkçe")
    disease_name_en: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_level: Optional[int] = Field(None, ge=1, le=5)
    pathogen_type: Optional[str] = None
    spread_risk: Optional[str] = None
    affected_percentage: Optional[int] = Field(None, ge=0, le=100)
    enrichment_json: Optional[str] = Field(None, description="DiseaseEnrichment JSON string")


class AnalysisRecordResponse(AnalysisRecordCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
