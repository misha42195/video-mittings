from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import MeetingNotFoundError
from api.meeting_files.exceptions import FileNotFoundError
from api.meeting_files.models import MeetingFile
from api.models import Meeting


async def _require_owned_meeting(db: AsyncSession, meeting_id: int, owner_id: int) -> None:
    meeting = await db.scalar(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == owner_id)
    )
    if meeting is None:
        raise MeetingNotFoundError()


@dataclass(frozen=True, slots=True)
class ListMeetingFilesQuery:
    meeting_id: int
    owner_id: int


class ListMeetingFilesHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: ListMeetingFilesQuery) -> list[MeetingFile]:
        await _require_owned_meeting(self._db, query.meeting_id, query.owner_id)

        result = await self._db.scalars(
            select(MeetingFile)
            .where(MeetingFile.meeting_id == query.meeting_id)
            .order_by(MeetingFile.created_at, MeetingFile.id)
        )
        return list(result.all())


@dataclass(frozen=True, slots=True)
class GetMeetingFileQuery:
    meeting_id: int
    file_id: int
    owner_id: int


class GetMeetingFileHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: GetMeetingFileQuery) -> MeetingFile:
        await _require_owned_meeting(self._db, query.meeting_id, query.owner_id)

        file = await self._db.scalar(
            select(MeetingFile).where(
                MeetingFile.id == query.file_id, MeetingFile.meeting_id == query.meeting_id
            )
        )
        if file is None:
            raise FileNotFoundError()
        return file
