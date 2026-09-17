from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from daily_win_api.domains.learning.enums import EvidenceKind, EvidenceSource


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    domain: str
    display_name: str
    description: str | None
    state_mode: str
    active: bool
    created_at: datetime


class ChildGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    child_id: UUID
    skill_id: UUID
    priority: int
    active: bool
    created_at: datetime
    updated_at: datetime


class LearningEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    child_id: UUID
    skill_id: UUID | None
    evidence_kind: EvidenceKind
    source: EvidenceSource
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]
    schema_version: int
    confidence: float | None
    supersedes_event_id: UUID | None
    created_at: datetime


class LearningEventCreate(BaseModel):
    household_id: UUID
    child_id: UUID
    skill_id: UUID | None = None
    evidence_kind: EvidenceKind
    source: EvidenceSource
    event_type: str = Field(min_length=1, max_length=64)
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1
    confidence: float | None = Field(default=None, ge=0, le=1)
    supersedes_event_id: UUID | None = None


class LearnerSkillStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    child_id: UUID
    skill_id: UUID
    state: dict[str, Any]
    evidence_count: int
    confidence: float | None
    algorithm_version: str
    computed_at: datetime
    created_at: datetime
    updated_at: datetime
