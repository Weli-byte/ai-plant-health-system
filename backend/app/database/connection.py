# =============================================================================
# database/connection.py
# Bu dosya PostgreSQL veritabanı bağlantısını yönetir.
# SQLAlchemy engine, session ve Base sınıfı burada tanımlanır.
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config.settings import settings

# -----------------------------------------------------------------------------
# Engine: Veritabanına gerçek bağlantıyı sağlayan nesne.
# "pool_pre_ping=True" → bağlantı koptuğunda otomatik yeniden bağlanır.
# -----------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # Bağlantı sağlığını kontrol et
    echo=settings.DEBUG,  # DEBUG modunda SQL sorgularını konsola yaz
)

# -----------------------------------------------------------------------------
# SessionLocal: Her HTTP isteği için ayrı bir veritabanı oturumu oluşturur.
# autocommit=False → işlemleri manuel onaylamamızı sağlar (güvenli yaklaşım)
# autoflush=False  → sorgu öncesi otomatik flush yapma
# -----------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# -----------------------------------------------------------------------------
# Base: Tüm SQLAlchemy modellerinin kalıtım alacağı temel sınıf.
# SQLAlchemy 2.0+ modern yaklaşımı: DeclarativeBase'den kalıtım alınır.
# Modeller bu sınıftan türetilir: class User(Base): ...
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# -----------------------------------------------------------------------------
# get_db: FastAPI dependency injection için veritabanı oturumu sağlar.
# Her istek başladığında session açılır, istek bitince kapatılır.
# Kullanım: def some_route(db: Session = Depends(get_db)):
# -----------------------------------------------------------------------------
def get_db():
    """
    FastAPI route'larında kullanılacak DB session dependency'si.
    'yield' kullanımı → istek bittikten sonra session otomatik kapatılır.
    """
    db = SessionLocal()
    try:
        yield db           # Route fonksiyonuna veritabanı oturumunu ver
    finally:
        db.close()         # Her durumda (hata olsa bile) oturumu kapat
