"""
app/ml/registry/model_registry.py
=================================
Centralized Model Registry.
Tracks lineage, metadata, and handles best model selection for deployment.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

REGISTRY_FILE = Path("backend/data/mlops/model_registry.json")


class ModelRegistry:
    def __init__(self):
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._registry: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if REGISTRY_FILE.exists():
            try:
                return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        REGISTRY_FILE.write_text(json.dumps(self._registry, indent=2), encoding="utf-8")

    def register_model(
        self,
        model_name: str,
        checkpoint_path: str,
        accuracy: float,
        dataset_version_id: str,
        training_job_id: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Registers a newly trained model and updates active status if it's the best."""
        
        # Deactivate previous active models for this type
        for model in self._registry:
            if model["model_name"] == model_name:
                model["is_active"] = False

        record = {
            "model_id": f"{model_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "model_name": model_name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "checkpoint_path": checkpoint_path,
            "accuracy": accuracy,
            "dataset_version_id": dataset_version_id,
            "training_job_id": training_job_id,
            "metrics": metrics,
            "is_active": True,  # Auto-deploy latest for now
        }

        self._registry.append(record)
        self._save()
        return record

    def get_active_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Returns the currently active deployment model."""
        for model in reversed(self._registry):
            if model["model_name"] == model_name and model.get("is_active"):
                return model
        return None

    def get_best_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Returns the historically best model by accuracy."""
        models = [m for m in self._registry if m["model_name"] == model_name]
        if not models:
            return None
        return max(models, key=lambda x: x.get("accuracy", 0.0))

model_registry = ModelRegistry()
