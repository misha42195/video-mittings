from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Meeting


@dataclass(frozen=True, slots=True)
class CreateMeetingCommand:
    owner_id: int
    title: str
    scheduled_at: datetime
    description: str | None = None


class CreateMeetingHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, command: CreateMeetingCommand) -> Meeting:
        meeting = Meeting(
            owner_id=command.owner_id,
            title=command.title,
            description=command.description,
            scheduled_at=command.scheduled_at,
        )
        self._db.add(meeting)
        await self._db.commit()
        await self._db.refresh(meeting)

        return meeting
