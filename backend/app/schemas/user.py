# =============================================================================
# schemas/user.py
# Bu dosya User (kullanıcı) modeli için Pydantic şemalarını tanımlar.
#
# Pydantic şemaları ne işe yarar?
#   - API'ye gelen verilerin doğrulanmasını sağlar (Validation)
#   - API'den dönen verilerin şeklini belirler (Serialization)
#   - SQLAlchemy modeli ile API katmanı arasında köprü görevi görür
# =============================================================================

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# -----------------------------------------------------------------------------
# UserBase: Tüm User şemalarının paylaştığı ortak alanlar
# -----------------------------------------------------------------------------
class UserBase(BaseModel):
    username: str = Field(
        ...,                      # "..." → bu alan zorunludur
        min_length=3,
        max_length=50,
        description="Kullanıcı adı (3-50 karakter)"
    )
    email: EmailStr = Field(
        ...,
        description="Geçerli bir email adresi"
    )


# -----------------------------------------------------------------------------
# UserCreate: Yeni kullanıcı oluşturmak için kullanılır (POST /users)
# Şifre yalnızca oluşturma sırasında alınır, asla geri döndürülmez.
# -----------------------------------------------------------------------------
class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        description="En az 8 karakterli şifre"
    )


# -----------------------------------------------------------------------------
# UserResponse: API'den kullanıcı verisi döndürülürken kullanılır (GET /users)
# Şifre alanı YOKTUR — güvenlik gereği şifre hiçbir zaman dışarı çıkmaz.
# -----------------------------------------------------------------------------
class UserResponse(UserBase):
    id: int
    # Şifre alanı kasıtlı olarak burada YOK!

    class Config:
        # SQLAlchemy model nesnelerinden doğrudan veri okumayı sağlar
        from_attributes = True  # Pydantic v2 (eski: orm_mode = True)
