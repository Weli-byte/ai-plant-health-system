"""
app/ml/training/orchestrator.py
===============================
Centralized training orchestrator.
Manages the training lifecycle: dataset snapshots, pipeline execution, and model registration.
"""

import logging
import uuid
import threading
from typing import Dict, Any

from app.ml.training.config import TrainingConfig
from app.ml.dataset.versioning import dataset_versioning
from app.ml.registry.model_registry import model_registry

logger = logging.getLogger(__name__)


class TrainingOrchestrator:
    def __init__(self):
        self._lock = threading.Lock()

    def run_training_pipeline(self, config: TrainingConfig, notes: str = "") -> Dict[str, Any]:
        """
        Executes the full end-to-end training pipeline.
        1. Snapshots the dataset
        2. Routes to the correct trainer (EfficientNet or YOLOv8)
        3. Registers the new model version in the registry
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        logger.info(f"Starting training pipeline {job_id} for {config.model_name}")

        with self._lock:
            # 1. Dataset Snapshot
            try:
                ds_version = dataset_versioning.create_snapshot(notes=notes)
                dataset_version_id = ds_version["version_id"]
            except Exception as e:
                logger.error(f"Dataset snapshot failed: {e}")
                raise ValueError(f"Cannot start training. Dataset error: {e}")

            # 2. Execute Training
            result = {}
            try:
                if config.model_name == "efficientnet":
                    from app.ml.training.efficientnet_trainer import train_efficientnet
                    result = train_efficientnet(config, job_id)
                elif config.model_name == "yolov8":
                    from app.ml.training.yolo_trainer import train_yolov8
                    result = train_yolov8(config, job_id)
                else:
                    raise ValueError(f"Unknown model name: {config.model_name}")
            except Exception as e:
                logger.error(f"Training failed: {e}")
                raise RuntimeError(f"Training execution failed: {e}")

            # 3. Register Model
            try:
                registry_record = model_registry.register_model(
                    model_name=config.model_name,
                    checkpoint_path=result["checkpoint_path"],
                    accuracy=result["best_accuracy"],
                    dataset_version_id=dataset_version_id,
                    training_job_id=job_id,
                    metrics={"metrics_history": result.get("metrics_history", [])}
                )
                logger.info(f"Model registered successfully: {registry_record['model_id']}")
            except Exception as e:
                logger.error(f"Model registration failed: {e}")
                raise RuntimeError(f"Model registration failed: {e}")

            return {
                "job_id": job_id,
                "model_id": registry_record["model_id"],
                "status": "completed",
                "accuracy": result["best_accuracy"]
            }

training_orchestrator = TrainingOrchestrator()
