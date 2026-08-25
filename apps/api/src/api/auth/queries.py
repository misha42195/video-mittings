from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.exceptions import InvalidCredentialsError
from api.auth.schemas import Token
from api.auth.security import create_access_token
from api.users.queries import GetUserByEmailHandler, GetUserByEmailQuery
from api.users.security import verify_password


@dataclass(frozen=True, slots=True)
class AuthenticateUserQuery:
    login: str
    password: str


class AuthenticateUserHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: AuthenticateUserQuery) -> Token:
        user = await GetUserByEmailHandler(self._db).handle(GetUserByEmailQuery(email=query.login))
        if user is None or not verify_password(query.password, user.hashed_password):
            raise InvalidCredentialsError()

        return Token(access_token=create_access_token(subject=str(user.id)))
