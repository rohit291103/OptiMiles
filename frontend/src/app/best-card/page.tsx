import type { Metadata } from "next";

import { BestCard } from "@/components/best-card";
import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";

export const metadata: Metadata = {
  title: "Best card for this spend — OptiMiles",
  description:
    "Tell us what you're about to buy and we'll tell you which of your cards earns the most miles — with the maths shown.",
};

/**
 * Public, signed-out Best Card page (roadmap Phase 1 — the daily habit).
 *
 * Deliberately outside the `(app)` route group: that shell is auth-gated, and
 * the whole acquisition argument for this feature is that anyone can pick
 * their real cards and get a genuinely true answer before signing up.
 */
export default function BestCardPage() {
  return (
    <main className="min-h-screen">
      <SiteNav />
      <BestCard />
      <SiteFooter />
    </main>
  );
}
