import { test, expect } from "@playwright/test";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function createUserAndMeeting(email: string) {
  const password = "supersecret123";
  // register
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
    body: JSON.stringify({
      title: `Test ${Date.now()}`,
      scheduled_at: new Date().toISOString(),
    }),
  });
  const meeting = (await meetingRes.json()) as { id: number };
  return { token: access_token, meetingId: meeting.id, email, password };
}

async function loginViaStorage(
  page: import("@playwright/test").Page,
  token: string,
  email: string,
) {
  await page.addInitScript(
    ({ t, e }: { t: string; e: string }) => {
      localStorage.setItem("access_token", t);
      localStorage.setItem("user_email", e);
    },
    { t: token, e: email },
  );
}

test.describe("Фаза 2: секция Файлы", () => {
  test("секция Файлы рендерится на странице встречи", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(
      `files-render-${Date.now()}@example.com`,
    );
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    await expect(
      page.getByRole("heading", { name: /Файлы/i }).first(),
    ).toBeVisible();
    await expect(page.getByTestId("files-empty")).toBeVisible();
    await expect(page.getByTestId("file-input")).toBeHidden();
    await expect(
      page.getByRole("button", { name: /Выбрать файл/i }),
    ).toBeVisible();
  });

  test("загрузка с прогресс-баром и обновление списка", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(
      `files-upload-${Date.now()}@example.com`,
    );
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    await expect(page.getByTestId("files-empty")).toBeVisible();

    // Prepare file and start upload
    const fileBuffer = Buffer.from("%PDF-1.4 fake pdf for e2e");
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "report.pdf",
      mimeType: "application/pdf",
      buffer: fileBuffer,
    });

    // progress should appear
    await expect(page.getByTestId("upload-progress")).toBeVisible();
    // after upload, file appears in list without reload
    await expect(page.getByText("report.pdf")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("files-empty")).toBeHidden();
    await expect(page.getByTestId("upload-progress")).toBeHidden({
      timeout: 5_000,
    });
  });

  test("ошибка 400 показывается для недопустимого типа", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(
      `files-400-${Date.now()}@example.com`,
    );
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    const exeBuffer = Buffer.from("MZ fake exe");
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "malware.exe",
      mimeType: "application/octet-stream",
      buffer: exeBuffer,
    });

    await expect(page.getByTestId("upload-error")).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByTestId("upload-error")).toContainText(
      /Недопустимый тип/i,
    );
    // empty state should remain, no file added
    await expect(page.getByTestId("files-empty")).toBeVisible();
    await expect(page.getByText("malware.exe")).toBeHidden();
  });

  test("список обновляется без перезагрузки", async ({ page }) => {
    const { token, meetingId, email } = await createUserAndMeeting(
      `files-list-${Date.now()}@example.com`,
    );
    await loginViaStorage(page, token, email);
    await page.goto(`/meetings/${meetingId}`);

    // initially empty
    await expect(page.getByTestId("files-empty")).toBeVisible();
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(0);

    // upload first file
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "doc.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("pdf content"),
    });
    await expect(page.getByText("doc.pdf")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(1);

    // upload second file should append
    await page.setInputFiles('[data-testid="file-input"]', {
      name: "video.mp4",
      mimeType: "video/mp4",
      buffer: Buffer.from("mp4 fake"),
    });
    await expect(page.getByText("video.mp4")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-testid="file-item"]')).toHaveCount(2);
  });
});
