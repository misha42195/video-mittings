from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser
from api.database import get_db
from api.exceptions import MeetingNotFoundError
from api.meeting_files.commands import UploadMeetingFileCommand, UploadMeetingFileHandler
from api.meeting_files.exceptions import FileTooLargeError, FileTypeNotAllowedError
from api.meeting_files.queries import ListMeetingFilesHandler, ListMeetingFilesQuery
from api.meeting_files.schemas import MeetingFileResponse

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
