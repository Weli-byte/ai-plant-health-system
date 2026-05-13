# =============================================================================
# models/regional_disease_data.py
#
# Sprint 4 (Son Aşama) — Regional Disease Data Modeli
#
# Bu tablo GNN modelinin çıktısı olan bölgesel hastalık risk verilerini
# PostgreSQL'de kalıcı olarak saklar.
# Eren'in harita görselleştirmesi bu tablodan beslenir.
#
# Sütunlar:
#   id            — Birincil anahtar (otomatik artan)
#   location_label — Bölge etiketi (örn: "Ege Bölgesi", "Ankara-Merkez")
#   disease_name  — Tespit edilen hastalık adı
#   risk_score    — GNN tarafından hesaplanan risk skoru (0.0–1.0)
#   detected_at   — Riskin tespit edildiği zaman damgası (UTC)
# =============================================================================

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

from app.database.connection import Base


class RegionalDiseaseData(Base):
    """
    Bölgesel hastalık risk verisi tablosu.

    GNN (Graph Neural Network) modelinin ürettiği bölgesel risk tahminlerini
    saklar. Her kayıt tek bir bölge–hastalık–zaman üçlüsünü temsil eder.

    Bu model ``Base.metadata.create_all()`` çağrısında otomatik olarak
    PostgreSQL'de oluşturulur; manuel migration gerekmez.
    """

    __tablename__ = "regional_disease_data"

    # -------------------------------------------------------------------------
    # Kolonlar
    # -------------------------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="Birincil anahtar",
    )

    location_label = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Bölge etiketi (örn: 'Ege Bölgesi', 'İzmir-Merkez')",
    )

    disease_name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="GNN tarafından tespit edilen hastalık adı",
    )

    risk_score = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Normalleştirilmiş risk skoru: 0.0 (düşük) – 1.0 (kritik)",
    )

    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # INSERT sırasında otomatik UTC timestamp
        nullable=False,
        comment="Riskin tespit edildiği zaman damgası (UTC)",
    )

    # -------------------------------------------------------------------------
    # Temsil Metodu
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<RegionalDiseaseData("
            f"id={self.id}, "
            f"location='{self.location_label}', "
            f"disease='{self.disease_name}', "
            f"risk={self.risk_score:.3f}"
            f")>"
        )
