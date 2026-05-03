"""
app/services/digital_twin_service.py
=====================================
Sprint 4 — Digital Twin forecast service layer.

Singleton pattern: the LSTM model is loaded ONCE and reused.

Public API
----------
    digital_twin_store              — singleton (call ``.load()`` at startup).
    predict_future(observations)    — run forecast, return 3-day & 7-day risk.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import torch

from app.ml._paths import DIGITAL_TWIN_MODEL_PATH
from app.ml.digital_twin_model import (
    DigitalTwinLSTM,
    forecast,
    load_model,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

class DigitalTwinModelStore:
    """Holds the LSTM digital-twin model in memory."""

    def __init__(self) -> None:
        self._model: Optional[DigitalTwinLSTM] = None
        self.is_loaded: bool = False
        self.device: torch.device = torch.device("cpu")

    def load(self, path: Path | str = DIGITAL_TWIN_MODEL_PATH) -> None:
        try:
            self._model = load_model(path)
            self.device = next(self._model.parameters()).device
            self.is_loaded = True
            logger.info(
                "✅ Digital twin model loaded (v%s) on %s | horizons=%s",
                self._model.config.version,
                self.device,
                self._model.config.forecast_horizons,
            )
        except FileNotFoundError:
            logger.warning(
                "⚠️  Digital twin model not found at %s. "
                "Train it via: python -m app.ml.digital_twin_model",
                path,
            )
            self.is_loaded = False
        except Exception as exc:
            logger.error("❌ Failed to load digital twin model: %s", exc)
            self.is_loaded = False

    def unload(self) -> None:
        self._model = None
        self.is_loaded = False
        logger.info("♻️  Digital twin model unloaded.")

    @property
    def model(self) -> DigitalTwinLSTM:
        if not self.is_loaded or self._model is None:
            raise RuntimeError(
                "Digital twin model is not loaded. "
                "Call digital_twin_store.load() first or train the model."
            )
        return self._model


# Global singleton
digital_twin_store = DigitalTwinModelStore()


# ---------------------------------------------------------------------------
# Public inference function
# ---------------------------------------------------------------------------

def predict_future(
    observations: Sequence[Sequence[float]],
) -> Dict[str, Any]:
    """
    Forecast future risk from a history window.

    Parameters
    ----------
    observations : list[list[float]]
        Recent daily observations (each inner list has 7 floats).

    Returns
    -------
    dict
        ``{horizons_days, risk_scores, risk_levels, model_version}``
    """
    model = digital_twin_store.model  # raises if not loaded

    result = forecast(model, observations)
    result["model_version"] = model.config.version
    return result
