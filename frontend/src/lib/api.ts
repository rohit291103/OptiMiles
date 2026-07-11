/**
 * Typed client for the OptiMiles backend (build-plan §7).
 *
 * The public Goal Simulator posts a *structured intent* (destination, cabin,
 * timeline chosen from menus) to `POST /simulations`, so it skips Stage 1 —
 * no LLM key is required. The response is the same discriminated union the
 * `/goals/recommendation` endpoint returns; every number in it traces to a
 * deterministic engine artifact, never to an LLM.
 *
 * Only the fields the simulator renders are typed here — the backend
 * `FinalRecommendation` is richer. Keep this in sync with
 * `backend/app/api/schemas.py` when the simulator starts showing more.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Request ──────────────────────────────────────────────────────────────

export type SimulateIntent = {
  origin_city?: string | null;
  destination_city: string;
  cabin_class: "economy" | "premium_economy" | "business" | "first";
  timeline_months: number;
  num_passengers?: number;
  confidence: number;
};

export type WalletCardInput = {
  card_id: string;
  current_points_balance?: number;
};

export type SpendItemInput = {
  category_slug: string;
  monthly_spend_inr: number;
  pinned_card_id?: string | null;
};

export type SimulateRequest = {
  intent: SimulateIntent;
  profile_city?: string | null;
  wallet?: WalletCardInput[];
  spend_profile?: SpendItemInput[];
};

// ── Response (subset the simulator renders) ──────────────────────────────

export type ScoreBreakdown = {
  goal_achievement: string;
  efficiency: string;
  cost: string;
  simplicity: string;
  portfolio_utilization: string;
  risk: string;
};

export type MonthLedgerEntry = {
  month: number;
  // Points earned this month (base + category + milestone bonuses) — the earn
  // delta, unaffected by transfers-out. Chart its cumulative sum for progress.
  points_earned_this_month: number;
  cumulative_target_miles: number;
};

export type CandidateStrategy = {
  strategy_id: string;
  archetype: string;
  cards_used: string[];
  cards_to_acquire: string[];
  // category slug → card id
  spend_allocation: Record<string, string>;
};

/** Per-category earn detail — the "why" behind a routing (rates/points). */
export type AllocationDetail = {
  category_slug: string;
  card_id: string;
  monthly_spend_inr: number;
  earn_rate: string;
  effective_miles_per_100inr: string;
  monthly_points: number;
  notes: string[];
};

export type RankedStrategy = {
  strategy: CandidateStrategy;
  score: string;
  score_breakdown: ScoreBreakdown;
  rank: number;
  headline_differentiator: string;
  co_recommended: boolean;
  allocation_details: AllocationDetail[];
  simulation: {
    ledger: MonthLedgerEntry[];
    months_to_goal: number | null;
    miles_at_target_date: number;
    total_fees_inr: number;
    buffer_achieved: boolean;
    misses_goal: boolean;
  };
};

export type RewardRequirement = {
  target_program_name: string;
  chart_miles_per_passenger: number;
  miles_required_total: number;
  buffer_miles: number;
};

export type FeasibilityVerdict = {
  feasible: boolean;
  best_case_miles: number;
  gap_miles: number;
  tight: boolean;
  adjustment_options: {
    kind: string;
    description: string;
    resulting_best_case_miles: number;
  }[];
};

export type Narration = {
  summary: string;
  reasoning: string;
  action_items: { priority: number; action: string; impact: string | null }[];
  comparison_notes: string | null;
  model_version: string;
};

export type FinalRecommendation = {
  requirement: RewardRequirement;
  verdict: FeasibilityVerdict;
  recommended: RankedStrategy | null;
  alternatives: RankedStrategy[];
  narration: Narration | null;
  risks_and_limitations: string[];
  assumed_flags: string[];
  catalog_snapshot_version: string;
  engine_version: string;
};

export type ClarificationRequest = {
  questions: string[];
  missing_fields: string[];
};

export type UnsupportedRoute = {
  supported_routes: string[];
  message?: string;
};

/** The `/simulations` response, discriminated on `kind`. `persisted` is set
 * only by the authenticated save endpoint: true iff the row actually landed. */
export type SimulateResponse =
  | { kind: "recommendation"; recommendation: FinalRecommendation; persisted?: boolean | null }
  | { kind: "clarification"; clarification: ClarificationRequest }
  | { kind: "unsupported_route"; unsupported_route: UnsupportedRoute }
  | { kind: "scope_refusal"; message: string | null };

export type CardSummary = {
  id: string;
  bank: string;
  card_name: string;
  annual_fee_inr: number;
  has_lounge_access: boolean;
  acquirable: boolean;
};

export type CatalogCardsResponse = {
  catalog_snapshot_version: string;
  cards: CardSummary[];
};

/** GET /goals list item — one saved goal + its latest recommendation summary,
 * read straight from persisted rows (matches `SavedGoalSummary` in schemas.py). */
export type SavedGoal = {
  goal_id: string;
  goal_name: string;
  goal_type: string;
  destination_city: string | null;
  cabin_class: string | null;
  target_miles: number;
  target_date: string | null;
  status: string;
  saved_at: string;
  summary: string | null;
  confidence_score: number | null;
  catalog_snapshot_version: string | null;
};

export type SavedGoalsResponse = { goals: SavedGoal[] };

/** GET /goals/{id} — the persisted strategy behind a saved goal (matches
 * `SavedGoalDetail` in schemas.py). Everything is a stored engine artifact
 * from save time; only the name maps come from the current catalog. */
export type SavedLedgerEntry = {
  month: number;
  points_earned_this_month: number;
  cumulative_target_miles: number;
};

export type SavedMilestone = {
  milestone_id: string;
  card_id: string;
  expected_month: number;
  bonus_points: number;
};

export type SavedTransferPlanItem = {
  from_card_id: string;
  to_partner_id: string;
  points: number;
  planned_month: number;
};

export type SavedScoreBreakdown = {
  goal_achievement: string;
  efficiency: string;
  cost: string;
  simplicity: string;
  portfolio_utilization: string;
  risk: string;
};

/** One tier of the "your cards → +1 → +2" comparison (persisted compactly). */
export type SavedStrategyOption = {
  strategy_id: string;
  archetype: string;
  headline_differentiator: string;
  miles_at_target_date: number;
  months_to_goal: number | null;
  total_fees_inr: number;
  cards_used: string[];
  cards_to_acquire: string[];
  score: string | null;
  is_recommended: boolean;
  co_recommended: boolean;
};

export type SavedStrategy = {
  spend_allocation: Record<string, string>;
  cards_used: string[];
  cards_to_acquire: string[];
  ledger: SavedLedgerEntry[];
  months_to_goal: number | null;
  optimization_score: string | null;
  milestones: SavedMilestone[];
  transfer_plan: SavedTransferPlanItem[];
  allocation_details: AllocationDetail[];
  score_breakdown: SavedScoreBreakdown | null;
  headline_differentiator: string | null;
};

export type SavedGoalDetail = {
  goal_id: string;
  goal_name: string;
  goal_type: string;
  origin_city: string | null;
  destination_city: string | null;
  cabin_class: string | null;
  num_passengers: number | null;
  target_miles: number;
  target_date: string | null;
  status: string;
  saved_at: string;
  recommendation_type: string | null;
  summary: string | null;
  reasoning: string | null;
  action_items: { priority: number; action: string; impact: string | null }[];
  confidence_score: number | null;
  catalog_snapshot_version: string | null;
  engine_version: string | null;
  strategy: SavedStrategy | null;
  strategy_options: SavedStrategyOption[];
  card_names: Record<string, string>;
  partner_names: Record<string, string>;
};

// ── Calls ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function postJson<T>(
  path: string,
  body: unknown,
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Couldn't reach the strategy engine. Please try again in a moment.",
    );
  }
  if (!response.ok) {
    throw new ApiError(
      `The strategy engine returned an error (${response.status}).`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

/** Run the deterministic pipeline for a structured goal (anonymous). */
export function simulate(request: SimulateRequest): Promise<SimulateResponse> {
  return postJson<SimulateResponse>("/simulations", request);
}

/**
 * Run the pipeline AND persist it under the signed-in user (needs a Supabase
 * access token). Same shape as `simulate`, but the result is saved server-side.
 */
export function simulateAndSave(
  request: SimulateRequest,
  token: string,
): Promise<SimulateResponse> {
  return postJson<SimulateResponse>("/goals/recommendation/save", request, token);
}

/** The signed-in user's saved goals, newest first (needs a Supabase token). */
export async function fetchSavedGoals(token: string): Promise<SavedGoal[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/goals`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError("Couldn't reach the strategy engine. Please try again.");
  }
  if (response.status === 401) {
    throw new ApiError("Your session expired — please log in again.", 401);
  }
  if (!response.ok) {
    throw new ApiError(`Couldn't load your goals (${response.status}).`, response.status);
  }
  const body = (await response.json()) as SavedGoalsResponse;
  return body.goals;
}

/** One saved goal's full stored strategy (needs a Supabase token). */
export async function fetchSavedGoal(
  goalId: string,
  token: string,
): Promise<SavedGoalDetail> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/goals/${goalId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError("Couldn't reach the strategy engine. Please try again.");
  }
  if (response.status === 401) {
    throw new ApiError("Your session expired — please log in again.", 401);
  }
  if (response.status === 404) {
    throw new ApiError("We couldn't find that goal.", 404);
  }
  if (!response.ok) {
    throw new ApiError(`Couldn't load this goal (${response.status}).`, response.status);
  }
  return (await response.json()) as SavedGoalDetail;
}

/** Delete a saved goal (and its stored strategy) permanently. */
export async function deleteSavedGoal(
  goalId: string,
  token: string,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/goals/${goalId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new ApiError("Couldn't reach the strategy engine. Please try again.");
  }
  if (response.status === 401) {
    throw new ApiError("Your session expired — please log in again.", 401);
  }
  if (response.status === 404) {
    throw new ApiError("We couldn't find that goal.", 404);
  }
  if (!response.ok) {
    throw new ApiError(`Couldn't delete this goal (${response.status}).`, response.status);
  }
}

/** Supported cards for the wallet picker. */
export async function fetchCards(): Promise<CardSummary[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/catalog/cards`);
  } catch {
    throw new ApiError("Couldn't load the card catalog.");
  }
  if (!response.ok) {
    throw new ApiError(`Card catalog error (${response.status}).`, response.status);
  }
  const body = (await response.json()) as CatalogCardsResponse;
  return body.cards;
}
