# Figma Make — OptiMiles landing page prompt

Paste **PROMPT 1** first and let it build. Then send prompts 2–4 as follow-up
messages in the same Make chat. Do not paste all four at once — Make degrades
badly past a few hundred lines and will silently drop sections.

Attach before prompt 1:
- the two reference screenshots (Nubank/Knot hero + card fan)
- the 8 card PNGs from `figma-assets/cards/` (already normalized to 1400×883)

---

## PROMPT 1 — foundation + hero

```
Build a dark, premium landing page for OptiMiles — an AI reward-optimization
engine for Indian credit cards. Positioning line: "Google Maps for Indian credit
card rewards." It maps the cards already in a user's wallet into an explainable
route to a travel goal (e.g. Singapore Airlines business class).

Tone: intelligent, premium, strategic, trustworthy. Editorial and cinematic —
closer to a luxury travel brand than a fintech dashboard. NOT playful, NOT
crypto, NOT a generic SaaS template.

=== STACK ===
React + TypeScript, Tailwind, and `motion` (import from "motion/react").
No 3D libraries. No carousel/slider libraries. CSS 3D transforms only.

=== DESIGN TOKENS (use these exact values) ===
background        oklch(0.16 0.012 264)   near-black, faint blue cast
foreground        oklch(0.96 0.012 80)    warm off-white
card              oklch(0.19 0.013 264)
secondary         oklch(0.24 0.013 264)
muted-foreground  oklch(0.66 0.02 75)
gold              oklch(0.74 0.1 75)      the ONLY accent colour
gold-foreground   oklch(0.16 0.012 264)
hairline          oklch(0.96 0.012 80 / 14%)   all borders, 1px

Type: headings in Fraunces (serif) at light weight, tight tracking, leading
~0.9–1.05. Body in Geist (sans). Eyebrow labels: 12px, uppercase, letter-spacing
0.22em, gold.

Signature heading treatment: a two-part headline where the second half is
Fraunces *italic in gold*. Example: "Real trips, / not just points." with
"not just points." italic gold. Use this on every section heading.

Surfaces: rounded-[2rem] cards, bg-card at ~50% opacity, backdrop-blur, a 1px
hairline border, and an inset top highlight
`inset 0 1px 0 rgba(255,255,255,0.08)`. Never use pure black or pure white.

=== MOTION SYSTEM (shared, define once) ===
- Easing everywhere: cubic-bezier(0.16, 1, 0.3, 1). Long and soft, never bouncy.
- Standard reveal: fade + 28px lift, 0.8s, triggered on viewport enter, once.
- Stagger children by 0.09s.
- DIRECTION-AWARE reveals: content in a left column enters from x:-40, content
  in a right column from x:+40. This is the look in reference image 1.
- Word-cascade headlines: split the h1 into words, each masked by an
  overflow-hidden wrapper, sliding up from y:110% staggered 0.08s.
- Every animation must respect useReducedMotion() and render static instead.
- Animate transform and opacity ONLY. Never width/height/top/left.

=== SECTION 1: NAV ===
Sticky, transparent over the hero, gaining a blurred background + hairline
bottom border after 40px of scroll. Left: OptiMiles wordmark in Fraunces.
Centre: How it works / Cards / Features / FAQ. Right: "Log in" ghost button and
"Get started" solid gold button.

=== SECTION 2: HERO (full viewport) ===
Two columns, 1.15fr / 0.85fr, edge-to-edge with generous side padding.

LEFT COLUMN (enters from x:-40, staggered):
- A small pill badge with a card icon: "Google Maps for Indian credit card rewards"
- h1, fluid clamp(2.75rem, 7vw, 6.25rem), three lines, word-cascade reveal:
    "Your cards."
    "Your goal."
    "Mapped."     <- this line italic + gold
- Sub-paragraph, muted: "Tell OptiMiles where you want to fly. It maps the cards
  already in your wallet into a clear, explainable route to get you there — which
  card to use, when to transfer, and exactly when you'll arrive."
- Two buttons: "Build my card strategy" (solid gold, arrow icon) and
  "Try the simulator" (ghost)
- A 3-up stat row above a hairline top border: "8 / Cards supported",
  "0 / SMS or statements read", "100% / Explainable routing"

RIGHT COLUMN (enters from x:+60, rotated ~1deg):
A floating glass panel showing a 4-step vertical journey, with a gold connector
line that draws itself downward between the steps:
  Your cards        -> HDFC Infinia · Axis Atlas
  Your goal         -> Long-haul business class
  Card-to-card routing -> Spend mapped, card by card
  Redemption        -> Ready in 11 months
Behind it, a soft gold radial glow.

BACKGROUND: layered — a slow-drifting dark gradient field, a faint static dot
starfield at 50% opacity, and a bottom fade to the page background.

HERO SCROLL BEHAVIOUR: as the user scrolls the first viewport, the entire hero
scales 1 -> 0.94, translates y 0 -> -80px, blurs 0 -> 6px, and fades to 0 — an
Apple-style camera pull-back, so the next section rises underneath rather than
hard-cutting. Drive this off scrollY in PIXELS (thresholds at 12vh and 70vh),
not off a scoped element progress.

Bottom-centre: a scroll cue reading "Try it now" with a small gold dot looping
inside a pill outline.
```

---

## PROMPT 2 — the card fan scene

```
Now add the signature scroll scene, directly after the hero. Match reference
image 2. Use the 8 attached card PNGs (already 1400x883, transparent rounded
corners).

STRUCTURE
- Outer track 300vh tall. Inner stage is sticky, h-screen, overflow-hidden.
- useScroll({ target, offset: ["start start", "end end"] }).
- Position must be a PURE FUNCTION of scrollYProgress. No mount/entrance
  animations. Scrolling back up must exactly reverse the fan.

GEOMETRY — expose all of these as named constants at the top of the file:
  SPREAD_DEG   = 40     angular gap between neighbouring cards
  PIVOT        = "50% 190%"   transform-origin BELOW the card, so the cards
                              fan from a shared point like a hand of cards
  PERSPECTIVE  = 1600   px, on the stage wrapper
  STAGE_TILT   = 14     rotateX on the whole fan
  SPIN_DEG     = 200    extra whole-fan rotation over the back half of scroll
  STAGGER      = 0.035  per-card offset in progress units
  FAN_DURATION = 0.34   progress span each card takes to reach its slot

PER CARD i of n:
  slot  = (i - (n-1)/2) * SPREAD_DEG
  start = 0.06 + i * STAGGER
  open  = start + FAN_DURATION
  rotate:  [start, open, 1] -> [0, slot, slot + SPIN_DEG]
  scale:   [start, open, 1] -> [0.86, 1, 0.92]
So at progress 0 all cards sit in a tight stack; they unfurl sequentially into
a full radial fan; then the whole fan rotates as one body.

CARD RENDERING — three layers in one wrapper:
1. the card art, aspect-ratio exactly 1.586 (ISO/IEC 7810 ID-1), rounded-[6%]
2. a SPECULAR SWEEP overlay: a linear-gradient whose angle is derived from that
   card's own current rotation (angle = 110 - rotation) so the highlight stays
   fixed in the world while the card turns under it. Use mix-blend-overlay,
   white at ~18% through the middle stop. This is what sells the 3D — without
   it the cards read as flat stickers.
3. drop-shadow 0 28px 45px rgba(0,0,0,0.55)
Cards are positioned absolute at the stage centre; put the -50%/-50% centring
into the motion transform (x/y), NOT Tailwind translate classes, or the motion
transform will overwrite it.

COPY OVERLAY
- Behind the cards, visible while stacked, fading out by progress 0.3:
  eyebrow "The wallet you already have", h2 "Eight cards. One route." with
  "One route." italic gold.
- Below the fan, fading IN from progress 0.62: "OptiMiles maps every rupee of
  spend across all of them — then tells you which card to swipe, when to
  transfer, and exactly when you fly."

Behind everything: a gold radial glow that blooms from 35% to 100% opacity as
the fan opens.

Reduced motion: render the fan static at its fully-open state, no scrub.
```

---

## PROMPT 3 — the middle sections

```
Add these sections below the fan. Every section: centred heading block
(gold uppercase eyebrow, then a Fraunces h2 whose second half is italic gold,
then a muted sub-paragraph), followed by the content. Alternate section
backgrounds between the page background and a subtly lighter "banded" surface.
py-32 between sections.

1. DREAM OUTCOMES
   Eyebrow "Where your card spend goes" / "Real trips, / not just points."
   Sub: "OptiMiles optimizes your credit card spend for goals achieved: the trip,
   the suite, the lounge — not points earned for their own sake."
   Content: a 4-up grid of tall image cards (business class seat, hotel suite,
   airport lounge, resort). Each has a dark gradient scrim, a title, and scales
   1.03 with the scrim lightening on hover. Use placeholder travel photography.

2. HOW IT WORKS
   A 4-step horizontal flow: Set your goal -> Add your cards -> See the route ->
   Track to redemption. Numbered gold markers connected by a hairline that
   draws itself left-to-right as the section scrolls into view.

3. WHY TRUST OPTIMILES
   Eyebrow "Why trust OptiMiles" / "Structured card logic first. / AI
   orchestration second."
   Sub: "Every card recommendation traces back to deterministic logic, not a
   language model improvising transfer ratios."
   Content: 3 pillar cards — "Deterministic math" / "Sourced card data" /
   "Explainable every step". Icon, title, short body. Stagger in.

4. STRATEGY OUTPUT
   Eyebrow "What you actually get" / "A card strategy you can / act on."
   Content: a realistic mock of the product's output — a panel listing spend
   categories mapped to specific cards with earn rates, a transfer path
   (card points -> KrisFlyer at a ratio), and a dated timeline bar. Make it look
   like real product UI, not an illustration. Numbers count up when it enters view.

5. SUPPORTED CARDS
   Eyebrow "Your existing wallet" / "The credit cards you already / carry."
   A 5-up responsive grid of the card images on dark plates, each with a name,
   a tier label, and a gold "Active" badge. Border warms to gold on hover.

6. SUPPORTED ECOSYSTEMS
   Eyebrow "Supported ecosystems" / "Airlines, hotels, / and your banks."
   An infinite horizontal marquee of program names (Singapore Airlines
   KrisFlyer, Air India Maharaja Club, Marriott Bonvoy, Accor ALL, British
   Airways Executive Club, Qatar Privilege Club, HDFC, Axis, Amex, HSBC).
   Two rows scrolling in opposite directions, masked to fade at both edges,
   paused on hover.

7. BUILT FOR
   Eyebrow "Built for" / "However you think / about rewards."
   3 persona cards: the goal-driven traveller, the points optimizer, the
   "I have cards and no idea" user.

8. CAPABILITIES
   Eyebrow "Under the hood" / "One engine, / four sharp tools."
   A tabbed panel — Knowledge / Valuation / Optimization / Simulation. Clicking
   a tab crossfades the panel content and slides a gold underline to the active
   tab with a shared layout animation.
```

---

## PROMPT 4 — closing sections + polish

```
Finish the page.

9. MANIFESTO — a centred full-width statement, no card, lots of air:
   eyebrow "Why OptiMiles exists", then in large Fraunces:
   "The seat you want already exists in the credit cards you already carry."
   Then a muted paragraph: "Most people leave business class on the table, not
   because they have the wrong cards, but because no one ever told them which
   card to swipe for which purchase. OptiMiles closes that gap."

10. FAQ — max-width 3xl, accordion, hairline dividers, gold chevron that rotates
    on open, smooth height animation. 6 questions covering: does it read my SMS
    or statements (no), which cards are supported, how transfer ratios are kept
    accurate, is it free, does it recommend new cards, how the timeline is
    calculated.

11. FINAL CTA — a large rounded-[2.5rem] panel, hairline border, gold aurora
    glow inside, centred: a shield icon, "Your next redemption is a card
    strategy away.", a short sub, and two buttons (solid gold "Build my card
    strategy", outline "Explore the simulator").

12. FOOTER — wordmark, three link columns (Product / Company / Legal), and a
    fine-print line. Hairline top border.

POLISH PASS across the whole page:
- Section transitions should feel continuous, not like independent blocks each
  fading in. Adjacent sections should overlap slightly in their scroll ranges.
- Add a thin gold scroll-progress bar fixed at the very top of the viewport.
- All interactive elements need visible focus-visible rings in gold.
- Verify nothing causes horizontal overflow at 375px, 768px, and 1440px.
- Verify the whole page renders correctly and statically with
  prefers-reduced-motion: reduce.
```

---

## What to bring back into the repo

Not the code — it won't know our tokens, our `motion/react` import path, or our
existing `FadeUp`/`WordReveal`/`Stagger` primitives in
`frontend/src/components/ui/motion.tsx`.

Bring back:
1. The **fan constants block** (angles, pivot, perspective, stagger, breakpoints)
   once you've tuned it by eye.
2. Screen recordings of any section whose motion you want to keep.
3. Any **copy** you preferred over what's live.

## Expected failure modes

| Symptom | Correction to send |
|---|---|
| Cards animate on mount instead of scrubbing | "The fan is animating on mount. It must not. Position must be a pure function of scrollYProgress — scrolling up must exactly reverse it." |
| Cards orbit the screen centre, not a point below | "Set transform-origin to `50% 190%` on each card so they share a pivot below the stage." |
| Everything fades in identically | "Reveals are all identical. Use direction-aware entrances: left-column content from x:-40, right-column from x:+40." |
| Gold used as a fill everywhere | "Gold is an accent only — use it for eyebrows, italic headline halves, and primary buttons. Surfaces stay near-black." |
| Sticky sections jitter | "Use a single sticky child inside a tall track. Do not nest sticky elements." |
