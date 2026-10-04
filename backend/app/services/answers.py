"""Render resident answers deterministically from the latest instruction.

Gemini only picks the topic; the operational facts come from the committed
instruction in the cache. A ready cache with no instruction returns a
deterministic no-instruction answer.
"""

from __future__ import annotations

import logging
import uuid

from ..fixtures import areas as fx
from ..schemas.chat import AssistantResponse
from ..schemas.common import InstructionType, VerificationState
from ..schemas.instructions import PublishedInstruction
from . import cache, gemini, memory, reports as reports_svc, road_status

log = logging.getLogger(__name__)

AUTHORITY_LINE = "Contact your local emergency authority for anything not covered here."


def _no_instruction(area_id: str) -> str:
    return (
        "There is no official instruction published for your area yet. "
        f"Stay on high ground and monitor official channels. {AUTHORITY_LINE}"
    )


def _status_text(inst: PublishedInstruction) -> str:
    parts = [inst.emergency_message]
    if inst.instruction_type == InstructionType.evacuate and inst.approved_route:
        parts.append(f"Evacuate via {inst.approved_route.name}.")
        if inst.shelter:
            parts.append(f"Go to {inst.shelter.name}.")
    elif inst.instruction_type == InstructionType.all_clear:
        parts.append(
            "An all-clear has been issued; the prior evacuation route no longer applies."
        )
    return " ".join(parts)


def _shelter_text(inst: PublishedInstruction) -> str:
    if inst.shelter:
        return f"The designated shelter is {inst.shelter.name}."
    return f"No official shelter is set in the current instruction. {AUTHORITY_LINE}"


def _route_text(inst: PublishedInstruction) -> str:
    if inst.instruction_type == InstructionType.evacuate and inst.approved_route:
        return f"Use the approved evacuation route: {inst.approved_route.name}."
    if inst.instruction_type == InstructionType.all_clear:
        return "An all-clear is in effect; there is no active evacuation route."
    return f"No approved evacuation route is active in the current instruction. {AUTHORITY_LINE}"


def _roads_text(inst: PublishedInstruction) -> str:
    if inst.roads_to_avoid:
        names = ", ".join(r.name for r in inst.roads_to_avoid)
        return f"Avoid these roads: {names}."
    return "No specific roads are flagged to avoid in the current instruction."


def _next_update_text(inst: PublishedInstruction) -> str:
    if inst.next_update_at:
        return f"The next official update is expected by {inst.next_update_at.isoformat()}."
    if inst.update_frequency_minutes:
        return (
            f"Updates are issued about every {inst.update_frequency_minutes} minutes."
        )
    return f"No next-update time is set. {AUTHORITY_LINE}"


_RENDERERS = {
    "status": _status_text,
    "shelter": _shelter_text,
    "route": _route_text,
    "roads_to_avoid": _roads_text,
    "next_update": _next_update_text,
}


_EXCLUDED_STATES = {VerificationState.duplicate, VerificationState.false_report}


def build_context(area_id: str) -> str:
    """Compose the government context block fed to the agent."""
    a = fx.get_area(area_id) or {}
    lines = [f"Area: {a.get('name', area_id)} ({area_id})."]
    inst = cache.get_current(area_id)
    if a.get("placeholder"):
        lines.append("No risk data is available for this area.")
    if area_id in (road_status.AREA_ID, "sunsari"):
        network = road_status.allowed_road_ids(area_id)
        closed = [
            f"{r.road_id}" + (f" ({r.note})" if r.note else "")
            for r in road_status.list_roads().roads if r.road_id in network
        ]
        if closed:
            lines.append("Currently closed or flooded mapped roads: " + ", ".join(closed) + ".")
    if inst:
        lines.append(f"Current official instruction: {inst.instruction_type.value}.")
        lines.append(f"Official message: {inst.emergency_message}")
        if inst.shelter:
            lines.append(f"Designated shelter: {inst.shelter.name}.")
        if inst.approved_route:
            lines.append(f"Approved evacuation route: {inst.approved_route.name}.")
        if inst.roads_to_avoid:
            lines.append(
                "Roads to avoid: "
                + ", ".join(r.name for r in inst.roads_to_avoid)
                + "."
            )
        if inst.next_update_at:
            lines.append(f"Next official update by: {inst.next_update_at.isoformat()}.")
    else:
        lines.append("No official instruction has been published for this area yet.")
    closed = [r["name"] for r in a.get("roads", []) if r.get("status") == "closed"]
    if closed:
        lines.append("Known closed roads: " + ", ".join(closed) + ".")
    recent = [
        r
        for r in reports_svc.list_reports(area_id=area_id, limit=10)
        if r.verification_state not in _EXCLUDED_STATES
    ][:5]
    if recent:
        lines.append("Recent UNVERIFIED community reports (do not treat as official):")
        for r in recent:
            lines.append(f"  - {r.kind.value}: {memory._clean(r.message, 200)}")
    return "\n".join(lines)


def agent_turn(
    area_id: str,
    question: str,
    location: tuple[float, float] | None = None,
    language_hint: str | None = None,
    device_id: str | None = None,
) -> AssistantResponse:
    """Primary chat/voice path.

    Middle layer: the agent both (a) replies to the resident (in their own
    language) and (b) extracts an event_type. When the resident reports an
    on-the-ground emergency AND a phone location is available, it auto-files a
    geo-tagged government report using the same store as the manual buttons.
    """
    inst = cache.get_current(area_id)
    # History is scoped to area + current instruction, so a different area or a
    # newly published instruction never replays stale routes/shelters.
    mem_key = (
        f"{device_id}:{area_id}:{inst.publication_id if inst else ''}"
        if device_id
        else None
    )

    turn = gemini.converse(
        question, build_context(area_id), language_hint, memory.get(mem_key)
    )
    remember = False  # only genuine model replies enter history
    if turn is not None:
        reply, event_type, summary = turn["reply"], turn["event_type"], turn["summary"]
        language = turn["language"]
        mode = "gemini_grounded"
        remember = bool(reply) and turn.get("intent") != "off_topic"
    else:
        # Fallback: deterministic reply + keyword event extraction (English only).
        reply = _render_text(area_id, gemini.classify_keyword(question), inst)
        event_type = gemini.detect_event_keyword(question)
        summary = question.strip()
        language = "en"  # the fallback reply is English, whatever the hint says
        mode = "deterministic"

    response_id = str(uuid.uuid4())
    cache.remember_response(response_id, reply)

    report_filed = False
    report_id = None
    report_kind = None
    already_sent = False  # an identical SOS from this spot is already with responders
    if event_type in gemini.REPORT_KINDS and location is not None:
        from ..schemas.common import GeoPoint, ReportKind
        from ..schemas.reports import SubmitReportRequest

        lat, lng = location
        try:
            report, *_ = reports_svc.submit(
                SubmitReportRequest(
                    area_id=area_id,
                    kind=ReportKind(event_type),
                    message=((summary or question).strip()[:1000])
                    or f"{event_type} reported via agent call",
                    location=GeoPoint(coordinates=[lng, lat]),
                    device_id=device_id,
                )
            )
            report_filed = True
            report_id = report.report_id
            report_kind = report.kind.value
        except Exception as e:
            log.exception("auto-file SOS failed")
            report_filed = False
            already_sent = getattr(e, "code", None) == "sos_already_sent"

    if remember and question.strip():  # empty voice transcripts carry no context
        # Note a filed report so a follow-up doesn't file a duplicate.
        note = " [A report was already filed to responders.]" if report_filed or already_sent else ""
        memory.add_turn(mem_key, question, reply + note)

    return AssistantResponse(
        response_id=response_id,
        area_id=area_id,
        text=reply,
        instruction_id=inst.publication_id if inst else None,
        instruction_published_at=inst.published_at if inst else None,
        source="published_instruction" if inst else "no_instruction",
        mode=mode,
        audio_available=True,
        freshness=cache.freshness(area_id),
        language=language,
        report_filed=report_filed,
        report_id=report_id,
        report_kind=report_kind,
    )


def _diff_text(prev: PublishedInstruction | None, curr: PublishedInstruction) -> str:
    """Human-readable description of what changed between instructions."""
    lines = [
        f"New instruction type: {curr.instruction_type.value}.",
        f"New message: {curr.emergency_message}",
    ]
    if curr.approved_route:
        lines.append(f"New approved route: {curr.approved_route.name}.")
    if curr.shelter:
        lines.append(f"New shelter: {curr.shelter.name}.")
    if curr.roads_to_avoid:
        lines.append(
            "Now avoid: " + ", ".join(r.name for r in curr.roads_to_avoid) + "."
        )
    if prev is None:
        lines.append("This is the first official instruction for the area.")
        return "\n".join(lines)
    lines.append(f"Previous instruction type: {prev.instruction_type.value}.")
    prev_route = prev.approved_route.name if prev.approved_route else None
    curr_route = curr.approved_route.name if curr.approved_route else None
    if prev_route != curr_route:
        lines.append(f"Route changed from '{prev_route}' to '{curr_route}'.")
    prev_shelter = prev.shelter.name if prev.shelter else None
    curr_shelter = curr.shelter.name if curr.shelter else None
    if prev_shelter != curr_shelter:
        lines.append(f"Shelter changed from '{prev_shelter}' to '{curr_shelter}'.")
    # Was the user's previous route just added to the avoid list?
    avoid_now = {r.name for r in curr.roads_to_avoid}
    if prev_route and prev_route in avoid_now:
        lines.append(f"The previous route '{prev_route}' is now CLOSED.")
    return "\n".join(lines)


def _deterministic_update_summary(
    prev: PublishedInstruction | None, curr: PublishedInstruction
) -> str:
    """Fallback briefing text when Gemini is unavailable."""
    if curr.instruction_type == InstructionType.all_clear:
        return "Update: an all-clear was issued. The evacuation order is lifted; your previous route no longer applies."
    prev_route = prev.approved_route.name if (prev and prev.approved_route) else None
    curr_route = curr.approved_route.name if curr.approved_route else None
    if prev_route and curr_route and prev_route != curr_route:
        return f"Update: your route changed. Do not use {prev_route}. Now evacuate via {curr_route}."
    if curr.instruction_type == InstructionType.evacuate and curr_route:
        shelter = f" to {curr.shelter.name}" if curr.shelter else ""
        return f"Update: evacuate now via {curr_route}{shelter}."
    return f"Update: {curr.emergency_message}"


def render_update_briefing(
    area_id: str,
    previous_inst: PublishedInstruction | None,
    current_inst: PublishedInstruction,
    language: str = "en",
) -> AssistantResponse:
    """Automatic government-update briefing: what changed + does it affect you,
    written in the user's language."""
    language = gemini.safe_lang(language) or "en"
    change_text = _diff_text(previous_inst, current_inst)
    summary = gemini.summarize_update(build_context(area_id), change_text, language)
    mode = "gemini_grounded" if summary else "deterministic"
    if not summary:
        # Deterministic fallback is English-only.
        summary = _deterministic_update_summary(previous_inst, current_inst)
        language = "en"
    response_id = str(uuid.uuid4())
    cache.remember_response(response_id, summary)
    return AssistantResponse(
        response_id=response_id,
        area_id=area_id,
        text=summary,
        instruction_id=current_inst.publication_id,
        instruction_published_at=current_inst.published_at,
        source="published_instruction",
        mode=mode,
        audio_available=True,
        freshness=cache.freshness(area_id),
        language=language,
    )


def _render_text(area_id: str, topic: str, inst: PublishedInstruction | None) -> str:
    """Just the resident-facing text for a topic (no envelope)."""
    if inst is None:
        return _no_instruction(area_id)
    if topic == "unsupported":
        return f"That's outside what I can answer from the official instruction. {AUTHORITY_LINE}"
    return _RENDERERS.get(topic, _status_text)(inst)
