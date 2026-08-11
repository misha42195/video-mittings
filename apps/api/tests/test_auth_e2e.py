import jwt
from httpx import AsyncClient

from api.config import get_settings


async def test_register_returns_201_and_jwt_access_token(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "bob@example.com", "password": "supersecret123"}

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "shortpw@example.com", "password": "short"},
    )

    assert response.status_code == 422


async def test_login_with_email_as_login_and_correct_password_returns_jwt(
    client: AsyncClient,
) -> None:
    await client.post(
        "/auth/register",
        json={"email": "carol@example.com", "password": "supersecret123"},
    )

    response = await client.post(
        "/auth/login",
        data={"username": "carol@example.com", "password": "supersecret123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "dave@example.com", "password": "supersecret123"},
    )

    response = await client.post(
        "/auth/login",
        data={"username": "dave@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_login_rejects_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": "unknown@example.com", "password": "whatever123"},
    )

    assert response.status_code == 401


async def test_access_token_subject_is_the_registered_users_id(client: AsyncClient) -> None:
    register_response = await client.post(
        "/auth/register",
        json={"email": "erin@example.com", "password": "supersecret123"},
    )
    register_token = register_response.json()["access_token"]

    login_response = await client.post(
        "/auth/login",
        data={"username": "erin@example.com", "password": "supersecret123"},
    )
    login_token = login_response.json()["access_token"]

    settings = get_settings()
    register_payload = jwt.decode(
        register_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    login_payload = jwt.decode(
        login_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )

    assert register_payload["sub"] == login_payload["sub"]
    assert register_payload["sub"].isdigit()
