"""Thin Snowflake access layer with key-pair auth.

A single lazily-created connection is reused across requests and
re-established if it drops. JSON columns are stored as TEXT and
(de)serialized in Python to avoid PARSE_JSON binding friction.
"""
from __future__ import annotations

import threading
from typing import Any, Sequence

import snowflake.connector
from cryptography.hazmat.primitives import serialization

from ..config import get_settings

_lock = threading.Lock()
_conn: snowflake.connector.SnowflakeConnection | None = None


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
    conn = get_connection()
    with _lock:
        cur = conn.cursor()
        try:
            cur.execute(sql, params or [])
        finally:
            cur.close()


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
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
