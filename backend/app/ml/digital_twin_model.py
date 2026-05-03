"""
app/ml/digital_twin_model.py
============================
Sprint 4 — Task 3: Digital Twin time-series forecaster.

A PyTorch LSTM that ingests a sliding window of past observations and emits
a multi-horizon risk forecast.

Per-timestep input vector (default ``input_size=7``):

    [risk_score, temperature, humidity, rainfall, wind_speed,
     soil_moisture, plant_health]

Output:
    A vector of length ``len(forecast_horizons)`` with one risk score per
    requested horizon — defaults to ``[3, 7]`` days (i.e. the model emits a
    risk estimate for *day +3* and *day +7* given the recent history).

Public API
----------
    DigitalTwinLSTM         — ``nn.Module`` subclass with ``forward``.
    train_digital_twin      — minimal training loop (synthetic AR data).
    save_model / load_model — checkpoint helpers.
    forecast                — turn raw observation list → forecast dict.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from app.ml._paths import DIGITAL_TWIN_MODEL_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_NAMES: List[str] = [
    "risk_score",
    "temperature",
    "humidity",
    "rainfall",
    "wind_speed",
    "soil_moisture",
    "plant_health",
]

DEFAULT_HORIZONS: List[int] = [3, 7]
DEFAULT_SEQUENCE_LENGTH: int = 14   # 14 days of history → forecast


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class DigitalTwinConfig:
    """All hyperparameters needed to rebuild the model from a checkpoint."""
    input_size: int = len(FEATURE_NAMES)
    hidden_size: int = 64
    num_layers: int = 2
    dropout: float = 0.20
    sequence_length: int = DEFAULT_SEQUENCE_LENGTH
    forecast_horizons: List[int] = field(default_factory=lambda: list(DEFAULT_HORIZONS))
    feature_names: List[str] = field(default_factory=lambda: list(FEATURE_NAMES))
    version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class DigitalTwinLSTM(nn.Module):
    """LSTM encoder → fully-connected head → multi-horizon risk forecast."""

    def __init__(self, config: DigitalTwinConfig | None = None) -> None:
        super().__init__()
        self.config: DigitalTwinConfig = config or DigitalTwinConfig()
        if not self.config.forecast_horizons:
            raise ValueError("forecast_horizons must contain at least one horizon.")

        self.lstm: nn.Module = nn.LSTM(
            input_size=self.config.input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            batch_first=True,
            dropout=self.config.dropout if self.config.num_layers > 1 else 0.0,
        )
        self.head: nn.Module = nn.Sequential(
            nn.Linear(self.config.hidden_size, self.config.hidden_size),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_size, len(self.config.forecast_horizons)),
        )

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        sequence : (B, T, F) float tensor.

        Returns
        -------
        Tensor of shape (B, len(forecast_horizons)), values in [0, 1].
        """
        if sequence.ndim != 3:
            raise ValueError(
                f"sequence must be 3-D (B,T,F); got {tuple(sequence.shape)}"
            )
        if sequence.size(-1) != self.config.input_size:
            raise ValueError(
                f"Last dim {sequence.size(-1)} != input_size {self.config.input_size}"
            )

        lstm_out, _ = self.lstm(sequence)   # (B, T, hidden)
        last_hidden = lstm_out[:, -1, :]    # (B, hidden)
        logits = self.head(last_hidden)     # (B, H)
        return torch.sigmoid(logits)


# ---------------------------------------------------------------------------
# Synthetic data + training
# ---------------------------------------------------------------------------

def _generate_synthetic_series(
    n_series: int,
    config: DigitalTwinConfig,
    seed: int = 11,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Build (X, y) tensors for training.

    Each series is an AR(1)-ish autoregressive sequence; targets are the
    actual future ``risk_score`` values at the requested horizons.
    """
    rng = np.random.default_rng(seed)
    max_horizon = max(config.forecast_horizons)
    series_len = config.sequence_length + max_horizon

    series = np.zeros((n_series, series_len, config.input_size), dtype=np.float32)
    for i in range(n_series):
        # Autoregressive risk score
        risk = np.clip(
            np.cumsum(rng.normal(0.0, 0.05, size=series_len)) + 0.5,
            0.0, 1.0,
        )
        # Other features as noisy correlates of risk
        temp = 24 + rng.normal(0, 3, size=series_len)
        humid = 60 + risk * 30 + rng.normal(0, 5, size=series_len)
        rain = np.clip(rng.gamma(2.0, 5.0, size=series_len), 0.0, 200.0)
        wind = np.clip(8 + rng.normal(0, 3, size=series_len), 0.0, 50.0)
        soil_m = np.clip(50 + rng.normal(0, 10, size=series_len), 0.0, 100.0)
        plant_h = np.clip(1.0 - risk + rng.normal(0, 0.05, size=series_len), 0.0, 1.0)

        series[i, :, 0] = risk
        series[i, :, 1] = temp
        series[i, :, 2] = humid
        series[i, :, 3] = rain
        series[i, :, 4] = wind
        series[i, :, 5] = soil_m
        series[i, :, 6] = plant_h

    X = series[:, : config.sequence_length, :]                      # (N, T, F)
    targets = np.zeros((n_series, len(config.forecast_horizons)), dtype=np.float32)
    for j, h in enumerate(config.forecast_horizons):
        targets[:, j] = series[:, config.sequence_length + h - 1, 0]

    return torch.from_numpy(X), torch.from_numpy(targets)


def train_digital_twin(
    config: DigitalTwinConfig | None = None,
    epochs: int = 5,
    batch_size: int = 16,
    n_series: int = 256,
    lr: float = 1e-3,
    save_path: Path | str = DIGITAL_TWIN_MODEL_PATH,
    device: str | torch.device | None = None,
) -> Dict[str, Any]:
    """Smoke-test training loop; ships a runnable artifact out of the box."""
    config = config or DigitalTwinConfig()
    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    X, y = _generate_synthetic_series(n_series, config)
    X, y = X.to(device), y.to(device)

    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = DigitalTwinLSTM(config).to(device)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    history: List[float] = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for X_b, y_b in loader:
            optimizer.zero_grad(set_to_none=True)
            preds = model(X_b)
            loss = criterion(preds, y_b)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item()) * X_b.size(0)
        epoch_loss /= len(dataset)
        history.append(epoch_loss)
        logger.info("epoch=%d  loss=%.4f", epoch + 1, epoch_loss)

    save_path = Path(save_path)
    save_model(model, save_path)
    return {
        "save_path": str(save_path),
        "epochs": epochs,
        "loss_history": history,
        "device": str(device),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_model(model: DigitalTwinLSTM, path: Path | str = DIGITAL_TWIN_MODEL_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"config": asdict(model.config), "state_dict": model.state_dict()},
        path,
    )
    logger.info("💾 Digital twin checkpoint saved → %s", path)
    return path


def load_model(
    path: Path | str = DIGITAL_TWIN_MODEL_PATH,
    device: str | torch.device | None = None,
) -> DigitalTwinLSTM:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Digital twin checkpoint not found: {path}. "
            f"Train it via: python -m app.ml.digital_twin_model"
        )
    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    payload = torch.load(path, map_location=device, weights_only=False)
    if not isinstance(payload, dict) or "config" not in payload or "state_dict" not in payload:
        raise RuntimeError(
            f"Checkpoint at {path} is malformed (missing 'config'/'state_dict')."
        )
    config = DigitalTwinConfig(**payload["config"])
    model = DigitalTwinLSTM(config).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Sequence preprocessing
# ---------------------------------------------------------------------------

def _validate_observations(
    observations: Sequence[Sequence[float]],
    sequence_length: int,
    n_features: int,
) -> np.ndarray:
    """
    Validate the user-supplied history and pad/trim to ``sequence_length``.

    * Each observation must contain exactly ``n_features`` floats.
    * If fewer than ``sequence_length`` observations are given, the array is
      *front-padded* by repeating the first observation (so the model still
      sees a full window — common forecasting practice).
    * If more, only the last ``sequence_length`` rows are kept.
    """
    if not isinstance(observations, Sequence) or len(observations) == 0:
        raise ValueError("observations must be a non-empty sequence of vectors.")

    rows: List[List[float]] = []
    for i, obs in enumerate(observations):
        if not isinstance(obs, Sequence) or isinstance(obs, (str, bytes)):
            raise ValueError(f"observation #{i} must be a sequence of floats.")
        if len(obs) != n_features:
            raise ValueError(
                f"observation #{i} has {len(obs)} features; expected {n_features}."
            )
        try:
            rows.append([float(v) for v in obs])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"observation #{i} contains non-numeric values: {exc}") from exc

    arr = np.array(rows, dtype=np.float32)

    if arr.shape[0] < sequence_length:
        pad_n = sequence_length - arr.shape[0]
        pad = np.repeat(arr[:1], pad_n, axis=0)
        arr = np.concatenate([pad, arr], axis=0)
    elif arr.shape[0] > sequence_length:
        arr = arr[-sequence_length:]

    return arr


def forecast(
    model: DigitalTwinLSTM,
    observations: Sequence[Sequence[float]],
    device: str | torch.device | None = None,
) -> Dict[str, Any]:
    """
    Run a forecast on a single history window.

    Returns
    -------
    dict
        ``{"horizons_days": [3, 7], "risk_scores": [..], "risk_levels": [..]}``
    """
    device = torch.device(device) if device else next(model.parameters()).device

    arr = _validate_observations(
        observations, model.config.sequence_length, model.config.input_size
    )
    tensor = torch.from_numpy(arr).unsqueeze(0).to(device)  # (1, T, F)

    model.eval()
    with torch.no_grad():
        preds = model(tensor).squeeze(0).cpu().numpy()      # (H,)

    risk_levels = [_risk_level(float(p)) for p in preds]

    return {
        "horizons_days": list(model.config.forecast_horizons),
        "risk_scores": [round(float(p), 4) for p in preds],
        "risk_levels": risk_levels,
    }


def _risk_level(score: float) -> str:
    """Same thresholds the legacy risk service uses."""
    if score < 0.34:
        return "low"
    if score < 0.67:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s → %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    info = train_digital_twin()
    print("\n" + "=" * 60)
    print("✅ Digital twin trained.")
    print(f"   Loss history: {info['loss_history']}")
    print(f"   Device:       {info['device']}")
    print(f"   File:         {info['save_path']}")
    print("=" * 60)
