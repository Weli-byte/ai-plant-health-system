# =============================================================================
# routes/analysis_records.py
# Kullanıcıya ait AI analiz kayıtları için CRUD endpoint'leri.
# =============================================================================

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.analysis_record import AnalysisRecord
from app.schemas.analysis_record import AnalysisRecordCreate, AnalysisRecordResponse

router = APIRouter(prefix="/analyses", tags=["Analysis Records"])


@router.post(
    "/",
    response_model=AnalysisRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni analiz kaydı oluştur",
)
def create_analysis_record(data: AnalysisRecordCreate, db: Session = Depends(get_db)):
    """Vision AI analiz sonucunu veritabanına kaydeder."""
    record = AnalysisRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/",
    response_model=list[AnalysisRecordResponse],
    summary="Kullanıcının tüm analizlerini getir",
)
def get_analyses_by_email(
    email: str = Query(..., description="Kullanıcının e-posta adresi"),
    db: Session = Depends(get_db),
):
    """E-posta adresine göre kullanıcının analizlerini yeniden eskiye sıralı döndürür."""
    return (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_email == email)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )
