"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, EyeOff, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const isSignup = mode === "signup";
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    // Front-end only for now — wire to the backend auth route when ready.
    setTimeout(() => setSubmitting(false), 1200);
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <Button variant="outline" className="border-hairline" type="button">
          <GoogleGlyph /> Google
        </Button>
        <Button variant="outline" className="border-hairline" type="button">
          <AppleGlyph /> Apple
        </Button>
      </div>

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

function AppleGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden fill="currentColor">
      <path d="M16.36 12.78c-.02-2.02 1.65-2.99 1.72-3.04-.94-1.37-2.4-1.56-2.92-1.58-1.24-.13-2.42.73-3.05.73-.63 0-1.6-.71-2.63-.69-1.35.02-2.6.79-3.3 2-1.4 2.44-.36 6.05 1.01 8.03.67.97 1.47 2.06 2.51 2.02 1.01-.04 1.39-.65 2.61-.65 1.22 0 1.56.65 2.63.63 1.09-.02 1.78-.99 2.45-1.96.77-1.12 1.09-2.21 1.1-2.27-.02-.01-2.11-.81-2.13-3.2ZM14.4 6.6c.56-.68.94-1.62.83-2.56-.81.03-1.79.54-2.37 1.21-.52.6-.97 1.56-.85 2.48.9.07 1.83-.46 2.39-1.13Z" />
    </svg>
  );
}
