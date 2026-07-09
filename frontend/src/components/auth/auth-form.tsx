"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { supabase } from "@/lib/supabase";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const isSignup = mode === "signup";
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (!supabase) {
      setError("Authentication isn't configured yet. Add the Supabase keys.");
      return;
    }

    const form = new FormData(e.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const fullName = String(form.get("name") ?? "");

    setSubmitting(true);
    try {
      if (isSignup) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName } },
        });
        if (error) throw error;
        // With email confirmation on, there's no session yet — tell the user.
        if (!data.session) {
          setNotice("Check your email to confirm your account, then log in.");
          return;
        }
        router.push("/");
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        router.push("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOAuth(provider: "google") {
    setError(null);
    if (!supabase) {
      setError("Authentication isn't configured yet. Add the Supabase keys.");
      return;
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      // Return to a dedicated route that exchanges the ?code= for a session,
      // then sends the user home. Redirecting straight to "/" leaves the code
      // unhandled and the user logged out.
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) setError(error.message);
  }

  return (
    <div className="space-y-6">
      <Button
        variant="outline"
        className="w-full border-hairline"
        type="button"
        onClick={() => handleOAuth("google")}
      >
        <GoogleGlyph /> Continue with Google
      </Button>

      <div className="flex items-center gap-3 text-xs text-muted-foreground/70">
        <span className="h-px flex-1 bg-hairline" />
        or continue with email
        <span className="h-px flex-1 bg-hairline" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {isSignup && (
          <div className="space-y-2">
            <Label htmlFor="name">Full name</Label>
            <Input id="name" name="name" placeholder="Aditya Rao" autoComplete="name" required />
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            {!isSignup && (
              <Link
                href="#"
                className="text-xs text-muted-foreground transition-colors hover:text-gold"
              >
                Forgot password?
              </Link>
            )}
          </div>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder={isSignup ? "At least 8 characters" : "••••••••"}
              autoComplete={isSignup ? "new-password" : "current-password"}
              required
              className="pr-10"
            />
            <button
              type="button"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((v) => !v)}
              className="absolute inset-y-0 right-0 grid w-10 place-items-center text-muted-foreground transition-colors hover:text-foreground"
            >
              {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>

        {isSignup && (
          <label className="flex items-start gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              required
              className="mt-0.5 size-4 rounded border-hairline bg-input/30 accent-gold"
            />
            <span>
              I agree to the Terms of Service and Privacy Policy.
            </span>
          </label>
        )}

        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="text-sm text-gold" role="status">
            {notice}
          </p>
        )}

        <Button
          type="submit"
          size="lg"
          disabled={submitting}
          className="w-full bg-gold text-gold-foreground hover:bg-gold/90"
        >
          {submitting && <Loader2 className="animate-spin" />}
          {isSignup ? "Create account" : "Log in"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {isSignup ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-gold hover:underline">
              Log in
            </Link>
          </>
        ) : (
          <>
            New to OptiMiles?{" "}
            <Link href="/signup" className="font-medium text-gold hover:underline">
              Create an account
            </Link>
          </>
        )}
      </p>
    </div>
  );
}

function GoogleGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden>
      <path
        fill="currentColor"
        d="M21.35 11.1H12v3.8h5.35c-.23 1.25-.94 2.3-2 3l3.23 2.5c1.88-1.74 2.97-4.3 2.97-7.35 0-.66-.06-1.3-.2-1.95Z"
      />
      <path
        fill="currentColor"
        d="M12 22c2.7 0 4.96-.9 6.62-2.43l-3.23-2.5c-.9.6-2.05.96-3.39.96-2.6 0-4.8-1.76-5.59-4.12l-3.34 2.58C4.7 19.74 8.06 22 12 22Z"
        opacity=".7"
      />
      <path
        fill="currentColor"
        d="M6.41 13.91A6 6 0 0 1 6.09 12c0-.66.11-1.31.32-1.91L3.07 7.51A10 10 0 0 0 2 12c0 1.61.39 3.14 1.07 4.49l3.34-2.58Z"
        opacity=".5"
      />
      <path
        fill="currentColor"
        d="M12 5.98c1.47 0 2.79.5 3.83 1.49l2.86-2.86C16.95 2.99 14.7 2 12 2 8.06 2 4.7 4.26 3.07 7.51l3.34 2.58C7.2 7.74 9.4 5.98 12 5.98Z"
        opacity=".85"
      />
    </svg>
  );
}
