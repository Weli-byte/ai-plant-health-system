# =============================================================================
# routes/plants.py
# Bu dosya bitki (Plant) ile ilgili API endpointlerini tanımlar.
# Sprint 1: Temel CRUD endpointleri oluşturuldu.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.plant import Plant
from app.models.user import User
from app.schemas.plant import PlantCreate, PlantResponse

router = APIRouter(
    prefix="/plants",
    tags=["Plants"]
)


@router.post(
    "/",
    response_model=PlantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni bitki ekle",
    description="Bir kullanıcıya ait yeni bir bitki kaydı oluşturur."
)
def create_plant(plant_data: PlantCreate, db: Session = Depends(get_db)):
    """
    Yeni bitki oluşturma endpoint'i.

    - **plant_name**: Bitkinin adı (örn: 'Domates Fidesi', 'Elma Ağacı')
    - **user_id**: Bu bitkinin sahibi olan kullanıcının ID'si
    """

    # Önce kullanıcının var olduğunu doğrula
    user = db.query(User).filter(User.id == plant_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={plant_data.user_id} olan kullanıcı bulunamadı."
        )

    # Yeni bitki nesnesi oluştur ve kaydet
    new_plant = Plant(
        plant_name=plant_data.plant_name,
        user_id=plant_data.user_id,
    )

    db.add(new_plant)
    db.commit()
    db.refresh(new_plant)

    return new_plant


@router.get(
    "/",
    response_model=list[PlantResponse],
    summary="Tüm bitkileri listele"
)
def get_all_plants(db: Session = Depends(get_db)):
    """Sistemdeki tüm bitkileri döndürür."""
    plants = db.query(Plant).all()
    return plants


@router.get(
    "/{plant_id}",
    response_model=PlantResponse,
    summary="Belirli bir bitkiyi getir"
)
def get_plant(plant_id: int, db: Session = Depends(get_db)):
    """ID'ye göre tek bir bitki döndürür."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={plant_id} olan bitki bulunamadı."
        )
    return plant


@router.get(
    "/user/{user_id}",
    response_model=list[PlantResponse],
    summary="Bir kullanıcının tüm bitkilerini getir"
)
def get_plants_by_user(user_id: int, db: Session = Depends(get_db)):
    """
    Belirli bir kullanıcıya ait tüm bitkileri döndürür.
    """
    # Kullanıcı var mı kontrol et
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={user_id} olan kullanıcı bulunamadı."
        )

    plants = db.query(Plant).filter(Plant.user_id == user_id).all()
    return plants
