"""
app/ml/global_gnn_model.py
===========================
Sprint 4 — Week 1: Global Disease Spread Analysis via Graph Neural Network.

A PyTorch Geometric GCN that operates on a spatial graph built from
geo-clustered disease reports. Each node represents a geographic region;
edges connect regions within a configurable distance threshold.

Per-node input vector (default ``input_dim = 22``):

    [avg_lat_norm, avg_lng_norm,                      # 2  spatial
     avg_humidity, avg_temperature, avg_rainfall,      # 3  weather
     avg_severity, report_density, crop_diversity,     # 3  meta
     disease_distribution[0..7],                       # 8  disease one-hot
     crop_distribution[0..5]]                          # 6  crop one-hot

Per-node output (2 values):

    [risk_score ∈ [0,1],  outbreak_probability ∈ [0,1]]

Public API
----------
    GlobalDiseaseGNN            — ``nn.Module`` (PyTorch Geometric).
    GNNConfig                   — dataclass with all hyperparameters.
    build_graph_from_reports    — reports → ``torch_geometric.data.Data``.
    generate_mock_reports       — synthetic dataset for demo/training.
    train_global_gnn            — training loop on synthetic data.
    save_model / load_model     — checkpoint helpers.
    predict_regions             — run inference, return per-node dicts.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from app.ml._paths import GNN_MODEL_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — aligned with existing modules
# ---------------------------------------------------------------------------

DISEASE_TYPES: List[str] = [
    "healthy",
    "powdery_mildew",
    "leaf_blight",
    "rust",
    "leaf_spot",
    "bacterial_wilt",
    "mosaic_virus",
    "anthracnose",
]

CROP_TYPES: List[str] = [
    "tomato", "wheat", "corn", "rice", "potato", "grape",
]

MODEL_VERSION: str = "1.0.0"
RANDOM_SEED: int = 42

# Feature counts
N_SPATIAL: int = 2          # lat_norm, lng_norm
N_WEATHER: int = 3          # humidity, temperature, rainfall
N_META: int = 3             # severity, density, crop_diversity
N_DISEASE: int = len(DISEASE_TYPES)
N_CROP: int = len(CROP_TYPES)
INPUT_DIM: int = N_SPATIAL + N_WEATHER + N_META + N_DISEASE + N_CROP  # 22


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class GNNConfig:
    """All hyperparameters needed to rebuild the model from a checkpoint."""
    input_dim: int = INPUT_DIM
    hidden_dim: int = 64
    num_gnn_layers: int = 2
    dropout: float = 0.20
    output_dim: int = 2           # risk_score, outbreak_probability
    version: str = MODEL_VERSION
    disease_types: List[str] = field(default_factory=lambda: list(DISEASE_TYPES))
    crop_types: List[str] = field(default_factory=lambda: list(CROP_TYPES))


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# GNN Model (uses torch_geometric if available, else pure-PyTorch fallback)
# ---------------------------------------------------------------------------

try:
    from torch_geometric.nn import GCNConv, BatchNorm as GBatchNorm
    from torch_geometric.data import Data as PyGData
    _HAS_PYG = True
except ImportError:
    _HAS_PYG = False
    logger.warning(
        "⚠️  torch_geometric not installed. "
        "GNN will use a pure-PyTorch message-passing fallback. "
        "Install via: pip install torch-geometric"
    )


class _FallbackGCNLayer(nn.Module):
    """Minimal GCN layer without torch_geometric dependency."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.linear = nn.Linear(in_channels, out_channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        n = x.size(0)
        src, dst = edge_index[0], edge_index[1]

        # Transform first
        h = self.linear(x)  # (N, out_channels)

        # Build degree-normalised adjacency  D^{-1/2} A D^{-1/2}
        deg = torch.zeros(n, device=x.device)
        if edge_weight is not None:
            deg.scatter_add_(0, dst, edge_weight)
        else:
            deg.scatter_add_(0, dst, torch.ones(src.size(0), device=x.device))
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float("inf")] = 0.0

        if edge_weight is not None:
            norm = deg_inv_sqrt[src] * edge_weight * deg_inv_sqrt[dst]
        else:
            norm = deg_inv_sqrt[src] * deg_inv_sqrt[dst]

        # Message passing: aggregate neighbours in transformed space
        out = torch.zeros_like(h)
        out.scatter_add_(0, dst.unsqueeze(-1).expand_as(h[src]), h[src] * norm.unsqueeze(-1))
        return out


class GlobalDiseaseGNN(nn.Module):
    """
    2-layer GCN encoder → FC head → per-node [risk, outbreak_prob].

    Works with torch_geometric.data.Data or plain tensors.
    """

    def __init__(self, config: GNNConfig | None = None) -> None:
        super().__init__()
        self.config = config or GNNConfig()

        if _HAS_PYG:
            self.conv1 = GCNConv(self.config.input_dim, self.config.hidden_dim)
            self.conv2 = GCNConv(self.config.hidden_dim, self.config.hidden_dim)
            self.bn1 = GBatchNorm(self.config.hidden_dim)
            self.bn2 = GBatchNorm(self.config.hidden_dim)
        else:
            self.conv1 = _FallbackGCNLayer(self.config.input_dim, self.config.hidden_dim)
            self.conv2 = _FallbackGCNLayer(self.config.hidden_dim, self.config.hidden_dim)
            self.bn1 = nn.BatchNorm1d(self.config.hidden_dim)
            self.bn2 = nn.BatchNorm1d(self.config.hidden_dim)

        self.dropout = nn.Dropout(self.config.dropout)
        self.head = nn.Sequential(
            nn.Linear(self.config.hidden_dim, self.config.hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_dim // 2, self.config.output_dim),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        x          : (N, input_dim) node feature matrix.
        edge_index : (2, E) COO edge indices.
        edge_weight: (E,) optional edge weights.

        Returns
        -------
        Tensor of shape (N, 2) with values in [0, 1] after sigmoid.
        """
        h = self.conv1(x, edge_index, edge_weight)
        h = self.bn1(h)
        h = torch.relu(h)
        h = self.dropout(h)

        h = self.conv2(h, edge_index, edge_weight)
        h = self.bn2(h)
        h = torch.relu(h)
        h = self.dropout(h)

        logits = self.head(h)       # (N, 2)
        return torch.sigmoid(logits)


# ---------------------------------------------------------------------------
# Graph construction from disease reports
# ---------------------------------------------------------------------------

def build_graph_from_reports(
    reports: List[Dict[str, Any]],
    cluster_radius_km: float = 5.0,
    min_reports_per_cluster: int = 2,
    edge_distance_threshold_km: float = 15.0,
) -> Dict[str, Any]:
    """
    Transform a list of disease report dicts into a graph structure.

    Returns
    -------
    dict with keys:
        ``x``            — (N, input_dim) node features (numpy).
        ``edge_index``   — (2, E) edge indices (numpy).
        ``edge_weight``  — (E,) inverse-distance weights (numpy).
        ``cluster_info`` — list of per-cluster metadata dicts.
    """
    from sklearn.cluster import DBSCAN

    if not reports:
        raise ValueError("reports list is empty — cannot build graph.")

    coords = np.array([[r["latitude"], r["longitude"]] for r in reports])

    # DBSCAN with haversine metric (expects radians)
    eps_rad = cluster_radius_km / 6371.0
    clustering = DBSCAN(
        eps=eps_rad,
        min_samples=min_reports_per_cluster,
        metric="haversine",
    ).fit(np.radians(coords))

    labels = clustering.labels_
    unique_labels = sorted(set(labels) - {-1})

    # If DBSCAN produced no valid clusters, treat all reports as one cluster
    if len(unique_labels) == 0:
        labels = np.zeros(len(reports), dtype=int)
        unique_labels = [0]

    # ── Aggregate features per cluster ────────────────────────────────────
    disease_to_idx = {d: i for i, d in enumerate(DISEASE_TYPES)}
    crop_to_idx = {c: i for i, c in enumerate(CROP_TYPES)}

    cluster_info: List[Dict[str, Any]] = []
    node_features: List[np.ndarray] = []

    for cid in unique_labels:
        mask = labels == cid
        cluster_reports = [r for r, m in zip(reports, mask) if m]
        n_rep = len(cluster_reports)

        avg_lat = np.mean([r["latitude"] for r in cluster_reports])
        avg_lng = np.mean([r["longitude"] for r in cluster_reports])
        avg_hum = np.mean([r.get("humidity", 50.0) for r in cluster_reports])
        avg_tmp = np.mean([r.get("temperature", 20.0) for r in cluster_reports])
        avg_rnf = np.mean([r.get("rainfall", 0.0) for r in cluster_reports])
        avg_sev = np.mean([r.get("severity_score", 0.5) for r in cluster_reports])

        # Normalised spatial (rough min-max for Turkey-ish range)
        lat_norm = (avg_lat - 36.0) / 10.0
        lng_norm = (avg_lng - 26.0) / 20.0

        # Normalise weather to [0,1]
        hum_norm = np.clip(avg_hum / 100.0, 0.0, 1.0)
        tmp_norm = np.clip((avg_tmp + 30.0) / 90.0, 0.0, 1.0)
        rnf_norm = np.clip(avg_rnf / 200.0, 0.0, 1.0)

        density = np.clip(n_rep / 20.0, 0.0, 1.0)

        # Crop diversity
        unique_crops = set(r.get("crop_type", "tomato") for r in cluster_reports)
        crop_div = len(unique_crops) / max(len(CROP_TYPES), 1)

        # Disease distribution
        disease_dist = np.zeros(N_DISEASE, dtype=np.float32)
        for r in cluster_reports:
            dt = r.get("disease_type", "healthy")
            idx = disease_to_idx.get(dt, 0)
            disease_dist[idx] += 1
        if disease_dist.sum() > 0:
            disease_dist /= disease_dist.sum()

        # Crop distribution
        crop_dist = np.zeros(N_CROP, dtype=np.float32)
        for r in cluster_reports:
            ct = r.get("crop_type", "tomato")
            idx = crop_to_idx.get(ct, 0)
            crop_dist[idx] += 1
        if crop_dist.sum() > 0:
            crop_dist /= crop_dist.sum()

        # Dominant disease / crop
        dom_disease = DISEASE_TYPES[int(np.argmax(disease_dist))]
        dom_crop = CROP_TYPES[int(np.argmax(crop_dist))]

        feat = np.concatenate([
            [lat_norm, lng_norm],
            [hum_norm, tmp_norm, rnf_norm],
            [avg_sev, density, crop_div],
            disease_dist,
            crop_dist,
        ]).astype(np.float32)

        node_features.append(feat)
        cluster_info.append({
            "region_id": f"region_{cid}",
            "center_lat": round(float(avg_lat), 5),
            "center_lng": round(float(avg_lng), 5),
            "num_reports": n_rep,
            "dominant_disease": dom_disease,
            "dominant_crop": dom_crop,
            "environmental_summary": {
                "avg_humidity": round(float(avg_hum), 2),
                "avg_temperature": round(float(avg_tmp), 2),
                "avg_rainfall": round(float(avg_rnf), 2),
                "avg_severity": round(float(avg_sev), 4),
            },
        })

    x = np.stack(node_features)  # (N, input_dim)

    # ── Build edges ───────────────────────────────────────────────────────
    n_nodes = len(cluster_info)
    src_list, dst_list, wt_list = [], [], []

    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            d = haversine_km(
                cluster_info[i]["center_lat"], cluster_info[i]["center_lng"],
                cluster_info[j]["center_lat"], cluster_info[j]["center_lng"],
            )
            if d <= edge_distance_threshold_km:
                w = 1.0 / max(d, 0.1)  # inverse-distance weight
                src_list.extend([i, j])
                dst_list.extend([j, i])
                wt_list.extend([w, w])

    # Self-loops for isolated nodes
    for i in range(n_nodes):
        src_list.append(i)
        dst_list.append(i)
        wt_list.append(1.0)

    edge_index = np.array([src_list, dst_list], dtype=np.int64)
    edge_weight = np.array(wt_list, dtype=np.float32)

    return {
        "x": x,
        "edge_index": edge_index,
        "edge_weight": edge_weight,
        "cluster_info": cluster_info,
    }


# ---------------------------------------------------------------------------
# Synthetic mock dataset
# ---------------------------------------------------------------------------

_TURKEY_REGIONS = [
    (39.92, 32.85),   # Ankara
    (41.01, 28.97),   # İstanbul
    (38.42, 27.14),   # İzmir
    (37.00, 35.32),   # Adana
    (40.19, 29.06),   # Bursa
    (37.87, 32.49),   # Konya
    (36.90, 30.69),   # Antalya
    (39.77, 30.52),   # Eskişehir
    (40.65, 35.83),   # Tokat
    (37.75, 29.09),   # Denizli
]


def generate_mock_reports(
    n_reports: int = 120,
    n_regions: int = 8,
    seed: int = RANDOM_SEED,
) -> List[Dict[str, Any]]:
    """Generate realistic synthetic disease reports for demo/training."""
    rng = np.random.default_rng(seed)
    n_regions = min(n_regions, len(_TURKEY_REGIONS))
    centers = _TURKEY_REGIONS[:n_regions]

    reports: List[Dict[str, Any]] = []
    for _ in range(n_reports):
        cidx = rng.integers(0, n_regions)
        clat, clng = centers[cidx]

        lat = clat + rng.normal(0, 0.03)
        lng = clng + rng.normal(0, 0.03)
        humidity = float(np.clip(rng.normal(70, 15), 10, 100))
        temperature = float(np.clip(rng.normal(24, 6), -5, 45))
        rainfall = float(np.clip(rng.exponential(15), 0, 200))

        # Severity correlates with humidity & temperature
        base_sev = (humidity / 100) * 0.4 + (1.0 - abs(temperature - 26) / 30) * 0.3
        severity = float(np.clip(base_sev + rng.normal(0, 0.1), 0.0, 1.0))

        disease = rng.choice(DISEASE_TYPES[1:])  # exclude "healthy"
        crop = rng.choice(CROP_TYPES)

        reports.append({
            "latitude": round(float(lat), 5),
            "longitude": round(float(lng), 5),
            "disease_type": disease,
            "humidity": round(humidity, 1),
            "temperature": round(temperature, 1),
            "rainfall": round(rainfall, 1),
            "crop_type": crop,
            "timestamp": "2026-05-10T12:00:00Z",
            "severity_score": round(severity, 4),
        })

    return reports


# ---------------------------------------------------------------------------
# Synthetic training targets
# ---------------------------------------------------------------------------

def _generate_targets(graph_data: Dict[str, Any]) -> np.ndarray:
    """
    Create pseudo ground-truth targets from node features for training.

    Uses a domain-informed formula so the GNN learns meaningful patterns:
      risk = f(severity, humidity, density, disease_entropy)
    """
    x = graph_data["x"]
    n = x.shape[0]
    targets = np.zeros((n, 2), dtype=np.float32)

    for i in range(n):
        hum = x[i, 2]           # normalised humidity
        sev = x[i, 5]           # severity
        density = x[i, 6]       # report density
        disease_dist = x[i, 8:8 + N_DISEASE]
        entropy = float(-np.sum(disease_dist * np.log(disease_dist + 1e-8)))
        entropy_norm = np.clip(entropy / 2.0, 0, 1)

        risk = np.clip(0.3 * hum + 0.3 * sev + 0.2 * density + 0.2 * entropy_norm, 0, 1)
        outbreak = np.clip(risk * 1.1 + np.random.normal(0, 0.05), 0, 1)
        targets[i] = [risk, outbreak]

    return targets


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_global_gnn(
    config: GNNConfig | None = None,
    epochs: int = 30,
    lr: float = 1e-3,
    n_graphs: int = 20,
    save_path: Path | str = GNN_MODEL_PATH,
    device: str | torch.device | None = None,
) -> Dict[str, Any]:
    """Train the GNN on multiple synthetic graphs and save checkpoint."""
    config = config or GNNConfig()
    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model = GlobalDiseaseGNN(config).to(device)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.MSELoss()

    logger.info("🚂 Training Global GNN (epochs=%d, graphs=%d, device=%s)", epochs, n_graphs, device)

    history: List[float] = []
    for epoch in range(epochs):
        epoch_loss = 0.0

        for g_idx in range(n_graphs):
            reports = generate_mock_reports(
                n_reports=np.random.randint(60, 180),
                n_regions=np.random.randint(4, 9),
                seed=RANDOM_SEED + epoch * n_graphs + g_idx,
            )
            graph = build_graph_from_reports(reports)
            targets = _generate_targets(graph)

            x_t = torch.from_numpy(graph["x"]).to(device)
            ei_t = torch.from_numpy(graph["edge_index"]).to(device)
            ew_t = torch.from_numpy(graph["edge_weight"]).to(device)
            y_t = torch.from_numpy(targets).to(device)

            optimizer.zero_grad(set_to_none=True)
            preds = model(x_t, ei_t, ew_t)
            loss = criterion(preds, y_t)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        avg_loss = epoch_loss / n_graphs
        history.append(avg_loss)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info("  epoch=%d/%d  loss=%.5f", epoch + 1, epochs, avg_loss)

    save_path = Path(save_path)
    save_model(model, save_path)
    return {
        "save_path": str(save_path),
        "epochs": epochs,
        "loss_history": history,
        "device": str(device),
        "final_loss": history[-1] if history else float("nan"),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_model(model: GlobalDiseaseGNN, path: Path | str = GNN_MODEL_PATH) -> Path:
    """Persist model checkpoint to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"config": asdict(model.config), "state_dict": model.state_dict()},
        path,
    )
    logger.info("💾 Global GNN checkpoint saved → %s", path)
    return path


def load_model(
    path: Path | str = GNN_MODEL_PATH,
    device: str | torch.device | None = None,
) -> GlobalDiseaseGNN:
    """Load a trained checkpoint. Raises ``FileNotFoundError`` if missing."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"GNN checkpoint not found: {path}. "
            f"Train via: python -m app.ml.global_gnn_model"
        )
    device = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    payload = torch.load(path, map_location=device, weights_only=False)
    if not isinstance(payload, dict) or "config" not in payload or "state_dict" not in payload:
        raise RuntimeError(
            f"Checkpoint at {path} is malformed (missing 'config'/'state_dict')."
        )
    config = GNNConfig(**payload["config"])
    model = GlobalDiseaseGNN(config).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def disease_heat_level(score: float) -> str:
    """Map a 0–100 risk score to a categorical heat level."""
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def predict_regions(
    model: GlobalDiseaseGNN,
    graph_data: Dict[str, Any],
    device: str | torch.device | None = None,
    risk_threshold: float = 50.0,
) -> List[Dict[str, Any]]:
    """
    Run GNN inference and return per-region prediction dicts.

    Parameters
    ----------
    model       : Trained GNN.
    graph_data  : Output of ``build_graph_from_reports``.
    device      : Compute device.
    risk_threshold : Score above which a neighbour is flagged "at risk".

    Returns
    -------
    list[dict]  — one dict per region with scores, heat level, etc.
    """
    device = device or next(model.parameters()).device

    x_t = torch.from_numpy(graph_data["x"]).to(device)
    ei_t = torch.from_numpy(graph_data["edge_index"]).to(device)
    ew_t = torch.from_numpy(graph_data["edge_weight"]).to(device)

    model.eval()
    with torch.no_grad():
        preds = model(x_t, ei_t, ew_t).cpu().numpy()  # (N, 2)

    cluster_info = graph_data["cluster_info"]
    n_nodes = len(cluster_info)

    # Build adjacency dict for neighbour lookup
    adj: Dict[int, List[int]] = {i: [] for i in range(n_nodes)}
    ei = graph_data["edge_index"]
    for k in range(ei.shape[1]):
        s, d = int(ei[0, k]), int(ei[1, k])
        if s != d:
            adj[s].append(d)

    results: List[Dict[str, Any]] = []
    for i in range(n_nodes):
        risk_score = float(np.clip(preds[i, 0] * 100.0, 0, 100))
        outbreak_prob = float(np.clip(preds[i, 1], 0, 1))

        # Find at-risk neighbours
        nearby_at_risk = []
        for nb in set(adj.get(i, [])):
            nb_score = float(preds[nb, 0] * 100.0)
            if nb_score >= risk_threshold:
                nearby_at_risk.append(cluster_info[nb]["region_id"])

        region = {
            **cluster_info[i],
            "regional_risk_score": round(risk_score, 2),
            "outbreak_probability": round(outbreak_prob, 4),
            "disease_heat_level": disease_heat_level(risk_score),
            "nearby_regions_at_risk": nearby_at_risk,
        }
        results.append(region)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s → %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    info = train_global_gnn()
    print("\n" + "=" * 60)
    print("[OK] Global Disease GNN trained.")
    print(f"   Final loss : {info['final_loss']:.5f}")
    print(f"   Device     : {info['device']}")
    print(f"   File       : {info['save_path']}")
    print("=" * 60)
