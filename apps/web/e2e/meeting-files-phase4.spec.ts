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
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${access_token}` },
    body: JSON.stringify({ title: `Phase4 ${Date.now()}`, scheduled_at: new Date().toISOString() }),
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

test.describe("Фаза 4: полировка — полный сценарий и состояния", () => {
  test("полный сценарий загрузка→список→скачивание→удаление→пусто", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(`phase4-full-${Date.now()}@example.com`);
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    // empty state initially
    await expect(page.getByTestId("files-empty")).toBeVisible();
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(0);

    // upload
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "report.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 phase4 lifecycle"),
    });
    await expect(page.getByText("report.pdf")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(1);

    // list after reload still shows file (persisted)
    await page.reload();
    await expect(page.getByText("report.pdf")).toBeVisible({ timeout: 5_000 });

    // download via API (verify stream) — UI download button should exist
    await expect(page.getByTestId("download-button").first()).toBeVisible();
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

    // delete via UI with confirmation
    await page.getByTestId("delete-button").first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByTestId("confirm-delete").click();
    await expect(page.getByText("report.pdf")).toBeHidden({ timeout: 5_000 });
    await expect(page.getByTestId("files-empty")).toBeVisible();

    // verify absence via API
    const listAfter = await (await fetch(`${API_BASE}/meetings/${meetingId}/files`, { headers: { Authorization: `Bearer ${token}` } })).json();
    expect(listAfter).toEqual([]);
  });

  test("негативные кейсы: 400 и 404", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(`phase4-neg-${Date.now()}@example.com`);
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    // invalid type via UI -> 400
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "bad.exe",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("MZ"),
    });
    await expect(page.getByTestId("upload-error")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByTestId("upload-error")).toContainText(/Недопустимый тип/i);
    await expect(page.getByTestId("files-empty")).toBeVisible();

    // too large via UI (client validation) -> 400 — tested via monkeypatch in backend, here just check 404 for foreign
    const other = await createUserAndMeeting(`phase4-neg-other-${Date.now()}@example.com`);
    await loginViaStorage(page, other.token, other.email);
    await page.goto(`/meetings/${meetingId}`);
    await expect(page.getByText(/Встреча не найдена/i)).toBeVisible({ timeout: 5_000 });
  });

  test("состояния загрузки, пусто, ошибка сети", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(`phase4-states-${Date.now()}@example.com`);
    await loginViaStorage(page, token, email);

    // intercept files list to simulate slow loading
    await page.route(`**/meetings/${meetingId}/files`, async (route) => {
      if (route.request().method() === "GET") {
        await new Promise((r) => setTimeout(r, 800));
      }
      await route.continue();
    });
    await page.goto(`/meetings/${meetingId}`);
    // loading spinner should appear
    await expect(page.getByLabel("Загрузка файлов")).toBeVisible();
    await expect(page.getByTestId("files-empty")).toBeVisible({ timeout: 5_000 });

    // network error: abort files request
    await page.unrouteAll({ behavior: "wait" });
    await page.route(`**/meetings/${meetingId}/files`, (route) => route.abort("failed"));
    await page.reload();
    // should show error, not empty
    await expect(page.getByText(/Не удалось загрузить файлы|Сеть недоступна/i)).toBeVisible({ timeout: 5_000 });

    // restore and verify empty still works after error
    await page.unrouteAll({ behavior: "wait" });
    await page.reload();
    await expect(page.getByTestId("files-empty")).toBeVisible({ timeout: 5_000 });
  });
});
