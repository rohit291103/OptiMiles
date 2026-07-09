"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";

import { supabase } from "@/lib/supabase";

export type AuthState = {
  user: User | null;
  loading: boolean;
};

/**
 * Subscribes to the Supabase session. Returns the current user (or null) and a
 * loading flag for the initial resolve. Updates live on login/logout via
 * onAuthStateChange, so the nav reflects auth state without a page reload.
 */
export function useAuth(): AuthState {
  const [user, setUser] = useState<User | null>(null);
  // If auth isn't configured there's nothing to resolve — start not-loading.
  const [loading, setLoading] = useState(() => supabase !== null);

  useEffect(() => {
    const client = supabase;
    if (!client) return;

    let active = true;
    client.auth.getSession().then(({ data }) => {
      if (!active) return;
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const { data: sub } = client.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  return { user, loading };
}

/** Sign the current user out (no-op if auth isn't configured). */
export async function signOut(): Promise<void> {
  if (supabase) await supabase.auth.signOut();
}
