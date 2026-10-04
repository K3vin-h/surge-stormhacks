"""ElevenLabs speech-to-text and text-to-speech.

STT uses the Scribe model; TTS returns audio/mpeg. The provider key stays on
the backend. If the key is missing these raise a 503 so the frontend can show
an explicit failure (it keeps the typed-chat path either way).
"""
from __future__ import annotations

import httpx

from ..config import get_settings
from ..errors import unavailable

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def transcribe(audio_bytes: bytes, content_type: str) -> str:
    settings = get_settings()
    if not settings.elevenlabs_enabled:
        raise unavailable("Transcription is unavailable (no ElevenLabs key).")
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    files = {"file": ("audio", audio_bytes, content_type or "application/octet-stream")}
    data = {"model_id": settings.elevenlabs_stt_model}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(STT_URL, headers=headers, data=data, files=files)
            resp.raise_for_status()
            return resp.json().get("text", "").strip()
    except httpx.HTTPError as e:
        raise unavailable(f"Transcription failed: {e}")


def synthesize(text: str) -> bytes:
    settings = get_settings()
    if not settings.elevenlabs_enabled:
        raise unavailable("Speech synthesis is unavailable (no ElevenLabs key).")
    url = TTS_URL.format(voice_id=settings.elevenlabs_tts_voice_id)
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as e:
        raise unavailable(f"Speech synthesis failed: {e}")
