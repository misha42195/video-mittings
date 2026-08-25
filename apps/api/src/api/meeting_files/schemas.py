from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MeetingFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    original_filename: str
    content_type: str
    size: int
    created_at: datetime
