# =============================================================================
# routes/plants.py
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.plant import Plant
from app.models.user import User
from app.schemas.plant import PlantCreate, PlantResponse

router = APIRouter(prefix="/plants", tags=["Plants"])


@router.post("/", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
def create_plant(plant_data: PlantCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == plant_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ID={plant_data.user_id} olan kullanıcı bulunamadı.")

    new_plant = Plant(
        plant_name=plant_data.plant_name,
        user_id=plant_data.user_id,
        plant_type=plant_data.plant_type,
        plant_emoji=plant_data.plant_emoji,
        planting_date=plant_data.planting_date,
        location=plant_data.location,
        growth_stage=plant_data.growth_stage,
        irrigation_method=plant_data.irrigation_method,
        irrigation_frequency=plant_data.irrigation_frequency,
        area_size=plant_data.area_size,
        notes=plant_data.notes,
    )
    db.add(new_plant)
    db.commit()
    db.refresh(new_plant)
    return new_plant


@router.get("/", response_model=list[PlantResponse])
def get_all_plants(db: Session = Depends(get_db)):
    return db.query(Plant).all()


@router.get("/user/{user_id}", response_model=list[PlantResponse])
def get_plants_by_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ID={user_id} olan kullanıcı bulunamadı.")
    return db.query(Plant).filter(Plant.user_id == user_id).all()


@router.get("/{plant_id}", response_model=PlantResponse)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ID={plant_id} olan bitki bulunamadı.")
    return plant
