/**
 * Thin client for the backend backlog analysis routes.
 *
 * All calls go through /api/backlog/<athleteId>/{status|skip|start},
 * which share the same JWT ownership guard as /api/athlete-memory.
 * The baseUrl is derived from AI_PUBLIC_BASE (athlete-memory origin);
 * the backlog routes are mounted on the same Express origin under a
 * different prefix.
 */

import { AI_PUBLIC_BASE, AI_PUBLIC_TOKEN, resolveAthleteId } from './ai-backend-config';

const TIMEOUT_MS = 20_000; // backlog start can be slow on first run

export interface BacklogClientConfig {
  baseUrl: string;
  token: string;
  athleteId: string;
  supabaseAccessToken: string | null;
}

export interface BacklogStatusResponse {
  ok: boolean;
  athleteId: string;
  status: {
    userId: string;
    athleteId: string;
    status: 'not_started' | 'permission_requested' | 'running' | 'partial' | 'complete' | 'failed' | 'skipped';
    consentGrantedAt: string | null;
    analysisStartedAt: string | null;
    analysisCompletedAt: string | null;
    windowStart: string | null;
    windowEnd: string | null;
    sourcesIncluded: string[];
    sourcesMissing: string[];
    recordsAnalysed: number;
    dailyArtifactsCreated: number;
    weeklyArtifactsCreated: number;
    patternCandidatesCreated: number;
    memoryProposalsCreated: number;
    missingnessNote: string | null;
    latestSummaryId: string | null;
    createdAt: string;
    updatedAt: string;
  };
  summary: {
    id: string;
    athleteId: string;
    generatedAt: string;
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
    earlyPatterns: string[];
    whatsMissing: string[];
    safeNextSteps: string[];
    reviewableMemoryCandidateIds: string[];
    comparison: {
      comparisonType: 'none' | 'curated_reference' | 'anonymous_cohort';
      cohortAvailable: boolean;
      cohortId: string | null;
      privacyLevel: 'aggregate_only';
      statement: string;
      confidenceImpact: 'none' | 'raises' | 'lowers';
      missingnessNote: string | null;
    };
    confidence: 'low' | 'medium' | 'high';
  } | null;
  trends: Array<{
    id: string;
    athleteId: string;
    kind: string;
    statement: string;
    evidenceFields: string[];
    windowStart: string;
    windowEnd: string;
    observationCount: number;
    confidence: 'low' | 'medium' | 'high';
    missingnessNote: string | null;
    eligibleForMemoryProposal: boolean;
    createdAt: string;
  }>;
}

function buildOrigin(): string {
  // Origin derived from AI_PUBLIC_BASE. Falls back to local dev.
  try {
    const u = new URL(AI_PUBLIC_BASE);
    return u.origin;
  } catch {
    return 'http://localhost:3000';
  }
}

export function buildBacklogClientConfig(
  userId: string | null | undefined,
  supabaseAccessToken: string | null | undefined,
): BacklogClientConfig | null {
  const athleteId = resolveAthleteId(userId);
  if (!athleteId) return null;
  return {
    baseUrl: buildOrigin(),
    token: AI_PUBLIC_TOKEN,
    athleteId,
    supabaseAccessToken: supabaseAccessToken ?? null,
  };
}

function headersFor(cfg: BacklogClientConfig): Record<string, string> {
  const h: Record<string, string> = {
    'Content-Type': 'application/json',
    'x-athlete-memory-token': cfg.token,
    'x-athlete-id': cfg.athleteId,
  };
  if (cfg.supabaseAccessToken) h['Authorization'] = `Bearer ${cfg.supabaseAccessToken}`;
  return h;
}

async function req<T>(
  method: 'GET' | 'POST',
  url: string,
  cfg: BacklogClientConfig,
  body?: unknown,
): Promise<{ ok: true; data: T } | { ok: false; error: string; status?: number }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      method,
      signal: controller.signal,
      headers: headersFor(cfg),
      body: body ? JSON.stringify(body) : undefined,
    });
    clearTimeout(timer);
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      return { ok: false, error: text.slice(0, 300) || `HTTP ${resp.status}`, status: resp.status };
    }
    return { ok: true, data: (await resp.json()) as T };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'Network error' };
  }
}

export async function getBacklogStatus(cfg: BacklogClientConfig) {
  return req<BacklogStatusResponse>(
    'GET',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/status`,
    cfg,
  );
}

export async function startBacklog(
  cfg: BacklogClientConfig,
  opts?: { windowDays?: number; dryRun?: boolean; sources?: string[] },
) {
  return req<Pick<BacklogStatusResponse, 'ok' | 'status' | 'summary'> & { trendCandidates: BacklogStatusResponse['trends'] }>(
    'POST',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/start`,
    cfg,
    opts ?? {},
  );
}

export async function skipBacklog(cfg: BacklogClientConfig) {
  return req<Pick<BacklogStatusResponse, 'ok' | 'status'>>(
    'POST',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/skip`,
    cfg,
  );
}

export interface ProposalsResponse {
  ok: boolean;
  athleteId: string;
  trendProposals: Array<{
    id: string;
    kind: string;
    statement: string;
    confidence: 'low' | 'medium' | 'high';
    evidenceFields: string[];
    windowStart: string;
    windowEnd: string;
    observationCount: number;
    createdAt: string;
    source: 'backlog_analysis';
  }>;
  weeklyCandidates: Array<{
    index: number;
    targetDoc: string;
    statement: string;
    confidence: string;
    eligible: boolean;
    approvalRequired: boolean;
    rejectionReason: string | null;
    windowStart: string;
    windowEnd: string;
    source: 'weekly_synthesis';
  }>;
  totalProposals: number;
}

export async function getProposals(cfg: BacklogClientConfig) {
  return req<ProposalsResponse>(
    'GET',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/proposals`,
    cfg,
  );
}

export async function acceptProposal(cfg: BacklogClientConfig, candidateIndex: number | string, source: string) {
  return req<{ ok: boolean; outcome: string; reason: string; statement?: string }>(
    'POST',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/proposals/accept`,
    cfg,
    { candidateIndex, source },
  );
}

export async function rejectProposal(cfg: BacklogClientConfig, candidateIndex: number | string, source: string) {
  return req<{ ok: boolean; outcome: string; reason: string }>(
    'POST',
    `${cfg.baseUrl}/api/backlog/${cfg.athleteId}/proposals/reject`,
    cfg,
    { candidateIndex, source },
  );
}
