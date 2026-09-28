from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)
from daily_win_api.domains.learning.enums import AcademicResult


class ParentAssessmentRead(BaseModel):
    what_to_check: str
    success_looks_like: str
    prompt_label: str
    asks_for_counts: bool
    support_caption: str


class LearningEngineDebugRead(BaseModel):
    target: str
    mode: str
    difficulty: str
    scaffold: str
    why: list[str]
    assessment: str
    policy: str
    selected_goal: str | None = None
    expected_entry: str | None = None
    evidence: str | None = None
    placement: str | None = None
    placement_why: str | None = None


class CoachCueRead(BaseModel):
    label: str
    text: str


class BonusChallengeRead(BaseModel):
    code: str
    category: str
    title: str
    minutes: int
    prompt: str
    safety: str
    personal_best: bool
    optional: bool = True
    counts_as_mastery: bool = False


class DiscoveryDomainRead(BaseModel):
    domain: str
    status: str
    label: str


class DiscoveryWeekRead(BaseModel):
    active: bool
    headline: str
    body: str
    domains: list[DiscoveryDomainRead] = Field(default_factory=list)


class SmartReflectionRead(BaseModel):
    questions: list[dict[str, str]] = Field(default_factory=list)
    notice_chips: list[str] = Field(default_factory=list)
    strategy_options: list[str] = Field(default_factory=list)
    self_correction_options: list[str] = Field(default_factory=list)
    effort_options: list[str] = Field(default_factory=list)
    bonus_engagement_options: list[str] = Field(default_factory=list)


class ResultSnapshotRead(BaseModel):
    difficulty: str | None = None
    academic_result: str | None = None
    setback_response: str | None = None
    completion: str | None = None
    engagement: str | None = None


class DemoDailyWinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    child_nickname: str
    title: str
    objective: str
    duration_minutes: int
    primary_skill_code: str
    primary_skill_display_name: str
    content: DailyWinDraft
    has_feedback: bool = False
    created_at: datetime
    assessment: ParentAssessmentRead | None = None
    asks_about_setback: bool = True
    what_changed_today: str | None = None
    learning_engine: LearningEngineDebugRead | None = None
    coach_card: list[str] = Field(default_factory=list)
    coach_cues: list[CoachCueRead] = Field(default_factory=list)
    wait_guidance: str | None = None
    bonus_challenge: BonusChallengeRead | None = None
    smart_reflection: SmartReflectionRead | None = None
    discovery: DiscoveryWeekRead | None = None
    guide_onboarding: list[str] | None = None
    teach_the_coach: bool = False
    protocol_version: str | None = None
    one_thing_to_improve: str | None = None
    result_snapshot: ResultSnapshotRead | None = None


class FirstWinTimingRead(BaseModel):
    profile_saved_at: str | None = None
    preparation_started_at: str | None = None
    terra_completed_at: str | None = None
    win_ready_at: str | None = None
    profile_saved_ms: int | None = None
    preparation_started_ms: int | None = None
    terra_completed_ms: int | None = None
    win_ready_ms: int | None = None
    raw_model_ms: int | None = None
    onboarding_ms: int | None = None
    visible_wait_ms: int | None = None
    ready_before_guide: bool | None = None
    trigger: str | None = None
    guide_started_at: str | None = None
    guide_finished_at: str | None = None
    guide_skipped: bool | None = None
    guide_dwell_ms: int | None = None


class NextWinStateRead(BaseModel):
    daily_win: DemoDailyWinRead | None = None
    preparation_status: str
    trigger: str | None = None
    generation_stage: str | None = None
    focus_preview: str | None = None
    coach_preview: list[str] = Field(default_factory=list)
    generated_after_reflection: bool = False
    plan_valid: bool | None = None
    error_code: str | None = None
    attempt_count: int | None = None
    model: str | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
    backend_elapsed_ms: int = 0
    first_win_timing: FirstWinTimingRead | None = None


class DailyWinFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    difficulty: Difficulty
    engagement: Engagement
    completion: Completion
    setback_response: SetbackResponse = SetbackResponse.NO_SETBACK_OCCURRED
    what_helped: str | None = Field(default=None, max_length=400)
    additional_note: str | None = Field(default=None, max_length=400)
    academic_result: AcademicResult | None = None
    correct_count: int | None = Field(default=None, ge=0, le=20)
    attempted_count: int | None = Field(default=None, ge=0, le=20)
    self_correction: str | None = Field(default=None, max_length=32)
    strategy_observed: str | None = Field(default=None, max_length=64)
    performance_effort: str | None = Field(default=None, max_length=32)
    notice_chips: list[str] = Field(default_factory=list, max_length=8)
    bonus_engagement: str | None = Field(default=None, max_length=32)
    non_target_error: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def academic_counts_are_consistent(self) -> "DailyWinFeedbackCreate":
        from daily_win_api.domains.learning.observations import (
            ALLOWED_BONUS_ENGAGEMENT,
            ALLOWED_EFFORT,
            ALLOWED_NOTICE_CHIPS,
            ALLOWED_SELF_CORRECTION,
            ALLOWED_STRATEGY,
        )

        correct = self.correct_count
        attempted = self.attempted_count
        if (correct is None) != (attempted is None):
            raise ValueError("academic_counts_incomplete")
        if correct is not None and attempted is not None and correct > attempted:
            raise ValueError("academic_counts_invalid")
        if self.self_correction and self.self_correction not in ALLOWED_SELF_CORRECTION:
            raise ValueError("invalid_self_correction")
        if self.strategy_observed and self.strategy_observed not in ALLOWED_STRATEGY:
            raise ValueError("invalid_strategy")
        if self.performance_effort and self.performance_effort not in ALLOWED_EFFORT:
            raise ValueError("invalid_performance_effort")
        if (
            self.bonus_engagement
            and self.bonus_engagement not in ALLOWED_BONUS_ENGAGEMENT
        ):
            raise ValueError("invalid_bonus_engagement")
        unknown = [
            item for item in self.notice_chips if item not in ALLOWED_NOTICE_CHIPS
        ]
        if unknown:
            raise ValueError("invalid_notice_chips")
        return self


class ParentInsight(BaseModel):
    observation: str
    next_adjustment: str


class ParentLearnerStateSummary(BaseModel):
    skill_code: str
    latest_signal: str
    direction: str
    evidence_count: int


class LearnedItem(BaseModel):
    area: str
    summary: str


class DemoFeedbackRead(BaseModel):
    feedback_id: UUID
    insight: ParentInsight
    learner_state: ParentLearnerStateSummary
    academic_observation: str | None = None
    growth_observation: str | None = None
    what_we_learned: list[LearnedItem] = Field(default_factory=list)
    what_changes_next: str | None = None


class DemoResetRead(BaseModel):
    status: str = "ok"
    mode: str = "activity"


class PilotStatusRead(BaseModel):
    api: str = "ok"
    db: str
    generation_config: str
    model: str
    curriculum: str
    placement: str
    scheduler: str
    instruction: str
    prompt: str
    background_preparation: str


class GuideTimingWrite(BaseModel):
    guide_started_at: datetime | None = None
    guide_finished_at: datetime | None = None
    guide_skipped: bool = False
    guide_dwell_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class WeeklyCoachReportRead(BaseModel):
    week_start: str
    week_end: str
    summary_version: str
    source_session_count: int
    this_week: dict[str, object]
    what_looked_strong: list[str]
    what_still_took_work: list[str]
    how_they_handled_challenge: list[str]
    what_they_enjoyed: list[str]
    what_changes_next_week: list[str]
    one_thing_for_the_parent: str
    win_of_the_week_candidates: list[str]
    emerging_needs: list[dict[str, object]]
    engagement_memory: dict[str, object]
    next_week: dict[str, object] | None = None
    discovery_progress: list[str] = Field(default_factory=list)
    claims_trace: list[dict[str, str]] = Field(default_factory=list)


class DailyWinGenerationError(Exception):
    def __init__(
        self,
        code: str,
        http_status: int,
        client_message: str,
        *,
        dev_reason: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.client_message = client_message
        self.dev_reason = dev_reason


class SkillContractError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RendererContractError(Exception):
    """Generated activity failed a deterministic renderer contract."""

    def __init__(
        self,
        rule: str,
        failed_contracts: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(rule)
        self.code = "renderer_contract_failed"
        self.rule = rule
        self.failed_contracts = failed_contracts or (rule,)


class SafetyRejectedError(Exception):
    """Generated content failed deterministic safety checks."""

    def __init__(self, rule: str) -> None:
        super().__init__(rule)
        self.code = "unsafe_content"
        self.rule = rule


class ContextUnavailableError(Exception):
    """Demo child, baseline, or active goals are missing."""


RECENT_LEARNING_EVENTS_CAP = 10
RECENT_DAILY_WINS_CAP = 3
BOUNDED_EVIDENCE_CAP = 6
RECENT_THEMES_CAP = 3
MAX_GENERATION_ATTEMPTS = 3
INPUT_SCHEMA_VERSION = "5"
OUTPUT_SCHEMA_VERSION = "2"
CONTENT_SCHEMA_VERSION = 2
DAILY_WIN_STATUS_READY = "ready"
DAILY_WIN_STATUS_INVALIDATED = "invalidated"
AI_RUN_STATUS_STARTED = "started"
AI_RUN_STATUS_SUCCEEDED = "succeeded"
AI_RUN_STATUS_REJECTED = "rejected"
AI_RUN_STATUS_FAILED = "failed"
OPERATION_DAILY_WIN_GENERATE = "daily_win_generate"

CLIENT_GENERATION_FAILED = "Daily Win could not be created. Please try again."
CLIENT_UNAVAILABLE = "Demo child profile is not available."
CLIENT_FEEDBACK_REQUIRED = "Reflect on the current Daily Win before creating another."
CLIENT_GENERATION_IN_PROGRESS = "Getting today's Win ready."
CLIENT_FEEDBACK_EXISTS = "This Daily Win already has a reflection."
CLIENT_FEEDBACK_NOT_FOUND = "That Daily Win is not available."
CLIENT_FEEDBACK_FAILED = "Reflection could not be saved. Please try again."
CLIENT_RESET_FAILED = "Demo could not be reset. Please try again."
CLIENT_SETUP_REQUIRED = "Create a demo profile first."
CLIENT_ALREADY_CONFIGURED = "A demo profile already exists."
CLIENT_NOT_FOUND = "That Daily Win is not available."
