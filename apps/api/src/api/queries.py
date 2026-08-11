from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import InvalidCredentialsError
from api.models import User
from api.schemas import Token
from api.security import create_access_token, verify_password


@dataclass(frozen=True, slots=True)
class AuthenticateUserQuery:
    login: str
    password: str


class AuthenticateUserHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: AuthenticateUserQuery) -> Token:
        user = await self._db.scalar(select(User).where(User.email == query.login))
        if user is None or not verify_password(query.password, user.hashed_password):
            raise InvalidCredentialsError

        return Token(access_token=create_access_token(subject=str(user.id)))
