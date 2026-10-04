"""Thin Snowflake access layer with key-pair auth.

A single lazily-created connection is reused across requests and
re-established if it drops. JSON columns are stored as TEXT and
(de)serialized in Python to avoid PARSE_JSON binding friction.

When Snowflake is not configured (no account or private key), the same
interface is served by a local SQLite file so the app runs for local dev.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime
from typing import Any, Sequence

import snowflake.connector
from cryptography.hazmat.primitives import serialization

from ..config import REPO_ROOT, get_settings

log = logging.getLogger("surge.db")

_lock = threading.Lock()
_conn: snowflake.connector.SnowflakeConnection | None = None

LOCAL_DB_PATH = REPO_ROOT / "backend" / "local.db"
_local: sqlite3.Connection | None = None
sqlite3.register_adapter(datetime, lambda d: d.isoformat())


def snowflake_configured() -> bool:
    s = get_settings()
    key = s.sf_private_key_abs
    return bool(s.sf_account and s.sf_user and key and key.exists())


def _local_conn() -> sqlite3.Connection:
    global _local
    if _local is None:
        log.warning("Snowflake not configured; using local SQLite store at %s", LOCAL_DB_PATH)
        _local = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
        _local.row_factory = sqlite3.Row
    return _local


def _local_sql(sql: str) -> str:
    return sql.replace("%s", "?")


def _load_private_key_der() -> bytes:
    settings = get_settings()
    path = settings.sf_private_key_abs
    if path is None or not path.exists():
        raise RuntimeError(f"Snowflake private key not found at {path}")
    with path.open("rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _connect() -> snowflake.connector.SnowflakeConnection:
    s = get_settings()
    return snowflake.connector.connect(
        account=s.sf_account,
        user=s.sf_user,
        private_key=_load_private_key_der(),
        warehouse=s.sf_warehouse,
        database=s.sf_database,
        schema=s.sf_schema,
        role=s.sf_role,
        client_session_keep_alive=True,
    )


def get_connection() -> snowflake.connector.SnowflakeConnection:
    global _conn
    with _lock:
        if _conn is None or _conn.is_closed():
            _conn = _connect()
        return _conn


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    if not snowflake_configured():
        with _lock:
            conn = _local_conn()
            conn.execute(_local_sql(sql), list(params or []))
            conn.commit()
        return
    conn = get_connection()
    with _lock:
        cur = conn.cursor()
        try:
            cur.execute(sql, params or [])
        finally:
            cur.close()


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    if not snowflake_configured():
        with _lock:
            rows = _local_conn().execute(_local_sql(sql), list(params or [])).fetchall()
        return [dict(r) for r in rows]
    conn = get_connection()
    with _lock:
        cur = conn.cursor(snowflake.connector.DictCursor)
        try:
            cur.execute(sql, params or [])
            return list(cur.fetchall())
        finally:
            cur.close()


def query_one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def ping() -> bool:
    try:
        rows = query("SELECT 1 AS ONE")
        return bool(rows and rows[0].get("ONE") == 1)
    except Exception:
        return False
