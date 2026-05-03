# =============================================================================
# train_risk_model.py
#
# XGBoost tabanlı bitki hastalık risk tahmini modeli eğitim scripti.
#
# Kullanım:
#   python train_risk_model.py
#
# Çıktı:
#   models/risk_model.pkl        → Eğitilmiş XGBoost pipeline
#   models/risk_model_meta.json  → Label encoder sınıfları ve feature isimleri
# =============================================================================

import os
import json
import pickle
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import mean_absolute_error, r2_score

# ---------------------------------------------------------------------------
# 1. Sentetik Veri Üretimi
# ---------------------------------------------------------------------------

def generate_synthetic_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Gerçekçi iklim koşullarına dayalı sentetik bitki hastalık risk verisi üretir.

    Risk skoru (0–100) şu kurallara göre hesaplanır:
      - Yüksek nem (>70%) → mantar hastalık riski artar
      - Sıcaklık 18–28°C arası → en uygun hastalık gelişim bölgesi
      - Yağış → toprak kaynaklı hastalık riskini artırır
      - Yüksek rüzgar → spor yayılımını hızlandırır
      - Sezon: Yaz ve İlkbahar en riskli dönemler
    """
    np.random.seed(seed)

    # Sezon bazlı veri dağılımı (gerçekçi mevsimsel koşullar)
    seasons = ["spring", "summer", "autumn", "winter"]
    season_profiles = {
        "spring": {"temp_mean": 18, "temp_std": 4, "humid_mean": 70, "humid_std": 12, "rain_mean": 60, "wind_mean": 15},
        "summer": {"temp_mean": 30, "temp_std": 5, "humid_mean": 60, "humid_std": 15, "rain_mean": 30, "wind_mean": 10},
        "autumn": {"temp_mean": 14, "temp_std": 5, "humid_mean": 75, "humid_std": 10, "rain_mean": 80, "wind_mean": 20},
        "winter": {"temp_mean": 5,  "temp_std": 4, "humid_mean": 80, "humid_std": 10, "rain_mean": 50, "wind_mean": 25},
    }

    records = []
    samples_per_season = n_samples // len(seasons)

    for season in seasons:
        p = season_profiles[season]
        n = samples_per_season

        temperature = np.clip(np.random.normal(p["temp_mean"], p["temp_std"], n), -5, 45)
        humidity    = np.clip(np.random.normal(p["humid_mean"], p["humid_std"], n), 10, 100)
        rainfall    = np.clip(np.random.exponential(p["rain_mean"], n), 0, 300)
        wind_speed  = np.clip(np.random.normal(p["wind_mean"], 5, n), 0, 80)

        # ---------------------------------------------------------------------------
        # Risk Skoru Hesaplama (domain bilgisine dayalı çok değişkenli formül)
        # ---------------------------------------------------------------------------

        # Nem katkısı: 70%'nin üzerinde her % için artan risk
        humidity_risk = np.clip((humidity - 50) / 50 * 40, 0, 40)

        # Sıcaklık katkısı: 18-28°C ideal hastalık gelişim aralığı
        temp_risk = np.clip(30 - np.abs(temperature - 23) * 2.5, 0, 30)

        # Yağış katkısı: logaritmik büyüme (çok fazla yağış riski platolar)
        rain_risk = np.clip(np.log1p(rainfall) / np.log1p(300) * 20, 0, 20)

        # Rüzgar katkısı: spor yayılımını artırır
        wind_risk = np.clip(wind_speed / 80 * 10, 0, 10)

        # Sezon katkısı
        season_bonus = {"spring": 8, "summer": 5, "autumn": 6, "winter": 0}[season]

        # Ham risk (0-108 aralığında)
        raw_risk = humidity_risk + temp_risk + rain_risk + wind_risk + season_bonus

        # Normalize et: 0-100
        risk_score = np.clip(raw_risk + np.random.normal(0, 3, n), 0, 100)

        for i in range(n):
            records.append({
                "temperature": round(temperature[i], 2),
                "humidity":    round(humidity[i], 2),
                "rainfall":    round(rainfall[i], 2),
                "wind_speed":  round(wind_speed[i], 2),
                "season":      season,
                "risk_score":  round(risk_score[i], 2),
            })

    df = pd.DataFrame(records).sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. Veri Ön İşleme & Model Eğitimi
# ---------------------------------------------------------------------------

def build_and_train_pipeline(df: pd.DataFrame):
    """
    ColumnTransformer + XGBRegressor pipeline'ı kurar ve eğitir.
    Sayısal özellikler StandardScaler ile normalize edilir.
    Kategorik 'season' özelliği OrdinalEncoder ile dönüştürülür.
    """
    NUMERIC_FEATURES  = ["temperature", "humidity", "rainfall", "wind_speed"]
    CATEGORY_FEATURES = ["season"]
    TARGET = "risk_score"

    X = df[NUMERIC_FEATURES + CATEGORY_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Season sıralı encode (ilkbahar, yaz, sonbahar, kış döngüsü anlamlı değil
    # bu yüzden nominal olarak kullanıyoruz; XGBoost kategorik işleyebilir)
    season_encoder = OrdinalEncoder(
        categories=[["spring", "summer", "autumn", "winter"]],
        handle_unknown="use_encoded_value",
        unknown_value=-1,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num",  StandardScaler(),   NUMERIC_FEATURES),
            ("cat",  season_encoder,     CATEGORY_FEATURES),
        ]
    )

    xgb_model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model",        xgb_model),
    ])

    print("[INFO] Model eğitimi başlıyor...")
    pipeline.fit(X_train, y_train)

    # Değerlendirme
    y_pred = pipeline.predict(X_test)
    y_pred = np.clip(y_pred, 0, 100)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)

    print(f"[RESULT] MAE  : {mae:.3f}")
    print(f"[RESULT] R²   : {r2:.4f}")
    print(f"[RESULT] Test örnek sayısı: {len(y_test)}")

    return pipeline, NUMERIC_FEATURES, CATEGORY_FEATURES, season_encoder.categories_[0].tolist()


# ---------------------------------------------------------------------------
# 3. Model Kaydetme
# ---------------------------------------------------------------------------

def save_model(pipeline, numeric_features, category_features, season_classes, output_dir: str = "models"):
    """Pipeline'ı .pkl, metadata'yı .json olarak kaydeder."""
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, "risk_model.pkl")
    meta_path  = os.path.join(output_dir, "risk_model_meta.json")

    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    meta = {
        "numeric_features":  numeric_features,
        "category_features": category_features,
        "season_classes":    season_classes,
        "risk_range":        [0, 100],
        "model_type":        "XGBRegressor",
        "version":           "1.0.0",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[SAVED] Model     → {model_path}")
    print(f"[SAVED] Metadata  → {meta_path}")


# ---------------------------------------------------------------------------
# 4. Ana Akış
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("  XGBoost Bitki Hastalık Risk Modeli — Eğitim")
    print("=" * 55)

    # Sentetik veri üret
    print(f"\n[STEP 1] Sentetik veri üretiliyor...")
    df = generate_synthetic_data(n_samples=5000)
    print(f"         Toplam örnek: {len(df)}")
    print(f"         Risk istatistikleri:\n{df['risk_score'].describe().round(2)}\n")

    # Model eğit
    print("[STEP 2] Model eğitiliyor...")
    pipeline, num_feats, cat_feats, season_classes = build_and_train_pipeline(df)

    # Kaydet
    print("\n[STEP 3] Model kaydediliyor...")
    save_model(pipeline, num_feats, cat_feats, season_classes)

    print("\n✅ Eğitim tamamlandı! risk_prediction_service.py ile tahmin yapabilirsiniz.")
