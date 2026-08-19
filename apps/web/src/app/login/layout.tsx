import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Вход",
  description: "Войти по email и паролю",
};

export default function LoginLayout({ children }: LayoutProps<"/login">) {
  return children;
}
