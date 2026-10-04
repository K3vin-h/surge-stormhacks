"""Stateless model endpoints for explicit demos/tests only.

The normal dashboard reads area snapshots instead of calling these.
"""
from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter

from ..errors import too_large, validation_error
from ..schemas.areas import DamageResult, PriorityResult, RiskResult
from ..services import models

router = APIRouter(prefix="/api")

MAX_IMAGE_B64 = 8 * 1024 * 1024  # generous encoded-size ceiling for the demo


@router.post("/risk", response_model=RiskResult)
def risk(payload: dict) -> RiskResult:
    features = payload.get("features")
    if not isinstance(features, dict):
        raise validation_error("features object is required.")
    return models.compute_risk(features)


@router.post("/damage", response_model=DamageResult)
def damage(payload: dict) -> DamageResult:
    before = payload.get("before_image_base64")
    after = payload.get("after_image_base64")
    if not before or not after:
        raise validation_error("before_image_base64 and after_image_base64 are required.")
    if len(before) > MAX_IMAGE_B64 or len(after) > MAX_IMAGE_B64:
        raise too_large("Encoded image exceeds the allowed size.")
    try:
        b = base64.b64decode(before, validate=True)
        a = base64.b64decode(after, validate=True)
    except (binascii.Error, ValueError) as err:
        raise validation_error("Images must be valid base64.") from err
    # Demo proxy for change: normalized byte-length delta. Not real damage.
    denom = max(len(b), len(a), 1)
    diff_fraction = abs(len(a) - len(b)) / denom
    return models.compute_damage_from_images(diff_fraction)


@router.post("/priority", response_model=PriorityResult)
def priority(payload: dict) -> PriorityResult:
    required = [
        "risk_score", "damage_score", "population", "distress_calls",
        "injuries", "vulnerable_population", "road_accessibility",
    ]
    missing = [k for k in required if k not in payload]
    if missing:
        raise validation_error(f"Missing fields: {', '.join(missing)}.")
    return models.compute_priority(
        risk_score=float(payload["risk_score"]),
        damage_score=float(payload["damage_score"]),
        population=int(payload["population"]),
        distress_calls=int(payload["distress_calls"]),
        injuries=int(payload["injuries"]),
        vulnerable_population=int(payload["vulnerable_population"]),
        road_accessibility=float(payload["road_accessibility"]),
    )
