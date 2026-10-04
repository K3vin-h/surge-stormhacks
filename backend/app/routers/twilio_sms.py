"""Twilio SMS fallback — talk to the relief agent with no app / no data.

Twilio posts inbound texts here (form-encoded) and we reply with TwiML. No
Twilio credentials are needed server-side for this inbound flow: Twilio calls
us, we answer. The phone number doubles as the conversation-memory device_id,
so an SMS thread remembers context just like the web app.

Setup (Twilio console): point the number's "A MESSAGE COMES IN" webhook at
    POST https://<your-public-url>/api/twilio/sms
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Form
from fastapi.responses import Response

from ..fixtures import areas as fx
from ..schemas.common import AREA_IDS
from ..services import answers

router = APIRouter(prefix="/api/twilio")

# phone number -> chosen area_id (in-memory; resets on restart — fine for demo).
_sessions: dict[str, str] = {}

_RESET_WORDS = {"area", "menu", "change", "reset", "restart", "hi", "hello", "start"}


def _area_name(area_id: str) -> str:
    a = fx.get_area(area_id) or {}
    return a.get("name", area_id)


def _menu() -> str:
    lines = ["Reply with your district number:"]
    for i, aid in enumerate(AREA_IDS, 1):
        lines.append(f"{i}) {_area_name(aid)}")
    return "\n".join(lines)


def _parse_area(text: str) -> str | None:
    t = text.strip().lower()
    # by number
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(AREA_IDS):
            return AREA_IDS[idx]
    # by name / substring
    for aid in AREA_IDS:
        if t == aid or t in _area_name(aid).lower():
            return aid
    return None


def _reply_for(from_number: str, body: str) -> str:
    text = (body or "").strip()
    if not text or text.lower() in _RESET_WORDS:
        _sessions.pop(from_number, None)
        return "SURGE flood assistant.\n" + _menu()

    area = _sessions.get(from_number)
    if not area:
        picked = _parse_area(text)
        if not picked:
            return "Sorry, I didn't catch that district.\n" + _menu()
        _sessions[from_number] = picked
        return (
            f"You're set to {_area_name(picked)}. Text your situation or a "
            "question (e.g. 'where do I go?'). Text AREA to switch districts."
        )

    # Area known -> run the same grounded agent. The phone number is the
    # device_id, so the SMS thread keeps conversation memory. No GPS over SMS,
    # so location is None (no auto-pin yet — v2 can ask for a landmark).
    resp = answers.agent_turn(area, text, None, None, from_number)
    return resp.text


def _twiml(message: str) -> Response:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(message)}</Message></Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/sms")
def sms(From: str = Form(""), Body: str = Form("")) -> Response:
    return _twiml(_reply_for(From or "unknown", Body))


# ---------------------------------------------------------------------------
# Voice IVR — call the Twilio number and talk to the agent live.
# Setup: point the number's "A CALL COMES IN" webhook at
#     POST https://<your-public-url>/api/twilio/voice
# Flow: /voice (pick district by keypad) -> /voice/area -> /voice/turn (loop:
# Twilio speech-to-texts the caller, agent_turn replies, we <Say> it and listen
# again). Twilio's own STT/TTS do the real-time audio, so it's naturally live.
# ---------------------------------------------------------------------------

VOICE = "Polly.Joanna"  # Twilio's Amazon Polly voice


def _say(text: str) -> str:
    return f'<Say voice="{VOICE}">{escape(text)}</Say>'


def _doc(inner: str) -> Response:
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response>' + inner + "</Response>"
    return Response(content=xml, media_type="application/xml")


def _ask_speech(prompt: str, action: str) -> str:
    return (
        f'<Gather input="speech" speechTimeout="auto" action="{action}" method="POST">'
        + _say(prompt)
        + "</Gather>"
        + _say("I didn't hear anything. Call back any time if you still need help. Goodbye.")
    )


@router.post("/voice")
def voice_entry(From: str = Form("")) -> Response:
    menu = " ".join(f"Press {i} for {_area_name(aid)}." for i, aid in enumerate(AREA_IDS, 1))
    inner = (
        '<Gather input="dtmf" numDigits="1" action="/api/twilio/voice/area" method="POST">'
        + _say("Welcome to SURGE flood relief. " + menu)
        + "</Gather>"
        + _say("No selection received. Goodbye.")
    )
    return _doc(inner)


@router.post("/voice/area")
def voice_area(From: str = Form(""), Digits: str = Form("")) -> Response:
    area = None
    if Digits.isdigit():
        idx = int(Digits) - 1
        if 0 <= idx < len(AREA_IDS):
            area = AREA_IDS[idx]
    if not area:
        return _doc(_say("Sorry, I didn't get that.")
                    + '<Redirect method="POST">/api/twilio/voice</Redirect>')
    _sessions[From or "unknown"] = area
    return _doc(_ask_speech(
        f"You're connected for {_area_name(area)}. Tell me your situation or ask a question.",
        "/api/twilio/voice/turn",
    ))


@router.post("/voice/turn")
def voice_turn(From: str = Form(""), SpeechResult: str = Form("")) -> Response:
    key = From or "unknown"
    area = _sessions.get(key)
    if not area:
        return _doc('<Redirect method="POST">/api/twilio/voice</Redirect>')
    said = (SpeechResult or "").strip()
    if not said:
        return _doc(_ask_speech("I didn't catch that. Please tell me what's happening.",
                                "/api/twilio/voice/turn"))
    # Phone number is the device_id -> the call keeps conversation memory.
    resp = answers.agent_turn(area, said, None, None, key)
    return _doc(_say(resp.text) + _ask_speech("Is there anything else?", "/api/twilio/voice/turn"))
