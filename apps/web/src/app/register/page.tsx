"use client";

import { useRouter } from "next/navigation";
import { useState, type SVGProps } from "react";
import {
  Alert,
  Button,
  Card,
  Description,
  FieldError,
  Form,
  Input,
  InputGroup,
  Label,
  TextField,
  ToggleButton,
} from "@heroui/react";

import { ApiError, registerUser } from "@/lib/api";

// Practical email check: RFC 5321-ish local part + domain made of valid
// labels (no leading/trailing hyphen, 1-63 chars each) with at least one dot.
const EMAIL_PATTERN =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

// Latin letters, digits, and standard ASCII punctuation — blocks spaces,
// Cyrillic, emoji, and other non-ASCII input in the password field.
const PASSWORD_DISALLOWED_CHARS = /[^\x21-\x7E]/g;

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

export default function RegisterPage() {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [passwordInput, setPasswordInput] = useState("");

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
      const token = await registerUser(email, password);
      localStorage.setItem("access_token", token.access_token);
      router.push("/");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setEmailError("Пользователь с таким email уже зарегистрирован");
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
            <Card.Title>Создать аккаунт</Card.Title>
            <Card.Description>
              Введите email и пароль, чтобы зарегистрироваться
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

                <TextField
                  isRequired
                  minLength={8}
                  name="password"
                  onChange={(value) =>
                    setPasswordInput(
                      value.replace(PASSWORD_DISALLOWED_CHARS, ""),
                    )
                  }
                  type={showPassword ? "text" : "password"}
                  validate={(value) =>
                    value.length < 8
                      ? "Пароль должен содержать не менее 8 символов"
                      : null
                  }
                  value={passwordInput}
                >
                  <Label>Пароль</Label>
                  <InputGroup variant="secondary">
                    <InputGroup.Input
                      autoComplete="new-password"
                      placeholder="Минимум 8 символов"
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
                  <Description>
                    Не менее 8 символов. Латиница, цифры и спецсимволы
                  </Description>
                  <FieldError />
                </TextField>
              </div>
            </Card.Content>

            <Card.Footer className="mt-2 flex flex-col gap-2">
              <Button
                className="h-11 w-full"
                isPending={isPending}
                type="submit"
              >
                {isPending ? "Регистрация..." : "Зарегистрироваться"}
              </Button>
            </Card.Footer>
          </Form>
        </Card>
      </div>
    </main>
  );
}
