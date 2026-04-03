# =============================================================================
# main.py
# Bu dosya FastAPI uygulamasının ana giriş noktasıdır.
# Tüm router'lar buraya bağlanır ve uygulama burada başlatılır.
#
# Çalıştırmak için terminal'de şunu yaz:
#   uvicorn app.main:app --reload
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Uygulama ayarlarını içe aktar
from app.config.settings import settings

# Veritabanı bağlantısını ve modellerini içe aktar
from app.database.connection import engine, Base

# Modelleri içe aktar → SQLAlchemy tabloları tanısın (önemli!)
import app.models.user          # noqa: F401 (kullanılmasa da import edilmeli)
import app.models.plant         # noqa: F401
import app.models.disease_record  # noqa: F401

# Route'ları içe aktar
from app.routes import users, plants, disease_records, ai_detection

# =============================================================================
# Veritabanı Tablolarını Oluştur
# Bu satır çalıştığında, tanımlanan tablolar PostgreSQL'de otomatik oluşturulur.
# Tablo zaten varsa tekrar oluşturmaz (güvenli).
# =============================================================================
Base.metadata.create_all(bind=engine)


# =============================================================================
# FastAPI Uygulama Nesnesi
# =============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    docs_url="/docs",      # Swagger UI: http://localhost:8000/docs
    redoc_url="/redoc",    # ReDoc UI:   http://localhost:8000/redoc
)


# =============================================================================
# CORS (Cross-Origin Resource Sharing) Middleware
# Frontend'in farklı bir port'tan API'ye erişmesine izin verir.
# Örn: React localhost:3000 → FastAPI localhost:8000
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # İzin verilen origin'ler
    allow_credentials=True,
    allow_methods=["*"],    # GET, POST, PUT, DELETE, vb. hepsine izin ver
    allow_headers=["*"],    # Tüm header'lara izin ver
)


# =============================================================================
# Router'ları Uygulamaya Bağla
# Her router kendi prefix'i ile çalışır (örn: /users, /plants, /ai)
# =============================================================================
app.include_router(users.router)
app.include_router(plants.router)
app.include_router(disease_records.router)
app.include_router(ai_detection.router)


# =============================================================================
# Kök Endpoint (Health Check)
# API'nin çalışıp çalışmadığını kontrol etmek için kullanılır.
# GET http://localhost:8000/
# =============================================================================
@app.get("/", tags=["Health Check"], summary="API sağlık kontrolü")
def root():
    """
    API'nin çalıştığını doğrulayan basit bir endpoint.
    CI/CD pipeline'larında ve deployment kontrollerinde kullanılır.
    """
    return {
        "status": "🌱 API is running!",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs": "http://localhost:8000/docs",
        "sprint": "Sprint 1 - Backend Foundation",
        "message": "Welcome to the AI Plant Health Detection Backend!"
    }


# =============================================================================
# Doğrudan Çalıştırma (opsiyonel)
# Terminal'de: python app/main.py
# Önerilen yol: uvicorn app.main:app --reload
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True   # Kod değişince otomatik yeniden başlat (geliştirme modu)
    )
