# OptiMILES — Database Schema v1
**Document Type:** Backend Architecture  
**Version:** 1.0.0 — **amended by v1.1, see banner**  
**Status:** MVP Draft  

> **v1.1 AMENDMENT (2026-07-03, decided):** the authoritative deltas live in
> [`backend-build-plan-v1.md`](backend-build-plan-v1.md) §3 — (1) new `reward_currencies`
> table; (2) `cards.points_currency` TEXT → `reward_currency_id` FK; (3)
> `card_transfer_partners` replaced by **`currency_transfer_partners`** (transfer
> relationships belong to currencies, not cards — RKE spec AD-04, build plan D-1);
> (4) lineage columns (`catalog_snapshot_version`, `engine_version`) on
> `simulation_results` / `recommendation_outputs`. No migration has ever run, so the
> amendment applies to the initial DDL. Fold into a `db-schema-v2.md` at leisure.

**Focus:** Singapore Airlines KrisFlyer · Indian Travel Credit Cards · Reward Optimization  

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Entity Overview](#2-entity-overview)
3. [Schema Definitions](#3-schema-definitions)
   - 3.1 [Reference / Catalog Layer](#31-reference--catalog-layer)
   - 3.2 [User Layer](#32-user-layer)
   - 3.3 [Simulation Layer](#33-simulation-layer)
   - 3.4 [Recommendation Layer](#34-recommendation-layer)
4. [Relationships & ERD Notes](#4-relationships--erd-notes)
5. [Indexes](#5-indexes)
6. [Scalability Considerations](#6-scalability-considerations)
7. [Design Decision Log](#7-design-decision-log)
8. [Future Extension Points](#8-future-extension-points)

---

## 1. Design Philosophy

| Principle | Application |
|---|---|
| **Normalize catalog data aggressively** | Cards, categories, transfer partners, and award charts are reference data. They must be clean, versioned, and card-level granular — not duplicated across user rows. |
| **Keep simulation state in its own layer** | Simulations are ephemeral user experiments, not truth. They get their own tables with clear FK lineage to catalog and goals. |
| **AI output is an artifact, not business logic** | Recommendation outputs are stored as structured JSONB + text — easy to regenerate, audit, and version. Never encode LLM reasoning in core tables. |
| **JSONB for flexibility at the edges** | Use JSONB only for genuinely variable/supplemental data (e.g., card metadata, allocated spend breakdowns). Never for anything you'll query or filter on. |
| **MVP scope = narrow and deep** | Tables are scoped to SQ KrisFlyer + Indian travel cards. Schema is extensible but not pre-built for everything. |

---

## 2. Entity Overview

```
CATALOG LAYER (reference / admin-managed)
┌─────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   cards     │────▶│ reward_categories │     │ transfer_partners │
└─────────────┘     └───────────────────┘     └───────────────────┘
       │                                               │
       └───────────────┐               ┌──────────────┘
                       ▼               ▼
               ┌────────────────────────────┐
               │   card_transfer_partners   │  (junction)
               └────────────────────────────┘
       │
       ▼
┌──────────────────┐     ┌───────────────┐
│ reward_milestones│     │ award_charts  │
└──────────────────┘     └───────────────┘

USER LAYER (per-user state)
┌─────────┐     ┌────────────┐     ┌────────────┐
│  users  │────▶│ user_cards │     │ user_goals │
└─────────┘     └────────────┘     └────────────┘

SIMULATION LAYER (user experiments)
┌──────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ spend_simulations│────▶│simulation_line_items  │     │ simulation_results │
└──────────────────┘     └──────────────────────┘     └────────────────────┘

RECOMMENDATION LAYER (AI output artifacts)
┌────────────────────────┐
│  recommendation_outputs│
└────────────────────────┘
```

---

## 3. Schema Definitions

### 3.1 Reference / Catalog Layer

> Admin-managed, relatively static. Seeded during setup. Users read, never write.

---

#### `cards`

Represents an Indian travel credit card product.

```sql
CREATE TABLE cards (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  bank               TEXT        NOT NULL,           -- 'HDFC', 'Axis', 'Amex', 'ICICI', 'SBI'
  card_name          TEXT        NOT NULL,           -- 'Infinia Metal', 'Atlas', 'Platinum Travel'
  card_network       TEXT        NOT NULL,           -- 'Visa', 'Mastercard', 'Amex'
  points_currency    TEXT        NOT NULL,           -- 'SmartPoints', 'Edge Miles', 'MR Points'
  annual_fee_inr     INTEGER     NOT NULL DEFAULT 0,
  joining_fee_inr    INTEGER     NOT NULL DEFAULT 0,
  base_earn_rate     NUMERIC(6,2) NOT NULL,          -- points per ₹100 on uncategorized spend
  min_income_inr     INTEGER,                        -- eligibility floor (nullable = not published)
  has_lounge_access  BOOLEAN     NOT NULL DEFAULT FALSE,
  is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
  metadata           JSONB,                          -- supplemental: forex markup %, welcome offer, etc.
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE cards IS 'Master catalog of Indian travel credit cards supported by OptiMILES.';
COMMENT ON COLUMN cards.base_earn_rate IS 'Points earned per ₹100 on non-accelerated spend. Used as fallback earn rate.';
COMMENT ON COLUMN cards.metadata IS 'Flexible bag for non-queryable card attributes: forex_markup_pct, welcome_bonus_points, etc.';
```

**Seed examples:**

| bank | card_name | points_currency | base_earn_rate | annual_fee_inr |
|---|---|---|---|---|
| HDFC | Infinia Metal | SmartPoints | 5.00 | 12500 |
| Axis | Atlas | Edge Miles | 5.00 | 5000 |
| Amex | Platinum Travel | MR Points | 1.00 | 60000 |
| ICICI | Emeralde | ICICI Points | 4.00 | 12000 |

---

#### `reward_categories`

Earn rates per spend category per card. One card → many category rows.

```sql
CREATE TABLE reward_categories (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  card_id            UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  category_slug      TEXT        NOT NULL,   -- machine key: 'travel', 'dining', 'international', 'fuel', 'groceries', 'default'
  category_label     TEXT        NOT NULL,   -- human label: 'International Spends'
  earn_rate          NUMERIC(6,2) NOT NULL,  -- points per ₹100 in this category
  monthly_cap_inr    INTEGER,                -- NULL = no cap on accelerated earn
  quarterly_cap_inr  INTEGER,
  annual_cap_inr     INTEGER,
  notes              TEXT,                   -- e.g. 'Excludes fuel surcharge waiver', 'Only on MakeMyTrip'
  is_active          BOOLEAN     NOT NULL DEFAULT TRUE,

  CONSTRAINT uq_card_category UNIQUE (card_id, category_slug)
);

COMMENT ON TABLE reward_categories IS 'Accelerated earn rates per spend category per card.';
COMMENT ON COLUMN reward_categories.category_slug IS 'Canonical slug matching the simulation line item category. Must be consistent across all cards.';
COMMENT ON COLUMN reward_categories.monthly_cap_inr IS 'Maximum eligible spend per month at this earn rate. Spend beyond the cap earns at base_earn_rate.';
```

**Canonical `category_slug` values (enforced at application layer):**

```
travel         → flights, hotels booked via any channel
dining         → restaurants, food delivery
international  → transactions in foreign currency
fuel           → petrol pumps
groceries      → supermarkets, grocery stores
utilities      → electricity, water, gas bills
online         → e-commerce (Amazon, Flipkart, etc.)
default        → all other spend (maps to card's base_earn_rate)
```

---

#### `transfer_partners`

Airlines and hotel programs that accept point transfers from Indian cards.

```sql
CREATE TABLE transfer_partners (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_name   TEXT        NOT NULL,     -- 'Singapore Airlines'
  program_name   TEXT        NOT NULL,     -- 'KrisFlyer'
  partner_type   TEXT        NOT NULL,     -- 'airline' | 'hotel'
  iata_code      TEXT,                     -- 'SQ' (airlines only)
  alliance       TEXT,                     -- 'Star Alliance', 'SkyTeam', 'oneworld' (nullable)
  is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
  metadata       JSONB,                    -- logo_url, website, program notes
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_partner_type CHECK (partner_type IN ('airline', 'hotel'))
);

COMMENT ON TABLE transfer_partners IS 'Loyalty programs that Indian credit card points can be transferred into.';
```

**MVP seed (SQ-focused):**

| partner_name | program_name | partner_type | iata_code |
|---|---|---|---|
| Singapore Airlines | KrisFlyer | airline | SQ |
| Air India | Flying Returns | airline | AI |
| Vistara | Club Vistara | airline | UK |
| Marriott | Bonvoy | hotel | — |

---

#### `card_transfer_partners`

Junction table: which cards can transfer to which programs, and at what ratio.

```sql
CREATE TABLE card_transfer_partners (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  card_id               UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  partner_id            UUID        NOT NULL REFERENCES transfer_partners(id) ON DELETE CASCADE,
  ratio_from            INTEGER     NOT NULL DEFAULT 1,   -- card points consumed
  ratio_to              INTEGER     NOT NULL DEFAULT 1,   -- partner miles credited
  min_transfer_points   INTEGER     NOT NULL DEFAULT 1000,
  transfer_fee_inr      INTEGER     NOT NULL DEFAULT 0,
  processing_days_min   INTEGER     NOT NULL DEFAULT 1,
  processing_days_max   INTEGER     NOT NULL DEFAULT 5,
  is_active             BOOLEAN     NOT NULL DEFAULT TRUE,
  notes                 TEXT,

  CONSTRAINT uq_card_partner UNIQUE (card_id, partner_id)
);

COMMENT ON TABLE card_transfer_partners IS 'Transfer ratios and mechanics between card points and loyalty program miles/points.';
COMMENT ON COLUMN card_transfer_partners.ratio_from IS 'Card points consumed per unit. E.g. ratio_from=2, ratio_to=1 means 2 SmartPoints → 1 KrisFlyer mile.';
```

**Example rows:**

| card | partner | ratio_from | ratio_to | min_transfer | processing_days |
|---|---|---|---|---|---|
| HDFC Infinia | KrisFlyer | 2 | 1 | 1000 | 2–5 |
| Axis Atlas | KrisFlyer | 2 | 1 | 500 | 1–3 |
| Amex Platinum | KrisFlyer | 2 | 1 | 1000 | 2–5 |

---

#### `reward_milestones`

Bonus points awarded when a user crosses defined spend thresholds.

```sql
CREATE TABLE reward_milestones (
  id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  card_id              UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  milestone_type       TEXT        NOT NULL,          -- 'spend_bonus', 'welcome_bonus', 'anniversary_bonus', 'category_bonus'
  spend_threshold_inr  INTEGER,                       -- NULL for non-spend-triggered bonuses
  bonus_points         INTEGER     NOT NULL,
  period               TEXT        NOT NULL DEFAULT 'annual',  -- 'monthly', 'quarterly', 'annual', 'one_time'
  description          TEXT,                          -- human-readable explanation
  valid_from           DATE,
  valid_until          DATE,
  is_active            BOOLEAN     NOT NULL DEFAULT TRUE,

  CONSTRAINT chk_milestone_type CHECK (
    milestone_type IN ('spend_bonus', 'welcome_bonus', 'anniversary_bonus', 'category_bonus')
  ),
  CONSTRAINT chk_period CHECK (
    period IN ('monthly', 'quarterly', 'annual', 'one_time')
  )
);

COMMENT ON TABLE reward_milestones IS 'Bonus point thresholds and accelerators per card. Used in simulation milestone projection.';
```

**Example:** HDFC Infinia — 10,000 bonus SmartPoints on ₹8L annual spend.

---

#### `award_charts`

KrisFlyer (and partner) redemption costs by route region and cabin class.

```sql
CREATE TABLE award_charts (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id            UUID        NOT NULL REFERENCES transfer_partners(id) ON DELETE CASCADE,
  origin_region         TEXT        NOT NULL,   -- 'India', 'Southeast Asia', 'Europe', 'North America'
  destination_region    TEXT        NOT NULL,
  cabin_class           TEXT        NOT NULL,   -- 'economy', 'premium_economy', 'business', 'first'
  award_type            TEXT        NOT NULL DEFAULT 'saver',  -- 'saver', 'advantage'
  miles_required        INTEGER     NOT NULL,
  taxes_fees_inr        INTEGER,                -- approximate taxes+YQ in INR
  notes                 TEXT,                   -- 'Waitlist only on peak dates', 'No YQ on SQ metal'
  effective_date        DATE        NOT NULL DEFAULT CURRENT_DATE,
  is_active             BOOLEAN     NOT NULL DEFAULT TRUE,

  CONSTRAINT uq_award_route UNIQUE (partner_id, origin_region, destination_region, cabin_class, award_type),
  CONSTRAINT chk_cabin CHECK (cabin_class IN ('economy', 'premium_economy', 'business', 'first')),
  CONSTRAINT chk_award_type CHECK (award_type IN ('saver', 'advantage'))
);

COMMENT ON TABLE award_charts IS 'Reference award pricing table. Used to compute miles_required for user goals. Updated manually for MVP.';
COMMENT ON COLUMN award_charts.taxes_fees_inr IS 'Approximate cash component in INR. Varies by route. Helps users understand total redemption cost.';
```

**Example (SQ KrisFlyer — one-way):**

| origin_region | destination_region | cabin_class | award_type | miles_required | taxes_fees_inr |
|---|---|---|---|---|---|
| India | Southeast Asia | business | saver | 35000 | 8500 |
| India | Europe | business | saver | 67500 | 32000 |
| India | North America | business | saver | 84500 | 38000 |
| India | Southeast Asia | first | saver | 47500 | 9000 |

---

### 3.2 User Layer

> Per-user state. Managed via Supabase Auth + RLS policies.

---

#### `users`

Extends Supabase `auth.users`. One row per authenticated user.

```sql
CREATE TABLE users (
  id                 UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name          TEXT,
  preferred_currency TEXT        NOT NULL DEFAULT 'INR',
  city               TEXT,                        -- 'Mumbai', 'Delhi' — used for origin default in goals
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'User profile extending Supabase auth. Minimal — auth and email live in auth.users.';
```

> **Why not store email here?** Supabase `auth.users` is the source of truth for identity. Duplicating email creates sync issues. Reference `auth.users.email` via Supabase joins when needed.

---

#### `user_cards`

Cards a user holds, with their current balance and spend allocation context.

```sql
CREATE TABLE user_cards (
  id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  card_id                  UUID        NOT NULL REFERENCES cards(id),
  current_points_balance   INTEGER     NOT NULL DEFAULT 0,
  monthly_spend_limit_inr  INTEGER,               -- user-declared monthly budget for this card
  is_primary               BOOLEAN     NOT NULL DEFAULT FALSE,
  member_since             DATE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_user_card UNIQUE (user_id, card_id)
);

COMMENT ON TABLE user_cards IS 'Cards held by a user. Links user to their card catalog entries with personalized context.';
COMMENT ON COLUMN user_cards.current_points_balance IS 'User-entered or synced balance. Used as starting point in simulations.';
COMMENT ON COLUMN user_cards.is_primary IS 'Flags default card for unrouted spend in simulations.';
```

---

#### `user_goals`

What the user is trying to achieve: a target flight/hotel redemption.

```sql
CREATE TABLE user_goals (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  goal_name           TEXT        NOT NULL,         -- 'Singapore Business Class for 2 - Anniversary'
  goal_type           TEXT        NOT NULL,          -- 'flight' | 'hotel' | 'custom'
  partner_id          UUID        REFERENCES transfer_partners(id),
  award_chart_id      UUID        REFERENCES award_charts(id),  -- locked reference
  origin_city         TEXT,                          -- IATA: 'BOM', 'DEL'
  destination_city    TEXT,                          -- IATA: 'SIN', 'LHR', 'JFK'
  cabin_class         TEXT,                          -- 'business', 'first', 'economy'
  award_type          TEXT        NOT NULL DEFAULT 'saver',
  num_passengers      INTEGER     NOT NULL DEFAULT 1,
  target_miles        INTEGER     NOT NULL,          -- total miles needed (auto-computed from award_chart × passengers)
  target_date         DATE,                          -- aspirational travel date
  status              TEXT        NOT NULL DEFAULT 'active',

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_goal_type   CHECK (goal_type IN ('flight', 'hotel', 'custom')),
  CONSTRAINT chk_goal_status CHECK (status IN ('active', 'achieved', 'abandoned', 'paused')),
  CONSTRAINT chk_cabin_goal  CHECK (cabin_class IN ('economy', 'premium_economy', 'business', 'first'))
);

COMMENT ON TABLE user_goals IS 'User-defined redemption target. Drives all simulation and recommendation logic.';
COMMENT ON COLUMN user_goals.target_miles IS 'Total miles needed = award_chart.miles_required × num_passengers. Stored for denormalization/speed.';
COMMENT ON COLUMN user_goals.award_chart_id IS 'Snapshot reference to the award chart row at goal creation time. Prevents goal drift if award chart changes.';
```

---

### 3.3 Simulation Layer

> User experiments: "If I spend this way every month, when do I hit my goal?"

---

#### `spend_simulations`

A named simulation scenario scoped to a user and optionally a goal.

```sql
CREATE TABLE spend_simulations (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  goal_id          UUID        REFERENCES user_goals(id) ON DELETE SET NULL,
  simulation_name  TEXT        NOT NULL DEFAULT 'Untitled Simulation',
  status           TEXT        NOT NULL DEFAULT 'draft',  -- 'draft' | 'computing' | 'completed' | 'stale'
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_sim_status CHECK (status IN ('draft', 'computing', 'completed', 'stale'))
);

COMMENT ON TABLE spend_simulations IS 'Container for a user spend scenario. A user may have multiple simulations per goal.';
COMMENT ON COLUMN spend_simulations.status IS '"stale" means inputs changed after last compute run — triggers re-computation.';
```

---

#### `simulation_line_items`

Individual spend buckets within a simulation, with card routing assignment.

```sql
CREATE TABLE simulation_line_items (
  id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  simulation_id        UUID        NOT NULL REFERENCES spend_simulations(id) ON DELETE CASCADE,
  category_slug        TEXT        NOT NULL,        -- must match reward_categories.category_slug
  monthly_spend_inr    INTEGER     NOT NULL,         -- user-declared monthly spend in this category
  assigned_card_id     UUID        REFERENCES cards(id),  -- which card to route this spend to (can be NULL = auto-optimized)
  override_reason      TEXT,                         -- if user manually overrides auto-assignment, why

  CONSTRAINT chk_spend_positive CHECK (monthly_spend_inr > 0)
);

COMMENT ON TABLE simulation_line_items IS 'Spend allocation per category within a simulation. assigned_card_id = NULL triggers OR-Tools routing.';
COMMENT ON COLUMN simulation_line_items.assigned_card_id IS 'NULL means this category is left to the optimizer. Non-NULL means user has pinned this spend to a card.';
```

---

#### `simulation_results`

Computed output of a simulation run. Produced by the OR-Tools optimizer.

```sql
CREATE TABLE simulation_results (
  id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  simulation_id            UUID        NOT NULL REFERENCES spend_simulations(id) ON DELETE CASCADE,
  goal_id                  UUID        REFERENCES user_goals(id),

  -- Aggregate outputs
  total_monthly_points_earned   INTEGER     NOT NULL,
  total_monthly_miles_earned    NUMERIC(10,2) NOT NULL,  -- after applying best transfer ratio
  months_to_goal                NUMERIC(6,1),             -- NULL if goal has no target_miles
  optimization_score            NUMERIC(5,2),             -- 0-100 composite efficiency score

  -- Structured breakdown (JSONB for flexibility, not for querying)
  card_allocations         JSONB       NOT NULL,
  -- Shape: { "<card_id>": { "category_slug": { "spend_inr": N, "points": N, "earn_rate": N }, ... }, ... }

  milestone_projections    JSONB,
  -- Shape: [{ "card_id": "...", "milestone_type": "spend_bonus", "threshold_inr": N, "on_track": bool, "months_to_trigger": N }]

  transfer_recommendation  JSONB,
  -- Shape: { "best_card_for_transfer": "...", "transfer_ratio": "2:1", "miles_on_transfer": N, "transfer_fee_inr": N }

  computed_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_score_range CHECK (optimization_score BETWEEN 0 AND 100)
);

COMMENT ON TABLE simulation_results IS 'Deterministic optimizer output for a simulation. Regenerated on each compute run. Never manually edited.';
COMMENT ON COLUMN simulation_results.card_allocations IS 'Full spend routing breakdown by card and category. Primary input for recommendation explainability.';
COMMENT ON COLUMN simulation_results.optimization_score IS 'Composite score: weighs miles/spend efficiency, milestone proximity, and transfer ratio quality.';
```

---

### 3.4 Recommendation Layer

> AI-generated explanations and action items. Stored as artifacts.

---

#### `recommendation_outputs`

LangGraph/LLM-generated recommendation explanations, tied to a simulation result.

```sql
CREATE TABLE recommendation_outputs (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  simulation_id         UUID        REFERENCES spend_simulations(id) ON DELETE SET NULL,
  goal_id               UUID        REFERENCES user_goals(id) ON DELETE SET NULL,
  result_id             UUID        REFERENCES simulation_results(id) ON DELETE SET NULL,

  recommendation_type   TEXT        NOT NULL,
  -- 'spend_routing'       → which card for which category
  -- 'card_suggestion'     → consider adding this card to wallet
  -- 'transfer_timing'     → when to transfer points to maximize value
  -- 'goal_feasibility'    → is the goal achievable, what adjustments help
  -- 'milestone_alert'     → you're close to a spend bonus threshold

  summary               TEXT        NOT NULL,   -- 1-2 sentence TL;DR shown in UI
  reasoning             TEXT        NOT NULL,   -- full chain-of-thought explanation from LLM
  action_items          JSONB,
  -- Shape: [{ "priority": 1, "action": "Route dining spend to Axis Atlas", "impact": "+320 miles/month", "card_id": "..." }]

  confidence_score      NUMERIC(4,2),           -- 0.00–1.00, derived from optimizer certainty
  model_version         TEXT,                   -- 'claude-sonnet-4-20250514', for auditability
  is_dismissed          BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_rec_type CHECK (
    recommendation_type IN (
      'spend_routing', 'card_suggestion', 'transfer_timing',
      'goal_feasibility', 'milestone_alert'
    )
  ),
  CONSTRAINT chk_confidence CHECK (confidence_score BETWEEN 0 AND 1)
);

COMMENT ON TABLE recommendation_outputs IS 'AI-generated recommendation artifacts. These are explanations of optimizer outputs, not the optimizer outputs themselves.';
COMMENT ON COLUMN recommendation_outputs.reasoning IS 'Full LLM chain-of-thought. Stored for debuggability and explainability audit. Not shown verbatim in UI.';
COMMENT ON COLUMN recommendation_outputs.action_items IS 'Structured list of concrete next steps the user should take. Parsed and rendered by frontend.';
```

---

## 4. Relationships & ERD Notes

```
cards (1) ──────────────────────── (M) reward_categories
  │                                       [card_id FK]
  │
  └── (1) ──────────────────────── (M) reward_milestones
  │                                       [card_id FK]
  │
  └── (M) ── card_transfer_partners ── (M) transfer_partners
                  [card_id FK]               [partner_id FK]

transfer_partners (1) ────────────── (M) award_charts
                                            [partner_id FK]

users (1) ──────────────────────── (M) user_cards
  │                                       [user_id FK] → cards [card_id FK]
  │
  └── (1) ──────────────────────── (M) user_goals
  │                                       [user_id FK] → transfer_partners, award_charts
  │
  └── (1) ──────────────────────── (M) spend_simulations
                                          [user_id FK] → user_goals [goal_id FK]
                                              │
                                              └── (1) ──── (M) simulation_line_items
                                              │                   [simulation_id FK] → cards
                                              │
                                              └── (1) ──── (1) simulation_results
                                                                  [simulation_id FK]
                                                                        │
                                                                        ▼
                                                           recommendation_outputs
                                                           [result_id FK, simulation_id FK, goal_id FK]
```

**Cascade rules:**
- `cards` → `reward_categories`: `ON DELETE CASCADE` (categories belong to a card)
- `cards` → `card_transfer_partners`: `ON DELETE CASCADE`
- `spend_simulations` → `simulation_line_items`: `ON DELETE CASCADE` (line items are part of the simulation)
- `spend_simulations` → `simulation_results`: `ON DELETE CASCADE`
- `user_goals` → references from `spend_simulations`: `ON DELETE SET NULL` (don't orphan simulations if a goal is deleted)
- `users` → all user tables: `ON DELETE CASCADE` (GDPR: removing a user removes everything)

---

## 5. Indexes

```sql
-- ─────────────────────────────────────────────
-- CATALOG LAYER
-- ─────────────────────────────────────────────

-- Cards: filter by bank and active status (admin UI, seeding)
CREATE INDEX idx_cards_bank        ON cards(bank);
CREATE INDEX idx_cards_is_active   ON cards(is_active) WHERE is_active = TRUE;

-- Reward categories: look up earn rates for a card quickly (hot path in optimizer)
CREATE INDEX idx_rewcat_card_id    ON reward_categories(card_id);
CREATE INDEX idx_rewcat_slug       ON reward_categories(category_slug);
-- Composite: optimizer queries both together
CREATE INDEX idx_rewcat_card_slug  ON reward_categories(card_id, category_slug);

-- Transfer partners: filter by type
CREATE INDEX idx_tp_type           ON transfer_partners(partner_type);
CREATE INDEX idx_tp_active         ON transfer_partners(is_active) WHERE is_active = TRUE;

-- Card-transfer-partner junction: both FKs indexed (bidirectional lookup)
CREATE INDEX idx_ctp_card_id       ON card_transfer_partners(card_id);
CREATE INDEX idx_ctp_partner_id    ON card_transfer_partners(partner_id);

-- Milestones: optimizer looks up milestones by card
CREATE INDEX idx_milestone_card_id ON reward_milestones(card_id);

-- Award charts: route lookup (most common query pattern)
CREATE INDEX idx_award_partner_id  ON award_charts(partner_id);
CREATE INDEX idx_award_route       ON award_charts(origin_region, destination_region, cabin_class, award_type);


-- ─────────────────────────────────────────────
-- USER LAYER
-- ─────────────────────────────────────────────

-- user_cards: user's wallet lookup
CREATE INDEX idx_ucards_user_id    ON user_cards(user_id);

-- user_goals: dashboard listing (all active goals for a user)
CREATE INDEX idx_goals_user_id     ON user_goals(user_id);
CREATE INDEX idx_goals_status      ON user_goals(user_id, status) WHERE status = 'active';


-- ─────────────────────────────────────────────
-- SIMULATION LAYER
-- ─────────────────────────────────────────────

-- Simulations: user's history panel
CREATE INDEX idx_sims_user_id      ON spend_simulations(user_id);
CREATE INDEX idx_sims_goal_id      ON spend_simulations(goal_id);
CREATE INDEX idx_sims_status       ON spend_simulations(status);

-- Line items: fetched together with simulation
CREATE INDEX idx_litems_sim_id     ON simulation_line_items(simulation_id);

-- Results: always fetched by simulation (1:1 relationship but FK still needs index)
CREATE INDEX idx_results_sim_id    ON simulation_results(simulation_id);


-- ─────────────────────────────────────────────
-- RECOMMENDATION LAYER
-- ─────────────────────────────────────────────

-- Recommendations: user's feed + per-simulation lookup
CREATE INDEX idx_recs_user_id      ON recommendation_outputs(user_id);
CREATE INDEX idx_recs_sim_id       ON recommendation_outputs(simulation_id);
CREATE INDEX idx_recs_type         ON recommendation_outputs(user_id, recommendation_type);
-- Filter dismissed recommendations out of feed
CREATE INDEX idx_recs_active       ON recommendation_outputs(user_id, is_dismissed)
                                   WHERE is_dismissed = FALSE;
```

---

## 6. Scalability Considerations

### 6.1 RLS (Row-Level Security) via Supabase

Every user-scoped table must have RLS policies enabled. Users can only access their own rows. Catalog tables (`cards`, `reward_categories`, etc.) are read-only for all authenticated users.

```sql
-- Example RLS policy for user_goals
ALTER TABLE user_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own goals"
  ON user_goals FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own goals"
  ON user_goals FOR ALL
  USING (auth.uid() = user_id);
```

### 6.2 Catalog Versioning (Post-MVP)

Transfer ratios, award charts, and earn rates change over time. For MVP, rows are updated in-place with `is_active` flags. Post-MVP path:

- Add `version INTEGER` and `superseded_by UUID` columns to `award_charts` and `card_transfer_partners`
- Simulations lock `award_chart_id` at creation (already done) — this prevents historical simulations from drifting

### 6.3 Simulation Volume

Each simulation run produces one `simulation_results` row. If users run many simulations, add:

```sql
-- Soft-delete old simulation results beyond last N per user (background job)
-- Or: add a computed_at index for time-based pruning
CREATE INDEX idx_results_computed_at ON simulation_results(computed_at);
```

### 6.4 JSONB Query Performance

JSONB columns (`card_allocations`, `action_items`) are never filtered or queried directly — they are read whole and parsed in application code. If we later need to query inside JSONB (e.g., "all simulations where card X was recommended"), add a GIN index:

```sql
-- Future: if querying inside card_allocations
CREATE INDEX idx_results_allocations_gin ON simulation_results USING GIN (card_allocations);
```

### 6.5 Connection Pooling

Use Supabase's PgBouncer (transaction mode) for all API connections. FastAPI services should use async SQLAlchemy with a pool size of 10–20 for the optimization compute path.

### 6.6 Read Replicas (Post-MVP)

Catalog data (`cards`, `reward_categories`, `award_charts`) is read-heavy. Post-MVP, route catalog reads to a Supabase read replica. Write path (simulations, goals) stays on primary.

---

## 7. Design Decision Log

| Decision | Rationale |
|---|---|
| **Separate `reward_categories` from `cards`** | Cards have 5–8 different earn rates across categories. Embedding them in `cards` as JSONB would make the optimizer blind — it couldn't query by category. Normalized rows make the earn-rate lookup deterministic and index-friendly. |
| **`card_transfer_partners` junction table** | Transfer ratios are a many-to-many relationship with attributes (ratio, fee, processing time). A junction table is the only correct model. Embedding in `cards` as an array would break normalization. |
| **`award_charts` as a separate table, not hardcoded** | Award charts change (KrisFlyer changed business saver rates in 2023). Keeping them in the DB means updates require no code deploy — just a row update. `user_goals.award_chart_id` snapshots the rate at goal creation. |
| **`simulation_results.card_allocations` as JSONB** | The allocation breakdown is a nested structure (card → category → spend/points). Normalizing this into rows would add 3+ tables for data that is always read whole, never filtered, and regenerated on each compute run. JSONB is the right call here. |
| **`recommendation_outputs` separate from `simulation_results`** | Optimizer output is deterministic (OR-Tools). AI explanation is probabilistic (LLM). Mixing them couples a reliable system to a non-deterministic one. Separating allows: (a) regenerating explanations without re-running the optimizer, (b) A/B testing recommendation prompts, (c) auditing LLM outputs independently. |
| **No `points_transactions` table in MVP** | A full ledger of point earn/burn is valuable but out of MVP scope. `current_points_balance` in `user_cards` is user-entered. A transactions table would require bank API integration or complex manual entry — future phase. |
| **`category_slug` as TEXT, not FK to an enum table** | An enum table adds a join on every optimizer query. Slug values are controlled at the application layer and documented. Adding a `CHECK` constraint or application-level enum validation is sufficient for MVP. |
| **`users` references `auth.users`** | Supabase handles identity, password hashing, and token management. Duplicating email or auth state in `users` creates sync risk. `users` stores only product-specific profile data. |
| **`ON DELETE CASCADE` on user tables** | Hard GDPR requirement. When a user account is deleted, all associated data must be purged. Cascade handles this atomically without application-level cleanup logic. |

---

## 8. Future Extension Points

The schema is designed to accommodate these future features without breaking changes:

| Future Feature | Extension Path |
|---|---|
| **Multi-airline optimization** | Add rows to `transfer_partners` and `card_transfer_partners`. `award_charts` is already multi-partner. No schema change needed. |
| **Hotel reward optimization** | `award_charts` already has `partner_type` via the partner FK. Add hotel award chart rows. `user_goals.goal_type = 'hotel'` already supported. |
| **Points ledger / transaction history** | Add a `points_transactions` table: `(user_id, card_id, transaction_type, points_delta, reference_id, transacted_at)`. `user_cards.current_points_balance` becomes a computed view. |
| **Card recommendation engine (wallet builder)** | Add a `card_recommendations` table (similar to `recommendation_outputs` but scoped to wallet-building advice, not simulation-specific). |
| **Real-time award availability** | Add an `award_availability_cache` table: `(partner_id, flight_date, route, cabin_class, seats_available, last_checked)` with a TTL-based refresh job. |
| **Spend data sync (bank APIs)** | Add a `spend_transactions` table and an `integrations` table tracking bank API connection state per user. Populate `simulation_line_items` from real spend data. |
| **Versioned award charts** | Add `version`, `effective_until`, and `superseded_by UUID` to `award_charts`. Goals already snapshot `award_chart_id` — no goal-layer changes needed. |
| **Team / travel agent accounts** | Add an `organizations` table and a `user_organizations` junction. Scope simulations and goals to `organization_id` in addition to `user_id`. |

---

## Appendix: Full Table Dependency Order (for migrations)

```
1. transfer_partners
2. cards
3. reward_categories          [→ cards]
4. card_transfer_partners     [→ cards, transfer_partners]
5. reward_milestones          [→ cards]
6. award_charts               [→ transfer_partners]
7. users                      [→ auth.users]
8. user_cards                 [→ users, cards]
9. user_goals                 [→ users, transfer_partners, award_charts]
10. spend_simulations         [→ users, user_goals]
11. simulation_line_items     [→ spend_simulations, cards]
12. simulation_results        [→ spend_simulations, user_goals]
13. recommendation_outputs    [→ users, spend_simulations, user_goals, simulation_results]
```

---

*Document maintained by: OptiMILES Backend Team*  
*Last updated: v1.0.0 — Initial schema design*  
*Next review: Post-MVP pilot (add points_transactions, award_availability_cache)*
