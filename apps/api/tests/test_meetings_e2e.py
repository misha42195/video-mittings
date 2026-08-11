from collections.abc import Awaitable, Callable

from httpx import AsyncClient

AuthHeadersFactory = Callable[[str], Awaitable[dict[str, str]]]


async def test_create_meeting_returns_201_and_meeting_body(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/meetings",
        json={
            "title": "Sprint planning",
            "description": "Plan next sprint",
            "scheduled_at": "2026-08-20T10:00:00Z",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["title"] == "Sprint planning"
    assert body["description"] == "Plan next sprint"
    assert body["scheduled_at"] == "2026-08-20T10:00:00Z"


async def test_create_meeting_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/meetings",
        json={"title": "No auth meeting", "scheduled_at": "2026-08-20T10:00:00Z"},
    )

    assert response.status_code == 401


async def test_create_meeting_rejects_missing_title(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/meetings",
        json={"scheduled_at": "2026-08-20T10:00:00Z"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_list_meetings_returns_empty_list_when_none_created(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/meetings", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_meetings_returns_created_meeting(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await client.post(
        "/meetings",
        json={"title": "Retro", "scheduled_at": "2026-08-21T10:00:00Z"},
        headers=auth_headers,
    )

    response = await client.get("/meetings", headers=auth_headers)

    assert response.status_code == 200
    titles = [meeting["title"] for meeting in response.json()]
    assert titles == ["Retro"]


async def test_list_meetings_excludes_other_users_meetings(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    await client.post(
        "/meetings",
        json={"title": "Owner's meeting", "scheduled_at": "2026-08-22T10:00:00Z"},
        headers=auth_headers,
    )
    other_headers = await register_user("meetings-other@example.com")

    response = await client.get("/meetings", headers=other_headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_meetings_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/meetings")

    assert response.status_code == 401


async def test_get_meeting_by_id_returns_200_and_meeting_body(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_response = await client.post(
        "/meetings",
        json={"title": "1:1", "scheduled_at": "2026-08-23T10:00:00Z"},
        headers=auth_headers,
    )
    meeting_id = create_response.json()["id"]

    response = await client.get(f"/meetings/{meeting_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == meeting_id
    assert body["title"] == "1:1"


async def test_get_meeting_by_id_requires_authentication(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_response = await client.post(
        "/meetings",
        json={"title": "No auth get", "scheduled_at": "2026-08-24T10:00:00Z"},
        headers=auth_headers,
    )
    meeting_id = create_response.json()["id"]

    response = await client.get(f"/meetings/{meeting_id}")

    assert response.status_code == 401


async def test_get_nonexistent_meeting_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/meetings/999999", headers=auth_headers)

    assert response.status_code == 404


async def test_get_other_users_meeting_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    create_response = await client.post(
        "/meetings",
        json={"title": "Private", "scheduled_at": "2026-08-25T10:00:00Z"},
        headers=auth_headers,
    )
    meeting_id = create_response.json()["id"]
    other_headers = await register_user("meetings-intruder@example.com")

    response = await client.get(f"/meetings/{meeting_id}", headers=other_headers)

    assert response.status_code == 404
