# =============================================================================
# models/disease_record.py
# Bu dosya "disease_records" tablosunu temsil eden SQLAlchemy modelini tanımlar.
# Bir bitkiye ait AI tarafından tespit edilen hastalık kayıtlarını saklar.
# =============================================================================

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class DiseaseRecord(Base):
    """
    Hastalık Kaydı modeli.
    AI analizi sonucu tespit edilen bitki hastalıklarının kayıtlarını tutar.
    Her kayıt bir bitkiye aittir (Many-to-One ilişki).

    Sprint 2'de AI entegrasyonu yapıldığında bu model dolu dolduruluracak.
    Şimdilik sadece tablo yapısı tanımlanmaktadır.
    """

    # Veritabanındaki tablo adı
    __tablename__ = "disease_records"

    # -------------------------------------------------------------------------
    # Kolonlar (Tablo Sütunları)
    # -------------------------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    plant_id = Column(
        Integer,
        ForeignKey("plants.id", ondelete="CASCADE"),  # plants tablosuna foreign key
        nullable=False,
        index=True
    )

    disease_name = Column(
        String(200),
        nullable=False   # Hastalık adı (örn: "Powdery Mildew", "Leaf Blight")
    )

    confidence_score = Column(
        Float,
        nullable=True,   # AI güven skoru: 0.0 - 1.0 arası değer
                         # NULL olabilir (AI henüz entegre edilmedi)
        default=None
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # Kayıt oluşturulunca otomatik zaman damgası
        nullable=False
    )

    # -------------------------------------------------------------------------
    # İlişkiler (Relationships)
    # -------------------------------------------------------------------------

    # Bu kaydın ait olduğu bitki (Many-to-One)
    plant = relationship(
        "Plant",
        back_populates="disease_records"
    )

    def __repr__(self):
        return (
            f"<DiseaseRecord("
            f"id={self.id}, "
            f"plant_id={self.plant_id}, "
            f"disease='{self.disease_name}', "
            f"confidence={self.confidence_score}"
            f")>"
        )
