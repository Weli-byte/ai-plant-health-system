"""
app/services/dataset_service.py
===============================
Sprint 4 — External Dataset Management System service layer.

Provides reusable utilities for dataset validation, scanning, 
and sampling without moving the dataset into the repository.

Features:
    - Verifies dataset integrity and structure.
    - Extracts class labels.
    - Samples random images for previews.
    - Provides file paths for internal training pipelines.
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Valid image extensions
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class DatasetService:
    """
    Service for managing the external PlantVillage dataset.
    """

    def __init__(self) -> None:
        self._dataset_path = settings.get_dataset_path
        self._path_obj = Path(self._dataset_path) if self._dataset_path else None

    # -- Core Utilities ---------------------------------------------------

    def get_path(self) -> Optional[Path]:
        """Returns the base path if configured."""
        return self._path_obj

    def validate_dataset(self) -> Dict[str, Any]:
        """
        Scans the external dataset folder to ensure it exists, 
        contains class subfolders, and counts valid images.
        """
        errors = []
        classes = []
        total_images = 0

        # 1. Path exists?
        if not self._path_obj:
            return {
                "is_valid": False,
                "path": "NOT_CONFIGURED",
                "total_classes": 0,
                "total_images": 0,
                "classes": [],
                "errors": ["DATASET_PATH environment variable is not set."],
            }

        if not self._path_obj.exists():
            return {
                "is_valid": False,
                "path": str(self._path_obj),
                "total_classes": 0,
                "total_images": 0,
                "classes": [],
                "errors": [f"Path does not exist: {self._path_obj}"],
            }

        if not self._path_obj.is_dir():
            return {
                "is_valid": False,
                "path": str(self._path_obj),
                "total_classes": 0,
                "total_images": 0,
                "classes": [],
                "errors": [f"Path is not a directory: {self._path_obj}"],
            }

        # 2. Scan folders
        try:
            for item in self._path_obj.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Quick count of images in this subfolder
                    img_count = sum(1 for f in item.iterdir() if f.suffix.lower() in VALID_EXTENSIONS)
                    if img_count > 0:
                        classes.append(item.name)
                        total_images += img_count
        except Exception as exc:
            errors.append(f"Failed to read dataset directory: {exc}")

        classes.sort()

        is_valid = len(classes) > 0 and len(errors) == 0

        if not classes and not errors:
            errors.append("No class subdirectories containing images were found.")
            is_valid = False

        return {
            "is_valid": is_valid,
            "path": str(self._path_obj),
            "total_classes": len(classes),
            "total_images": total_images,
            "classes": classes,
            "errors": errors,
        }

    # -- Sampling ---------------------------------------------------------

    def get_sample_images(self, n_samples: int = 10) -> List[Dict[str, str]]:
        """
        Randomly selects `n_samples` images across available classes.
        Useful for UI preview or dataset sanity checks.
        """
        val_res = self.validate_dataset()
        if not val_res["is_valid"]:
            return []

        all_images = []
        for class_name in val_res["classes"]:
            class_dir = self._path_obj / class_name
            for img_path in class_dir.iterdir():
                if img_path.suffix.lower() in VALID_EXTENSIONS:
                    all_images.append({
                        "class_name": class_name,
                        "image_path": str(img_path.resolve()),
                    })

        if not all_images:
            return []

        # Safe sample size
        k = min(n_samples, len(all_images))
        return random.sample(all_images, k)


# Singleton instance
dataset_service = DatasetService()
