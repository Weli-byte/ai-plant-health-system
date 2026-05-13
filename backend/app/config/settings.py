# =============================================================================
# config/settings.py
# Bu dosya projenin genel ayarlarını barındırır.
# Veritabanı URL'si, gizli anahtarlar gibi konfigürasyonlar buradan okunur.
# =============================================================================

import os
from dotenv import load_dotenv

# .env dosyasını yükle (eğer varsa)
load_dotenv()


class Settings:
    """
    Uygulama genelinde kullanılacak ayarlar sınıfı.
    Tüm environment variable'lar buradan okunur.
    """

    # Proje Bilgileri
    PROJECT_NAME: str = "AI Plant Health Detection System"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = (
        "Yapay zeka destekli bitki hastalık tespiti için backend API'si. "
        "Sprint 1 - Temel Altyapı."
    )

    # PostgreSQL Veritabanı Ayarları
    # .env dosyasında bu değerleri tanımla; yoksa varsayılan değerler kullanılır.
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "plant_health_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")

    # SQLite Fallback (Geliştirme kolaylığı için)
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "True").lower() == "true"

    # SQLAlchemy bağlantı URL'si
    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE:
            return "sqlite:///./plant_health.db"
        
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Uygulama Genel Ayarları
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret-change-me-in-production")

    # CORS Ayarları (Frontend ile iletişim için)
    # Hem localhost hem 127.0.0.1 varyantları eklendi:
    # Windows'ta bazı tarayıcılar localhost yerine 127.0.0.1 kullanır;
    # ikisi ayrı origin sayılır ve her ikisi de izin listesinde olmalıdır.
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",    # React/Next.js
        "http://localhost:5173",    # Vite varsayılan
        "http://localhost:8080",    # Vite (bu proje)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",   # Windows IPv4 çözümlemesi için kritik
        "http://0.0.0.0:8080",     # Vite 0.0.0.0 bind
    ]

    # Yerel ağdaki cihazlardan erişim için IP aralığı regex'i
    # 192.168.x.x ve 10.x.x.x özel ağ aralıklarını kapsar
    ALLOWED_ORIGIN_REGEX: str = (
        r"http://(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"
    )

    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # External Dataset Ayarları
    DATASET_PATH: str = os.getenv("DATASET_PATH", "")

    @property
    def get_dataset_path(self) -> str:
        """Güvenli bir şekilde dataset yolunu döndür, fallback olarak boş string."""
        if not self.DATASET_PATH:
            return ""
        return self.DATASET_PATH


# Ayarların tek bir örneğini oluştur (Singleton pattern)
settings = Settings()
