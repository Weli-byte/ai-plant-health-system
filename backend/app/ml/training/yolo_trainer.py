"""
app/ml/training/yolo_trainer.py
===============================
YOLOv8 training wrapper for the external dataset.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, Any

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

from app.config.settings import settings
from app.ml.training.config import TrainingConfig
from app.ml._paths import MODELS_DIR

logger = logging.getLogger(__name__)


def train_yolov8(config: TrainingConfig, job_id: str) -> Dict[str, Any]:
    """
    Executes YOLOv8 training.
    Assumes dataset is formatted for classification or detection appropriately.
    """
    if not HAS_YOLO:
        raise ImportError("Ultralytics YOLO is not installed.")

    dataset_path = settings.get_dataset_path
    if not dataset_path or not Path(dataset_path).exists():
        raise ValueError(f"Dataset path not found: {dataset_path}")

    logger.info(f"🚀 Starting YOLOv8 training (Job: {job_id})")

    # For PlantVillage, we use YOLO classification mode
    # If detection is needed, the dataset path should point to a yolo yaml format.
    # We will assume classification mode for external folder structures like PlantVillage.
    model = YOLO("yolov8n-cls.pt")
    
    device = "0" if config.device == "cuda" else "cpu"
    if config.device == "auto":
        device = "" # Ultralytics handles auto
        
    results = model.train(
        data=dataset_path,
        epochs=config.epochs,
        batch=config.batch_size,
        imgsz=config.yolo_img_size,
        lr0=config.learning_rate,
        device=device,
        project="backend/data/mlops/yolo_runs",
        name=f"run_{job_id}",
        exist_ok=True,
    )

    # Save to standard location
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = MODELS_DIR / "yolov8_leaf.pt"
    
    # YOLO saves best.pt in the run directory
    run_dir = Path("backend/data/mlops/yolo_runs") / f"run_{job_id}"
    best_weights = run_dir / "weights" / "best.pt"
    
    if best_weights.exists():
        shutil.copy(best_weights, save_path)
    else:
        logger.warning(f"best.pt not found in {best_weights}. Cannot copy to final destination.")

    return {
        "job_id": job_id,
        "model_name": "yolov8",
        "best_accuracy": float(results.results_dict.get('metrics/accuracy_top1', 0.0)),
        "metrics_history": [],  # YOLO handles its own logging in runs/
        "checkpoint_path": str(save_path),
        "classes": list(results.names.values()) if hasattr(results, 'names') else []
    }
