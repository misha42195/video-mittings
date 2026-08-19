from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.users.exceptions import EmailAlreadyRegisteredError
from api.users.models import User
from api.users.security import hash_password


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    password: str


class CreateUserHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, command: CreateUserCommand) -> User:
        existing = await self._db.scalar(select(User).where(User.email == command.email))
        if existing is not None:
            raise EmailAlreadyRegisteredError(command.email)

        user = User(email=command.email, hashed_password=hash_password(command.password))
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)

        return user
