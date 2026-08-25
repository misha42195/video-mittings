from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import MeetingNotFoundError
from api.meeting_files.models import MeetingFile
from api.models import Meeting


@dataclass(frozen=True, slots=True)
class ListMeetingFilesQuery:
    meeting_id: int
    owner_id: int


class ListMeetingFilesHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: ListMeetingFilesQuery) -> list[MeetingFile]:
        meeting = await self._db.scalar(
            select(Meeting).where(
                Meeting.id == query.meeting_id, Meeting.owner_id == query.owner_id
            )
        )
        if meeting is None:
            raise MeetingNotFoundError

        result = await self._db.scalars(
            select(MeetingFile)
            .where(MeetingFile.meeting_id == query.meeting_id)
            .order_by(MeetingFile.created_at, MeetingFile.id)
        )
        return list(result.all())
