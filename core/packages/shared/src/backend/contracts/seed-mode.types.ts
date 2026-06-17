/**
 * Seed-mode response metadata — appended to any backend read response
 * when the system is running from cached/exported seed data rather
 * than live WHOOP-native ingestion.
 *
 * Consumers check these fields to know:
 *   - whether the data is provisional
 *   - whether WHOOP-native readiness fields are missing
 *   - what caveats apply to the current response
 *
 * When live WHOOP is restored, `seedMode` becomes false and
 * `provisionalUntilDirectWhoop` becomes false.
 */

export interface SeedModeMetadata {
  /** True when the daily artifact is not for the requested date. */
  seedMode: boolean;
  /** True when source health indicates WHOOP is stale/degraded/missing. */
  provisionalUntilDirectWhoop: boolean;
  /** Human-readable warnings about data provenance. Empty when fully live. */
  seedCaveats: string[];
}

/**
 * Standard envelope shape for public/internal read responses that
 * include seed-mode awareness. Consumers can check these fields
 * before displaying readiness, recovery, or HRV data.
 */
export interface SeedAwareReadResponse extends SeedModeMetadata {
  ok: boolean;
  athleteId: string;
  date: string;
  confidence: string;
}
