from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import EmailAlreadyRegisteredError
from api.models import Meeting, User
from api.schemas import Token
from api.security import create_access_token, hash_password


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str


class RegisterUserHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, command: RegisterUserCommand) -> Token:
        existing = await self._db.scalar(select(User).where(User.email == command.email))
        if existing is not None:
            raise EmailAlreadyRegisteredError(command.email)

        user = User(email=command.email, hashed_password=hash_password(command.password))
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        return Token(access_token=create_access_token(subject=str(user.id)))


@dataclass(frozen=True, slots=True)
class CreateMeetingCommand:
    owner_id: int
    title: str
    scheduled_at: datetime
    description: str | None = None


class CreateMeetingHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, command: CreateMeetingCommand) -> Meeting:
        meeting = Meeting(
            owner_id=command.owner_id,
            title=command.title,
            description=command.description,
            scheduled_at=command.scheduled_at,
        )
        self._db.add(meeting)
        await self._db.commit()
        await self._db.refresh(meeting)

        return meeting
