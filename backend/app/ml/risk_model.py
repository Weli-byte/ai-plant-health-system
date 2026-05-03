"""
app/ml/risk_model.py
====================
Sprint 4 — Task 1: Advanced Risk Prediction Pipeline.

A production-grade scikit-learn ``Pipeline`` that combines:

    preprocessing → encoding (OneHot) → scaling (StandardScaler) → XGBoost

Inputs (5 features required by the spec):
    temperature   : float  (°C)
    humidity      : float  (%)
    rainfall      : float  (mm/day)
    soil_type     : str    {"clay", "sandy", "loam", "silt", "peat", "chalky"}
    crop_type     : str    {"tomato", "wheat", "corn", "rice", "potato", "grape"}

Output:
    risk_score    : float  ∈ [0, 100]   (regression, clipped to range)

Public API
----------
    train_risk_model(...)            → fit pipeline on synthetic data, save to disk
    load_risk_model(path)            → joblib-load a saved bundle
    predict_risk_score(bundle, data) → run inference for one or many rows

The bundle saved to disk includes the fitted ``Pipeline`` plus metadata
(feature lists, training metrics, version) so the service layer can introspect
without re-deriving anything.

This module is **independent** from the legacy Sprint 3 ``risk_service.py`` /
``train_risk_model.py``. Existing endpoints continue to work untouched.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from app.ml._paths import RISK_MODEL_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUMERIC_FEATURES: List[str] = ["temperature", "humidity", "rainfall"]
CATEGORICAL_FEATURES: List[str] = ["soil_type", "crop_type"]
ALL_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

SOIL_TYPES: List[str] = ["clay", "sandy", "loam", "silt", "peat", "chalky"]
CROP_TYPES: List[str] = ["tomato", "wheat", "corn", "rice", "potato", "grape"]

MODEL_VERSION: str = "2.0.0"
RANDOM_SEED: int = 42


# ---------------------------------------------------------------------------
# Synthetic dataset
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    """Configuration for synthetic-data training."""
    n_samples: int = 6000
    test_size: float = 0.2
    seed: int = RANDOM_SEED


def _generate_synthetic_dataset(cfg: TrainConfig) -> pd.DataFrame:
    """
    Build a domain-informed synthetic dataset.

    Risk drivers (clipped to [0, 100]):
      * humidity > 70  + temperature 20–28°C  → fungal pressure ↑↑
      * rainfall > 50 mm                       → standing-water risk ↑
      * soil_type susceptibility               → multiplicative
      * crop_type baseline susceptibility      → additive
    """
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_samples

    temperature = rng.uniform(-5.0, 45.0, size=n)
    humidity = rng.uniform(10.0, 100.0, size=n)
    rainfall = rng.uniform(0.0, 200.0, size=n)
    soil = rng.choice(SOIL_TYPES, size=n)
    crop = rng.choice(CROP_TYPES, size=n)

    # Numeric risk components (each in [0, 1])
    temp_risk = np.where(
        (temperature >= 20) & (temperature <= 28),
        0.10,
        np.minimum(1.0, np.abs(temperature - 24) / 25.0),
    )
    humidity_risk = np.clip((humidity - 50) / 50.0, 0.0, 1.0) ** 1.5
    rain_risk = np.clip(rainfall / 100.0, 0.0, 1.0)

    # Categorical multipliers
    soil_susceptibility = {
        "clay": 1.20, "sandy": 0.85, "loam": 0.95,
        "silt": 1.05, "peat": 1.10, "chalky": 0.90,
    }
    crop_baseline = {
        "tomato": 0.15, "wheat": 0.10, "corn": 0.12,
        "rice": 0.20, "potato": 0.18, "grape": 0.22,
    }
    soil_mult = np.array([soil_susceptibility[s] for s in soil])
    crop_base = np.array([crop_baseline[c] for c in crop])

    raw = (0.30 * temp_risk + 0.40 * humidity_risk + 0.20 * rain_risk) * soil_mult \
          + 0.10 * crop_base
    raw = np.clip(raw, 0.0, 1.0)

    noise = rng.normal(0.0, 0.04, size=n)
    risk_score = np.clip((raw + noise) * 100.0, 0.0, 100.0)

    return pd.DataFrame({
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "soil_type": soil,
        "crop_type": crop,
        "risk_score": risk_score,
    })


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------

def _build_pipeline() -> Pipeline:
    """
    Construct the preprocessing + estimator pipeline.

    OneHotEncoder uses ``handle_unknown="ignore"`` so unseen categories at
    inference time do not raise — they simply produce an all-zero one-hot
    block. ``sparse_output=False`` keeps the transform compatible with
    XGBoost's dense-matrix fast path.
    """
    # sklearn >=1.2 deprecated ``sparse=`` in favour of ``sparse_output=``.
    onehot = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        categories=[SOIL_TYPES, CROP_TYPES],
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", onehot, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    estimator = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", estimator),
    ])


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_risk_model(
    config: TrainConfig | None = None,
    save_path: Path | str = RISK_MODEL_PATH,
) -> Dict[str, Any]:
    """
    Train the pipeline on synthetic data and persist it via ``joblib``.

    Parameters
    ----------
    config:
        Dataset/training configuration (defaults to ``TrainConfig()``).
    save_path:
        Where to write the joblib bundle.

    Returns
    -------
    dict
        ``{"rmse", "mae", "r2", "save_path"}``.
    """
    cfg = config or TrainConfig()
    save_path = Path(save_path)

    logger.info("📊 Generating synthetic dataset (n=%d)", cfg.n_samples)
    df = _generate_synthetic_dataset(cfg)

    X = df[ALL_FEATURES]
    y = df["risk_score"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=cfg.test_size, random_state=cfg.seed
    )
    logger.info("   train=%d  test=%d", len(X_train), len(X_test))

    pipeline = _build_pipeline()
    logger.info("🚂 Fitting pipeline (StandardScaler + OneHot + XGBoost)")
    pipeline.fit(X_train, y_train)

    y_pred = np.clip(pipeline.predict(X_test), 0.0, 100.0)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))
    logger.info("📈 RMSE=%.3f  MAE=%.3f  R²=%.4f", rmse, mae, r2)

    bundle: Dict[str, Any] = {
        "pipeline": pipeline,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_features": ALL_FEATURES,
        "soil_types": SOIL_TYPES,
        "crop_types": CROP_TYPES,
        "metrics": {"rmse": rmse, "mae": mae, "r2": r2},
        "version": MODEL_VERSION,
        "output_range": [0.0, 100.0],
    }

    save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, save_path)
    logger.info("💾 Saved → %s", save_path)

    return {"rmse": rmse, "mae": mae, "r2": r2, "save_path": str(save_path)}


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def load_risk_model(path: Path | str = RISK_MODEL_PATH) -> Dict[str, Any]:
    """
    Load a trained bundle. Raises ``FileNotFoundError`` if the artifact is missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Risk model artifact not found: {path}. "
            f"Train it via: python -m app.ml.risk_model"
        )
    bundle = joblib.load(path)
    if not isinstance(bundle, Mapping) or "pipeline" not in bundle:
        raise RuntimeError(
            f"Risk model bundle at {path} is malformed (missing 'pipeline'). "
            "Re-run training."
        )
    return dict(bundle)


def _coerce_to_dataframe(
    data: Union[Mapping[str, Any], Sequence[Mapping[str, Any]], pd.DataFrame],
) -> pd.DataFrame:
    """Accept dict / list[dict] / DataFrame and return a DataFrame in canonical column order."""
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, Mapping):
        df = pd.DataFrame([dict(data)])
    elif isinstance(data, Sequence):
        df = pd.DataFrame([dict(row) for row in data])
    else:
        raise TypeError(
            f"Unsupported input type for risk inference: {type(data).__name__}"
        )

    missing = [c for c in ALL_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature(s): {missing}")

    return df[ALL_FEATURES]


def predict_risk_score(
    bundle: Mapping[str, Any],
    data: Union[Mapping[str, Any], Sequence[Mapping[str, Any]], pd.DataFrame],
) -> List[float]:
    """
    Run inference. Input can be a single dict, a list of dicts, or a DataFrame.

    Returns a list of float risk scores in [0, 100].
    """
    pipeline = bundle["pipeline"]
    df = _coerce_to_dataframe(data)
    raw = pipeline.predict(df)
    clipped = np.clip(raw, 0.0, 100.0)
    return [float(x) for x in clipped]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s → %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    metrics = train_risk_model()
    print("\n" + "=" * 60)
    print("✅ Advanced risk model trained.")
    print(f"   RMSE : {metrics['rmse']:.3f}")
    print(f"   MAE  : {metrics['mae']:.3f}")
    print(f"   R²   : {metrics['r2']:.4f}")
    print(f"   File : {metrics['save_path']}")
    print("=" * 60)
