"""
app/ml/continual_learning.py
==============================
Sprint 4 — Continual Learning infrastructure.

Provides the core building blocks for an experience-replay-based
continual learning pipeline:

    ReplayBuffer        — fixed-capacity ring buffer with balanced sampling.
    DatasetUpdater      — append verified samples to persistent JSON datasets.
    RetrainingTrigger   — configurable threshold-based trigger logic.
    ModelVersionTracker — metadata persistence for model version history.

All persistent state is stored as JSON files under
``backend/data/continual_learning/`` so the system works without a database.

Public API
----------
    replay_buffer       — module-level singleton ``ReplayBuffer``.
    dataset_updater     — module-level singleton ``DatasetUpdater``.
    retraining_trigger  — module-level singleton ``RetrainingTrigger``.
    version_tracker     — module-level singleton ``ModelVersionTracker``.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.ml._paths import _BACKEND_ROOT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CL_DATA_DIR: Path = _BACKEND_ROOT / "data" / "continual_learning"
REPLAY_BUFFER_PATH: Path = CL_DATA_DIR / "replay_buffer.json"
DATASET_PATH: Path = CL_DATA_DIR / "verified_samples.json"
FEEDBACK_LOG_PATH: Path = CL_DATA_DIR / "feedback_log.json"
VERSION_REGISTRY_PATH: Path = CL_DATA_DIR / "model_versions.json"


def _ensure_dir() -> None:
    """Create the data directory tree if it does not exist."""
    CL_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeedbackSample:
    """A single user-verified prediction sample."""

    sample_id: str
    image_path: str
    predicted_class: str
    corrected_class: str
    confidence: float
    is_correct: bool
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeedbackSample":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ModelVersionMeta:
    """Metadata for a single model checkpoint version."""

    version_id: str
    version_number: int
    training_date: str
    dataset_size: int
    accuracy: float
    loss: float
    replay_samples_used: int
    new_samples_used: int
    notes: str = ""
    is_active: bool = False
    checkpoint_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelVersionMeta":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Replay Buffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    """
    Fixed-capacity experience replay buffer with class-balanced sampling.

    Stores verified feedback samples and provides balanced mini-batches
    for retraining so the model does not forget previously learned classes
    (catastrophic-forgetting mitigation).

    Thread-safe via a reentrant lock.
    """

    def __init__(self, capacity: int = 10_000) -> None:
        self.capacity = capacity
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    # -- persistence -------------------------------------------------------

    def save(self, path: Path | str = REPLAY_BUFFER_PATH) -> None:
        """Persist buffer to disk as JSON."""
        _ensure_dir()
        path = Path(path)
        with self._lock:
            data = {"capacity": self.capacity, "samples": self._buffer}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("💾 Replay buffer saved (%d samples) → %s", len(self._buffer), path)

    def load(self, path: Path | str = REPLAY_BUFFER_PATH) -> None:
        """Restore buffer from disk."""
        path = Path(path)
        if not path.exists():
            logger.info("📂 No existing replay buffer found — starting fresh.")
            return
        with self._lock:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._buffer = data.get("samples", [])
            self.capacity = data.get("capacity", self.capacity)
        logger.info("✅ Replay buffer loaded (%d samples) ← %s", len(self._buffer), path)

    # -- core operations ---------------------------------------------------

    def add(self, sample: FeedbackSample) -> None:
        """Add a verified sample; evict oldest if at capacity."""
        with self._lock:
            self._buffer.append(sample.to_dict())
            if len(self._buffer) > self.capacity:
                self._buffer.pop(0)

    def add_batch(self, samples: Sequence[FeedbackSample]) -> int:
        """Add multiple samples, return count added."""
        with self._lock:
            for s in samples:
                self._buffer.append(s.to_dict())
            overflow = len(self._buffer) - self.capacity
            if overflow > 0:
                self._buffer = self._buffer[overflow:]
        return len(samples)

    def sample_balanced(self, n: int, seed: int | None = None) -> List[Dict[str, Any]]:
        """
        Draw *n* samples with class-balanced stratification.

        Groups by ``corrected_class`` and draws equally from each class,
        filling any remainder via random sampling from the full buffer.
        """
        with self._lock:
            if not self._buffer:
                return []
            n = min(n, len(self._buffer))

            rng = np.random.default_rng(seed)

            by_class: Dict[str, List[int]] = defaultdict(list)
            for idx, s in enumerate(self._buffer):
                by_class[s.get("corrected_class", "unknown")].append(idx)

            per_class = max(1, n // max(len(by_class), 1))
            chosen_indices: List[int] = []

            for cls, indices in by_class.items():
                k = min(per_class, len(indices))
                chosen_indices.extend(rng.choice(indices, size=k, replace=False).tolist())

            # Fill remainder
            remaining = n - len(chosen_indices)
            if remaining > 0:
                pool = [i for i in range(len(self._buffer)) if i not in set(chosen_indices)]
                if pool:
                    extra = rng.choice(pool, size=min(remaining, len(pool)), replace=False)
                    chosen_indices.extend(extra.tolist())

            return [self._buffer[i] for i in chosen_indices[:n]]

    def sample_random(self, n: int, seed: int | None = None) -> List[Dict[str, Any]]:
        """Draw *n* samples uniformly at random."""
        with self._lock:
            if not self._buffer:
                return []
            rng = np.random.default_rng(seed)
            n = min(n, len(self._buffer))
            indices = rng.choice(len(self._buffer), size=n, replace=False)
            return [self._buffer[int(i)] for i in indices]

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def stats(self) -> Dict[str, Any]:
        """Return buffer statistics."""
        with self._lock:
            class_counts: Dict[str, int] = defaultdict(int)
            correct = 0
            for s in self._buffer:
                class_counts[s.get("corrected_class", "unknown")] += 1
                if s.get("is_correct", False):
                    correct += 1
            return {
                "total_samples": len(self._buffer),
                "capacity": self.capacity,
                "utilization_pct": round(len(self._buffer) / max(self.capacity, 1) * 100, 2),
                "class_distribution": dict(class_counts),
                "accuracy_in_buffer": round(correct / max(len(self._buffer), 1), 4),
            }


# ---------------------------------------------------------------------------
# Dataset Updater
# ---------------------------------------------------------------------------

class DatasetUpdater:
    """
    Appends verified feedback samples to a persistent JSON dataset file.

    The dataset grows monotonically — historical data is never deleted.
    A separate ``pending`` counter tracks samples added since the last
    retraining run.
    """

    def __init__(self) -> None:
        self._pending_count: int = 0
        self._lock = threading.RLock()

    def append_sample(self, sample: FeedbackSample) -> int:
        """Append one sample and return new pending count."""
        _ensure_dir()
        with self._lock:
            dataset = self._load_dataset()
            dataset.append(sample.to_dict())
            self._save_dataset(dataset)
            self._pending_count += 1
            return self._pending_count

    def append_batch(self, samples: Sequence[FeedbackSample]) -> int:
        """Append many samples; return new pending count."""
        _ensure_dir()
        with self._lock:
            dataset = self._load_dataset()
            dataset.extend(s.to_dict() for s in samples)
            self._save_dataset(dataset)
            self._pending_count += len(samples)
            return self._pending_count

    def reset_pending(self) -> None:
        """Reset pending counter after a retraining run."""
        with self._lock:
            self._pending_count = 0

    @property
    def pending_count(self) -> int:
        with self._lock:
            return self._pending_count

    @property
    def total_count(self) -> int:
        return len(self._load_dataset())

    def get_all(self) -> List[Dict[str, Any]]:
        return self._load_dataset()

    def get_recent(self, n: int) -> List[Dict[str, Any]]:
        ds = self._load_dataset()
        return ds[-n:] if n < len(ds) else ds

    # -- internal ----------------------------------------------------------

    def _load_dataset(self) -> List[Dict[str, Any]]:
        if not DATASET_PATH.exists():
            return []
        try:
            return json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("⚠️  Corrupted dataset file — returning empty list.")
            return []

    def _save_dataset(self, data: List[Dict[str, Any]]) -> None:
        DATASET_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Retraining Trigger
# ---------------------------------------------------------------------------

@dataclass
class TriggerConfig:
    """Configurable thresholds for automatic retraining."""

    min_new_samples: int = 50
    min_accuracy_drop: float = 0.05
    max_days_since_training: int = 30
    min_buffer_utilization_pct: float = 10.0


class RetrainingTrigger:
    """
    Evaluate whether retraining should be triggered based on configurable
    thresholds (new sample count, accuracy degradation, staleness).
    """

    def __init__(self, config: TriggerConfig | None = None) -> None:
        self.config = config or TriggerConfig()

    def should_retrain(
        self,
        pending_samples: int,
        current_accuracy: float = 1.0,
        baseline_accuracy: float = 1.0,
        last_training_date: str | None = None,
        buffer_utilization_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Evaluate all trigger conditions and return a verdict.

        Returns
        -------
        dict
            ``{should_retrain: bool, reasons: list[str], details: dict}``
        """
        reasons: List[str] = []

        # 1. Sample count threshold
        sample_ok = pending_samples >= self.config.min_new_samples
        if sample_ok:
            reasons.append(
                f"New sample threshold met ({pending_samples} >= {self.config.min_new_samples})"
            )

        # 2. Accuracy degradation
        acc_drop = baseline_accuracy - current_accuracy
        acc_ok = acc_drop >= self.config.min_accuracy_drop
        if acc_ok:
            reasons.append(
                f"Accuracy drop detected ({acc_drop:.4f} >= {self.config.min_accuracy_drop})"
            )

        # 3. Staleness
        stale = False
        if last_training_date:
            try:
                last_dt = datetime.fromisoformat(last_training_date)
                age_days = (datetime.now(timezone.utc) - last_dt).days
                stale = age_days >= self.config.max_days_since_training
                if stale:
                    reasons.append(
                        f"Model stale ({age_days} days >= {self.config.max_days_since_training})"
                    )
            except ValueError:
                pass

        # 4. Buffer utilization
        buf_ok = buffer_utilization_pct >= self.config.min_buffer_utilization_pct
        if buf_ok and sample_ok:
            reasons.append(
                f"Buffer utilization sufficient ({buffer_utilization_pct:.1f}%)"
            )

        should = sample_ok or acc_ok or stale

        return {
            "should_retrain": should,
            "reasons": reasons,
            "details": {
                "pending_samples": pending_samples,
                "sample_threshold": self.config.min_new_samples,
                "accuracy_drop": round(acc_drop, 4),
                "accuracy_threshold": self.config.min_accuracy_drop,
                "is_stale": stale,
                "buffer_utilization_pct": round(buffer_utilization_pct, 2),
            },
        }


# ---------------------------------------------------------------------------
# Model Version Tracker
# ---------------------------------------------------------------------------

class ModelVersionTracker:
    """
    JSON-backed registry of all model versions with rollback support.

    Each version entry stores training metadata, metrics, and the path
    to the saved checkpoint. The ``active`` version is the one currently
    serving predictions.
    """

    def __init__(self, registry_path: Path | str = VERSION_REGISTRY_PATH) -> None:
        self._path = Path(registry_path)
        self._lock = threading.RLock()

    # -- persistence -------------------------------------------------------

    def _load_registry(self) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("⚠️  Corrupted version registry — returning empty list.")
            return []

    def _save_registry(self, data: List[Dict[str, Any]]) -> None:
        _ensure_dir()
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- public API --------------------------------------------------------

    def register_version(self, meta: ModelVersionMeta) -> None:
        """Add a new version and set it as active."""
        with self._lock:
            registry = self._load_registry()
            # Deactivate all previous versions
            for entry in registry:
                entry["is_active"] = False
            meta.is_active = True
            registry.append(meta.to_dict())
            self._save_registry(registry)
        logger.info(
            "📦 Model version registered: v%d (id=%s, acc=%.4f)",
            meta.version_number, meta.version_id, meta.accuracy,
        )

    def get_all_versions(self) -> List[Dict[str, Any]]:
        """Return all versions, newest first."""
        with self._lock:
            return list(reversed(self._load_registry()))

    def get_active_version(self) -> Optional[Dict[str, Any]]:
        """Return the currently active version or ``None``."""
        with self._lock:
            for entry in reversed(self._load_registry()):
                if entry.get("is_active"):
                    return entry
        return None

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Lookup a specific version by ID."""
        with self._lock:
            for entry in self._load_registry():
                if entry.get("version_id") == version_id:
                    return entry
        return None

    @property
    def latest_version_number(self) -> int:
        """Return the highest version number, or 0 if no versions exist."""
        with self._lock:
            registry = self._load_registry()
            if not registry:
                return 0
            return max(e.get("version_number", 0) for e in registry)

    def rollback(self, target_version_id: str) -> Dict[str, Any]:
        """
        Set ``target_version_id`` as the active version.

        Returns the activated version dict.

        Raises
        ------
        ValueError — target version not found.
        """
        with self._lock:
            registry = self._load_registry()
            target = None
            for entry in registry:
                if entry.get("version_id") == target_version_id:
                    target = entry
                    break

            if target is None:
                raise ValueError(f"Version '{target_version_id}' not found in registry.")

            for entry in registry:
                entry["is_active"] = False
            target["is_active"] = True
            self._save_registry(registry)

        logger.info(
            "🔄 Rolled back to version v%d (id=%s)",
            target.get("version_number", -1), target_version_id,
        )
        return target

    @property
    def total_versions(self) -> int:
        with self._lock:
            return len(self._load_registry())


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

replay_buffer = ReplayBuffer(capacity=10_000)
dataset_updater = DatasetUpdater()
retraining_trigger = RetrainingTrigger()
version_tracker = ModelVersionTracker()
