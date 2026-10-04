"""Sample instructions, reports and events for the local SQLite store.

Only runs when Snowflake is not configured and the local store is empty, so
local dev starts with a populated dashboard. Goes through the real services so
snapshots and events match what a live publish/report would write.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from unittest import mock

from ..schemas.common import GeoPoint
from ..schemas.instructions import PublishInstructionRequest
from ..schemas.reports import SubmitReportRequest
from ..util import now_utc
from . import snowflake_client as sf

log = logging.getLogger("surge.seed")

# (minutes_ago, area_id, payload). Publish payloads carry "instruction_type".
SAMPLES: list[tuple[int, str, dict]] = [
    (320, "kathmandu_valley", {"instruction_type": "advisory",
        "emergency_message": "Bagmati levels are rising. Avoid riverbanks and the Thapathali bridge until further notice."}),
    (300, "sunsari", {"instruction_type": "advisory",
        "emergency_message": "Prepare essential items and monitor official updates. Floodwater may affect low-lying roads in Sunsari."}),
    (280, "saptari", {"instruction_type": "advisory",
        "emergency_message": "Heavy rain upstream. Keep away from the Khado river and prepare to move to higher ground."}),
    (250, "sunsari", {"kind": "rescue_needed", "message": "help us we are drowning in our house", "at": [87.1810, 26.6290]}),
    (230, "bardiya", {"instruction_type": "advisory",
        "emergency_message": "Babai river is high. Avoid low crossings and follow updates from the District Emergency Office."}),
    (210, "sunsari", {"instruction_type": "shelter_in_place",
        "emergency_message": "Remain indoors above ground level in Sunsari. Keep away from rivers and follow official updates."}),
    (190, "saptari", {"kind": "rescue_needed", "message": "help us we are drowning in our house", "at": [86.9970, 26.6180]}),
    (175, "sunsari", {"kind": "road_hazard", "message": "Road in front of me is blocked by floodwater.", "at": [87.1900, 26.6310]}),
    (160, "saptari", {"instruction_type": "shelter_in_place", "roads_to_avoid_ids": ["khado_culvert"],
        "emergency_message": "Remain indoors above ground level in Saptari. Do not cross the Khado River Culvert."}),
    (150, "sunsari", {"kind": "rescue_seen", "message": "I can see someone stuck on a roof across the street.", "at": [87.1750, 26.6200]}),
    (140, "saptari", {"kind": "rescue_seen", "message": "I can see someone stuck on a roof across the street", "at": [86.9990, 26.6170]}),
    (125, "sunsari", {"kind": "rescue_needed", "message": "I am trapped on my roof and my neighbor is injured, we need help", "at": [87.1855, 26.6301]}),
    (110, "bardiya", {"kind": "road_hazard", "message": "Water is over the road near the Babai bridge approach.", "at": [81.4300, 28.3020]}),
    (95, "sunsari", {"instruction_type": "evacuate", "shelter_id": "koshi_community_school",
        "approved_route_id": "east_canal_route", "roads_to_avoid_ids": ["mahendra_underpass"],
        "emergency_message": "Evacuate affected wards immediately using the approved route."}),
    (80, "sunsari", {"kind": "rescue_needed", "message": "Stuck on roof with 3 people near the canal.", "at": [87.1820, 26.6270]}),
    (60, "sunsari", {"kind": "rescue_seen", "message": "Caller reports seeing someone drowning in the river beside them.", "at": [87.1820, 26.6270]}),
    (45, "kathmandu_valley", {"kind": "road_hazard", "message": "Thapathali bridge approach is flooded, cars turning back.", "at": [85.3180, 27.6930]}),
    (30, "sunsari", {"kind": "rescue_needed", "message": "Resident is trapped in a flash flood and requesting rescue.", "at": [87.1790, 26.6250]}),
    (12, "saptari", {"kind": "road_hazard", "message": "Ring road near the market is under water.", "at": [86.9950, 26.6150]}),
    (235, "sunsari", {"kind": "road_hazard", "message": "Embankment road has collapsed near the school, do not drive.", "at": [87.1585, 26.6405], "verify": "actioned"}),
    (205, "kathmandu_valley", {"kind": "rescue_needed", "message": "Elderly couple stuck on second floor in Teku, water rising.", "at": [85.3060, 27.6955], "verify": "reviewed"}),
    (185, "bardiya", {"kind": "rescue_needed", "message": "Family of five on a rooftop near the levee, need a boat.", "at": [81.3960, 28.3140], "verify": "actioned"}),
    (165, "sunsari", {"kind": "rescue_needed", "message": "help us we are drowning in our house", "at": [87.1810, 26.6290], "verify": "duplicate"}),
    (155, "saptari", {"kind": "road_hazard", "message": "Trijuga bridge is cracked and water is over the deck.", "at": [86.9752, 26.6348], "verify": "reviewed"}),
    (135, "kathmandu_valley", {"kind": "rescue_seen", "message": "Saw a man clinging to a tree in the Bishnumati.", "at": [85.2985, 27.7075]}),
    (118, "saptari", {"kind": "rescue_needed", "message": "Our village is cut off, two children have fever.", "at": [87.0100, 26.6050]}),
    (100, "kathmandu_valley", {"instruction_type": "evacuate", "shelter_id": "tudikhel_ground",
        "approved_route_id": "kantipath_route", "roads_to_avoid_ids": ["bagmati_bridge", "teku_road"],
        "emergency_message": "Evacuate riverside wards of Teku and Thapathali now. Walk via Kantipath to Tundikhel Open Ground."}),
    (88, "bardiya", {"kind": "rescue_seen", "message": "Cattle herder stranded on an island in the Orahi Khola.", "at": [81.4425, 28.2925], "verify": "reviewed"}),
    (72, "sunsari", {"kind": "road_hazard", "message": "Budhi Khola ford is impassable, bus stuck midstream.", "at": [87.2140, 26.6330], "verify": "reviewed"}),
    (55, "bardiya", {"kind": "road_hazard", "message": "Gulariya bazaar is waist deep, shops closed.", "at": [81.3525, 28.2150]}),
    (40, "kathmandu_valley", {"kind": "rescue_needed", "message": "Water entering the ground floor of our apartment in Thapathali.", "at": [85.3190, 27.6940]}),
    (22, "saptari", {"kind": "rescue_seen", "message": "Boat capsized near the culvert, people in the water.", "at": [86.9310, 26.6005]}),
    (8, "sunsari", {"kind": "rescue_needed", "message": "Pregnant woman needs to reach hospital, roads flooded.", "at": [87.1880, 26.6220]}),
    (4, "bardiya", {"kind": "rescue_needed", "message": "Elderly man cannot walk, water at knee height inside.", "at": [81.4280, 28.3050]}),
]
SAMPLES.sort(key=lambda s: -s[0])


def _is_empty() -> bool:
    for table in ("INSTRUCTIONS", "REPORTS", "EVENTS"):
        row = sf.query_one(f"SELECT COUNT(*) AS N FROM {table}")
        if row and row["N"]:
            return False
    return True


def seed_samples() -> None:
    if sf.snowflake_configured() or not _is_empty():
        return
    # An explicit government reset leaves the tables empty on purpose.
    from ..services import events, instructions, reports
    from ..services.slate import CLEARED_MARKER

    if CLEARED_MARKER.exists():
        return

    base = now_utc()
    clock = {"t": base}
    fake_now = lambda: clock["t"]  # noqa: E731
    with mock.patch.object(instructions, "now_utc", fake_now), \
         mock.patch.object(reports, "now_utc", fake_now), \
         mock.patch.object(events, "now_utc", fake_now):
        for i, (minutes_ago, area_id, data) in enumerate(SAMPLES):
            clock["t"] = base - timedelta(minutes=minutes_ago)
            if "instruction_type" in data:
                instructions.publish(PublishInstructionRequest(
                    publication_id=f"sample-pub-{i}", area_id=area_id,
                    update_frequency_minutes=60, **data,
                ))
            else:
                report, *_ = reports.submit(SubmitReportRequest(
                    area_id=area_id, kind=data["kind"], message=data["message"],
                    location=GeoPoint(coordinates=data["at"]),
                    reported_at=clock["t"], idempotency_key=f"sample-rep-{i}",
                ))
                if data.get("verify"):
                    sf.execute(
                        "UPDATE REPORTS SET VERIFICATION_STATE = %s WHERE REPORT_ID = %s",
                        [data["verify"], report.report_id],
                    )
    log.info("Seeded %d sample records into the local store.", len(SAMPLES))
