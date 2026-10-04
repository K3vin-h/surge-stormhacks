"""Assistant chat, voice transcription, and TTS."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from ..errors import not_found, too_large, validation_error
from ..fixtures import areas as fx
from ..schemas.chat import ChatRequest, VoiceResponse
from ..services import answers, cache, elevenlabs, gemini, instructions

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
    return _answer(req.area_id, req.question, _loc(req.latitude, req.longitude), req.language,
                   req.device_id)


@router.post("/voice", response_model=VoiceResponse)
async def voice(
    area_id: str = Form(...),
    audio: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    language: str | None = Form(None),
    device_id: str | None = Form(None, max_length=64),
) -> VoiceResponse:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")
    data = await audio.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise too_large("Audio exceeds the 5 MiB limit.")
    if audio.content_type and audio.content_type not in ALLOWED_AUDIO:
        raise validation_error(f"Unsupported audio type '{audio.content_type}'.")
    transcript = elevenlabs.transcribe(data, audio.content_type or "audio/webm")
    response = _answer(area_id, transcript or "", _loc(latitude, longitude), language,
                       device_id)
    return VoiceResponse(transcript=transcript, response=response)


@router.post("/tts")
async def tts(payload: dict):
    """Resolve text by ID server-side; never accept arbitrary text."""
    kind = payload.get("kind")
    if kind == "instruction":
        pub_id = payload.get("instruction_id")
        inst = instructions.get_by_id(pub_id) if pub_id else None
        if inst is None:
            raise not_found("Unknown instruction_id.")
        text = inst.emergency_message
    elif kind == "assistant_response":
        resp_id = payload.get("response_id")
        text = cache.get_response_text(resp_id) if resp_id else None
        if text is None:
            raise not_found("Unknown response_id.")
    else:
        raise validation_error("kind must be 'instruction' or 'assistant_response'.")

    audio = elevenlabs.synthesize(text)
    return Response(content=audio, media_type="audio/mpeg")
