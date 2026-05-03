"""
app/ml/multimodal_model.py
==========================
Sprint 4 — Task 2: Multimodal disease-risk model.

Three input streams, one head:

    image      → EfficientNet-B0 backbone (pretrained=False by default to keep
                 unit tests offline; pass ``pretrained=True`` in production)
                 → 1280-d feature vector → MLP → ``image_dim`` features.

    weather    → numerical vector (temperature, humidity, rainfall, wind_speed,
                 soil_moisture) → MLP → ``weather_dim`` features.

    soil_type  → categorical id → ``nn.Embedding`` → ``soil_dim`` features.

    fusion     → concat([image, weather, soil]) → MLP → output.

Two output modes:
    * ``"regression"``     → 1 logit, sigmoid → score ∈ [0, 1].
    * ``"classification"`` → ``num_classes`` logits.

Public API
----------
    MultimodalRiskModel       — ``nn.Module`` subclass with ``forward``.
    train_multimodal_model    — minimal training loop (synthetic data).
    save_model / load_model   — checkpoint helpers (config + state_dict).
    dummy_inference           — deterministic inference helper for tests.

Notes
-----
* Pretrained weights are optional (``pretrained=False`` default) so the
  module imports cleanly in offline/CI environments. The forward pass and
  shapes are unaffected by the choice.
* All public functions are fully type-hinted.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torchvision import models

from app.ml._paths import MULTIMODAL_MODEL_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Soil categories shared with the tabular risk model (Task 1)
SOIL_TYPES: List[str] = ["clay", "sandy", "loam", "silt", "peat", "chalky"]
SOIL_TO_ID: Dict[str, int] = {name: i for i, name in enumerate(SOIL_TYPES)}

WEATHER_FEATURES: List[str] = [
    "temperature", "humidity", "rainfall", "wind_speed", "soil_moisture",
]

DISEASE_CLASSES: List[str] = [
    "Healthy", "Powdery Mildew", "Leaf Blight", "Rust",
]


# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------

@dataclass
class MultimodalConfig:
    """All hyperparameters needed to rebuild the architecture."""
    # Inputs
    weather_dim_in: int = len(WEATHER_FEATURES)
    num_soil_types: int = len(SOIL_TYPES)
    soil_embedding_dim: int = 8

    # Encoders
    image_feature_dim: int = 128
    weather_feature_dim: int = 64

    # Fusion
    fusion_hidden_dim: int = 128
    dropout: float = 0.30

    # Output
    task: str = "regression"          # "regression" | "classification"
    num_classes: int = len(DISEASE_CLASSES)

    # Backbone
    pretrained: bool = False           # keep False for offline unit tests
    image_size: int = 224

    # Persisted metadata
    soil_types: List[str] = field(default_factory=lambda: list(SOIL_TYPES))
    weather_features: List[str] = field(default_factory=lambda: list(WEATHER_FEATURES))
    disease_classes: List[str] = field(default_factory=lambda: list(DISEASE_CLASSES))
    version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class MultimodalRiskModel(nn.Module):
    """
    EfficientNet image encoder + MLP weather encoder + soil embedding + fusion.

    Forward signature
    -----------------
        forward(image, weather, soil_type_id) → Tensor

        image          : (B, 3, H, W) float
        weather        : (B, weather_dim_in) float
        soil_type_id   : (B,) long

        returns        : (B,) for regression, (B, num_classes) for classification.
    """

    def __init__(self, config: MultimodalConfig | None = None) -> None:
        super().__init__()
        self.config: MultimodalConfig = config or MultimodalConfig()

        if self.config.task not in {"regression", "classification"}:
            raise ValueError(
                f"Unknown task '{self.config.task}'. "
                "Expected 'regression' or 'classification'."
            )

        # ---- Image encoder: EfficientNet-B0 backbone ----
        # We swap the classifier for an identity to expose raw features (1280-d).
        weights = (
            models.EfficientNet_B0_Weights.DEFAULT
            if self.config.pretrained
            else None
        )
        backbone = models.efficientnet_b0(weights=weights)
        self._image_feature_dim_raw: int = backbone.classifier[1].in_features  # 1280
        backbone.classifier = nn.Identity()
        self.image_backbone: nn.Module = backbone

        self.image_head: nn.Module = nn.Sequential(
            nn.Linear(self._image_feature_dim_raw, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(256, self.config.image_feature_dim),
            nn.ReLU(inplace=True),
        )

        # ---- Weather encoder (MLP) ----
        self.weather_encoder: nn.Module = nn.Sequential(
            nn.Linear(self.config.weather_dim_in, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(64, self.config.weather_feature_dim),
            nn.ReLU(inplace=True),
        )

        # ---- Soil embedding ----
        self.soil_embedding: nn.Module = nn.Embedding(
            num_embeddings=self.config.num_soil_types,
            embedding_dim=self.config.soil_embedding_dim,
        )

        # ---- Fusion head ----
        fused_dim = (
            self.config.image_feature_dim
            + self.config.weather_feature_dim
            + self.config.soil_embedding_dim
        )
        out_features = (
            1 if self.config.task == "regression" else self.config.num_classes
        )
        self.fusion_head: nn.Module = nn.Sequential(
            nn.Linear(fused_dim, self.config.fusion_hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.fusion_hidden_dim, self.config.fusion_hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Linear(self.config.fusion_hidden_dim // 2, out_features),
        )

    # ----- forward -------------------------------------------------------

    def forward(
        self,
        image: torch.Tensor,
        weather: torch.Tensor,
        soil_type_id: torch.Tensor,
    ) -> torch.Tensor:
        if image.ndim != 4:
            raise ValueError(f"image must be 4-D (B,C,H,W); got {tuple(image.shape)}")
        if weather.ndim != 2:
            raise ValueError(f"weather must be 2-D (B,F); got {tuple(weather.shape)}")
        if soil_type_id.ndim != 1:
            raise ValueError(
                f"soil_type_id must be 1-D (B,); got {tuple(soil_type_id.shape)}"
            )

        img_feat = self.image_head(self.image_backbone(image))      # (B, image_feature_dim)
        wx_feat = self.weather_encoder(weather)                     # (B, weather_feature_dim)
        soil_feat = self.soil_embedding(soil_type_id)               # (B, soil_embedding_dim)

        fused = torch.cat([img_feat, wx_feat, soil_feat], dim=1)
        out = self.fusion_head(fused)

        if self.config.task == "regression":
            return torch.sigmoid(out).squeeze(-1)                   # (B,) in [0, 1]
        return out                                                  # (B, num_classes)


# ---------------------------------------------------------------------------
# Synthetic data + training loop
# ---------------------------------------------------------------------------

def _generate_synthetic_batch(
    n: int,
    config: MultimodalConfig,
    device: torch.device,
    seed: int = 7,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build deterministic synthetic data for a smoke-test training loop."""
    g = torch.Generator(device="cpu").manual_seed(seed)

    images = torch.rand(
        (n, 3, config.image_size, config.image_size), generator=g
    )
    weather = torch.randn((n, config.weather_dim_in), generator=g)
    soil_ids = torch.randint(
        low=0, high=config.num_soil_types, size=(n,), generator=g
    )

    if config.task == "regression":
        # Risk increases with humidity (col 1) + rainfall (col 2)
        score = torch.sigmoid(0.7 * weather[:, 1] + 0.5 * weather[:, 2])
        targets = score
    else:
        # Class id derived from soil + weather sum (deterministic-ish)
        logits = (soil_ids.float() + weather.sum(dim=1)) % config.num_classes
        targets = logits.long()

    return (
        images.to(device),
        weather.to(device),
        soil_ids.to(device),
        targets.to(device),
    )


def train_multimodal_model(
    config: MultimodalConfig | None = None,
    epochs: int = 2,
    batch_size: int = 16,
    n_train: int = 64,
    lr: float = 1e-3,
    save_path: Path | str = MULTIMODAL_MODEL_PATH,
    device: str | torch.device | None = None,
) -> Dict[str, Any]:
    """
    Train the multimodal model on synthetic data and save a checkpoint.

    The defaults are tiny on purpose — this is a *bootstrap* training loop so
    the platform ships with a runnable artifact. Real training would feed
    images + matched tabular features + labels via a dedicated ``Dataset``.
    """
    config = config or MultimodalConfig()
    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model = MultimodalRiskModel(config).to(device)
    model.train()

    images, weather, soil_ids, targets = _generate_synthetic_batch(
        n_train, config, device
    )
    if config.task == "regression":
        targets = targets.float()
    dataset = TensorDataset(images, weather, soil_ids, targets)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    if config.task == "regression":
        criterion: nn.Module = nn.MSELoss()
    else:
        criterion = nn.CrossEntropyLoss()

    history: List[float] = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for img_b, wx_b, soil_b, y_b in loader:
            optimizer.zero_grad(set_to_none=True)
            preds = model(img_b, wx_b, soil_b)
            loss = criterion(preds, y_b)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item()) * img_b.size(0)
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

def save_model(model: MultimodalRiskModel, path: Path | str = MULTIMODAL_MODEL_PATH) -> Path:
    """Persist config + state_dict to a single ``.pt`` checkpoint."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"config": asdict(model.config), "state_dict": model.state_dict()},
        path,
    )
    logger.info("💾 Multimodal checkpoint saved → %s", path)
    return path


def load_model(
    path: Path | str = MULTIMODAL_MODEL_PATH,
    device: str | torch.device | None = None,
) -> MultimodalRiskModel:
    """Load a checkpoint and return a model in ``eval`` mode."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Multimodal checkpoint not found: {path}. "
            f"Train it via: python -m app.ml.multimodal_model"
        )

    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    payload = torch.load(path, map_location=device, weights_only=False)
    if not isinstance(payload, dict) or "config" not in payload or "state_dict" not in payload:
        raise RuntimeError(
            f"Checkpoint at {path} is malformed (missing 'config'/'state_dict')."
        )

    config = MultimodalConfig(**payload["config"])
    model = MultimodalRiskModel(config).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Dummy inference helper (used by tests + service layer fallback)
# ---------------------------------------------------------------------------

def dummy_inference(
    model: MultimodalRiskModel,
    weather_vector: List[float],
    soil_type: str,
    device: str | torch.device | None = None,
) -> Dict[str, Any]:
    """
    Run a single inference with a randomly-generated image tensor.

    Useful for end-to-end smoke testing the API surface when no image is
    supplied. The service layer will replace the random image with the
    user-uploaded one.
    """
    if soil_type not in SOIL_TO_ID:
        raise ValueError(
            f"Unknown soil_type '{soil_type}'. "
            f"Expected one of {SOIL_TYPES}."
        )
    if len(weather_vector) != model.config.weather_dim_in:
        raise ValueError(
            f"weather_vector length {len(weather_vector)} != "
            f"{model.config.weather_dim_in}"
        )

    device = torch.device(device) if device else next(model.parameters()).device

    image = torch.rand((1, 3, model.config.image_size, model.config.image_size), device=device)
    weather = torch.tensor([weather_vector], dtype=torch.float32, device=device)
    soil = torch.tensor([SOIL_TO_ID[soil_type]], dtype=torch.long, device=device)

    model.eval()
    with torch.no_grad():
        out = model(image, weather, soil)

    if model.config.task == "regression":
        score = float(out.item())
        return {
            "task": "regression",
            "risk_score": score,
            "risk_score_pct": round(score * 100.0, 2),
        }
    probs = torch.softmax(out, dim=-1).squeeze(0)
    cls_id = int(torch.argmax(probs).item())
    return {
        "task": "classification",
        "predicted_class": model.config.disease_classes[cls_id],
        "predicted_class_index": cls_id,
        "probabilities": {
            cls_name: float(probs[i].item())
            for i, cls_name in enumerate(model.config.disease_classes)
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s → %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    info = train_multimodal_model()
    print("\n" + "=" * 60)
    print("✅ Multimodal model trained.")
    print(f"   Loss history: {info['loss_history']}")
    print(f"   Device:       {info['device']}")
    print(f"   File:         {info['save_path']}")
    print("=" * 60)
