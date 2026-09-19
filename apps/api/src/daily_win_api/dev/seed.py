from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import (
    DEMO_CHILD_ID,
    DEMO_HOUSEHOLD_ID,
    demo_baseline_id,
    demo_goal_id,
    skill_id_for_code,
)
from daily_win_api.dev.presets import HAYES_PROFILE
from daily_win_api.dev.profile import apply_synthetic_profile
from daily_win_api.domains.learning.models import (
    Skill,
    SkillPrerequisite,
    SkillStandardRef,
)
from daily_win_api.domains.learning.prerequisites import (
    PREREQUISITE_EDGES,
    assert_prerequisites_valid,
)
from daily_win_api.domains.learning.standards import SKILL_STANDARD_REFS
from daily_win_api.domains.learning.taxonomy import SKILL_DEFINITIONS

DEMO_HOUSEHOLD_NAME = "Demo Household"
HAYES_GOAL_CODES = HAYES_PROFILE.goal_codes


def seed_development_data(session: Session) -> None:
    """Idempotent development seed. Not production data and not authorization."""
    seed_skill_taxonomy(session)
    session.flush()
    seed_hayes_profile(
        session,
        household_id=DEMO_HOUSEHOLD_ID,
        child_id=DEMO_CHILD_ID,
        baseline_id=demo_baseline_id(),
        goal_id_for_code=demo_goal_id,
    )
    session.flush()


def seed_skill_taxonomy(session: Session) -> None:
    existing = {skill.code: skill for skill in session.scalars(select(Skill))}
    for definition in SKILL_DEFINITIONS:
        skill = existing.get(definition["code"])
        if skill is None:
            skill = Skill(id=skill_id_for_code(definition["code"]))
            session.add(skill)
        skill.code = definition["code"]
        skill.domain = definition["domain"]
        skill.display_name = definition["display_name"]
        skill.description = definition["description"]
        skill.state_mode = definition["state_mode"]
        skill.skill_kind = definition["skill_kind"]
        skill.strand = definition.get("strand")
        skill.parent_code = definition.get("parent_code")
        skill.grade_band_min = definition["grade_band_min"]
        skill.grade_band_max = definition["grade_band_max"]
        skill.measurable_outcome = definition.get("measurable_outcome")
        skill.progression_position = definition["progression_position"]
        skill.taxonomy_version = definition["taxonomy_version"]
        skill.active = True
    seed_prerequisites(session)
    seed_standard_refs(session)


def seed_prerequisites(session: Session) -> None:
    existing = {
        (row.skill_code, row.prerequisite_code)
        for row in session.scalars(select(SkillPrerequisite))
    }
    for source, dest in PREREQUISITE_EDGES:
        key = (dest, source)
        if key not in existing:
            session.add(SkillPrerequisite(skill_code=dest, prerequisite_code=source))
    assert_prerequisites_valid()


def seed_standard_refs(session: Session) -> None:
    existing = {
        (row.skill_code, row.standard_code, row.source, row.version)
        for row in session.scalars(select(SkillStandardRef))
    }
    for item in SKILL_STANDARD_REFS:
        key = (
            item["skill_code"],
            item["standard_code"],
            item["source"],
            item["version"],
        )
        if key not in existing:
            session.add(
                SkillStandardRef(
                    skill_code=item["skill_code"],
                    standard_code=item["standard_code"],
                    source=item["source"],
                    version=item["version"],
                )
            )


def seed_hayes_profile(
    session: Session,
    *,
    household_id,
    child_id,
    baseline_id,
    goal_id_for_code,
):
    """Idempotent Hayes baseline/goals. Does not rewrite historical Daily Wins."""
    return apply_synthetic_profile(
        session,
        household_id=household_id,
        child_id=child_id,
        preset=HAYES_PROFILE,
        baseline_id=baseline_id,
        goal_id_for_code=goal_id_for_code,
    )
