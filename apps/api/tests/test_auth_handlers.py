import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.commands import RegisterUserCommand, RegisterUserHandler
from api.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from api.queries import AuthenticateUserHandler, AuthenticateUserQuery


async def test_register_user_handler_creates_user_and_returns_token(db: AsyncSession) -> None:
    token = await RegisterUserHandler(db).handle(
        RegisterUserCommand(email="handler@example.com", password="supersecret123")
    )

    assert token.token_type == "bearer"
    assert token.access_token


async def test_register_user_handler_rejects_duplicate_email(db: AsyncSession) -> None:
    command = RegisterUserCommand(email="dup-handler@example.com", password="supersecret123")
    await RegisterUserHandler(db).handle(command)

    with pytest.raises(EmailAlreadyRegisteredError):
        await RegisterUserHandler(db).handle(command)


async def test_authenticate_user_handler_returns_token_for_valid_credentials(
    db: AsyncSession,
) -> None:
    await RegisterUserHandler(db).handle(
        RegisterUserCommand(email="auth-handler@example.com", password="supersecret123")
    )

    token = await AuthenticateUserHandler(db).handle(
        AuthenticateUserQuery(login="auth-handler@example.com", password="supersecret123")
    )

    assert token.access_token


async def test_authenticate_user_handler_rejects_wrong_password(db: AsyncSession) -> None:
    await RegisterUserHandler(db).handle(
        RegisterUserCommand(email="wrongpw-handler@example.com", password="supersecret123")
    )

    with pytest.raises(InvalidCredentialsError):
        await AuthenticateUserHandler(db).handle(
            AuthenticateUserQuery(login="wrongpw-handler@example.com", password="wrong")
        )


async def test_authenticate_user_handler_rejects_unknown_login(db: AsyncSession) -> None:
    with pytest.raises(InvalidCredentialsError):
        await AuthenticateUserHandler(db).handle(
            AuthenticateUserQuery(login="ghost@example.com", password="whatever123")
        )
