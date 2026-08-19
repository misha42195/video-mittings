from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.users.models import User


@dataclass(frozen=True, slots=True)
class GetUserByEmailQuery:
    email: str


class GetUserByEmailHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: GetUserByEmailQuery) -> User | None:
        user: User | None = await self._db.scalar(select(User).where(User.email == query.email))
        return user


@dataclass(frozen=True, slots=True)
class GetUserByIdQuery:
    user_id: int


class GetUserByIdHandler:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle(self, query: GetUserByIdQuery) -> User | None:
        return await self._db.get(User, query.user_id)
