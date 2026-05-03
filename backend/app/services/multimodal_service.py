"""
app/services/multimodal_service.py
===================================
Sprint 4 — Multimodal disease-risk service layer.

Singleton pattern: the PyTorch ``MultimodalRiskModel`` is loaded ONCE
and reused across requests.

Public API
----------
    multimodal_store                 — singleton (call ``.load()`` at startup).
    predict_multimodal(weather, soil_type, image_base64)
                                     — run inference, return prediction dict.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from PIL import Image
from torchvision import transforms

from app.ml._paths import MULTIMODAL_MODEL_PATH
from app.ml.multimodal_model import (
    SOIL_TO_ID,
    SOIL_TYPES,
    MultimodalRiskModel,
    load_model,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image preprocessing (same resize the model expects)
# ---------------------------------------------------------------------------

def _build_transform(image_size: int = 224) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


def _decode_base64_image(b64: str, image_size: int = 224) -> torch.Tensor:
    """
    Decode a base64-encoded image string into a (1, 3, H, W) tensor.

    Accepts both raw base64 and data-URI prefixed strings
    (``data:image/...;base64,...``).
    """
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError(f"Cannot decode image bytes: {exc}") from exc

    transform = _build_transform(image_size)
    return transform(img).unsqueeze(0)  # (1, 3, H, W)


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

class MultimodalModelStore:
    """Holds the loaded multimodal PyTorch model in memory."""

    def __init__(self) -> None:
        self._model: Optional[MultimodalRiskModel] = None
        self.is_loaded: bool = False
        self.device: torch.device = torch.device("cpu")

    def load(self, path: Path | str = MULTIMODAL_MODEL_PATH) -> None:
        try:
            self._model = load_model(path)
            self.device = next(self._model.parameters()).device
            self.is_loaded = True
            logger.info(
                "✅ Multimodal model loaded (v%s) on %s",
                self._model.config.version,
                self.device,
            )
        except FileNotFoundError:
            logger.warning(
                "⚠️  Multimodal model not found at %s. "
                "Train it via: python -m app.ml.multimodal_model",
                path,
            )
            self.is_loaded = False
        except Exception as exc:
            logger.error("❌ Failed to load multimodal model: %s", exc)
            self.is_loaded = False

    def unload(self) -> None:
        self._model = None
        self.is_loaded = False
        logger.info("♻️  Multimodal model unloaded.")

    @property
    def model(self) -> MultimodalRiskModel:
        if not self.is_loaded or self._model is None:
            raise RuntimeError(
                "Multimodal model is not loaded. "
                "Call multimodal_store.load() first or train the model."
            )
        return self._model


# Global singleton
multimodal_store = MultimodalModelStore()


# ---------------------------------------------------------------------------
# Public inference function
# ---------------------------------------------------------------------------

def predict_multimodal(
    weather_vector: List[float],
    soil_type: str,
    image_base64: str,
) -> Dict[str, Any]:
    """
    Run multimodal inference.

    Parameters
    ----------
    weather_vector : list[float]
        Five numeric values: [temperature, humidity, rainfall, wind_speed, soil_moisture].
    soil_type : str
        One of SOIL_TYPES.
    image_base64 : str
        Base64-encoded plant leaf image.

    Returns
    -------
    dict with task-dependent keys (see multimodal_model.py).
    """
    model = multimodal_store.model
    device = multimodal_store.device

    # Validate soil
    soil_key = soil_type.strip().lower()
    if soil_key not in SOIL_TO_ID:
        raise ValueError(
            f"Invalid soil_type '{soil_type}'. Expected one of {SOIL_TYPES}."
        )

    # Decode image
    image_tensor = _decode_base64_image(
        image_base64, image_size=model.config.image_size
    ).to(device)

    # Tensors
    weather_t = torch.tensor(
        [weather_vector], dtype=torch.float32, device=device
    )
    soil_t = torch.tensor(
        [SOIL_TO_ID[soil_key]], dtype=torch.long, device=device
    )

    # Inference
    model.eval()
    with torch.no_grad():
        out = model(image_tensor, weather_t, soil_t)

    # Build result
    if model.config.task == "regression":
        score = float(out.item())
        return {
            "task": "regression",
            "risk_score": round(score, 4),
            "risk_score_pct": round(score * 100.0, 2),
            "model_version": model.config.version,
        }

    # classification
    probs = torch.softmax(out, dim=-1).squeeze(0)
    cls_id = int(torch.argmax(probs).item())
    return {
        "task": "classification",
        "predicted_class": model.config.disease_classes[cls_id],
        "predicted_class_index": cls_id,
        "probabilities": {
            name: round(float(probs[i].item()), 4)
            for i, name in enumerate(model.config.disease_classes)
        },
        "model_version": model.config.version,
    }
