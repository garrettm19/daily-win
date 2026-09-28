"""v5 generated-payload field audit. Classification only. No schema cuts."""

from __future__ import annotations

from typing import Any

from daily_win_api.ai.providers.fake import valid_daily_win_draft
from daily_win_api.ai.schemas import DailyWinDraft

REQUIRED_UI = "REQUIRED FOR UI"
REQUIRED_VALIDATION = "REQUIRED FOR VALIDATION"
REQUIRED_HISTORY = "REQUIRED FOR HISTORY"
REDUNDANT = "REDUNDANT / CANDIDATE FOR REMOVAL"

FIELD_AUDIT: tuple[dict[str, str], ...] = (
    {
        "field": "title",
        "class": REQUIRED_UI,
        "note": "Home and Daily Win title.",
    },
    {
        "field": "objective",
        "class": REQUIRED_UI,
        "note": "Shown under the title.",
    },
    {
        "field": "duration_minutes",
        "class": REQUIRED_UI,
        "note": "Home and Daily Win duration.",
    },
    {
        "field": "primary_skill_code",
        "class": REQUIRED_VALIDATION,
        "note": "Must match the InstructionPlan. Display uses skill catalog name.",
    },
    {
        "field": "supporting_skill_codes",
        "class": REQUIRED_VALIDATION,
        "note": "Contract/plan alignment. Not shown as its own Home field.",
    },
    {
        "field": "personalization_summary",
        "class": REQUIRED_UI,
        "note": "Why this Win intro.",
    },
    {
        "field": "materials",
        "class": REQUIRED_UI,
        "note": "Before you start.",
    },
    {
        "field": "parent_briefing.purpose",
        "class": REQUIRED_UI,
        "note": "Why this Win.",
    },
    {
        "field": "parent_briefing.how_to_coach",
        "class": REQUIRED_UI,
        "note": "Overlaps CoachProtocol card; still shown.",
    },
    {
        "field": "parent_briefing.watch_for",
        "class": REQUIRED_UI,
        "note": "Parent observation cue.",
    },
    {
        "field": "parent_briefing.avoid",
        "class": REQUIRED_UI,
        "note": "Anti-rescue briefing.",
    },
    {
        "field": "segments.LEARN",
        "class": REQUIRED_UI,
        "note": "Activity body.",
    },
    {
        "field": "segments.DO",
        "class": REQUIRED_UI,
        "note": "Activity body.",
    },
    {
        "field": "segments.GROW",
        "class": REQUIRED_UI,
        "note": "Activity body.",
    },
    {
        "field": "segments.*.parent_role",
        "class": REQUIRED_UI,
        "note": "Shown per segment; overlaps briefing and coach card.",
    },
    {
        "field": "adaptations.if_too_easy",
        "class": REQUIRED_UI,
        "note": "In-activity adjustment.",
    },
    {
        "field": "adaptations.if_too_hard",
        "class": REQUIRED_UI,
        "note": "In-activity adjustment.",
    },
    {
        "field": "success_checks",
        "class": REDUNDANT,
        "note": (
            "Client shows planner-derived assessment, not these strings. "
            "Still schema-required. Candidate after fixture coverage."
        ),
    },
    {
        "field": "observation_focus",
        "class": REQUIRED_VALIDATION,
        "note": "Parent-burden and schema. Not rendered on Daily Win.",
    },
    {
        "field": "safety_flags",
        "class": REQUIRED_VALIDATION,
        "note": (
            "Application safety scans activity text, not this list. "
            "Stored; unused in mobile UI."
        ),
    },
    {
        "field": "adaptation_summary",
        "class": REDUNDANT,
        "note": (
            "Fallback for what_changed_today when planner copy is empty. "
            "Often duplicates planner text."
        ),
    },
)


MOBILE_UNUSED_OR_FALLBACK: tuple[dict[str, str], ...] = (
    {
        "field": "content.success_checks",
        "status": "stored, not displayed",
        "note": "Assessment card uses planner probe fields.",
    },
    {
        "field": "content.observation_focus",
        "status": "stored, not displayed",
        "note": "Reflection uses structured chips, not this string.",
    },
    {
        "field": "content.safety_flags",
        "status": "stored, not displayed",
        "note": "Safety is application-owned.",
    },
    {
        "field": "content.supporting_skill_codes",
        "status": "stored, not displayed",
        "note": "Primary skill display name is shown instead.",
    },
    {
        "field": "content.adaptation_summary",
        "status": "fallback only",
        "note": "changedTodayCopy prefers planner what_changed_today.",
    },
    {
        "field": "one_thing_to_improve",
        "status": "stored, not displayed on Daily Win",
        "note": "CoachProtocol field. Not rendered in v0.4.2 client.",
    },
    {
        "field": "teach_the_coach",
        "status": "stored, unused in UI",
        "note": "Protocol flag only.",
    },
    {
        "field": "coach_cues after LEARN",
        "status": "partially used",
        "note": "Daily Win shows at most two LEARN cues.",
    },
)


def char_breakdown(draft: DailyWinDraft) -> dict[str, int]:
    briefing = draft.parent_briefing
    learn, do, grow = draft.segments
    buckets = {
        "title_objective": len(draft.title) + len(draft.objective),
        "parent_briefing": (
            len(briefing.purpose)
            + len(briefing.how_to_coach)
            + len(briefing.watch_for)
            + len(briefing.avoid)
        ),
        "learn": _segment_chars(learn),
        "do": _segment_chars(do),
        "grow": _segment_chars(grow),
        "assessment_like": sum(len(item) for item in draft.success_checks)
        + len(draft.observation_focus),
        "adaptations": len(draft.adaptations.if_too_easy)
        + len(draft.adaptations.if_too_hard),
        "safety": sum(len(item) for item in draft.safety_flags),
        "other": len(draft.personalization_summary)
        + len(draft.primary_skill_code)
        + sum(len(item) for item in draft.supporting_skill_codes)
        + len(draft.adaptation_summary or ""),
    }
    buckets["total_chars"] = sum(
        value for key, value in buckets.items() if key != "total_chars"
    )
    return buckets


def audit_payload(draft: DailyWinDraft | None = None) -> dict[str, Any]:
    sample = draft or valid_daily_win_draft()
    chars = char_breakdown(sample)
    total = max(chars["total_chars"], 1)
    shares = {
        key: round(value / total, 4)
        for key, value in chars.items()
        if key != "total_chars"
    }
    return {
        "prompt_version": "daily_win_generator_v5",
        "do_not_cut_yet": True,
        "quality_blind_cutting_forbidden": True,
        "fields": [dict(item) for item in FIELD_AUDIT],
        "mobile_unused": [dict(item) for item in MOBILE_UNUSED_OR_FALLBACK],
        "sample_char_breakdown": chars,
        "sample_char_share": shares,
        "repeated_information": [
            "parent_briefing.how_to_coach overlaps CoachProtocol coach_card",
            "segment parent_role repeats wait/rescue guidance",
            "success_checks overlap planner assessment probe",
            "adaptation_summary can duplicate what_changed_today",
        ],
        "note": (
            "Future output reduction needs fixture coverage. "
            "Do not shorten every field to chase Terra latency."
        ),
    }


def _segment_chars(segment) -> int:
    return (
        len(segment.title)
        + sum(len(step) for step in segment.steps)
        + len(segment.parent_role)
    )
