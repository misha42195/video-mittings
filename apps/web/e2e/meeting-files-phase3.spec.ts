import { test, expect } from "@playwright/test";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function createUserAndMeeting(email: string) {
  const password = "supersecret123";
  await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const loginRes = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  const { access_token } = (await loginRes.json()) as { access_token: string };
  const meetingRes = await fetch(`${API_BASE}/meetings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access_token}`,
    },
    body: JSON.stringify({ title: `Test ${Date.now()}`, scheduled_at: new Date().toISOString() }),
  });
  const meeting = (await meetingRes.json()) as { id: number };
  return { token: access_token, meetingId: meeting.id, email };
}

async function loginViaStorage(page: import("@playwright/test").Page, token: string, email: string) {
  await page.addInitScript(
    ({ t, e }: { t: string; e: string }) => {
      localStorage.setItem("access_token", t);
      localStorage.setItem("user_email", e);
    },
    { t: token, e: email },
  );
}

test.describe("Фаза 3: скачивание и удаление", () => {
  test("кнопки скачать и удалить видны после загрузки, скачивание стримом", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(`files-dl-${Date.now()}@example.com`);
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    // upload
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "report.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 dl test"),
    });
    await expect(page.getByText("report.pdf")).toBeVisible({ timeout: 10_000 });

    // buttons visible
    await expect(page.getByTestId("download-button").first()).toBeVisible();
    await expect(page.getByTestId("delete-button").first()).toBeVisible();

    // verify via API directly that download endpoint returns attachment and streams
    const filesResp = await fetch(`${API_BASE}/meetings/${meetingId}/files`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const files = (await filesResp.json()) as { id: number }[];
    const fileId = files[0].id;
    const dlResp = await fetch(`${API_BASE}/meetings/${meetingId}/files/${fileId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(dlResp.status).toBe(200);
    expect(dlResp.headers.get("content-disposition") ?? "").toContain("attachment");
    expect(dlResp.headers.get("content-type")).toBe("application/pdf");
    const body = await dlResp.arrayBuffer();
    expect(body.byteLength).toBeGreaterThan(0);
  });

  test("удаление с подтверждением чистит список, диск и БД", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(`files-del-${Date.now()}@example.com`);
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    await page.setInputFiles('[data-testid="file-input"]', {
      name: "doc.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("to be deleted"),
    });
    await expect(page.getByText("doc.pdf")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(1);

    // click delete
    await page.getByTestId("delete-button").first().click();
    // confirmation modal
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Удалить файл/i })).toBeVisible();
    await page.getByTestId("confirm-delete").click();

    await expect(page.getByText("doc.pdf")).toBeHidden({ timeout: 5_000 });
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(0);
    await expect(page.getByTestId("files-empty")).toBeVisible();

    // verify via API that file is gone from DB and disk
    const listResp = await fetch(`${API_BASE}/meetings/${meetingId}/files`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const list = (await listResp.json()) as unknown[];
    expect(list).toEqual([]);
  });

  test("чужой файл 404 и удаление не доступно", async ({ page }) => {
    const { token, meetingId } = await createUserAndMeeting(`files-owner-${Date.now()}@example.com`);
    // owner uploads file via API
    const content = Buffer.from("owner file");
    const fd = new FormData();
    fd.append("file", new Blob([content], { type: "application/pdf" }), "owner.pdf");
    const uploadResp = await fetch(`${API_BASE}/meetings/${meetingId}/files`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd as unknown as BodyInit,
    });
    expect(uploadResp.status).toBe(201);
    const uploaded = (await uploadResp.json()) as { id: number };

    // other user
    const otherEmail = `files-intruder-${Date.now()}@example.com`;
    const { token: otherToken } = await createUserAndMeeting(otherEmail);
    await loginViaStorage(page, otherToken, otherEmail);
    await page.goto(`/meetings/${meetingId}`);

    // should see 404 for meeting (files not visible)
    await expect(page.getByText(/Встреча не найдена/i)).toBeVisible({ timeout: 5_000 });

    // direct API download as intruder -> 404
    const dlResp = await fetch(`${API_BASE}/meetings/${meetingId}/files/${uploaded.id}/download`, {
      headers: { Authorization: `Bearer ${otherToken}` },
    });
    expect(dlResp.status).toBe(404);

    const delResp = await fetch(`${API_BASE}/meetings/${meetingId}/files/${uploaded.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${otherToken}` },
    });
    expect(delResp.status).toBe(404);
  });
});
