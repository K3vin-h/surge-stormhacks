"""Chat / voice / TTS request+response shapes."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import AreaId, PublicationFreshness


class ChatRequest(BaseModel):
    """Intentionally minimal: no system_prompt, language, or context fields.

    The backend owns the safety prompt and trusted instruction data.
    """

    area_id: AreaId
    question: str = Field(..., min_length=1, max_length=2000)
    # Optional phone location so the middle layer can geo-tag an auto-report.
    latitude: float | None = None
    longitude: float | None = None
    # Optional language hint (BCP-47) carried from an earlier detected turn.
    language: str | None = None
    # Browser device id (UUID from deviceId(), or its non-secure-context fallback):
    # a chat SOS moves the device's existing pin, and it keys conversation memory.
    device_id: str | None = Field(None, max_length=128)


class AssistantResponse(BaseModel):
    response_id: str
    area_id: AreaId
    text: str
    instruction_id: str | None = None
    instruction_published_at: datetime | None = None
    source: str  # published_instruction | no_instruction | fallback
    mode: str  # gemini_grounded | deterministic
    audio_available: bool
    freshness: PublicationFreshness
    # Detected/used language (BCP-47) so the client can keep later turns +
    # auto-briefings in the same language.
    language: str = "en"
    # Set when the middle layer auto-filed a government report from this turn.
    report_filed: bool = False
    report_id: str | None = None
    report_kind: str | None = None


class VoiceResponse(BaseModel):
    transcript: str
    response: AssistantResponse


class TtsInstructionRequest(BaseModel):
    kind: Literal["instruction"]
    instruction_id: str


class TtsAssistantRequest(BaseModel):
    kind: Literal["assistant_response"]
    response_id: str
