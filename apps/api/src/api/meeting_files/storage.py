from pathlib import Path
from uuid import uuid4

import aiofiles  # type: ignore[import-untyped]
from fastapi import UploadFile

from api.config import get_settings
from api.meeting_files.exceptions import FileTooLargeError


class LocalStorageService:
    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.storage_root)
        self._max_size = settings.max_file_size

    @property
    def root(self) -> Path:
        return self._root

    @property
    def max_size(self) -> int:
        return self._max_size

    async def save(self, file: UploadFile, meeting_id: int) -> tuple[str, str, int]:
        """Save upload to disk chunk-by-chunk, return (relative_path, stored_filename, size)."""
        original_name = file.filename or "file"
        ext = Path(original_name).suffix.lower()
        stored_filename = f"{uuid4().hex}{ext}"
        relative_path = f"meetings/{meeting_id}/{stored_filename}"
        dest = self._root / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first for atomicity
        tmp_path = dest.with_suffix(dest.suffix + ".tmp")

        size = 0
        try:
            async with aiofiles.open(tmp_path, "wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self._max_size:
                        # cleanup handled in finally/except
                        raise FileTooLargeError(
                            f"Файл слишком большой. Максимум {self._max_size // (1024 * 1024)} МБ"
                        )
                    await out.write(chunk)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise
        else:
            tmp_path.rename(dest)

        return relative_path, stored_filename, size

    async def delete(self, relative_path: str) -> None:
        path = self._root / relative_path
        if path.exists():
            path.unlink(missing_ok=True)

    def absolute_path(self, relative_path: str) -> Path:
        return self._root / relative_path
