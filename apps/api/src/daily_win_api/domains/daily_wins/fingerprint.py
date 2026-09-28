"""Deterministic READY-Win validity. Hashes planner inputs, not public IDs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from daily_win_api.ai.prompts.current import PROMPT_VERSION
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.learning.models import ChildGoal, LearningEvent, Skill
from daily_win_api.domains.learning.placement import PLACEMENT_POLICY_CURRENT
from daily_win_api.domains.learning.planner import INSTRUCTION_POLICY_CURRENT
from daily_win_api.domains.learning.scheduler import INSTRUCTION_SCHEDULER_V1
from daily_win_api.domains.learning.taxonomy import TAXONOMY_VERSION

FINGERPRINT_VERSION = "plan_fingerprint_v1"


def compute_plan_fingerprint(session: Session, child: Child) -> str:
    baseline = session.scalars(
        select(ChildBaseline)
        .where(
            ChildBaseline.child_id == child.id,
            ChildBaseline.household_id == child.household_id,
        )
        .order_by(ChildBaseline.recorded_at.desc())
        .limit(1)
    ).first()
    goals = session.execute(
        select(ChildGoal.priority, Skill.code)
        .join(Skill, Skill.id == ChildGoal.skill_id)
        .where(
            ChildGoal.child_id == child.id,
            ChildGoal.household_id == child.household_id,
            ChildGoal.active.is_(True),
        )
        .order_by(ChildGoal.priority.asc(), Skill.code.asc())
    ).all()
    event_count = session.scalar(
        select(func.count())
        .select_from(LearningEvent)
        .where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
        )
    )
    latest_event_at = session.scalar(
        select(func.max(LearningEvent.occurred_at)).where(
            LearningEvent.child_id == child.id,
            LearningEvent.household_id == child.household_id,
        )
    )
    payload = {
        "v": FINGERPRINT_VERSION,
        "age": None if baseline is None else baseline.age_years,
        "grade": None if baseline is None else baseline.grade,
        "interests": [] if baseline is None else list(baseline.interests),
        "motivators": [] if baseline is None else list(baseline.motivators),
        "strengths": [] if baseline is None else list(baseline.strengths),
        "difficulties": (
            [] if baseline is None else list(baseline.current_difficulties)
        ),
        "minutes": (
            None if baseline is None else baseline.preferred_activity_minutes
        ),
        "response_to_difficulty": (
            None if baseline is None else baseline.response_to_difficulty
        ),
        "goals": [[int(priority), code] for priority, code in goals],
        "events": int(event_count or 0),
        "latest_event": _stamp(latest_event_at),
        "curriculum": TAXONOMY_VERSION,
        "scheduler": INSTRUCTION_SCHEDULER_V1,
        "placement": PLACEMENT_POLICY_CURRENT,
        "policy": INSTRUCTION_POLICY_CURRENT,
        "prompt": PROMPT_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def fingerprints_match(stored: str | None, current: str) -> bool:
    if not stored:
        return True
    return stored == current


def _stamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
