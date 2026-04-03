# =============================================================================
# schemas/disease_record.py
# Bu dosya DiseaseRecord modeli için Pydantic şemalarını tanımlar.
# Sprint 2'de AI entegrasyonu tamamlandığında bu şemalar genişletilecek.
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# -----------------------------------------------------------------------------
# DiseaseRecordBase: Tüm DiseaseRecord şemalarının paylaştığı ortak alanlar
# -----------------------------------------------------------------------------
class DiseaseRecordBase(BaseModel):
    disease_name: str = Field(
        ...,
        max_length=200,
        description="Tespit edilen hastalığın adı (örn: 'Powdery Mildew')"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,   # "greater than or equal to" 0.0
        le=1.0,   # "less than or equal to" 1.0
        description="AI güven skoru: 0.0 (düşük) ile 1.0 (yüksek) arasında"
    )


# -----------------------------------------------------------------------------
# DiseaseRecordCreate: Yeni hastalık kaydı oluşturmak için (POST /disease-records)
# -----------------------------------------------------------------------------
class DiseaseRecordCreate(DiseaseRecordBase):
    plant_id: int = Field(
        ...,
        description="Hastalığın tespit edildiği bitkinin ID'si"
    )


# -----------------------------------------------------------------------------
# DiseaseRecordResponse: API'den veri döndürülürken kullanılır
# -----------------------------------------------------------------------------
class DiseaseRecordResponse(DiseaseRecordBase):
    id: int
    plant_id: int
    created_at: datetime

    class Config:
        from_attributes = True
