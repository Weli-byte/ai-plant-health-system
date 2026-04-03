# =============================================================================
# routes/disease_records.py
# Bu dosya hastalık kayıtları (DiseaseRecord) ile ilgili endpointleri tanımlar.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.disease_record import DiseaseRecord
from app.models.plant import Plant
from app.schemas.disease_record import DiseaseRecordCreate, DiseaseRecordResponse

router = APIRouter(
    prefix="/disease-records",
    tags=["Disease Records"]
)


@router.post(
    "/",
    response_model=DiseaseRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni hastalık kaydı oluştur",
    description=(
        "Bir bitkiye ait hastalık tespiti kaydını oluşturur. "
        "Sprint 2'de AI modeli bu endpoint'i otomatik olarak çağıracak."
    )
)
def create_disease_record(
    record_data: DiseaseRecordCreate,
    db: Session = Depends(get_db)
):
    """Yeni bir hastalık kaydı oluşturur."""

    # Bitkinin var olduğunu doğrula
    plant = db.query(Plant).filter(Plant.id == record_data.plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={record_data.plant_id} olan bitki bulunamadı."
        )

    new_record = DiseaseRecord(
        plant_id=record_data.plant_id,
        disease_name=record_data.disease_name,
        confidence_score=record_data.confidence_score,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record


@router.get(
    "/plant/{plant_id}",
    response_model=list[DiseaseRecordResponse],
    summary="Bir bitkinin tüm hastalık kayıtlarını getir"
)
def get_disease_records_by_plant(plant_id: int, db: Session = Depends(get_db)):
    """Belirli bir bitkiye ait tüm hastalık kayıtlarını döndürür."""

    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={plant_id} olan bitki bulunamadı."
        )

    records = (
        db.query(DiseaseRecord)
        .filter(DiseaseRecord.plant_id == plant_id)
        .order_by(DiseaseRecord.created_at.desc())  # Yeniden eskiye sırala
        .all()
    )
    return records
