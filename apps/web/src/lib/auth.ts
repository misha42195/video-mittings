const ACCESS_TOKEN_KEY = "access_token";
const USER_EMAIL_KEY = "user_email";

export type Session = {
  token: string;
  email: string;
};

export function saveSession(token: string, email: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  localStorage.setItem(USER_EMAIL_KEY, email);
}

export function getSession(): Session | null {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  const email = localStorage.getItem(USER_EMAIL_KEY);
  if (!token || !email) return null;
  return { token, email };
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
}
