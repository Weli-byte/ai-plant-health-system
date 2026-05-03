"""
app/services/risk_v2_service.py
===============================
Sprint 4 — Advanced Risk Prediction service layer.

Singleton pattern: the XGBoost pipeline is loaded ONCE from
``backend/models/risk_model_v2.pkl`` and reused across requests.

Public API
----------
    risk_v2_store          — singleton holder (call ``.load()`` at startup).
    predict_risk_v2(data)  — run inference, return score + metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

from app.ml._paths import RISK_MODEL_PATH
from app.ml.risk_model import (
    ALL_FEATURES,
    MODEL_VERSION,
    load_risk_model,
    predict_risk_score,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk level thresholds (0-100 scale)
# ---------------------------------------------------------------------------

LOW_THRESHOLD = 34.0
HIGH_THRESHOLD = 67.0


def _risk_level(score: float) -> str:
    """Map a 0-100 score to a discrete label."""
    if score < LOW_THRESHOLD:
        return "low"
    if score < HIGH_THRESHOLD:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

class RiskV2ModelStore:
    """
    Holds the loaded model bundle in memory.

    Usage::

        risk_v2_store.load()             # once at startup
        result = predict_risk_v2(data)   # per request
        risk_v2_store.unload()           # at shutdown
    """

    def __init__(self) -> None:
        self._bundle: Optional[Dict[str, Any]] = None
        self.is_loaded: bool = False

    # -- lifecycle ---------------------------------------------------------

    def load(self, path: Path | str = RISK_MODEL_PATH) -> None:
        """Load the trained pipeline bundle from disk."""
        try:
            self._bundle = load_risk_model(path)
            self.is_loaded = True
            version = self._bundle.get("version", "unknown")
            metrics = self._bundle.get("metrics", {})
            logger.info(
                "✅ Risk v2 model loaded (v%s) | RMSE=%.3f | Features=%s",
                version,
                metrics.get("rmse", float("nan")),
                self._bundle.get("all_features", ALL_FEATURES),
            )
        except FileNotFoundError:
            logger.warning(
                "⚠️  Risk v2 model not found at %s. "
                "Train it via: python -m app.ml.risk_model",
                path,
            )
            self.is_loaded = False
        except Exception as exc:
            logger.error("❌ Failed to load risk v2 model: %s", exc)
            self.is_loaded = False

    def unload(self) -> None:
        """Release model from memory."""
        self._bundle = None
        self.is_loaded = False
        logger.info("♻️  Risk v2 model unloaded.")

    @property
    def bundle(self) -> Dict[str, Any]:
        if not self.is_loaded or self._bundle is None:
            raise RuntimeError(
                "Risk v2 model is not loaded. "
                "Call risk_v2_store.load() first or train the model."
            )
        return self._bundle


# Global singleton — imported by routes and main.py
risk_v2_store = RiskV2ModelStore()


# ---------------------------------------------------------------------------
# Public inference function
# ---------------------------------------------------------------------------

def predict_risk_v2(data: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Run risk inference on a single input dict.

    Parameters
    ----------
    data : dict
        Must contain keys: temperature, humidity, rainfall, soil_type, crop_type.

    Returns
    -------
    dict
        ``{risk_score, risk_level, model_version, metrics}``

    Raises
    ------
    RuntimeError  — model not loaded.
    ValueError    — invalid / missing features.
    """
    bundle = risk_v2_store.bundle  # raises if not loaded

    scores: List[float] = predict_risk_score(bundle, data)
    score = float(np.clip(scores[0], 0.0, 100.0))

    return {
        "risk_score": round(score, 2),
        "risk_level": _risk_level(score),
        "model_version": bundle.get("version", MODEL_VERSION),
        "metrics": bundle.get("metrics", {}),
    }
