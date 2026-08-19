from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MeetingCreate(BaseModel):
    title: str
    description: str | None = None
    scheduled_at: datetime


class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    scheduled_at: datetime
    created_at: datetime
