from collections.abc import Awaitable, Callable
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.meeting_files.models import MeetingFile

AuthHeadersFactory = Callable[[str], Awaitable[dict[str, str]]]


async def _create_meeting(client: AsyncClient, auth_headers: dict[str, str]) -> int:
    resp = await client.post(
        "/meetings",
        json={"title": "Test meeting", "scheduled_at": "2026-08-24T10:00:00Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _upload_file(client: AsyncClient, auth_headers: dict[str, str], meeting_id: int) -> dict:
    content = b"%PDF-1.4 download test content"
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("report.pdf", content, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    # store content for verification
    body["_content"] = content  # type: ignore
    return body


# --- GET /download ---


async def test_download_success_stream_and_headers(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]
    content: bytes = uploaded["_content"]  # type: ignore

    resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers
    )

    assert resp.status_code == 200
    assert resp.content == content
    # FileResponse should set content-type and disposition without loading whole file into memory
    assert resp.headers.get("content-type") == "application/pdf"
    disp = resp.headers.get("content-disposition", "")
    assert "attachment" in disp
    assert "report.pdf" in disp

    # DB still exists
    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    # disk still exists
    storage_root = Path(get_settings().storage_root)
    assert (storage_root / db_file.storage_path).exists()


async def test_download_returns_404_for_foreign_meeting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]
    other_headers = await register_user("download-other@example.com")

    resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=other_headers
    )
    assert resp.status_code == 404


async def test_download_returns_404_for_nonexistent_file(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.get(f"/meetings/{meeting_id}/files/999999/download", headers=auth_headers)
    assert resp.status_code == 404


async def test_download_returns_404_when_file_missing_on_disk(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]

    # manually delete file from disk to simulate orphan
    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    storage_root = Path(get_settings().storage_root)
    (storage_root / db_file.storage_path).unlink(missing_ok=True)

    resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_download_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/meetings/1/files/1/download")
    assert resp.status_code == 401


# --- DELETE ---


async def test_delete_success_cleans_db_and_disk(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]

    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    storage_path = db_file.storage_path
    storage_root = Path(get_settings().storage_root)
    assert (storage_root / storage_path).exists()

    resp = await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 204

    # DB cleaned
    db_file_after = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file_after is None
    # disk cleaned
    assert not (storage_root / storage_path).exists()
    # list no longer contains file
    list_resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json() == []
    # download after delete 404
    dl_resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers
    )
    assert dl_resp.status_code == 404


async def test_delete_returns_404_for_foreign_meeting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]
    other_headers = await register_user("delete-other@example.com")

    resp = await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=other_headers)
    assert resp.status_code == 404


async def test_delete_returns_404_for_nonexistent_file(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.delete(f"/meetings/{meeting_id}/files/999999", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_requires_authentication(client: AsyncClient) -> None:
    resp = await client.delete("/meetings/1/files/1")
    assert resp.status_code == 401


async def test_delete_idempotent_when_file_already_missing_on_disk(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    uploaded = await _upload_file(client, auth_headers, meeting_id)
    file_id = uploaded["id"]

    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    storage_root = Path(get_settings().storage_root)
    (storage_root / db_file.storage_path).unlink(missing_ok=True)

    # delete should still succeed (204) even if file already missing on disk
    resp = await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 204
    db_file_after = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file_after is None
