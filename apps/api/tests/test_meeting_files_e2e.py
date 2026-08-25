from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
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


# --- POST /meetings/{id}/files ---


async def test_upload_file_success_and_persisted_on_disk_and_db(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    content = b"%PDF-1.4 fake pdf content"
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("report.pdf", content, "application/pdf")},
        headers=auth_headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["meeting_id"] == meeting_id
    assert body["original_filename"] == "report.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size"] == len(content)
    assert "id" in body
    assert "created_at" in body
    assert "storage_path" not in body

    # DB check
    file_id = body["id"]
    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    assert db_file.meeting_id == meeting_id
    assert db_file.size == len(content)

    # Disk check
    storage_root = get_settings().storage_root
    stored_path = Path(storage_root) / db_file.storage_path
    assert stored_path.exists()
    assert stored_path.read_bytes() == content


async def test_upload_file_rejects_invalid_type(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("malware.exe", b"MZ fake", "application/octet-stream")},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert "Недопустимый тип" in resp.json()["detail"]


async def test_upload_file_rejects_too_large(
    client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    db: AsyncSession,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    # Patch max size to 10 bytes to avoid sending 100MB payload
    settings = get_settings()
    monkeypatch.setattr(settings, "max_file_size", 10)

    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("report.pdf", b"0123456789ABCDEF", "application/pdf")},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "слишком большой" in detail or "too large" in detail

    # Ensure no orphan file persisted in DB or on disk after rejection
    files = await db.scalars(select(MeetingFile).where(MeetingFile.meeting_id == meeting_id))
    assert list(files.all()) == []
    storage_root = Path(get_settings().storage_root)
    meetings_dir = storage_root / f"meetings/{meeting_id}"
    if meetings_dir.exists():
        assert not any(meetings_dir.iterdir())


async def test_upload_file_rejects_missing_extension(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("noext", b"hello", "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_upload_file_returns_404_for_foreign_meeting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    other_headers = await register_user("files-other@example.com")

    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("report.pdf", b"content", "application/pdf")},
        headers=other_headers,
    )

    assert resp.status_code == 404


async def test_upload_file_returns_404_for_nonexistent_meeting(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/meetings/999999/files",
        files={"file": ("report.pdf", b"content", "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_upload_file_requires_authentication(client: AsyncClient) -> None:
    resp = await client.post(
        "/meetings/1/files",
        files={"file": ("report.pdf", b"content", "application/pdf")},
    )
    assert resp.status_code == 401


# --- GET /meetings/{id}/files ---


async def test_list_files_empty_initially(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_files_returns_uploaded_file(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("doc.pdf", b"pdf content", "application/pdf")},
        headers=auth_headers,
    )

    resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "doc.pdf"
    assert data[0]["meeting_id"] == meeting_id


async def test_list_files_returns_404_for_foreign_meeting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)
    other_headers = await register_user("files-list-other@example.com")

    resp = await client.get(f"/meetings/{meeting_id}/files", headers=other_headers)

    assert resp.status_code == 404


async def test_list_files_requires_authentication(client: AsyncClient) -> None:
    resp = await client.get("/meetings/1/files")
    assert resp.status_code == 401


# --- Validation edge cases ---


@pytest.mark.parametrize(
    "filename,content_type",
    [
        ("video.mp4", "video/mp4"),
        ("clip.mov", "video/quicktime"),
        ("audio.wav", "audio/wav"),
        ("song.mp3", "audio/mpeg"),
        ("paper.pdf", "application/pdf"),
        ("report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ],
)
async def test_upload_allowed_types(
    client: AsyncClient,
    auth_headers: dict[str, str],
    filename: str,
    content_type: str,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": (filename, b"fake content", content_type)},
        headers=auth_headers,
    )

    assert resp.status_code == 201, f"failed for {filename} {content_type}: {resp.text}"
