# HDFC Transfer Partner Infographics — Captured Research (v1)

**Captured:** 2026-08-10
**Status:** ⚠️ **UNVERIFIED — DO NOT PROMOTE TO SEED DATA AS-IS**
**Source medium:** four social-media infographic cards (Instagram/Reel-style
carousels) supplied by the user. No publisher, author, or publication date is
visible on any of the four. Mute icons in the corners indicate these are video
frames, not documents.

---

## Why this file exists and what it is not

`backend/seeds/catalog/transfer_links.yaml` calls itself "the most dangerous file
in the repo," and every row there carries a named `source` plus a `verified_on`
date. These infographics meet neither bar: they are uncredited marketing
creative, and marketing creative is exactly the medium in which stale ratios
survive longest.

This file is therefore a **research capture**, not a data source. Its job is to
(a) preserve the claims before the images are lost, (b) record where they agree
and disagree with the seeded catalog, and (c) name the specific things to verify.

Related: [`singapore_airlines_krisflyer_indian_credit_card_research_v1.md`](./singapore_airlines_krisflyer_indian_credit_card_research_v1.md).

---

## 1. Claimed ratios, as extracted

All four cards use the same three HDFC card labels. Mapping to catalog currency
slugs: "Infinia" and "DCB Metal" / "Diners Club Black Metal" → `hdfc-rp-premium`;
"Regalia Gold" → `hdfc-rp-regalia`.

| Destination program | Regalia Gold | Infinia | Diners Club Black Metal |
|---|---|---|---|
| Singapore Airlines KrisFlyer | 2:1 | 1:1 | 1:1 |
| Finnair Plus (Avios) | 2:1 | 1:1 | 1:1 |
| Flying Blue (Air France/KLM) | 2:1 | 1:1 | 1:1 |
| Accor Live Limitless (ALL) | **3:1** | **2:1** | **2:1** |

Read as `ratio_from : ratio_to` — points consumed : miles credited, matching the
seed file's convention.

---

## 2. Cross-check against the seeded catalog

| Claim | Seeded value | Verdict |
|---|---|---|
| `hdfc-rp-premium` → `krisflyer` 1:1 | 1:1 | ✅ agrees |
| `hdfc-rp-regalia` → `krisflyer` 2:1 | 2:1 | ✅ agrees |
| `hdfc-rp-premium` → `accor-all` 2:1 | 2:1 | ✅ agrees |
| `hdfc-rp-regalia` → `accor-all` 3:1 | **2:1** | ❌ **CONFLICT** |
| `hdfc-rp-*` → Finnair Plus | *absent* | 🆕 new partner |
| `hdfc-rp-*` → Flying Blue | *absent* | 🆕 new partner |
| `hdfc-rp-*` → British Airways / Qatar | *absent* | 🆕 new partner |

### 2.1 The one conflict — Regalia Gold → Accor — ✅ RESOLVED 2026-08-10

The infographic claimed **3:1**. [`transfer_links.yaml:210-221`](../../backend/seeds/catalog/transfer_links.yaml)
seeds **2:1**, sourced to the pointsmath.com HDFC table (updated 2026-06-21) and
verified 2026-07-04.

**Resolution: 2:1 is correct — user-confirmed 2026-08-10. The infographic is
wrong. No seed change required.**

Recorded because the reasoning is worth keeping: "same as premium tier for this
partner" is anomalous — Regalia is worse than premium for every *other* partner
in the catalog — so 3:1 looked directionally plausible on structure alone. It
isn't. Accor is a genuine exception where both HDFC tiers transfer at the same
ratio, and that anomaly should not be re-litigated next time someone notices it.

---

## 3. The Avios backdoor — the strategically important item

The Finnair card documents a multi-hop routing technique rather than a single
ratio, and it is the most product-relevant thing in the four images.

**Claimed problem:** transferring HDFC points *directly* to British Airways
Executive Club or Qatar Airways Privilege Club runs at 2:1 — an instant 50%
value loss.

**Claimed workaround:**

1. HDFC points → **Finnair Plus** at **1:1** (no loss)
2. Finnair Plus Avios → **British Airways Executive Club** — "instant & free,
   same currency"
3. British Airways → **Qatar Airways Privilege Club** — bridge

**Claimed outcome:** full 1:1 value preserved, unlocking premium cabins such as
Qsuites.

The underlying mechanic is real and well documented outside this source: Avios
is a shared currency across British Airways, Iberia, Aer Lingus, Finnair, Qatar
and Vueling, and balances move between those programs directly. The claim to
verify is not "does Avios move between programs" (it does) but the three
specifics below.

### 3.1 Why this matters architecturally, not just as data

The current schema models transfers as a **single hop**: `currency → partner`,
one row per link. This technique is a **three-hop path** whose end-to-end
effective ratio (1:1) is strictly better than the modeled direct link (2:1).

An optimizer that only reads `currency_transfer_partners` will never find it. It
will confidently recommend the 50%-worse route — which is precisely the failure
mode the product exists to prevent.

That is a **design question for the Optimization Engine, not a seed-data
question**, and it should not be answered by quietly adding a synthetic
"HDFC → Qatar 1:1" row. Options worth weighing, in rough order of increasing
cost:

- treat Avios as a single reward currency with member programs (models reality
  most closely, and the intra-Avios move is genuinely free)
- add an explicit `partner → partner` link table and let the optimizer search
  paths of length ≤ 2
- keep single-hop and encode known good paths as curated named routes

Whichever way it goes, it needs a decision-log entry per the Backend Build Rules
(no new top-level concept without one).

---

## 4. Supporting claims (context, all unverified)

**KrisFlyer** — "the anchor for Star Alliance redemptions." Spontaneous Escapes
promo: up to 30% off miles on Economy, Premium Economy and Business. Claimed to
be the *only* way to book Singapore Airlines First Class Suites, which are not
available to partner programs. The Suites claim is consistent with the existing
KrisFlyer research doc and is a genuine differentiator for the MVP's primary goal.

**Flying Blue** — positioned as SkyTeam access (Delta, Saudia, Vietnam Airlines
named). "Promo Rewards" engine claimed at 25–50% off mileage redemptions on
monthly rotating routes. Combined claim: 1:1 transfer + 50% promo discount.

**Accor ALL** — claimed floor value of **₹2 per point, guaranteed**, with no
dynamic pricing; 30+ onward airline partners; onward transfer power quoted as
1:1 (select), 2:1 (major airlines), up to 1:1.25 (best case); claimed realistic
upside ₹4–₹5 per point.

The Accor ₹2/point floor is the single most useful number here for the Valuation
Engine *if it holds* — a guaranteed floor is rare and makes Accor a natural
worst-case anchor for reward valuation. Verify before relying on it.

---

## 5. Verification checklist before any of this reaches a seed row

Ordered by impact:

1. ~~**Regalia Gold → Accor: 2:1 or 3:1?**~~ — ✅ **RESOLVED 2026-08-10: 2:1.**
   Seed was already correct; infographic wrong. See §2.1.
2. **Finnair Plus as an HDFC partner** — confirm it exists on HDFC SmartBuy and
   confirm the 1:1 premium-tier ratio.
3. ~~**Avios inter-program movement**~~ — ✅ **VERIFIED 2026-08-10.** Free, 1:1,
   between British Airways, Iberia, Aer Lingus, Finnair and Qatar; usually
   instant, up to 24h. Caveats: Qatar and Finnair route via **British Airways as
   the hub** (two-stage, handled inside "Combine My Avios" at avios.com);
   accounts must share the same name and matching details; 2FA required on every
   account. See [`accor-outbound-transfer-partners-v1.md`](./accor-outbound-transfer-partners-v1.md) §2.
4. **Flying Blue as an HDFC partner** and its ratios.
5. **BA / Qatar direct ratios from HDFC** — the 2:1 figure is the premise of the
   whole backdoor argument and is currently unverified.
6. **Accor's ₹2/point floor** — confirm and date it.
7. For every one of the above, capture `source` + `verified_on` in the seed row,
   and prefer a primary source (HDFC SmartBuy, the program's own site) over an
   aggregator.

Until items 1–6 are checked, nothing in this document belongs in
`transfer_links.yaml`, `partners.yaml`, or `currencies.yaml`.
