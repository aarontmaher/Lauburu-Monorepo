/**
 * Canonical freshness/stale definition for the platform-native
 * health source — Apple Health on iOS, Health Connect on Android.
 *
 * Single source of truth for "is the native health source stale?"
 * Duplicating the threshold in component code leads to drift, which
 * is exactly the truth-label gap the v21 installed-device QA cycle
 * is designed to catch.
 *
 * Staleness threshold: 48 hours. Most modern sleep + HRV + RHR
 * readings land within minutes of waking; if no sync has happened
 * in two full days the source either disconnected or the user
 * hasn't launched the app since. Coach context, the Manage
 * Sources sheet, and the home widget all reach the same verdict
 * because they all import from this file.
 */

export const NATIVE_HEALTH_STALE_HOURS = 48;
export const NATIVE_HEALTH_STALE_MS = NATIVE_HEALTH_STALE_HOURS * 60 * 60 * 1000;

/**
 * True when the native health source's last sync is older than
 * NATIVE_HEALTH_STALE_HOURS. Returns false when lastSyncAt is
 * absent or unparseable — "we have no record" is not the same as
 * "we know it's stale", and the caller surfaces those distinctly.
 */
export function isNativeHealthSyncStale(
  lastSyncAt: string | null | undefined,
  nowMs: number = Date.now(),
): boolean {
  if (!lastSyncAt) return false;
  const syncedMs = new Date(lastSyncAt).getTime();
  if (!Number.isFinite(syncedMs)) return false;
  return nowMs - syncedMs > NATIVE_HEALTH_STALE_MS;
}

/**
 * Hours since lastSyncAt, rounded to one decimal place. Returns
 * null when lastSyncAt is absent or unparseable so the Coach AI
 * evidence builder can render a numeric freshness or "no record"
 * — never zero.
 */
export function hoursSinceNativeHealthSync(
  lastSyncAt: string | null | undefined,
  nowMs: number = Date.now(),
): number | null {
  if (!lastSyncAt) return null;
  const syncedMs = new Date(lastSyncAt).getTime();
  if (!Number.isFinite(syncedMs)) return null;
  const ms = Math.max(0, nowMs - syncedMs);
  return Math.round((ms / (60 * 60 * 1000)) * 10) / 10;
}
