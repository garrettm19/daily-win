from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from daily_win_api.core.demo import skill_id_for_code
from daily_win_api.dev.presets import (
    ALLOWED_DURATIONS,
    ALLOWED_GRADES,
    ALLOWED_ONBOARDING_GOAL_CODES,
    ALLOWED_RESPONSES,
    HAYES_PROFILE,
    MAX_DIFFICULTIES,
    MAX_GOALS,
    MAX_INTERESTS,
    MAX_LABEL_LENGTH,
    MAX_MOTIVATORS,
    MAX_STRENGTHS,
    MIN_GOALS,
    SyntheticProfile,
)
from daily_win_api.dev.sessions import (
    DemoTenant,
    session_baseline_id,
    session_child_id,
    session_goal_id,
)
from daily_win_api.domains.children.models import Child, ChildBaseline
from daily_win_api.domains.children.queries import load_demo_child_profile
from daily_win_api.domains.children.schemas import DemoChildProfileRead
from daily_win_api.domains.households.models import Household
from daily_win_api.domains.learning.models import ChildGoal, Skill

PROFILE_SOURCE_HAYES = "hayes"
PROFILE_SOURCE_CUSTOM = "custom"
ITEM_MAX_LEN = MAX_LABEL_LENGTH


class ProfileSetupError(Exception):
    def __init__(self, code: str, http_status: int, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.message = message


class DemoProfileWrite(BaseModel):
    """Custom synthetic profile. Extra fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    nickname: str = Field(min_length=1, max_length=30)
    age_years: int = Field(ge=5, le=9)
    grade: str
    interests: list[str] = Field(min_length=1, max_length=MAX_INTERESTS)
    strengths: list[str] = Field(min_length=1, max_length=MAX_STRENGTHS)
    current_difficulties: list[str] = Field(min_length=1, max_length=MAX_DIFFICULTIES)
    response_to_difficulty: str
    goal_codes: list[str] = Field(min_length=MIN_GOALS, max_length=MAX_GOALS)
    primary_goal_code: str
    motivators: list[str] = Field(min_length=1, max_length=MAX_MOTIVATORS)
    preferred_activity_minutes: int

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("nickname is required")
        return cleaned

    @field_validator("grade")
    @classmethod
    def normalize_grade(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in ALLOWED_GRADES:
            raise ValueError("unsupported grade")
        return cleaned

    @field_validator("interests", "strengths", "current_difficulties", "motivators")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        return _normalize_labels(values)

    @field_validator("response_to_difficulty")
    @classmethod
    def normalize_response(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if cleaned not in ALLOWED_RESPONSES:
            raise ValueError("unsupported response to difficulty")
        return cleaned

    @field_validator("preferred_activity_minutes")
    @classmethod
    def normalize_duration(cls, value: int) -> int:
        if value not in ALLOWED_DURATIONS:
            raise ValueError("unsupported duration")
        return value

    @field_validator("goal_codes")
    @classmethod
    def normalize_goals(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            code = raw.strip()
            if code in seen:
                raise ValueError("duplicate goal")
            if code not in ALLOWED_ONBOARDING_GOAL_CODES:
                raise ValueError("unknown goal")
            seen.add(code)
            cleaned.append(code)
        return cleaned

    @field_validator("primary_goal_code")
    @classmethod
    def normalize_primary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("primary goal is required")
        return cleaned

    @model_validator(mode="after")
    def primary_must_be_selected(self) -> "DemoProfileWrite":
        if self.primary_goal_code not in self.goal_codes:
            raise ValueError("primary goal must be one of the selected goals")
        ordered = [self.primary_goal_code] + [
            code for code in self.goal_codes if code != self.primary_goal_code
        ]
        self.goal_codes = ordered
        return self


class DemoProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interests: list[str] = Field(min_length=1, max_length=MAX_INTERESTS)
    strengths: list[str] = Field(min_length=1, max_length=MAX_STRENGTHS)
    current_difficulties: list[str] = Field(min_length=1, max_length=MAX_DIFFICULTIES)
    response_to_difficulty: str
    goal_codes: list[str] = Field(min_length=MIN_GOALS, max_length=MAX_GOALS)
    primary_goal_code: str
    motivators: list[str] = Field(min_length=1, max_length=MAX_MOTIVATORS)
    preferred_activity_minutes: int

    @field_validator("interests", "strengths", "current_difficulties", "motivators")
    @classmethod
    def normalize_labels(cls, values: list[str]) -> list[str]:
        return _normalize_labels(values)

    @field_validator("response_to_difficulty")
    @classmethod
    def normalize_response(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if cleaned not in ALLOWED_RESPONSES:
            raise ValueError("unsupported response to difficulty")
        return cleaned

    @field_validator("preferred_activity_minutes")
    @classmethod
    def normalize_duration(cls, value: int) -> int:
        if value not in ALLOWED_DURATIONS:
            raise ValueError("unsupported duration")
        return value

    @field_validator("goal_codes")
    @classmethod
    def normalize_goals(cls, values: list[str]) -> list[str]:
        return DemoProfileWrite.normalize_goals(values)

    @field_validator("primary_goal_code")
    @classmethod
    def normalize_primary(cls, value: str) -> str:
        return DemoProfileWrite.normalize_primary(value)

    @model_validator(mode="after")
    def primary_must_be_selected(self) -> "DemoProfileUpdate":
        if self.primary_goal_code not in self.goal_codes:
            raise ValueError("primary goal must be one of the selected goals")
        self.goal_codes = [self.primary_goal_code] + [
            code for code in self.goal_codes if code != self.primary_goal_code
        ]
        return self


def _normalize_labels(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = " ".join(raw.split())
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        if len(item) > ITEM_MAX_LEN:
            raise ValueError("label too long")
        seen.add(key)
        cleaned.append(item)
    if not cleaned:
        raise ValueError("at least one value is required")
    return cleaned


def setup_hayes_profile(session: Session, tenant: DemoTenant) -> DemoChildProfileRead:
    if tenant.child is not None:
        raise ProfileSetupError(
            "already_configured", 409, "A demo profile already exists."
        )
    child = _create_child_from_preset(
        session, tenant, HAYES_PROFILE, PROFILE_SOURCE_HAYES
    )
    return load_demo_child_profile(
        session, child, tester_fingerprint=tenant.tester_fingerprint
    )


def setup_custom_profile(
    session: Session, tenant: DemoTenant, data: DemoProfileWrite
) -> DemoChildProfileRead:
    if tenant.child is not None:
        raise ProfileSetupError(
            "already_configured", 409, "A demo profile already exists."
        )
    preset = SyntheticProfile(
        key="custom",
        nickname=data.nickname,
        age_years=data.age_years,
        grade=data.grade,
        interests=tuple(data.interests),
        strengths=tuple(data.strengths),
        current_difficulties=tuple(data.current_difficulties),
        motivators=tuple(data.motivators),
        response_to_difficulty=data.response_to_difficulty,
        preferred_activity_minutes=data.preferred_activity_minutes,
        goal_codes=tuple(data.goal_codes),
    )
    child = _create_child_from_preset(session, tenant, preset, PROFILE_SOURCE_CUSTOM)
    return load_demo_child_profile(
        session, child, tester_fingerprint=tenant.tester_fingerprint
    )


def update_demo_profile(
    session: Session, tenant: DemoTenant, data: DemoProfileUpdate
) -> DemoChildProfileRead:
    child = tenant.child
    if child is None:
        raise ProfileSetupError("setup_required", 409, "Create a demo profile first.")
    latest = _latest_baseline(session, child)
    if latest is None:
        raise ProfileSetupError("setup_required", 409, "Create a demo profile first.")
    _insert_baseline(
        session,
        household_id=child.household_id,
        child_id=child.id,
        age_years=latest.age_years,
        grade=latest.grade,
        interests=list(data.interests),
        strengths=list(data.strengths),
        current_difficulties=list(data.current_difficulties),
        motivators=list(data.motivators),
        response_to_difficulty=data.response_to_difficulty,
        preferred_activity_minutes=data.preferred_activity_minutes,
        baseline_id=uuid4(),
    )
    _replace_active_goals(
        session,
        household_id=child.household_id,
        child_id=child.id,
        goal_codes=data.goal_codes,
        goal_id_for_code=lambda code: session_goal_id(tenant.session_hash, code),
    )
    session.flush()
    return load_demo_child_profile(
        session, child, tester_fingerprint=tenant.tester_fingerprint
    )


def apply_synthetic_profile(
    session: Session,
    *,
    household_id: UUID,
    child_id: UUID,
    preset: SyntheticProfile,
    baseline_id: UUID,
    goal_id_for_code,
) -> Child:
    household = session.get(Household, household_id)
    if household is None:
        household = Household(id=household_id, display_name="Demo Household")
        session.add(household)
        session.flush()

    child = session.get(Child, child_id)
    if child is None:
        child = Child(id=child_id, household_id=household_id)
        session.add(child)
    child.household_id = household_id
    child.nickname = preset.nickname
    session.flush()

    existing = _latest_baseline(session, child)
    if existing is None:
        _insert_baseline(
            session,
            household_id=household_id,
            child_id=child_id,
            age_years=preset.age_years,
            grade=preset.grade,
            interests=list(preset.interests),
            strengths=list(preset.strengths),
            current_difficulties=list(preset.current_difficulties),
            motivators=list(preset.motivators),
            response_to_difficulty=preset.response_to_difficulty,
            preferred_activity_minutes=preset.preferred_activity_minutes,
            baseline_id=baseline_id,
        )
    elif not _baseline_matches_preset(existing, preset):
        _insert_baseline(
            session,
            household_id=household_id,
            child_id=child_id,
            age_years=preset.age_years,
            grade=preset.grade,
            interests=list(preset.interests),
            strengths=list(preset.strengths),
            current_difficulties=list(preset.current_difficulties),
            motivators=list(preset.motivators),
            response_to_difficulty=preset.response_to_difficulty,
            preferred_activity_minutes=preset.preferred_activity_minutes,
            baseline_id=uuid4(),
        )
    _replace_active_goals(
        session,
        household_id=household_id,
        child_id=child_id,
        goal_codes=list(preset.goal_codes),
        goal_id_for_code=goal_id_for_code,
    )
    session.flush()
    return child


def _create_child_from_preset(
    session: Session,
    tenant: DemoTenant,
    preset: SyntheticProfile,
    source: str,
) -> Child:
    from daily_win_api.dev.models import DemoSession
    from daily_win_api.dev.seed import seed_skill_taxonomy

    seed_skill_taxonomy(session)
    child_id = session_child_id(tenant.session_hash)
    child = apply_synthetic_profile(
        session,
        household_id=tenant.household_id,
        child_id=child_id,
        preset=preset,
        baseline_id=session_baseline_id(tenant.session_hash),
        goal_id_for_code=lambda code: session_goal_id(tenant.session_hash, code),
    )
    row = session.scalar(
        select(DemoSession).where(DemoSession.session_hash == tenant.session_hash)
    )
    if row is None:
        raise ProfileSetupError("demo_unavailable", 400, "Demo is not available.")
    row.child_id = child.id
    row.profile_source = source
    session.flush()
    return child


def _insert_baseline(
    session: Session,
    *,
    household_id: UUID,
    child_id: UUID,
    age_years: int,
    grade: str,
    interests: list[str],
    strengths: list[str],
    current_difficulties: list[str],
    motivators: list[str],
    response_to_difficulty: str,
    preferred_activity_minutes: int,
    baseline_id: UUID,
) -> ChildBaseline:
    baseline = ChildBaseline(
        id=baseline_id,
        household_id=household_id,
        child_id=child_id,
        recorded_at=datetime.now(UTC),
        age_years=age_years,
        grade=grade,
        interests=interests,
        strengths=strengths,
        current_difficulties=current_difficulties,
        motivators=motivators,
        response_to_difficulty=response_to_difficulty,
        preferred_activity_minutes=preferred_activity_minutes,
        schema_version=1,
    )
    session.add(baseline)
    session.flush()
    return baseline


def _replace_active_goals(
    session: Session,
    *,
    household_id: UUID,
    child_id: UUID,
    goal_codes: list[str],
    goal_id_for_code,
) -> None:
    existing = list(
        session.scalars(
            select(ChildGoal).where(
                ChildGoal.child_id == child_id,
                ChildGoal.household_id == household_id,
            )
        )
    )
    by_skill = {row.skill_id: row for row in existing}
    wanted_ids = [skill_id_for_code(code) for code in goal_codes]
    wanted_set = set(wanted_ids)
    for row in existing:
        if row.skill_id not in wanted_set:
            row.active = False
    for priority, skill_id in enumerate(wanted_ids, start=1):
        row = by_skill.get(skill_id)
        if row is None:
            skill = session.get(Skill, skill_id)
            if skill is None:
                raise ProfileSetupError("unknown_skill", 422, "Unknown goal.")
            code = next(
                code for code in goal_codes if skill_id_for_code(code) == skill_id
            )
            row = ChildGoal(id=goal_id_for_code(code))
            session.add(row)
        row.household_id = household_id
        row.child_id = child_id
        row.skill_id = skill_id
        row.priority = priority
        row.active = True
    session.flush()


def _baseline_matches_preset(baseline: ChildBaseline, preset: SyntheticProfile) -> bool:
    return (
        baseline.age_years == preset.age_years
        and baseline.grade == preset.grade
        and list(baseline.interests) == list(preset.interests)
        and list(baseline.strengths) == list(preset.strengths)
        and list(baseline.current_difficulties) == list(preset.current_difficulties)
        and list(baseline.motivators) == list(preset.motivators)
        and baseline.response_to_difficulty == preset.response_to_difficulty
        and baseline.preferred_activity_minutes == preset.preferred_activity_minutes
    )


def _latest_baseline(session: Session, child: Child) -> ChildBaseline | None:
    return session.scalars(
        select(ChildBaseline)
        .where(
            ChildBaseline.child_id == child.id,
            ChildBaseline.household_id == child.household_id,
        )
        .order_by(ChildBaseline.recorded_at.desc())
        .limit(1)
    ).first()
