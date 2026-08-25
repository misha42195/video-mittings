from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.exceptions import MeetingNotFoundError
from api.meeting_files.exceptions import FileNotFoundError, FileTypeNotAllowedError
from api.meeting_files.models import MeetingFile
from api.meeting_files.storage import LocalStorageService
from api.models import Meeting


async def _require_owned_meeting(db: AsyncSession, meeting_id: int, owner_id: int) -> None:
    meeting = await db.scalar(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == owner_id)
    )
    if meeting is None:
        raise MeetingNotFoundError()


@dataclass(frozen=True, slots=True)
class UploadMeetingFileCommand:
    meeting_id: int
    owner_id: int
    upload_file: UploadFile


class UploadMeetingFileHandler:
    def __init__(self, db: AsyncSession, storage: LocalStorageService | None = None) -> None:
        self._db = db
        self._storage = storage or LocalStorageService()

    async def handle(self, command: UploadMeetingFileCommand) -> MeetingFile:
        await _require_owned_meeting(self._db, command.meeting_id, command.owner_id)

        # Validation: extension and content_type
        settings = get_settings()
        original_filename = (command.upload_file.filename or "").strip()
        ext = Path(original_filename).suffix.lower()

        if not original_filename or ext not in settings.allowed_extensions:
            allowed = ", ".join(sorted(e.lstrip(".") for e in settings.allowed_extensions))
            raise FileTypeNotAllowedError(f"Недопустимый тип файла. Разрешены: {allowed}")

        content_type = command.upload_file.content_type or ""
        # Allow empty or generic octet-stream — rely on extension check for those cases
        # Strict check only for explicit mime types
        if (
            content_type
            and content_type != "application/octet-stream"
            and content_type not in settings.allowed_content_types
        ):
            allowed = ", ".join(sorted(e.lstrip(".") for e in settings.allowed_extensions))
            raise FileTypeNotAllowedError(f"Недопустимый тип файла. Разрешены: {allowed}")

        relative_path, stored_filename, size = await self._storage.save(
            command.upload_file, command.meeting_id
        )

        if size == 0:
            await self._storage.delete(relative_path)
            raise FileTypeNotAllowedError("Пустой файл не разрешен")

        meeting_file = MeetingFile(
            meeting_id=command.meeting_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=relative_path,
            content_type=content_type or "application/octet-stream",
            size=size,
        )
        self._db.add(meeting_file)
        try:
            await self._db.commit()
            await self._db.refresh(meeting_file)
        except Exception:
            # orphan file cleanup — DB commit failed after file was written to disk
            await self._storage.delete(relative_path)
            raise
        return meeting_file


@dataclass(frozen=True, slots=True)
class DeleteMeetingFileCommand:
    meeting_id: int
    file_id: int
    owner_id: int


class DeleteMeetingFileHandler:
    def __init__(self, db: AsyncSession, storage: LocalStorageService | None = None) -> None:
        self._db = db
        self._storage = storage or LocalStorageService()

    async def handle(self, command: DeleteMeetingFileCommand) -> None:
        await _require_owned_meeting(self._db, command.meeting_id, command.owner_id)

        file = await self._db.scalar(
            select(MeetingFile).where(
                MeetingFile.id == command.file_id, MeetingFile.meeting_id == command.meeting_id
            )
        )
        if file is None:
            raise FileNotFoundError()

        storage_path = file.storage_path
        await self._db.delete(file)
        await self._db.commit()
        # delete from disk after DB commit — if file already missing, keep 204 (idempotent)
        try:
            await self._storage.delete(storage_path)
        except OSError:
            # log and keep 204 even if disk delete fails
            pass
