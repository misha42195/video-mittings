from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import MeetingNotFoundError
from api.models import Meeting


@dataclass(frozen=True, slots=True)
class ListMeetingsQuery:
    owner_id: int


class ListMeetingsHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: ListMeetingsQuery) -> list[Meeting]:
        result = await self._db.scalars(
            select(Meeting).where(Meeting.owner_id == query.owner_id).order_by(Meeting.id)
        )
        return list(result.all())


@dataclass(frozen=True, slots=True)
class GetMeetingQuery:
    meeting_id: int
    owner_id: int


class GetMeetingHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: GetMeetingQuery) -> Meeting:
        meeting = await self._db.scalar(
            select(Meeting).where(
                Meeting.id == query.meeting_id, Meeting.owner_id == query.owner_id
            )
        )
        if meeting is None:
            raise MeetingNotFoundError()
        return meeting
