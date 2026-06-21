import type { Metadata } from "next";

import { AuthShell } from "@/components/auth/auth-shell";
import { AuthForm } from "@/components/auth/auth-form";

export const metadata: Metadata = {
  title: "Log in — OptiMiles",
  description: "Log in to your OptiMiles reward strategy account.",
};

export default function LoginPage() {
  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to pick up your reward strategy where you left off."
    >
      <AuthForm mode="login" />
    </AuthShell>
  );
}
