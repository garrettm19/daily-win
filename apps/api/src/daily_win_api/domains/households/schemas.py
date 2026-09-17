from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HouseholdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str | None
    created_at: datetime
    updated_at: datetime
