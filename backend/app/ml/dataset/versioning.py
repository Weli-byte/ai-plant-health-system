"""
app/ml/dataset/versioning.py
============================
Dataset Versioning & Metadata Tracking.
Tracks snapshots of the dataset state for reproducibility.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from app.services.dataset_service import dataset_service

VERSION_FILE = Path("backend/data/mlops/dataset_versions.json")


class DatasetVersioning:
    def __init__(self):
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._versions: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if VERSION_FILE.exists():
            try:
                return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        VERSION_FILE.write_text(json.dumps(self._versions, indent=2), encoding="utf-8")

    def create_snapshot(self, notes: str = "") -> Dict[str, Any]:
        """Validates the current dataset and saves a snapshot."""
        val = dataset_service.validate_dataset()
        if not val["is_valid"]:
            raise ValueError("Cannot create snapshot of invalid dataset.")

        snapshot = {
            "version_id": f"ds_v{len(self._versions) + 1}_{uuid.uuid4().hex[:6]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "path": val["path"],
            "total_classes": val["total_classes"],
            "total_images": val["total_images"],
            "classes": val["classes"],
            "notes": notes,
        }

        self._versions.append(snapshot)
        self._save()
        return snapshot

    def get_latest_version(self) -> Dict[str, Any]:
        if not self._versions:
            return self.create_snapshot("Initial automated snapshot")
        return self._versions[-1]

    def get_all_versions(self) -> List[Dict[str, Any]]:
        return list(reversed(self._versions))

dataset_versioning = DatasetVersioning()
