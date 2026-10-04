"""Centralized configuration loaded from the repo-root .env.

Secrets (Gemini, ElevenLabs, Snowflake key) never leave the backend.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> repo root is two parents up from this file's dir.
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


def _clean(value: str | None) -> str | None:
    # The .env in this repo uses "KEY = value" with surrounding spaces.
    return value.strip() if value is not None else None


class Settings:
    # --- Providers ---
    gemini_api_key: str | None = _clean(os.getenv("GEMINI_API_KEY"))
    gemini_model: str = _clean(os.getenv("GEMINI_MODEL")) or "gemini-2.5-flash"

    elevenlabs_api_key: str | None = _clean(os.getenv("ELEVENLABS_API_KEY"))
    elevenlabs_tts_voice_id: str = (
        _clean(os.getenv("ELEVENLABS_VOICE_ID")) or "JBFqnCBsd6RMkjVDRZzb"
    )
    elevenlabs_stt_model: str = (
        _clean(os.getenv("ELEVENLABS_STT_MODEL")) or "scribe_v1"
    )

    # --- Snowflake ---
    sf_account: str | None = _clean(os.getenv("SNOWFLAKE_ACCOUNT"))
    sf_user: str | None = _clean(os.getenv("SNOWFLAKE_USER"))
    sf_private_key_path: str | None = _clean(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"))
    sf_warehouse: str | None = _clean(os.getenv("SNOWFLAKE_WAREHOUSE"))
    sf_database: str | None = _clean(os.getenv("SNOWFLAKE_DATABASE"))
    sf_schema: str = _clean(os.getenv("SNOWFLAKE_SCHEMA")) or "PUBLIC"
    sf_role: str | None = _clean(os.getenv("SNOWFLAKE_ROLE"))

    # Private key path is relative to repo root in .env.
    @property
    def sf_private_key_abs(self) -> Path | None:
        if not self.sf_private_key_path:
            return None
        p = Path(self.sf_private_key_path)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def gemini_enabled(self) -> bool:
        # A real AI Studio key starts with "AIza". Anything else (e.g. an
        # OAuth "AQ." token) is treated as unavailable so chat falls back
        # to the deterministic topic classifier instead of crashing.
        return bool(self.gemini_api_key and self.gemini_api_key.startswith("AIza"))

    @property
    def elevenlabs_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
