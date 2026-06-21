# Decision Log — Real Card Art + Supported-Card Scope Change

**Date:** 2026-06-21
**Area:** frontend / product

---

## Context

The supported-cards carousel ([2026-06-21-landing-page-outcome-redesign.md](2026-06-21-landing-page-outcome-redesign.md)) used styled gradient placeholders for every card and listed a mix of in-scope cards plus filler entries (ICICI Emeralde, IDFC First Wealth, Air India SBI, Vistara SBI, Amex MRCC) that were never part of the MVP set. The user supplied real card photography and asked to show real art and tighten the list to cards we actually intend to feature.

The original MVP card list in root `CLAUDE.md` is: HDFC Infinia, HDFC Diners Black, Axis Atlas, Axis Magnus, Amex Platinum Travel, SBI Cashback. The user's available photos and stated intent diverged from that list, so the supported set changed.

## Decisions

1. **Real card art wired in.** `SupportedCards` now supports an optional `image` field per card. Cards with a photo render it via `next/image` (`fill` + `object-cover`) with a bottom-up `bg-linear-to-t` scrim so the tier/name label stays legible; cards without a photo keep the icon + gradient treatment. Photos live in `frontend/public/cards/`.

2. **Supported-card set changed from the CLAUDE.md MVP list.** This is a deliberate scope change, confirmed with the user across several turns:
   - **Added (active, with real photos):** HDFC Regalia Gold, HSBC Premier, HSBC TravelOne — none of these are in the original `CLAUDE.md` MVP list. Adding them widens MVP card scope.
   - **Kept (active, with real photos):** HDFC Infinia, HDFC Diners Club Black.
   - **Kept (coming-soon placeholders, no photo yet):** Axis Atlas, Axis Magnus, Amex Platinum Travel — awaiting real photography.
   - **Removed:** SBI Cashback (was in the MVP list; user asked to drop it), plus the off-scope filler entries (ICICI Emeralde, IDFC First Wealth, Air India SBI Signature, Vistara SBI Prime, Amex MRCC).
   - Net carousel: **5 photo cards + 3 coming-soon = 8**.

3. **Photo files added to `public/cards/`.** `infinia.png`, `diners-black.png`, `regalia-gold.png`, `hsbc-premier.jpg`, `hsbc-travelone.jpg`. Source images came from the user's `~/Downloads/cc-photos/` and were copied (renamed to stable kebab-case slugs), not moved.

## Final state (same-day follow-up)

The card set was tightened again after a visual review, and the canonical docs were reconciled:

4. **Wallet section trimmed to 4 example cards.** The "cards you already carry" carousel is now an *illustrative example*, not the full supported set — 4 cards, all active with real photos: HDFC Infinia, HDFC Diners Club Black, HDFC Regalia Gold, HSBC TravelOne. HSBC Premier was dropped and its photo deleted (`public/cards/hsbc-premier.jpg`; original kept in `_originals/`). The Axis/Amex coming-soon placeholders were removed from this section. Breadth now lives in the "Supported ecosystems" section, not the wallet.

5. **SBI removed from the frontend** per user request. Dropped the "SBI" badge from the ecosystem marquee and refreshed the FAQ "what cards are supported" answer to the cards actually featured (HDFC Infinia, Diners Club Black, Regalia Gold, HSBC TravelOne) — it previously over-claimed Axis/Amex/SBI.

6. **Canonical card scope reconciled (the deferred item below — now done).** Per user decision:
   - **Root `CLAUDE.md` "Initial Supported Cards":** added HDFC Regalia Gold + HSBC TravelOne (now 8 cards). SBI Cashback kept in scope here (removed from the *UI* only, not the product target).
   - **`docs/prd/mvp_scope_1.md` "Recommended Initial Card List":** added HSBC TravelOne to Premium Travel; removed SBI Aurum and ICICI Emeralde. HDFC Regalia Gold was already listed under Mid-Tier.
   - The frontend 4-card wallet remains a curated *example*, deliberately narrower than the MVP scope — this UI/scope divergence is intentional, not drift.

## Not done (deferred)

- **Axis / Amex photography.** Axis Atlas, Axis Magnus, and Amex Platinum Travel are in scope (`CLAUDE.md`/PRD) but not shown in the wallet example; real photos (`atlas.png`, `magnus.png`, `amex-platinum-travel.png`) can be added to `public/cards/` later if they're wanted in the carousel.
- **HSBC TravelOne EXIF orientation.** The image renders correctly after the user's rotation; `file` still reports portrait pixels + an EXIF orientation flag. User confirmed it looks right in-browser — no pixel re-encode done.
