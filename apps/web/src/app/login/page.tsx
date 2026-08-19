"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type SVGProps } from "react";
import {
  Alert,
  Button,
  Card,
  FieldError,
  Form,
  Input,
  InputGroup,
  Label,
  TextField,
  ToggleButton,
} from "@heroui/react";

import { ApiError, loginUser } from "@/lib/api";
import { saveSession } from "@/lib/auth";

// Practical email check: RFC 5321-ish local part + domain made of valid
// labels (no leading/trailing hyphen, 1-63 chars each) with at least one dot.
const EMAIL_PATTERN =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

function EyeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      viewBox="0 0 24 24"
      {...props}
    >
      <path d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      viewBox="0 0 24 24"
      {...props}
    >
      <path d="M3 3l18 18" />
      <path d="M10.58 10.58a2.25 2.25 0 0 0 2.84 2.84" />
      <path d="M9.32 4.86A9.77 9.77 0 0 1 12 4.5c6 0 9.75 7.5 9.75 7.5a15.9 15.9 0 0 1-3.31 4.24M6.32 6.32C3.68 8.05 2.25 10.5 2.25 10.5S6 18 12 18a9.7 9.7 0 0 0 3.02-.49" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);

    const formData = new FormData(e.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    if (!EMAIL_PATTERN.test(email)) {
      setEmailError("Введите корректный email");
      return;
    }
    setEmailError(null);

    setIsPending(true);
    try {
      const token = await loginUser(email, password);
      saveSession(token.access_token, email);
      router.push("/");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError("Неверный email или пароль");
      } else if (error instanceof ApiError) {
        setFormError(error.message);
      } else {
        setFormError(
          "Не удалось подключиться к серверу. Проверьте соединение и попробуйте снова.",
        );
      }
    } finally {
      setIsPending(false);
    }
  };

  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-12">
      <div className="relative w-full max-w-md">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-16 -left-16 size-72 rounded-full bg-accent/25 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -bottom-16 size-72 rounded-full bg-accent/15 blur-3xl"
        />

        <Card className="relative w-full">
          <Card.Header>
            <Card.Title>Вход</Card.Title>
            <Card.Description>
              Введите email и пароль, чтобы войти
            </Card.Description>
          </Card.Header>

          <Form className="contents" onSubmit={onSubmit}>
            <Card.Content>
              <div className="flex flex-col gap-4">
                {formError ? (
                  <Alert status="danger">
                    <Alert.Indicator />
                    <Alert.Content>
                      <Alert.Description>{formError}</Alert.Description>
                    </Alert.Content>
                  </Alert>
                ) : null}

                <TextField
                  isRequired
                  isInvalid={Boolean(emailError)}
                  name="email"
                  type="email"
                  onBlur={(e) => {
                    const value = e.target.value;
                    if (value) {
                      setEmailError(
                        EMAIL_PATTERN.test(value)
                          ? null
                          : "Введите корректный email",
                      );
                    }
                  }}
                  onChange={() => setEmailError(null)}
                >
                  <Label>Email</Label>
                  <Input
                    autoComplete="email"
                    placeholder="you@example.com"
                    variant="secondary"
                  />
                  {emailError ? (
                    <FieldError>{emailError}</FieldError>
                  ) : (
                    <FieldError />
                  )}
                </TextField>

                <TextField isRequired name="password">
                  <Label>Пароль</Label>
                  <InputGroup variant="secondary">
                    <InputGroup.Input
                      autoComplete="current-password"
                      placeholder="Введите пароль"
                      type={showPassword ? "text" : "password"}
                    />
                    <InputGroup.Suffix>
                      <ToggleButton
                        aria-label={
                          showPassword ? "Скрыть пароль" : "Показать пароль"
                        }
                        className="size-11"
                        isIconOnly
                        isSelected={showPassword}
                        onChange={setShowPassword}
                        size="lg"
                        variant="ghost"
                      >
                        {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                      </ToggleButton>
                    </InputGroup.Suffix>
                  </InputGroup>
                  <FieldError />
                </TextField>
              </div>
            </Card.Content>

            <Card.Footer className="mt-2 flex flex-col gap-3">
              <Button
                className="h-11 w-full"
                isPending={isPending}
                type="submit"
              >
                {isPending ? "Вход..." : "Войти"}
              </Button>
              <p className="text-center text-sm text-muted">
                Нет аккаунта?{" "}
                <Link className="font-medium text-link" href="/register">
                  Зарегистрироваться
                </Link>
              </p>
            </Card.Footer>
          </Form>
        </Card>
      </div>
    </main>
  );
}
