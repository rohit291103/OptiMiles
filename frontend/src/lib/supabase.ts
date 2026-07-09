"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Browser Supabase client (singleton). Auth lives entirely client-side: the
 * session/access-token is minted here and persisted by supabase-js in
 * localStorage; the API client reads the token off this client to authenticate
 * calls to FastAPI (which verifies the JWT and extracts the real auth.users id).
 *
 * Both env vars are NEXT_PUBLIC_ (browser-exposed) — the anon key is designed to
 * be public; RLS + the JWT secret (server-side only) are what enforce access.
 * When they're unset, `supabase` is null and the UI treats auth as unavailable
 * rather than crashing.
 */

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase: SupabaseClient | null =
  url && anonKey
    ? createClient(url, anonKey, {
        auth: {
          // Explicit PKCE flow: OAuth returns a `?code=` that /auth/callback
          // exchanges for a session. detectSessionInUrl auto-exchanges it;
          // persistSession + autoRefresh keep the browser session alive.
          flowType: "pkce",
          detectSessionInUrl: true,
          persistSession: true,
          autoRefreshToken: true,
        },
      })
    : null;

export const isAuthConfigured = Boolean(url && anonKey);

/** The current session's access token, or null when signed out / unconfigured. */
export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
