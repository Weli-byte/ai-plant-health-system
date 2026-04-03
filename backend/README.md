# =============================================================================
# backend/README.md
# AI Plant Health Detection System — Backend Dokümantasyonu
# =============================================================================

# 🌱 AI Plant Health Detection — Backend

**Sprint 1 | FastAPI + PostgreSQL + SQLAlchemy**

Yapay zeka destekli bitki hastalık tespiti sisteminin backend altyapısı.

---

## 📁 Proje Yapısı

```
backend/
├── app/
│   ├── main.py              ← FastAPI uygulamasının giriş noktası
│   ├── config/
│   │   └── settings.py      ← Ortam değişkenleri ve uygulama ayarları
│   ├── database/
│   │   └── connection.py    ← PostgreSQL bağlantısı, Engine, Session, Base
│   ├── models/
│   │   ├── user.py          ← SQLAlchemy: users tablosu
│   │   ├── plant.py         ← SQLAlchemy: plants tablosu
│   │   └── disease_record.py← SQLAlchemy: disease_records tablosu
│   ├── schemas/
│   │   ├── user.py          ← Pydantic: kullanıcı veri doğrulama şemaları
│   │   ├── plant.py         ← Pydantic: bitki veri doğrulama şemaları
│   │   └── disease_record.py← Pydantic: hastalık kaydı şemaları
│   └── routes/
│       ├── users.py         ← GET/POST /users endpointleri
│       ├── plants.py        ← GET/POST /plants endpointleri
│       ├── disease_records.py← GET/POST /disease-records endpointleri
│       └── ai_detection.py  ← Dummy AI endpointleri (Sprint 2'de doldurulacak)
├── .env                     ← Gizli ortam değişkenleri (Git'e EKLEMEYİN)
├── requirements.txt         ← Python bağımlılıkları
└── README.md                ← Bu dosya
```

---

## 🗄️ Veritabanı Şeması

```
users
  ├── id          (PK, Integer, Auto-increment)
  ├── username    (String 50, Unique, Not Null)
  ├── email       (String 100, Unique, Not Null)
  └── password    (String 255, Not Null)
        │ 1:N
        ▼
plants
  ├── id          (PK, Integer, Auto-increment)
  ├── user_id     (FK → users.id, Not Null)
  ├── plant_name  (String 100, Not Null)
  └── created_at  (DateTime, Auto)
        │ 1:N
        ▼
disease_records
  ├── id              (PK, Integer, Auto-increment)
  ├── plant_id        (FK → plants.id, Not Null)
  ├── disease_name    (String 200, Not Null)
  ├── confidence_score(Float, Nullable — AI eklenince dolar)
  └── created_at      (DateTime, Auto)
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. PostgreSQL'i hazırla

PostgreSQL kurulu ve çalışıyor olmalı. Veritabanını oluştur:

```sql
CREATE DATABASE plant_health_db;
```

### 2. Sanal ortam oluştur

```bash
# Backend klasörüne gir
cd backend

# Sanal ortam oluştur
python -m venv venv

# Aktif et (Windows)
venv\Scripts\activate

# Aktif et (Mac/Linux)
source venv/bin/activate
```

### 3. Bağımlılıkları kur

```bash
pip install -r requirements.txt
```

### 4. .env dosyasını yapılandır

`.env` dosyasını aç ve kendi PostgreSQL bilgilerini gir:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=plant_health_db
DB_USER=postgres
DB_PASSWORD=your_actual_password
```

### 5. Sunucuyu başlat

```bash
uvicorn app.main:app --reload
```

✅ API çalışıyor: http://localhost:8000  
📖 Swagger UI: http://localhost:8000/docs  
📖 ReDoc: http://localhost:8000/redoc

---

## 🔌 API Endpointleri

### Health Check
| Method | URL | Açıklama |
|--------|-----|----------|
| GET | `/` | API çalışıyor mu kontrol et |

### Users
| Method | URL | Açıklama |
|--------|-----|----------|
| POST | `/users/` | Yeni kullanıcı oluştur |
| GET | `/users/` | Tüm kullanıcıları listele |
| GET | `/users/{user_id}` | Belirli kullanıcıyı getir |

### Plants
| Method | URL | Açıklama |
|--------|-----|----------|
| POST | `/plants/` | Yeni bitki ekle |
| GET | `/plants/` | Tüm bitkileri listele |
| GET | `/plants/{plant_id}` | Belirli bitkiyi getir |
| GET | `/plants/user/{user_id}` | Kullanıcının bitkilerini getir |

### Disease Records
| Method | URL | Açıklama |
|--------|-----|----------|
| POST | `/disease-records/` | Hastalık kaydı oluştur |
| GET | `/disease-records/plant/{plant_id}` | Bitkinin hastalık kayıtları |

### AI Detection (Sprint 2 — Şu an Dummy)
| Method | URL | Açıklama |
|--------|-----|----------|
| POST | `/ai/upload_image` | Bitki görseli yükle |
| POST | `/ai/detect_disease` | Hastalık tespiti yap |
| GET | `/ai/get_risk_prediction` | Risk tahmini al |

---

## 📅 Sprint Planı

| Sprint | Durum | Kapsam |
|--------|-------|--------|
| Sprint 1 | ✅ Tamamlandı | Backend altyapısı, DB modelleri, temel CRUD endpointleri |
| Sprint 2 | 🔜 Planlandı | AI model entegrasyonu, görsel yükleme, şifre hash'leme |
| Sprint 3 | 🔜 Planlandı | Authentication (JWT), risk analizi, frontend bağlantısı |

---

## 🛠️ Teknoloji Yığını

- **FastAPI** — Modern Python web framework
- **PostgreSQL** — İlişkisel veritabanı
- **SQLAlchemy** — Python ORM
- **Pydantic v2** — Veri doğrulama
- **Uvicorn** — ASGI sunucusu
- **python-dotenv** — Ortam değişkenleri yönetimi
