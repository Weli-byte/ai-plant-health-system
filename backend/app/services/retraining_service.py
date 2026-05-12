"""
app/services/retraining_service.py
====================================
Sprint 4 — Continual Learning service layer.

Orchestrates the full continual-learning lifecycle:

    1. Accept user feedback → store in replay buffer + dataset.
    2. Evaluate retraining triggers.
    3. Queue & execute simulated retraining jobs (thread-safe).
    4. Register new model versions.
    5. Support rollback to any previous version.

The retraining itself is currently **simulated** (no real EfficientNet
fine-tuning) — the infrastructure is production-ready for real training
to be plugged in later.

Public API
----------
    retraining_service          — module-level singleton.
    submit_feedback(data)       — process one feedback submission.
    trigger_retraining(opts)    — evaluate triggers & run retraining.
    get_training_status()       — current queue / buffer / trigger state.
    get_model_versions()        — all versions from the registry.
    rollback_model(version_id)  — activate a previous version.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import numpy as np

from app.ml._paths import MODELS_DIR
from app.ml.continual_learning import (
    FeedbackSample,
    ModelVersionMeta,
    dataset_updater,
    replay_buffer,
    retraining_trigger,
    version_tracker,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Training job status
# ---------------------------------------------------------------------------

_STATUS = Literal["idle", "queued", "running", "completed", "failed"]


class _TrainingState:
    """Mutable training-queue state, protected by a lock."""

    def __init__(self) -> None:
        self.status: str = "idle"
        self.current_job_id: Optional[str] = None
        self.last_error: Optional[str] = None
        self._lock = threading.RLock()
        self._training_thread: Optional[threading.Thread] = None

    def acquire(self, job_id: str) -> bool:
        """Try to start a new job. Returns False if one is already running."""
        with self._lock:
            if self.status in ("queued", "running"):
                return False
            self.status = "queued"
            self.current_job_id = job_id
            self.last_error = None
            return True

    def set_running(self) -> None:
        with self._lock:
            self.status = "running"

    def set_completed(self) -> None:
        with self._lock:
            self.status = "completed"
            self.current_job_id = None

    def set_failed(self, error: str) -> None:
        with self._lock:
            self.status = "failed"
            self.last_error = error
            self.current_job_id = None

    def is_busy(self) -> bool:
        with self._lock:
            return self.status in ("queued", "running")

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
                "current_job_id": self.current_job_id,
                "last_error": self.last_error,
            }


# ---------------------------------------------------------------------------
# Retraining Service
# ---------------------------------------------------------------------------

class RetrainingService:
    """
    Orchestrates feedback collection, retraining triggers, simulated
    training runs, model versioning, and rollback.

    Singleton — instantiated once at module level.
    """

    def __init__(self) -> None:
        self._state = _TrainingState()
        self._lock = threading.RLock()

    # -- startup / shutdown ------------------------------------------------

    def initialize(self) -> None:
        """Load persisted state (replay buffer) on startup."""
        replay_buffer.load()
        logger.info(
            "✅ Continual learning system initialised — "
            "buffer=%d, versions=%d",
            replay_buffer.size,
            version_tracker.total_versions,
        )

    def shutdown(self) -> None:
        """Persist state on application shutdown."""
        replay_buffer.save()
        logger.info("♻️  Replay buffer persisted on shutdown.")

    # -- feedback ----------------------------------------------------------

    def submit_feedback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single user feedback submission.

        Steps:
            1. Create a ``FeedbackSample``.
            2. Add to replay buffer.
            3. Append to persistent dataset.
            4. Return acknowledgement with current counts.
        """
        sample_id = f"fb_{uuid.uuid4().hex[:12]}"
        is_correct = data["predicted_class"].strip().lower() == data["corrected_class"].strip().lower()

        sample = FeedbackSample(
            sample_id=sample_id,
            image_path=data["image_path"],
            predicted_class=data["predicted_class"],
            corrected_class=data["corrected_class"],
            confidence=data.get("confidence", 0.0),
            is_correct=is_correct,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=data.get("metadata", {}),
        )

        # Store in both buffer and dataset
        replay_buffer.add(sample)
        pending = dataset_updater.append_sample(sample)

        logger.info(
            "📥 Feedback received: %s → %s (correct=%s, pending=%d)",
            sample.predicted_class,
            sample.corrected_class,
            is_correct,
            pending,
        )

        return {
            "sample_id": sample_id,
            "is_correct": is_correct,
            "buffer_size": replay_buffer.size,
            "pending_samples": dataset_updater.pending_count,
            "dataset_total": dataset_updater.total_count,
        }

    # -- retraining --------------------------------------------------------

    def trigger_retraining(
        self,
        force: bool = False,
        replay_ratio: float = 0.3,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate trigger conditions and start a retraining job if warranted.

        Parameters
        ----------
        force        : Skip threshold checks.
        replay_ratio : Fraction of replay samples in the training batch.
        notes        : Annotation for the new model version.

        Returns
        -------
        dict matching ``RetrainingJobData`` schema.
        """
        # Evaluate trigger
        active = version_tracker.get_active_version()
        last_date = active.get("training_date") if active else None
        buf_stats = replay_buffer.stats()

        evaluation = retraining_trigger.should_retrain(
            pending_samples=dataset_updater.pending_count,
            current_accuracy=buf_stats.get("accuracy_in_buffer", 1.0),
            baseline_accuracy=active.get("accuracy", 1.0) if active else 1.0,
            last_training_date=last_date,
            buffer_utilization_pct=buf_stats.get("utilization_pct", 0.0),
        )

        should = force or evaluation["should_retrain"]

        if not should:
            return {
                "job_id": "",
                "status": "skipped",
                "trigger_evaluation": evaluation,
                "new_version": None,
            }

        # Try to acquire the training queue
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        if not self._state.acquire(job_id):
            return {
                "job_id": self._state.current_job_id or "",
                "status": "queued",
                "trigger_evaluation": evaluation,
                "new_version": None,
            }

        # Run simulated retraining in background thread
        thread = threading.Thread(
            target=self._run_training,
            args=(job_id, replay_ratio, notes),
            daemon=True,
            name=f"retrain-{job_id}",
        )
        self._state._training_thread = thread
        thread.start()

        return {
            "job_id": job_id,
            "status": "queued",
            "trigger_evaluation": evaluation,
            "new_version": None,
        }

    def _run_training(self, job_id: str, replay_ratio: float, notes: str) -> None:
        """
        Simulated retraining pipeline (runs in a background thread).

        In a real implementation this would:
            1. Load the EfficientNet model.
            2. Combine new verified samples + replay buffer samples.
            3. Fine-tune with a low learning rate.
            4. Evaluate on a held-out set.
            5. Save the new checkpoint.

        Currently simulates the workflow with realistic delays and
        metrics to validate the full infrastructure.
        """
        self._state.set_running()
        logger.info("🚂 Retraining started (job=%s)", job_id)

        try:
            # 1. Gather training data
            new_samples = dataset_updater.get_all()
            n_new = len(new_samples)
            n_replay = max(1, int(n_new * replay_ratio))
            replay_samples = replay_buffer.sample_balanced(n_replay)

            total_samples = n_new + len(replay_samples)
            logger.info(
                "📊 Training data: %d new + %d replay = %d total",
                n_new, len(replay_samples), total_samples,
            )

            # 2. Simulate training (sleep to mimic compute)
            time.sleep(3)

            # 3. Simulate metrics
            rng = np.random.default_rng()
            sim_accuracy = float(np.clip(rng.normal(0.92, 0.03), 0.80, 0.99))
            sim_loss = float(np.clip(rng.normal(0.15, 0.05), 0.01, 0.50))

            # 4. Create new version
            next_num = version_tracker.latest_version_number + 1
            version_id = f"v{next_num}_{uuid.uuid4().hex[:8]}"
            checkpoint_path = str(MODELS_DIR / f"efficientnet_v{next_num}.pt")

            meta = ModelVersionMeta(
                version_id=version_id,
                version_number=next_num,
                training_date=datetime.now(timezone.utc).isoformat(),
                dataset_size=total_samples,
                accuracy=round(sim_accuracy, 4),
                loss=round(sim_loss, 4),
                replay_samples_used=len(replay_samples),
                new_samples_used=n_new,
                notes=notes or f"Auto-retrain job {job_id}",
                is_active=True,
                checkpoint_path=checkpoint_path,
            )

            version_tracker.register_version(meta)

            # 5. Reset pending counter
            dataset_updater.reset_pending()

            # 6. Persist buffer
            replay_buffer.save()

            self._state.set_completed()
            logger.info(
                "✅ Retraining completed (job=%s) → v%d (acc=%.4f, loss=%.4f)",
                job_id, next_num, sim_accuracy, sim_loss,
            )

        except Exception as exc:
            self._state.set_failed(str(exc))
            logger.error("❌ Retraining failed (job=%s): %s", job_id, exc)

    # -- status & versions -------------------------------------------------

    def get_training_status(self) -> Dict[str, Any]:
        """Return comprehensive training pipeline status."""
        buf_stats = replay_buffer.stats()
        active = version_tracker.get_active_version()

        evaluation = retraining_trigger.should_retrain(
            pending_samples=dataset_updater.pending_count,
            current_accuracy=buf_stats.get("accuracy_in_buffer", 1.0),
            baseline_accuracy=active.get("accuracy", 1.0) if active else 1.0,
            last_training_date=active.get("training_date") if active else None,
            buffer_utilization_pct=buf_stats.get("utilization_pct", 0.0),
        )

        state_snap = self._state.snapshot()

        return {
            "is_training": self._state.is_busy(),
            "current_job_id": state_snap.get("current_job_id"),
            "pending_samples": dataset_updater.pending_count,
            "dataset_total": dataset_updater.total_count,
            "buffer_stats": buf_stats,
            "trigger_evaluation": evaluation,
            "active_model_version": active.get("version_id") if active else None,
            "total_model_versions": version_tracker.total_versions,
        }

    def get_model_versions(self) -> Dict[str, Any]:
        """Return all model versions + active version."""
        versions = version_tracker.get_all_versions()
        active = version_tracker.get_active_version()

        return {
            "total_versions": len(versions),
            "active_version": active,
            "versions": versions,
        }

    def rollback_model(self, target_version_id: str) -> Dict[str, Any]:
        """Rollback to a previous model version."""
        return version_tracker.rollback(target_version_id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

retraining_service = RetrainingService()
