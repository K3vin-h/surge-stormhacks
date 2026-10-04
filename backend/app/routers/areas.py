"""Area read routes used by the government dashboard."""
from __future__ import annotations

from fastapi import APIRouter

from ..errors import not_found
from ..fixtures import areas as fx
from ..schemas.areas import AreaDetail, AreasResponse
from ..schemas.common import AREA_IDS
from ..services import models, reports as reports_svc
from ..util import now_utc

router = APIRouter(prefix="/api")


@router.get("/areas", response_model=AreasResponse)
def list_areas() -> AreasResponse:
    summaries = [models.build_summary(aid) for aid in AREA_IDS
                 if not (fx.get_area(aid) or {}).get("placeholder")]
    return AreasResponse(areas=summaries, updated_at=now_utc())


@router.get("/areas/{area_id}", response_model=AreaDetail)
def area_detail(area_id: str) -> AreaDetail:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")
    area_reports = [r.model_dump(mode="json") for r in
                    reports_svc.list_reports(area_id=area_id, limit=50)]
    return models.build_detail(area_id, reports=area_reports)
