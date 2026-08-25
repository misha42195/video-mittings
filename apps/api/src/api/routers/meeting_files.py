from typing import Annotated

import anyio.to_thread
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser
from api.database import get_db
from api.exceptions import MeetingNotFoundError
from api.meeting_files.commands import (
    DeleteMeetingFileCommand,
    DeleteMeetingFileHandler,
    UploadMeetingFileCommand,
    UploadMeetingFileHandler,
)
from api.meeting_files.exceptions import (
    FileNotFoundError,
    FileTooLargeError,
    FileTypeNotAllowedError,
)
from api.meeting_files.queries import (
    GetMeetingFileHandler,
    GetMeetingFileQuery,
    ListMeetingFilesHandler,
    ListMeetingFilesQuery,
)
from api.meeting_files.schemas import MeetingFileResponse
from api.meeting_files.storage import LocalStorageService

router = APIRouter(prefix="/meetings", tags=["meeting-files"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/{meeting_id}/files",
    response_model=MeetingFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meeting_file(
    meeting_id: int,
    file: Annotated[UploadFile, File(...)],
    db: DbDep,
    current_user: CurrentUser,
) -> MeetingFileResponse:
    command = UploadMeetingFileCommand(
        meeting_id=meeting_id, owner_id=current_user.id, upload_file=file
    )
    try:
        meeting_file = await UploadMeetingFileHandler(db).handle(command)
    except MeetingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found") from exc
    except FileTypeNotAllowedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return MeetingFileResponse.model_validate(meeting_file)


@router.get("/{meeting_id}/files", response_model=list[MeetingFileResponse])
async def list_meeting_files(
    meeting_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> list[MeetingFileResponse]:
    query = ListMeetingFilesQuery(meeting_id=meeting_id, owner_id=current_user.id)
    try:
        files = await ListMeetingFilesHandler(db).handle(query)
    except MeetingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found") from exc
    return [MeetingFileResponse.model_validate(f) for f in files]


@router.get("/{meeting_id}/files/{file_id}/download")
async def download_meeting_file(
    meeting_id: int,
    file_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> FileResponse:
    query = GetMeetingFileQuery(meeting_id=meeting_id, file_id=file_id, owner_id=current_user.id)
    try:
        meeting_file = await GetMeetingFileHandler(db).handle(query)
    except MeetingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found") from exc

    storage = LocalStorageService()
    abs_path = storage.absolute_path(meeting_file.storage_path)
    exists = await anyio.to_thread.run_sync(abs_path.exists)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")

    return FileResponse(
        path=abs_path,
        media_type=meeting_file.content_type,
        filename=meeting_file.original_filename,
    )


@router.delete("/{meeting_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_file(
    meeting_id: int,
    file_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> None:
    command = DeleteMeetingFileCommand(
        meeting_id=meeting_id, file_id=file_id, owner_id=current_user.id
    )
    try:
        await DeleteMeetingFileHandler(db).handle(command)
    except MeetingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found") from exc
