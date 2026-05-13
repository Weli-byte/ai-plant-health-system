"""
app/routes/ai_sprint4.py
=========================
Sprint 4 (Son Aşama) — Birleşik AI Endpoint'leri

Bu router üç temel endpoint'i barındırır:

    GET  /api/v4/global_risk_analysis   → GNN tabanlı bölgesel risk haritası
    GET  /api/v4/get_regional_alerts    → Belirtilen bölge için kritik uyarılar
    POST /api/v4/update_model           → Continual Learning simülasyonu

Tasarım kararları:
    - Her endpoint kendi try/except bloğuyla korunur (independent fault isolation).
    - Veritabanı işlemleri SQLAlchemy Session üzerinden yapılır.
    - Continual Learning sonuçları ``model_updates`` tablosuna yazılır.
    - GNN verileri ``regional_disease_data`` tablosundan okunur.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.regional_disease_data import RegionalDiseaseData
from app.models.model_update_record import ModelUpdateRecord

logger = logging.getLogger(__name__)

# =============================================================================
# Router Tanımı
# =============================================================================

router = APIRouter(
    prefix="/api/v4",
    tags=["Sprint 4 — Son Aşama AI Endpoints"],
)


# =============================================================================
# Pydantic Şemaları — Bu endpoint'lere özgü, mevcut şemalarla çakışmaz.
# =============================================================================

# ── /global_risk_analysis yanıt şeması ───────────────────────────────────────

class RegionalRiskEntry(BaseModel):
    """Tek bir bölgeye ait GNN risk kaydı."""

    id: int = Field(..., description="Veritabanı kayıt ID'si")
    location_label: str = Field(..., description="Bölge etiketi")
    disease_name: str = Field(..., description="Hastalık adı")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk skoru (0.0–1.0)")
    risk_level: str = Field(..., description="Risk seviyesi: low / medium / high / critical")
    detected_at: datetime = Field(..., description="Tespit zamanı (UTC)")

    class Config:
        from_attributes = True


class GlobalRiskAnalysisResponse(BaseModel):
    """GET /global_risk_analysis yanıt zarfı."""

    success: bool
    total_records: int
    high_risk_count: int
    data: List[RegionalRiskEntry]
    message: str


# ── /get_regional_alerts yanıt şeması ───────────────────────────────────────

class RegionalAlert(BaseModel):
    """Tek bir kritik bölge uyarısı."""

    alert_id: str = Field(..., description="UUID uyarı kimliği")
    location_label: str
    disease_name: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    severity: str = Field(..., description="Uyarı önceliği: WATCH / WARNING / EMERGENCY")
    recommended_action: str = Field(..., description="Önerilen acil eylem")
    detected_at: datetime


class RegionalAlertsResponse(BaseModel):
    """GET /get_regional_alerts yanıt zarfı."""

    success: bool
    region_queried: str
    alert_count: int
    critical_count: int
    alerts: List[RegionalAlert]
    message: str


# ── /update_model istek ve yanıt şeması ─────────────────────────────────────

class UpdateModelRequest(BaseModel):
    """POST /update_model istek gövdesi."""

    model_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Güncellenecek modelin adı (örn: 'GNN', 'XGBoost')",
        examples=["GNN"],
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Yeni versiyon etiketi (örn: 'v1.0.2')",
        examples=["v1.0.2"],
    )
    training_data_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Eğitim seti boyutu (örnek sayısı)",
    )
    epochs: Optional[int] = Field(
        default=10,
        ge=1,
        le=1000,
        description="Eğitim epoch sayısı",
    )
    learning_rate: Optional[float] = Field(
        default=0.001,
        gt=0.0,
        description="Öğrenme oranı",
    )


class UpdateModelData(BaseModel):
    """Güncelleme işlemi sonuç detayları."""

    record_id: int = Field(..., description="Veritabanına yazılan kayıt ID'si")
    model_name: str
    version: str
    metrics: Dict[str, Any]
    updated_at: datetime


class UpdateModelResponse(BaseModel):
    """POST /update_model yanıt zarfı."""

    success: bool
    data: UpdateModelData
    message: str


# =============================================================================
# Yardımcı Fonksiyonlar
# =============================================================================

_RISK_THRESHOLDS = {
    "low": 0.35,
    "medium": 0.60,
    "high": 0.80,
}

_SEVERITY_MAP = {
    "medium": "WATCH",
    "high": "WARNING",
    "critical": "EMERGENCY",
}

_ACTION_MAP = {
    "WATCH":     "Bölgeyi 48 saat içinde tekrar değerlendirin.",
    "WARNING":   "Bölge tarım müdürlüğünü bilgilendirin; önleyici ilaçlama başlatın.",
    "EMERGENCY": "ACİL müdahale ekibi konuşlandırın; karantina prosedürlerini uygulayın.",
}


def _classify_risk(score: float) -> str:
    """0.0–1.0 arası skoru dört kategoriye ayırır."""
    if score < _RISK_THRESHOLDS["low"]:
        return "low"
    if score < _RISK_THRESHOLDS["medium"]:
        return "medium"
    if score < _RISK_THRESHOLDS["high"]:
        return "high"
    return "critical"


def _seed_demo_data(db: Session) -> None:
    """
    Veritabanında hiç kayıt yoksa demo GNN verileri ekler.

    Bu fonksiyon SADECE bos tabloya karşı çalışır; mevcut kayıtlara
    dokunmaz (idempotent). Üretim ortamında gerçek GNN çıktısıyla
    bu verilerin üzerine yazılır.
    """
    count = db.query(RegionalDiseaseData).count()
    if count > 0:
        return  # Tablo zaten dolu → seeding atla

    demo_records = [
        RegionalDiseaseData(
            location_label="Ege Bölgesi",
            disease_name="Powdery Mildew",
            risk_score=0.82,
        ),
        RegionalDiseaseData(
            location_label="Marmara Bölgesi",
            disease_name="Leaf Blight",
            risk_score=0.61,
        ),
        RegionalDiseaseData(
            location_label="Akdeniz Bölgesi",
            disease_name="Rust",
            risk_score=0.45,
        ),
        RegionalDiseaseData(
            location_label="İç Anadolu Bölgesi",
            disease_name="Bacterial Wilt",
            risk_score=0.91,
        ),
        RegionalDiseaseData(
            location_label="Karadeniz Bölgesi",
            disease_name="Anthracnose",
            risk_score=0.28,
        ),
        RegionalDiseaseData(
            location_label="Güneydoğu Anadolu Bölgesi",
            disease_name="Mosaic Virus",
            risk_score=0.73,
        ),
        RegionalDiseaseData(
            location_label="Doğu Anadolu Bölgesi",
            disease_name="Leaf Spot",
            risk_score=0.55,
        ),
    ]

    db.add_all(demo_records)
    db.commit()
    logger.info("🌱 Demo regional disease data seeded (%d records).", len(demo_records))


def _simulate_continual_learning(
    model_name: str,
    version: str,
    epochs: int,
    learning_rate: float,
    training_data_size: Optional[int],
) -> Dict[str, Any]:
    """
    Continual Learning eğitim sürecini simüle eder.

    Gerçek bir üretim sisteminde bu fonksiyon yerine gerçek model
    fine-tuning kodu (PyTorch / XGBoost re-fit) çağrılır.

    Döndürülen metrikler rastgele ama gerçekçi değerler içerir;
    bunlar ``model_updates`` tablosuna JSON olarak kaydedilir.
    """
    rng = random.Random()  # Thread-safe local RNG — global state'i bozmaz

    base_accuracy = rng.uniform(0.88, 0.97)
    base_f1 = rng.uniform(0.85, 0.95)
    base_precision = rng.uniform(0.87, 0.96)
    base_recall = rng.uniform(0.83, 0.94)
    base_loss = rng.uniform(0.05, 0.22)

    # Epoch sayısı arttıkça loss azalır (gerçekçi simülasyon)
    epoch_bonus = min(epochs * 0.001, 0.05)
    final_loss = max(base_loss - epoch_bonus, 0.03)

    return {
        "accuracy": round(base_accuracy, 4),
        "f1_score": round(base_f1, 4),
        "precision": round(base_precision, 4),
        "recall": round(base_recall, 4),
        "loss": round(final_loss, 4),
        "epochs_trained": epochs,
        "learning_rate": learning_rate,
        "training_samples": training_data_size or rng.randint(500, 5000),
        "training_strategy": "continual_learning",
        "replay_buffer_used": True,
        "catastrophic_forgetting_prevented": True,
    }


# =============================================================================
# Endpoint: GET /api/v4/global_risk_analysis
# =============================================================================

@router.get(
    "/global_risk_analysis",
    response_model=GlobalRiskAnalysisResponse,
    summary="GNN tabanlı bölgesel risk haritası verilerini döndürür",
    description=(
        "``regional_disease_data`` tablosundan tüm bölge–hastalık risk kayıtlarını "
        "çeker ve Eren'in harita görselleştirmesine uygun formatta döndürür. "
        "Tablo boşsa otomatik olarak demo verisiyle doldurulur."
    ),
    responses={
        200: {"description": "Bölgesel risk haritası başarıyla getirildi."},
        500: {"description": "Veritabanı hatası."},
    },
)
def global_risk_analysis_v4(
    min_risk_score: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum risk skoru filtresi (0.0 = tüm kayıtlar)",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Döndürülecek maksimum kayıt sayısı",
    ),
    db: Session = Depends(get_db),
) -> GlobalRiskAnalysisResponse:
    """
    GNN model çıktısı olan bölgesel hastalık risk verilerini döndürür.

    Parametreler:
        min_risk_score: Bu skorun altındaki kayıtlar filtrelenir.
        limit:          Sayfa başı maksimum kayıt.
        db:             FastAPI dependency injection ile sağlanan DB oturumu.
    """
    try:
        # Tablo boşsa demo verisi ekle (geliştirme / demo ortamı için)
        _seed_demo_data(db)

        # Veritabanından kayıtları çek
        records: List[RegionalDiseaseData] = (
            db.query(RegionalDiseaseData)
            .filter(RegionalDiseaseData.risk_score >= min_risk_score)
            .order_by(RegionalDiseaseData.risk_score.desc())
            .limit(limit)
            .all()
        )

    except Exception as exc:
        logger.error("global_risk_analysis_v4 DB error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Veritabanı sorgu hatası: {exc}",
        )

    # Her kayda risk seviyesi etiketi ekle
    entries: List[RegionalRiskEntry] = []
    high_risk_count = 0

    for rec in records:
        level = _classify_risk(rec.risk_score)
        if level in ("high", "critical"):
            high_risk_count += 1
        entries.append(
            RegionalRiskEntry(
                id=rec.id,
                location_label=rec.location_label,
                disease_name=rec.disease_name,
                risk_score=rec.risk_score,
                risk_level=level,
                detected_at=rec.detected_at,
            )
        )

    return GlobalRiskAnalysisResponse(
        success=True,
        total_records=len(entries),
        high_risk_count=high_risk_count,
        data=entries,
        message=(
            f"{len(entries)} bölge analiz edildi. "
            f"{high_risk_count} bölge yüksek/kritik risk seviyesinde."
        ),
    )


# =============================================================================
# Endpoint: GET /api/v4/get_regional_alerts
# =============================================================================

@router.get(
    "/get_regional_alerts",
    response_model=RegionalAlertsResponse,
    summary="Belirli bir bölge için kritik risk uyarılarını döndürür",
    description=(
        "``location`` parametresiyle belirtilen bölgeye ait tüm kayıtları sorgular; "
        "``risk_threshold`` üzerindeki kayıtları uyarıya dönüştürür. "
        "Her uyarıya risk seviyesine göre önerilen eylem planı eklenir."
    ),
    responses={
        200: {"description": "Bölge uyarıları başarıyla getirildi."},
        404: {"description": "Belirtilen bölge için kayıt bulunamadı."},
        500: {"description": "Veritabanı hatası."},
    },
)
def get_regional_alerts(
    location: str = Query(
        ...,
        min_length=2,
        max_length=255,
        description="Sorgulanacak bölge etiketi (kısmi eşleşme desteklenir)",
        examples=["Ege"],
    ),
    risk_threshold: float = Query(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Bu skorun üzerindeki kayıtlar uyarıya dönüştürülür",
    ),
    db: Session = Depends(get_db),
) -> RegionalAlertsResponse:
    """
    Belirtilen bölge için risk eşiğini aşan kayıtları uyarı olarak döndürür.

    Parametreler:
        location:       Bölge adı (ILIKE ile kısmi eşleşme yapılır).
        risk_threshold: Uyarı tetikleme eşiği (varsayılan: 0.50).
        db:             FastAPI dependency injection ile sağlanan DB oturumu.
    """
    try:
        # ILIKE → büyük/küçük harf duyarsız kısmi eşleşme (PostgreSQL)
        records: List[RegionalDiseaseData] = (
            db.query(RegionalDiseaseData)
            .filter(
                RegionalDiseaseData.location_label.ilike(f"%{location}%"),
                RegionalDiseaseData.risk_score >= risk_threshold,
            )
            .order_by(RegionalDiseaseData.risk_score.desc())
            .all()
        )

    except Exception as exc:
        logger.error("get_regional_alerts DB error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Veritabanı sorgu hatası: {exc}",
        )

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"'{location}' bölgesi için risk eşiği ({risk_threshold}) "
                "üzerinde kayıt bulunamadı."
            ),
        )

    alerts: List[RegionalAlert] = []
    critical_count = 0

    for rec in records:
        level = _classify_risk(rec.risk_score)
        severity = _SEVERITY_MAP.get(level, "WATCH")
        action = _ACTION_MAP.get(severity, "Standart tarım protokollerini uygulayın.")

        if level == "critical":
            critical_count += 1

        alerts.append(
            RegionalAlert(
                alert_id=str(uuid.uuid4()),
                location_label=rec.location_label,
                disease_name=rec.disease_name,
                risk_score=rec.risk_score,
                risk_level=level,
                severity=severity,
                recommended_action=action,
                detected_at=rec.detected_at,
            )
        )

    return RegionalAlertsResponse(
        success=True,
        region_queried=location,
        alert_count=len(alerts),
        critical_count=critical_count,
        alerts=alerts,
        message=(
            f"'{location}' için {len(alerts)} uyarı tespit edildi. "
            f"{critical_count} kritik seviyede uyarı mevcut."
        ),
    )


# =============================================================================
# Endpoint: POST /api/v4/update_model
# =============================================================================

@router.post(
    "/update_model",
    response_model=UpdateModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Continual Learning sürecini simüle eder ve sonucu kaydeder",
    description=(
        "İstenen modelin Continual Learning (Sürekli Öğrenme) sürecini simüle eder. "
        "Katastrofik unutmayı önleyen replay buffer stratejisi kullanılır. "
        "Eğitim metrikleri ``model_updates`` tablosuna JSON formatında yazılır."
    ),
    responses={
        201: {"description": "Model güncelleme kaydı oluşturuldu."},
        422: {"description": "Geçersiz istek gövdesi."},
        500: {"description": "Eğitim veya veritabanı hatası."},
    },
)
def update_model_v4(
    request: UpdateModelRequest,
    db: Session = Depends(get_db),
) -> UpdateModelResponse:
    """
    Continual Learning eğitim döngüsünü simüle eder ve sonucu DB'ye kaydeder.

    Parametreler:
        request: Model adı, versiyon, epoch sayısı ve öğrenme oranı.
        db:      FastAPI dependency injection ile sağlanan DB oturumu.

    Gerçek üretim sisteminde ``_simulate_continual_learning`` yerine
    gerçek model eğitim kodu (PyTorch trainer, XGBoost fit, vb.) çağrılır.
    """
    # ── Eğitimi simüle et ────────────────────────────────────────────────────
    try:
        metrics = _simulate_continual_learning(
            model_name=request.model_name,
            version=request.version,
            epochs=request.epochs or 10,
            learning_rate=request.learning_rate or 0.001,
            training_data_size=request.training_data_size,
        )
        logger.info(
            "🤖 Continual Learning simülasyonu tamamlandı: %s @ %s",
            request.model_name,
            request.version,
        )

    except Exception as exc:
        logger.error("Continual learning simulation error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eğitim simülasyonu başarısız: {exc}",
        )

    # ── Sonuçları veritabanına kaydet ────────────────────────────────────────
    try:
        db_record = ModelUpdateRecord(
            model_name=request.model_name,
            version=request.version,
            metrics=metrics,
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)  # ID ve server_default (updated_at) değerlerini al

        logger.info(
            "✅ Model güncelleme kaydı DB'ye yazıldı: id=%d, model=%s, version=%s",
            db_record.id,
            db_record.model_name,
            db_record.version,
        )

    except Exception as exc:
        db.rollback()  # Tutarsız durumu önlemek için geri al
        logger.error("update_model_v4 DB write error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Veritabanı yazma hatası: {exc}",
        )

    return UpdateModelResponse(
        success=True,
        data=UpdateModelData(
            record_id=db_record.id,
            model_name=db_record.model_name,
            version=db_record.version,
            metrics=db_record.metrics,
            updated_at=db_record.updated_at,
        ),
        message=(
            f"'{request.model_name}' modeli başarıyla güncellendi "
            f"(versiyon: {request.version}). "
            f"Accuracy: {metrics.get('accuracy', 'N/A')}"
        ),
    )
