# =============================================================================
# routes/users.py
# Bu dosya kullanıcı (User) ile ilgili API endpointlerini tanımlar.
# Sprint 1: Temel CRUD endpointleri oluşturuldu.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

# APIRouter: FastAPI'de ilgili endpointleri gruplamak için kullanılır.
# prefix → tüm endpoint'lerin başına "/users" eklenir
# tags   → Swagger UI'de bu grup "Users" başlığı altında görünür
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı oluştur",
    description="Sisteme yeni bir kullanıcı kaydeder. Email ve kullanıcı adı benzersiz olmalıdır."
)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Yeni kullanıcı oluşturma endpoint'i.

    - **username**: Benzersiz kullanıcı adı (3-50 karakter)
    - **email**: Geçerli ve benzersiz email adresi
    - **password**: En az 8 karakterli şifre (hash'lenmiş olarak saklanır)

    ⚠️ Sprint 1 Notu: Şifre hash'leme henüz eklenmedi.
    Sprint 2'de bcrypt veya passlib ile şifreler güvenli şekilde saklanacak.
    """

    # Email ile aynı kullanıcı var mı kontrol et
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kayıtlı."
        )

    # Kullanıcı adı benzersiz mi kontrol et
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten alınmış."
        )

    # Yeni kullanıcı nesnesi oluştur
    # TODO Sprint 2: password'ü hash'le → hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,  # ⚠️ Gerçek projede HASH'lenmeli!
    )

    # Veritabanına kaydet
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # DB'den güncel veriyi al (id, vs.)

    return new_user


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="Tüm kullanıcıları listele"
)
def get_all_users(db: Session = Depends(get_db)):
    """
    Sistemdeki tüm kullanıcıları döndürür.
    ⚠️ Sprint 2'de sayfalandırma (pagination) eklenecek.
    """
    users = db.query(User).all()
    return users


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Belirli bir kullanıcıyı getir"
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    ID'ye göre tek bir kullanıcı döndürür.
    Kullanıcı bulunamazsa 404 hatası verir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={user_id} olan kullanıcı bulunamadı."
        )
    return user
