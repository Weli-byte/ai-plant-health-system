# =============================================================================
# models/user.py
# Bu dosya "users" tablosunu temsil eden SQLAlchemy modelini tanımlar.
# Her User nesnesi, veritabanındaki bir satıra karşılık gelir.
# =============================================================================

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class User(Base):
    """
    Kullanıcı modeli.
    Sistemde kayıtlı kullanıcıları temsil eder.
    Bir kullanıcının birden fazla bitkisi olabilir (One-to-Many ilişki).
    """

    # Veritabanındaki tablo adı
    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # Kolonlar (Tablo Sütunları)
    # -------------------------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,  # Benzersiz tanımlayıcı
        index=True,        # Sorgu hızını artırmak için indeks
        autoincrement=True # Otomatik artan sayı
    )

    username = Column(
        String(50),
        unique=True,       # Her kullanıcı adı benzersiz olmalı
        nullable=False,    # Boş bırakılamaz
        index=True
    )

    email = Column(
        String(100),
        unique=True,       # Her email benzersiz olmalı
        nullable=False,
        index=True
    )

    password = Column(
        String(255),       # Hash'lenmiş şifre için yeterli uzunluk
        nullable=False
    )

    # -------------------------------------------------------------------------
    # İlişkiler (Relationships)
    # -------------------------------------------------------------------------

    # Bir kullanıcının birden fazla bitkisi olabilir
    # "back_populates" → Plant modelindeki "owner" ile çift yönlü bağlantı kurar
    plants = relationship(
        "Plant",
        back_populates="owner",
        cascade="all, delete-orphan"  # Kullanıcı silinince bitkileri de sil
    )

    def __repr__(self):
        """Nesneyi string olarak temsil eder (debugging için kullanışlı)"""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
