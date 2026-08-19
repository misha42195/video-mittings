from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import CurrentUser
from api.commands import CreateMeetingCommand, CreateMeetingHandler
from api.database import get_db
from api.exceptions import MeetingNotFoundError
from api.queries import (
    GetMeetingHandler,
    GetMeetingQuery,
    ListMeetingsHandler,
    ListMeetingsQuery,
)
from api.schemas import MeetingCreate, MeetingResponse

router = APIRouter(prefix="/meetings", tags=["meetings"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate, db: DbDep, current_user: CurrentUser
) -> MeetingResponse:
    command = CreateMeetingCommand(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        scheduled_at=payload.scheduled_at,
    )
    meeting = await CreateMeetingHandler(db).handle(command)
    return MeetingResponse.model_validate(meeting)


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(db: DbDep, current_user: CurrentUser) -> list[MeetingResponse]:
    query = ListMeetingsQuery(owner_id=current_user.id)
    meetings = await ListMeetingsHandler(db).handle(query)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int, db: DbDep, current_user: CurrentUser) -> MeetingResponse:
    query = GetMeetingQuery(meeting_id=meeting_id, owner_id=current_user.id)
    try:
        meeting = await GetMeetingHandler(db).handle(query)
    except MeetingNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found") from exc
    return MeetingResponse.model_validate(meeting)
