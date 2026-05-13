# =============================================================================
# models/plant.py
# =============================================================================

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Sprint 3+ — bitki detayları
    plant_type = Column(String(100), nullable=True)
    plant_emoji = Column(String(10), nullable=True)
    planting_date = Column(String(20), nullable=True)   # ISO date string "2026-04-15"
    location = Column(String(200), nullable=True)
    growth_stage = Column(String(50), nullable=True)    # seedling/vegetative/flowering/fruiting/harvest
    irrigation_method = Column(String(50), nullable=True)
    irrigation_frequency = Column(String(50), nullable=True)
    area_size = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    owner = relationship("User", back_populates="plants")
    disease_records = relationship("DiseaseRecord", back_populates="plant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plant(id={self.id}, name='{self.plant_name}', user_id={self.user_id})>"
