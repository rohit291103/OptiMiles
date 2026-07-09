"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { supabase } from "@/lib/supabase";

/**
 * OAuth return handler. Supabase redirects here after Google with a `?code=` in
 * the URL; the browser client (PKCE, detectSessionInUrl) exchanges it for a
 * session on load. We then send the user home. Without this route the code is
 * never exchanged and the user lands logged-out — the bug this fixes.
 */
/** Read an OAuth error from the URL (query or hash) at first render, if any. */
function providerErrorFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  const query = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const err =
    query.get("error_description") ||
    query.get("error") ||
    hash.get("error_description") ||
    hash.get("error");
  return err ? `Google sign-in failed: ${err}` : null;
}

export default function AuthCallbackPage() {
  const router = useRouter();
  // Initialize from the URL so a provider error is shown without a synchronous
  // setState inside the effect (which would trigger cascading renders).
  const [error, setError] = useState<string | null>(providerErrorFromUrl);

  useEffect(() => {
    const client = supabase;
    if (!client) {
      router.replace("/login");
      return;
    }
    // A provider error was already captured at render; don't try to exchange.
    if (providerErrorFromUrl()) return;

    let active = true;
    const query = new URLSearchParams(window.location.search);

    // detectSessionInUrl auto-exchanges the code; getSession then reflects it.
    client.auth
      .getSession()
      .then(({ data }) => {
        if (!active) return;
        if (data.session) {
          router.replace("/");
          return;
        }
        // Fall back to an explicit exchange if auto-detection didn't fire.
        const code = query.get("code");
        if (!code) {
          setError(
            "Sign-in didn't complete — no code returned. " +
              `URL was: ${window.location.search || window.location.hash || "(empty)"}`,
          );
          return;
        }
        client.auth.exchangeCodeForSession(code).then(({ error }) => {
          if (!active) return;
          if (error) setError(`Code exchange failed: ${error.message}`);
          else router.replace("/");
        });
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : "Sign-in failed.");
      });

    return () => {
      active = false;
    };
  }, [router]);

  return (
    <div className="grid min-h-dvh place-items-center px-6 text-center">
      {error ? (
        <div className="space-y-3">
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
          <a href="/login" className="text-sm text-gold hover:underline">
            Back to log in
          </a>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground" role="status">
          Signing you in…
        </p>
      )}
    </div>
  );
}
