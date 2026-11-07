# SaveSage Teardown v1

**Date:** 2026-11-02 · **Method:** REA (`rea-agents` 6.8.0) attached to an isolated Chrome profile over CDP, plus SaveSage's public `llms.txt`, `llms-cards.txt`, `robots.txt` and sitemap. **Scope:** public, logged-out web pages only. We did not log in, call `/api/` directly (it is disallowed in `robots.txt`), decompile the app, or copy any SaveSage data into our catalog. The calculator was used once, the way any visitor would use it, while REA recorded the *shapes* of the requests and responses (field names and types, not values).

**Status:** research input. Nothing here is a decision yet. §4 is the part that needs action.

---

## 1. What SaveSage is

An Indian rewards-management app (iOS/Android, launched Oct 2024). It makes money from **paid subscriptions** (Pro / Elite / Private), **bill payments over NPCI Bharat Connect** (with an IndiGo BluChip earn tie-up), gift cards, and **1-on-1 human expert consultations** (Elite). The website exists mainly to bring in search traffic and send people to the app.

## 2. What the web surface covers

| Surface | What it does | OptiMILES equivalent |
|---|---|---|
| ~757 card pages (`/credit-card/<slug>`), 40 bank hubs, 42 issuers in the calculator picker | Fees "at a glance" with plain-English glosses ("Only if you don't pay the full bill"), forex markup, interest rate, add-on card, earn categories, an **"Earns nothing on these"** exclusion list, caps such as "₹2L/month eligible · min ₹100/txn" | 9 cards, verified tier only |
| 23 "best-for" collections (lifetime-free, zero-forex, RuPay-for-UPI, lounge under ₹1k, …) | Fixed curated lists | None |
| Lounge by airport (`/credit-cards/lounge`) | 36 airports, 62 lounges, terminal by terminal, which cards get you in | Card-side lounge model shipped 2026-08-31; airport directory deliberately deferred |
| Rewards calculator | Bank + card + **one** category + monthly spend → your card vs. a "suggested" card | Best Card for this Spend |
| Devaluation tracker | Dated list of issuer changes, written as a blog post and updated by hand | None |
| `llms.txt`, `llms-cards.txt`, `llms-full.txt` | Machine-readable index written for AI crawlers | None |

Gating: the card pages show 2 of 5 earn categories ("We track all 5… see the full breakdown in the app"). The calculator's suggested card is blurred until you tap through to sign up.

## 3. How the calculator works

REA captured two calls:

```
GET  /api/reward-calculator/banks/{bankId}/cards  → [{id, label, value, isPopular, cardImageLink}]
POST /api/reward-calculator/calculate
     req  {bankId, cardId, categorySlug, spendAmount}
     resp {annualSavings,
           userCard:      {cardId, cardName, bankName, rewardPoints, rewardWorth, isCashbackCard, blurUntilReveal, …},
           suggestedCard: {…same…},
           suggestedCardIsSame}
```

All the logic runs on their server, and the response contains **no working**: no earn rule, no cap, no ₹-per-point basis, no source. Only one category can be entered, so it is not a spend mix. `blurUntilReveal` sits in the response itself, so the gate is a product choice, not a UI accident.

**Observed result (Axis Atlas, Travel, ₹50,000/month):**

- The headline says "You earn **₹6.5k**/month → Earn up to **₹20k**/month (₹1.6L/year)".
- The panels say "Axis Atlas: **1.3k** points, worth up to **₹3.5k**" and "Suggested: 10.7k points, worth up to **₹10.7k**".
- The headline and the panels disagree. The ₹1.6L comes from the headline numbers: (20k − 6.5k) × 12. The panels would give ≈ ₹86k.
- The two surfaces value miles differently. The Atlas card page says "Return 2% to 5%", which implies ≈ ₹1 per EDGE Mile. The calculator implies ≈ ₹2.7 per mile (3.5k ÷ 1.3k).

Their headline stats also contradict each other: users are "10L+" (calculator), "7.5 Lakh+" (home) and "50,000+" (press, Mar 2025); cards are "700+", "757" and "1,000+".

**Why this matters:** they are broad and their numbers cannot be checked. This is the exact gap CLAUDE.md names: *"as comprehensive as the competition, and the only one whose numbers you can check."* The calculator is the clearest side-by-side we could ask for.

## 4. Stale seed rows — needs action

Their devaluation tracker named changes to cards in **our engine-eligible core**. We checked three against independent sources (see links). All three hold up, and our seeds are out of date:

| Card | Our seed | Reported current | Independent sources |
|---|---|---|---|
| **SBI Cashback** | online 5%, `monthly_cap_inr: 100000` (₹5k cashback), verified 2026-07-04 | From **1 Apr 2026**: ₹2,000 online cap + ₹2,000 offline cap **per statement cycle**, ₹4,000 combined; gaming, toll and govt/tax excluded | [LiveFromALounge](https://livefromalounge.com/sbicards-cashback-card-imposes-new-restrictions-effective-april-1-2026/), [CardInsider](https://cardinsider.com/blog/sbi-cashback-credit-card-devaluation/), [PickMyCard](https://www.pickmycard.in/blog/sbi-cashback-card-devaluation-2026), [SBI PDF](https://www.sbicard.com/sbi-card-en/assets/docs/pdf/cashback-revised.pdf) |
| **HDFC Regalia Gold** | base `2.67` (4 RP/₹150), verified 2026-07-04 | From **15 May 2026**: 5 RP/₹200 = **2.50**; domestic lounge gated at ₹60k/quarter | [CardInsider](https://cardinsider.com/blog/hdfc-regalia-gold-credit-card-revision/), [PickMyCard](https://www.pickmycard.in/blog/hdfc-regalia-gold-devaluation-2026), [Paisabazaar](https://www.paisabazaar.com/credit-card/hdfc-credit-card-revisions/) |
| **Amex Platinum Travel** | ₹1.9L → 15,000 MR; ₹4L → 25,000 MR; lounge 8/yr, 2/quarter (verified 2026-08-31) | ₹1.9L bonus **removed** from 10 Sep 2026; ₹4L → **10,000**; ₹7L → ₹20k Taj voucher, no points; domestic lounge **₹1L prior-quarter spend** gate from 1 Oct 2026 | [InsideFlyer](https://www.insideflyer.com/posts/amex-platinum-travel-card-loses-inr-1-9l-milestone-lounge-access-now-requires-sp/), [LiveFromALounge](https://livefromalounge.com/american-express-platinum-travel-card-gets-another-devaluation-inr-1-9-lakh-milestone-removed-inr-7-lakh-milestone-rewards-cut-lounge-access-gets-a-spend-condition/), [CardInsider](https://cardinsider.com/blog/american-express-platinum-travel-devalued-again/) |

Also from their tracker, **not yet checked** against our seeds: HDFC Infinia SmartBuy voucher cap (3,000 RP/month from 1 Jul 2026), Infinia retention criteria, and Axis transfer-group and ratio changes (Sep 2026). We carry no Amex→Etihad or Axis→ITC rows, so those removals don't affect us.

**Our own gap:** Axis Atlas earn-category rows are `needs_verification: true` ("market knowledge — VERIFY") even though Atlas is in the depth-verified core. Under the tiered-coverage rule, the engine should not be optimizing over them.

**What this says about our process:** two rows were stamped `verified_on` *after* the issuer change and still carry the old values. Our verification checks a row once and never re-checks it. Devaluations are now frequent enough (issuers changed something roughly every month in 2026) that a `verified_on` date tells you when someone last looked, not that the row is still current.

None of these values may be edited into `seeds/` from this document. Per CLAUDE.md, the fix is a seed PR verified against **issuer** terms and reviewed line by line. SaveSage and the blogs above are leads, not sources.

## 5. What to take, and what not to

**Take (fits the constitution):**

1. **A "what changed" catalog feed.** Our rows already carry `source` + `verified_on`, which they do not have. A dated, row-level change log ("Regalia Gold base rate 2.67 → 2.50, effective 15 May, source: …") is a *sourced* devaluation tracker. It gives people a reason to come back during the months they are building up points, and our data model already supports it. Pair it with a **re-verification cadence** (e.g. every core row re-checked at least quarterly) so §4 doesn't happen again.
2. **Show the working in the calculator.** Best Card already computes from rules. On the page, show per-card: earn rule → points → cap applied → (optional, user-chosen) valuation, with `source` + `verified_on`. Their calculator can't do this, so it is the clearest place to prove the difference.
3. **More card fields we lack:** forex markup, interest rate, add-on card fee, and an explicit **"earns nothing on"** list (we model exclusions; we don't *show* them as a list). Copy their plain-English glosses ("Only if you don't pay the full bill"). It fits our "no fintech jargon" rule.
4. **"Best-for" collections built on the listed tier.** These are informational pages that the broadened scope now allows. Each must say which tier it rests on and end in a recommendation, not a table.
5. **`llms.txt` for OptiMILES.** It costs almost nothing, and it matters more for a product whose selling point is citable numbers.

**Don't take:**

- **Gating and blurring answers to drive sign-ups.** "Tap to reveal card" works against "every number shows its working".
- **Headline numbers we can't trace to a source** ("₹170 Cr+ saved", "3.2× more rewards", "14% average return"). Our stats should be computed and come with their source, or we don't print them.
- **A ₹-per-point valuation without a source.** Their two surfaces imply different valuations for the same mile. This is exactly the "never invent a number" rule.
- **Bill payments, credit score, human consultations.** These are a different business (BBPS licensing, ops headcount). Not rejected forever, but outside "rewards, not banking" for now.
- **An airport lounge directory.** Still deferred per `2026-08-31-lounge-access-model.md`. Their 36-airport page shows demand, but our card-side conditions (spend gates, quarterly caps) are the part they get wrong. §4 shows the spend gates are now the norm.

## 6. Where the line is, and what their public terms reveal

**Their engines can't be reverse-engineered, and we shouldn't try.** Recommendations, Savvy and portfolio tracking all run on SaveSage's servers. No tool can see inside them. Decompiling the app or intercepting its traffic would only show what the phone receives, which is the same kind of output-only result as §3. Their [Terms of Use](https://savesage.club/terms-condition) also forbid it outright: *"you shall not attempt to decompile or reverse engineer or reverse compile our technology/software that is available on the App/Website"*, and for the chatbot, *"Users must not attempt to exploit, spam, or reverse-engineer the chatbot."* REA's own disclaimer excludes copying proprietary software. **So: no APK decompilation, no traffic interception of the app, no prompt-extraction of Savvy.** Note that §3 (recording the calculator's request/response field names in the browser) also arguably falls under that broad clause. Keep it internal, and don't repeat it.

**Their public terms work as a feature spec.** The terms page lists:

- **Savvy (AI chatbot):** answers come from the user's saved cards, reward balances and transaction history. It has thumbs up/down feedback, says it is in a "learning and training phase", and tells users to *"double-check financial information like reward rates."*
- **ROI Guarantee (annual plans):** if savings are below **2× the subscription fee**, the fee is refunded. "Savings" includes points at a valuation "standardized by SaveSage". The user must link all cards and *follow the recommendations*. *"Final determination of savings rests solely with SaveSage's evaluation framework."* Outside the guarantee, subscriptions are non-refundable.
- **Bill payments (BBPS) with earn partners:** IndiGo BluChip, and Flipkart SuperCoins as an "Active Earn Partner" for paid plans only. Cashback is offered on bill payments and referrals.
- **Bundles:** HDFC Ergo cyber insurance, personal accident cover, Care Health insurance, EazyDiner Prime, Yatra.

**What this means for us:** their ROI guarantee is the strongest claim they make, and it is judged by their own hidden valuation. We could offer a version the user can check: a **realized-value ledger** built from Phase 2 spend logging and the activity log, where every rupee of claimed value traces to a catalog row and a logged transaction. Same promise, but the user can audit it. Worth taking through `feature-discussion`.

**Other legitimate channels for further teardown:** using the app as an ordinary member (to observe the experience, not to copy flows); App Store and Play listings, screenshots and release notes; public user reviews, which are a direct source of their users' pain points; their blog and `llms-full.txt`.

## 7. Multi-source research (2026-11-02)

Four research agents each covered one group of public, logged-out sources:

1. **iOS App Store:** listing, 25 versions of release notes, 908 reviews.
2. **Google Play:** listing, Data safety section, 4,081 reviews (Apr–Nov 2026).
3. **Community:** TechnoFino, DesiDime, Product Hunt, competitor comparison pages. Reddit was not reachable, and TechnoFino came through search-engine snippets only.
4. **Company and content:** press, funding, pricing, and the 130-article blog.

A finding counts as **confirmed** only when at least two independent source groups agree. Theme counts come from keyword coding: they show direction, not exact numbers.

### 7.1 Snapshot

| | Value | Source |
|---|---|---|
| Installs | 1.13M on Play. Crossed 500K on 2026-04-05 and 1M on 2026-09-06 | Play, AndroidRank |
| Ratings | iOS **4.1** (8,804 ratings, 1,441 of them 1★). Play **4.0** (16,597 ratings, 21% 1★). The site claims "4.8" | stores, homepage |
| Rating trend | New Play reviews averaged ~4.2–4.4 from May to Aug, then **2.65 in Sep and 2.54 in Oct**, after the Sep redesign | Play reviews |
| Funding | ₹2.5 Cr angel (Dec 2024), then $1M pre-seed (Oct 2025), then Shark Tank ₹4 Cr for 9% (Jan 2026). $1.1M ARR claimed (Sep 2025) | press |
| Pricing | Not published anywhere. Users report **Pro ₹99/month or ₹399/year**, **Elite ~₹999/quarter to ₹1,699**, **Private ₹9,999/quarter or ₹14,999/year**. iOS subscriptions are billed outside Apple, through UPI autopay | reviews, coupon sites |
| Ship cadence | Roughly weekly releases on both platforms | store histories |
| Content | 130 articles. Output rose to ~3.5 a week from mid-2026. Devaluations are published on the day they are announced, typically **~30 days before they take effect**. **No article links an issuer notice.** 122 of the 130 articles carry the same bulk-restamped `dateModified` | blog, llms-full.txt |

**2026 feature sequence (iOS release notes):**

- Outlook/Yahoo statement sync and points-expiry alerts (Jan–Mar)
- Expert chat (Feb)
- Expense tracking (Mar)
- FD-backed credit-builder card, and loan recommendations (Apr)
- **Scan & Save**, which suggests how to pay at checkout (May)
- **Flights in cash vs points**, and **Spend Insights**, which shows what you "missed" by using the wrong card (May)
- Personal-loan offers (Aug)
- Full redesign (Sep)
- Bill payments with Flipkart SuperCoins (Oct)

Their monetisation keeps spreading: subscriptions, bill-pay earn partners (IndiGo BluChip, Flipkart SuperCoins), gift cards for 250+ brands, loan and insurance referrals, and human experts.

### 7.2 Confirmed findings, ranked

| # | Finding | Found in | Evidence |
|---|---|---|---|
| 1 | **They charge before showing anything.** No trial, prices not shown, upgrade pressure, refunds refused | iOS, Play, community, company | iOS: 161 of 201 reviews at ≤2★ mention paying. Play: 127 paywall reviews and 44 refund reviews. A 1★ wave followed Shark Tank. In Aug 2025 they paywalled bill pay and then reversed it |
| 2 | **Their numbers can't be trusted or traced** | iOS, Play, community, company, our §3 capture | "saving amount shown is fictitious". Points shown at "₹300" when the bank says ₹2k. "doesn't take into account the milestone benefits". A wrong Infinia transfer ratio. Users, cards and the calculator all contradict each other (§3, §7.1) |
| 3 | **Savvy loses to free ChatGPT and Gemini** | iOS, Play, community | iOS: 20 of 25 Savvy reviews negative, plus 20 more saying "ChatGPT gives the same". Play: 139 Savvy reviews, split |
| 4 | **Advice is generic** ("tells me what I already know") | Play, iOS, community | Play: 168 reviews, averaging 1.09★. "recommend the same two cards for any purchase". Power users say what's missing is milestones, caps and MCC detail |
| 5 | **Getting data in is unreliable, and it costs trust** | iOS, Play, community | ~47 reviews about manual entry, sync breaks and full Gmail access. The Play Data safety section says *"No data collected"* while the app requests **READ_SMS**. The iOS privacy label declares only "Usage Data" |
| 6 | **Recommendations look commission-driven** | iOS, Play, company | "commission ka game"; "card suggestions seemingly driven by commissions". Loans, insurance and card applications are part of the product |
| 7 | **Their ratings look inflated.** Observed, not proven | iOS, Play, community | iOS: 425 of the 908 reviews arrived in Jul–Aug, almost all 5★, many on a template. Play: 1,261 five-star reviews of ≤25 characters. 889 of their 1,056 developer replies go to 5★ reviews |

**What users actually like** (iOS and Play):

- Gift cards and vouchers at full value with no fee (Play: 120 reviews, 4.5★)
- Travel-on-points redemption wins (iOS: 26 positive)
- Seeing all points in one place
- Being told which card to use

Their distribution also works: search pages, `llms.txt` that welcomes AI crawlers, and Shark Tank exposure.

**Top unmet needs** (community, confirmed by Play):

1. Tracking progress on milestones, fee waivers and caps
2. Accurate card data plus alerts when a card is devalued
3. "Which card for this purchase"
4. Automatic sync without handing over the whole inbox
5. Trying the app before paying
6. Points-expiry and renewal reminders
7. Knowing which MCC a payment is coded under, and whether it earns

**Competitors that came up:**

- **Krediit** (iOS, ₹599/yr): advertises caps and exclusions applied, a lounge directory and cap logging. It is positioned closest to us.
- **PointsFly** (₹2,999/yr)
- **CRED**: free bill pay, now adding milestone tracking
- **TrackCards**: a fee-waiver tracker built by a TechnoFino member
- **Magnify**, **CheQ**

### 7.3 What this means for OptiMILES

Every confirmed weakness above is something our constitution already commits us to avoid. The opportunity is to make that difference *visible* to users. Ranked:

1. **P0: Fix our own data before we claim to be the accurate one.** The stale rows in §4 matter all the more given finding #2. Two process changes:
   - Add an **"announced, effective from"** state to catalog rows. SaveSage publishes on the day a change is announced, and we are currently months behind the day it takes effect.
   - Run a **re-verification cadence** on the core cards.
2. **P1: Answer for free, with the working shown, before asking for anything.** This counters #1, #2 and #4. Best Card and Portfolio should answer without sign-up or payment. Each number should show rule → cap → points → issuer source link + `verified_on`. A point valuation appears only when the user chooses one.
3. **P1: Milestone, cap and fee-waiver progress from the activity log.** This is the top unmet need, and it counters #4. The activity log already in progress (`2026-09-02-activity-log-unified.md`) is the right foundation. MCC exclusions should be shown line by line.
4. **P2: A sourced change feed.** A devaluation tracker where every entry links the issuer notice and the catalog row it changed. It brings people back to the app and is something SaveSage cannot copy cheaply.
5. **P2: Make our trust posture an explicit product promise.** No inbox access, no SMS reading, manual entry or CSV only, published prices, and a stated position on commissions. Only claim what is true: we would need to decide the affiliate question first. This counters #5 and #6.
6. **P2: Make our sourced numbers what AI assistants cite.** Add `llms.txt` and per-card pages that carry their working in machine-readable form.
7. **Later: a realized-value ledger that users can audit** (§6), as a checkable alternative to SaveSage's ROI guarantee.
8. **Later, informational only: a voucher and gift-card route guide.** Which purchase routes earn what, under which caps (e.g. the SmartBuy voucher cap from §4). This is their most-praised feature, and we would cover it as sourced information without becoming a seller.

**Confirmed not to copy:**

- Paywalling the first answer
- Ungrounded chat
- Loan and insurance cross-sell
- Inbox and SMS scraping
- Headline statistics we cannot source

**Gaps in this research:** Reddit; full TechnoFino threads; official SaveSage prices (served only from their disallowed `/api/`); Play reviews before Apr 2026; any first-hand account of claiming the ROI guarantee. The ROI guarantee itself *is* confirmed in their [Terms](https://savesage.club/terms-condition) (§6), even though the company-research agent could not find it on their marketing pages. The raw review exports were kept in the session scratchpad and are not committed.

## 8. Reproducing this

REA is installed per-project. Node 24 and `rea-agents` live under `.tools/` (gitignored), and it is registered with `claude mcp add --scope local`, so it is in `~/.claude.json` under this project only. Its MCP tools load in a fresh Claude Code session. Website analysis needs a Chrome started with `--remote-debugging-port` and a throwaway `--user-data-dir`. REA does not launch Chrome itself.
