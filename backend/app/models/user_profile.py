from sqlalchemy import Column, Integer, String, Float
from app.database.connection import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    city = Column(String(50), nullable=True)
    district = Column(String(50), nullable=True)
    field_size = Column(Float, nullable=True)  # dönüm cinsinden
    crops = Column(String(1000), nullable=True)  # JSON liste: ["buğday", "mısır"]

    def __repr__(self):
        return f"<UserProfile(email='{self.email}', city='{self.city}')>"
