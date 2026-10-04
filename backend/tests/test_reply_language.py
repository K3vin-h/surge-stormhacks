"""converse() must follow the resident's current language, not a stale hint."""

from app.services import gemini


def _converse(monkeypatch, hint):
    seen = {}

    def fake(prompt, **_):
        seen["prompt"] = prompt
        return '{"reply": "ok", "event_type": "none", "summary": "", "language": "es"}'

    monkeypatch.setattr(gemini, "_generate", fake)
    out = gemini.converse("¿Dónde está el refugio?", "ctx", hint)
    return seen["prompt"], out


def test_stale_hint_does_not_force_reply_language(monkeypatch):
    prompt, out = _converse(monkeypatch, "en")
    assert "CURRENT message" in prompt
    assert "Write 'reply' in that language" not in prompt
    assert "use 'en'" in prompt  # tie-breaker only
    assert out["language"] == "es"


def test_detects_language_without_hint(monkeypatch):
    prompt, _ = _converse(monkeypatch, None)
    assert "CURRENT message" in prompt
    assert "use '" not in prompt
