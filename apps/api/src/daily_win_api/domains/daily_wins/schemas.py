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

    @model_validator(mode="after")
    def academic_counts_are_consistent(self) -> "DailyWinFeedbackCreate":
        correct = self.correct_count
        attempted = self.attempted_count
        if (correct is None) != (attempted is None):
            raise ValueError("academic_counts_incomplete")
        if correct is not None and attempted is not None and correct > attempted:
            raise ValueError("academic_counts_invalid")
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

    def __init__(self, rule: str) -> None:
        super().__init__(rule)
        self.code = "renderer_contract_failed"
        self.rule = rule


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
INPUT_SCHEMA_VERSION = "4"
OUTPUT_SCHEMA_VERSION = "2"
CONTENT_SCHEMA_VERSION = 2
DAILY_WIN_STATUS_READY = "ready"
AI_RUN_STATUS_STARTED = "started"
AI_RUN_STATUS_SUCCEEDED = "succeeded"
AI_RUN_STATUS_REJECTED = "rejected"
AI_RUN_STATUS_FAILED = "failed"
OPERATION_DAILY_WIN_GENERATE = "daily_win_generate"

CLIENT_GENERATION_FAILED = "Daily Win could not be created. Please try again."
CLIENT_UNAVAILABLE = "Demo child profile is not available."
CLIENT_FEEDBACK_REQUIRED = "Reflect on the current Daily Win before creating another."
CLIENT_FEEDBACK_EXISTS = "This Daily Win already has a reflection."
CLIENT_FEEDBACK_NOT_FOUND = "That Daily Win is not available."
CLIENT_FEEDBACK_FAILED = "Reflection could not be saved. Please try again."
CLIENT_RESET_FAILED = "Demo could not be reset. Please try again."
CLIENT_SETUP_REQUIRED = "Create a demo profile first."
CLIENT_ALREADY_CONFIGURED = "A demo profile already exists."
CLIENT_NOT_FOUND = "That Daily Win is not available."
