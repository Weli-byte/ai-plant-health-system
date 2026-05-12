"""
app/services/analytics_service.py
===================================
Sprint 4 — Regional Analytics Engine service layer.

Aggregates disease reports across geographic regions and produces
analytics outputs for dashboards and map visualisations:

    * regional statistics & disease distribution
    * heatmap-ready (lat, lng, intensity) data
    * top-risk-region rankings
    * outbreak trend analysis over time

A built-in mock dataset generator creates realistic Turkish agricultural
data so the system is demo-ready without an external database.

Public API
----------
    analytics_service   — module-level singleton.
    .get_regional_statistics()
    .get_disease_heatmap()
    .get_top_risk_regions(limit)
    .get_outbreak_trends(days)
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DISEASE_TYPES: List[str] = [
    "powdery_mildew", "leaf_blight", "rust", "leaf_spot",
    "bacterial_wilt", "mosaic_virus", "anthracnose",
]

CROP_TYPES: List[str] = [
    "tomato", "wheat", "corn", "rice", "potato", "grape",
]

# Realistic Turkish agricultural regions with coordinates
_TURKEY_REGIONS: List[Dict[str, Any]] = [
    {"name": "Adana",       "lat": 37.00, "lng": 35.32},
    {"name": "Ankara",      "lat": 39.92, "lng": 32.85},
    {"name": "Antalya",     "lat": 36.90, "lng": 30.69},
    {"name": "Bursa",       "lat": 40.19, "lng": 29.06},
    {"name": "Denizli",     "lat": 37.75, "lng": 29.09},
    {"name": "Diyarbakir",  "lat": 37.91, "lng": 40.22},
    {"name": "Elazig",      "lat": 38.67, "lng": 39.22},
    {"name": "Eskisehir",   "lat": 39.77, "lng": 30.52},
    {"name": "Gaziantep",   "lat": 37.06, "lng": 37.38},
    {"name": "Istanbul",    "lat": 41.01, "lng": 28.97},
    {"name": "Izmir",       "lat": 38.42, "lng": 27.14},
    {"name": "Konya",       "lat": 37.87, "lng": 32.49},
    {"name": "Malatya",     "lat": 38.35, "lng": 38.31},
    {"name": "Manisa",      "lat": 38.61, "lng": 27.43},
    {"name": "Mersin",      "lat": 36.80, "lng": 34.63},
    {"name": "Samsun",      "lat": 41.29, "lng": 36.33},
    {"name": "Sanliurfa",   "lat": 37.17, "lng": 38.79},
    {"name": "Tokat",       "lat": 40.31, "lng": 36.55},
    {"name": "Trabzon",     "lat": 41.00, "lng": 39.72},
    {"name": "Van",         "lat": 38.50, "lng": 43.38},
]


# ---------------------------------------------------------------------------
# Mock dataset generator
# ---------------------------------------------------------------------------

def generate_mock_reports(
    n_reports: int = 800,
    n_days: int = 30,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """
    Generate realistic mock disease reports across Turkish regions.

    Each report contains region, coordinates, disease, severity,
    environmental readings, and a timestamp spread over ``n_days``.
    Some regions are intentionally made "hotter" to create realistic
    outbreak clusters.
    """
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc)
    reports: List[Dict[str, Any]] = []

    # Make some regions hotspots (higher report density + severity)
    hotspot_indices = {0, 6, 8, 12, 16}  # Adana, Elazig, Gaziantep, Malatya, Sanliurfa

    for _ in range(n_reports):
        # Bias towards hotspots
        if rng.random() < 0.40:
            ridx = rng.choice(list(hotspot_indices))
        else:
            ridx = rng.integers(0, len(_TURKEY_REGIONS))

        region = _TURKEY_REGIONS[ridx]
        is_hot = ridx in hotspot_indices

        # Jitter coordinates slightly
        lat = region["lat"] + rng.normal(0, 0.05)
        lng = region["lng"] + rng.normal(0, 0.05)

        # Disease — hotspots skew towards severe diseases
        if is_hot:
            disease = rng.choice(["leaf_blight", "rust", "bacterial_wilt", "anthracnose"])
        else:
            disease = rng.choice(DISEASE_TYPES)

        crop = rng.choice(CROP_TYPES)

        humidity = float(np.clip(rng.normal(72 if is_hot else 60, 12), 10, 100))
        temperature = float(np.clip(rng.normal(28 if is_hot else 22, 5), -5, 45))
        rainfall = float(np.clip(rng.exponential(20 if is_hot else 10), 0, 200))

        base_sev = 0.65 if is_hot else 0.35
        severity = float(np.clip(base_sev + rng.normal(0, 0.15), 0, 1))

        # Distribute timestamps with recent-bias for hotspots
        if is_hot:
            day_offset = int(rng.integers(0, min(n_days, 14)))
        else:
            day_offset = int(rng.integers(0, n_days))

        ts = now - timedelta(days=day_offset, hours=int(rng.integers(0, 24)))

        risk = float(np.clip(
            severity * 40 + humidity * 0.3 + (1 if is_hot else 0) * 15 + rng.normal(0, 5),
            0, 100,
        ))

        reports.append({
            "region": region["name"],
            "latitude": round(float(lat), 5),
            "longitude": round(float(lng), 5),
            "disease_type": disease,
            "crop_type": crop,
            "humidity": round(humidity, 1),
            "temperature": round(temperature, 1),
            "rainfall": round(rainfall, 1),
            "severity_score": round(severity, 4),
            "risk_score": round(risk, 2),
            "timestamp": ts.isoformat(),
        })

    return reports


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

def _outbreak_level(score: float) -> str:
    """Classify a 0–100 score into outbreak level."""
    if score < 25:
        return "LOW"
    if score < 50:
        return "MEDIUM"
    if score < 75:
        return "HIGH"
    return "CRITICAL"


def _trend_direction(change_pct: float) -> str:
    """Map percentage change to a categorical direction."""
    if change_pct > 10:
        return "increasing"
    if change_pct < -10:
        return "decreasing"
    return "stable"


def _disease_distribution(reports: List[Dict]) -> List[Dict[str, Any]]:
    """Build disease distribution with percentages."""
    counts = Counter(r["disease_type"] for r in reports)
    total = sum(counts.values()) or 1
    return sorted(
        [
            {"disease": d, "count": c, "percentage": round(c / total * 100, 2)}
            for d, c in counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )


def _region_centroid(reports: List[Dict]) -> Tuple[float, float]:
    """Average lat/lng for a set of reports."""
    lats = [r["latitude"] for r in reports]
    lngs = [r["longitude"] for r in reports]
    return round(float(np.mean(lats)), 5), round(float(np.mean(lngs)), 5)


# ---------------------------------------------------------------------------
# Analytics Service
# ---------------------------------------------------------------------------

class AnalyticsService:
    """
    Regional agricultural intelligence analytics engine.

    Consumes disease report data (mock or real) and produces aggregated
    statistics, heatmap payloads, risk rankings, and trend analyses.
    """

    def __init__(self) -> None:
        self._reports: List[Dict[str, Any]] = []
        self._loaded: bool = False

    # -- lifecycle ---------------------------------------------------------

    def initialize(self) -> None:
        """Load mock data on startup (placeholder for real data source)."""
        self._reports = generate_mock_reports()
        self._loaded = True
        logger.info(
            "✅ Analytics engine initialised — %d mock reports across %d regions.",
            len(self._reports),
            len(set(r["region"] for r in self._reports)),
        )

    def refresh(self, reports: Optional[List[Dict[str, Any]]] = None) -> None:
        """Replace the dataset (call with fresh data or ``None`` for mock)."""
        self._reports = reports if reports is not None else generate_mock_reports()
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and len(self._reports) > 0

    # -- helpers -----------------------------------------------------------

    def _by_region(self) -> Dict[str, List[Dict]]:
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for r in self._reports:
            grouped[r["region"]].append(r)
        return dict(grouped)

    def _by_disease(self) -> Dict[str, List[Dict]]:
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for r in self._reports:
            grouped[r["disease_type"]].append(r)
        return dict(grouped)

    # =====================================================================
    # 1. Regional Statistics
    # =====================================================================

    def get_regional_statistics(self) -> Dict[str, Any]:
        """
        Aggregate disease reports into per-region summaries with
        overall platform-level statistics.
        """
        by_region = self._by_region()
        total_reports = len(self._reports)

        regions: List[Dict[str, Any]] = []
        all_risks: List[float] = []
        all_severities: List[float] = []

        for name, reps in sorted(by_region.items(), key=lambda x: -len(x[1])):
            lat, lng = _region_centroid(reps)
            risks = [r["risk_score"] for r in reps]
            sevs = [r["severity_score"] for r in reps]
            avg_risk = float(np.mean(risks))
            avg_sev = float(np.mean(sevs))

            all_risks.extend(risks)
            all_severities.extend(sevs)

            # Dominant disease / crop
            disease_counts = Counter(r["disease_type"] for r in reps)
            crop_counts = Counter(r["crop_type"] for r in reps)

            regions.append({
                "region": name,
                "latitude": lat,
                "longitude": lng,
                "total_reports": len(reps),
                "risk_score": round(avg_risk, 2),
                "severity_index": round(avg_sev, 4),
                "dominant_disease": disease_counts.most_common(1)[0][0],
                "dominant_crop": crop_counts.most_common(1)[0][0],
                "disease_distribution": _disease_distribution(reps),
                "environment": {
                    "avg_humidity": round(float(np.mean([r["humidity"] for r in reps])), 1),
                    "avg_temperature": round(float(np.mean([r["temperature"] for r in reps])), 1),
                    "avg_rainfall": round(float(np.mean([r["rainfall"] for r in reps])), 1),
                },
            })

        return {
            "total_regions": len(regions),
            "total_reports": total_reports,
            "overall_avg_risk": round(float(np.mean(all_risks)) if all_risks else 0, 2),
            "overall_avg_severity": round(float(np.mean(all_severities)) if all_severities else 0, 4),
            "regions": regions,
            "disease_overview": _disease_distribution(self._reports),
        }

    # =====================================================================
    # 2. Heatmap
    # =====================================================================

    def get_disease_heatmap(self) -> Dict[str, Any]:
        """
        Produce map-visualisation-ready heatmap points.

        Each point = one region with its centroid, intensity score,
        outbreak level, and dominant disease.
        """
        by_region = self._by_region()
        points: List[Dict[str, Any]] = []

        for name, reps in by_region.items():
            lat, lng = _region_centroid(reps)
            risks = [r["risk_score"] for r in reps]
            sevs = [r["severity_score"] for r in reps]

            # Heat score = weighted combo of risk, severity, and density
            density_factor = min(len(reps) / 50.0, 1.0)
            heat = float(np.clip(
                np.mean(risks) * 0.5 + np.mean(sevs) * 100 * 0.3 + density_factor * 100 * 0.2,
                0, 100,
            ))

            disease_counts = Counter(r["disease_type"] for r in reps)

            points.append({
                "region": name,
                "latitude": lat,
                "longitude": lng,
                "heat_score": round(heat, 1),
                "outbreak_level": _outbreak_level(heat),
                "report_count": len(reps),
                "dominant_disease": disease_counts.most_common(1)[0][0],
            })

        # Sort by heat descending
        points.sort(key=lambda p: p["heat_score"], reverse=True)

        scores = [p["heat_score"] for p in points]

        return {
            "total_points": len(points),
            "max_heat_score": max(scores) if scores else 0.0,
            "min_heat_score": min(scores) if scores else 0.0,
            "points": points,
        }

    # =====================================================================
    # 3. Top Risk Regions
    # =====================================================================

    def get_top_risk_regions(self, limit: int = 10) -> Dict[str, Any]:
        """
        Rank regions by risk score and return the top *limit*.
        """
        by_region = self._by_region()
        scored: List[Dict[str, Any]] = []

        for name, reps in by_region.items():
            lat, lng = _region_centroid(reps)
            avg_risk = float(np.mean([r["risk_score"] for r in reps]))
            disease_counts = Counter(r["disease_type"] for r in reps)
            top_diseases = [d for d, _ in disease_counts.most_common(3)]

            scored.append({
                "region": name,
                "latitude": lat,
                "longitude": lng,
                "risk_score": round(avg_risk, 2),
                "disease_count": len(reps),
                "outbreak_level": _outbreak_level(avg_risk),
                "top_diseases": top_diseases,
            })

        scored.sort(key=lambda x: x["risk_score"], reverse=True)
        top = scored[:limit]

        for i, entry in enumerate(top):
            entry["rank"] = i + 1

        return {
            "total_regions_analysed": len(scored),
            "top_regions": top,
        }

    # =====================================================================
    # 4. Outbreak Trends
    # =====================================================================

    def get_outbreak_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyse outbreak trends over the last *days*.

        Produces per-disease and per-region timelines with direction
        indicators (increasing / stable / decreasing).
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        recent = [
            r for r in self._reports
            if datetime.fromisoformat(r["timestamp"]) >= cutoff
        ]

        if not recent:
            return {
                "analysis_period_days": days,
                "overall_trend": "stable",
                "overall_change_pct": 0.0,
                "disease_trends": [],
                "region_trends": [],
            }

        # Split into first half / second half for trend detection
        midpoint = cutoff + timedelta(days=days / 2)
        first_half = [r for r in recent if datetime.fromisoformat(r["timestamp"]) < midpoint]
        second_half = [r for r in recent if datetime.fromisoformat(r["timestamp"]) >= midpoint]

        fh_count = max(len(first_half), 1)
        sh_count = len(second_half)
        overall_change = (sh_count - fh_count) / fh_count * 100

        # --- Disease trends ---
        disease_trends: List[Dict[str, Any]] = []
        by_disease = defaultdict(list)
        for r in recent:
            by_disease[r["disease_type"]].append(r)

        for disease, reps in sorted(by_disease.items(), key=lambda x: -len(x[1])):
            d_first = sum(1 for r in reps if datetime.fromisoformat(r["timestamp"]) < midpoint)
            d_second = len(reps) - d_first
            d_change = (d_second - max(d_first, 1)) / max(d_first, 1) * 100

            timeline = self._build_timeline(reps, days)

            disease_trends.append({
                "disease": disease,
                "total_reports": len(reps),
                "trend_direction": _trend_direction(d_change),
                "change_pct": round(d_change, 1),
                "timeline": timeline,
            })

        # --- Region trends ---
        region_trends: List[Dict[str, Any]] = []
        by_region = defaultdict(list)
        for r in recent:
            by_region[r["region"]].append(r)

        for region, reps in sorted(by_region.items(), key=lambda x: -len(x[1])):
            r_first = sum(1 for r in reps if datetime.fromisoformat(r["timestamp"]) < midpoint)
            r_second = len(reps) - r_first
            r_change = (r_second - max(r_first, 1)) / max(r_first, 1) * 100

            timeline = self._build_timeline(reps, days)

            region_trends.append({
                "region": region,
                "total_reports": len(reps),
                "trend_direction": _trend_direction(r_change),
                "change_pct": round(r_change, 1),
                "timeline": timeline,
            })

        return {
            "analysis_period_days": days,
            "overall_trend": _trend_direction(overall_change),
            "overall_change_pct": round(overall_change, 1),
            "disease_trends": disease_trends,
            "region_trends": region_trends,
        }

    # -- timeline builder --------------------------------------------------

    @staticmethod
    def _build_timeline(reports: List[Dict], days: int) -> List[Dict[str, Any]]:
        """Bucket reports into daily aggregates."""
        now = datetime.now(timezone.utc)
        buckets: Dict[str, List[Dict]] = defaultdict(list)

        for r in reports:
            dt = datetime.fromisoformat(r["timestamp"])
            day_key = dt.strftime("%Y-%m-%d")
            buckets[day_key].append(r)

        timeline: List[Dict[str, Any]] = []
        for d in range(days):
            day = now - timedelta(days=days - 1 - d)
            key = day.strftime("%Y-%m-%d")
            day_reports = buckets.get(key, [])

            if day_reports:
                avg_sev = float(np.mean([r["severity_score"] for r in day_reports]))
                avg_risk = float(np.mean([r["risk_score"] for r in day_reports]))
            else:
                avg_sev = 0.0
                avg_risk = 0.0

            timeline.append({
                "date": key,
                "report_count": len(day_reports),
                "avg_severity": round(avg_sev, 4),
                "avg_risk_score": round(avg_risk, 2),
            })

        return timeline


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

analytics_service = AnalyticsService()
