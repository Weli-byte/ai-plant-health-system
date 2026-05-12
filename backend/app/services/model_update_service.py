"""
app/services/model_update_service.py
======================================
Sprint 4 — Automated Retraining Infrastructure service layer.

Orchestrates the model lifecycle management system:
    - Retraining orchestration (simulated training loops)
    - Epoch-level metrics tracking
    - Model versioning and checkpoint management
    - Rollback and deployment logic
    - JSON-backed history and registry

Public API
----------
    model_update_service       — module-level singleton.
    .update_model(...)         — start a retraining job.
    .get_training_status()     — live tracking of current job.
    .get_training_history()    — history of completed runs.
    .get_model_versions()      — registry of all model versions.
    .rollback_model(...)       — revert to a previous version.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from app.ml._paths import MODELS_DIR, _BACKEND_ROOT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage Paths
# ---------------------------------------------------------------------------

MLOPS_DATA_DIR = _BACKEND_ROOT / "data" / "mlops"
VERSIONS_PATH = MLOPS_DATA_DIR / "model_versions.json"
HISTORY_PATH = MLOPS_DATA_DIR / "training_history.json"


def _ensure_dir() -> None:
    MLOPS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------

class _TrainingState:
    """Thread-safe state for live training tracking."""

    def __init__(self) -> None:
        self.is_active: bool = False
        self.job_id: Optional[str] = None
        self.model_name: Optional[str] = None
        self.started_at: Optional[str] = None
        self.total_epochs: int = 0
        self.current_epoch: int = 0
        self.current_loss: Optional[float] = None
        self.current_accuracy: Optional[float] = None
        self.status: str = "idle"
        self._lock = threading.RLock()

    def acquire(self, job_id: str, model_name: str, epochs: int) -> bool:
        with self._lock:
            if self.is_active:
                return False
            self.is_active = True
            self.job_id = job_id
            self.model_name = model_name
            self.started_at = datetime.now(timezone.utc).isoformat()
            self.total_epochs = epochs
            self.current_epoch = 0
            self.current_loss = None
            self.current_accuracy = None
            self.status = "running"
            return True

    def update_epoch(self, epoch: int, loss: float, acc: float) -> None:
        with self._lock:
            self.current_epoch = epoch
            self.current_loss = loss
            self.current_accuracy = acc

    def release(self, final_status: str = "completed") -> None:
        with self._lock:
            self.is_active = False
            self.status = final_status

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "training_active": self.is_active,
                "job_id": self.job_id,
                "model_name": self.model_name,
                "status": self.status,
                "started_at": self.started_at,
                "total_epochs": self.total_epochs,
                "current_epoch": self.current_epoch,
                "current_loss": self.current_loss,
                "current_accuracy": self.current_accuracy,
            }


# ---------------------------------------------------------------------------
# MLOps Service
# ---------------------------------------------------------------------------

class ModelUpdateService:
    """
    Central orchestration for model lifecycle, retraining, and versioning.
    """

    def __init__(self) -> None:
        self._state = _TrainingState()
        self._lock = threading.RLock()
        self._versions: List[Dict[str, Any]] = []
        self._history: List[Dict[str, Any]] = []

    # -- Lifecycle ---------------------------------------------------------

    def initialize(self) -> None:
        """Load JSON state on startup."""
        _ensure_dir()
        self._load_state()
        logger.info(
            "✅ MLOps infrastructure initialised — "
            "%d versions, %d history records.",
            len(self._versions), len(self._history)
        )

    def _load_state(self) -> None:
        if VERSIONS_PATH.exists():
            try:
                self._versions = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
            except Exception:
                self._versions = []
        
        if HISTORY_PATH.exists():
            try:
                self._history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            except Exception:
                self._history = []

    def _save_state(self) -> None:
        _ensure_dir()
        VERSIONS_PATH.write_text(json.dumps(self._versions, indent=2), encoding="utf-8")
        HISTORY_PATH.write_text(json.dumps(self._history, indent=2), encoding="utf-8")

    # -- Orchestration -----------------------------------------------------

    def update_model(
        self,
        model_name: str,
        epochs: int,
        learning_rate: float,
        batch_size: int,
        notes: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Queue or start a new retraining job.
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"

        with self._lock:
            # Check if busy
            if self._state.is_active and not force:
                return {
                    "job_id": self._state.job_id or "",
                    "model_name": self._state.model_name or "",
                    "status": "running",
                }

            if force and self._state.is_active:
                logger.warning("⚠️ Forcing new training job, overriding current.")
                self._state.release("cancelled")

            # Acquire state
            acquired = self._state.acquire(job_id, model_name, epochs)
            if not acquired:
                return {
                    "job_id": self._state.job_id or "",
                    "model_name": self._state.model_name or "",
                    "status": "running",
                }

        # Start background thread
        thread = threading.Thread(
            target=self._simulate_training_loop,
            args=(job_id, model_name, epochs, learning_rate, batch_size, notes),
            daemon=True,
            name=f"train-{job_id}",
        )
        thread.start()

        return {
            "job_id": job_id,
            "model_name": model_name,
            "status": "queued",
            "total_epochs": epochs,
        }

    def _simulate_training_loop(
        self,
        job_id: str,
        model_name: str,
        epochs: int,
        lr: float,
        batch_size: int,
        notes: str,
    ) -> None:
        """
        Simulate an actual ML training loop with epoch-level metrics.
        """
        logger.info("🚂 Starting training job %s for %s (%d epochs)", job_id, model_name, epochs)
        
        epoch_metrics = []
        rng = np.random.default_rng()
        
        # Simulated starting metrics
        curr_loss = 0.5 + rng.normal(0, 0.1)
        curr_val_loss = 0.6 + rng.normal(0, 0.1)
        curr_acc = 0.75 + rng.normal(0, 0.05)
        curr_val_acc = 0.70 + rng.normal(0, 0.05)
        
        best_val_acc = curr_val_acc
        best_epoch = 1

        try:
            for ep in range(1, epochs + 1):
                # Check if cancelled
                if self._state.job_id != job_id:
                    logger.info("⛔ Job %s cancelled during epoch %d", job_id, ep)
                    return

                # Simulate work
                time.sleep(1.0) # 1 sec per epoch
                
                # Improve metrics
                curr_loss = max(0.01, curr_loss * rng.uniform(0.85, 0.98))
                curr_val_loss = max(0.02, curr_val_loss * rng.uniform(0.88, 1.0))
                curr_acc = min(0.999, curr_acc + (1.0 - curr_acc) * rng.uniform(0.05, 0.15))
                curr_val_acc = min(0.99, curr_val_acc + (1.0 - curr_val_acc) * rng.uniform(0.02, 0.10))

                if curr_val_acc > best_val_acc:
                    best_val_acc = curr_val_acc
                    best_epoch = ep

                # Record
                metrics = {
                    "epoch": ep,
                    "train_loss": round(float(curr_loss), 4),
                    "val_loss": round(float(curr_val_loss), 4),
                    "train_accuracy": round(float(curr_acc), 4),
                    "val_accuracy": round(float(curr_val_acc), 4),
                    "learning_rate": lr,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                epoch_metrics.append(metrics)
                
                # Update live state
                self._state.update_epoch(ep, round(float(curr_loss), 4), round(float(curr_acc), 4))
                logger.info("   Epoch %d/%d - loss: %.4f, acc: %.4f", ep, epochs, curr_loss, curr_acc)

            # Training complete -> Create version and history
            self._finalize_training(
                job_id, model_name, epochs, lr, batch_size, notes, 
                epoch_metrics, best_val_acc, best_epoch
            )

        except Exception as exc:
            logger.error("❌ Training failed: %s", exc, exc_info=True)
            self._state.release("failed")

    def _finalize_training(
        self, job_id: str, model_name: str, epochs: int, lr: float, bs: int, 
        notes: str, metrics: List[Dict], best_acc: float, best_epoch: int
    ) -> None:
        """Register the new version and history record after successful training."""
        with self._lock:
            # Generate version string
            v_num = len([v for v in self._versions if v["model_name"] == model_name]) + 1
            version_str = f"v{v_num}.0.0"
            version_id = f"{model_name}_{version_str}_{uuid.uuid4().hex[:6]}"
            
            completed_at = datetime.now(timezone.utc).isoformat()
            started_at = self._state.started_at or completed_at
            
            # Deactivate older versions of the same model
            for v in self._versions:
                if v["model_name"] == model_name:
                    v["status"] = "INACTIVE"
            
            # 1. Create model version
            chk_path = str(MODELS_DIR / f"{model_name}_{version_str}.pt")
            new_version = {
                "version_id": version_id,
                "model_version": version_str,
                "model_name": model_name,
                "created_at": completed_at,
                "status": "ACTIVE",
                "accuracy": round(float(best_acc), 4),
                "loss": metrics[-1]["val_loss"] if metrics else 0.0,
                "epochs_trained": epochs,
                "checkpoint_path": chk_path,
                "dataset_size": 1500, # Mock size
                "training_job_id": job_id,
                "notes": notes,
            }
            self._versions.append(new_version)
            
            # 2. Create history record
            history_record = {
                "job_id": job_id,
                "model_name": model_name,
                "model_version": version_str,
                "status": "completed",
                "started_at": started_at,
                "completed_at": completed_at,
                "total_epochs": epochs,
                "final_train_loss": metrics[-1]["train_loss"] if metrics else 0.0,
                "final_val_loss": metrics[-1]["val_loss"] if metrics else 0.0,
                "final_accuracy": metrics[-1]["val_accuracy"] if metrics else 0.0,
                "best_accuracy": round(float(best_acc), 4),
                "best_epoch": best_epoch,
                "learning_rate": lr,
                "batch_size": bs,
                "dataset_size": 1500,
                "notes": notes,
                "epoch_metrics": metrics,
            }
            self._history.append(history_record)
            
            # Save and release
            self._save_state()
            self._state.release("completed")
            
            logger.info("✅ Training job %s finalized. New version: %s (acc: %.4f)", job_id, version_str, best_acc)

    # -- Status & Info -----------------------------------------------------

    def get_training_status(self) -> Dict[str, Any]:
        """Live tracking."""
        state_snap = self._state.snapshot()
        
        job_info = None
        if state_snap["training_active"] or state_snap["status"] == "completed":
             job_info = {
                 "job_id": state_snap["job_id"],
                 "model_name": state_snap["model_name"],
                 "status": state_snap["status"],
                 "started_at": state_snap["started_at"],
                 "total_epochs": state_snap["total_epochs"],
                 "current_epoch": state_snap["current_epoch"],
                 "current_loss": state_snap["current_loss"],
                 "current_accuracy": state_snap["current_accuracy"],
             }
             
        with self._lock:
             last_hist = self._history[-1] if self._history else None
             last_date = last_hist["completed_at"] if last_hist else None
             
        return {
            "training_active": state_snap["training_active"],
            "current_job": job_info,
            "queue_length": 0, # Simplified
            "total_completed_jobs": len([h for h in self._history if h["status"] == "completed"]),
            "total_model_versions": len(self._versions),
            "last_training_date": last_date,
        }

    def get_training_history(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_runs": len(self._history),
                "history": list(reversed(self._history)),
            }

    def get_model_versions(self) -> Dict[str, Any]:
        with self._lock:
            active = next((v for v in self._versions if v["status"] == "ACTIVE"), None)
            return {
                "total_versions": len(self._versions),
                "active_version": active,
                "versions": list(reversed(self._versions)),
            }

    # -- Rollback ----------------------------------------------------------

    def rollback_model(self, target_version_id: str, reason: str) -> Dict[str, Any]:
        """Revert active status to an older checkpoint."""
        with self._lock:
            target = next((v for v in self._versions if v["version_id"] == target_version_id), None)
            if not target:
                raise ValueError(f"Version ID '{target_version_id}' not found.")
            
            model_name = target["model_name"]
            
            # Find current active for this model type
            current_active = next((v for v in self._versions if v["model_name"] == model_name and v["status"] == "ACTIVE"), None)
            prev_id = current_active["version_id"] if current_active else None
            
            if current_active:
                current_active["status"] = "ROLLED_BACK"
                
            target["status"] = "ACTIVE"
            self._save_state()
            
            logger.info("🔄 Rolled back %s to version %s", model_name, target["model_version"])
            
            return {
                "previous_active": prev_id,
                "new_active": target["version_id"],
                "rolled_back_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            }

# Singleton
model_update_service = ModelUpdateService()
