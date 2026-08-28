/**
 * Mobile client for the private athlete-memory backend.
 *
 * Consumes backend artifacts — does NOT own memory design,
 * freshness policy, promotion logic, or raw WHOOP interpretation.
 * The backend is authoritative; this client reads and displays.
 *
 * Freshness rules:
 *   - An artifact is "fresh" if generatedAt is today (local date).
 *   - An artifact is "stale" if generatedAt is before today.
 *   - An artifact is "expired" if now > expiresAt.
 *   - A missing artifact means the backend hasn't generated one yet.
 *   - Source degraded means the backend ran but had incomplete inputs.
 *
 * The mobile app should NEVER invent coaching claims that aren't
 * in the artifact. Display what the backend computed, show freshness
 * honestly, and surface degraded/missing states to the user.
 */

import type {
  AthleteDailyRefreshArtifact,
  AthleteWeeklySynthesisArtifact,
  AthleteMemoryRecord,
  AthleteSourceStatus,
  AthleteConfidence,
  AthleteDayState,
  VideoAttachmentSummary,
} from '@lauburu/shared';
import {
  ATHLETE_CAPABILITY_COPY,
  deriveAthleteCapabilityMode,
  type AthleteCapabilityMode,
} from './athlete-capability-display';

// ---------------------------------------------------------------------------
// API response envelope
// ---------------------------------------------------------------------------

/** Shape returned by GET /api/athlete-memory/:id/latest */
export interface AthleteLatestArtifactsResponse {
  ok?: boolean;
  athleteId?: string;
  date?: string;
  confidence?: AthleteConfidence | null;
  memory: AthleteMemoryRecord | null;
  latestDaily: AthleteDailyRefreshArtifact | null;
  latestWeekly: AthleteWeeklySynthesisArtifact | null;
  dailyArtifact?: AthleteDailyRefreshArtifact | null;
  weeklyArtifact?: AthleteWeeklySynthesisArtifact | null;
  stableMemory?: AthleteMemoryRecord | null;
  sourceHealth?: unknown;
  seedMode?: boolean;
  provisionalUntilDirectWhoop?: boolean;
  seedCaveats?: string[];
}

export interface AthleteHealthCheckResponse {
  athleteId: string;
  checkedAt: string;
  mode: 'seed_partial' | 'live_partial' | 'live_ready' | 'uninitialized';
  seedMode: boolean;
  provisionalUntilDirectWhoop: boolean;
  missingWhoopNativeFields: string[];
  safeFor: string[];
  notSafeFor: string[];
  recommendedReadOrder: string[];
}

export interface AthleteAiContextResponse {
  ok: boolean;
  athleteId: string;
  date: string;
  seedMode: boolean;
  provisionalUntilDirectWhoop: boolean;
  seedCaveats: string[];
  capability: {
    mode: 'seed_partial' | 'live_partial' | 'live_ready' | 'uninitialized';
    safeFor: string[];
    notSafeFor: string[];
    missingWhoopNativeFields: string[];
    recommendedReadOrder: string[];
  };
  sourceHealth?: {
    status?: string | null;
    summary?: string | null;
    fallbackReason?: string | null;
    missingInputs?: string[];
    sourceCoverage?: string[];
  } | null;
  normalizedDay?: {
    date?: string;
    recoveryScore?: number | null;
    sleepHours?: number | null;
    dayStrain?: number | null;
    nutritionCoverage?: string | null;
  } | null;
  dailyArtifact?: AthleteDailyRefreshArtifact | null;
  weeklyArtifact?: AthleteWeeklySynthesisArtifact | null;
  baselines?: {
    recoveryBaseline: number | null;
    hrvBaseline: number | null;
    restingHrBaseline: number | null;
    sleepBaseline: number | null;
    strainBaseline: number | null;
    dataWindowDays: number;
    computedAt: string;
  } | null;
  blockSummary?: string | null;
  nutritionDailySummary?: {
    calories: number | null;
    proteinGrams: number | null;
    carbGrams: number | null;
    fatGrams: number | null;
    coverage: 'full' | 'partial' | 'none';
    missingFields: string[];
    sourceState?: 'live' | 'manual' | 'estimated' | 'mixed' | null;
    sourceDependencies?: string[];
    allConfirmed?: boolean;
  } | null;
  confidence?: AthleteConfidence | null;
}

export interface AthleteVideoAttachmentsResponse {
  ok: boolean;
  athleteId: string;
  belt: string;
  totalTechniques: number;
  attachedReady: number;
  attachedUnavailable: number;
  notAttached: number;
  items: VideoAttachmentSummary[];
  note: string;
}

export type CoachAnswerDomain = 'hiit' | 'nutrition' | 'recovery' | 'training' | 'general';
export type CoachAnswerStatus = 'answered' | 'downgraded' | 'insufficient_data' | 'unsupported';
export type CoachConfidence = 'high' | 'medium' | 'low' | 'speculative';

export interface CoachAnswerResponse {
  ok: boolean;
  domain: CoachAnswerDomain;
  mode: 'seed_partial' | 'live_partial' | 'live_ready' | 'uninitialized';
  questionClass: string;
  status: CoachAnswerStatus;
  answer: {
    short: string;
    why: string;
    nextStep: string;
    missingnessNote: string | null;
  };
  confidence: CoachConfidence;
  sourceDependencies: string[];
  missingFields: string[];
  safetyFlags: string[];
  upgradeHint?: string | null;
}

// ---------------------------------------------------------------------------
// Freshness classification — mobile-side display logic only
// ---------------------------------------------------------------------------

export type ArtifactFreshness = 'fresh' | 'stale' | 'expired' | 'missing';

export function classifyFreshness(
  artifact: { generatedAt: string; expiresAt: string } | null,
  nowIso?: string,
): ArtifactFreshness {
  if (!artifact) return 'missing';
  const now = nowIso ?? new Date().toISOString();
  if (now > artifact.expiresAt) return 'expired';
  const todayDate = now.slice(0, 10);
  const generatedDate = artifact.generatedAt.slice(0, 10);
  return generatedDate >= todayDate ? 'fresh' : 'stale';
}

// ---------------------------------------------------------------------------
// UI-ready display state — what screens actually render
// ---------------------------------------------------------------------------

export interface AthleteArtifactDisplayState {
  /** Whether we're currently fetching from the backend. */
  loading: boolean;
  /** Fetch error message, if any. */
  error: string | null;

  /** Daily artifact freshness for display. */
  dailyFreshness: ArtifactFreshness;
  /** Weekly artifact freshness for display. */
  weeklyFreshness: ArtifactFreshness;

  /** Today's readiness state from the daily artifact (if available). */
  dayState: AthleteDayState | null;
  /** Today's confidence level. */
  confidence: AthleteConfidence | null;
  /** Primary guidance line from the daily artifact. */
  guidanceLine: string | null;
  /** Key drivers from the daily artifact. */
  keyDrivers: string[];
  /** Warning flags from the daily artifact. */
  warnings: string[];

  /** Source health — is the backend's data source working? */
  sourceStatus: AthleteSourceStatus | null;
  /** Human-readable source note. */
  sourceNote: string | null;

  /** Weekly dominant driver (if weekly exists). */
  weeklyDriver: string | null;
  /** Weekly focus items for next week. */
  weeklyFocus: string[];
  /** Shared mobile capability state for seed/provisional/live truth. */
  capabilityMode: AthleteCapabilityMode;

  /** Seed-mode marker from the backend envelope. */
  seedMode: boolean;
  /** Provisional marker until direct WHOOP-backed coverage improves. */
  provisionalUntilDirectWhoop: boolean;
  /** Compact caveats from the backend seed envelope. */
  seedCaveats: string[];

  /** Current block summary from stable memory. */
  blockSummary: string | null;

  /** Raw artifacts for components that need deeper access. */
  raw: AthleteLatestArtifactsResponse | null;
}

/**
 * Derive the full UI display state from the backend response.
 * Pure function — no side effects, no network calls.
 */
export function deriveDisplayState(
  response: AthleteLatestArtifactsResponse | null,
  loading: boolean,
  error: string | null,
): AthleteArtifactDisplayState {
  if (!response) {
    return {
      loading,
      error,
      dailyFreshness: 'missing',
      weeklyFreshness: 'missing',
      dayState: null,
      confidence: null,
      guidanceLine: null,
      keyDrivers: [],
      warnings: [],
      sourceStatus: null,
      sourceNote: null,
      weeklyDriver: null,
      weeklyFocus: [],
      capabilityMode: 'seed',
      seedMode: false,
      provisionalUntilDirectWhoop: false,
      seedCaveats: [],
      blockSummary: null,
      raw: null,
    };
  }

  const memory = response.memory ?? response.stableMemory ?? null;
  const latestDaily = response.latestDaily ?? response.dailyArtifact ?? null;
  const latestWeekly = response.latestWeekly ?? response.weeklyArtifact ?? null;

  const dailyFreshness = classifyFreshness(latestDaily);
  const weeklyFreshness = classifyFreshness(latestWeekly);

  return {
    loading,
    error,
    dailyFreshness,
    weeklyFreshness,

    dayState: latestDaily?.dayClassification.state ?? null,
    confidence: latestDaily?.confidence ?? null,
    guidanceLine: latestDaily?.nextBestAction.guidance ?? null,
    keyDrivers: latestDaily?.keyDrivers ?? [],
    warnings: latestDaily?.warningFlags.map((f) => f.label) ?? [],

    sourceStatus: latestDaily?.sourceState.status ?? null,
    sourceNote: formatSourceNote(
      latestDaily,
      response.seedMode ?? false,
      response.provisionalUntilDirectWhoop ?? false,
    ),

    weeklyDriver: latestWeekly?.dominantDriver ?? null,
    weeklyFocus: latestWeekly?.nextThreeToSevenDayGuidance.map((g) => g.guidance) ?? [],
    capabilityMode: deriveAthleteCapabilityMode({
      seedMode: response.seedMode ?? false,
      provisionalUntilDirectWhoop: response.provisionalUntilDirectWhoop ?? false,
      confidence: latestDaily?.confidence ?? response.confidence ?? null,
    }),

    seedMode: response.seedMode ?? false,
    provisionalUntilDirectWhoop: response.provisionalUntilDirectWhoop ?? false,
    seedCaveats: response.seedCaveats ?? [],

    blockSummary: memory?.currentBlockSummary ?? null,

    raw: response,
  };
}

function formatSourceNote(
  daily: AthleteDailyRefreshArtifact | null,
  seedMode: boolean,
  provisionalUntilDirectWhoop: boolean,
): string | null {
  if (seedMode || provisionalUntilDirectWhoop) {
    return ATHLETE_CAPABILITY_COPY.provisionalBackendNote;
  }
  if (!daily) return null;
  const { sourceState } = daily;
  if (sourceState.status === 'ready') {
    return `Data from ${sourceState.sourceCoverage.join(', ')} as of ${daily.sourceDate}`;
  }
  if (sourceState.status === 'degraded') {
    const reason = sourceState.fallbackReason === 'whoop_mcp_auth_not_restored'
      ? 'WHOOP connection needs refresh'
      : sourceState.fallbackReason === 'cached_history_only'
        ? 'Using cached history'
        : 'Some data sources unavailable';
    return `${reason} — ${sourceState.missingInputs.length ? `missing: ${sourceState.missingInputs.join(', ')}` : 'partial coverage'}`;
  }
  return 'Data source unavailable';
}

// ---------------------------------------------------------------------------
// Freshness labels for UI copy — never overclaim
// ---------------------------------------------------------------------------

export function freshnessLabel(freshness: ArtifactFreshness): string {
  switch (freshness) {
    case 'fresh': return 'Seed updated today';
    case 'stale': return 'Seed from a previous day';
    case 'expired': return 'Seed expired — waiting for refresh';
    case 'missing': return 'Not yet available';
  }
}

export function dayStateLabel(state: AthleteDayState): string {
  switch (state) {
    case 'green': return 'Good to train';
    case 'yellow': return 'Train with caution';
    case 'red': return 'Recovery day';
    case 'blocked': return 'Rest recommended';
  }
}

export function dayStateColor(state: AthleteDayState): string {
  switch (state) {
    case 'green': return '#4ade80';
    case 'yellow': return '#d4e157';
    case 'red': return '#ff6b6b';
    case 'blocked': return '#666';
  }
}

// ---------------------------------------------------------------------------
// API client — fetch from backend
// ---------------------------------------------------------------------------

const TIMEOUT_MS = 8000;

export interface AthleteMemoryClientConfig {
  /** Base URL for the athlete-memory API. */
  baseUrl: string;
  /** Shared API token for private athlete routes. */
  token: string;
  /** Athlete ID (must equal authenticated user's id). */
  athleteId: string;
  /** Supabase access token — backend uses this for ownership check. */
  supabaseAccessToken?: string | null;
}

import { AI_PUBLIC_BASE, AI_PUBLIC_TOKEN, resolveAthleteId } from './ai-backend-config';

/**
 * Build a per-user client config. Returns null when no user is signed in
 * in a production context — callers MUST handle null and not read data.
 *
 * SECURITY: Never share a single config across users. Each request must
 * carry the signed-in user's own athleteId and Supabase access token so
 * the backend can verify ownership.
 */
export function buildAthleteMemoryClientConfig(
  userId: string | null | undefined,
  supabaseAccessToken?: string | null,
): AthleteMemoryClientConfig | null {
  const athleteId = resolveAthleteId(userId);
  if (!athleteId) return null;
  return {
    baseUrl: AI_PUBLIC_BASE,
    token: AI_PUBLIC_TOKEN,
    athleteId,
    supabaseAccessToken: supabaseAccessToken ?? null,
  };
}

/** Build headers with ownership claim for each request. */
function buildHeaders(config: AthleteMemoryClientConfig): Record<string, string> {
  const h: Record<string, string> = {
    'x-athlete-memory-token': config.token,
    'x-athlete-id': config.athleteId,
  };
  if (config.supabaseAccessToken) {
    h['Authorization'] = `Bearer ${config.supabaseAccessToken}`;
  }
  return h;
}

async function fetchWithTimeout<T>(
  url: string,
  headers: Record<string, string>,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...headers },
    });
    if (!resp.ok) {
      const body = await resp.text().catch(() => '');
      throw new Error(`${resp.status}: ${body.slice(0, 200)}`);
    }
    return resp.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

async function postWithTimeout<T>(
  url: string,
  headers: Record<string, string>,
  body: unknown,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`${resp.status}: ${text.slice(0, 200)}`);
    }
    return resp.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch the latest artifacts for an athlete from the backend.
 * Returns null on network/auth failure (never throws — caller
 * handles the error via the returned state).
 */
export async function fetchLatestArtifacts(
  config: AthleteMemoryClientConfig,
): Promise<{ data: AthleteLatestArtifactsResponse | null; error: string | null }> {
  try {
    const data = await fetchWithTimeout<AthleteLatestArtifactsResponse>(
      `${config.baseUrl}/${config.athleteId}/latest`,
      buildHeaders(config),
    );
    return { data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return { data: null, error: msg };
  }
}

export async function fetchHealthCheck(
  config: AthleteMemoryClientConfig,
): Promise<{ data: AthleteHealthCheckResponse | null; error: string | null }> {
  try {
    const data = await fetchWithTimeout<AthleteHealthCheckResponse>(
      `${config.baseUrl}/${config.athleteId}/health-check`,
      buildHeaders(config),
    );
    return { data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return { data: null, error: msg };
  }
}

export async function fetchAiContext(
  config: AthleteMemoryClientConfig,
  date?: string,
): Promise<{ data: AthleteAiContextResponse | null; error: string | null }> {
  try {
    const suffix = date ? `?date=${encodeURIComponent(date)}` : '';
    const data = await fetchWithTimeout<AthleteAiContextResponse>(
      `${config.baseUrl}/${config.athleteId}/ai-context${suffix}`,
      buildHeaders(config),
    );
    return { data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return { data: null, error: msg };
  }
}

export async function fetchVideoAttachments(
  config: AthleteMemoryClientConfig,
  belt?: string,
): Promise<{ data: AthleteVideoAttachmentsResponse | null; error: string | null }> {
  try {
    const suffix = belt ? `?belt=${encodeURIComponent(belt)}` : '';
    const data = await fetchWithTimeout<AthleteVideoAttachmentsResponse>(
      `${config.baseUrl}/${config.athleteId}/videos${suffix}`,
      buildHeaders(config),
    );
    return { data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return { data: null, error: msg };
  }
}

/**
 * Ask the Coach. The app-owned device-agnostic athlete analysis
 * layer (AppAthleteState) is sent alongside the question so the
 * backend can reason over our normalized concepts (recovery_context,
 * load_context, fueling_adequacy, etc.) instead of reconstructing
 * them from raw vendor metrics. Backends that don't understand the
 * app_athlete_state field simply ignore it — safe to ship now.
 */
export async function fetchCoachAnswer(
  config: AthleteMemoryClientConfig,
  input: {
    question: string;
    topic?: string;
    app_athlete_state?: unknown;
    nutrition_today?: unknown;
    nutrition_targets?: unknown;
    session_summary?: unknown;
    // Backlog context — already ingested to Railway per-user but not
    // previously attached to the Coach request. Without these fields
    // Coach sees ~1 day of history and can't answer "how has my
    // fueling trended" / "what's different this week" questions.
    // Backends that don't yet know these fields simply ignore them.
    nutrition_history?: unknown;
    recent_sessions?: unknown;
    hiit_history?: unknown;
    whoop_csv_coverage?: unknown;
    platform?: string;
  },
): Promise<{ data: CoachAnswerResponse | null; error: string | null }> {
  try {
    const data = await postWithTimeout<CoachAnswerResponse>(
      `${config.baseUrl}/${config.athleteId}/coach/ask`,
      buildHeaders(config),
      input,
    );
    return { data, error: null };
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Unknown error';
    return { data: null, error: msg };
  }
}
