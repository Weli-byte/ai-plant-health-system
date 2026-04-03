# =============================================================================
# schemas/plant.py
# Bu dosya Plant (bitki) modeli için Pydantic şemalarını tanımlar.
# API isteklerinde veri doğrulama ve yanıt serileştirme için kullanılır.
# =============================================================================

from pydantic import BaseModel, Field
from datetime import datetime


# -----------------------------------------------------------------------------
# PlantBase: Tüm Plant şemalarının paylaştığı ortak alanlar
# -----------------------------------------------------------------------------
class PlantBase(BaseModel):
    plant_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Bitkinin adı (örn: 'Domates', 'Elma Ağacı')"
    )


# -----------------------------------------------------------------------------
# PlantCreate: Yeni bitki eklemek için kullanılır (POST /plants)
# user_id route üzerinden veya authentication'dan gelecek, body'de alınmaz.
# -----------------------------------------------------------------------------
class PlantCreate(PlantBase):
    user_id: int = Field(
        ...,
        description="Bitkinin sahibi olan kullanıcının ID'si"
    )


# -----------------------------------------------------------------------------
# PlantResponse: API'den bitki verisi döndürülürken kullanılır (GET /plants)
# -----------------------------------------------------------------------------
class PlantResponse(PlantBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy nesnelerinden doğrudan okuma
