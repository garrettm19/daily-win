from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Material(StrEnum):
    NONE = "NONE"
    PAPER = "PAPER"
    PENCIL = "PENCIL"
    CRAYONS_OR_MARKERS = "CRAYONS_OR_MARKERS"
    TAPE = "TAPE"
    INDEX_CARDS = "INDEX_CARDS"
    PLASTIC_CUPS = "PLASTIC_CUPS"
    BLOCKS = "BLOCKS"
    BOOK = "BOOK"
    COINS = "COINS"
    SOFT_BALL = "SOFT_BALL"
    TIMER = "TIMER"


class SegmentType(StrEnum):
    LEARN = "LEARN"
    DO = "DO"
    GROW = "GROW"


class ParentBriefing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(min_length=1, max_length=400)
    how_to_coach: str = Field(min_length=1, max_length=400)
    watch_for: str = Field(min_length=1, max_length=400)
    avoid: str = Field(min_length=1, max_length=400)


class DailyWinSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SegmentType
    title: str = Field(min_length=1, max_length=80)
    minutes: int = Field(ge=2, le=15)
    steps: list[Annotated[str, Field(min_length=1, max_length=400)]] = Field(
        min_length=1, max_length=6
    )
    parent_role: str = Field(min_length=1, max_length=400)


class Adaptations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    if_too_easy: str = Field(min_length=1, max_length=400)
    if_too_hard: str = Field(min_length=1, max_length=400)


class DailyWinDraft(BaseModel):
    """Validated structured Daily Win produced by ModelGateway."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    objective: str = Field(min_length=1, max_length=400)
    duration_minutes: int = Field(ge=10, le=25)
    primary_skill_code: str = Field(min_length=1, max_length=64)
    supporting_skill_codes: list[Annotated[str, Field(min_length=1, max_length=64)]] = (
        Field(default_factory=list, max_length=2)
    )
    personalization_summary: str = Field(min_length=1, max_length=500)
    materials: list[Material] = Field(min_length=1, max_length=8)
    parent_briefing: ParentBriefing
    segments: list[DailyWinSegment] = Field(min_length=3, max_length=3)
    adaptations: Adaptations
    success_checks: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=2, max_length=4
    )
    observation_focus: str = Field(min_length=1, max_length=400)
    safety_flags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=12
    )
    adaptation_summary: str | None = Field(default=None, max_length=400)

    @field_validator("segments")
    @classmethod
    def segments_must_be_learn_do_grow(
        cls, segments: list[DailyWinSegment]
    ) -> list[DailyWinSegment]:
        types = [segment.type for segment in segments]
        expected = [SegmentType.LEARN, SegmentType.DO, SegmentType.GROW]
        if types != expected:
            raise ValueError("segments must be LEARN, DO, GROW in that order")
        return segments


class GoalContext(BaseModel):
    priority: int
    skill_code: str
    display_name: str
    domain: str


class SkillStateContext(BaseModel):
    skill_code: str
    evidence_count: int
    confidence: float | None
    has_derived_state: bool
    latest_signal: str | None = None
    direction: str | None = None
    summary: str | None = None


class LearningEventContext(BaseModel):
    evidence_kind: str
    source: str
    event_type: str
    skill_code: str | None
    occurred_at: datetime
    summary: str


class PriorDailyWinContext(BaseModel):
    title: str
    primary_skill_code: str
    objective: str


class InstructionPlanContext(BaseModel):
    """Authoritative instructional decision. Renderer must not change these."""

    primary_skill_code: str
    supporting_skill_code: str | None = None
    selection_reason_codes: list[str]
    instruction_mode: str
    intended_difficulty: str
    scaffold_level: str
    prerequisite_rationale: str
    assessment_objective: str
    assessment_probe: dict[str, object]
    desired_evidence: str
    growth_target_code: str | None = None
    growth_adaptation_summary: str | None = None
    duration_minutes: int = Field(ge=10, le=25)
    engagement_theme_constraints: list[str] = Field(default_factory=list, max_length=3)
    recent_themes_to_avoid: list[str] = Field(default_factory=list, max_length=3)
    policy_version: str
    academic_band: str | None = None
    renderer_contracts: list[str] = Field(default_factory=list, max_length=12)
    placement_policy_version: str | None = None
    placement_entry_label: str | None = None
    placement_why: str | None = None
    presentation_constraint: str | None = None


class EvidenceSummaryContext(BaseModel):
    skill_code: str
    summary: str
    reporting_kind: str


class AdaptationDirective(BaseModel):
    """Application-owned coaching policy sent to the model. Not a diagnosis."""

    skill_code: str
    latest_signal: str
    challenge_adjustment: str
    coaching_adjustment: str
    parent_facing_summary: str = Field(min_length=1, max_length=400)


class ParentReportedBaselineContext(BaseModel):
    """Parent-reported snapshot. Not an established learner fact."""

    age_years: int
    grade: str
    interests: list[str]
    strengths: list[str]
    current_difficulties: list[str]
    motivators: list[str]
    response_to_difficulty: str | None
    preferred_activity_minutes: int
    reporting_kind: Literal["parent_reported"] = "parent_reported"


class DailyWinModelContext(BaseModel):
    """Bounded renderer context. Contains no database identifiers."""

    nickname: str
    parent_reported_baseline: ParentReportedBaselineContext
    instruction_plan: InstructionPlanContext
    bounded_evidence_summaries: list[EvidenceSummaryContext] = Field(
        default_factory=list, max_length=6
    )
    recent_themes: list[str] = Field(default_factory=list, max_length=3)
    allowed_skill_codes: list[str]
    allowed_materials: list[str]


class ContextManifest(BaseModel):
    """Internal provenance IDs. Never sent to the model or the mobile client."""

    child_id: UUID
    household_id: UUID
    baseline_id: UUID | None = None
    goal_ids: list[UUID] = Field(default_factory=list)
    skill_state_ids: list[UUID] = Field(default_factory=list)
    learning_event_ids: list[UUID] = Field(default_factory=list)
    prior_daily_win_ids: list[UUID] = Field(default_factory=list)
    instruction_plan_id: UUID | None = None
    prompt_version: str
    input_schema_version: str
    output_schema_version: str


class DailyWinGenerationResult(BaseModel):
    draft: DailyWinDraft
    provider: str
    model: str
    prompt_version: str
    provider_request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    service_tier: str | None = None
    requested_service_tier: str | None = None
    reasoning_effort: str | None = None
    generation_intent: str | None = None
