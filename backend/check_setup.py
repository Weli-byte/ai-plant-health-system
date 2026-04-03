"""
check_setup.py — Proje Kurulum Doğrulama Scripti
=================================================
Projeyi başlatmadan önce kurulumun doğru yapıldığını kontrol eder.
Sunucuyu açmadan ÖNCE bu scripti çalıştır.

Çalıştırma:
    python check_setup.py

Kontrol Listesi:
    ✅ Gerekli paketler kurulu mu?
    ✅ .env dosyası mevcut mu?
    ✅ Tüm zorunlu ortam değişkenleri tanımlı mı?
    ✅ PostgreSQL'e bağlanılabiliyor mu?
    ✅ FastAPI uygulaması import edilebiliyor mu?
"""

import sys
import os

# Scripti backend/ klasöründen çalıştır
# Böylece 'app' paketi bulunabilir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def check_packages():
    """Gerekli Python paketlerinin kurulu olduğunu kontrol eder."""
    print("\n📦 Paket Kontrolü")
    print("-" * 40)

    required = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "psycopg2-binary"),
        ("pydantic", "Pydantic"),
        ("dotenv", "python-dotenv"),
        ("multipart", "python-multipart"),
        ("email_validator", "email-validator"),
    ]

    all_ok = True
    for module, package_name in required:
        try:
            __import__(module)
            print(f"  {PASS} {package_name}")
        except ImportError:
            print(f"  {FAIL} {package_name} → pip install {package_name} ile kur")
            all_ok = False

    return all_ok


def check_env_file():
    """'.env' dosyasının mevcut olduğunu kontrol eder."""
    print("\n📄 .env Dosyası Kontrolü")
    print("-" * 40)

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    example_path = os.path.join(os.path.dirname(__file__), ".env.example")

    if os.path.exists(env_path):
        print(f"  {PASS} .env dosyası mevcut")
    else:
        print(f"  {FAIL} .env dosyası bulunamadı!")
        if os.path.exists(example_path):
            print(f"  {WARN} .env.example dosyasını kopyala:")
            print(f"       Windows: copy .env.example .env")
            print(f"       Mac/Linux: cp .env.example .env")
        return False
    return True


def check_env_variables():
    """Zorunlu ortam değişkenlerinin tanımlı olduğunu kontrol eder."""
    print("\n🔑 Ortam Değişkenleri Kontrolü")
    print("-" * 40)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print(f"  {FAIL} python-dotenv kurulu değil")
        return False

    required_vars = {
        "DB_HOST": "Veritabanı sunucu adresi",
        "DB_PORT": "Veritabanı port numarası",
        "DB_NAME": "Veritabanı adı",
        "DB_USER": "Veritabanı kullanıcı adı",
        "DB_PASSWORD": "Veritabanı şifresi",
    }

    all_ok = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Şifreyi ekrana yazma, sadece uzunluğunu göster
            display = "*" * len(value) if "PASSWORD" in var else value
            print(f"  {PASS} {var} = {display}  ({description})")
        else:
            print(f"  {FAIL} {var} tanımlı değil → {description}")
            all_ok = False

    return all_ok


def check_database_connection():
    """PostgreSQL veritabanına gerçekten bağlanılabiliyor mu test eder."""
    print("\n🗄️  Veritabanı Bağlantı Testi")
    print("-" * 40)

    try:
        from app.database.connection import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            # PostgreSQL versiyonunu kısa göster
            short_version = version.split(",")[0]
            print(f"  {PASS} Bağlantı başarılı!")
            print(f"  {PASS} {short_version}")
        return True

    except Exception as e:
        print(f"  {FAIL} Bağlantı başarısız: {e}")
        print(f"\n  Olası nedenler:")
        print(f"    • PostgreSQL servisi çalışmıyor olabilir")
        print(f"    • .env dosyasındaki DB_PASSWORD yanlış olabilir")
        print(f"    • '{os.getenv('DB_NAME', 'plant_health_db')}' veritabanı oluşturulmamış olabilir")
        print(f"\n  Veritabanı oluşturmak için:")
        print(f"    psql -U postgres -c \"CREATE DATABASE {os.getenv('DB_NAME', 'plant_health_db')};\"")
        return False


def check_app_import():
    """FastAPI uygulamasının hatasız import edildiğini kontrol eder."""
    print("\n🚀 FastAPI Uygulama İmport Testi")
    print("-" * 40)

    try:
        # Bu import ana uygulamayı ve tüm router'ları yükler
        # Hata varsa burada yakalanır
        from app.main import app
        print(f"  {PASS} FastAPI uygulaması başarıyla yüklendi")
        print(f"  {PASS} Kayıtlı route sayısı: {len(app.routes)}")
        return True
    except Exception as e:
        print(f"  {FAIL} Uygulama yüklenemedi: {e}")
        return False


def main():
    print("=" * 50)
    print("  🌱 AI Plant Health System — Kurulum Kontrolü")
    print("=" * 50)

    results = {
        "Paketler": check_packages(),
        ".env Dosyası": check_env_file(),
        "Ortam Değişkenleri": check_env_variables(),
        "Veritabanı Bağlantısı": check_database_connection(),
        "FastAPI Import": check_app_import(),
    }

    print("\n" + "=" * 50)
    print("  📊 SONUÇ ÖZETİ")
    print("=" * 50)

    all_passed = True
    for check_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  🎉 Her şey hazır! Sunucuyu başlatabilirsin:")
        print("     uvicorn app.main:app --reload")
        print("     Swagger UI → http://localhost:8000/docs")
    else:
        print("  🔧 Yukarıdaki hataları düzelt ve tekrar çalıştır.")

    print("=" * 50)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
