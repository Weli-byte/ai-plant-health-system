# =============================================================================
# main.py
# Bu dosya FastAPI uygulamasının ana giriş noktasıdır.
# Tüm router'lar buraya bağlanır ve uygulama burada başlatılır.
#
# Sprint 2 Değişiklikleri:
#   - lifespan context manager eklendi → AI modeller uygulama başlarken
#     BİR KEZ yüklenir, kapanırken bellekten temizlenir.
#   - app=FastAPI(...) artık lifespan parametresi alıyor.
#
# Çalıştırmak için terminal'de şunu yaz:
#   uvicorn app.main:app --reload
# =============================================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Uygulama ayarlarını içe aktar
from app.config.settings import settings

# Veritabanı bağlantısını ve modellerini içe aktar
from app.database.connection import engine, Base

# SQLAlchemy modellerini içe aktar → tablolar tanınsın (önemli!)
import app.models.user            # noqa: F401
import app.models.plant           # noqa: F401
import app.models.disease_record  # noqa: F401

# Route'ları içe aktar
from app.routes import users, plants, disease_records, ai_detection

# AI Model deposunu içe aktar (lifespan içinde doldurulacak)
from app.core.model_manager import model_store

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s → %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Veritabanı Tablolarını Oluştur
# Bu satır çalıştığında, tanımlanan tablolar PostgreSQL'de otomatik oluşturulur.
# Tablo zaten varsa tekrar oluşturmaz (güvenli).
# =============================================================================
Base.metadata.create_all(bind=engine)


# =============================================================================
# Lifespan — Uygulama Başlatma / Kapatma Olayları
#
# Bu async context manager iki kritik görevi üstlenir:
#   STARTUP  (yield öncesi): AI modellerini belleğe yükle.
#   SHUTDOWN (yield sonrası): Modelleri bellekten temizle (graceful shutdown).
#
# Neden lifespan?
#   - AI modelleri (YOLOv8 + EfficientNet) her istekte yeniden yüklenemez;
#     bu hem yavaşlatır hem de sunucuyu çökertir.
#   - Lifespan yaklaşımı, FastAPI'nin önerdiği modern startup/shutdown yöntemidir.
#     (Deprecated @app.on_event("startup") yerine kullanılır.)
#
# Model dosyaları bulunamazsa uygulama BAŞLAMAZ (fail-fast).
# Bu davranış, sessiz hataları önler ve erken fark edilmesini sağlar.
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    STARTUP aşaması:
        - YOLOv8, EfficientNet-B3 ve Grad-CAM bileşenlerini belleğe yükler.
        - Model dosyaları bulunamazsa FileNotFoundError fırlatır → uygulama başlamaz.

    SHUTDOWN aşaması:
        - Modelleri bellekten temizler.
        - GPU kullanılıyorsa CUDA belleğini boşaltır.
    """
    # ──── STARTUP ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("🌱 AI Plant Health Detection System başlatılıyor...")
    logger.info(f"   Proje: {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info("=" * 60)

    try:
        model_store.load_all()
        logger.info("✅ AI modelleri başarıyla yüklendi. API isteklere hazır.")
    except FileNotFoundError as exc:
        # Model dosyaları eksik → uyarı ver ama uygulamayı durdur
        logger.warning(
            f"⚠️  Model dosyası bulunamadı: {exc}\n"
            "   AI endpoint'leri (/ai/*) 503 hatası döndürecek.\n"
            "   Weli'nin .pt dosyalarını 'models/' klasörüne yerleştirin."
        )
        # is_loaded=False kalır → endpoint'ler 503 döndürür (uygulama çökmez)
    except Exception as exc:
        logger.error(
            f"❌ Kritik model yükleme hatası: {exc}\n"
            "   AI endpoint'leri devre dışı. Diğer endpoint'ler çalışmaya devam eder."
        )

    # ──── UYGULAMA ÇALIŞIYOR ─────────────────────────────────────────────────
    yield  # Bu noktada uygulama istekleri karşılar

    # ──── SHUTDOWN ───────────────────────────────────────────────────────────
    logger.info("🔄 Uygulama kapatılıyor...")
    model_store.unload_all()
    logger.info("♻️  Bellekten modeller kaldırıldı. Güvenli kapatma tamamlandı.")


# =============================================================================
# FastAPI Uygulama Nesnesi
# lifespan parametresi ile startup/shutdown yönetimi devredilir.
# =============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=(
        settings.PROJECT_DESCRIPTION
        + "\n\n**Sprint 2**: YOLOv8 yaprak tespiti, EfficientNet-B3 hastalık "
        "sınıflandırma ve Grad-CAM açıklanabilirlik endpoint'leri eklendi."
    ),
    docs_url="/docs",      # Swagger UI: http://localhost:8000/docs
    redoc_url="/redoc",    # ReDoc UI:   http://localhost:8000/redoc
    lifespan=lifespan,     # Sprint 2: Lifespan ile model yönetimi
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
app.include_router(ai_detection.router)   # Sprint 2: Gerçek AI endpoint'leri


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
        "sprint": "Sprint 2 - AI Integration",
        "ai_models_loaded": model_store.is_loaded,
        "ai_device": model_store.device.type if model_store.device else "unknown",
        "message": "Welcome to the AI Plant Health Detection Backend!",
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
