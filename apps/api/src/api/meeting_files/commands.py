from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.exceptions import MeetingNotFoundError
from api.meeting_files.exceptions import FileTypeNotAllowedError
from api.meeting_files.models import MeetingFile
from api.meeting_files.storage import LocalStorageService
from api.models import Meeting


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
        # Ownership check — 404 if not owned or not exists
        meeting = await self._db.scalar(
            select(Meeting).where(
                Meeting.id == command.meeting_id, Meeting.owner_id == command.owner_id
            )
        )
        if meeting is None:
            raise MeetingNotFoundError

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
