from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChildRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    nickname: str
    created_at: datetime
    updated_at: datetime


class ChildBaselineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID
    child_id: UUID
    recorded_at: datetime
    age_years: int
    grade: str
    interests: list[str]
    strengths: list[str]
    current_difficulties: list[str]
    motivators: list[str]
    response_to_difficulty: str | None
    preferred_activity_minutes: int
    schema_version: int
    created_at: datetime


class DemoChildSummary(BaseModel):
    id: UUID
    nickname: str


class DemoBaselineSummary(BaseModel):
    age_years: int
    grade: str
    interests: list[str]
    strengths: list[str]
    current_difficulties: list[str]
    motivators: list[str]
    response_to_difficulty: str | None
    preferred_activity_minutes: int
    recorded_at: datetime


class DemoGoalSummary(BaseModel):
    priority: int
    skill_code: str
    display_name: str
    domain: str


class DemoChildProfileRead(BaseModel):
    child: DemoChildSummary
    baseline: DemoBaselineSummary
    goals: list[DemoGoalSummary]


class ChildBaselineCreate(BaseModel):
    """Parent-reported snapshot. Not an established learner fact."""

    age_years: int = Field(ge=3, le=12)
    grade: str = Field(min_length=1, max_length=32)
    interests: list[str]
    strengths: list[str]
    current_difficulties: list[str]
    motivators: list[str]
    response_to_difficulty: str | None = None
    preferred_activity_minutes: int = Field(ge=5, le=90)
    schema_version: int = 1
