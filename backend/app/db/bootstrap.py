"""Create the durable tables if they do not exist. Idempotent."""
from __future__ import annotations

from . import snowflake_client as sf

DDL = [
    """
    CREATE TABLE IF NOT EXISTS INSTRUCTIONS (
        PUBLICATION_ID            STRING NOT NULL PRIMARY KEY,
        AREA_ID                   STRING NOT NULL,
        INSTRUCTION_TYPE          STRING NOT NULL,
        SEVERITY                  STRING NOT NULL,
        EMERGENCY_MESSAGE         STRING NOT NULL,
        SHELTER_ID                STRING,
        SHELTER_JSON              STRING,
        APPROVED_ROUTE_ID         STRING,
        APPROVED_ROUTE_JSON       STRING,
        ROADS_TO_AVOID_JSON       STRING,
        CANCELS_INSTRUCTION_ID    STRING,
        UPDATE_FREQUENCY_MINUTES  NUMBER,
        NEXT_UPDATE_AT            TIMESTAMP_TZ,
        PUBLISHED_AT              TIMESTAMP_TZ NOT NULL,
        REQUEST_FINGERPRINT       STRING
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS REPORTS (
        REPORT_ID          STRING NOT NULL PRIMARY KEY,
        AREA_ID            STRING NOT NULL,
        KIND               STRING NOT NULL,
        MESSAGE            STRING NOT NULL,
        LONGITUDE          FLOAT NOT NULL,
        LATITUDE           FLOAT NOT NULL,
        VERIFICATION_STATE STRING NOT NULL,
        REPORTED_AT        TIMESTAMP_TZ,
        RECEIVED_AT        TIMESTAMP_TZ NOT NULL,
        IDEMPOTENCY_KEY    STRING,
        PROVENANCE         STRING,
        DEVICE_ID          STRING
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS REPORT_REQUEST_KEYS (
        AREA_ID         STRING NOT NULL,
        IDEMPOTENCY_KEY STRING NOT NULL,
        REPORT_ID       STRING NOT NULL,
        PRIMARY KEY (AREA_ID, IDEMPOTENCY_KEY)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS EVENTS (
        EVENT_ID    STRING NOT NULL PRIMARY KEY,
        KIND        STRING NOT NULL,
        AREA_ID     STRING,
        SUMMARY     STRING NOT NULL,
        CREATED_AT  TIMESTAMP_TZ NOT NULL
    )
    """,
]


def ensure_schema() -> None:
    for stmt in DDL:
        sf.execute(stmt)
    # Upgrade tables created before DEVICE_ID existed. SQLite reports
    # "duplicate column name", Snowflake "already exists"; anything else is real.
    try:
        sf.execute("ALTER TABLE REPORTS ADD COLUMN DEVICE_ID STRING")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate column" not in msg and "already exists" not in msg:
            raise
