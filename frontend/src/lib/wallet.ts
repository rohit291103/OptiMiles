"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * "My wallet" — the cards the user actually holds.
 *
 * ONE wallet, shared by every surface (Portfolio View, Best Card, the goal
 * wizard). Before this existed each surface asked for the same list again,
 * which is both tedious and a quiet trust problem: the same person could get
 * answers computed over three different wallets in one session.
 *
 * Storage is `localStorage`, deliberately, for now:
 *  - Best Card is signed-out by design (roadmap Phase 1), so the wallet has
 *    to work with no account at all;
 *  - the wallet is a list of catalog card ids — no balances, no statements,
 *    nothing sensitive;
 *  - a server-side wallet needs a schema change and a real migration story
 *    for signed-out users, and Phase 2 (spend logging) is when a per-user
 *    row starts earning its keep. Until then this is the honest, small
 *    version: per-device, and the UI says so.
 *
 * Reads are a `useSyncExternalStore` subscription so every mounted surface
 * re-renders together — including across browser tabs, via `storage`.
 */

const STORAGE_KEY = "optimiles.wallet.v1";

/** Stable identity for the server/empty snapshot — a fresh [] each call would
 *  make useSyncExternalStore loop forever. */
const EMPTY: readonly string[] = [];

const listeners = new Set<() => void>();

/** Cached parse of the raw string, so getSnapshot returns a stable reference
 *  between writes (the store contract requires identity, not deep equality). */
let cachedRaw: string | null = null;
let cachedValue: readonly string[] = EMPTY;

function readRaw(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    // Safari private mode and "block all cookies" both throw on access.
    return null;
  }
}

function getSnapshot(): readonly string[] {
  const raw = readRaw();
  if (raw === cachedRaw) return cachedValue;
  cachedRaw = raw;
  cachedValue = parse(raw);
  return cachedValue;
}

function parse(raw: string | null): readonly string[] {
  if (!raw) return EMPTY;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return EMPTY;
    const ids = parsed.filter((id): id is string => typeof id === "string");
    return ids.length > 0 ? ids : EMPTY;
  } catch {
    return EMPTY;
  }
}

function getServerSnapshot(): readonly string[] {
  return EMPTY;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", notify);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener("storage", notify);
  };
}

function notify(): void {
  for (const listener of listeners) listener();
}

/**
 * One-shot, non-reactive read — for callers that need the wallet once inside
 * an effect (e.g. seeding a form's initial selection) and must not re-run
 * when it changes. Reactive surfaces use `useWallet`.
 */
export function readWallet(): readonly string[] {
  if (typeof window === "undefined") return EMPTY;
  return getSnapshot();
}

/** Overwrite the wallet. Order is preserved — it is the user's own ordering. */
export function saveWallet(cardIds: readonly string[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...cardIds]));
  } catch {
    // Storage full or blocked: the in-memory snapshot below still updates, so
    // the current session keeps working and only persistence is lost.
  }
  cachedRaw = null;
  notify();
}

/**
 * The user's wallet, plus a setter and a `hydrated` flag.
 *
 * `hydrated` is false during SSR and the first client render (both see the
 * empty snapshot). Surfaces must not render "you have no cards" until it is
 * true, or a returning user gets a flash of the empty state.
 */
export function useWallet(): {
  cardIds: readonly string[];
  setWallet: (ids: readonly string[]) => void;
  toggleCard: (id: string) => void;
  hydrated: boolean;
} {
  const cardIds = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const hydrated = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const toggleCard = useCallback((id: string) => {
    const current = getSnapshot();
    saveWallet(
      current.includes(id) ? current.filter((cardId) => cardId !== id) : [...current, id],
    );
  }, []);
  return { cardIds, setWallet: saveWallet, toggleCard, hydrated };
}
