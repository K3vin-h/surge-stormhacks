"""Deterministic stand-ins for the risk / damage / priority models.

Real models would consume satellite imagery and gridded weather. For the
demo these are transparent, bounded calculations so the dashboard and the
`/api/risk|damage|priority` demo endpoints return consistent numbers.
"""
from __future__ import annotations

from typing import Any

from ..schemas.areas import (
    AreaDetail,
    AreaSummary,
    DamageResult,
    PriorityFactor,
    PriorityResult,
    RiskResult,
    RoadRef,
    ShelterRef,
    HospitalRef,
    RouteRef,
)
from ..schemas.common import RiskLevel
from ..util import now_utc
from ..fixtures import areas as fx

RISK_MODEL_VERSION = "risk-heuristic-0.1"
DAMAGE_MODEL_VERSION = "damage-ssim-0.1"
PRIORITY_MODEL_VERSION = "priority-weighted-0.1"

PRIORITY_WEIGHTS = {
    "risk": 0.30,
    "damage": 0.15,
    "population": 0.15,
    "distress_calls": 0.15,
    "injuries": 0.10,
    "vulnerable_population": 0.10,
    "road_inaccessibility": 0.05,
}

# Normalization ceilings used to map raw counts into [0, 1].
NORM = {
    "population": 3_000_000,
    "distress_calls": 100,
    "injuries": 50,
    "vulnerable_population": 500_000,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _risk_level(score: float) -> RiskLevel:
    if score >= 0.8:
        return RiskLevel.severe
    if score >= 0.6:
        return RiskLevel.high
    if score >= 0.4:
        return RiskLevel.moderate
    return RiskLevel.low


def compute_risk(features: dict[str, Any]) -> RiskResult:
    rainfall = _clamp(float(features.get("rainfall_mm", 0)) / 250.0)
    river = _clamp(float(features.get("river_level_m", 0)) / 8.0)
    soil = _clamp(float(features.get("soil_moisture", 0)))
    forecast = _clamp(float(features.get("forecast_severity", 0)))
    # Low elevation and flat slope raise flood risk.
    elevation = float(features.get("elevation_m", 500))
    slope = float(features.get("slope_deg", 5))
    terrain = _clamp((1.0 - _clamp(elevation / 1500.0)) * 0.5
                     + (1.0 - _clamp(slope / 10.0)) * 0.5)
    score = _clamp(
        0.30 * rainfall + 0.25 * river + 0.15 * soil
        + 0.20 * forecast + 0.10 * terrain
    )
    return RiskResult(
        score=round(score, 4),
        risk_level=_risk_level(score),
        model_version=RISK_MODEL_VERSION,
        provenance="synthetic signals (demo)",
        evaluated_at=now_utc(),
    )


def compute_damage_from_signals(features: dict[str, Any]) -> DamageResult:
    # Without before/after imagery, approximate change from flood signals.
    base = _clamp(
        0.5 * _clamp(float(features.get("river_level_m", 0)) / 8.0)
        + 0.5 * _clamp(float(features.get("soil_moisture", 0)))
    )
    return DamageResult(
        score=round(base, 4),
        change_percentage=round(base * 100, 2),
        model_version=DAMAGE_MODEL_VERSION,
        provenance="derived from flood signals (demo)",
        evaluated_at=now_utc(),
    )


def compute_damage_from_images(diff_fraction: float) -> DamageResult:
    diff_fraction = _clamp(diff_fraction)
    return DamageResult(
        score=round(diff_fraction, 4),
        change_percentage=round(diff_fraction * 100, 2),
        model_version=DAMAGE_MODEL_VERSION,
        provenance="image difference (demo)",
        evaluated_at=now_utc(),
    )


def compute_priority(
    *,
    risk_score: float,
    damage_score: float,
    population: int,
    distress_calls: int,
    injuries: int,
    vulnerable_population: int,
    road_accessibility: float,
) -> PriorityResult:
    normalized = {
        "risk": _clamp(risk_score),
        "damage": _clamp(damage_score),
        "population": _clamp(population / NORM["population"]),
        "distress_calls": _clamp(distress_calls / NORM["distress_calls"]),
        "injuries": _clamp(injuries / NORM["injuries"]),
        "vulnerable_population": _clamp(vulnerable_population / NORM["vulnerable_population"]),
        "road_inaccessibility": _clamp(1.0 - road_accessibility),
    }
    factors: list[PriorityFactor] = []
    score = 0.0
    for name, w in PRIORITY_WEIGHTS.items():
        contribution = w * normalized[name]
        score += contribution
        factors.append(PriorityFactor(
            name=name, normalized=round(normalized[name], 4),
            weight=w, contribution=round(contribution, 4),
        ))
    score = _clamp(score)
    level = ("critical" if score >= 0.7 else
             "high" if score >= 0.5 else
             "moderate" if score >= 0.3 else "low")
    return PriorityResult(
        score=round(score, 4),
        priority_level=level,
        factors=factors,
        model_version=PRIORITY_MODEL_VERSION,
        evaluated_at=now_utc(),
    )


def build_summary(area_id: str) -> AreaSummary:
    a = fx.get_area(area_id)
    if a is None:
        raise KeyError(area_id)
    risk = compute_risk(a["signals"])
    damage = compute_damage_from_signals(a["signals"])
    priority = compute_priority(
        risk_score=risk.score,
        damage_score=damage.score,
        population=a["population"],
        distress_calls=a["distress_calls"],
        injuries=a["injuries"],
        vulnerable_population=a["vulnerable_population"],
        road_accessibility=a["road_accessibility"],
    )
    return AreaSummary(
        area_id=area_id, name=a["name"],
        risk=risk, damage=damage, priority=priority,
    )


def build_detail(area_id: str, reports: list[dict[str, Any]] | None = None) -> AreaDetail:
    a = fx.get_area(area_id)
    if a is None:
        raise KeyError(area_id)
    summary = build_summary(area_id)
    return AreaDetail(
        area_id=area_id,
        name=a["name"],
        risk=summary.risk,
        damage=summary.damage,
        priority=summary.priority,
        geometry=fx.geometry_for(area_id),
        population=a["population"],
        distress_calls=a["distress_calls"],
        injuries=a["injuries"],
        vulnerable_population=a["vulnerable_population"],
        road_accessibility=a["road_accessibility"],
        roads=[RoadRef(**r) for r in a["roads"]],
        shelters=[ShelterRef(**s) for s in a["shelters"]],
        hospitals=[HospitalRef(**h) for h in a["hospitals"]],
        routes=[RouteRef(**r) for r in a["routes"]],
        reports=reports or [],
        provenance="synthetic signals + fixture catalog (demo)",
        updated_at=now_utc(),
    )
