# UX — Landing Page (Design System Baseline)

**Status:** Current implementation (`frontend/src/app/page.tsx`)

**v2 (2026-06-26):** Product-first restructure — the live Goal Simulator was promoted from mid-page to **section 1** (directly under the hero, before any explanation), following the Replit "put the usable product at the top" pattern.

**v3 (2026-06-26, same session):** Went fully **edge-to-edge** and **cinematic**, per direct user direction ("use the full width, no box… not a very simple scroll, redesign like the Apple website").
- **No centered box.** The page has no `max-w` content cage. `Inner` (in `components/sections/section-shell.tsx`) is the *only* horizontal gutter — a small fluid pad (`px-5 … 2xl:px-24`) so content uses essentially the whole screen. Nav and footer follow the same gutter. Long-form paragraphs opt back to a readable line-length with `max-w-prose`/`Measure`, not by re-centering the section.
- **Scroll choreography (Apple-style, but no scroll-hijacking).** The hero is a pin-and-release stage that scales/blurs/fades on scroll (`useScroll`/`useTransform`) — appropriate because it's passive. The simulator deliberately is **not** pinned: an early attempt to make it a ~260vh pinned scroll scene hijacked the wheel and clipped the expanding results (felt "stuck"), so `simulator-scene.tsx` is now a normal, freely-scrollable block with a one-time scale/fade *entrance* (`whileInView`, `once`) and sticky intro copy on wide screens. All scroll effects collapse to a calm static layout under `prefers-reduced-motion`.
- **Removed decorative `PageFrame`.** The old fixed side-rail frame (vertical rails with gold dots travelling down them) was built for the centered-column layout; in the edge-to-edge design its rails sat inside the content and the dots read as distracting "droplets." Component deleted. The `bg-starfield` texture was also made static (drift animation removed) for the same reason.

Built on branch `redesign/full-bleed-simulator-hero`.

---

## Design System

| Element | Choice |
|---|---|
| Theme | Dark-only (`color-scheme: dark`), no light mode toggle in MVP |
| Accent | Gold (`--gold`, oklch(0.74 0.1 75)) — used sparingly for emphasis, CTAs, "Active" status |
| Headings | Fraunces (serif, `font-heading`), italic used for emphasis words |
| Body | Geist Sans |
| Borders | "Hairline" — low-opacity foreground color, not a hard border color |
| Background texture | Subtle dot-grain radial gradient (`.bg-grain`) |

This should feel "intelligent, premium, strategic, trustworthy" per CLAUDE.md's Product Design Philosophy — not a generic SaaS dashboard.

## Page Structure (v2)

1. **Header** — sticky, blurred, logo + anchor nav (Simulator first, then How it works / Supported cards / Features / FAQ) + CTA. Edge-to-edge gutter (no centered measure).
2. **Hero** (`min-h-[100svh]`, edge-to-edge) — fluid display headline (`clamp(3rem,8.5vw,8rem)`) spanning the width + `HeroFlow` floated to the right edge. Pin-and-release: scales/blurs/fades on scroll. Scroll cue + secondary CTA point at `#simulate` ("Try it now").
3. **Goal Simulator** (`#simulate`) — directly below the hero (`simulator-scene.tsx`). Edge-to-edge split: sticky "Pick your cards. / See the path." copy beside the live simulator, which scale/fades in once on entry. Freely scrollable (not pinned) so the interactive form behaves normally. Lets a visitor run the core loop before signing up.
4. **Dream outcomes** — trips, not points.
5. **How it works** (`#how`) — sticky-scroll step list.
6. **Trust pillars** — "structured card logic first, AI second."
7. **Strategy output** — concrete example of what the user gets.
8. **Supported cards** (`#cards`) — "the credit cards you already carry." A **static responsive grid** (no carousel): 5 cards, all **Active** (gold badge), each shown full-bleed-uncropped (`object-contain`, `1.586:1` landscape) on a dark plate with the name/tier label below. This is a **5-card illustrative wallet** (a deliberate subset of the 8-card MVP scope), *not* a tiered roadmap roster. (The component still supports a "Coming soon" badge branch, but no card uses it currently.) Earlier drafts described an autoplay/drag carousel and a tier-by-tier roadmap with Coming-soon cards — both were dropped: the carousel cropped wide card logos (`object-cover`), and the roadmap framing was replaced by the simpler "your existing wallet" story. See decision `2026-06-21-supported-cards-photos-and-scope.md`.
9. **Ecosystem marquee** — airlines / hotels / banks.
10. **Built for** — audience framing.
11. **Feature tabs** (`#features`) — the four engine tools "under the hood."
12. **Why OptiMiles exists** — manifesto block.
13. **FAQ** (`#faq`) → **Final CTA** → **Footer**.

Alternating sections use the `banded` flag on `Bleed` (tinted `bg-card/20` + hairline border) for vertical rhythm.

## Known constraints

- The Goal Simulator is currently a static mock (`goal-simulator.tsx`) — destinations and mile counts are hardcoded, not wired to a real optimizer. This is correct for the current "frontend shell, no backend yet" phase, but should not be confused with the real Simulation Engine once the backend exists.
- Only 3 destinations (Singapore, London, New York) are wired in the simulator. These are now the canonical MVP routes — `docs/prd/mvp_scope_1.md` was reconciled to match the built product (an earlier PRD draft listed Dubai instead of New York; the product is the source of truth).

## Open questions for future UX work

- What happens when a "Coming soon" card is clicked — nothing yet, intentionally inert in MVP.
- Auth/onboarding flow ("Get started" button) is not yet implemented.
