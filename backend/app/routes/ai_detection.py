# =============================================================================
# routes/ai_detection.py
# Bu dosya AI tabanlı bitki hastalık tespiti için API endpointlerini tanımlar.
#
# ⚠️ SPRINT 1 DURUMU: Bu endpointler DUMMY (sahte) yanıt döndürür.
#    Gerçek AI entegrasyonu Sprint 2'de yapılacak.
#    Şu an sadece API yapısı ve endpoint yolları tanımlanmıştır.
# =============================================================================

from fastapi import APIRouter, UploadFile, File
from typing import Dict, Any

router = APIRouter(
    prefix="/ai",
    tags=["AI Detection (Sprint 2)"]  # Swagger'da ayrı bir grup oluşturur
)


@router.post(
    "/upload_image",
    summary="Bitki görseli yükle",
    description=(
        "Analiz edilecek bitki görselini sisteme yükler. "
        "⚠️ Sprint 2'de gerçek dosya yükleme ve AI analizi entegre edilecek."
    )
)
async def upload_image(
    file: UploadFile = File(
        ...,
        description="Analiz edilecek bitki görseli (JPG, PNG, WEBP)"
    )
) -> Dict[str, Any]:
    """
    Bitki görseli yükleme endpoint'i.

    Sprint 2'de yapılacaklar:
    - Görseli sunucuya veya cloud storage'a kaydet (AWS S3, GCS, vb.)
    - Dosya türü ve boyutunu doğrula
    - Yükleme işlemini logla
    - Upload edilen dosyanın URL'sini döndür
    """
    return {
        "status": "placeholder",
        "message": "This endpoint will be implemented in Sprint 2",
        "planned_features": [
            "Image upload to storage (AWS S3 / local)",
            "File type validation (JPG, PNG, WEBP)",
            "Max file size check (10MB)",
            "Return image URL for AI processing"
        ],
        # Alınan dosya adını göster (en azından dosya geldiğini kanıtla)
        "received_filename": file.filename if file else None
    }


@router.post(
    "/detect_disease",
    summary="Bitki hastalığını tespit et",
    description=(
        "Yüklenen görseli AI modeline göndererek hastalık tespiti yapar. "
        "⚠️ Sprint 2'de gerçek AI modeli (TensorFlow / PyTorch) entegre edilecek."
    )
)
async def detect_disease(image_url: str = None) -> Dict[str, Any]:
    """
    AI Hastalık Tespiti endpoint'i.

    Sprint 2'de yapılacaklar:
    - Görseli AI modeline gönder (TensorFlow/PyTorch)
    - Modelin döndürdüğü tahmin sınıfını al
    - Güven skorunu hesapla
    - Sonuçları disease_records tablosuna kaydet
    - Detaylı hastalık raporu döndür
    """
    return {
        "status": "placeholder",
        "message": "This endpoint will be implemented in Sprint 2",
        "planned_features": [
            "AI model inference (TensorFlow / PyTorch)",
            "Disease classification from plant image",
            "Confidence score calculation (0.0 - 1.0)",
            "Save result to disease_records table",
            "Return detailed disease report"
        ]
    }


@router.get(
    "/get_risk_prediction",
    summary="Hastalık risk tahmini al",
    description=(
        "Geçmiş hastalık kayıtlarına göre bitkinin risk durumunu analiz eder. "
        "⚠️ Sprint 2/3'te gerçek risk analizi algoritması entegre edilecek."
    )
)
async def get_risk_prediction(plant_id: int = None) -> Dict[str, Any]:
    """
    Risk Tahmin endpoint'i.

    Sprint 2/3'te yapılacaklar:
    - Bitkinin geçmiş disease_records kayıtlarını analiz et
    - Mevsimsel ve çevresel faktörleri hesaba kat
    - Risk skoru hesapla (LOW / MEDIUM / HIGH / CRITICAL)
    - Önleyici tedbirler öner
    - Trend analizi yap (hastalık kötüleşiyor mu, iyileşiyor mu?)
    """
    return {
        "status": "placeholder",
        "message": "This endpoint will be implemented in Sprint 2/3",
        "planned_features": [
            "Historical disease record analysis",
            "Risk score calculation (LOW/MEDIUM/HIGH/CRITICAL)",
            "Seasonal risk factors",
            "Preventive treatment recommendations",
            "Disease trend analysis"
        ]
    }
