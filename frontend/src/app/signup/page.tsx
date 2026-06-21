import type { Metadata } from "next";

import { AuthShell } from "@/components/auth/auth-shell";
import { AuthForm } from "@/components/auth/auth-form";

export const metadata: Metadata = {
  title: "Sign up — OptiMiles",
  description: "Create your free OptiMiles account and start optimizing your travel rewards.",
};

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your account"
      subtitle="Start charting an explainable path to your next redemption — free."
    >
      <AuthForm mode="signup" />
    </AuthShell>
  );
}
