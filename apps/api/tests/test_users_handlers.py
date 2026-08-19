import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.users.commands import CreateUserCommand, CreateUserHandler
from api.users.exceptions import EmailAlreadyRegisteredError
from api.users.queries import (
    GetUserByEmailHandler,
    GetUserByEmailQuery,
    GetUserByIdHandler,
    GetUserByIdQuery,
)


async def test_create_user_handler_creates_user_with_hashed_password(db: AsyncSession) -> None:
    user = await CreateUserHandler(db).handle(
        CreateUserCommand(email="new-user@example.com", password="supersecret123")
    )

    assert user.id is not None
    assert user.email == "new-user@example.com"
    assert user.hashed_password != "supersecret123"


async def test_create_user_handler_rejects_duplicate_email(db: AsyncSession) -> None:
    command = CreateUserCommand(email="dup-user@example.com", password="supersecret123")
    await CreateUserHandler(db).handle(command)

    with pytest.raises(EmailAlreadyRegisteredError):
        await CreateUserHandler(db).handle(command)


async def test_get_user_by_email_handler_finds_existing_user(db: AsyncSession) -> None:
    created = await CreateUserHandler(db).handle(
        CreateUserCommand(email="find-me@example.com", password="supersecret123")
    )

    found = await GetUserByEmailHandler(db).handle(GetUserByEmailQuery(email="find-me@example.com"))

    assert found is not None
    assert found.id == created.id


async def test_get_user_by_email_handler_returns_none_for_unknown_email(db: AsyncSession) -> None:
    found = await GetUserByEmailHandler(db).handle(GetUserByEmailQuery(email="ghost@example.com"))

    assert found is None


async def test_get_user_by_id_handler_finds_existing_user(db: AsyncSession) -> None:
    created = await CreateUserHandler(db).handle(
        CreateUserCommand(email="by-id@example.com", password="supersecret123")
    )

    found = await GetUserByIdHandler(db).handle(GetUserByIdQuery(user_id=created.id))

    assert found is not None
    assert found.email == "by-id@example.com"


async def test_get_user_by_id_handler_returns_none_for_unknown_id(db: AsyncSession) -> None:
    found = await GetUserByIdHandler(db).handle(GetUserByIdQuery(user_id=999999))

    assert found is None
