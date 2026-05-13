import json
from pydantic import BaseModel
from typing import Optional, List


class UserProfileCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    field_size: Optional[float] = None
    crops: Optional[List[str]] = None


class UserProfileResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    field_size: Optional[float] = None
    crops: List[str] = []

    @classmethod
    def from_db(cls, profile) -> "UserProfileResponse":
        crops: List[str] = []
        try:
            crops = json.loads(profile.crops or "[]")
        except Exception:
            pass
        return cls(
            id=profile.id,
            email=profile.email,
            full_name=profile.full_name,
            phone=profile.phone,
            city=profile.city,
            district=profile.district,
            field_size=profile.field_size,
            crops=crops,
        )
