# =============================================================================
# scripts/train_risk_model.py
#
# XGBoost plant-disease risk prediction — training pipeline.
# MODEL VERSION: 2.0.0
#
# Usage (from backend/ directory):
#   python scripts/train_risk_model.py
#   python scripts/train_risk_model.py --samples 15000 --seed 7 --output app/models
#
# Outputs:
#   app/models/risk_model.pkl        — joblib-serialised sklearn Pipeline
#   app/models/risk_model_meta.json  — feature schema + metrics + version
# =============================================================================
from __future__ import annotations  # must be first executable statement

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
MODEL_VERSION: str = "2.0.0"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("train_risk_model")

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------
NUMERIC_FEATURES: list[str] = ["temperature", "humidity", "rainfall", "wind_speed"]
CATEGORY_FEATURES: list[str] = ["season"]
VALID_SEASONS: list[str] = ["spring", "summer", "autumn", "winter"]
TARGET: str = "risk_score"

# ---------------------------------------------------------------------------
# Tuned XGBoost hyper-parameters
# ---------------------------------------------------------------------------
XGB_PARAMS: dict[str, Any] = {
    "n_estimators":    400,
    "max_depth":       6,
    "learning_rate":   0.04,
    "subsample":       0.85,
    "colsample_bytree": 0.80,
    "min_child_weight": 3,
    "reg_alpha":       0.05,
    "reg_lambda":      1.2,
    "random_state":    42,
    "n_jobs":          -1,
    "objective":       "reg:squarederror",
}


# =============================================================================
# 1. DATA GENERATION
# =============================================================================

def generate_dataset(n_samples: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a realistic synthetic plant-disease risk dataset.

    Risk score is composed of additive, domain-informed components:
    - humidity_component  : exponential effect above 60 %
    - temp_component      : Gaussian peak at 23 °C (optimal fungal range)
    - rain_component      : log-scale growth (plateaus at high values)
    - wind_component      : linear spore-dispersal effect
    - season_offset       : base risk shift per season
    - interaction_term    : humidity × temperature synergy (fungal amplifier)
    - noise               : Gaussian noise simulating measurement uncertainty

    Args:
        n_samples: Total rows (≥ 4 × base_per_season).
        seed:      NumPy random seed for full reproducibility.

    Returns:
        Shuffled DataFrame with columns:
        [temperature, humidity, rainfall, wind_speed, season, risk_score]
    """
    logger.info(f"Generating {n_samples:,} synthetic samples (seed={seed}) …")
    rng = np.random.default_rng(seed)

    # Per-season climate profiles (mean / std drawn from domain knowledge)
    profiles: dict[str, dict[str, float]] = {
        "spring": dict(temp_mu=18.0, temp_sig=4.5, hum_mu=70.0, hum_sig=11.0,
                       rain_scale=55.0, wind_mu=15.0, wind_sig=6.0, offset=9.0),
        "summer": dict(temp_mu=31.0, temp_sig=5.0, hum_mu=58.0, hum_sig=14.0,
                       rain_scale=30.0, wind_mu=10.0, wind_sig=5.0, offset=5.0),
        "autumn": dict(temp_mu=14.0, temp_sig=5.5, hum_mu=76.0, hum_sig=9.0,
                       rain_scale=70.0, wind_mu=21.0, wind_sig=7.0, offset=7.0),
        "winter": dict(temp_mu=4.0,  temp_sig=4.0, hum_mu=81.0, hum_sig=8.0,
                       rain_scale=45.0, wind_mu=27.0, wind_sig=8.0, offset=2.0),
    }

    base_n = n_samples // len(VALID_SEASONS)
    counts  = {s: base_n for s in VALID_SEASONS}
    counts[VALID_SEASONS[-1]] += n_samples - sum(counts.values())  # remainder

    frames: list[pd.DataFrame] = []

    for season, n in counts.items():
        p = profiles[season]

        temperature = np.clip(rng.normal(p["temp_mu"],   p["temp_sig"], n), -10.0, 50.0)
        humidity    = np.clip(rng.normal(p["hum_mu"],    p["hum_sig"],  n),   5.0, 100.0)
        rainfall    = np.clip(rng.exponential(p["rain_scale"], n),            0.0, 400.0)
        wind_speed  = np.clip(rng.normal(p["wind_mu"],   p["wind_sig"], n),   0.0, 120.0)

        # ── risk components ────────────────────────────────────────────────
        # Humidity: steep rise above 60 %
        hum_comp  = np.clip((humidity - 60.0) / 40.0 * 38.0, 0.0, 38.0)
        # Temperature: bell-shaped peak at 23 °C
        temp_comp = np.clip(28.0 * np.exp(-0.5 * ((temperature - 23.0) / 9.0) ** 2),
                            0.0, 28.0)
        # Rainfall: log-scaled
        rain_comp = np.clip(np.log1p(rainfall) / np.log1p(400.0) * 18.0, 0.0, 18.0)
        # Wind: linear spore dispersal
        wind_comp = np.clip(wind_speed / 120.0 * 9.0, 0.0, 9.0)
        # Season base offset
        seas_comp = np.full(n, p["offset"])
        # Interaction: high humidity AND high temperature amplify fungal risk
        inter     = np.clip((humidity / 100.0) * (temperature / 50.0) * 12.0, 0.0, 12.0)
        # Noise
        noise     = rng.normal(0.0, 2.5, n)

        risk_score = np.clip(
            hum_comp + temp_comp + rain_comp + wind_comp + seas_comp + inter + noise,
            0.0, 100.0,
        )

        frames.append(pd.DataFrame({
            "temperature": np.round(temperature, 2),
            "humidity":    np.round(humidity,    2),
            "rainfall":    np.round(rainfall,    2),
            "wind_speed":  np.round(wind_speed,  2),
            "season":      season,
            TARGET:        np.round(risk_score,  2),
        }))

    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    logger.info(
        f"Dataset ready — shape: {df.shape} | "
        f"risk min={df[TARGET].min():.1f}  "
        f"mean={df[TARGET].mean():.1f}  "
        f"max={df[TARGET].max():.1f}"
    )
    return df


# =============================================================================
# 2. PIPELINE CONSTRUCTION
# =============================================================================

def build_pipeline() -> Pipeline:
    """
    Assemble the sklearn Pipeline:

        ColumnTransformer
        ├── StandardScaler   (numeric features)
        └── OneHotEncoder    (season → 4 binary columns, handle_unknown='ignore')
        └── XGBRegressor

    Returns:
        Untrained sklearn Pipeline.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                StandardScaler(),
                NUMERIC_FEATURES,
            ),
            (
                "cat",
                OneHotEncoder(
                    categories=[VALID_SEASONS],
                    handle_unknown="ignore",  # robust to unseen categories at inference
                    sparse_output=False,
                ),
                CATEGORY_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    model = XGBRegressor(**XGB_PARAMS)

    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model",        model),
    ])


# =============================================================================
# 3. TRAINING + EVALUATION
# =============================================================================

def train(
    df: pd.DataFrame,
    test_size: float = 0.20,
    seed: int = 42,
) -> tuple[Pipeline, dict[str, float]]:
    """
    Split data, fit the pipeline, and compute RMSE + R².

    Args:
        df:        Full dataset from :func:`generate_dataset`.
        test_size: Fraction reserved for validation (default 20 %).
        seed:      Random state for the split.

    Returns:
        ``(fitted_pipeline, metrics_dict)`` where metrics_dict has keys:
        ``rmse``, ``r2``, ``n_train``, ``n_val``.
    """
    X = df[NUMERIC_FEATURES + CATEGORY_FEATURES]
    y = df[TARGET]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )
    logger.info(f"Split — train: {len(X_train):,}  val: {len(X_val):,}")

    pipeline = build_pipeline()

    logger.info("Fitting pipeline …")
    t0 = time.perf_counter()
    pipeline.fit(X_train, y_train)
    elapsed = time.perf_counter() - t0
    logger.info(f"Training complete in {elapsed:.2f}s")

    y_pred = np.clip(pipeline.predict(X_val), 0.0, 100.0)
    rmse   = float(np.sqrt(mean_squared_error(y_val, y_pred)))
    r2     = float(r2_score(y_val, y_pred))

    metrics: dict[str, float] = {
        "rmse":    round(rmse, 4),
        "r2":      round(r2,   4),
        "n_train": int(len(X_train)),
        "n_val":   int(len(X_val)),
    }

    logger.info("=" * 50)
    logger.info(f"  RMSE  (validation) : {rmse:.4f}")
    logger.info(f"  R²    (validation) : {r2:.4f}")
    logger.info("=" * 50)

    return pipeline, metrics


# =============================================================================
# 4. SERIALIZATION
# =============================================================================

def save_artifacts(
    pipeline: Pipeline,
    metrics:  dict[str, float],
    output_dir: str | Path = "app/models",
) -> None:
    """
    Persist the fitted pipeline and companion metadata to disk.

    Files written:
        <output_dir>/risk_model.pkl       — joblib-compressed Pipeline
        <output_dir>/risk_model_meta.json — JSON metadata

    Args:
        pipeline:   Fitted sklearn Pipeline.
        metrics:    Dict returned by :func:`train`.
        output_dir: Target directory (created if absent).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    model_path = out / "risk_model.pkl"
    meta_path  = out / "risk_model_meta.json"

    # ── Pipeline ──────────────────────────────────────────────────────────────
    joblib.dump(pipeline, model_path, compress=3)
    size_kb = model_path.stat().st_size / 1024
    logger.info(f"Pipeline saved → {model_path}  ({size_kb:.1f} KB)")

    # ── Metadata ──────────────────────────────────────────────────────────────
    meta: dict[str, Any] = {
        "model_version":     MODEL_VERSION,
        "model_type":        "XGBRegressor",
        "numeric_features":  NUMERIC_FEATURES,
        "category_features": CATEGORY_FEATURES,
        "season_categories": VALID_SEASONS,
        "target":            TARGET,
        "output_range":      [0, 100],
        "xgb_params":        XGB_PARAMS,
        "metrics":           metrics,
        "serialization":     "joblib",
    }
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    logger.info(f"Metadata saved  → {meta_path}")


# =============================================================================
# 5. CLI
# =============================================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train XGBoost plant-disease risk model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--samples",   type=int,   default=10_000,
                        help="Number of synthetic samples to generate.")
    parser.add_argument("--seed",      type=int,   default=42,
                        help="Random seed for full reproducibility.")
    parser.add_argument("--test-size", type=float, default=0.20,
                        help="Validation fraction [0.05, 0.40].")
    parser.add_argument("--output",    type=str,   default="app/models",
                        help="Directory to write model artifacts.")
    return parser.parse_args()


def main() -> None:
    """End-to-end orchestrator: generate → train → evaluate → save."""
    args = _parse_args()

    if args.samples < 1_000:
        logger.error("--samples must be ≥ 1,000. Aborting.")
        sys.exit(1)
    if not (0.05 <= args.test_size <= 0.40):
        logger.error("--test-size must be in [0.05, 0.40]. Aborting.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info(f"  XGBoost Disease Risk Model — v{MODEL_VERSION}")
    logger.info("=" * 60)

    df                  = generate_dataset(n_samples=args.samples, seed=args.seed)
    pipeline, metrics   = train(df, test_size=args.test_size, seed=args.seed)
    save_artifacts(pipeline, metrics, output_dir=args.output)

    logger.info("✅  Done.  Load the model with:")
    logger.info(f"    pipeline = joblib.load('{args.output}/risk_model.pkl')")


if __name__ == "__main__":
    main()
