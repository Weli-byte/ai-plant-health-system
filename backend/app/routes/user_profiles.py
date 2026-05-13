import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse

router = APIRouter(prefix="/user-profiles", tags=["User Profiles"])


@router.post("/", response_model=UserProfileResponse)
def upsert_profile(data: UserProfileCreate, db: Session = Depends(get_db)):
    """E-postaya göre profil oluşturur veya günceller (upsert)."""
    crops_str = json.dumps(data.crops or [], ensure_ascii=False)
    profile = db.query(UserProfile).filter(UserProfile.email == data.email).first()

    if profile:
        profile.full_name = data.full_name
        profile.phone = data.phone
        profile.city = data.city
        profile.district = data.district
        profile.field_size = data.field_size
        profile.crops = crops_str
    else:
        profile = UserProfile(
            email=data.email,
            full_name=data.full_name,
            phone=data.phone,
            city=data.city,
            district=data.district,
            field_size=data.field_size,
            crops=crops_str,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return UserProfileResponse.from_db(profile)


@router.get("/{email}", response_model=UserProfileResponse)
def get_profile(email: str, db: Session = Depends(get_db)):
    """E-postaya göre kullanıcı profilini getirir."""
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil bulunamadı.")
    return UserProfileResponse.from_db(profile)
