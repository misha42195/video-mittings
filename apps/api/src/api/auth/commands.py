from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.schemas import Token
from api.auth.security import create_access_token
from api.users.commands import CreateUserCommand, CreateUserHandler


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str


class RegisterUserHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, command: RegisterUserCommand) -> Token:
        user = await CreateUserHandler(self._db).handle(
            CreateUserCommand(email=command.email, password=command.password)
        )
        return Token(access_token=create_access_token(subject=str(user.id)))
