 # =============================================================================
# services/risk_service.py
#
# Sprint 3 — Plant Risk Prediction Service
#
# Bu servis, eğitilmiş XGBoost risk modelini bellekte tek seferlik
# (singleton) yükler ve `predict_risk()` fonksiyonu ile bitki hastalık
# riski tahmini yapar.
#
# Mimari notlar:
#   - Mevcut `core/model_manager.py` ağır AI modelleri içindir.
#   - Risk modeli hafiftir (~MB ölçeğinde) ve bağımsızdır; bu yüzden
#     ayrı bir singleton (`RiskModelStore`) olarak yönetilir.
#   - Uygulama başlangıcında `risk_model_store.load()` çağrılır (main.py).
#   - Endpoint katmanı `predict_risk(data)` üzerinden tahmin alır.
# =============================================================================

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Eğitim scripti ile birebir aynı yol
_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
RISK_MODEL_PATH = _MODELS_DIR / "risk_model.pkl"

# Risk seviyesi eşikleri
LOW_THRESHOLD = 0.34
HIGH_THRESHOLD = 0.67

# Doğrulama aralıkları (eğitim verisi aralığına yakın esnek sınırlar)
_BOUNDS = {
    "temperature": (-20.0, 60.0),     # °C
    "humidity": (0.0, 100.0),         # %
    "rainfall": (0.0, 500.0),         # mm/gün
    "wind_speed": (0.0, 200.0),       # km/sa
    "soil_moisture": (0.0, 100.0),    # %
}


# ---------------------------------------------------------------------------
# Özel Hata Sınıfları
# ---------------------------------------------------------------------------

class RiskModelNotLoadedError(RuntimeError):
    """Risk modeli henüz yüklenmemişse fırlatılır."""


class RiskInputValidationError(ValueError):
    """Geçersiz girdi (eksik alan, tip hatası, sınır dışı değer)."""


# ---------------------------------------------------------------------------
# Singleton Model Store
# ---------------------------------------------------------------------------

class RiskModelStore:
    """
    Risk modelini ve metadata'sını bellekte tutan singleton.

    Attributes:
        model:          XGBRegressor örneği.
        feature_order:  Özelliklerin model girişindeki sırası.
        season_map:     "spring/summer/autumn/winter" → int eşlemesi.
        metrics:        Eğitim sırasındaki RMSE/R².
        version:        Model sürümü.
        is_loaded:      Yükleme durumu bayrağı.
    """

    def __init__(self) -> None:
        self.model: Optional[Any] = None
        self.feature_order: List[str] = []
        self.season_map: Dict[str, int] = {}
        self.metrics: Dict[str, float] = {}
        self.version: Optional[str] = None
        self.is_loaded: bool = False

    # -- Yaşam Döngüsü --------------------------------------------------------

    def load(self, path: Path = RISK_MODEL_PATH) -> None:
        """
        Modeli pickle dosyasından belleğe yükler.

        Raises:
            FileNotFoundError: Dosya yoksa (eğitim scripti henüz çalıştırılmamış).
            RuntimeError:      Bozuk pickle / uyumsuz format.
        """
        if not path.exists():
            raise FileNotFoundError(
                f"Risk model dosyası bulunamadı: {path}\n"
                f"   Önce eğitim scriptini çalıştırın:\n"
                f"   python -m app.ml.train_risk_model"
            )

        try:
            with open(path, "rb") as f:
                payload = pickle.load(f)
        except Exception as exc:
            raise RuntimeError(f"Risk modeli yüklenemedi: {exc}") from exc

        # Beklenen anahtarlar
        for key in ("model", "feature_order", "season_map"):
            if key not in payload:
                raise RuntimeError(
                    f"Risk modeli bozuk: '{key}' alanı eksik. "
                    "Eğitim scriptini yeniden çalıştırın."
                )

        self.model = payload["model"]
        self.feature_order = list(payload["feature_order"])
        self.season_map = dict(payload["season_map"])
        self.metrics = dict(payload.get("metrics", {}))
        self.version = payload.get("version", "unknown")
        self.is_loaded = True

        logger.info(
            f"✅ Risk modeli yüklendi (v{self.version}) | "
            f"RMSE: {self.metrics.get('rmse', 'n/a')} | "
            f"Özellikler: {self.feature_order}"
        )

    def unload(self) -> None:
        """Bellekteki modeli temizler."""
        self.model = None
        self.feature_order = []
        self.season_map = {}
        self.metrics = {}
        self.version = None
        self.is_loaded = False
        logger.info("♻️  Risk modeli bellekten kaldırıldı.")


# Tek global örnek — main.py içinden import edilir
risk_model_store = RiskModelStore()


# ---------------------------------------------------------------------------
# Girdi Doğrulama
# ---------------------------------------------------------------------------

def _validate_and_prepare(data: Dict[str, Any]) -> np.ndarray:
    """
    Gelen sözlüğü doğrular ve modelin beklediği sırayla numpy dizisine çevirir.

    Args:
        data: Frontend'den/endpoint'ten gelen sözlük.
              Anahtarlar: temperature, humidity, rainfall, wind_speed,
              soil_moisture, season ('spring'|'summer'|'autumn'|'winter' veya int 0-3).

    Returns:
        Şekil (1, 6) numpy dizisi → model.predict() için hazır.

    Raises:
        RiskInputValidationError: Eksik / hatalı / sınır dışı alanlar.
    """
    if not isinstance(data, dict):
        raise RiskInputValidationError("Girdi bir sözlük (dict) olmalıdır.")

    if not risk_model_store.is_loaded:
        raise RiskModelNotLoadedError("Risk modeli henüz yüklenmedi.")

    feature_order = risk_model_store.feature_order
    season_map = risk_model_store.season_map

    # Eksik alan kontrolü
    missing = [k for k in feature_order if k not in data]
    if missing:
        raise RiskInputValidationError(
            f"Eksik alan(lar): {missing}. Beklenen alanlar: {feature_order}"
        )

    row: List[float] = []

    for feat in feature_order:
        value = data[feat]

        # ----- season alanı: string veya int -----
        if feat == "season":
            if isinstance(value, str):
                key = value.strip().lower()
                if key not in season_map:
                    raise RiskInputValidationError(
                        f"Geçersiz mevsim: '{value}'. "
                        f"Beklenen: {list(season_map.keys())}"
                    )
                row.append(float(season_map[key]))
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                ivalue = int(value)
                if ivalue not in season_map.values():
                    raise RiskInputValidationError(
                        f"Geçersiz mevsim kodu: {ivalue}. "
                        f"Beklenen: {sorted(season_map.values())}"
                    )
                row.append(float(ivalue))
            else:
                raise RiskInputValidationError(
                    f"'season' alanı string veya integer olmalı, alındı: {type(value).__name__}"
                )
            continue

        # ----- Sayısal alanlar -----
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RiskInputValidationError(
                f"'{feat}' sayısal olmalı, alındı: {type(value).__name__}"
            )

        fvalue = float(value)

        if np.isnan(fvalue) or np.isinf(fvalue):
            raise RiskInputValidationError(f"'{feat}' geçerli bir sayı değil.")

        lo, hi = _BOUNDS[feat]
        if not (lo <= fvalue <= hi):
            raise RiskInputValidationError(
                f"'{feat}' aralık dışı: {fvalue} (beklenen: [{lo}, {hi}])"
            )

        row.append(fvalue)

    return np.array([row], dtype=np.float32)


# ---------------------------------------------------------------------------
# Risk Seviyesi Hesabı
# ---------------------------------------------------------------------------

def _risk_level(score: float) -> str:
    """
    Sürekli risk skorunu (0–1) ayrık etikete çevirir.
      0.00 – 0.34  → low
      0.34 – 0.67  → medium
      0.67 – 1.00  → high
    """
    if score < LOW_THRESHOLD:
        return "low"
    if score < HIGH_THRESHOLD:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict_risk(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verilen çevre verilerine göre bitki hastalık riski tahmini yapar.

    Args:
        data: 6 alanlı sözlük (bkz. _validate_and_prepare).

    Returns:
        {
          "risk_score": float (0.0–1.0, 4 ondalık),
          "risk_level": "low" | "medium" | "high",
          "model_version": str,
        }

    Raises:
        RiskModelNotLoadedError: Model yüklenmemişse.
        RiskInputValidationError: Geçersiz girdi.
        RuntimeError: Inference sırasında beklenmeyen hata.
    """
    X = _validate_and_prepare(data)

    try:
        raw_pred = risk_model_store.model.predict(X)
    except Exception as exc:  # pragma: no cover
        logger.error(f"Risk inference hatası: {exc}")
        raise RuntimeError(f"Risk modeli çalıştırma hatası: {exc}") from exc

    # XGBoost float32 dönebilir; clipleyip Python float yap
    score = float(np.clip(raw_pred[0], 0.0, 1.0))

    return {
        "risk_score": round(score, 4),
        "risk_level": _risk_level(score),
        "model_version": risk_model_store.version or "unknown",
    }
