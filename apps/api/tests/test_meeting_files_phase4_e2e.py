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
        json={"title": "Phase4 meeting", "scheduled_at": "2026-08-24T10:00:00Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def test_full_lifecycle_upload_list_download_delete_verify_absence(
    client: AsyncClient, auth_headers: dict[str, str], db: AsyncSession
) -> None:
    """PRD 7 критериев: загрузка→БД/диск→список→стрим→удаление→отсутствие"""
    meeting_id = await _create_meeting(client, auth_headers)

    # empty initially
    resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # upload
    content = b"%PDF-1.4 phase4 full lifecycle test"
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("report.pdf", content, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    file_id = body["id"]
    assert body["original_filename"] == "report.pdf"
    assert body["size"] == len(content)

    # DB and disk
    db_file = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file is not None
    storage_root = Path(get_settings().storage_root)
    assert (storage_root / db_file.storage_path).exists()
    assert (storage_root / db_file.storage_path).read_bytes() == content

    # list returns it
    resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == file_id

    # download streams (FileResponse) — check headers and content
    resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.content == content
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert "report.pdf" in resp.headers["content-disposition"]

    # delete
    resp = await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 204

    # verify absence in DB, disk, list, download
    db_file_after = await db.scalar(select(MeetingFile).where(MeetingFile.id == file_id))
    assert db_file_after is None
    assert not (storage_root / db_file.storage_path).exists()

    resp = await client.get(f"/meetings/{meeting_id}/files", headers=auth_headers)
    assert resp.json() == []

    resp = await client.get(
        f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers
    )
    assert resp.status_code == 404

    resp = await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_negative_cases_unified_errors(
    client: AsyncClient,
    auth_headers: dict[str, str],
    register_user: AuthHeadersFactory,
    monkeypatch: pytest.MonkeyPatch,
    db: AsyncSession,
) -> None:
    meeting_id = await _create_meeting(client, auth_headers)

    # invalid type -> 400 with unified text
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("bad.exe", b"MZ", "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Недопустимый тип" in resp.json()["detail"]

    # too large -> 400
    settings = get_settings()
    monkeypatch.setattr(settings, "max_file_size", 10)
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("big.pdf", b"0123456789ABC", "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "слишком большой" in resp.json()["detail"].lower()

    # foreign -> 404 (not 403) for all endpoints
    other_headers = await register_user("phase4-other@example.com")
    for url, method in [
        (f"/meetings/{meeting_id}/files", "GET"),
        (f"/meetings/{meeting_id}/files", "POST"),
        (f"/meetings/{meeting_id}/files/999/download", "GET"),
        (f"/meetings/{meeting_id}/files/999", "DELETE"),
    ]:
        if method == "GET":
            r = await client.get(url, headers=other_headers)
        elif method == "POST":
            r = await client.post(
                url,
                files={"file": ("a.pdf", b"a", "application/pdf")},
                headers=other_headers,
            )
        else:
            r = await client.delete(url, headers=other_headers)
        assert r.status_code == 404, f"{method} {url} should be 404 for foreign"

    # empty file -> 400
    monkeypatch.setattr(settings, "max_file_size", 100 * 1024 * 1024)
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Пустой" in resp.json()["detail"]


async def test_streaming_large_file_not_loaded_into_memory(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """100MB boundary: 5MB file should stream via FileResponse without OOM"""
    meeting_id = await _create_meeting(client, auth_headers)
    # 5MB is enough to test chunked path without needing 100MB in CI
    large_content = b"a" * (5 * 1024 * 1024)
    resp = await client.post(
        f"/meetings/{meeting_id}/files",
        files={"file": ("large.pdf", large_content, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    file_id = resp.json()["id"]

    # download should return same content and be streamed (we check headers, not RAM usage)
    dl = await client.get(f"/meetings/{meeting_id}/files/{file_id}/download", headers=auth_headers)
    assert dl.status_code == 200
    assert int(dl.headers.get("content-length", "0")) == len(large_content)
    assert dl.content == large_content

    # cleanup
    await client.delete(f"/meetings/{meeting_id}/files/{file_id}", headers=auth_headers)
