import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import bootstrap, snowflake_client as sf  # noqa: E402
from app.main import app  # noqa: E402
from app.services import answers, events, road_status, slate  # noqa: E402


@pytest.fixture(autouse=True)
def local_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sf, "snowflake_configured", lambda: False)
    monkeypatch.setattr(sf, "LOCAL_DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(sf, "_local", None)
    monkeypatch.setattr(slate, "CLEARED_MARKER", tmp_path / "cleared")
    bootstrap.ensure_schema()
    yield
    if sf._local is not None:
        sf._local.close()


client = TestClient(app)
A, B = sorted(road_status.allowed_road_ids())[:2]


def put(road, status, note=None):
    return client.put(
        f"/api/government/roads/{road}", json={"status": status, "note": note}
    )


def pub():
    return client.get("/api/public/roads/status").json()


def test_round_trip_and_version_changes_each_time():
    assert pub() == {"version": "0", "roads": []}
    versions = [pub()["version"]]
    for road, status in [
        (A, "closed"),
        (B, "flooded"),
        (A, "flooded"),
        (B, "open"),
        (A, "open"),
    ]:
        r = put(road, status, "x")
        assert r.status_code == 200 and r.json()["road_id"] == road
        versions.append(pub()["version"])
    assert all(a != b for a, b in zip(versions, versions[1:]))
    assert pub()["roads"] == []


def test_public_lists_only_non_open():
    put(A, "closed", "bridge out")
    put(B, "flooded")
    put(B, "open")
    roads = pub()["roads"]
    assert [(r["road_id"], r["status"], r["note"]) for r in roads] == [
        (A, "closed", "bridge out")
    ]
    assert roads[0]["updated_at"]


@pytest.mark.parametrize(
    "road", ["way-1", "osm-way-", "osm-way-1a", "osm-way-" + "9" * 40]
)
def test_invalid_road_id_422(road):
    assert put(road, "closed").status_code == 422


def test_invalid_status_and_long_note_422():
    assert put(A, "burning").status_code == 422
    assert put(A, "closed", "n" * 201).status_code == 422


def test_reset_clears_roads():
    put(A, "closed")
    counts = client.post("/api/government/reset").json()
    assert counts["roads"] == 1
    assert pub()["roads"] == []


def test_rasuwa_endpoints():
    assert client.get("/api/public/status/rasuwa").status_code == 200
    assert client.get("/api/government/dashboard").status_code == 200
    r = client.post("/api/chat", json={"area_id": "rasuwa", "question": "Is it safe?"})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("note", ["123", "1.5"])
def test_numeric_looking_note_round_trips_as_string(note):
    put(A, "closed", note)
    assert pub()["roads"][0]["note"] == note
    assert client.get("/api/public/status/rasuwa").status_code == 200


def test_version_changes_on_every_mutation_and_is_zero_when_empty():
    assert pub()["version"] == "0"
    seen = []
    for args in [(A, "closed", "a"), (A, "closed", "b"), (A, "flooded", "b"), (A, "open")]:
        put(*args)
        seen.append(pub()["version"])
    assert seen[-1] == "0"
    assert len(set(seen[:-1])) == 3


def test_concurrent_puts_same_road_leave_one_row_no_500():
    codes = []

    def worker(i):
        codes.append(put(A, "closed" if i % 2 else "flooded", f"n{i}").status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes == [200] * 8
    assert [r["road_id"] for r in pub()["roads"]] == [A]


def test_open_on_road_without_row_records_no_event():
    put(A, "open")
    assert not [e for e in events.list_events(limit=50) if e.kind == "road_status"]
    put(A, "closed")
    put(A, "open")
    assert len([e for e in events.list_events(limit=50) if e.kind == "road_status"]) == 2


def test_placeholder_area_is_not_ranked_on_dashboard():
    ids = [a["area_id"] for a in client.get("/api/government/dashboard").json()["areas"]]
    assert "rasuwa" not in ids and "sunsari" in ids


def test_placeholder_status_reports_unknown_risk():
    s = client.get("/api/public/status/rasuwa").json()["summary"]
    assert s["risk_level"] == "unknown" and s["risk_score"] is None
    assert client.get("/api/public/status/sunsari").json()["summary"]["risk_level"] != "unknown"


def test_placeholder_chat_context_has_no_risk_but_lists_closed_roads():
    put(A, "closed", "landslide")
    put(B, "open")
    ctx = answers.build_context("rasuwa")
    assert "No risk data is available" in ctx
    assert f"{A} (landslide)" in ctx and B not in ctx


def test_unknown_road_id_404_known_ok():
    r = put("osm-way-999999999999", "closed")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert put(A, "closed").status_code == 200


def test_allowlist_fails_closed_when_data_missing(monkeypatch):
    road_status.allowed_road_ids.cache_clear()
    monkeypatch.setattr(road_status, "PREPARED_JSON", road_status.PREPARED_JSON.with_name("nope.json"))
    try:
        assert put(A, "closed").status_code == 503
    finally:
        road_status.allowed_road_ids.cache_clear()


def test_cache_refreshed_after_put_and_reset_and_no_db_on_read(monkeypatch):
    assert pub()["roads"] == []
    put(A, "closed")
    calls = []
    real = sf.query
    monkeypatch.setattr(sf, "query", lambda *a, **k: calls.append(a) or real(*a, **k))
    assert [r["road_id"] for r in pub()["roads"]] == [A]
    pub()
    assert calls == []
    client.post("/api/government/reset")
    assert pub()["roads"] == []


def test_etag_304_when_unchanged():
    put(A, "closed")
    r = client.get("/api/public/roads/status")
    tag = r.headers["etag"]
    assert tag == f'"{r.json()["version"]}"'
    assert client.get("/api/public/roads/status", headers={"If-None-Match": tag}).status_code == 304
    put(A, "flooded")
    assert client.get("/api/public/roads/status", headers={"If-None-Match": tag}).status_code == 200


def test_placeholder_not_in_areas_list_and_map_risk_unknown():
    ids = [a["area_id"] for a in client.get("/api/areas").json()["areas"]]
    assert "rasuwa" not in ids and "sunsari" in ids
    r = client.get("/api/public/map/rasuwa")
    assert r.status_code == 200 and r.json()["risk_level"] == "unknown"
    assert client.get("/api/public/map/sunsari").json()["risk_level"] != "unknown"
