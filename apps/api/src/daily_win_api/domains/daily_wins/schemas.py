from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from daily_win_api.ai.schemas import DailyWinDraft
from daily_win_api.domains.daily_wins.enums import (
    Completion,
    Difficulty,
    Engagement,
    SetbackResponse,
)


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


class DailyWinFeedbackCreate(BaseModel):
    difficulty: Difficulty
    engagement: Engagement
    completion: Completion
    setback_response: SetbackResponse
    what_helped: str | None = Field(default=None, max_length=400)
    additional_note: str | None = Field(default=None, max_length=400)


class ParentInsight(BaseModel):
    observation: str
    next_adjustment: str


class ParentLearnerStateSummary(BaseModel):
    skill_code: str
    latest_signal: str
    direction: str
    evidence_count: int


class DemoFeedbackRead(BaseModel):
    feedback_id: UUID
    insight: ParentInsight
    learner_state: ParentLearnerStateSummary


class DemoResetRead(BaseModel):
    status: str = "ok"


class DailyWinGenerationError(Exception):
    def __init__(self, code: str, http_status: int, client_message: str) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.client_message = client_message


class SkillContractError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SafetyRejectedError(Exception):
    """Generated content failed deterministic safety checks."""

    def __init__(self, code: str = "unsafe_content") -> None:
        super().__init__(code)
        self.code = code


class ContextUnavailableError(Exception):
    """Demo child, baseline, or active goals are missing."""


RECENT_LEARNING_EVENTS_CAP = 10
RECENT_DAILY_WINS_CAP = 3
INPUT_SCHEMA_VERSION = "2"
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
CLIENT_FEEDBACK_REQUIRED = (
    "Reflect on the current Daily Win before creating another."
)
CLIENT_FEEDBACK_EXISTS = "This Daily Win already has a reflection."
CLIENT_FEEDBACK_NOT_FOUND = "That Daily Win is not available."
CLIENT_FEEDBACK_FAILED = "Reflection could not be saved. Please try again."
CLIENT_RESET_FAILED = "Demo could not be reset. Please try again."
