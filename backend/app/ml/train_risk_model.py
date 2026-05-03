 
# =============================================================================
# ml/train_risk_model.py
#
# Sprint 3 — Plant Risk Prediction System
#
# Bu script, yapısal çevre verilerinden (sıcaklık, nem, yağış, rüzgar,
# toprak nemi, mevsim) bitki hastalık riski (0–1) tahmin eden bir
# XGBoost regressor eğitir.
#
# Çalıştırmak için:
#   cd backend
#   python -m app.ml.train_risk_model
#
# Çıktı:
#   backend/models/risk_model.pkl   → eğitilmiş model + metadata
# =============================================================================

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s → %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Model dosyası, mevcut model klasörü ile aynı yere kaydedilir
# (backend/app/core/model_manager.py içindeki _MODELS_DIR ile uyumlu)
_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
MODEL_PATH = _MODELS_DIR / "risk_model.pkl"

# Mevsim adları → sayısal kodlama (ordinal)
SEASON_MAP: Dict[str, int] = {
    "spring": 0,
    "summer": 1,
    "autumn": 2,
    "winter": 3,
}

# Eğitim sırasında kullanılan özellik sırası — inference sırasında AYNI olmalı.
FEATURE_ORDER: List[str] = [
    "temperature",
    "humidity",
    "rainfall",
    "wind_speed",
    "soil_moisture",
    "season",
]

RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Sentetik Veri Üretici
# ---------------------------------------------------------------------------

@dataclass
class DatasetConfig:
    """Sentetik veri üretimi için konfigürasyon."""
    n_samples: int = 5000
    test_size: float = 0.2
    seed: int = RANDOM_SEED


def generate_synthetic_dataset(config: DatasetConfig) -> pd.DataFrame:
    """
    Çevresel özelliklerden hastalık riski (0–1) üretir.

    Risk modellemesi (domain bilgisine dayalı):
      - Yüksek nem (humidity > 70) + ılık sıcaklık → yüksek risk (mantar)
      - Aşırı yağış + düşük rüzgar → yüksek risk (durağan su)
      - Aşırı soil moisture (>%80) → kök hastalıkları
      - Aşırı sıcak / aşırı soğuk → stres riski
      - Mevsim katsayısı: yaz/sonbahar daha riskli

    Returns:
        n_samples × 7 sütunlu DataFrame (6 özellik + risk_score).
    """
    rng = np.random.default_rng(config.seed)
    n = config.n_samples

    # Özellikler — gerçekçi aralıklar
    temperature = rng.uniform(-5.0, 45.0, size=n)        # °C
    humidity = rng.uniform(10.0, 100.0, size=n)          # %
    rainfall = rng.uniform(0.0, 200.0, size=n)           # mm/gün
    wind_speed = rng.uniform(0.0, 40.0, size=n)          # km/sa
    soil_moisture = rng.uniform(0.0, 100.0, size=n)      # %
    season = rng.integers(0, 4, size=n)                  # 0–3

    # ----- Risk skoru hesabı (deterministik formül + gürültü) -----
    # Sıcaklık riski: optimum 20–28°C (düşük risk); uçlar yüksek risk
    temp_risk = np.where(
        (temperature >= 20) & (temperature <= 28),
        0.1,
        np.minimum(1.0, np.abs(temperature - 24) / 25.0),
    )

    # Nem riski: humidity > 70 → mantar riski katlanarak artar
    humidity_risk = np.clip((humidity - 50) / 50.0, 0.0, 1.0) ** 1.5

    # Yağış riski: 0–10 mm güvenli; >50 mm yüksek risk
    rain_risk = np.clip(rainfall / 100.0, 0.0, 1.0)

    # Rüzgar riski: düşük rüzgar + yüksek nem → kötü; yüksek rüzgar = iyi
    wind_factor = 1.0 - np.clip(wind_speed / 25.0, 0.0, 1.0)
    wind_risk = wind_factor * humidity_risk * 0.6

    # Toprak nemi riski: çok düşük (kuraklık) veya çok yüksek (kök çürüklüğü)
    soil_risk = np.where(
        soil_moisture < 20, (20 - soil_moisture) / 20.0,
        np.where(soil_moisture > 80, (soil_moisture - 80) / 20.0, 0.05),
    )

    # Mevsim katsayısı: yaz (1) ve sonbahar (2) daha riskli, kış (3) en güvenli
    season_factor = np.array([0.9, 1.15, 1.10, 0.75])[season]

    # Birleşik risk
    raw_risk = (
        0.25 * temp_risk
        + 0.30 * humidity_risk
        + 0.15 * rain_risk
        + 0.10 * wind_risk
        + 0.20 * soil_risk
    ) * season_factor

    # Hafif Gauss gürültü → modelin overfit olmaması için
    noise = rng.normal(0.0, 0.04, size=n)
    risk_score = np.clip(raw_risk + noise, 0.0, 1.0)

    df = pd.DataFrame({
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "wind_speed": wind_speed,
        "soil_moisture": soil_moisture,
        "season": season,
        "risk_score": risk_score,
    })

    return df


# ---------------------------------------------------------------------------
# Eğitim Pipeline
# ---------------------------------------------------------------------------

def train_and_save(config: DatasetConfig | None = None) -> Dict[str, float]:
    """
    Sentetik veri üretir, XGBoost modelini eğitir, RMSE değerlendirir
    ve modeli pickle olarak kaydeder.

    Returns:
        {"rmse": ..., "r2": ...} metrik sözlüğü.
    """
    config = config or DatasetConfig()

    # 1) Veri
    logger.info(f"📊 Sentetik veri üretiliyor: n={config.n_samples}")
    df = generate_synthetic_dataset(config)

    X = df[FEATURE_ORDER].values
    y = df["risk_score"].values

    # 2) Train / test bölme
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config.test_size,
        random_state=config.seed,
    )
    logger.info(f"   Eğitim: {len(X_train)} satır | Test: {len(X_test)} satır")

    # 3) XGBoost Regressor
    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=config.seed,
        n_jobs=-1,
        tree_method="hist",
    )

    logger.info("🚂 Model eğitiliyor (XGBoost Regressor)...")
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # 4) Değerlendirme
    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))
    logger.info(f"📈 Değerlendirme → RMSE: {rmse:.4f} | R²: {r2:.4f}")

    # 5) Kaydet
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": model,
        "feature_order": FEATURE_ORDER,
        "season_map": SEASON_MAP,
        "metrics": {"rmse": rmse, "r2": r2},
        "version": "1.0.0",
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)
    logger.info(f"💾 Model kaydedildi: {MODEL_PATH}")

    return {"rmse": rmse, "r2": r2}


# ---------------------------------------------------------------------------
# CLI Giriş Noktası
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    metrics = train_and_save()
    print("\n" + "=" * 60)
    print(f"✅ Eğitim tamamlandı.")
    print(f"   RMSE: {metrics['rmse']:.4f}")
    print(f"   R²:   {metrics['r2']:.4f}")
    print(f"   Model: {MODEL_PATH}")
    print("=" * 60)