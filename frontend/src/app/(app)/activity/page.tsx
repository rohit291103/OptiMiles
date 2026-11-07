"use client";

import { useEffect, useState } from "react";

import { ActivityLog } from "@/components/app/activity-log";
import { fetchCards, type CardSummary } from "@/lib/api";

/**
 * `/activity` — the log, and what it proves.
 *
 * ONE surface for spend and lounge visits together (roadmap: "design them as
 * one pattern, not two — same entry surface, same mental model"). It is also
 * where the three figures Portfolio View ships without finally land: cap
 * utilisation, milestone progress, and lounge visits used.
 *
 * Signed-in only, unlike Best Card and `/cards`: those are anonymous because
 * the wallet is whatever the client sends, but a log is a personal record that
 * has to survive a device.
 */

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; cards: CardSummary[] }
  | { phase: "error"; message: string };

export default function ActivityPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    let active = true;
    fetchCards()
      .then((cards) => {
        if (active) setState({ phase: "ready", cards });
      })
      .catch((e) => {
        if (active)
          setState({
            phase: "error",
            message:
              e instanceof Error ? e.message : "Couldn't load the catalog.",
          });
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <h2 className="font-heading text-xl text-foreground sm:text-2xl">
          My log
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
          Record what you spend and the lounges you get into. OptiMiles turns
          that into the things it otherwise has to leave blank — how much of a
          bonus-rate cap you have used, how close a milestone is, how many
          lounge visits you have left, and whether a card has earned its
          annual-fee waiver.
        </p>
      </header>

      {state.phase === "loading" && (
        <p className="text-sm text-muted-foreground" role="status">
          Loading your cards…
        </p>
      )}
      {state.phase === "error" && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4">
          <p className="text-sm text-destructive" role="alert">
            {state.message}
          </p>
        </div>
      )}
      {state.phase === "ready" && <ActivityLog catalog={state.cards} />}
    </div>
  );
}
