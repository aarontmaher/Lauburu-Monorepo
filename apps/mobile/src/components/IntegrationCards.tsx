/**
 * Integration status cards — renders per-user status for all third-party
 * sources (Polar direct, WHOOP direct, Concept2, Cronometer). Each card
 * fetches its own status from the backend, renders truthfully, and wires
 * connect/disconnect/sync actions where the backend supports them.
 *
 * Key invariants:
 *   - No fake connected states. If config is missing, say so with setup
 *     instructions.
 *   - Non-owner users never see Aaron's WHOOP bridge data.
 *   - Polar via Apple Health / Health Connect and direct Polar are shown distinctly.
 *   - Manual nutrition/barcode/photo are always available regardless of
 *     Cronometer status.
 */
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Pressable, ActivityIndicator, Linking, Alert } from 'react-native';
import { Text, View } from '@/components/Themed';
import { Platform } from 'react-native';
import { useAuthStore } from '../store/auth-store';
import { useHealthStore } from '../store/health-store';
import {
  buildIntegrationConfig,
  getPolarStatus,
  getPolarConnectUrl,
  disconnectPolar,
  syncPolar,
  getWhoopStatus,
  getWhoopConnectUrl,
  disconnectWhoop,
  syncWhoop,
  backfillWhoop,
} from '../services/integrations-client';

// ═══════════════════════════════════════════════════════════════
// Shared helpers
// ═══════════════════════════════════════════════════════════════

/**
 * Local-time formatters. Hermes falls back to UTC for toLocaleString
 * without full ICU, so we format with explicit local accessors.
 */
function formatLocalClock(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}
function formatLocalDateTime(raw: unknown): string {
  if (typeof raw !== 'string' || raw.length === 0) return '';
  const d = new Date(raw);
  if (!Number.isFinite(d.getTime())) return '';
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const da = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${da} ${formatLocalClock(d)}`;
}

function StatusPill({ label, color }: { label: string; color: string }) {
  return (
    <View style={[styles.pill, { borderColor: color, flexShrink: 1, maxWidth: 180 }]}>
      <Text style={[styles.pillText, { color }]} numberOfLines={1}>{label}</Text>
    </View>
  );
}

function ActionBtn({ label, onPress, loading, disabled, variant = 'primary' }: {
  label: string; onPress: () => void; loading?: boolean; disabled?: boolean; variant?: 'primary' | 'secondary' | 'danger';
}) {
  const bg = variant === 'primary' ? '#d4e157' : variant === 'danger' ? '#ff6b6b' : 'transparent';
  const fg = variant === 'primary' ? '#0a0a0a' : variant === 'danger' ? '#fff' : '#aaa';
  const border = variant === 'secondary' ? 'rgba(255,255,255,0.15)' : 'transparent';
  const isDisabled = loading || disabled;
  return (
    <Pressable
      style={[styles.actionBtn, { backgroundColor: bg, borderColor: border, borderWidth: variant === 'secondary' ? 1 : 0, opacity: isDisabled ? 0.5 : 1 }]}
      onPress={onPress}
      disabled={isDisabled}>
      {loading ? <ActivityIndicator size="small" color={fg} /> : <Text style={[styles.actionBtnText, { color: fg }]}>{label}</Text>}
    </Pressable>
  );
}

function useIntegrationConfig() {
  const userId = useAuthStore((s) => s.user?.id);
  const accessToken = useAuthStore((s) => s.session?.access_token);
  return buildIntegrationConfig(userId, accessToken);
}

/**
 * Normalize a backend error string (which may be a stringified JSON
 * body, an HTTP status line, or a network message) into a single
 * user-safe sentence. Never returns raw JSON — that's the entire
 * purpose. Returns null when the error is non-actionable for a
 * normal user (e.g. upstream 404 on a not-yet-registered direct-sync
 * integration), so the caller can hide the line entirely.
 */
function friendlyDirectSyncError(
  raw: string | null,
  kind: 'whoop' | 'polar',
): string | null {
  if (!raw || raw.trim().length === 0) return null;
  // Quick test — does the body look like JSON? If yes, parse and
  // map common upstream "application not found / configured" shapes
  // to the silent / planned state.
  let parsed: any = null;
  try { parsed = JSON.parse(raw); } catch { /* not JSON */ }
  const code = parsed?.code ?? parsed?.statusCode ?? null;
  const upstreamMsg = String(parsed?.message ?? '').toLowerCase();
  // Upstream "application not found" / dev-portal app missing → not
  // actionable for the user, surface as planned/coming-soon and
  // suppress the inline error line entirely. The card's StatusPill
  // already says "Planned" for these states.
  if (code === 404 || upstreamMsg.includes('application not found') || upstreamMsg.includes('not configured')) {
    return null;
  }
  if (/timeout|timed out|network/i.test(raw)) {
    return 'Network hiccup — pull to refresh.';
  }
  if (/\b401\b|unauthorized/i.test(raw)) {
    return kind === 'whoop'
      ? 'WHOOP session expired. Tap Reconnect WHOOP.'
      : 'Polar session expired. Tap Reconnect Polar.';
  }
  if (/\b403\b/.test(raw)) {
    return 'Access denied — sign out and back in.';
  }
  if (/\b5\d{2}\b/.test(raw)) {
    return 'Direct sync is temporarily unavailable. Try again later.';
  }
  // Default: short generic — never the raw body.
  const nativeHub = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
  return kind === 'whoop'
    ? `Direct WHOOP sync is not connected yet. Use ${nativeHub} for now.`
    : `Direct Polar sync is not connected yet. Use ${nativeHub} for now.`;
}

// ═══════════════════════════════════════════════════════════════
// POLAR DIRECT
// ═══════════════════════════════════════════════════════════════

export function PolarDirectCard() {
  const cfg = useIntegrationConfig();
  const polarViaHc = useHealthStore((s) => s.polarViaHc);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!cfg) return;
    setLoading(true);
    const res = await getPolarStatus(cfg);
    setLoading(false);
    if (res.ok) setStatus(res.data);
    else setError(res.error);
  }, [cfg]);

  useEffect(() => { void refresh(); }, [refresh]);

  const handleConnect = useCallback(async () => {
    if (!cfg) return;
    setLoading(true);
    const res = await getPolarConnectUrl(cfg);
    setLoading(false);
    if (res.ok) {
      await Linking.openURL(res.data.url);
      // Poll for connection after redirect
      setTimeout(() => void refresh(), 5000);
    } else {
      setError(res.error);
    }
  }, [cfg, refresh]);

  const handleDisconnect = useCallback(async () => {
    if (!cfg) return;
    setLoading(true);
    await disconnectPolar(cfg);
    await refresh();
  }, [cfg, refresh]);

  const handleSync = useCallback(async () => {
    if (!cfg) return;
    setSyncing(true);
    await syncPolar(cfg);
    setSyncing(false);
    await refresh();
  }, [cfg, refresh]);

  const s = status?.status;
  const viaHcDetected = !!polarViaHc?.detected;
  const nativeHubName = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>Polar Direct</Text>
        {s === 'connected' && <StatusPill label="Connected" color="#4ade80" />}
        {s === 'config_missing' && <StatusPill label="Planned" color="#888" />}
        {s === 'auth_required' && <StatusPill label="Planned" color="#888" />}
        {s === 'partial' && <StatusPill label="Partial" color="#d4e157" />}
        {s === 'stale' && <StatusPill label="Stale" color="#ffa500" />}
        {s === 'disconnected' && <StatusPill label="Disconnected" color="#888" />}
        {(!s || s === 'error') && <StatusPill label={loading ? 'Loading…' : 'Planned'} color="#888" />}
      </View>

      {s !== 'connected' && (
        <Text style={[styles.bodyText, { opacity: 0.8 }]}>
          For now, Polar users can sync through {nativeHubName}. Polar Direct (AccessLink OAuth) is planned for a later release.
        </Text>
      )}

      {s === 'config_missing' && (
        <Text style={styles.bodyText}>
          Direct Polar AccessLink requires vendor setup on the backend.{'\n'}
          {viaHcDetected
            ? `Meanwhile, Polar data is arriving via ${nativeHubName} (${polarViaHc?.sourceApp ?? 'Polar Flow'}).`
            : `If you use Polar Flow, enable sharing to ${nativeHubName} in Flow settings to get data through that path now.`}
        </Text>
      )}

      {s === 'auth_required' && (
        <Text style={styles.bodyText}>
          Direct Polar AccessLink (OAuth) is planned. Use the {nativeHubName} path above in the meantime.
        </Text>
      )}

      {s === 'connected' && (
        <>
          <Text style={styles.bodyText}>
            Polar AccessLink connected.
            {status?.lastSyncAt ? ` Last sync: ${status.lastSyncAt.slice(0, 10)}.` : ' Not synced yet.'}
          </Text>
          <View style={styles.actions}>
            <ActionBtn label="Sync now" onPress={handleSync} loading={syncing} variant="secondary" />
            <ActionBtn label="Disconnect" onPress={handleDisconnect} variant="danger" />
          </View>
        </>
      )}

      {viaHcDetected && s !== 'connected' && (
        <Text style={styles.subtleNote}>
          Polar via {nativeHubName} is active ({polarViaHc?.domains.join(', ')}). Direct Polar adds richer data.
        </Text>
      )}

      {(() => {
        const friendly = friendlyDirectSyncError(error, 'polar');
        return friendly ? <Text style={styles.subtleNote}>{friendly}</Text> : null;
      })()}
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
// WHOOP DIRECT
// ═══════════════════════════════════════════════════════════════

export function WhoopDirectCard() {
  const cfg = useIntegrationConfig();
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (announce?: boolean) => {
    if (!cfg) {
      if (announce) {
        Alert.alert('WHOOP', 'Sign in first, then try WHOOP Direct again.');
      }
      return;
    }
    setLoading(true);
    const res = await getWhoopStatus(cfg);
    setLoading(false);
    if (res.ok) {
      setStatus(res.data);
      setError(null);
      if (announce) {
        // Always surface the result on explicit tap so the user sees
        // that the button worked, even when the visual state is
        // identical before/after (e.g. still config_missing).
        const d = res.data as any;
        if (d?.status === 'config_missing') {
          Alert.alert(
            'WHOOP setup required',
            'WHOOP Direct is not ready on the backend yet. Ask Aaron to finish the vendor setup, then try again.',
          );
        } else if (d?.status === 'auth_required') {
          Alert.alert('WHOOP', 'Ready to connect. Tap Connect WHOOP to start OAuth.');
        } else if (d?.status === 'connected') {
          Alert.alert('WHOOP', 'Connected. Tap Sync now to pull latest recovery / HRV / sleep.');
        } else {
          Alert.alert('WHOOP', `Status: ${d?.status ?? 'unknown'}.`);
        }
      }
    } else {
      setError(res.error);
      if (announce) Alert.alert('WHOOP status', res.error ?? 'Network error.');
    }
  }, [cfg]);

  useEffect(() => { void refresh(false); }, [refresh]);

  const handleConnect = useCallback(async () => {
    // eslint-disable-next-line no-console
    console.log('[WhoopDirect] Connect tapped', { hasCfg: !!cfg, status: status?.status });
    if (!cfg) {
      Alert.alert(
        'WHOOP',
        'Sign in first, then try WHOOP Direct again.',
      );
      return;
    }
    setLoading(true);
    const res = await getWhoopConnectUrl(cfg);
    setLoading(false);
    if (res.ok) {
      await Linking.openURL(res.data.url);
      setTimeout(() => void refresh(false), 5000);
    } else {
      setError(res.error);
      const text = res.error ?? 'Could not start WHOOP connection.';
      try {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed?.missingVars)) {
          Alert.alert(
            'WHOOP setup required',
            'WHOOP Direct is not ready on the backend yet. Ask Aaron to finish the vendor setup, then try again.',
          );
          return;
        }
      } catch { /* fall through */ }
      Alert.alert('WHOOP', text);
    }
  }, [cfg, refresh, status?.status]);

  const handleDisconnect = useCallback(async () => {
    if (!cfg) return;
    setLoading(true);
    await disconnectWhoop(cfg);
    await refresh();
  }, [cfg, refresh]);

  const [lastClientSyncAt, setLastClientSyncAt] = useState<string | null>(null);
  const handleSync = useCallback(async () => {
    if (!cfg) return;
    setSyncing(true);
    const res = await syncWhoop(cfg);
    // Record the exact client moment the sync returned, independent of
    // the backend's lastSyncAt (which reflects the latest scored cycle,
    // not the round-trip). That keeps "synced just now" honest even if
    // WHOOP hasn't scored today yet.
    if (res.ok) setLastClientSyncAt(new Date().toISOString());
    setSyncing(false);
    await refresh();
  }, [cfg, refresh]);

  const s = status?.status;

  // Match the sheet's truth: `partial` is only "awaiting today's cycle"
  // when the latest scored cycle IS today's date. When it's yesterday
  // or older AND we have missing domains, that's a real partial sync
  // the user should know about.
  const todayYmd = (() => { const d = new Date(); const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const da = String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${da}`; })();
  const latestIsToday = typeof status?.latestDayDate === 'string' && status.latestDayDate === todayYmd;
  const isAwaitingTodaysCycle = s === 'partial' && latestIsToday;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>WHOOP Direct</Text>
        {s === 'connected' && <StatusPill label="Connected" color="#4ade80" />}
        {s === 'config_missing' && <StatusPill label="Setup required" color="#888" />}
        {s === 'auth_required' && <StatusPill label="Not connected" color="#d4e157" />}
        {isAwaitingTodaysCycle && <StatusPill label="Awaiting today's cycle" color="#4ade80" />}
        {s === 'partial' && !isAwaitingTodaysCycle && <StatusPill label="Partial" color="#ffa500" />}
        {s === 'stale' && <StatusPill label="Stale — sync needed" color="#d4e157" />}
        {s === 'disconnected' && <StatusPill label="Disconnected" color="#888" />}
        {s === 'error' && <StatusPill label="Reconnect required" color="#ff6b6b" />}
        {!s && <StatusPill label={loading ? 'Loading…' : (error ? 'Coming soon' : 'Unknown')} color="#666" />}
      </View>

      {s === 'config_missing' && (
        <>
          <Text style={styles.bodyText}>
            WHOOP Direct requires vendor setup on the backend before account linking can start.
          </Text>
          {Array.isArray(status?.missingVars) && status.missingVars.length > 0 && (
            <View style={{ gap: 2, marginTop: 4 }}>
              <Text style={styles.subtleNote}>Backend setup required before WHOOP Direct can connect.</Text>
            </View>
          )}
          {Array.isArray(status?.setupInstructions) && (
            <View style={{ gap: 2, marginTop: 4 }}>
              <Text style={styles.subtleNote}>Ask Aaron to finish WHOOP vendor setup, then retry status.</Text>
            </View>
          )}
          <View style={styles.actions}>
            {/* Primary button always present so the card is obviously
                tappable even when the underlying OAuth is blocked. */}
            <ActionBtn
              label="Connect WHOOP"
              onPress={handleConnect}
              loading={loading}
            />
            <ActionBtn
              label="Retry status"
              onPress={() => void refresh(true)}
              loading={loading}
              variant="secondary"
            />
          </View>
        </>
      )}

      {s === 'auth_required' && (
        <>
          <Text style={styles.bodyText}>
            Connect your WHOOP account for direct recovery, HRV, strain, and sleep data. Until then, readiness stays provisional and uses only available hub/manual data.
          </Text>
          <View style={styles.actions}>
            <ActionBtn label="Connect WHOOP" onPress={handleConnect} loading={loading} />
          </View>
        </>
      )}

      {/* Fallback: if status hasn't loaded or returned an unknown value,
          surface a Retry button so the card is never non-interactive.
          When error is set (typically upstream 404 — direct WHOOP
          isn't registered yet), explain in plain language instead of
          leaving the user with a bare "Unknown" pill. */}
      {!s && !loading && (
        <>
          {error && (
            <Text style={[styles.bodyText, { opacity: 0.8 }]}>
              Direct WHOOP sync isn&apos;t connected yet. Use Apple Health on iOS or Health Connect on Android for now. WHOOP export upload can be added later.
            </Text>
          )}
          <View style={styles.actions}>
            <ActionBtn
              label="Retry status"
              onPress={() => void refresh()}
              loading={loading}
              variant="secondary"
            />
          </View>
        </>
      )}

      {s === 'error' && (
        <>
          <Text style={styles.bodyText}>
            WHOOP sync failed. This usually means the stored token expired and the refresh attempt was rejected — common after the offline-scope change. Reconnect to issue a fresh refresh token.
          </Text>
          {status?.reason && (
            <Text style={[styles.subtleNote, { color: '#ff6b6b' }]}>
              {status.reason}
            </Text>
          )}
          <View style={styles.actions}>
            <ActionBtn label="Reconnect WHOOP" onPress={handleConnect} loading={loading} />
            <ActionBtn label="Disconnect" onPress={handleDisconnect} variant="danger" />
          </View>
        </>
      )}

      {(s === 'connected' || s === 'partial') && (
        <>
          <Text style={styles.bodyText}>
            WHOOP connected{isAwaitingTodaysCycle ? ' — awaiting today\u2019s scored cycle' : s === 'partial' ? ' — partial sync' : ''}.
          </Text>
          {lastClientSyncAt && (
            <Text style={styles.subtleNote}>
              Synced just now · {formatLocalClock(new Date(lastClientSyncAt))} local
            </Text>
          )}
          {typeof status?.latestDayDate === 'string' && status.latestDayDate.length > 0 && (
            <Text style={styles.subtleNote}>
              Latest WHOOP day: {status.latestDayDate}
            </Text>
          )}
          {typeof status?.lastSyncAt === 'string' && status.lastSyncAt.length >= 16 && (
            <Text style={styles.subtleNote}>
              Backend lastSyncAt: {formatLocalDateTime(status.lastSyncAt)} local
            </Text>
          )}
          {Array.isArray(status?.domainsAvailable) && status.domainsAvailable.length > 0 && (
            <Text style={styles.subtleNote}>
              Present: {status.domainsAvailable.join(', ')}.
            </Text>
          )}
          {Array.isArray(status?.missingDomains) && status.missingDomains.length > 0 && !isAwaitingTodaysCycle && (
            <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
              Missing: {status.missingDomains.join(', ')}. WHOOP hasn{"'"}t scored those fields yet — tap Sync now after your next WHOOP sync, or leave it; it fills in after the next cycle completes.
            </Text>
          )}
          {isAwaitingTodaysCycle && (
            <Text style={[styles.subtleNote, { color: '#4ade80' }]}>
              Today{"'"}s cycle is still in progress — WHOOP will score it after your next sleep. Recovery and strain appear then.
            </Text>
          )}
          {status?.readinessStatus === 'available' && (
            <Text style={[styles.subtleNote, { color: '#4ade80' }]}>
              Direct WHOOP fields present — recovery, HRV, strain, and sleep are available for app-owned readiness.
            </Text>
          )}
          {status?.readinessStatus === 'partial' && (
            <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
              Readiness unavailable until recovery + HRV + strain + sleep are all present.
            </Text>
          )}
          {typeof status?.historyDaysAvailable === 'number' && (
            <Text style={styles.subtleNote}>
              WHOOP history: {status.historyDaysAvailable} day{status.historyDaysAvailable === 1 ? '' : 's'} ingested.
            </Text>
          )}
          <View style={styles.actions}>
            <ActionBtn label="Sync now" onPress={handleSync} loading={syncing} />
            <ActionBtn
              label="Backfill 1y"
              onPress={async () => {
                if (!cfg) return;
                setSyncing(true);
                const res = await backfillWhoop(cfg, 365);
                setSyncing(false);
                if (res.ok) setLastClientSyncAt(new Date().toISOString());
                await refresh();
                Alert.alert(
                  'WHOOP backfill',
                  res.ok
                    ? 'Deep backfill requested. The backend will ingest as much authorized history as WHOOP returns.'
                    : res.error ?? 'Backfill failed.',
                );
              }}
              loading={syncing}
              variant="secondary"
            />
            <ActionBtn label="Disconnect" onPress={handleDisconnect} variant="danger" />
          </View>
        </>
      )}

      {(() => {
        const friendly = friendlyDirectSyncError(error, 'whoop');
        return friendly ? <Text style={styles.subtleNote}>{friendly}</Text> : null;
      })()}
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
// CONCEPT2 + CRONOMETER — INTENTIONALLY NEUTRALIZED
// ═══════════════════════════════════════════════════════════════
// These exports previously rendered "Concept2" and "Cronometer"
// status cards. Both integrations are out of the active product
// path: conditioning/machine capture goes through FTMS/BLE in
// Build 9+, nutrition goes through Apple Health / manual /
// barcode / AI photo. The exports stay so stale bundles don't
// crash on undefined-component, but render nothing.

export function Concept2Card(): null { return null; }
export function CronometerCard(): null { return null; }

// ═══════════════════════════════════════════════════════════════
// HEALTH CONNECT PROVENANCE
// ═══════════════════════════════════════════════════════════════

export function HealthConnectProvenanceCard() {
  const polarViaHc = useHealthStore((s) => s.polarViaHc);
  const samsungViaHc = useHealthStore((s) => s.samsungHealthViaHc);

  if (Platform.OS !== 'android') return null;

  // Only render when there's interesting provenance to show
  if (!polarViaHc?.detected && !samsungViaHc?.detected) return null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>Health Connect Sources</Text>
        <StatusPill label="Provenance detected" color="#a8d96a" />
      </View>
      {samsungViaHc?.detected && (
        <Text style={styles.bodyText}>
          Samsung Health is writing to Health Connect.
          Domains: {samsungViaHc.domains.join(', ')}.
          {samsungViaHc.daysWithRecords > 0 ? ` ${samsungViaHc.daysWithRecords} days with records.` : ''}
        </Text>
      )}
      {polarViaHc?.detected && (
        <Text style={styles.bodyText}>
          {polarViaHc.sourceApp ?? 'Polar Flow'} is writing to Health Connect.
          Domains: {polarViaHc.domains.join(', ')}.
          {polarViaHc.daysWithRecords > 0 ? ` ${polarViaHc.daysWithRecords} days with records.` : ''}
        </Text>
      )}
      <Text style={styles.subtleNote}>
        Provenance tracking also detects ErgData/Concept2, Garmin Connect, and other apps writing to Health Connect.
      </Text>
    </View>
  );
}

export function AppleHealthCard() {
  const permissions = useHealthStore((s) => s.permissions);
  const syncing = useHealthStore((s) => s.syncing);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const requestPerms = useHealthStore((s) => s.requestPermissions);
  const days = useHealthStore((s) => s.days);
  const diag = useHealthStore((s) => s.lastSyncDiagnostics);
  const storeError = useHealthStore((s) => s.error);

  if (Platform.OS !== 'ios') return null;

  // Prefer the live native probe over cached permissions.available so
  // the card never stalls on "Not connected" when HealthKit is ready.
  let nativeProbe: boolean | null = null;
  let nativeAuthErr: string | null = null;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getHealthKitNativeDebug } = require('../services/health.ios');
    const d = getHealthKitNativeDebug();
    nativeProbe = d.isHealthDataAvailableResult ?? null;
    nativeAuthErr = d.lastAuthRequestError ?? null;
  } catch {
    nativeProbe = null;
  }
  const isAvailable = nativeProbe ?? !!permissions?.available;
  const anyAuthorized =
    !!permissions &&
    !!permissions.permissions &&
    Object.values(permissions.permissions).some((p) => p === 'authorized');
  const recordCounts = diag?.recordCounts ?? null;
  const recordTotal = recordCounts
    ? Object.values(recordCounts).reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0)
    : 0;
  // Apple-Health-only record signal. `days` can include merged manual
  // training sessions that inflate the count even when HealthKit
  // returned zero samples, so we key "has records" off the diagnostics
  // record counts only.
  const hasAppleHealthRecords = recordTotal > 0;
  const hasSynced = !!lastSyncAt;
  const presentMetrics = recordCounts
    ? (Object.entries(recordCounts) as [string, number][])
        .filter(([, v]) => v > 0)
        .map(([k]) => k)
    : [];
  // Records are the ultimate proof of permission — a successful sync
  // with samples means iOS granted at least those metrics, regardless
  // of what the cached `permissions.permissions` says. Without this
  // decoupling, a clean sync can render as "Ready to connect" because
  // requestPermissions() returns `not_determined` when the canary
  // read is 0 but the user later granted in iOS Settings.
  const isConnectedFull = hasSynced && hasAppleHealthRecords && presentMetrics.length >= 3;
  const isPartial =
    hasSynced && hasAppleHealthRecords && presentMetrics.length >= 1 && presentMetrics.length < 3;
  const isConnectedNoData = hasSynced && !hasAppleHealthRecords;
  const isPermissionReadyToSync = !hasSynced && anyAuthorized;
  const errorReason = storeError ?? nativeAuthErr ?? null;

  // Order matters: successful-sync signals win over any stale
  // permissions state. Error only wins if we haven't successfully
  // synced — an old `storeError` shouldn't override a clean sync.
  const pillLabel = isConnectedFull
    ? 'Connected'
    : isPartial
      ? 'Partial'
      : isConnectedNoData
        ? 'Connected — no recent data'
        : errorReason
          ? 'Error'
          : isPermissionReadyToSync
            ? 'Permission granted — sync needed'
            : isAvailable
              ? 'Ready to connect'
              : 'Unavailable';
  const pillColor = isConnectedFull
    ? '#4ade80'
    : isPartial
      ? '#ffa500'
      : isConnectedNoData
        ? '#d4a157'
        : errorReason
          ? '#ff6b6b'
          : isPermissionReadyToSync
            ? '#d4e157'
            : isAvailable
              ? '#d4e157'
              : '#888';

  const handleGrant = useCallback(async () => {
    // eslint-disable-next-line no-console
    console.log('[AppleHealthCard] Grant tapped', { isAvailable });
    const perms = await requestPerms();
    if (!perms) {
      Alert.alert(
        'Apple Health',
        "iOS didn't report any granted metrics. Open iOS Settings → Health → Data Access & Devices → Lauburu and enable the metrics you want to share, then tap Grant again.",
      );
    }
  }, [isAvailable, requestPerms]);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>Apple Health / HealthKit</Text>
        <StatusPill label={pillLabel} color={pillColor} />
      </View>

      {isConnectedFull && (
        <>
          <Text style={styles.bodyText}>
            Apple Health is synced. Last sync: {lastSyncAt!.slice(0, 16).replace('T', ' ')}.
            {' '}{days.length} day{days.length === 1 ? '' : 's'} of data, {recordTotal} samples.
          </Text>
          {presentMetrics.length > 0 && (
            <Text style={styles.subtleNote}>
              Present: {presentMetrics.join(', ')}.
            </Text>
          )}
        </>
      )}

      {isPartial && (
        <Text style={styles.bodyText}>
          Connected, partial data. Present: {presentMetrics.join(', ') || '(none)'}.
          Grant more metrics in iOS Settings → Health → Data Access & Devices → Lauburu to unlock full context.
        </Text>
      )}

      {isConnectedNoData && (
        <Text style={styles.bodyText}>
          Connected — no recent data. Apple Health didn't return any samples for the last 30 days.
          Open iOS Settings → Health → Data Access & Devices → Lauburu and enable the metrics you want to share, then tap Sync Apple Health again.
        </Text>
      )}

      {!isConnectedFull && !isPartial && !isConnectedNoData && errorReason && (
        <Text style={[styles.bodyText, { color: '#ff6b6b' }]}>
          {errorReason}
        </Text>
      )}

      {isPermissionReadyToSync && (
        <>
          <Text style={styles.bodyText}>
            Permission granted. Tap Sync Apple Health on the Health tab to start loading data.
          </Text>
          {syncing && <Text style={styles.subtleNote}>Syncing…</Text>}
        </>
      )}

      {!isConnectedFull && !isPartial && !isConnectedNoData && !isPermissionReadyToSync && !errorReason && (
        <>
          <Text style={styles.bodyText}>
            Apple Health / HealthKit is the native data path on iPhone. Grant access to sync sleep, workouts, steps, heart rate, and training history.
          </Text>
          {!isAvailable && (
            <Text style={styles.subtleNote}>
              iOS reports HealthKit as unavailable on this device. Tapping Grant will still attempt a permission request — the exact native error is captured in the Health actions diagnostics.
            </Text>
          )}
          <View style={styles.actions}>
            <ActionBtn label="Grant Apple Health access" onPress={handleGrant} />
          </View>
        </>
      )}

      <Text style={styles.subtleNote}>
        Apple Health / HealthKit hub data is separate from true WHOOP Direct or Polar Direct.
      </Text>
    </View>
  );
}

export function SamsungHealthCard() {
  const samsungViaHc = useHealthStore((s) => s.samsungHealthViaHc);
  const viaHcDetected = !!samsungViaHc?.detected;

  // Primary status label
  const primaryLabel = viaHcDetected ? 'Via Health Connect' : 'Use Health Connect';
  const primaryColor = viaHcDetected ? '#4ade80' : '#888';

  if (Platform.OS !== 'android') return null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>Samsung Health</Text>
        <StatusPill label={primaryLabel} color={primaryColor} />
      </View>

      {viaHcDetected && (
        <Text style={styles.bodyText}>
          Samsung Health via Health Connect: {samsungViaHc!.domains.join(', ')}.
          {samsungViaHc!.daysWithRecords > 0 ? ` ${samsungViaHc!.daysWithRecords} days.` : ''}
        </Text>
      )}

      {!viaHcDetected && (
        <Text style={styles.subtleNote}>
          If you use Samsung Health or Galaxy Watch, enable Samsung Health → Health Connect sharing, then grant Health Connect permissions here.
        </Text>
      )}

      <Text style={styles.subtleNote}>
        Samsung Health data reaches Lauburu through Health Connect.
      </Text>
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
// MACHINE CAPTURE (BLE / FTMS)
// ═══════════════════════════════════════════════════════════════

import {
  getBleMachineState,
  scanBleMachines,
  connectBleMachine,
  disconnectBleMachine,
  startBleSession,
  markSessionStart,
  getLiveStreamStatus,
  deviceRank,
  type BleMachineState,
  type LiveBleSessionHandle,
  type FtmsLiveSample,
} from '../services/ble-connect';

const HR_SERVICE_UUID_LC = '0000180d-0000-1000-8000-00805f9b34fb';
const FTMS_SERVICE_UUID_LC = '00001826-0000-1000-8000-00805f9b34fb';
const CPS_SERVICE_UUID_LC = '00001818-0000-1000-8000-00805f9b34fb';
const CSC_SERVICE_UUID_LC = '00001816-0000-1000-8000-00805f9b34fb';

function isBluetoothCaptureUiEnabled(): boolean {
  return false;
}

export function FTMSMachineCard() {
  if (!isBluetoothCaptureUiEnabled()) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Bluetooth heart-rate sensors planned</Text>
        <Text style={styles.bodyText}>
          Manual session logging is the supported path today. Bluetooth
          heart-rate straps and machine capture will stay hidden until direct
          capture is ready for normal testing.
        </Text>
        <Text style={styles.subtleNote}>
          Polar may appear through Apple Health or Health Connect. Do not treat
          hub data as Polar Direct or live Bluetooth data.
        </Text>
      </View>
    );
  }

  return <FTMSMachineCardLive />;
}

function FTMSMachineCardLive() {
  const [state, setState] = useState<BleMachineState>(() => getBleMachineState());
  const [scanning, setScanning] = useState(false);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [liveSession, setLiveSession] = useState<LiveBleSessionHandle | null>(null);
  const [liveHr, setLiveHr] = useState<number | null>(null);
  const [livePowerW, setLivePowerW] = useState<number | null>(null);
  const [liveEnergyKj, setLiveEnergyKj] = useState<number | null>(null);
  const [liveCadenceRpm, setLiveCadenceRpm] = useState<number | null>(null);
  const [liveDistanceM, setLiveDistanceM] = useState<number | null>(null);
  const [liveElapsedS, setLiveElapsedS] = useState<number | null>(null);
  const [liveHealth, setLiveHealth] = useState(() => getLiveStreamStatus());

  const refresh = useCallback(() => setState(getBleMachineState()), []);

  // Poll live-stream health while a session is active. The poll is
  // cheap (single function call) and runs only while liveSession is
  // set. It detects the WHOOP-proprietary-profile case (connected,
  // subscription attempted, but no samples ever arrived).
  useEffect(() => {
    if (!liveSession) return;
    const t = setInterval(() => setLiveHealth(getLiveStreamStatus()), 1000);
    return () => clearInterval(t);
  }, [liveSession]);

  // Clean up the BLE subscriptions when this card unmounts mid-session.
  useEffect(() => {
    return () => {
      try { liveSession?.stop(); } catch { /* ignore */ }
    };
  }, [liveSession]);

  const startLive = useCallback(() => {
    try {
      const handle = startBleSession();
      if (!handle.live) {
        setLiveSession(null);
        return;
      }
      handle.onHr((bpm) => setLiveHr(bpm));
      handle.onFtms((s: FtmsLiveSample) => {
        if (typeof s.instantaneousPowerW === 'number') setLivePowerW(s.instantaneousPowerW);
        if (typeof s.heartRateBpm === 'number') setLiveHr(s.heartRateBpm);
        if (typeof s.energyKj === 'number') setLiveEnergyKj(s.energyKj);
        if (typeof s.instantaneousCadenceRpm === 'number') setLiveCadenceRpm(s.instantaneousCadenceRpm);
        if (typeof s.totalDistanceM === 'number') setLiveDistanceM(s.totalDistanceM);
        if (typeof s.elapsedTimeS === 'number') setLiveElapsedS(s.elapsedTimeS);
      });
      // Start the session ring so the Train save path can auto-fill
      // avgHr/peakHr/avgWatts when the user saves a HIIT session
      // after using live BLE capture.
      markSessionStart();
      setLiveSession(handle);
    } catch { /* non-fatal */ }
  }, []);

  const stopLive = useCallback(() => {
    try { liveSession?.stop(); } catch { /* ignore */ }
    setLiveSession(null);
    setLiveHr(null);
    setLivePowerW(null);
    setLiveEnergyKj(null);
    // Intentionally NOT calling clearSession here — the session ring
    // remains intact so a subsequent Save in Train reads the full
    // session's samples. Train save is the one that calls clearSession.
    refresh();
  }, [liveSession, refresh]);

  const pillLabel = (() => {
    switch (state.status) {
      case 'bluetooth_unavailable': return 'Not available on this build';
      case 'initializing':          return 'Initialising Bluetooth…';
      case 'idle':                  return 'Ready to scan';
      case 'permission_required':   return 'Permission required';
      case 'scanning':              return 'Scanning…';
      case 'device_found':          return 'Device found';
      case 'connected':             return liveHealth.hasEverReceivedSample ? 'Connected' : 'Connected · waiting';
      case 'receiving_data':        return 'Live data';
      case 'partial_manual_fallback': return 'Manual fallback';
      case 'error':                 return 'Error';
      default:                      return 'Manual only';
    }
  })();
  const pillColor =
    state.status === 'receiving_data' ? '#4ade80'
    : state.status === 'connected' ? (liveHealth.hasEverReceivedSample ? '#4ade80' : '#d4e157')
    : state.status === 'scanning' || state.status === 'device_found' ? '#d4e157'
    : state.status === 'initializing' ? '#d4e157'
    : state.status === 'partial_manual_fallback' ? '#a8b84a'
    : state.status === 'error' ? '#ff6b6b'
    : '#888';

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardTitle}>Bluetooth machine + HR strap</Text>
        <StatusPill label={pillLabel} color={pillColor} />
      </View>

      <Text style={styles.bodyText}>
        Direct Bluetooth capture from FTMS bikes/rowers/ski ergs, Concept2 PM5, and any standard BLE heart-rate strap or armband (Polar H10/H9/Verity Sense, Wahoo TICKR FIT, Scosche Rhythm+, Garmin HRM straps). Manual session logging stays available regardless of device state.
      </Text>
      <Text style={[styles.bodyText, { opacity: 0.75, marginTop: 4 }]}>
        Use a heart-rate strap if you don&apos;t have WHOOP or Polar Flow — you&apos;ll get live session HR + average/max HR for trends and training-load context. A strap alone won&apos;t capture sleep or all-day recovery data; pair it with Apple Health for those.
      </Text>

      {state.status === 'bluetooth_unavailable' && !state.moduleLinked && (
        <Text style={styles.subtleNote}>
          Bluetooth machine capture needs the native BLE module compiled into the app. Install the latest TestFlight build — Build 11 registers the BLE plugin. Manual session logging works in the meantime; saves flow into Recent Days + Coach immediately.
        </Text>
      )}

      {state.status === 'permission_required' && (
        <Text style={[styles.subtleNote, { color: '#d4e157' }]}>
          Grant Bluetooth permission in iOS Settings → Lauburu to enable device discovery.
        </Text>
      )}

      {state.moduleLinked && (
        <View style={styles.actions}>
          {/* Two independent slots: HR source + machine source. Each can
              be bound / disconnected independently. The scan action stays
              visible until both slots are full so users can pair the
              second role without dropping the first. */}
          {state.hrDevice && (
            <View style={styles.slotRow}>
              <Text style={styles.slotLabel}>HR: {state.hrDevice.name}</Text>
              <Pressable
                onPress={() => { disconnectBleMachine('hr'); refresh(); }}
                hitSlop={6}
              >
                <Text style={styles.slotDisconnect}>Disconnect</Text>
              </Pressable>
            </View>
          )}
          {state.machineDevice && (
            <View style={styles.slotRow}>
              <Text style={styles.slotLabel}>Machine: {state.machineDevice.name}</Text>
              <Pressable
                onPress={() => { stopLive(); disconnectBleMachine('machine'); refresh(); }}
                hitSlop={6}
              >
                <Text style={styles.slotDisconnect}>Disconnect</Text>
              </Pressable>
            </View>
          )}
          {(state.hrDevice || state.machineDevice) && (
            !liveSession ? (
              <ActionBtn label="Start live read" onPress={startLive} />
            ) : (
              <ActionBtn label="Stop live read" onPress={stopLive} variant="secondary" />
            )
          )}
          {!(state.hrDevice && state.machineDevice) && !liveSession && (
            <ActionBtn
              label={
                state.status === 'initializing' ? 'Initialising Bluetooth…'
                : scanning ? 'Scanning…'
                : (state.hrDevice || state.machineDevice) ? 'Scan for more devices'
                : 'Scan for devices'
              }
              onPress={async () => {
                setScanning(true);
                await scanBleMachines();
                setScanning(false);
                refresh();
              }}
              loading={scanning || state.status === 'initializing'}
              disabled={state.status === 'initializing'}
            />
          )}
          {state.discoveredDevices && state.discoveredDevices.length > 0 && !liveSession && (() => {
            // Sort so FTMS bike/rower/skierg + PM5 + standard HR straps
            // float to the top; WHOOP (proprietary BLE profile we
            // cannot read) is ranked last and clearly labeled so it
            // never hijacks the live capture flow.
            const boundIds = new Set<string>();
            if (state.hrDevice) boundIds.add(state.hrDevice.id);
            if (state.machineDevice) boundIds.add(state.machineDevice.id);
            const sorted = [...state.discoveredDevices]
              .filter((d) => !boundIds.has(d.id))
              .sort((a, b) => deviceRank(a) - deviceRank(b));
            return (
              <>
                {sorted.slice(0, 4).map((d) => {
                  const isConnectingThis = connectingId === d.id;
                  const isWhoop = d.kind === 'whoop_proprietary';
                  const baseLabel = d.name || 'device';
                  const suffix = d.kind === 'ftms_bike' ? ' · FTMS bike'
                    : d.kind === 'ftms_rower' ? ' · FTMS rower'
                    : d.kind === 'ftms_skierg' ? ' · FTMS ski'
                    : d.kind === 'pm5' ? ' · PM5'
                    : d.kind === 'hr_only' ? ' · HR strap'
                    : isWhoop ? ' · proprietary, not recommended'
                    : '';
                  const label = isConnectingThis
                    ? `Connecting ${baseLabel}…`
                    : `Connect ${baseLabel}${suffix}`;
                  return (
                    <ActionBtn
                      key={d.id}
                      label={label}
                      onPress={async () => {
                        if (connectingId) return;
                        if (isWhoop) {
                          Alert.alert(
                            'WHOOP not supported for live Train capture',
                            'WHOOP uses a proprietary Bluetooth profile — it does not expose heart rate over standard BLE. Use a chest strap (Polar / Wahoo / Garmin) or pair the FTMS bike for live readings. WHOOP Direct in the Health tab still feeds recovery/HRV/sleep via the WHOOP API.',
                          );
                          return;
                        }
                        setConnectingId(d.id);
                        try {
                          await connectBleMachine(d.id);
                        } finally {
                          setConnectingId(null);
                          refresh();
                        }
                      }}
                      loading={isConnectingThis}
                      disabled={(connectingId != null && !isConnectingThis) || (isWhoop && !isConnectingThis)}
                      variant="secondary"
                    />
                  );
                })}
              </>
            );
          })()}
        </View>
      )}

      {liveSession && (() => {
        const secsSinceStart = liveHealth.secondsSinceStart ?? 0;
        const receiving = liveHealth.hasEverReceivedSample;
        const services = liveHealth.servicesOnDevice;
        const advertisesHr = services.some((s) => s === HR_SERVICE_UUID_LC);
        const advertisesFtms = services.some((s) => s === FTMS_SERVICE_UUID_LC);
        const advertisesCps = services.some((s) => s === CPS_SERVICE_UUID_LC);
        const advertisesCsc = services.some((s) => s === CSC_SERVICE_UUID_LC);
        const advertisesAnySupported = advertisesHr || advertisesFtms || advertisesCps || advertisesCsc;
        const waitedEnough = secsSinceStart >= 8;
        const longWait = secsSinceStart >= 20;
        const vendorFrames = (liveHealth as any).vendorFrames ?? [];
        const vendorChars = (liveHealth as any).vendorCharsOnDevice ?? [];
        const ftmsChars = (liveHealth as any).ftmsCharsOnDevice ?? [];
        const vendorCapturedFrame = vendorFrames.length > 0;
        // "vendor data not supported" = FTMS/HR absent but we've seen
        // some proprietary notifications during the session. We can't
        // decode these without vendor docs, so we log them and tell
        // the user so they can fall back to manual save.
        const vendorUnsupported = !advertisesFtms && !advertisesHr && vendorCapturedFrame;
        const deviceName = state.connectedDevice?.name ?? 'device';
        const isWhoopLike = /whoop/i.test(deviceName);
        // Proprietary-profile diagnosis:
        //   - device advertises NEITHER HR nor FTMS → we cannot read it
        //   - device is named WHOOP-something → WHOOP uses proprietary BLE
        //   - waited > 8s with no sample and no expected services → warn
        const proprietaryProbable = services.length > 0 && !advertisesAnySupported;
        return (
          <>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12, paddingVertical: 8 }}>
              <Text style={{ color: receiving ? '#4ade80' : '#888', fontSize: 14, fontWeight: '700' }}>
                {liveHr != null ? `♥ ${liveHr} bpm` : (waitedEnough ? '♥ waiting…' : '♥ —')}
              </Text>
              {livePowerW != null && (
                <Text style={{ color: '#d4e157', fontSize: 14, fontWeight: '700' }}>
                  ⚡ {livePowerW} W
                </Text>
              )}
              {liveCadenceRpm != null && (
                <Text style={{ color: '#d4e157', fontSize: 13, fontWeight: '600' }}>
                  ↻ {Math.round(liveCadenceRpm)} rpm
                </Text>
              )}
              {liveElapsedS != null && (
                <Text style={{ color: '#888', fontSize: 12 }}>
                  {Math.floor(liveElapsedS / 60)}:{String(liveElapsedS % 60).padStart(2, '0')}
                </Text>
              )}
              {liveDistanceM != null && liveDistanceM > 0 && (
                <Text style={{ color: '#888', fontSize: 12 }}>
                  {(liveDistanceM / 1000).toFixed(2)} km
                </Text>
              )}
              {liveEnergyKj != null && (
                <Text style={{ color: '#888', fontSize: 12 }}>
                  {liveEnergyKj} kJ
                </Text>
              )}
            </View>
            {!receiving && waitedEnough && isWhoopLike && (
              <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
                {`Connected to WHOOP but it uses a proprietary Bluetooth profile — live HR is not available over standard BLE. Tap Disconnect, then pair a chest strap or the FTMS bike instead. WHOOP Direct in Health still pulls recovery/HRV/sleep via the WHOOP API.`}
              </Text>
            )}
            {!receiving && waitedEnough && !isWhoopLike && proprietaryProbable && (
              <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
                {`Connected, but ${deviceName} does not expose any supported metric stream (Heart Rate 0x180D, FTMS 0x1826, Cycling Power 0x1818, or Cycling Speed/Cadence 0x1816). You can still save the manual session.`}
              </Text>
            )}
            {!receiving && longWait && !isWhoopLike && advertisesAnySupported && (
              <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
                {`Connected to ${deviceName}, but no samples after ${Math.round(secsSinceStart)}s. The bike advertises ${[advertisesFtms ? 'FTMS' : null, advertisesCps ? 'CPS' : null, advertisesCsc ? 'CSC' : null, advertisesHr ? 'HR' : null].filter(Boolean).join('/')} but isn't broadcasting yet. Pedal to wake the data stream — or save the manual session.`}
              </Text>
            )}
            {!receiving && waitedEnough && !longWait && !isWhoopLike && !proprietaryProbable && (advertisesFtms || advertisesCps) && (
              <Text style={[styles.subtleNote, { color: '#d4e157' }]}>
                {`Connected to ${deviceName}. Awaiting bike notifications — start pedaling to wake the data stream.`}
              </Text>
            )}
            {!receiving && waitedEnough && !longWait && !isWhoopLike && !proprietaryProbable && advertisesHr && !advertisesFtms && !advertisesCps && (
              <Text style={[styles.subtleNote, { color: '#d4e157' }]}>
                {`Connected to ${deviceName}. Awaiting HR notifications — touch the electrodes or strap to skin to wake it.`}
              </Text>
            )}
            {!receiving && longWait && advertisesFtms && vendorCapturedFrame && (
              <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
                {`${deviceName}: FTMS silent but vendor data stream detected (${vendorFrames.length} frame${vendorFrames.length === 1 ? '' : 's'}). This firmware may use a proprietary layout. Save the manual session; open the debug log below to share frames for decode.`}
              </Text>
            )}
            {vendorUnsupported && (
              <Text style={[styles.subtleNote, { color: '#ffa500' }]}>
                {`Connected · vendor-specific data not supported. Logging ${vendorFrames.length} raw frame${vendorFrames.length === 1 ? '' : 's'} for future decode. Save the manual session.`}
              </Text>
            )}
            {(vendorChars.length > 0 || vendorFrames.length > 0) && (
              <View style={{ marginTop: 8, padding: 10, borderRadius: 8, backgroundColor: 'rgba(255,255,255,0.04)', gap: 4 }}>
                <Text style={[styles.subtleNote, { color: '#d4e157', fontWeight: '700' }]}>
                  Debug · vendor notify chars
                </Text>
                {vendorChars.slice(0, 6).map((vc: { serviceUuid: string; charUuid: string }, i: number) => (
                  <Text key={`vc-${i}`} selectable style={[styles.subtleNote, { fontSize: 10, opacity: 0.7 }]}>
                    {vc.serviceUuid.slice(0, 8)}…/{vc.charUuid.slice(0, 8)}…
                  </Text>
                ))}
                {ftmsChars.length > 0 && (
                  <Text selectable style={[styles.subtleNote, { fontSize: 10, opacity: 0.7 }]}>
                    FTMS chars: {ftmsChars.map((c: string) => c.slice(4, 8)).join(', ')}
                  </Text>
                )}
                {vendorFrames.length > 0 && (
                  <Text style={[styles.subtleNote, { fontSize: 10, opacity: 0.6 }]}>
                    Last frame ({vendorFrames[vendorFrames.length - 1].byteLen} B): {vendorFrames[vendorFrames.length - 1].hex.slice(0, 64)}{vendorFrames[vendorFrames.length - 1].hex.length > 64 ? '…' : ''}
                  </Text>
                )}
                <Text style={[styles.subtleNote, { fontSize: 10, opacity: 0.45, fontStyle: 'italic' }]}>
                  Long-press to copy. Share frames if live metrics don't arrive — they'll unlock Rogue/vendor decode.
                </Text>
              </View>
            )}
          </>
        );
      })()}

      {state.lastError && state.status !== 'initializing' && (
        <Text style={[styles.subtleNote, { color: '#ff6b6b' }]}>
          {state.lastError}
        </Text>
      )}

      <Text style={styles.subtleNote}>
        Supported: HR strap (0x180D), FTMS bike (0x1826) Indoor Bike Data + Cross Trainer + Rower + Treadmill, Cycling Power (0x1818) instantaneous power, Cycling Speed/Cadence (0x1816), Concept2 PM5 (FTMS half), Echelon/Rogue Echo proprietary. PM5 proprietary pace/stroke and CSC cadence delta-tracking are follow-ups.
      </Text>
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════

const styles = StyleSheet.create({
  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'nowrap',
  },
  cardTitle: { fontSize: 16, fontWeight: '600', flexShrink: 1 },
  bodyText: { fontSize: 13, opacity: 0.75, lineHeight: 18 },
  subtleNote: { fontSize: 12, opacity: 0.5, lineHeight: 17 },
  errorText: { fontSize: 12, color: '#ff6b6b' },
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    borderWidth: 1,
  },
  pillText: { fontSize: 11, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 8, marginTop: 6, flexWrap: 'wrap' },
  actionBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center',
    minWidth: 100,
  },
  actionBtnText: { fontSize: 13, fontWeight: '700' },
  slotRow: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(74,222,128,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(74,222,128,0.25)',
  },
  slotLabel: { fontSize: 12, color: '#4ade80', fontWeight: '700', flex: 1 },
  slotDisconnect: { fontSize: 11, color: '#ff6b6b', fontWeight: '700' },
});
