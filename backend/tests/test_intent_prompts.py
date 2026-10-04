"""Replies adapt to what the resident is asking; off-topic gets a refusal."""

import json

import pytest

from app.services import answers, gemini


def _converse(monkeypatch, **fields):
    seen = {}
    payload = {
        "intent": "evacuation",
        "reply": "Go to the school.",
        "event_type": "none",
        "summary": "",
        "language": "en",
        **fields,
    }

    def fake(prompt, **kw):
        seen.update(prompt=prompt, **kw)
        return json.dumps(payload)

    monkeypatch.setattr(gemini, "_generate", fake)
    return gemini.converse("q", "ctx"), seen


def test_prompt_lists_every_intent_with_its_guidance(monkeypatch):
    _, seen = _converse(monkeypatch)
    for intent, guidance in gemini.INTENT_GUIDANCE.items():
        assert f"- {intent}: {guidance}" in seen["prompt"]


def test_panic_framing_is_not_forced_on_every_message(monkeypatch):
    _, seen = _converse(monkeypatch)
    assert "trapped" not in seen["system"]


@pytest.mark.parametrize("intent", [None, "banana", 7, []])
def test_unknown_intent_still_helps(monkeypatch, intent):
    out, _ = _converse(monkeypatch, intent=intent)
    assert out["intent"] == "general_safety"
    assert out["reply"] == "Go to the school."


def test_off_topic_keeps_short_translated_refusal_and_drops_report(monkeypatch):
    out, _ = _converse(
        monkeypatch,
        intent="off_topic",
        reply="Lo siento, no puedo ayudar con eso.",
        language="es",
        event_type="none",
        summary="x",
    )
    assert out == {
        "reply": "Lo siento, no puedo ayudar con eso.",
        "event_type": "none",
        "summary": "",
        "language": "es",
        "intent": "off_topic",
    }


@pytest.mark.parametrize(
    "reply", ["", "Paris.", "2+2 is 4.", "The capital of France is Paris. " * 10]
)
def test_off_topic_ignores_model_text_and_uses_fixed_refusal(monkeypatch, reply):
    out, _ = _converse(monkeypatch, intent="off_topic", reply=reply, language="fr-CA")
    assert out["reply"] == gemini.REFUSALS["fr"]
    assert out["language"] == "fr-CA"


def test_off_topic_unlisted_language_gets_english(monkeypatch):
    out, _ = _converse(monkeypatch, intent="off_topic", reply="Hej då", language="sv")
    assert (out["reply"], out["language"]) == (gemini.REFUSAL_EN, "en")


@pytest.mark.parametrize(
    "fields",
    [
        {"event_type": "rescue_needed", "summary": "trapped on roof"},
        {"event_type": "road_hazard"},
    ],
)
def test_off_topic_label_never_suppresses_model_reported_emergency(monkeypatch, fields):
    out, _ = _converse(monkeypatch, intent="off_topic", reply="Sorry, no.", **fields)
    assert out["intent"] == "emergency"
    assert out["event_type"] == fields["event_type"]
    assert out["reply"] == "Sorry, no."


def test_off_topic_label_never_refuses_keyword_distress(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        gemini,
        "_generate",
        lambda *a, **k: json.dumps(
            {"intent": "off_topic", "reply": "no", "language": "en"}
        ),
    )
    out = gemini.converse("what's the score, also I'm trapped on my roof", "ctx")
    assert out["intent"] == "emergency"


def test_normal_turn_is_remembered(monkeypatch):
    monkeypatch.setattr(answers, "build_context", lambda a: "ctx")
    monkeypatch.setattr(
        gemini,
        "converse",
        lambda *a, **k: {
            "reply": "Go to the school.",
            "event_type": "none",
            "summary": "",
            "language": "en",
            "intent": "evacuation",
        },
    )
    added = []
    monkeypatch.setattr(answers.memory, "add_turn", lambda *a: added.append(a))
    answers.agent_turn("sunsari", "where to go", None, None, "dev1")
    assert len(added) == 1


def test_off_topic_turn_files_no_report_and_is_not_remembered(monkeypatch):
    monkeypatch.setattr(answers, "build_context", lambda a: "ctx")
    monkeypatch.setattr(
        gemini,
        "converse",
        lambda *a, **k: {
            "reply": gemini.REFUSAL_EN,
            "event_type": "none",
            "summary": "",
            "language": "en",
            "intent": "off_topic",
        },
    )
    added = []
    monkeypatch.setattr(answers.memory, "add_turn", lambda *a: added.append(a))
    resp = answers.agent_turn("sunsari", "what's 2+2", (27.0, 85.0), None, "dev1")
    assert resp.text == gemini.REFUSAL_EN
    assert resp.report_filed is False
    assert added == []


def test_fallback_unsupported_text_still_points_to_authorities():
    text = answers._render_text("sunsari", "unsupported", object())
    assert answers.AUTHORITY_LINE in text
