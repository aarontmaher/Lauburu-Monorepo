/**
 * First-run backlog analysis — permissioned per-user, per-athlete.
 *
 * The athlete opts in (explicit consent) to have Coach analyse the
 * historical data they've already connected (Health Connect, Polar via
 * HC, WHOOP if owned, Cronometer, manual nutrition, HIIT/session logs,
 * machine sessions). The pipeline produces:
 *
 *   - backfilled daily_refresh_artifact rows for every day with data
 *   - weekly_synthesis_artifact rows covering completed ISO weeks
 *   - trend candidates (provisional, never auto-promoted)
 *   - memory proposals (explicit review required)
 *   - an initial Coach-facing summary ("what Coach can tell so far")
 *
 * Hard privacy invariants enforced by every service in this pipeline:
 *
 *   - analysis reads ONLY records scoped to the passed athleteId; it
 *     never joins across athletes
 *   - cohort/comparison layer is curated-reference-only today — no
 *     other user's private memory is ever read, mixed, or surfaced
 *   - stable memory is never silently updated; pattern candidates and
 *     memory proposals are the only durable outputs this pipeline
 *     produces, both of which require user approval before promotion
 *   - the consent record itself is the contract — no data is pulled
 *     through the pipeline without `consentGrantedAt` set on the status
 */

export type BacklogAnalysisStatus =
  | 'not_started'
  | 'permission_requested'
  | 'running'
  | 'partial'
  | 'complete'
  | 'failed'
  | 'skipped';

/**
 * Classification applied to each source when Coach runs source
 * discovery at the start of a backlog analysis. Mirrors the
 * `SourceConnectionStatus` vocabulary used by buildMultiSourceHealth
 * so the UI can render these rows with the same labels.
 */
export type BacklogSourceState =
  | 'connected'
  | 'permission_required'
  | 'sync_needed'
  | 'not_connected'
  | 'unavailable'
  | 'stale'
  | 'partial';

export interface BacklogSourceDiscovery {
  source: string; // e.g. 'health_connect', 'polar_via_health_connect', 'whoop', 'cronometer', 'manual_nutrition', 'hiit_sessions'
  state: BacklogSourceState;
  /** For Polar via HC and similar: the upstream app identifier when known. */
  sourceApp?: string | null;
  /** Which domains this source can contribute on this user's account. */
  domainsAvailable: string[];
  /** Why the source is in its current state (human-readable). */
  reason: string | null;
}

/**
 * Per-user backlog analysis status record. Stored server-side under
 * the athlete's memory namespace; loaded into the first-run Coach
 * prompt on app open. The userId field is captured explicitly so a
 * later server-side audit can confirm the signed-in Supabase user
 * matches the athleteId the record was saved under.
 */
export interface BacklogAnalysisStatusRecord {
  userId: string;
  athleteId: string;
  status: BacklogAnalysisStatus;

  /** ISO-8601. Set when user taps "Analyse my history". Cleared on skip. */
  consentGrantedAt: string | null;
  /** ISO-8601. Set when the service actually begins reading records. */
  analysisStartedAt: string | null;
  /** ISO-8601. Set on complete, partial, or failed — whichever ends the run. */
  analysisCompletedAt: string | null;

  /** Window the most recent run covered. Default 30 days, allowed up to 90. */
  windowStart: string | null; // YYYY-MM-DD
  windowEnd: string | null;   // YYYY-MM-DD

  sourcesIncluded: string[];
  sourcesMissing: string[];

  recordsAnalysed: number;
  dailyArtifactsCreated: number;
  weeklyArtifactsCreated: number;
  patternCandidatesCreated: number;
  memoryProposalsCreated: number;

  missingnessNote: string | null;

  /**
   * Whether the analysis had access to full Health Connect history
   * (Android 14+ PERMISSION_READ_HEALTH_DATA_HISTORY) or was limited
   * to the default ~30-day window.
   */
  historyScope: 'full_history' | 'limited_history' | 'unknown';

  /**
   * ID of the most recently produced initial summary (see
   * BacklogInitialSummary). The full summary body is stored separately
   * so re-runs can overwrite without losing historical status rows if
   * a future schema adds versioning.
   */
  latestSummaryId: string | null;

  createdAt: string;
  updatedAt: string;
}

/**
 * A candidate trend found in this user's own history. Provisional by
 * construction — never auto-promoted. The eligibility gate is explicit
 * so Coach can show "reviewable memory suggestions" distinctly from
 * "early patterns that need more data."
 */
export interface BacklogTrendCandidate {
  id: string;
  athleteId: string;
  kind: TrendKind;
  statement: string;
  /** Which normalized fields the pattern is grounded in. */
  evidenceFields: string[];
  windowStart: string;
  windowEnd: string;
  observationCount: number;
  confidence: 'low' | 'medium' | 'high';
  /** Explicit "what would make this statement stronger" note. */
  missingnessNote: string | null;
  /**
   * Whether this candidate clears the bar to become a memory proposal.
   * Eligibility requires confidence ≥ medium AND at least 2 weeks of
   * supporting observations AND no readiness-claim requirements.
   */
  eligibleForMemoryProposal: boolean;
  createdAt: string;
}

export type TrendKind =
  | 'sleep_consistency'
  | 'training_frequency'
  | 'hiit_frequency'
  | 'zone2_vs_hiit_balance'
  | 'grappling_session_load'
  | 'heart_rate_resting_trend'
  | 'workout_duration_trend'
  | 'nutrition_consistency'
  | 'nutrition_protein_coverage'
  | 'nutrition_calories_coverage'
  | 'logging_completeness'
  // Gated — only generated when direct user-owned WHOOP is live.
  | 'recovery_trend'
  | 'hrv_trend'
  | 'strain_trend';

/**
 * Privacy-safe comparison output. The backlog pipeline ONLY emits
 * curated_reference today — `anonymous_cohort` is reserved for a
 * future layer that must include a privacy review before enabling.
 * If that layer is absent, `cohortAvailable` is false and the
 * statement leans on curated training knowledge only.
 */
export interface BacklogCohortComparison {
  comparisonType: 'none' | 'curated_reference' | 'anonymous_cohort';
  cohortAvailable: boolean;
  cohortId: string | null;
  privacyLevel: 'aggregate_only';
  statement: string;
  confidenceImpact: 'none' | 'raises' | 'lowers';
  missingnessNote: string | null;
}

/**
 * The "what Coach can tell so far" summary. Produced once per run.
 * The ID lets the UI deep-link back to it and lets future re-runs
 * overwrite atomically without stranding stale references.
 */
export interface BacklogInitialSummary {
  id: string;
  athleteId: string;
  generatedAt: string;

  /** "Data found" section */
  dataFound: {
    normalizedDays: number;
    healthConnectDays: number;
    appleHealthDays: number;
    polarViaHealthConnectDays: number;
    whoopDays: number;
    cronometerDays: number;
    manualNutritionDays: number;
    hiitSessions: number;
    grapplingSessions: number;
  };

  /** "Early patterns" — short human-readable statements, not types. */
  earlyPatterns: string[];

  /** "What's missing" — honest list of sources not contributing. */
  whatsMissing: string[];

  /** "Safe next steps" — always non-prescriptive, never readiness claims. */
  safeNextSteps: string[];

  /** "Reviewable memory suggestions" — IDs of candidates that cleared eligibility. */
  reviewableMemoryCandidateIds: string[];

  /** Attached cohort/reference comparison — informational. */
  comparison: BacklogCohortComparison;

  confidence: 'low' | 'medium' | 'high';
}

/**
 * Input to the backfill service. `sources` is optional; when omitted,
 * the service auto-discovers available sources for the athlete. The
 * `dryRun` flag lets the mobile UI preview what would be analysed
 * without touching artifact storage — useful for the consent screen.
 */
export interface RunBacklogAnalysisInput {
  userId: string;
  athleteId: string;
  windowStart: string; // YYYY-MM-DD
  windowEnd: string;   // YYYY-MM-DD
  sources?: string[];
  dryRun?: boolean;
  /** Whether full Health Connect history was available for this run. */
  historyScope?: 'full_history' | 'limited_history' | 'unknown';
}

export interface RunBacklogAnalysisResult {
  status: BacklogAnalysisStatusRecord;
  summary: BacklogInitialSummary | null;
  trendCandidates: BacklogTrendCandidate[];
}
