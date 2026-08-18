import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Регистрация",
  description: "Создать аккаунт: email и пароль",
};

export default function RegisterLayout({ children }: LayoutProps<"/register">) {
  return children;
}
