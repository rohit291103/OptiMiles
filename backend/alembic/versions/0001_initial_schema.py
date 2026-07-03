"""Initial schema: db-schema-v1 + the v1.1 amendment (backend-build-plan-v1 §3).

v1.1 deltas baked into this initial DDL (no migration had ever run, D-1/D-2):
- new `reward_currencies` table, created first;
- `cards.points_currency` TEXT replaced by `reward_currency_id` FK;
- `card_transfer_partners` replaced by `currency_transfer_partners`
  (transfer relationships belong to currencies, not cards);
- lineage columns (`catalog_snapshot_version`, `engine_version`) on
  `simulation_results` / `recommendation_outputs`.

Target: a fresh **Supabase** project — `users` references `auth.users(id)`
and RLS policies use `auth.uid()`. Plain-Postgres local runs need an auth
stub schema first (deferred until a local-dev workflow exists).

Revision ID: 0001
Revises:
Create Date: 2026-07-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Catalog layer (dependency order per build plan §3.5) ──────────────

    op.execute("""
        CREATE TABLE reward_currencies (
          id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          currency_name  TEXT        NOT NULL UNIQUE,
          issuer         TEXT        NOT NULL,
          expiry_rules   TEXT,
          is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
          metadata       JSONB,
          created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE reward_currencies IS
          'Bank points currencies (v1.1, D-1). Transfer relationships belong here, not to cards.';
    """)

    op.execute("""
        CREATE TABLE transfer_partners (
          id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          partner_name   TEXT        NOT NULL,
          program_name   TEXT        NOT NULL,
          partner_type   TEXT        NOT NULL,
          iata_code      TEXT,
          alliance       TEXT,
          is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
          metadata       JSONB,
          created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT chk_partner_type CHECK (partner_type IN ('airline', 'hotel'))
        );
        COMMENT ON TABLE transfer_partners IS
          'Loyalty programs that Indian credit card points can be transferred into.';
    """)

    op.execute("""
        CREATE TABLE cards (
          id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          bank               TEXT        NOT NULL,
          card_name          TEXT        NOT NULL,
          card_network       TEXT        NOT NULL,
          reward_currency_id UUID        NOT NULL REFERENCES reward_currencies(id),
          annual_fee_inr     INTEGER     NOT NULL DEFAULT 0,
          joining_fee_inr    INTEGER     NOT NULL DEFAULT 0,
          base_earn_rate     NUMERIC(6,2) NOT NULL,
          min_income_inr     INTEGER,
          has_lounge_access  BOOLEAN     NOT NULL DEFAULT FALSE,
          is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
          metadata           JSONB,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE cards IS
          'Master catalog of Indian travel credit cards supported by OptiMiles.';
        COMMENT ON COLUMN cards.base_earn_rate IS
          'Points earned per ₹100 on non-accelerated spend. Fallback earn rate.';
        COMMENT ON COLUMN cards.reward_currency_id IS
          'v1.1 (D-1): replaces points_currency TEXT. Card → currency → transfer links.';
    """)

    op.execute("""
        CREATE TABLE reward_categories (
          id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          card_id            UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          category_slug      TEXT        NOT NULL,
          category_label     TEXT        NOT NULL,
          earn_rate          NUMERIC(6,2) NOT NULL,
          monthly_cap_inr    INTEGER,
          quarterly_cap_inr  INTEGER,
          annual_cap_inr     INTEGER,
          notes              TEXT,
          is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
          CONSTRAINT uq_card_category UNIQUE (card_id, category_slug)
        );
        COMMENT ON TABLE reward_categories IS
          'Accelerated earn rates per spend category per card.';
        COMMENT ON COLUMN reward_categories.monthly_cap_inr IS
          'Max eligible spend/month at this rate. Beyond the cap, spend earns base_earn_rate.';
    """)

    op.execute("""
        CREATE TABLE currency_transfer_partners (
          id                    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
          currency_id           UUID    NOT NULL REFERENCES reward_currencies(id) ON DELETE CASCADE,
          partner_id            UUID    NOT NULL REFERENCES transfer_partners(id) ON DELETE CASCADE,
          ratio_from            INTEGER NOT NULL DEFAULT 1,
          ratio_to              INTEGER NOT NULL DEFAULT 1,
          min_transfer_points   INTEGER NOT NULL DEFAULT 1000,
          max_transfer_points   INTEGER,
          transfer_fee_inr      INTEGER NOT NULL DEFAULT 0,
          processing_days_min   INTEGER NOT NULL DEFAULT 1,
          processing_days_max   INTEGER NOT NULL DEFAULT 5,
          is_active             BOOLEAN NOT NULL DEFAULT TRUE,
          notes                 TEXT,
          CONSTRAINT uq_currency_partner UNIQUE (currency_id, partner_id)
        );
        COMMENT ON TABLE currency_transfer_partners IS
          'v1.1 (D-1): replaces card_transfer_partners. Ratios between a reward currency and a program.';
        COMMENT ON COLUMN currency_transfer_partners.ratio_from IS
          'Currency points consumed per unit. ratio_from=2, ratio_to=1 ⇒ 2 points → 1 mile.';
        COMMENT ON COLUMN currency_transfer_partners.max_transfer_points IS
          'NULL = uncapped. Recent bank transfer caps make this a real field.';
    """)

    op.execute("""
        CREATE TABLE reward_milestones (
          id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          card_id              UUID        NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
          milestone_type       TEXT        NOT NULL,
          spend_threshold_inr  INTEGER,
          bonus_points         INTEGER     NOT NULL,
          period               TEXT        NOT NULL DEFAULT 'annual',
          description          TEXT,
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
        COMMENT ON TABLE reward_milestones IS
          'Bonus point thresholds and accelerators per card. Used in milestone projection.';
    """)

    op.execute("""
        CREATE TABLE award_charts (
          id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          partner_id            UUID        NOT NULL REFERENCES transfer_partners(id) ON DELETE CASCADE,
          origin_region         TEXT        NOT NULL,
          destination_region    TEXT        NOT NULL,
          cabin_class           TEXT        NOT NULL,
          award_type            TEXT        NOT NULL DEFAULT 'saver',
          miles_required        INTEGER     NOT NULL,
          taxes_fees_inr        INTEGER,
          notes                 TEXT,
          effective_date        DATE        NOT NULL DEFAULT CURRENT_DATE,
          is_active             BOOLEAN     NOT NULL DEFAULT TRUE,
          CONSTRAINT uq_award_route UNIQUE
            (partner_id, origin_region, destination_region, cabin_class, award_type),
          CONSTRAINT chk_cabin CHECK
            (cabin_class IN ('economy', 'premium_economy', 'business', 'first')),
          CONSTRAINT chk_award_type CHECK (award_type IN ('saver', 'advantage'))
        );
        COMMENT ON TABLE award_charts IS
          'Reference award pricing. Computes miles_required for goals. Updated manually for MVP.';
    """)

    # ── User layer (Supabase auth + RLS) ──────────────────────────────────

    op.execute("""
        CREATE TABLE users (
          id                 UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
          full_name          TEXT,
          preferred_currency TEXT        NOT NULL DEFAULT 'INR',
          city               TEXT,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        COMMENT ON TABLE users IS
          'Profile extending Supabase auth. Identity/email live in auth.users only.';
    """)

    op.execute("""
        CREATE TABLE user_cards (
          id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id                  UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          card_id                  UUID        NOT NULL REFERENCES cards(id),
          current_points_balance   INTEGER     NOT NULL DEFAULT 0,
          monthly_spend_limit_inr  INTEGER,
          is_primary               BOOLEAN     NOT NULL DEFAULT FALSE,
          member_since             DATE,
          created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT uq_user_card UNIQUE (user_id, card_id)
        );
        COMMENT ON TABLE user_cards IS
          'Cards held by a user, with balances used as simulation starting points.';
    """)

    op.execute("""
        CREATE TABLE user_goals (
          id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          goal_name           TEXT        NOT NULL,
          goal_type           TEXT        NOT NULL,
          partner_id          UUID        REFERENCES transfer_partners(id),
          award_chart_id      UUID        REFERENCES award_charts(id),
          origin_city         TEXT,
          destination_city    TEXT,
          cabin_class         TEXT,
          award_type          TEXT        NOT NULL DEFAULT 'saver',
          num_passengers      INTEGER     NOT NULL DEFAULT 1,
          target_miles        INTEGER     NOT NULL,
          target_date         DATE,
          status              TEXT        NOT NULL DEFAULT 'active',
          created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT chk_goal_type   CHECK (goal_type IN ('flight', 'hotel', 'custom')),
          CONSTRAINT chk_goal_status CHECK (status IN ('active', 'achieved', 'abandoned', 'paused')),
          CONSTRAINT chk_cabin_goal  CHECK
            (cabin_class IN ('economy', 'premium_economy', 'business', 'first'))
        );
        COMMENT ON COLUMN user_goals.award_chart_id IS
          'Snapshot reference locked at goal creation. Prevents drift if the chart changes.';
    """)

    # ── Simulation layer ──────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE spend_simulations (
          id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          goal_id          UUID        REFERENCES user_goals(id) ON DELETE SET NULL,
          simulation_name  TEXT        NOT NULL DEFAULT 'Untitled Simulation',
          status           TEXT        NOT NULL DEFAULT 'draft',
          created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT chk_sim_status CHECK (status IN ('draft', 'computing', 'completed', 'stale'))
        );
    """)

    op.execute("""
        CREATE TABLE simulation_line_items (
          id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          simulation_id        UUID        NOT NULL REFERENCES spend_simulations(id) ON DELETE CASCADE,
          category_slug        TEXT        NOT NULL,
          monthly_spend_inr    INTEGER     NOT NULL,
          assigned_card_id     UUID        REFERENCES cards(id),
          override_reason      TEXT,
          CONSTRAINT chk_spend_positive CHECK (monthly_spend_inr > 0)
        );
        COMMENT ON COLUMN simulation_line_items.assigned_card_id IS
          'NULL = left to the optimizer. Non-NULL = user pinned this spend to a card.';
    """)

    op.execute("""
        CREATE TABLE simulation_results (
          id                            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          simulation_id                 UUID        NOT NULL REFERENCES spend_simulations(id) ON DELETE CASCADE,
          goal_id                       UUID        REFERENCES user_goals(id),
          total_monthly_points_earned   INTEGER     NOT NULL,
          total_monthly_miles_earned    NUMERIC(10,2) NOT NULL,
          months_to_goal                NUMERIC(6,1),
          optimization_score            NUMERIC(5,2),
          card_allocations              JSONB       NOT NULL,
          milestone_projections         JSONB,
          transfer_recommendation       JSONB,
          catalog_snapshot_version      TEXT        NOT NULL,
          engine_version                TEXT        NOT NULL,
          computed_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT chk_score_range CHECK (optimization_score BETWEEN 0 AND 100)
        );
        COMMENT ON TABLE simulation_results IS
          'Deterministic engine output. Regenerated per compute run. Never manually edited.';
        COMMENT ON COLUMN simulation_results.catalog_snapshot_version IS
          'v1.1 (D-2): lineage — replaying same inputs + this snapshot is byte-identical.';
    """)

    # ── Recommendation layer ──────────────────────────────────────────────

    op.execute("""
        CREATE TABLE recommendation_outputs (
          id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id               UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          simulation_id         UUID        REFERENCES spend_simulations(id) ON DELETE SET NULL,
          goal_id               UUID        REFERENCES user_goals(id) ON DELETE SET NULL,
          result_id             UUID        REFERENCES simulation_results(id) ON DELETE SET NULL,
          recommendation_type   TEXT        NOT NULL,
          summary               TEXT        NOT NULL,
          reasoning             TEXT        NOT NULL,
          action_items          JSONB,
          confidence_score      NUMERIC(4,2),
          model_version         TEXT,
          catalog_snapshot_version TEXT,
          engine_version        TEXT,
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
        COMMENT ON TABLE recommendation_outputs IS
          'AI narration artifacts — explanations of engine outputs, never the outputs themselves.';
    """)

    # ── Indexes (db-schema-v1 §5; junction indexes re-pointed per v1.1) ───

    op.execute("""
        CREATE INDEX idx_cards_bank        ON cards(bank);
        CREATE INDEX idx_cards_is_active   ON cards(is_active) WHERE is_active = TRUE;
        CREATE INDEX idx_rewcat_card_id    ON reward_categories(card_id);
        CREATE INDEX idx_rewcat_slug       ON reward_categories(category_slug);
        CREATE INDEX idx_rewcat_card_slug  ON reward_categories(card_id, category_slug);
        CREATE INDEX idx_tp_type           ON transfer_partners(partner_type);
        CREATE INDEX idx_tp_active         ON transfer_partners(is_active) WHERE is_active = TRUE;
        CREATE INDEX idx_ctp_currency_id   ON currency_transfer_partners(currency_id);
        CREATE INDEX idx_ctp_partner_id    ON currency_transfer_partners(partner_id);
        CREATE INDEX idx_milestone_card_id ON reward_milestones(card_id);
        CREATE INDEX idx_award_partner_id  ON award_charts(partner_id);
        CREATE INDEX idx_award_route       ON award_charts(origin_region, destination_region, cabin_class, award_type);
        CREATE INDEX idx_ucards_user_id    ON user_cards(user_id);
        CREATE INDEX idx_goals_user_id     ON user_goals(user_id);
        CREATE INDEX idx_goals_status      ON user_goals(user_id, status) WHERE status = 'active';
        CREATE INDEX idx_sims_user_id      ON spend_simulations(user_id);
        CREATE INDEX idx_sims_goal_id      ON spend_simulations(goal_id);
        CREATE INDEX idx_sims_status       ON spend_simulations(status);
        CREATE INDEX idx_litems_sim_id     ON simulation_line_items(simulation_id);
        CREATE INDEX idx_results_sim_id    ON simulation_results(simulation_id);
        CREATE INDEX idx_recs_user_id      ON recommendation_outputs(user_id);
        CREATE INDEX idx_recs_sim_id       ON recommendation_outputs(simulation_id);
        CREATE INDEX idx_recs_type         ON recommendation_outputs(user_id, recommendation_type);
        CREATE INDEX idx_recs_active       ON recommendation_outputs(user_id, is_dismissed)
                                           WHERE is_dismissed = FALSE;
    """)

    # ── RLS on user-scoped tables (defense in depth, D-4) ─────────────────
    # FastAPI uses the service role (bypasses RLS); these protect any future
    # direct-from-frontend reads. Catalog tables stay RLS-off: admin-seeded,
    # served to clients via the API, never written by users.

    op.execute("""
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        CREATE POLICY users_own ON users FOR ALL
          USING (auth.uid() = id);

        ALTER TABLE user_cards ENABLE ROW LEVEL SECURITY;
        CREATE POLICY user_cards_own ON user_cards FOR ALL
          USING (auth.uid() = user_id);

        ALTER TABLE user_goals ENABLE ROW LEVEL SECURITY;
        CREATE POLICY user_goals_own ON user_goals FOR ALL
          USING (auth.uid() = user_id);

        ALTER TABLE spend_simulations ENABLE ROW LEVEL SECURITY;
        CREATE POLICY spend_simulations_own ON spend_simulations FOR ALL
          USING (auth.uid() = user_id);

        ALTER TABLE simulation_line_items ENABLE ROW LEVEL SECURITY;
        CREATE POLICY simulation_line_items_own ON simulation_line_items FOR ALL
          USING (EXISTS (
            SELECT 1 FROM spend_simulations s
            WHERE s.id = simulation_id AND s.user_id = auth.uid()
          ));

        ALTER TABLE simulation_results ENABLE ROW LEVEL SECURITY;
        CREATE POLICY simulation_results_own ON simulation_results FOR ALL
          USING (EXISTS (
            SELECT 1 FROM spend_simulations s
            WHERE s.id = simulation_id AND s.user_id = auth.uid()
          ));

        ALTER TABLE recommendation_outputs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY recommendation_outputs_own ON recommendation_outputs FOR ALL
          USING (auth.uid() = user_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS recommendation_outputs;
        DROP TABLE IF EXISTS simulation_results;
        DROP TABLE IF EXISTS simulation_line_items;
        DROP TABLE IF EXISTS spend_simulations;
        DROP TABLE IF EXISTS user_goals;
        DROP TABLE IF EXISTS user_cards;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS award_charts;
        DROP TABLE IF EXISTS reward_milestones;
        DROP TABLE IF EXISTS currency_transfer_partners;
        DROP TABLE IF EXISTS reward_categories;
        DROP TABLE IF EXISTS cards;
        DROP TABLE IF EXISTS transfer_partners;
        DROP TABLE IF EXISTS reward_currencies;
    """)
