"""
app/services/risk_prediction_service.py
=========================================
Production service layer for the XGBoost plant-disease risk prediction model.

Model Version : 2.0.0
Python        : 3.11+

Public API
----------
    from app.services.risk_prediction_service import predict_risk, get_risk_predictor

    # Simple functional interface (FastAPI-friendly):
    result = predict_risk({
        "temperature": 24.5,
        "humidity":    78.0,
        "rainfall":    55.0,
        "wind_speed":  12.0,
        "season":      "spring",
    })

    # Returns:
    # {
    #     "risk_score":      67.4,
    #     "normalized":      True,
    #     "risk_level":      "High",
    #     "risk_label":      "High Risk",
    #     "risk_color":      "#f97316",
    #     "action":          "Inspect plants daily ...",
    #     "recommendations": [...],
    #     "meta": {
    #         "model_version": "2.0.0",
    #         "input":         {...},
    #         "inference_ms":  4.2,
    #     }
    # }
"""

# =============================================================================
# Imports
# =============================================================================

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

# Navigate from  …/app/services/  →  …/models/
_SERVICE_DIR: Path = Path(__file__).resolve().parent          # app/services/
_APP_DIR:     Path = _SERVICE_DIR.parent                      # app/
_BACKEND_DIR: Path = _APP_DIR.parent                          # backend/

# Primary: app/models/ (written by scripts/train_risk_model.py)
_APP_MODELS_DIR: Path = _APP_DIR / "models"
# Fallback: project-level models/ (written by legacy train_risk_model.py)
_LEGACY_MODELS_DIR: Path = _BACKEND_DIR.parent / "models"

MODEL_PATH: Path = _APP_MODELS_DIR / "risk_model.pkl"
META_PATH:  Path = _APP_MODELS_DIR / "risk_model_meta.json"

# If app/models/ doesn't have the file, fall back to project-level models/
if not MODEL_PATH.exists() and (_LEGACY_MODELS_DIR / "risk_model.pkl").exists():
    MODEL_PATH = _LEGACY_MODELS_DIR / "risk_model.pkl"
    META_PATH  = _LEGACY_MODELS_DIR / "risk_model_meta.json"

VALID_SEASONS: frozenset[str] = frozenset({"spring", "summer", "autumn", "winter"})

NUMERIC_FEATURES:  list[str] = ["temperature", "humidity", "rainfall", "wind_speed"]
CATEGORY_FEATURES: list[str] = ["season"]

# Feature bounds for input validation
FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature": (-10.0, 50.0),
    "humidity":    (0.0,  100.0),
    "rainfall":    (0.0,  400.0),
    "wind_speed":  (0.0,  120.0),
}

REQUIRED_FIELDS: frozenset[str] = frozenset(
    NUMERIC_FEATURES + CATEGORY_FEATURES
)


# =============================================================================
# Input dataclass + validation
# =============================================================================

@dataclass(frozen=True, slots=True)
class RiskInput:
    """
    Validated and normalised input for the risk model.

    Raises ``ValueError`` with a human-readable message on any invalid field.
    ``frozen=True`` makes instances hashable and prevents accidental mutation.
    """

    temperature: float
    humidity:    float
    rainfall:    float
    wind_speed:  float
    season:      str

    # ------------------------------------------------------------------
    # Post-init validation (runs automatically on __init__)
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        # Numeric range checks
        for field, (lo, hi) in FEATURE_BOUNDS.items():
            val: float = getattr(self, field)
            if not (lo <= val <= hi):
                raise ValueError(
                    f"'{field}' value {val!r} is out of the expected range "
                    f"[{lo}, {hi}]. Please supply a realistic measurement."
                )

        # Season check (case-insensitive handled by factory)
        if self.season not in VALID_SEASONS:
            raise ValueError(
                f"Invalid season: {self.season!r}. "
                f"Accepted values: {sorted(VALID_SEASONS)}"
            )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to a single-row DataFrame ready for sklearn Pipeline."""
        row = {
            "temperature": self.temperature,
            "humidity":    self.humidity,
            "rainfall":    self.rainfall,
            "wind_speed":  self.wind_speed,
            "season":      self.season,
        }
        return pd.DataFrame([row], columns=NUMERIC_FEATURES + CATEGORY_FEATURES)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RiskInput":
        """
        Factory that coerces types and normalises casing before validation.

        Args:
            data: Raw input dict (e.g. from JSON body or ``predict_risk`` call).

        Raises:
            ValueError: If required fields are missing or values are invalid.
            TypeError:  If a numeric field cannot be cast to float.
        """
        # --- Missing field check ---
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValueError(
                f"Missing required field(s): {sorted(missing)}. "
                f"All of the following must be present: {sorted(REQUIRED_FIELDS)}"
            )

        # --- Type coercion ---
        try:
            temperature = float(data["temperature"])
            humidity    = float(data["humidity"])
            rainfall    = float(data["rainfall"])
            wind_speed  = float(data["wind_speed"])
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"Numeric fields (temperature, humidity, rainfall, wind_speed) "
                f"must be convertible to float. Got: {exc}"
            ) from exc

        season = str(data["season"]).strip().lower()

        return cls(
            temperature=temperature,
            humidity=humidity,
            rainfall=rainfall,
            wind_speed=wind_speed,
            season=season,
        )


# =============================================================================
# Risk classification helpers
# =============================================================================

def _classify_risk(score: float) -> dict[str, str]:
    """
    Map a 0-100 risk score to a human-readable tier.

    Thresholds:
        [0,  25)  → Low      — routine care
        [25, 50)  → Medium   — increased monitoring
        [50, 75)  → High     — preventive action
        [75, 100] → Critical — immediate intervention
    """
    if score < 25.0:
        return {
            "risk_level": "Low",
            "risk_label": "Low Risk",
            "risk_color": "#22c55e",
            "action": (
                "Continue your routine maintenance. "
                "No significant disease threat detected."
            ),
        }
    elif score < 50.0:
        return {
            "risk_level": "Medium",
            "risk_label": "Medium Risk",
            "risk_color": "#f59e0b",
            "action": (
                "Increase inspection frequency to weekly. "
                "Watch for early warning signs on leaves."
            ),
        }
    elif score < 75.0:
        return {
            "risk_level": "High",
            "risk_label": "High Risk",
            "risk_color": "#f97316",
            "action": (
                "Inspect plants daily. "
                "Consider preventive fungicide application."
            ),
        }
    else:
        return {
            "risk_level": "Critical",
            "risk_label": "Critical Risk",
            "risk_color": "#ef4444",
            "action": (
                "Immediate intervention required! "
                "Isolate affected plants and consult an agronomist."
            ),
        }


def _build_recommendations(inp: RiskInput, risk_score: float) -> list[str]:
    """
    Generate context-aware recommendations based on input features and risk score.

    Args:
        inp:        Validated ``RiskInput`` instance.
        risk_score: Clipped risk score (0–100).

    Returns:
        Non-empty list of recommendation strings with emoji indicators.
    """
    recs: list[str] = []

    # Humidity
    if inp.humidity > 75:
        recs.append(
            f"🌫️  High humidity ({inp.humidity:.0f}%). Improve air circulation "
            "between plants — fungal disease risk is elevated."
        )
    elif inp.humidity < 30:
        recs.append(
            f"💧 Very low humidity ({inp.humidity:.0f}%). Plants may experience "
            "water stress; increase watering frequency."
        )

    # Temperature
    if 18.0 <= inp.temperature <= 28.0:
        recs.append(
            f"🌡️  Temperature ({inp.temperature:.1f}°C) is in the optimal fungal "
            "development range. Increase leaf monitoring."
        )
    elif inp.temperature > 35.0:
        recs.append(
            f"🔥 High temperature ({inp.temperature:.1f}°C) is stressing plants. "
            "Water in the cooler hours and consider shade netting."
        )
    elif inp.temperature < 5.0:
        recs.append(
            f"❄️  Low temperature ({inp.temperature:.1f}°C) suppresses some "
            "pathogens but increases cold-injury risk. Avoid overwatering."
        )

    # Rainfall
    if inp.rainfall > 100.0:
        recs.append(
            f"🌧️  Heavy rainfall ({inp.rainfall:.0f} mm). Check soil drainage; "
            "root rot and soil-borne diseases are more likely."
        )
    elif inp.rainfall > 50.0:
        recs.append(
            f"🌦️  Moderate rainfall ({inp.rainfall:.0f} mm). Monitor for "
            "leaf-spot and mildew after wet periods."
        )

    # Wind
    if inp.wind_speed > 40.0:
        recs.append(
            f"💨 Strong winds ({inp.wind_speed:.0f} km/h) accelerate spore "
            "dispersal. Install windbreaks where possible."
        )

    # Season-specific tip
    season_tips: dict[str, str] = {
        "spring": (
            "🌸 Spring warmth and moisture promote fungal outbreaks. "
            "Begin sulfur-based preventive treatment."
        ),
        "summer": (
            "☀️  Summer brings fire blight and bacterial disease risk. "
            "Irrigate early in the morning to reduce leaf wetness."
        ),
        "autumn": (
            "🍂 Autumn humidity favours rust and powdery mildew. "
            "Apply copper-based fungicide regularly."
        ),
        "winter": (
            "❄️  Plant immunity is reduced in winter. "
            "Avoid excess irrigation to prevent root rot."
        ),
    }
    recs.append(season_tips[inp.season])

    # High-risk universal warning
    if risk_score >= 60.0:
        recs.append(
            f"⚠️  Risk score is {risk_score:.1f}/100. "
            "Consider consulting a certified agronomist for a site inspection."
        )

    return recs if recs else [
        "✅ Current conditions are relatively safe. Continue routine monitoring."
    ]


# =============================================================================
# Core predictor class (singleton-ready)
# =============================================================================

class RiskPredictor:
    """
    Lazy-loading wrapper around the serialised sklearn Pipeline.

    Design choices
    --------------
    - **Lazy loading**: The model is loaded on the first ``predict()`` call,
      not at import time. This avoids import-time side-effects and allows the
      service to start even when the model file is not yet present (useful
      during first-run / CI scenarios).
    - **Thread safety**: For FastAPI's multi-threaded ASGI environment the
      singleton pattern is sufficient because the underlying sklearn pipeline
      is stateless at inference time (no shared mutable state).
    - **Joblib**: Uses ``joblib.load`` to match the serialiser used in
      ``scripts/train_risk_model.py``.  Falls back to ``pickle.load`` for
      backward compatibility with the legacy training script.

    Attributes:
        model_path (Path): Path to the ``.pkl`` pipeline file.
        _pipeline  : Loaded sklearn Pipeline (None until first call).
        _meta      : Metadata dict loaded from companion JSON (or defaults).
        _model_version (str): Version string from metadata.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        meta_path:  Path = META_PATH,
    ) -> None:
        self.model_path:     Path = Path(model_path)
        self.meta_path:      Path = Path(meta_path)
        self._pipeline:      Any  = None
        self._meta:          Optional[dict[str, Any]] = None
        self._model_version: str = "unknown"

    # ------------------------------------------------------------------
    # Internal — model loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """
        Load the pipeline and metadata from disk.

        Raises:
            FileNotFoundError: If the ``.pkl`` file does not exist.
            RuntimeError: If deserialisation fails.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Risk model not found at: {self.model_path}\n"
                "Run 'python scripts/train_risk_model.py' first "
                "to generate the model artifact."
            )

        logger.info(f"[RiskPredictor] Loading pipeline from {self.model_path} …")
        try:
            self._pipeline = joblib.load(self.model_path)
        except Exception:
            # Fallback to pickle for legacy models saved without joblib
            import pickle
            with open(self.model_path, "rb") as fh:
                self._pipeline = pickle.load(fh)

        # Load metadata
        if self.meta_path.exists():
            import json
            with open(self.meta_path, "r", encoding="utf-8") as fh:
                self._meta = json.load(fh)
            self._model_version = self._meta.get("model_version", "unknown")
            logger.info(
                f"[RiskPredictor] Model v{self._model_version} loaded successfully."
            )
        else:
            logger.warning(
                "[RiskPredictor] Metadata file not found — using defaults."
            )
            self._meta = {}

    def _ensure_loaded(self) -> None:
        """Load the model if it has not been loaded yet (lazy pattern)."""
        if self._pipeline is None:
            self._load()

    @property
    def is_loaded(self) -> bool:
        """True if the pipeline is in memory."""
        return self._pipeline is not None

    # ------------------------------------------------------------------
    # Public API — single prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        temperature: float,
        humidity:    float,
        rainfall:    float,
        wind_speed:  float,
        season:      str,
    ) -> dict[str, Any]:
        """
        Predict the plant-disease risk score from individual feature values.

        Args:
            temperature: Air temperature in °C  (-10 to 50).
            humidity:    Relative humidity in % (0 to 100).
            rainfall:    Precipitation in mm    (0 to 400).
            wind_speed:  Wind speed in km/h     (0 to 120).
            season:      One of: spring, summer, autumn, winter.

        Returns:
            Prediction dict (see module docstring for full schema).

        Raises:
            ValueError:       On out-of-range or invalid input.
            TypeError:        On non-numeric numeric fields.
            FileNotFoundError: If the model file is missing.
            RuntimeError:     On unexpected inference errors.
        """
        # 1 — Validate
        inp = RiskInput.from_dict(
            {
                "temperature": temperature,
                "humidity":    humidity,
                "rainfall":    rainfall,
                "wind_speed":  wind_speed,
                "season":      season,
            }
        )

        # 2 — Lazy-load model
        self._ensure_loaded()

        # 3 — Inference
        X = inp.to_dataframe()
        t0 = time.perf_counter()
        try:
            raw: float = float(self._pipeline.predict(X)[0])
        except Exception as exc:
            logger.error(f"[RiskPredictor] Inference error: {exc}", exc_info=True)
            raise RuntimeError(
                f"Inference failed unexpectedly: {exc}"
            ) from exc
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        # 4 — Post-process
        risk_score      = round(float(np.clip(raw, 0.0, 100.0)), 2)
        classification  = _classify_risk(risk_score)
        recommendations = _build_recommendations(inp, risk_score)

        return {
            "risk_score":      risk_score,
            "normalized":      True,
            "risk_level":      classification["risk_level"],
            "risk_label":      classification["risk_label"],
            "risk_color":      classification["risk_color"],
            "action":          classification["action"],
            "recommendations": recommendations,
            "meta": {
                "model_version": self._model_version,
                "input": {
                    "temperature": inp.temperature,
                    "humidity":    inp.humidity,
                    "rainfall":    inp.rainfall,
                    "wind_speed":  inp.wind_speed,
                    "season":      inp.season,
                },
                "inference_ms": inference_ms,
            },
        }

    # ------------------------------------------------------------------
    # Public API — batch prediction
    # ------------------------------------------------------------------

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Run prediction over a list of input dicts.

        Errors in individual records are caught and returned as
        ``{"error": "...", "index": i}`` without aborting the batch.

        Args:
            records: List of dicts, each with the five feature keys.

        Returns:
            List of prediction dicts (same length as ``records``).
        """
        results: list[dict[str, Any]] = []
        for i, rec in enumerate(records):
            try:
                result = self.predict(
                    temperature=rec["temperature"],
                    humidity=   rec["humidity"],
                    rainfall=   rec["rainfall"],
                    wind_speed= rec["wind_speed"],
                    season=     rec["season"],
                )
                results.append(result)
            except (ValueError, TypeError, RuntimeError, KeyError) as exc:
                logger.warning(f"[RiskPredictor] Record {i} failed: {exc}")
                results.append({"error": str(exc), "index": i})
        return results


# =============================================================================
# Module-level singleton + functional interface
# =============================================================================

_predictor_instance: Optional[RiskPredictor] = None


def get_risk_predictor() -> RiskPredictor:
    """
    Return the application-wide ``RiskPredictor`` singleton.

    This function is safe to use as a FastAPI ``Depends()`` dependency.
    The singleton is created on the first call and reused for all subsequent
    calls, meaning the model is loaded only once per process lifetime.

    Example (FastAPI route)::

        from fastapi import Depends
        from app.services.risk_prediction_service import get_risk_predictor, RiskPredictor

        @router.post("/predict")
        def predict(payload: RiskPayloadSchema, predictor: RiskPredictor = Depends(get_risk_predictor)):
            return predictor.predict(**payload.model_dump())
    """
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = RiskPredictor()
    return _predictor_instance


def predict_risk(data: dict[str, Any]) -> dict[str, Any]:
    """
    Thin functional wrapper around the singleton predictor.

    This is the primary entry-point for callers that prefer a plain function
    over class-based usage (e.g. background tasks, unit tests, FastAPI routes
    that don't use ``Depends``).

    Args:
        data: Dict with keys: temperature, humidity, rainfall, wind_speed, season.

    Returns:
        Prediction dict:
        {
            "risk_score":      float,    # 0–100
            "normalized":      bool,     # always True
            "risk_level":      str,      # Low | Medium | High | Critical
            "risk_label":      str,      # human-readable label
            "risk_color":      str,      # hex colour for UI
            "action":          str,      # recommended immediate action
            "recommendations": list[str],
            "meta": {
                "model_version": str,
                "input":         dict,
                "inference_ms":  float,
            }
        }

    Raises:
        ValueError:        On invalid or out-of-range input.
        TypeError:         On wrong field types.
        FileNotFoundError: If the model file has not been generated yet.
        RuntimeError:      On unexpected inference errors.
    """
    predictor = get_risk_predictor()
    inp = RiskInput.from_dict(data)   # validate first for clear error messages
    return predictor.predict(
        temperature=inp.temperature,
        humidity=   inp.humidity,
        rainfall=   inp.rainfall,
        wind_speed= inp.wind_speed,
        season=     inp.season,
    )


# =============================================================================
# Quick smoke-test — run directly: python -m app.services.risk_prediction_service
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    print("=" * 60)
    print("  Risk Prediction Service — Smoke Test")
    print("=" * 60)

    test_cases: list[dict[str, Any]] = [
        {
            "label":       "🌸 Risky Spring (high humidity + warm)",
            "temperature": 24.0,
            "humidity":    84.0,
            "rainfall":    72.0,
            "wind_speed":  15.0,
            "season":      "spring",
        },
        {
            "label":       "☀️  Dry Summer (low humidity)",
            "temperature": 35.0,
            "humidity":    42.0,
            "rainfall":    8.0,
            "wind_speed":  8.0,
            "season":      "summer",
        },
        {
            "label":       "🍂 Wet Autumn (heavy rain)",
            "temperature": 12.0,
            "humidity":    88.0,
            "rainfall":    130.0,
            "wind_speed":  27.0,
            "season":      "autumn",
        },
        {
            "label":       "❄️  Cold Winter (minimal risk)",
            "temperature": 2.0,
            "humidity":    75.0,
            "rainfall":    28.0,
            "wind_speed":  35.0,
            "season":      "winter",
        },
        {
            "label":       "⛔ Invalid input (humidity > 100)",
            "temperature": 20.0,
            "humidity":    110.0,
            "rainfall":    50.0,
            "wind_speed":  10.0,
            "season":      "spring",
        },
    ]

    for case in test_cases:
        label = case.pop("label")
        print(f"\n{'─' * 55}")
        print(f"  {label}")
        print(f"{'─' * 55}")
        try:
            result = predict_risk(case)
            print(f"  Risk Score  : {result['risk_score']}/100")
            print(f"  Level       : {result['risk_label']}  ({result['risk_level']})")
            print(f"  Action      : {result['action']}")
            print(f"  Model ver.  : {result['meta']['model_version']}")
            print(f"  Inference   : {result['meta']['inference_ms']} ms")
            print("  Recommendations:")
            for rec in result["recommendations"]:
                print(f"    → {rec}")
        except FileNotFoundError as exc:
            print(f"  ⚠️  Model not found — run training first.\n  Detail: {exc}")
        except (ValueError, TypeError) as exc:
            print(f"  ✅ Validation caught (expected): {exc}")

    print(f"\n{'=' * 60}\n  Smoke test complete.\n{'=' * 60}")
