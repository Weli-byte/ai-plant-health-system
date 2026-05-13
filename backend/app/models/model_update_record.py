# =============================================================================
# models/model_update_record.py
#
# Sprint 4 (Son Aşama) — Model Update Record Modeli
#
# Bu tablo Continual Learning (sürekli öğrenme) sürecindeki her model
# güncelleme olayını PostgreSQL'de kayıt altına alır.
# MLOps izleme ve model versiyonlama için kullanılır.
#
# Sütunlar:
#   id         — Birincil anahtar (otomatik artan)
#   model_name — Güncellenen modelin adı (örn: "GNN", "XGBoost", "EfficientNet")
#   version    — Semantik versiyon etiketi (örn: "v1.0.2", "2024-05-13-a")
#   metrics    — Eğitim/değerlendirme metrikleri (JSON sütun)
#   updated_at — Güncellemenin gerçekleştiği zaman (UTC)
#
# NOT: SQLAlchemy'nin JSON tipini kullanmak için PostgreSQL >= 9.4 gereklidir.
#      SQLite ile de çalışır (JSON → TEXT olarak saklanır).
# =============================================================================

from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func

from app.database.connection import Base


class ModelUpdateRecord(Base):
    """
    Model güncelleme kaydı tablosu.

    Continual Learning sistemi her yeni model versiyonunu buraya yazar.
    MLflow veya Weights & Biases entegrasyonu olmadan hafif bir
    model kayıt defteri görevi görür.

    Bu model ``Base.metadata.create_all()`` çağrısında otomatik olarak
    PostgreSQL'de oluşturulur; manuel migration gerekmez.
    """

    __tablename__ = "model_updates"

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

    model_name = Column(
        String(150),
        nullable=False,
        index=True,
        comment="Modelin tanımlayıcı adı (örn: 'GNN', 'XGBoost', 'EfficientNet-B3')",
    )

    version = Column(
        String(100),
        nullable=False,
        comment="Semantik versiyon etiketi (örn: 'v1.0.2', '2024-05-13-cl')",
    )

    metrics = Column(
        JSON,
        nullable=True,
        comment=(
            "Eğitim/test metrikleri — serbest biçim JSON. "
            "Örn: {\"accuracy\": 0.94, \"f1\": 0.92, \"loss\": 0.18}"
        ),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),  # INSERT sırasında otomatik UTC timestamp
        nullable=False,
        comment="Model güncellemesinin gerçekleştiği zaman damgası (UTC)",
    )

    # -------------------------------------------------------------------------
    # Temsil Metodu
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<ModelUpdateRecord("
            f"id={self.id}, "
            f"model='{self.model_name}', "
            f"version='{self.version}'"
            f")>"
        )
