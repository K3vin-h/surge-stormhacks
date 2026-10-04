"""Assistant chat, voice transcription, and TTS."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import Response

from ..errors import not_found, too_large, validation_error
from ..fixtures import areas as fx
from ..schemas.chat import (
    ChatRequest,
    TtsAssistantRequest,
    TtsInstructionRequest,
    VoiceResponse,
)
from ..services import answers, cache, elevenlabs, instructions

TtsRequest = Annotated[
    TtsInstructionRequest | TtsAssistantRequest, Body(discriminator="kind")
]

router = APIRouter(prefix="/api")

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MiB per contract
ALLOWED_AUDIO = {"audio/webm", "audio/mp4", "audio/wav", "audio/x-wav", "audio/mpeg"}


def _loc(lat: float | None, lng: float | None):
    return (lat, lng) if (lat is not None and lng is not None) else None


def _answer(area_id: str, question: str, location=None, language=None, device_id=None):
    # Grounded agent advice + middle-layer event extraction / auto-report.
    # Replies in the resident's own language; falls back to deterministic
    # English rendering + keywords when Gemini is down.
    return answers.agent_turn(area_id, question, location, language, device_id)


@router.post("/chat")
def chat(req: ChatRequest):
    if fx.get_area(req.area_id) is None:
        raise not_found(f"Unknown area '{req.area_id}'.")
    return _answer(req.area_id, req.question, _loc(req.latitude, req.longitude), req.language, req.device_id)


@router.post("/voice", response_model=VoiceResponse)
def voice(
    area_id: str = Form(...),
    audio: UploadFile = File(...),
    latitude: float | None = Form(None, ge=-90, le=90),
    longitude: float | None = Form(None, ge=-180, le=180),
    language: str | None = Form(None, max_length=35),
    device_id: str | None = Form(None, max_length=128),
) -> VoiceResponse:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise too_large("Audio exceeds the 5 MiB limit.")
    # MediaRecorder sends e.g. "audio/webm;codecs=opus": match the base type.
    base_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
    if base_type and base_type not in ALLOWED_AUDIO:
        raise validation_error(f"Unsupported audio type '{audio.content_type}'.")
    transcript = elevenlabs.transcribe(data, audio.content_type or "audio/webm")
    response = _answer(area_id, transcript or "", _loc(latitude, longitude), language, device_id)
    return VoiceResponse(transcript=transcript, response=response)


@router.post("/tts")
def tts(payload: TtsRequest):
    """Resolve text by ID server-side; never accept arbitrary text."""
    if isinstance(payload, TtsInstructionRequest):
        inst = instructions.get_by_id(payload.instruction_id)
        if inst is None:
            raise not_found("Unknown instruction_id.")
        text = inst.emergency_message
    else:
        text = cache.get_response_text(payload.response_id)
        if text is None:
            raise not_found("Unknown response_id.")

    audio = elevenlabs.synthesize(text)
    return Response(content=audio, media_type="audio/mpeg")
