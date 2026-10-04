import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import bootstrap, snowflake_client as sf  # noqa: E402
from app.schemas.common import GeoPoint, ReportKind, VerificationState  # noqa: E402
from app.schemas.reports import SubmitReportRequest  # noqa: E402
from app.services import reports  # noqa: E402


@pytest.fixture(autouse=True)
def local_db(tmp_path, monkeypatch):
    monkeypatch.setattr(sf, "snowflake_configured", lambda: False)
    monkeypatch.setattr(sf, "LOCAL_DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(sf, "_local", None)
    bootstrap.ensure_schema()
    yield
    if sf._local is not None:
        sf._local.close()


def _req(device, lng=85.0, lat=28.0, kind=ReportKind.rescue_needed, area=None, msg="help", key=None):
    return SubmitReportRequest(
        area_id=area or _area(), kind=kind, message=msg,
        location=GeoPoint(coordinates=[lng, lat]), device_id=device, idempotency_key=key,
    )


def _area():
    from app.fixtures import areas as fx
    return next(iter(fx.AREAS))


def _rows(device, kind=None):
    q = "SELECT * FROM REPORTS WHERE DEVICE_ID = %s"
    p = [device]
    if kind:
        q += " AND KIND = %s"
        p.append(kind)
    return sf.query(q, p)


def test_ensure_schema_twice_is_safe():
    bootstrap.ensure_schema()


def test_repeat_sos_moves_existing_pin():
    first, created, moved = reports.submit(_req("d1"))
    assert created and not moved
    reports.set_state(first.report_id, VerificationState.actioned)
    second, created, moved = reports.submit(_req("d1", lng=86.0, lat=29.0, msg="moved"))
    assert (second.report_id, created, moved) == (first.report_id, False, True)
    rows = _rows("d1")
    assert len(rows) == 1
    r = rows[0]
    assert (r["LONGITUDE"], r["LATITUDE"], r["MESSAGE"]) == (86.0, 29.0, "moved")
    assert r["VERIFICATION_STATE"] == "unverified"


def test_sos_after_resolved_creates_new_report():
    first, *_ = reports.submit(_req("d1"))
    reports.set_state(first.report_id, VerificationState.resolved)
    second, created, moved = reports.submit(_req("d1"))
    assert second.report_id != first.report_id and created and not moved


def test_different_device_gets_separate_row():
    a, *_ = reports.submit(_req("d1"))
    b, *_ = reports.submit(_req("d2"))
    assert a.report_id != b.report_id


def test_road_hazard_not_deduplicated():
    reports.submit(_req("d1", kind=ReportKind.road_hazard))
    reports.submit(_req("d1", kind=ReportKind.road_hazard))
    assert len(_rows("d1", "road_hazard")) == 2


def test_sos_moves_across_areas():
    from app.fixtures import areas as fx
    a1, a2 = list(fx.AREAS)[:2]
    first, *_ = reports.submit(_req("d1", area=a1))
    second, _, moved = reports.submit(_req("d1", area=a2))
    assert moved and second.report_id == first.report_id and second.area_id == a2


def test_retry_of_move_is_noop():
    first, *_ = reports.submit(_req("d1", key="k1"))
    reports.submit(_req("d1", key="k2", lng=86.0))
    reports.set_state(first.report_id, VerificationState.actioned)
    _, created, moved = reports.submit(_req("d1", key="k2", lng=86.0))
    assert (created, moved) == (False, False)
    assert _rows("d1")[0]["VERIFICATION_STATE"] == "actioned"


@pytest.mark.parametrize("key,lng", [("k1", 85.0), ("k2", 86.0)])
def test_retry_of_earlier_sos_keeps_latest_location_and_actioned_state(key, lng):
    first, *_ = reports.submit(_req("d1", key="k1", lng=85.0))
    reports.submit(_req("d1", key="k2", lng=86.0))
    reports.submit(_req("d1", key="k3", lng=87.0))
    reports.set_state(first.report_id, VerificationState.actioned)
    event_count = len(sf.query("SELECT * FROM EVENTS"))
    report, created, moved = reports.submit(_req("d1", key=key, lng=lng))
    assert (report.report_id, created, moved) == (first.report_id, False, False)
    assert report.location.lng == 87.0
    assert report.verification_state == VerificationState.actioned
    assert len(_rows("d1")) == 1
    assert len(sf.query("SELECT * FROM EVENTS")) == event_count


def test_retry_from_previous_area_does_not_move_pin_back():
    from app.fixtures import areas as fx
    a1, a2 = list(fx.AREAS)[:2]
    first, *_ = reports.submit(_req("d1", area=a1, key="old"))
    reports.submit(_req("d1", area=a2, key="new", lng=86.0))
    reports.set_state(first.report_id, VerificationState.resolved)
    retry, created, moved = reports.submit(_req("d1", area=a1, key="old"))
    assert (retry.report_id, created, moved) == (first.report_id, False, False)
    assert retry.area_id == a2
    assert retry.location.lng == 86.0
    assert retry.verification_state == VerificationState.resolved


def test_move_preserves_legacy_key_without_history():
    first, *_ = reports.submit(_req("d1", key="legacy"))
    sf.execute("DELETE FROM REPORT_REQUEST_KEYS")
    reports.submit(_req("d1", key="new", lng=86.0))
    retry, created, moved = reports.submit(_req("d1", key="legacy"))
    assert (retry.report_id, created, moved) == (first.report_id, False, False)
    assert retry.location.lng == 86.0


def test_earlier_retry_remains_noop_after_database_reconnect(monkeypatch):
    first, *_ = reports.submit(_req("d1", key="old"))
    reports.submit(_req("d1", key="new", lng=86.0))
    reports.set_state(first.report_id, VerificationState.actioned)
    sf._local.close()
    monkeypatch.setattr(sf, "_local", None)
    bootstrap.ensure_schema()
    retry, created, moved = reports.submit(_req("d1", key="old"))
    assert (created, moved) == (False, False)
    assert retry.location.lng == 86.0
    assert retry.verification_state == VerificationState.actioned


@pytest.mark.parametrize("retry_before_next_move", [False, True])
def test_retry_recovers_after_history_registration_fails(monkeypatch, retry_before_next_move):
    first, *_ = reports.submit(_req("d1", key="old"))
    execute = sf.execute

    def fail_new_history(sql, params=None):
        if "INSERT INTO REPORT_REQUEST_KEYS" in sql and params[1] == "new":
            raise RuntimeError("History write interrupted")
        return execute(sql, params)

    with monkeypatch.context() as patch:
        patch.setattr(sf, "execute", fail_new_history)
        with pytest.raises(RuntimeError, match="History write interrupted"):
            reports.submit(_req("d1", key="new", lng=86.0))
    reports.set_state(first.report_id, VerificationState.actioned)
    if retry_before_next_move:
        retry, created, moved = reports.submit(_req("d1", key="new", lng=86.0))
        assert (created, moved) == (False, False)
        assert retry.location.lng == 86.0
        assert retry.verification_state == VerificationState.actioned
    reports.submit(_req("d1", key="newest", lng=87.0))
    reports.set_state(first.report_id, VerificationState.actioned)
    retry, created, moved = reports.submit(_req("d1", key="new", lng=86.0))
    assert (created, moved) == (False, False)
    assert retry.location.lng == 87.0
    assert retry.verification_state == VerificationState.actioned
    old_retry, created, moved = reports.submit(_req("d1", key="old"))
    assert (created, moved) == (False, False)
    assert old_retry.location.lng == 87.0


def test_failed_legacy_key_preservation_aborts_move(monkeypatch):
    first, *_ = reports.submit(_req("d1", key="legacy"))
    reports.set_state(first.report_id, VerificationState.actioned)
    sf.execute("DELETE FROM REPORT_REQUEST_KEYS")
    execute = sf.execute

    def fail_history(sql, params=None):
        if "INSERT INTO REPORT_REQUEST_KEYS" in sql:
            raise RuntimeError("History write interrupted")
        return execute(sql, params)

    with monkeypatch.context() as patch:
        patch.setattr(sf, "execute", fail_history)
        with pytest.raises(RuntimeError, match="History write interrupted"):
            reports.submit(_req("d1", key="new", lng=86.0))
    row = _rows("d1")[0]
    assert row["LONGITUDE"] == 85.0
    assert row["IDEMPOTENCY_KEY"] == "legacy"
    assert row["VERIFICATION_STATE"] == "actioned"


def test_no_device_id_never_dedupes():
    reports.submit(_req(None))
    reports.submit(_req(None))
    assert len(sf.query("SELECT * FROM REPORTS WHERE DEVICE_ID IS NULL")) == 2


def test_concurrent_sos_from_one_device_makes_one_row():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda _: reports.submit(_req("d1")), range(8)))
    assert len(_rows("d1")) == 1


def test_ensure_schema_adds_column_to_legacy_table():
    sf.execute("DROP TABLE REPORTS")
    sf.execute("""CREATE TABLE REPORTS (REPORT_ID STRING NOT NULL PRIMARY KEY, AREA_ID STRING NOT NULL,
        KIND STRING NOT NULL, MESSAGE STRING NOT NULL, LONGITUDE FLOAT NOT NULL, LATITUDE FLOAT NOT NULL,
        VERIFICATION_STATE STRING NOT NULL, REPORTED_AT TIMESTAMP_TZ, RECEIVED_AT TIMESTAMP_TZ NOT NULL,
        IDEMPOTENCY_KEY STRING, PROVENANCE STRING)""")
    bootstrap.ensure_schema()
    assert _rows("nobody") == []
