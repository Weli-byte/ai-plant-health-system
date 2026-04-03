# =============================================================================
# models/plant.py
# Bu dosya "plants" tablosunu temsil eden SQLAlchemy modelini tanımlar.
# Her bitki, bir kullanıcıya aittir (Many-to-One ilişki).
# =============================================================================

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class Plant(Base):
    """
    Bitki modeli.
    Kullanıcıların sisteme kaydettiği bitkileri temsil eder.
    Bir bitkinin birden fazla hastalık kaydı olabilir (One-to-Many ilişki).
    """

    # Veritabanındaki tablo adı
    __tablename__ = "plants"

    # -------------------------------------------------------------------------
    # Kolonlar (Tablo Sütunları)
    # -------------------------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # users tablosuna foreign key
        nullable=False,
        index=True
    )

    plant_name = Column(
        String(100),
        nullable=False   # Bitki adı zorunludur
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # Kayıt oluşturulunca otomatik zaman damgası
        nullable=False
    )

    # -------------------------------------------------------------------------
    # İlişkiler (Relationships)
    # -------------------------------------------------------------------------

    # Bu bitkinin sahibi olan kullanıcı (Many-to-One)
    owner = relationship(
        "User",
        back_populates="plants"
    )

    # Bu bitkiye ait hastalık kayıtları (One-to-Many)
    disease_records = relationship(
        "DiseaseRecord",
        back_populates="plant",
        cascade="all, delete-orphan"  # Bitki silinince hastalık kayıtları da sil
    )

    def __repr__(self):
        return f"<Plant(id={self.id}, name='{self.plant_name}', user_id={self.user_id})>"
