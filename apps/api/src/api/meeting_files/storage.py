from pathlib import Path
from uuid import uuid4

import aiofiles  # type: ignore[import-untyped]
import anyio.to_thread
from fastapi import UploadFile

from api.config import get_settings
from api.meeting_files.exceptions import FileTooLargeError


class LocalStorageService:
    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.storage_root)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def max_size(self) -> int:
        return get_settings().max_file_size

    async def save(self, file: UploadFile, meeting_id: int) -> tuple[str, str, int]:
        """Save upload to disk chunk-by-chunk, return (relative_path, stored_filename, size)."""
        original_name = file.filename or "file"
        ext = Path(original_name).suffix.lower()
        stored_filename = f"{uuid4().hex}{ext}"
        relative_path = f"meetings/{meeting_id}/{stored_filename}"
        dest = self._root / relative_path
        await anyio.to_thread.run_sync(lambda: dest.parent.mkdir(parents=True, exist_ok=True))

        # Write to temp file first for atomicity
        tmp_path = dest.with_name(dest.name + ".tmp")

        size = 0
        try:
            async with aiofiles.open(tmp_path, "wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.max_size:
                        raise FileTooLargeError(
                            f"Файл слишком большой. Максимум {self.max_size // (1024 * 1024)} МБ"
                        )
                    await out.write(chunk)
        except Exception:
            exists = await anyio.to_thread.run_sync(tmp_path.exists)
            if exists:
                await anyio.to_thread.run_sync(lambda: tmp_path.unlink(missing_ok=True))
            raise
        else:
            await anyio.to_thread.run_sync(lambda: tmp_path.rename(dest))

        return relative_path, stored_filename, size

    async def delete(self, relative_path: str) -> None:
        # defense-in-depth: prevent traversal even though path is from DB
        if ".." in Path(relative_path).parts:
            return
        path = self._root / relative_path
        exists = await anyio.to_thread.run_sync(path.exists)
        if exists:
            await anyio.to_thread.run_sync(lambda: path.unlink(missing_ok=True))

    def absolute_path(self, relative_path: str) -> Path:
        if ".." in Path(relative_path).parts:
            raise ValueError("Invalid storage path")
        return self._root / relative_path
