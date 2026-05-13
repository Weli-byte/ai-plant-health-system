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
import socket
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

# Sprint 4 (Son Aşama): Yeni tablolar için SQLAlchemy modelleri
# Bu satırlar olmadan Base.metadata.create_all() bu tabloları oluşturmaz!
import app.models.regional_disease_data  # noqa: F401  → regional_disease_data tablosu
import app.models.model_update_record    # noqa: F401  → model_updates tablosu
import app.models.user_profile           # noqa: F401  → user_profiles tablosu
import app.models.analysis_record        # noqa: F401  → analysis_records tablosu

# Route'ları içe aktar
from app.routes import users, plants, disease_records, ai_detection
from app.routes import user_profiles
from app.routes import analysis_records
from app.routes import reports

# Sprint 3: Tarım Karar Destek Sistemi route'larını içe aktar
from app.routes import ai_sprint3

# Sprint 4 (Son Aşama): Birleşik AI endpoint'leri
# global_risk_analysis, get_regional_alerts, update_model
from app.routes import ai_sprint4

# Sprint 4: Week 3 route'larını içe aktar
from app.routes import risk_v2, multimodal, digital_twin, leaf_detection

# Sprint 4: Week 1 — Global Disease Spread Analysis
from app.routes import global_risk

# Sprint 4: Continual Learning
from app.routes import retraining

# Sprint 4: Regional Analytics Engine
from app.routes import analytics

# Sprint 4: MLOps Automated Retraining
from app.routes import model_updates

# Sprint 4: External Dataset Management
from app.routes import dataset

# AI Model deposunu içe aktar (lifespan içinde doldurulacak)
from app.core.model_manager import model_store

# Sprint 4: Week 3 servis singleton'larını içe aktar
from app.services.risk_v2_service import risk_v2_store
from app.services.multimodal_service import multimodal_store
from app.services.digital_twin_service import digital_twin_store
from app.ml.yolo_detector import yolo_detector

# Sprint 4: Week 1 — Global GNN singleton
from app.services.global_risk_service import global_gnn_store

# Sprint 4: Continual Learning service
from app.services.retraining_service import retraining_service

# Sprint 4: Regional Analytics service
from app.services.analytics_service import analytics_service

# Sprint 4: MLOps service
from app.services.model_update_service import model_update_service

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

# Mevcut DB için kolon migration (create_all eksik kolonları eklemez)
try:
    from sqlalchemy import text
    _NEW_PLANT_COLS = [
        ("plant_type", "VARCHAR(100)"),
        ("plant_emoji", "VARCHAR(10)"),
        ("planting_date", "VARCHAR(20)"),
        ("location", "VARCHAR(200)"),
        ("growth_stage", "VARCHAR(50)"),
        ("irrigation_method", "VARCHAR(50)"),
        ("irrigation_frequency", "VARCHAR(50)"),
        ("area_size", "FLOAT"),
        ("notes", "TEXT"),
    ]
    with engine.connect() as _conn:
        for _col, _typ in _NEW_PLANT_COLS:
            try:
                _conn.execute(text(f"ALTER TABLE plants ADD COLUMN {_col} {_typ}"))
                _conn.commit()
            except Exception:
                pass  # kolon zaten var
except Exception as _mig_exc:
    logger.warning("Plant kolon migration atlandı: %s", _mig_exc)


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
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        logger.info(f"🌐 Yerel Ağ Erişimi: http://{local_ip}:8000")
        logger.info(f"   Frontend (Vite): http://{local_ip}:8080")
    except Exception:
        logger.info("🌐 Yerel ağ IP'si alınamadı.")
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

    # Sprint 4: Week 3 modellerini yükle (her biri bağımsız try/except ile korunur)
    for name, fn in [
        ("risk_v2_store",        risk_v2_store.load),
        ("multimodal_store",     multimodal_store.load),
        ("digital_twin_store",   digital_twin_store.load),
        ("yolo_detector",        yolo_detector.load_model),
        ("global_gnn_store",     global_gnn_store.load),
        ("retraining_service",   retraining_service.initialize),
        ("analytics_service",    analytics_service.initialize),
        ("model_update_service", model_update_service.initialize),
    ]:
        try:
            fn()
        except Exception as exc:
            logger.warning("⚠️  %s başlatılamadı (ilgili endpoint'ler 503 döner): %s", name, exc)

    # ──── UYGULAMA ÇALIŞIYOR ─────────────────────────────────────────────────
    yield  # Bu noktada uygulama istekleri karşılar

    # ──── SHUTDOWN ───────────────────────────────────────────────────────────
    logger.info("🔄 Uygulama kapatılıyor...")
    model_store.unload_all()
    # Sprint 4: Week 3 modellerini bellekten temizle
    risk_v2_store.unload()
    multimodal_store.unload()
    digital_twin_store.unload()
    # Sprint 4: Week 1
    global_gnn_store.unload()
    # Sprint 4: Continual Learning — persist replay buffer
    retraining_service.shutdown()
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,  # 192.168.x.x / 10.x.x.x LAN erişimi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Router'ları Uygulamaya Bağla
# Her router kendi prefix'i ile çalışır (örn: /users, /plants, /ai)
# =============================================================================
app.include_router(users.router)
app.include_router(user_profiles.router)
app.include_router(plants.router)
app.include_router(disease_records.router)
app.include_router(analysis_records.router)
app.include_router(reports.router)
app.include_router(ai_detection.router)   # Sprint 2: Gerçek AI endpoint'leri
app.include_router(ai_sprint3.router)      # Sprint 3: Karar Destek Sistemi

# Sprint 4: Week 3 router'ları
app.include_router(risk_v2.router)
app.include_router(multimodal.router)
app.include_router(digital_twin.router)
app.include_router(leaf_detection.router)

# Sprint 4: Week 1 — Global Disease Spread Analysis
app.include_router(global_risk.router)

# Sprint 4: Continual Learning
app.include_router(retraining.router)

# Sprint 4: Regional Analytics Engine
app.include_router(analytics.router)

# Sprint 4: MLOps Automated Retraining
app.include_router(model_updates.router)

# Sprint 4: External Dataset Management
app.include_router(dataset.router)

# Sprint 4 (Son Aşama): Birleşik AI endpoint'leri
# Prefix: /api/v4 — global_risk_analysis, get_regional_alerts, update_model
app.include_router(ai_sprint4.router)


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
        host="0.0.0.0",   # Tüm ağ arayüzlerinden erişim (LAN dahil)
        port=8000,
        reload=True
    )
