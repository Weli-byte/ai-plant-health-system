"""
app/ml/_paths.py
================
Centralised model-artifact paths for all Sprint 4 ML modules.

Every ML module (risk_model, multimodal_model, digital_twin_model) imports
its default save/load path from here so there is a single source of truth.
"""

from pathlib import Path

# Root of the backend package (backend/)
_BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]

# All trained artifacts live under backend/models/
MODELS_DIR: Path = _BACKEND_ROOT / "models"

# Individual model paths
RISK_MODEL_PATH: Path = MODELS_DIR / "risk_model_v2.pkl"
MULTIMODAL_MODEL_PATH: Path = MODELS_DIR / "multimodal_model.pt"
DIGITAL_TWIN_MODEL_PATH: Path = MODELS_DIR / "digital_twin_model.pt"
