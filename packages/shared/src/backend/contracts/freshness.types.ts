/**
 * Freshness policy types — decides when live WHOOP reads are allowed.
 *
 * Live WHOOP is allowed ONLY when:
 *   1. artifact freshness is expired
 *   2. cached normalized/raw data is missing a required field
 *   3. source health indicates failed or incomplete ingest
 *   4. the user explicitly asks for current real-time status
 *
 * Everything else reads from cached artifacts.
 */

// ── Source health (first-class object) ────────────────────────

export type FreshnessStatus = 'fresh' | 'stale' | 'expired' | 'missing';
export type UpstreamStatus = 'healthy' | 'degraded' | 'down' | 'unknown';

export interface SourceHealthStatus {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;

  athleteId: string;
  provider: string;

  /** When the last successful ingest completed. */
  lastSuccessfulIngestAt: string | null;
  /** When the last ingest attempt failed. */
  lastFailedIngestAt: string | null;
  /** Current freshness of ingested data. */
  freshnessStatus: FreshnessStatus;
  /** Per-domain coverage. */
  coverageByDomain: Record<string, {
    lastDate: string | null;
    status: FreshnessStatus;
  }>;
  /** Current upstream provider status. */
  upstreamStatus: UpstreamStatus;
  /** Why the source is degraded, if applicable. */
  degradedReason: string | null;
}

// ── Freshness decision input/output ───────────────────────────

export interface FreshnessDecisionInput {
  /** Current daily artifact for this athlete (if any). */
  latestArtifactFreshUntil: string | null;
  /** Source health for the primary provider. */
  sourceHealth: SourceHealthStatus | null;
  /** Whether the user explicitly requested real-time data. */
  userRequestedRealtime: boolean;
  /** Fields the caller needs that may be missing from cache. */
  requiredFields: string[];
  /** Fields actually present in cached normalized data. */
  cachedPresentFields: string[];
}

export interface FreshnessDecisionResult {
  /** Whether a live WHOOP read is allowed. */
  liveReadAllowed: boolean;
  /** Why. */
  reason: string;
  /** Which of the four allowed conditions was met (or 'denied'). */
  trigger: 'artifact_expired' | 'missing_required_field' | 'source_unhealthy' | 'user_requested' | 'denied';
}
