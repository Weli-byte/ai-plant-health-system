# =============================================================================
# models/analysis_record.py
# Kullanıcıya ait AI analiz kayıtlarını saklar.
# plant_id bağımlılığı yok; user_email ile kullanıcıya bağlıdır.
# =============================================================================

from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func

from app.database.connection import Base


class AnalysisRecord(Base):
    """Tam AI analizi sonuçlarını kullanıcıya bağlı olarak saklar."""

    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_email = Column(String(255), nullable=False, index=True)
    disease_name_tr = Column(String(300), nullable=False, default="Bilinmiyor")
    disease_name_en = Column(String(300), nullable=True)
    confidence_score = Column(Float, nullable=True)
    risk_level = Column(Integer, nullable=True)
    pathogen_type = Column(String(50), nullable=True)
    spread_risk = Column(String(20), nullable=True)
    affected_percentage = Column(Integer, nullable=True)
    enrichment_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AnalysisRecord(id={self.id}, email={self.user_email}, disease='{self.disease_name_tr}')>"
