/**
 * Cronometer connection adapter — mobile-side boundary for
 * Cronometer nutrition data integration.
 *
 * Current external blocker: Cronometer does not offer a public
 * API for third-party apps. This adapter is fully wired and ready:
 * when credentials become available, only checkConnection() and
 * syncDaily() need real implementations. Everything else
 * (source-health, ai-context, Coach) is already wired.
 *
 * Connection states exposed to the UI and Coach:
 *   connected        — actively syncing
 *   not_connected    — no credentials configured
 *   auth_required    — credentials needed
 *   auth_expired     — was connected, token expired
 *   unavailable      — API unreachable
 *   stale            — connected but last sync old
 */
import type { CronometerConnectionState, CronometerConnectionStatus } from '@lauburu/shared';
import { secureStorage } from '../store/secure-storage';
import { AI_INTERNAL_BASE, AI_INTERNAL_TOKEN } from './ai-backend-config';

const STORAGE_KEY = 'cronometer_connection_v1';

/** Read local connection state from secureStorage. */
export async function getCronometerConnectionState(): Promise<CronometerConnectionState> {
  try {
    const raw = await secureStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as CronometerConnectionState;
      if (parsed && parsed.status) return parsed;
    }
  } catch {
    // Fall through to default.
  }
  return {
    status: 'not_connected',
    lastSyncAt: null,
    reason: 'Cronometer does not currently offer a public API for third-party apps.',
    hasCredentials: false,
    actionRequired: 'Use manual nutrition entry, barcode scanning, or AI photo logging as alternatives.',
  };
}

/** Set connection state (called by backend sync result or future OAuth flow). */
export async function setCronometerConnectionState(
  status: CronometerConnectionStatus,
  reason?: string,
  hasCredentials?: boolean,
): Promise<void> {
  const state: CronometerConnectionState = {
    status,
    lastSyncAt: status === 'connected' ? new Date().toISOString() : null,
    reason: reason ?? null,
    hasCredentials: hasCredentials ?? false,
    actionRequired: status === 'not_connected'
      ? 'Use manual nutrition entry, barcode scanning, or AI photo logging as alternatives.'
      : status === 'auth_required'
        ? 'Configure Cronometer credentials to enable syncing.'
        : null,
  };
  try {
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Swallowed — connection state is advisory, not critical.
  }
}

/** Check if Cronometer is currently connected. */
export async function isCronometerConnected(): Promise<boolean> {
  const state = await getCronometerConnectionState();
  return state.status === 'connected';
}

/**
 * Check Cronometer connection status from the backend.
 * Fire-and-forget safe — never throws, returns local state on failure.
 */
export async function checkCronometerStatusFromBackend(
  athleteId: string,
): Promise<CronometerConnectionState> {
  if (!AI_INTERNAL_TOKEN) return getCronometerConnectionState();
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const resp = await fetch(`${AI_INTERNAL_BASE}/cronometer/${athleteId}/status`, {
      headers: { 'x-internal-token': AI_INTERNAL_TOKEN },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!resp.ok) return getCronometerConnectionState();
    const data = await resp.json();
    const connState = data.connection as CronometerConnectionState;
    // Persist locally
    await setCronometerConnectionState(
      connState.status,
      connState.reason ?? undefined,
      connState.hasCredentials,
    );
    return connState;
  } catch {
    return getCronometerConnectionState();
  }
}

/**
 * Attempt to sync Cronometer nutrition for a date.
 * Returns the sync result. If not connected, returns honest blocked status.
 */
export async function syncCronometerDaily(
  athleteId: string,
  date?: string,
): Promise<{
  ok: boolean;
  status: CronometerConnectionStatus;
  reason: string | null;
  coverage?: string[];
}> {
  if (!AI_INTERNAL_TOKEN) return { ok: false, status: 'not_connected', reason: 'Backend not configured.' };
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    const resp = await fetch(`${AI_INTERNAL_BASE}/cronometer/${athleteId}/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({ date }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const data = await resp.json();
    // Update local state
    await setCronometerConnectionState(
      data.status ?? 'not_connected',
      data.reason ?? null,
      data.hasCredentials ?? false,
    );
    return {
      ok: data.ok ?? false,
      status: data.status ?? 'not_connected',
      reason: data.reason ?? null,
      coverage: data.coverage,
    };
  } catch {
    return {
      ok: false,
      status: 'unavailable',
      reason: 'Backend unreachable.',
    };
  }
}
