"""
app/services/global_risk_service.py
====================================
Sprint 4 — Week 1: Global Disease Spread Analysis service layer.

Singleton pattern: the GNN model is loaded ONCE from
``backend/models/global_gnn_model.pt`` and reused across requests.

Public API
----------
    global_gnn_store                — singleton holder (``.load()`` at startup).
    analyze_global_risk(reports, config) — orchestrate full pipeline → dict.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from app.ml._paths import GNN_MODEL_PATH
from app.ml.global_gnn_model import (
    MODEL_VERSION,
    GlobalDiseaseGNN,
    GNNConfig,
    build_graph_from_reports,
    load_model,
    predict_regions,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

class GlobalGNNModelStore:
    """
    Holds the loaded GNN model in memory.

    Usage::

        global_gnn_store.load()                         # once at startup
        result = analyze_global_risk(reports, config)   # per request
        global_gnn_store.unload()                       # at shutdown
    """

    def __init__(self) -> None:
        self._model: Optional[GlobalDiseaseGNN] = None
        self._device: Optional[torch.device] = None
        self.is_loaded: bool = False

    # -- lifecycle ---------------------------------------------------------

    def load(self, path: Path | str = GNN_MODEL_PATH) -> None:
        """Load the trained GNN checkpoint from disk."""
        try:
            self._model = load_model(path)
            self._device = next(self._model.parameters()).device
            self.is_loaded = True
            logger.info(
                "✅ Global GNN model loaded (v%s) on %s",
                MODEL_VERSION,
                self._device,
            )
        except FileNotFoundError:
            logger.warning(
                "⚠️  Global GNN model not found at %s. "
                "Train via: python -m app.ml.global_gnn_model",
                path,
            )
            self.is_loaded = False
        except Exception as exc:
            logger.error("❌ Failed to load Global GNN model: %s", exc)
            self.is_loaded = False

    def unload(self) -> None:
        """Release model from memory."""
        self._model = None
        self._device = None
        self.is_loaded = False
        logger.info("♻️  Global GNN model unloaded.")

    @property
    def model(self) -> GlobalDiseaseGNN:
        if not self.is_loaded or self._model is None:
            raise RuntimeError(
                "Global GNN model is not loaded. "
                "Call global_gnn_store.load() first or train the model."
            )
        return self._model

    @property
    def device(self) -> torch.device:
        if self._device is None:
            return torch.device("cpu")
        return self._device


# Global singleton — imported by routes and main.py
global_gnn_store = GlobalGNNModelStore()


# ---------------------------------------------------------------------------
# Public inference orchestrator
# ---------------------------------------------------------------------------

def analyze_global_risk(
    reports: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full pipeline: reports → graph → GNN inference → structured results.

    Parameters
    ----------
    reports : list[dict]
        Disease report dicts with lat, lng, disease_type, weather, etc.
    config : dict | None
        Optional clustering / edge parameters.

    Returns
    -------
    dict
        Structured result matching ``GlobalRiskAnalysisData`` schema.

    Raises
    ------
    RuntimeError — model not loaded.
    ValueError   — empty / invalid reports.
    """
    model = global_gnn_store.model  # raises if not loaded
    device = global_gnn_store.device

    cfg = config or {}
    cluster_radius = cfg.get("cluster_radius_km", 5.0)
    min_reports = cfg.get("min_reports_per_cluster", 2)
    edge_threshold = cfg.get("edge_distance_threshold_km", 15.0)

    # 1. Build graph
    graph_data = build_graph_from_reports(
        reports,
        cluster_radius_km=cluster_radius,
        min_reports_per_cluster=min_reports,
        edge_distance_threshold_km=edge_threshold,
    )

    # 2. Run GNN inference
    region_results = predict_regions(model, graph_data, device=device)

    # 3. Graph summary
    n_nodes = len(graph_data["cluster_info"])
    n_edges_directed = graph_data["edge_index"].shape[1]
    # Subtract self-loops for undirected edge count
    n_self = n_nodes
    n_edges_undirected = max((n_edges_directed - n_self) // 2, 0)
    avg_degree = (n_edges_directed - n_self) / max(n_nodes, 1)

    # 4. Count risk levels for summary message
    high_count = sum(
        1 for r in region_results
        if r.get("disease_heat_level") in ("high", "critical")
    )

    # 5. Generate analysis ID
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    analysis_id = f"gra_{ts}_{uuid.uuid4().hex[:8]}"

    return {
        "analysis_id": analysis_id,
        "total_reports_processed": len(reports),
        "total_regions_identified": n_nodes,
        "graph_summary": {
            "num_nodes": n_nodes,
            "num_edges": n_edges_undirected,
            "avg_node_degree": round(avg_degree, 2),
        },
        "regions": region_results,
        "model_version": MODEL_VERSION,
        "inference_device": str(device),
        "_high_risk_count": high_count,
    }
