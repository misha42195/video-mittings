const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Token = {
  access_token: string;
  token_type: string;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type Meeting = {
  id: number;
  title: string;
  description: string | null;
  scheduled_at: string;
  created_at: string;
};

export async function registerUser(
  email: string,
  password: string,
): Promise<Token> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    throw new ApiError(await extractErrorMessage(res), res.status);
  }

  return (await res.json()) as Token;
}

export async function loginUser(
  email: string,
  password: string,
): Promise<Token> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });

  if (!res.ok) {
    throw new ApiError(await extractErrorMessage(res), res.status);
  }

  return (await res.json()) as Token;
}

export async function listMeetings(token: string): Promise<Meeting[]> {
  const res = await fetch(`${API_BASE_URL}/meetings`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new ApiError(await extractErrorMessage(res), res.status);
  }

  return (await res.json()) as Meeting[];
}

export async function createMeeting(
  token: string,
  meeting: { title: string; description: string | null; scheduled_at: string },
): Promise<Meeting> {
  const res = await fetch(`${API_BASE_URL}/meetings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(meeting),
  });

  if (!res.ok) {
    throw new ApiError(await extractErrorMessage(res), res.status);
  }

  return (await res.json()) as Meeting;
}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item
              ? String(item.msg)
              : String(item),
          )
          .join("; ");
      }
    }
  } catch {
    return "Не удалось разобрать ответ сервера";
  }
  return "Что-то пошло не так, попробуйте ещё раз";
}
