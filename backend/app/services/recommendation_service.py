# =============================================================================
# services/recommendation_service.py
#
# Sprint 3 — Tarım Karar Destek Sistemi (Kural Motoru)
#
# Bu servis iki temel işlev sunar:
#   1. Kural tabanlı tarım önerisi üretimi (iklim + bitki sağlığı → tavsiye)
#   2. Zirai ilaç veritabanı (pesticides.json) üzerinden hastalığa göre ilaç eşleştirme
#
# Mimari notlar:
#   - Tamamen rule-based (ML gerektirmez); modeller yüklü olmasa bile çalışır.
#   - pesticides.json yalnızca bir kez okunur ve bellekte saklanır (lazy load).
#   - Tüm public fonksiyonlar type-hinted ve loglama içerir.
#   - Endpoint katmanı yalnızca get_farming_advice() ve get_pesticide_recommendations()
#     fonksiyonlarını çağırır.
# =============================================================================

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler — Dosya Yolu
# ---------------------------------------------------------------------------

# Bu dosya: backend/app/services/recommendation_service.py
# Hedef:     backend/app/data/pesticides.json
_PESTICIDES_PATH: Path = (
    Path(__file__).resolve().parent.parent / "data" / "pesticides.json"
)

# Risk seviyesi eşikleri (0-100 ölçeği)
_RISK_LOW_THRESHOLD:    float = 25.0
_RISK_MEDIUM_THRESHOLD: float = 50.0
_RISK_HIGH_THRESHOLD:   float = 75.0


# ---------------------------------------------------------------------------
# Pesticide Veritabanı — Lazy Loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_pesticide_db() -> dict[str, Any]:
    """
    pesticides.json dosyasını diskten okur ve bellekte önbelleğe alır.

    lru_cache(maxsize=1) sayesinde ilk çağrıda yüklenir, sonraki
    çağrılarda disk I/O olmadan aynı dict döner.

    Returns:
        pesticides.json içeriği (dict).

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        json.JSONDecodeError: JSON formatı bozuksa.
    """
    if not _PESTICIDES_PATH.exists():
        raise FileNotFoundError(
            f"Pesticide veritabanı bulunamadı: {_PESTICIDES_PATH}\n"
            "backend/app/data/pesticides.json dosyasının var olduğundan emin olun."
        )
    logger.info("Pesticide veritabanı yükleniyor: %s", _PESTICIDES_PATH)
    with open(_PESTICIDES_PATH, "r", encoding="utf-8") as fh:
        db = json.load(fh)
    logger.info(
        "✅ Pesticide veritabanı yüklendi. Hastalık sayısı: %d",
        len(db.get("diseases", {})),
    )
    return db


# ---------------------------------------------------------------------------
# Yardımcı: Risk Seviyesi Hesabı
# ---------------------------------------------------------------------------

def _classify_risk_level(risk_score: float) -> tuple[str, str, str]:
    """
    0-100 arasındaki risk skorunu seviye, etiket ve renk koduna çevirir.

    Args:
        risk_score: 0-100 arasında normalize edilmiş risk skoru.

    Returns:
        (risk_level, risk_label, risk_color) üçlüsü.
    """
    if risk_score < _RISK_LOW_THRESHOLD:
        return "Low", "Low Risk", "#22c55e"
    if risk_score < _RISK_MEDIUM_THRESHOLD:
        return "Medium", "Medium Risk", "#f59e0b"
    if risk_score < _RISK_HIGH_THRESHOLD:
        return "High", "High Risk", "#f97316"
    return "Critical", "Critical Risk", "#ef4444"


# ---------------------------------------------------------------------------
# Kural Motoru — Tarım Önerisi Üretimi
# ---------------------------------------------------------------------------

def _apply_humidity_rules(
    humidity: float,
    risk_score: float,
    advice: list[str],
) -> float:
    """
    Nem kurallarını uygular ve risk skorunu ayarlar.

    Kural: humidity > 80 → risk artar, fungisit öner.
    """
    if humidity > 80:
        advice.append(
            f"🌫️ Bağıl nem çok yüksek (%{humidity:.0f}). "
            "Bitkiler arasındaki hava sirkülasyonunu artırın ve "
            "fungal hastalık baskısı için koruyucu fungisit uygulayın."
        )
        risk_score = min(risk_score + 10.0, 100.0)
    elif humidity > 65:
        advice.append(
            f"💧 Nem orta-yüksek (%{humidity:.0f}). "
            "Yaprakların uzun süre ıslak kalmaması için sabah sulayın."
        )
        risk_score = min(risk_score + 5.0, 100.0)
    elif humidity < 30:
        advice.append(
            f"🏜️ Nem çok düşük (%{humidity:.0f}). "
            "Bitkilerde su stresi oluşabilir; sulama sıklığını artırın."
        )
    return risk_score


def _apply_temperature_rules(
    temperature: float,
    advice: list[str],
) -> None:
    """Sıcaklık kurallarını uygular."""
    if 18.0 <= temperature <= 28.0:
        advice.append(
            f"🌡️ Sıcaklık ({temperature:.1f}°C) mantar gelişimi için "
            "optimal aralıkta. Yaprak izleme sıklığını artırın."
        )
    elif temperature > 35.0:
        advice.append(
            f"🔥 Yüksek sıcaklık ({temperature:.1f}°C) bitkileri strese sokar. "
            "Serin saatlerde (sabah/akşam) sulayın; gölgeleme değerlendirin."
        )
    elif temperature < 5.0:
        advice.append(
            f"❄️ Düşük sıcaklık ({temperature:.1f}°C). "
            "Aşırı sulama kök çürüklüğüne yol açabilir; sulamayı kısın."
        )


def _apply_rainfall_rules(
    rainfall: float,
    risk_score: float,
    advice: list[str],
) -> float:
    """Yağış kurallarını uygular."""
    if rainfall > 100.0:
        advice.append(
            f"🌧️ Çok yüksek yağış ({rainfall:.0f} mm). "
            "Drenajı kontrol edin; toprak kaynaklı hastalıklar (kök çürüklüğü) riski var."
        )
        risk_score = min(risk_score + 8.0, 100.0)
    elif rainfall > 50.0:
        advice.append(
            f"🌦️ Orta yağış ({rainfall:.0f} mm). "
            "Yağış sonrası yaprak lekesi ve külleme belirtilerini kontrol edin."
        )
        risk_score = min(risk_score + 4.0, 100.0)
    return risk_score


def _apply_wind_rules(
    wind_speed: float,
    advice: list[str],
) -> None:
    """Rüzgar kurallarını uygular."""
    if wind_speed > 40.0:
        advice.append(
            f"💨 Kuvvetli rüzgar ({wind_speed:.0f} km/s). "
            "Spor yayılımı hızlanır; ilaçlama planını rüzgarsız güne erteleyebilirsiniz."
        )
    elif wind_speed > 20.0:
        advice.append(
            f"🌬️ Orta rüzgar ({wind_speed:.0f} km/s). "
            "İlaçlama yaparken sürüklenmeye (drift) dikkat edin."
        )


def _apply_season_rules(
    season: str,
    advice: list[str],
) -> None:
    """Mevsime özgü tarım önerisi ekler."""
    season_tips: dict[str, str] = {
        "spring": (
            "🌸 İlkbahar dönemi: Islak ve ılık hava mantar salgınlarına zemin hazırlar. "
            "Kükürt bazlı koruyucu fungisit uygulamasına başlayın."
        ),
        "summer": (
            "☀️ Yaz dönemi: Yangın yanıklığı ve bakteriyel hastalık riski artar. "
            "Sabah erkenden sulayın; yaprakları ıslak bırakmayın."
        ),
        "autumn": (
            "🍂 Sonbahar dönemi: Pas ve külleme için elverişli. "
            "Bakır bazlı fungisit ile düzenli koruyucu uygulama yapın."
        ),
        "winter": (
            "❄️ Kış dönemi: Bitki bağışıklığı zayıflar. "
            "Aşırı sulamadan kaçının; kök çürüklüğü riskini azaltın."
        ),
    }
    tip = season_tips.get(season.lower())
    if tip:
        advice.append(tip)


def _apply_health_status_rules(
    plant_health_status: str,
    risk_score: float,
    advice: list[str],
) -> float:
    """
    Bitki sağlık durumuna göre kural uygular.

    Kural: diseased → risk maksimuma yaklaşır, acil müdahale öner.
    """
    status = plant_health_status.strip().lower()
    if status == "diseased":
        advice.append(
            "⚠️ Bitki HASTA olarak işaretlenmiş. "
            "Etkilenen yaprakları hemen uzaklaştırın ve kompost etmeyin. "
            "Ziraat mühendisiyle iletişime geçin."
        )
        risk_score = min(risk_score + 20.0, 100.0)
    elif status == "stressed":
        advice.append(
            "🟡 Bitki STRESDE. Sulama programını gözden geçirin ve "
            "dengeli beslenmeyi (NPK) kontrol edin."
        )
        risk_score = min(risk_score + 10.0, 100.0)
    elif status == "healthy":
        advice.append(
            "✅ Bitki şu an SAĞLIKLI. Rutin bakım ve düzenli izlemeye devam edin."
        )
    return risk_score


def _build_irrigation_advice(
    humidity: float,
    rainfall: float,
    temperature: float,
) -> str:
    """
    İklim koşullarına göre sulama önerisi üretir.

    Args:
        humidity:    Bağıl nem (%).
        rainfall:    Yağış miktarı (mm).
        temperature: Sıcaklık (°C).

    Returns:
        Sulama önerisi string'i.
    """
    if rainfall > 50.0:
        return (
            "Son yağışlar yeterli nem sağladı. "
            "Sulama ihtiyacını toprak nem ölçümüyle doğrulayın; "
            "gereksiz sulama kök çürüklüğüne yol açabilir."
        )
    if temperature > 30.0 and humidity < 50.0:
        return (
            "Yüksek sıcaklık ve düşük nem nedeniyle sabah 06:00-08:00 "
            "arasında bol ama seyrek sulama yapın. "
            "Damlama sulama sistemi önerilir."
        )
    if humidity > 75.0:
        return (
            "Nem zaten yüksek. Sulama miktarını azaltın; "
            "akşam sulamaktan kesinlikle kaçının."
        )
    return (
        "Sabah erken saatlerde sulayın; yaprakların gün batımından "
        "önce kuruyacağından emin olun."
    )


# ---------------------------------------------------------------------------
# Pesticide Eşleştirici
# ---------------------------------------------------------------------------

def get_pesticide_recommendations(
    disease_name: Optional[str],
) -> list[dict[str, Any]]:
    """
    Hastalık adına göre pesticides.json'dan ilaç önerilerini döndürür.

    Args:
        disease_name: Hastalık adı (örn. "Powdery Mildew", "Apple Scab").
                      None veya boş string verilirse boş liste döner.

    Returns:
        İlaç öneri sözlüklerinin listesi. Hastalık bulunamazsa [] döner.
    """
    if not disease_name:
        logger.debug("Hastalık adı belirtilmedi; ilaç önerisi atlandı.")
        return []

    try:
        db = _load_pesticide_db()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Pesticide DB yüklenemedi: %s", exc)
        return []

    diseases: dict[str, Any] = db.get("diseases", {})

    # Tam eşleşme dene (büyük/küçük harf duyarsız)
    disease_key: Optional[str] = None
    disease_name_lower = disease_name.strip().lower()
    for key in diseases:
        if key.lower() == disease_name_lower:
            disease_key = key
            break

    # Kısmi eşleşme dene (içeriyor mu?)
    if disease_key is None:
        for key in diseases:
            if disease_name_lower in key.lower() or key.lower() in disease_name_lower:
                disease_key = key
                logger.info(
                    "Hastalık '%s' için kısmi eşleşme bulundu: '%s'",
                    disease_name,
                    key,
                )
                break

    if disease_key is None:
        logger.warning(
            "Hastalık '%s' pesticide veritabanında bulunamadı.", disease_name
        )
        return []

    entry = diseases[disease_key]
    recs: list[dict[str, Any]] = entry.get("recommendations", [])

    # Sağlıklı bitki → öneri yok
    if entry.get("pathogen_type", "") == "none":
        return []

    # Her öneriyi standart formata çevir
    result: list[dict[str, Any]] = []
    for rec in recs:
        result.append({
            "disease":            disease_key,
            "product_type":       rec.get("product_type", "unknown"),
            "active_ingredient":  rec.get("active_ingredient", "unknown"),
            "product_name":       rec.get("product_name", "unknown"),
            "application_notes":  rec.get("application_notes", ""),
            "pre_harvest_interval_days": rec.get("pre_harvest_interval_days", 0),
            "safety_notes":       rec.get("safety_notes", ""),
        })

    logger.info(
        "Hastalık '%s' için %d ilaç önerisi döndürüldü.", disease_name, len(result)
    )
    return result


# ---------------------------------------------------------------------------
# Ana Public API
# ---------------------------------------------------------------------------

def get_farming_advice(
    temperature: float,
    humidity: float,
    rainfall: float,
    wind_speed: float,
    season: str,
    plant_health_status: str = "healthy",
    disease_name: Optional[str] = None,
    crop_type: Optional[str] = None,
    base_risk_score: float = 0.0,
) -> dict[str, Any]:
    """
    Kural motoru tabanlı tarım danışma raporu üretir.

    İklim verileri ve bitki sağlık durumuna göre:
      - Tarımsal öneriler listesi
      - Sulama tavsiyesi
      - Genel gözlem notu
      - Hesaplanan risk seviyesi
      - Pesticide eşleştirme (disease_name verilmişse)

    Args:
        temperature:         Hava sıcaklığı (°C).
        humidity:            Bağıl nem (%).
        rainfall:            Yağış miktarı (mm).
        wind_speed:          Rüzgar hızı (km/s).
        season:              Mevsim: 'spring', 'summer', 'autumn', 'winter'.
        plant_health_status: 'healthy', 'stressed', 'diseased'.
        disease_name:        Tespit edilmiş hastalık adı (opsiyonel).
        crop_type:           Bitki/ürün türü (opsiyonel, şu an loglama için).
        base_risk_score:     0-100 arası başlangıç risk skoru (örn. XGBoost çıktısı).
                             Kural motoru bu değer üzerine ekleme/düzeltme yapar.

    Returns:
        {
            "risk_score":               float,       # 0-100
            "risk_level":               str,         # Low|Medium|High|Critical
            "risk_label":               str,
            "risk_color":               str,         # hex renk kodu
            "farming_advice":           list[str],
            "pesticide_recommendations":list[dict],
            "irrigation_advice":        str,
            "general_notes":            str,
        }
    """
    logger.info(
        "Tarım öneri motoru çalışıyor | sıc=%.1f°C nem=%.0f%% yağış=%.0fmm "
        "mevsim=%s sağlık=%s hastalık=%s ürün=%s",
        temperature, humidity, rainfall, season,
        plant_health_status, disease_name, crop_type,
    )

    farming_advice: list[str] = []
    risk_score: float = float(base_risk_score)

    # ── Kural Bloğu 1: Nem ───────────────────────────────────────────────────
    risk_score = _apply_humidity_rules(humidity, risk_score, farming_advice)

    # ── Kural Bloğu 2: Sıcaklık ─────────────────────────────────────────────
    _apply_temperature_rules(temperature, farming_advice)

    # ── Kural Bloğu 3: Yağış ────────────────────────────────────────────────
    risk_score = _apply_rainfall_rules(rainfall, risk_score, farming_advice)

    # ── Kural Bloğu 4: Rüzgar ───────────────────────────────────────────────
    _apply_wind_rules(wind_speed, farming_advice)

    # ── Kural Bloğu 5: Mevsim ───────────────────────────────────────────────
    _apply_season_rules(season, farming_advice)

    # ── Kural Bloğu 6: Bitki Sağlığı ────────────────────────────────────────
    risk_score = _apply_health_status_rules(
        plant_health_status, risk_score, farming_advice
    )

    # ── Genel Not ────────────────────────────────────────────────────────────
    risk_level, risk_label, risk_color = _classify_risk_level(risk_score)

    general_notes: str
    if risk_score >= 75.0:
        general_notes = (
            f"⚠️ Risk skoru {risk_score:.1f}/100 — KRİTİK SEVİYE. "
            "Uzman ziraat mühendisi ile iletişime geçmeniz önerilir."
        )
    elif risk_score >= 50.0:
        general_notes = (
            f"Risk skoru {risk_score:.1f}/100 — Yüksek. "
            "Önleyici tedbirler alınmazsa hastalık yayılabilir."
        )
    elif risk_score >= 25.0:
        general_notes = (
            f"Risk skoru {risk_score:.1f}/100 — Orta. "
            "Düzenli izlemeye devam edin."
        )
    else:
        general_notes = (
            f"Risk skoru {risk_score:.1f}/100 — Düşük. "
            "Koşullar şu an nispeten güvenli."
        )

    # ── Sulama Önerisi ───────────────────────────────────────────────────────
    irrigation_advice = _build_irrigation_advice(humidity, rainfall, temperature)

    # ── Pesticide Eşleştirme ─────────────────────────────────────────────────
    pesticide_recs = get_pesticide_recommendations(disease_name)

    # Öneri yoksa ama risk yüksekse genel uyarı ekle
    if not pesticide_recs and risk_score >= 50.0:
        farming_advice.append(
            "💊 Genel önlem: Lokal ziraat müdürlüğünden bölgenize uygun "
            "fungisit/bakterisit önerisi alın."
        )

    return {
        "risk_score":                round(risk_score, 2),
        "risk_level":                risk_level,
        "risk_label":                risk_label,
        "risk_color":                risk_color,
        "farming_advice":            farming_advice,
        "pesticide_recommendations": pesticide_recs,
        "irrigation_advice":         irrigation_advice,
        "general_notes":             general_notes,
    }
