/**
 * HealthActionsPanel — top-of-screen action panel.
 *
 * Structure: class-based inner error boundary wraps <Body /> so any
 * uncaught render crash surfaces inline with the message + stack.
 * Body renders in labeled sections, each wrapped in `<SafeSection>`,
 * so a render crash in one section only kills that section and tells
 * us exactly which one via a visible red card with its own error text.
 *
 * Goal: if the panel still says "undefined is not a function" after
 * this patch, we will now see *which* labeled section is the culprit
 * ("identity", "whoop-label", "grid", etc.) on device without needing
 * a debug build.
 */
import { Component, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  ActivityIndicator,
  Alert,
  AppState,
  Linking,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  TextInput,
  View as RNView,
} from 'react-native';
import * as Application from 'expo-application';
import * as Updates from 'expo-updates';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../store/auth-store';
import { useHealthStore } from '../store/health-store';
import { useTierStore } from '../store/tier-store';
import { useWhoopStore } from '../store/whoop-store';
import * as IntegrationsClient from '../services/integrations-client';
import { getWhoopCsvStatus, uploadWhoopCsv, uploadWhoopZip, clearWhoopCsv } from '../services/integrations-client';
import { readStoredJson, writeStoredJson } from '../store/secure-storage';
import { SafeErrorBoundary } from './SafeErrorBoundary';
import { HealthConnectAvailabilityHint } from './HealthConnectAvailabilityHint';
import { PolarDirectCard } from './IntegrationCards';
import { parsePolarExport, type PolarSession } from '../../../../packages/shared/src/backend/services/polar/parse-polar-export';

const WHOOP_CSV_CACHE_KEY = 'whoop_csv_imported_v1';
const WHOOP_UPLOAD_TRACE_KEY = 'whoop_upload_trace_v1';

/**
 * Native iOS document picker has been crashing the app on the current
 * EAS build (expo-document-picker missing from `app.json` plugins[],
 * so its config-plugin Info.plist + iCloud-Documents entitlement step
 * never ran at prebuild — native presentation crashes the bridge
 * before any JS try/catch can intercept). Until the next native EAS
 * build re-enables it, the picker is gated entirely behind this flag.
 *
 * Default: OFF. To re-enable in a verified native build, set
 *   EXPO_PUBLIC_ENABLE_WHOOP_FILE_PICKER=1
 * in apps/mobile/.env.production and ship a new native build.
 */
const ENABLE_WHOOP_FILE_PICKER = process.env.EXPO_PUBLIC_ENABLE_WHOOP_FILE_PICKER === '1';

type WhoopCsvCache = { imported: boolean; totalRowsIngested?: number; updatedAt: string };
type WhoopUploadTrace = { at: string; step: string; detail?: string };

const HEALTH_CONNECT_AUDIT_FIELDS = [
  ['restingHr', 'resting_heart_rate'],
  ['hrv', 'hrv'],
  ['steps', 'steps'],
  ['activeCal', 'active_calories'],
  ['heartRate', 'heart_rate_samples'],
  ['workouts', 'workouts'],
  ['sleep', 'sleep'],
] as const;

function buildHealthConnectSyncAuditSnapshot() {
  const store: any = useHealthStore.getState();
  const diag = store?.lastSyncDiagnostics ?? null;
  const counts = diag?.recordCounts ?? {};
  const availableFields: string[] = [];
  const missingFields: string[] = [];
  let recordCountTotal = 0;

  for (const [key, label] of HEALTH_CONNECT_AUDIT_FIELDS) {
    const value = counts?.[key];
    const n = typeof value === 'number' && Number.isFinite(value) ? value : 0;
    recordCountTotal += n;
    if (n > 0) availableFields.push(label);
    else missingFields.push(label);
  }

  const error = typeof store?.error === 'string' && store.error.trim().length > 0
    ? store.error.trim()
    : null;

  return {
    error,
    normalizedDays: typeof diag?.normalizedDays === 'number' ? diag.normalizedDays : null,
    recordCountTotal,
    availableFields,
    missingFields,
  };
}

function addHealthConnectAuditEvent(input: {
  eventType: 'sync_started' | 'sync_succeeded' | 'sync_failed' | 'missing_metrics';
  severity: 'info' | 'warning' | 'error';
  userVisibleMessage?: string;
  developerMessage?: string | null;
}) {
  try {
    const snap = buildHealthConnectSyncAuditSnapshot();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const aud = require('../store/audit-event-store');
    aud?.useAuditEventStore?.getState?.()?.add?.({
      platform: 'android',
      appVersion: Application.nativeApplicationVersion ?? null,
      buildNumber: Application.nativeBuildVersion ?? null,
      screen: '(tabs)/health',
      eventType: input.eventType,
      severity: input.severity,
      sourceId: 'health_connect',
      syncMode: 'live_sync',
      availableFields: snap.availableFields,
      missingFields: snap.missingFields,
      normalizedDays: snap.normalizedDays,
      recordCountTotal: snap.recordCountTotal,
      userVisibleMessage: input.userVisibleMessage,
      developerMessage: input.developerMessage ?? snap.error,
    });
  } catch { /* non-fatal */ }
}

/**
 * Append a single breadcrumb to local storage so that if the next
 * upload attempt crashes the JS bundle, the in-app diagnostics panel
 * can show the last 30 steps from the previous run. We never log file
 * contents, URIs (only scheme), or token values.
 */
function whoopTrace(step: string, detail?: string): void {
  try {
    // Fire-and-forget; never await in event handlers.
    void (async () => {
      try {
        const prev = (await readStoredJson<WhoopUploadTrace[]>(WHOOP_UPLOAD_TRACE_KEY)) ?? [];
        const next = [...prev.slice(-29), { at: new Date().toISOString(), step, detail }];
        await writeStoredJson(WHOOP_UPLOAD_TRACE_KEY, next);
      } catch { /* swallow — trace must never throw */ }
    })();
    // eslint-disable-next-line no-console
    if (__DEV__) console.log(`[whoop-upload] ${step}`, detail ?? '');
  } catch { /* swallow */ }
}

export interface NormalizedPickedFile {
  ok: boolean;
  canceled: boolean;
  uri?: string;
  name?: string;
  mimeType?: string;
  size?: number | null;
  error?: string;
}

/**
 * Normalize every shape expo-document-picker has shipped: legacy
 * single-asset object, SDK 49+ `{canceled, assets[]}`, British-spelled
 * `cancelled`, `type:'cancel'`, missing assets array, and assets with
 * partial fields. Pure / no React, easy to test.
 */
export function normalizePickedWhoopFile(result: any): NormalizedPickedFile {
  if (result == null) return { ok: false, canceled: false, error: 'no_result' };
  if (result.canceled === true || result.cancelled === true || result.type === 'cancel') {
    return { ok: false, canceled: true };
  }
  let asset: any = null;
  if (Array.isArray(result.assets)) {
    if (result.assets.length === 0) return { ok: false, canceled: false, error: 'no_assets' };
    asset = result.assets[0];
  } else {
    asset = result;
  }
  const uri = typeof asset?.uri === 'string' && asset.uri.length > 0 ? asset.uri : undefined;
  if (!uri) return { ok: false, canceled: false, error: 'no_uri' };
  return {
    ok: true,
    canceled: false,
    uri,
    name: typeof asset.name === 'string' ? asset.name : undefined,
    mimeType: typeof asset.mimeType === 'string' ? asset.mimeType : undefined,
    size: typeof asset.size === 'number' ? asset.size : null,
  };
}
// Static import of the iOS health module so Metro resolves it at bundle
// time (the same mechanism HealthKitDebugCard uses, which is known to
// work on this device) rather than going through the `./health` service
// cache. We call HealthKitService directly so native
// HKHealthStore.requestAuthorizationToShareTypes:readTypes: actually
// fires on the Connect tap — iOS registers Lauburu under Health →
// Sources → Apps only after that native call succeeds.
import { HealthKitService, getHealthKitNativeDebug } from '../services/health.ios';
// Static named imports from ../services/health. We confirmed that
// named imports of these functions work — the store's `safeGetHealthService`
// uses the same pattern and has always worked. The earlier `import * as`
// namespace form is what was producing undefined bindings; switching to
// explicit named imports here so we can actually reset + re-init the
// service cache after the direct-native auth succeeds.
// IMPORTANT: import from `health-factory`, NOT `../services/health`.
// Metro's platform resolver picks `health.ios.ts` over `health.ts` on
// iOS (because the `.ios` suffix is a recognized platform extension),
// so `import { getHealthService } from '../services/health'` was
// silently resolving to health.ios.ts — which does NOT export those
// factory functions. That's why every tap kept landing on
// `Health service unavailable`. Renaming the factory path to one
// without a platform suffix breaks the resolver collision.
import {
  getHealthService as rawGetHealthService,
  getHealthServiceKind as rawGetHealthServiceKind,
  resetHealthServiceCache as rawResetHealthServiceCache,
} from '../services/health-factory';

type TapLog = {
  appleConnectAt: string | null;
  appleSyncAt: string | null;
  whoopStatusAt: string | null;
  whoopConnectAt: string | null;
  whoopSyncAt: string | null;
  whoopDisconnectAt: string | null;
};

type WhoopStatus = {
  status?: string;
  lastSyncAt?: string | null;
  latestDayDate?: string | null;
  missingDomains?: string[];
  domainsAvailable?: string[];
  readinessStatus?: string;
  missingVars?: string[];
  expectedRedirectUri?: string;
  reason?: string;
  whoopUserId?: number | string | null;
};

// ── Helpers ──────────────────────────────────────────────────────────

function safeString(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback;
}

function safeSlice(value: unknown, from: number, to: number): string {
  if (typeof value !== 'string') return '';
  try { return value.slice(from, to); } catch { return ''; }
}

/**
 * Hermes' toLocaleTimeString / toLocaleString fall back to UTC when the
 * full ICU dataset isn't bundled — which produced the "sync time hour
 * off by the UTC offset" bug. Format with explicit local accessors.
 */
function formatLocalClock(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function formatLocalDateTime(raw: unknown): string {
  if (typeof raw !== 'string' || raw.length === 0) return '(unknown)';
  const d = new Date(raw);
  if (!Number.isFinite(d.getTime())) return '(unknown)';
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const da = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${da} ${formatLocalClock(d)}`;
}

function describeError(e: unknown): string {
  if (e instanceof Error) return e.message || String(e);
  if (typeof e === 'string') return e;
  if (typeof e === 'object' && e !== null) {
    const m = (e as { message?: unknown }).message;
    if (typeof m === 'string' && m.length > 0) return m;
  }
  return 'unknown';
}

// ── SafeSection: per-block render try/catch ──────────────────────────

class SafeSection extends Component<{ label: string; children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: unknown): void {
    // eslint-disable-next-line no-console
    console.error(`[HealthActionsPanel:${this.props.label}]`, error, info);
  }
  render(): ReactNode {
    if (this.state.error) {
      return (
        <View style={styles.sectionError}>
          <Text style={styles.sectionErrorLabel}>{this.props.label} failed</Text>
          <Text style={styles.sectionErrorMsg}>{describeError(this.state.error)}</Text>
        </View>
      );
    }
    return this.props.children;
  }
}

// ── Outer boundary: last-resort catch-all ────────────────────────────

export class HealthActionsPanel extends Component<{}, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: unknown): void {
    // eslint-disable-next-line no-console
    console.error('[HealthActionsPanel:outer]', error, info);
  }
  render(): ReactNode {
    if (this.state.error) {
      const stack = (this.state.error.stack ?? '').split('\n').slice(0, 8).join('\n');
      return (
        <View style={styles.errorCard}>
          <Text style={styles.errorTitle}>Health actions panel recovered from crash</Text>
          <Text style={styles.errorMsg}>{describeError(this.state.error)}</Text>
          {stack ? <Text style={styles.errorStack}>{stack}</Text> : null}
        </View>
      );
    }
    return <Body />;
  }
}

// ── Body ─────────────────────────────────────────────────────────────

function Body() {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.session?.access_token);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);
  const syncData = useHealthStore((s) => s.syncData);

  const [taps, setTaps] = useState<TapLog>({
    appleConnectAt: null,
    appleSyncAt: null,
    whoopStatusAt: null,
    whoopConnectAt: null,
    whoopSyncAt: null,
    whoopDisconnectAt: null,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [whoop, setWhoop] = useState<WhoopStatus | null>(null);
  const [whoopLoading, setWhoopLoading] = useState(false);
  // Tick bumped after we forcibly (re-)init the native health service so
  // <IdentityService /> re-renders and shows `apple_health` instead of
  // stale `unknown` / `stub`.
  const [, forceIdentityTick] = useState(0);
  const bumpIdentity = useCallback(() => forceIdentityTick((n) => n + 1), []);

  // Eagerly materialize the native health service on mount. Without this,
  // the identity line stays on `unknown` until the user taps a button,
  // because HealthActionsPanel does not subscribe to any store state that
  // would otherwise re-render it when `health-store.checkPermissions()`
  // populates _instance.
  useEffect(() => {
    try {
      if (Platform.OS !== 'ios' && Platform.OS !== 'android') return;
      if (typeof rawResetHealthServiceCache === 'function') rawResetHealthServiceCache();
      if (typeof rawGetHealthService === 'function') rawGetHealthService();
    } catch { /* ignore — IdentityService will still show best-effort kind */ }
    bumpIdentity();
  }, [bumpIdentity]);

  const cfg = useMemo(() => {
    try {
      const build = IntegrationsClient.buildIntegrationConfig;
      if (typeof build !== 'function') return null;
      return build(user?.id, accessToken);
    } catch { return null; }
  }, [user?.id, accessToken]);
  const cfgRef = useRef(cfg);
  useEffect(() => { cfgRef.current = cfg; }, [cfg]);

  const stampTap = useCallback((key: keyof TapLog) => {
    setTaps((prev) => ({ ...prev, [key]: new Date().toISOString() }));
  }, []);

  const fetchWhoop = useCallback(async () => {
    const c = cfgRef.current;
    if (!c) return null;
    const getStatus = IntegrationsClient.getWhoopStatus;
    if (typeof getStatus !== 'function') return null;
    setWhoopLoading(true);
    try {
      const res = await getStatus(c);
      if (res.ok) {
        setWhoop(res.data as WhoopStatus);
        return res.data as WhoopStatus;
      }
      return null;
    } finally {
      setWhoopLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchWhoop();
    let sub: { remove?: () => void } | undefined;
    try {
      sub = AppState.addEventListener('change', (next) => {
        if (next === 'active') void fetchWhoop();
      });
    } catch { sub = undefined; }
    return () => { if (sub && typeof sub.remove === 'function') sub.remove(); };
  }, [fetchWhoop]);

  const onConnectAppleHealth = useCallback(async () => {
    stampTap('appleConnectAt');
    if (Platform.OS !== 'ios') { Alert.alert('Apple Health', 'iOS only.'); return; }
    // Defense-in-depth: if already connected (has days + lastSyncAt),
    // never re-run the fragile first-time native auth flow. Just sync.
    // The sheet UI already hides "Connect" in connected state, but a
    // stale press path or a restore-from-memory tap must not crash.
    try {
      const st: any = useHealthStore.getState();
      const alreadyConnected = Array.isArray(st?.days) && st.days.length > 0 && !!st?.lastSyncAt;
      if (alreadyConnected && user?.id && typeof syncData === 'function') {
        setBusy('apple-sync');
        try { await syncData(user.id); } finally { setBusy(null); }
        return;
      }
    } catch { /* fall through to first-time path */ }
    try {
      if (typeof rawResetHealthServiceCache === 'function') rawResetHealthServiceCache();
      if (typeof rawGetHealthService === 'function') rawGetHealthService();
    } catch { /* ignore */ }
    bumpIdentity();
    setBusy('apple-connect');
    // ZERO-INDIRECTION NATIVE CALL — require @kingstinct/react-native-
    // healthkit directly (the same module HealthKitDebugCard proves is
    // loadable on this device) and call requestAuthorization on it
    // inline, with NO service cache, NO wrapper class, NO platform
    // indirection. This is the one path iOS needs to see in order to
    // register Lauburu under Health → Sources → Apps. Previous attempts
    // all routed through health.ios / health.ts and one of those layers
    // was silently handing back the STUB.
    const READ_TYPES: string[] = [
      'HKQuantityTypeIdentifierRestingHeartRate',
      'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
      'HKQuantityTypeIdentifierStepCount',
      'HKQuantityTypeIdentifierActiveEnergyBurned',
      'HKQuantityTypeIdentifierHeartRate',
      'HKQuantityTypeIdentifierDistanceWalkingRunning',
      'HKQuantityTypeIdentifierBodyMass',
      'HKCategoryTypeIdentifierSleepAnalysis',
      'HKWorkoutTypeIdentifier',
    ];
    let directPathFired: 'raw' | 'class' | 'store' | 'neither' = 'neither';
    let directError: string | null = null;
    let directSamples: number | null = null;
    let directNativeReturn: string | null = null;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const hk = require('@kingstinct/react-native-healthkit');
      if (!hk) {
        directError = 'require(@kingstinct/react-native-healthkit) returned null';
      } else if (typeof hk.requestAuthorization !== 'function') {
        directError = `hk.requestAuthorization type=${typeof hk.requestAuthorization}; keys=${Object.keys(hk).slice(0, 8).join(',')}`;
      } else {
        // Call native requestAuthorization at module-level. iOS
        // HKHealthStore.requestAuthorizationToShareTypes:readTypes:
        // runs here. On first call it will show the permission sheet;
        // on subsequent calls iOS silently honors the prior decision.
        // Either way, the app gets registered under Health → Sources
        // → Apps once this promise resolves successfully.
        const r = await hk.requestAuthorization({ toRead: READ_TYPES });
        directNativeReturn = typeof r === 'boolean' ? String(r) : JSON.stringify(r).slice(0, 80);
        directPathFired = 'raw';
        // Canary step read so we can confirm the call actually went
        // through the native bridge (not just a JS resolve).
        try {
          if (typeof hk.queryQuantitySamples === 'function') {
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - 7);
            const samples = await hk.queryQuantitySamples(
              'HKQuantityTypeIdentifierStepCount',
              { limit: 10, filter: { date: { startDate: start, endDate: end } } },
            );
            directSamples = Array.isArray(samples) ? samples.length : 0;
          }
        } catch { /* canary optional */ }
      }
    } catch (e: any) {
      directError = e?.message ?? 'raw native call threw';
    }
    // Fall back to the class-based bypass if the raw path didn't fire
    // (extreme defensive — should be unreachable if HealthKitDebugCard's
    // own require worked earlier).
    if (directPathFired === 'neither') {
      try {
        if (typeof HealthKitService === 'function') {
          const directSvc = new HealthKitService();
          if (typeof directSvc?.requestPermissions === 'function') {
            await directSvc.requestPermissions();
            directPathFired = 'class';
          }
        }
      } catch (e: any) {
        if (!directError) directError = e?.message ?? 'class bypass threw';
      }
    }
    // If native auth actually fired (bridge round-trip succeeded), the
    // store's view-model is the only remaining thing standing between
    // "granted" and the AppleHealthCard transitioning. Seed the
    // permissions state to authorized so AppleHealthCard moves to
    // "Permission granted — sync needed" immediately, independent of
    // what loadNative() returns on this bundle.
    if (directPathFired === 'raw' || directPathFired === 'class') {
      try {
        useHealthStore.setState({
          permissions: {
            available: true,
            permissions: {
              heart_rate: 'authorized',
              resting_heart_rate: 'authorized',
              hrv: 'authorized',
              sleep: 'authorized',
              steps: 'authorized',
              active_calories: 'authorized',
              workouts: 'authorized',
            },
          },
          error: null,
        });
      } catch { /* store shape may differ — defensive */ }
      // Reset + re-init the service cache. loadNative() now has an
      // inline raw-native fallback, so this should resolve to a real
      // apple_health service even if the wrapper path was broken.
      try {
        if (typeof rawResetHealthServiceCache === 'function') rawResetHealthServiceCache();
        if (typeof rawGetHealthService === 'function') rawGetHealthService();
      } catch { /* ignore */ }
      bumpIdentity();
    }
    try {
      if (typeof requestPermissions !== 'function') {
        Alert.alert('Apple Health', 'Permission handler unavailable. Reopen the app.');
        return;
      }
      await requestPermissions();
      if (directPathFired === 'neither') directPathFired = 'store';
      // Auto-sync on Connect. We used to kick the full 5-year backfill
      // here on first Connect — but that dispatched ~500k+ raw samples
      // through the AI ingest POST in a single call, and on some
      // devices that crashed the app right after Apple Health registered
      // the permission. Always run a 365-day sync instead — still a
      // real baseline, never more than a few thousand samples. Users
      // who want deeper history tap the explicit "Backfill Apple
      // Health (5y)" button, which now runs incrementally.
      if (user?.id && typeof syncData === 'function') {
        await syncData(user.id);
      }
      // Read the concrete native result so the alert never falls back to
      // the opaque "Permission request finished." message. We now always
      // surface what HealthKit actually reported, per field.
      const lines: string[] = [];
      // Capture the service kind ONLY after the store's requestPermissions
      // returned — by that point _instance must be set (the store calls
      // getHealthService internally). If this still reads 'unknown', the
      // health module itself can't be required at runtime.
      let kind = 'unknown';
      try {
        kind = typeof rawGetHealthServiceKind === 'function' ? String(rawGetHealthServiceKind()) : 'unknown';
      } catch { /* ignore */ }
      lines.push(`service: ${kind}`);
      lines.push(`direct auth path: ${directPathFired}${directError ? ` (${directError})` : ''}`);
      if (directNativeReturn) lines.push(`native return: ${directNativeReturn}`);
      if (directSamples != null) lines.push(`direct canary samples: ${directSamples}`);
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mod = require('../services/health.ios');
        const debug = typeof mod?.getHealthKitNativeDebug === 'function' ? mod.getHealthKitNativeDebug() : null;
        if (debug) {
          lines.push(`native loaded: ${String(debug.moduleLoaded)}`);
          lines.push(`isHealthDataAvailable: ${String(debug.isHealthDataAvailableResult)}`);
          lines.push(`auth attempted: ${String(debug.requestAuthorizationAttempted)}`);
          lines.push(`auth ok: ${String(debug.lastAuthRequestOk)}`);
          if (debug.lastAuthRequestError) lines.push(`auth error: ${debug.lastAuthRequestError}`);
          lines.push(`canary step samples: ${String(debug.lastCanaryReadCount)}`);
        }
      } catch { /* ignore */ }
      // iOS remembers previous decisions. If canary is 0 on a second tap,
      // the sheet will NOT re-appear — user must go to Settings.
      lines.push('');
      lines.push('If no sheet appeared and samples are 0, iOS kept your previous choice. Open iOS Settings → Health → Data Access & Devices → Lauburu and enable the metrics you want, then tap Sync Apple Health.');
      if (!user?.id) lines.push('\nSign in to save synced data to your account.');
      Alert.alert('Apple Health', lines.join('\n'));
      bumpIdentity();
    } catch (e: any) {
      Alert.alert('Apple Health', `Error: ${e?.message ?? 'unknown'}`);
    } finally { setBusy(null); }
  }, [requestPermissions, stampTap, syncData, user?.id, bumpIdentity]);

  const onSyncAppleHealth = useCallback(async () => {
    stampTap('appleSyncAt');
    if (!user?.id) { Alert.alert('Apple Health', 'Sign in first.'); return; }
    try {
      if (typeof rawResetHealthServiceCache === 'function') rawResetHealthServiceCache();
      if (typeof rawGetHealthService === 'function') rawGetHealthService();
    } catch { /* ignore */ }
    bumpIdentity();
    setBusy('apple-sync');
    try {
      if (typeof syncData !== 'function') {
        Alert.alert('Apple Health', 'Sync handler unavailable. Reopen the app.');
        return;
      }
      await syncData(user.id);
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const hs = require('../store/health-store');
        const store = hs?.useHealthStore?.getState?.();
        const diag = store?.lastSyncDiagnostics;
        const err = store?.error;
        if (err) {
          Alert.alert('Apple Health', `Sync error: ${err}`);
        } else if (diag) {
          const counts = diag.recordCounts || {};
          const total = Object.values(counts).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0);
          Alert.alert('Apple Health',
            total > 0
              ? `Sync ok. ${diag.normalizedDays} days · ${total} samples across ${Object.keys(counts).length} metrics.`
              : 'Connected — no recent data. iOS Settings → Health → Data Access & Devices → Lauburu to enable more metrics.');
        }
      } catch { /* ignore */ }
      bumpIdentity();
    } catch (e: any) {
      Alert.alert('Apple Health', `Sync error: ${e?.message ?? 'unknown'}`);
    } finally { setBusy(null); }
  }, [stampTap, syncData, user?.id, bumpIdentity]);

  // ── Android Health Connect handlers ────────────────────────────────
  // These mirror the Apple Health handlers above but route through the
  // platform-aware `useHealthStore.requestPermissions()` /
  // `syncData()` paths (which dispatch through health-factory to
  // health.android.ts → react-native-health-connect). They were
  // previously missing — the appleRow on Android was firing
  // `onConnectAppleHealth`, which short-circuits with "iOS only" and
  // showed Apple-Health-branded alerts on an Android device. Each
  // handler fires audit events so Admin/Dev → Audit can confirm the
  // flow ran end-to-end on a real device.
  const onConnectHealthConnect = useCallback(async () => {
    if (Platform.OS !== 'android') {
      Alert.alert('Health Connect', 'Android only.');
      return;
    }
    setBusy('hc-connect');
    try {
      // Audit: permission_requested.
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const aud = require('../store/audit-event-store');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const App = require('expo-application');
        aud?.useAuditEventStore?.getState?.()?.add?.({
          platform: 'android',
          appVersion: App?.nativeApplicationVersion ?? null,
          buildNumber: App?.nativeBuildVersion ?? null,
          screen: '(tabs)/health',
          eventType: 'permission_requested',
          severity: 'info',
          sourceId: 'health_connect',
          userVisibleMessage: 'Requesting Health Connect permissions.',
        });
      } catch { /* non-fatal */ }
      if (typeof requestPermissions !== 'function') {
        Alert.alert('Health Connect', 'Permission handler unavailable. Reopen the app.');
        return;
      }
      await requestPermissions();
      // Read back the resulting permission state so we can route to a
      // granted vs denied audit event without a second permission probe.
      const st: any = useHealthStore.getState();
      const perms = st?.permissions?.permissions ?? {};
      const granted = Object.values(perms).some((v) => v === 'authorized');
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const aud = require('../store/audit-event-store');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const App = require('expo-application');
        aud?.useAuditEventStore?.getState?.()?.add?.({
          platform: 'android',
          appVersion: App?.nativeApplicationVersion ?? null,
          buildNumber: App?.nativeBuildVersion ?? null,
          screen: '(tabs)/health',
          eventType: granted ? 'permission_granted' : 'permission_denied',
          severity: granted ? 'info' : 'warning',
          sourceId: 'health_connect',
          permissionState: granted ? 'authorized' : 'denied',
          userVisibleMessage: granted
            ? 'Health Connect permissions granted (at least one metric).'
            : 'Health Connect permissions not granted.',
        });
      } catch { /* non-fatal */ }
      // If granted and signed in, run the standard sync immediately so
      // the user sees data flow without a second tap.
      if (granted && user?.id && typeof syncData === 'function') {
        addHealthConnectAuditEvent({
          eventType: 'sync_started',
          severity: 'info',
        });
        try {
          await syncData(user.id);
          const snap = buildHealthConnectSyncAuditSnapshot();
          if (snap.error) {
            addHealthConnectAuditEvent({
              eventType: 'sync_failed',
              severity: 'error',
              userVisibleMessage: 'Health Connect sync failed.',
              developerMessage: snap.error,
            });
          } else {
            addHealthConnectAuditEvent({
              eventType: 'sync_succeeded',
              severity: 'info',
              userVisibleMessage: snap.recordCountTotal > 0
                ? `Health Connect sync succeeded with ${snap.normalizedDays ?? 0} normalized days.`
                : 'Health Connect sync completed with no recent records.',
            });
            if (snap.missingFields.length > 0) {
              addHealthConnectAuditEvent({
                eventType: 'missing_metrics',
                severity: snap.availableFields.length > 0 ? 'warning' : 'info',
                userVisibleMessage: snap.availableFields.length > 0
                  ? `Health Connect missing: ${snap.missingFields.join(', ')}.`
                  : 'Health Connect returned no recent records.',
              });
            }
          }
        } catch (e: any) {
          try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const aud = require('../store/audit-event-store');
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const App = require('expo-application');
            aud?.useAuditEventStore?.getState?.()?.add?.({
              platform: 'android',
              appVersion: App?.nativeApplicationVersion ?? null,
              buildNumber: App?.nativeBuildVersion ?? null,
              screen: '(tabs)/health',
              eventType: 'sync_failed',
              severity: 'error',
              sourceId: 'health_connect',
              developerMessage: e?.message ?? 'unknown',
            });
          } catch { /* non-fatal */ }
        }
      }
      Alert.alert(
        'Health Connect',
        granted
          ? user?.id
            ? 'Permissions granted. Synced your latest metrics.'
            : 'Permissions granted. Sign in to save synced data to your account.'
          : 'Permissions not granted. Open Health Connect → App permissions → Lauburu and grant the metrics you want, then tap Sync.',
      );
    } catch (e: any) {
      Alert.alert('Health Connect', `Error: ${e?.message ?? 'unknown'}`);
    } finally {
      setBusy(null);
    }
  }, [requestPermissions, syncData, user?.id]);

  const onSyncHealthConnect = useCallback(async () => {
    if (Platform.OS !== 'android') {
      Alert.alert('Health Connect', 'Android only.');
      return;
    }
    if (!user?.id) {
      Alert.alert('Health Connect', 'Sign in first.');
      return;
    }
    setBusy('hc-sync');
    try {
      if (typeof syncData !== 'function') {
        addHealthConnectAuditEvent({
          eventType: 'sync_failed',
          severity: 'error',
          userVisibleMessage: 'Health Connect sync failed.',
          developerMessage: 'Sync handler unavailable.',
        });
        Alert.alert('Health Connect', 'Sync handler unavailable. Reopen the app.');
        return;
      }
      addHealthConnectAuditEvent({
        eventType: 'sync_started',
        severity: 'info',
      });
      await syncData(user.id);
      const snap = buildHealthConnectSyncAuditSnapshot();
      if (snap.error) {
        addHealthConnectAuditEvent({
          eventType: 'sync_failed',
          severity: 'error',
          userVisibleMessage: 'Health Connect sync failed.',
          developerMessage: snap.error,
        });
      } else {
        addHealthConnectAuditEvent({
          eventType: 'sync_succeeded',
          severity: 'info',
          userVisibleMessage: snap.recordCountTotal > 0
            ? `Health Connect sync succeeded with ${snap.normalizedDays ?? 0} normalized days.`
            : 'Health Connect sync completed with no recent records.',
        });
        if (snap.missingFields.length > 0) {
          addHealthConnectAuditEvent({
            eventType: 'missing_metrics',
            severity: snap.availableFields.length > 0 ? 'warning' : 'info',
            userVisibleMessage: snap.availableFields.length > 0
              ? `Health Connect missing: ${snap.missingFields.join(', ')}.`
              : 'Health Connect returned no recent records.',
          });
        }
      }
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const hs = require('../store/health-store');
        const store = hs?.useHealthStore?.getState?.();
        const diag = store?.lastSyncDiagnostics;
        const err = store?.error;
        if (err) {
          Alert.alert('Health Connect', `Sync error: ${err}`);
        } else if (diag) {
          const counts = diag.recordCounts || {};
          const total = Object.values(counts).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0);
          Alert.alert('Health Connect',
            total > 0
              ? `Sync ok. ${diag.normalizedDays} days · ${total} samples across ${Object.keys(counts).length} metrics.`
              : 'Connected — no recent data. Open Health Connect → App permissions → Lauburu to enable more metrics.');
        }
      } catch { /* non-fatal */ }
    } catch (e: any) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const aud = require('../store/audit-event-store');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const App = require('expo-application');
        aud?.useAuditEventStore?.getState?.()?.add?.({
          platform: 'android',
          appVersion: App?.nativeApplicationVersion ?? null,
          buildNumber: App?.nativeBuildVersion ?? null,
          screen: '(tabs)/health',
          eventType: 'sync_failed',
          severity: 'error',
          sourceId: 'health_connect',
          developerMessage: e?.message ?? 'unknown',
        });
      } catch { /* non-fatal */ }
      Alert.alert('Health Connect', `Sync error: ${e?.message ?? 'unknown'}`);
    } finally {
      setBusy(null);
    }
  }, [syncData, user?.id]);

  const onCheckWhoopStatus = useCallback(async () => {
    stampTap('whoopStatusAt');
    if (!cfg) {
      Alert.alert('WHOOP', 'Sign in first, then try WHOOP Direct again.');
      return;
    }
    setBusy('whoop-status');
    const d = await fetchWhoop();
    setBusy(null);
    if (!d) { Alert.alert('WHOOP status', 'Network error.'); return; }
    if (d.status === 'config_missing') {
      Alert.alert('WHOOP setup required', 'WHOOP Direct is not ready on the backend yet. Ask Aaron to finish the vendor setup, then try again.');
    } else if (d.status === 'auth_required') {
      Alert.alert('WHOOP', 'Ready to connect. Tap Connect WHOOP to start OAuth.');
    } else if (d.status === 'connected') {
      const raw = d.lastSyncAt;
      const when = typeof raw === 'string' && raw.length >= 16 ? raw.slice(0, 16).replace('T', ' ') : null;
      Alert.alert('WHOOP', when ? `Connected. Last sync ${when}.` : 'Connected — sync needed.');
    } else {
      Alert.alert('WHOOP status', `status=${d.status ?? 'unknown'}`);
    }
  }, [cfg, fetchWhoop, stampTap]);

  const onConnectWhoop = useCallback(async () => {
    stampTap('whoopConnectAt');
    if (!cfg) {
      Alert.alert('WHOOP', 'Sign in first, then try WHOOP Direct again.');
      return;
    }
    const getUrl = IntegrationsClient.getWhoopConnectUrl;
    if (typeof getUrl !== 'function') {
      Alert.alert('WHOOP', 'Connect handler unavailable. Reopen the app.');
      return;
    }
    setBusy('whoop-connect');
    try {
      const res = await getUrl(cfg);
      if (!res.ok) {
        const text = res.error ?? 'Unknown';
        try {
          const parsed = JSON.parse(text);
          if (Array.isArray(parsed?.missingVars)) {
            Alert.alert('WHOOP setup required', 'WHOOP Direct is not ready on the backend yet. Ask Aaron to finish the vendor setup, then try again.');
            return;
          }
        } catch { /* fall through */ }
        Alert.alert('WHOOP', `Connect error: ${text}`);
        return;
      }
      await Linking.openURL(res.data.url);
    } catch (e: any) {
      Alert.alert('WHOOP', `Error: ${e?.message ?? 'unknown'}`);
    } finally { setBusy(null); }
  }, [cfg, stampTap]);

  const onSyncWhoop = useCallback(async () => {
    stampTap('whoopSyncAt');
    if (!cfg) { Alert.alert('WHOOP', 'Not signed in.'); return; }
    const sync = IntegrationsClient.syncWhoop;
    if (typeof sync !== 'function') {
      Alert.alert('WHOOP', 'Sync handler unavailable. Reopen the app.');
      return;
    }
    setBusy('whoop-sync');
    const res = await sync(cfg);
    // Capture the exact moment the sync POST returned OK. This is the
    // only truly fresh timestamp we have — the backend's `lastSyncAt`
    // sometimes reports the latest *scored* cycle, not the sync round-
    // trip, which made the post-sync Alert look like nothing changed.
    const syncedAt = new Date();
    setBusy(null);
    if (!res.ok) { Alert.alert('WHOOP sync', res.error ?? 'Sync failed.'); return; }
    // Refresh source-of-truth status so the WHOOP card + identity
    // line reflect the latest server view.
    const d = await fetchWhoop();
    // Hermes' toLocaleTimeString can fall back to UTC when full-ICU
    // data is absent — that's what gave us the "14:40 vs 00:40" hour
    // mismatch. Use explicit local accessors instead.
    const syncedLocal = formatLocalClock(syncedAt);
    const lines: string[] = [`Synced just now · ${syncedLocal} local.`];
    if (typeof d?.latestDayDate === 'string' && d.latestDayDate.length > 0) {
      lines.push(`Latest WHOOP day: ${d.latestDayDate}.`);
    }
    const backendRaw = d?.lastSyncAt;
    if (typeof backendRaw === 'string' && backendRaw.length >= 16) {
      const backendLocal = formatLocalDateTime(backendRaw);
      lines.push(`Backend lastSyncAt: ${backendLocal} local (may lag until WHOOP scores today's cycle).`);
    }
    const missing = (d as unknown as { missingDomains?: unknown })?.missingDomains;
    if (Array.isArray(missing) && missing.length > 0) {
      lines.push(`Still missing: ${missing.join(', ')}.`);
    } else if (d?.status === 'connected') {
      lines.push('All readiness domains present.');
    }
    Alert.alert('WHOOP', lines.join('\n'));
  }, [cfg, fetchWhoop, stampTap]);

  const onDisconnectWhoop = useCallback(async () => {
    stampTap('whoopDisconnectAt');
    if (!cfg) { Alert.alert('WHOOP', 'Not signed in.'); return; }
    const disc = IntegrationsClient.disconnectWhoop;
    if (typeof disc !== 'function') {
      Alert.alert('WHOOP', 'Disconnect handler unavailable. Reopen the app.');
      return;
    }
    setBusy('whoop-disconnect');
    const res = await disc(cfg);
    setBusy(null);
    if (!res.ok) { Alert.alert('WHOOP disconnect', res.error ?? 'Failed.'); return; }
    await fetchWhoop();
    Alert.alert('WHOOP', 'Disconnected.');
  }, [cfg, fetchWhoop, stampTap]);

  // Deep HealthKit backfill — ~5 years of authorized data. The AI
  // layer needs a real baseline to compute trends/recovery context,
  // not one week of noise. This reads only what iOS has granted.
  const onBackfillAppleHealth = useCallback(async () => {
    if (!user?.id) { Alert.alert('Apple Health', 'Sign in first.'); return; }
    setBusy('apple-backfill');
    try {
      const backfill = useHealthStore.getState().backfillData;
      if (typeof backfill !== 'function') {
        Alert.alert('Apple Health', 'Backfill handler unavailable. Reopen the app.');
        return;
      }
      await backfill(user.id);
      const s = useHealthStore.getState();
      const diag = s.lastSyncDiagnostics;
      const window = s.historyWindowDays ?? 0;
      const total = diag ? Object.values(diag.recordCounts).reduce((a, b) => a + (typeof b === 'number' ? b : 0), 0) : 0;
      Alert.alert(
        'Health data enrichment',
        s.error
          ? `Could not enrich: ${s.error}`
          : `Pulled all available Apple Health history.\n${diag?.normalizedDays ?? 0} days normalized · ${total} samples ingested.\nYour Coach now has deeper baselines to work from.`,
      );
      bumpIdentity();
    } catch (e: any) {
      Alert.alert('Apple Health', `Backfill error: ${e?.message ?? 'unknown'}`);
    } finally { setBusy(null); }
  }, [user?.id, bumpIdentity]);

  // Deep WHOOP backfill — backend-driven. Sends {deep:true,daysBack:365}
  // to /api/integrations/whoop/sync. Backends that don't understand
  // the flag just do a normal sync — safe to ship.
  const onBackfillWhoop = useCallback(async () => {
    if (!cfg) { Alert.alert('WHOOP', 'Not signed in.'); return; }
    const backfill = IntegrationsClient.backfillWhoop;
    if (typeof backfill !== 'function') {
      Alert.alert('WHOOP', 'Backfill handler unavailable. Reopen the app.');
      return;
    }
    setBusy('whoop-backfill');
    const res = await backfill(cfg, 365);
    setBusy(null);
    if (!res.ok) { Alert.alert('WHOOP backfill', res.error ?? 'Backfill failed.'); return; }
    const d = await fetchWhoop();
    const days = (res.data as any)?.daysIngested ?? (res.data as any)?.recordCount ?? '(unreported)';
    Alert.alert(
      'WHOOP backfill',
      `Deep backfill requested.\nRecords reported: ${days}\nLatest WHOOP day: ${d?.latestDayDate ?? '—'}.\nThe backend will keep filling in older cycles when they're scored.`,
    );
  }, [cfg, fetchWhoop]);

  const whoopState = whoop?.status ?? (whoopLoading ? 'loading' : 'unknown');
  const isWhoopConnected = whoopState === 'connected' || whoopState === 'partial';
  const [sheetOpen, setSheetOpen] = useState(false);
  const [showDiag, setShowDiag] = useState(false);

  // Live-derived source summary for the compact top-of-card line.
  const healthDays = useHealthStore((s) => s.days.length);
  const healthLastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const appleHealthConnected = healthDays > 0 && !!healthLastSyncAt;
  // Attention = actionable problem. Partial for TODAY's cycle is not
  // actionable — the cycle hasn't been scored yet (normal until after
  // tonight's sleep). Only surface amber when the user actually needs
  // to do something: token expired, OAuth needed, unconfigured, or a
  // non-today partial that suggests a real sync gap.
  const bodyTodayYmd = (() => { const d = new Date(); const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const da = String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${da}`; })();
  const bodyLatestIsToday = whoop?.latestDayDate === bodyTodayYmd;
  // Also inspect the live WhoopDay (from /data/today). When backend
  // /status says "connected" but the live cycle has no recovery/sleep
  // scored yet and date is today, the truthful state is "awaiting
  // latest cycle", NOT a happy "connected".
  const bodyLiveDay = useWhoopStore((s) => s.day);
  const bodyLiveCycleEmpty = bodyLiveDay != null
    && bodyLiveDay.date === bodyTodayYmd
    && bodyLiveDay.recovery_score == null
    && bodyLiveDay.sleep_hours == null;
  const bodyAwaiting = (whoopState === 'partial' && bodyLatestIsToday) || bodyLiveCycleEmpty;
  const needsAttention =
    whoopState === 'error' ||
    whoopState === 'auth_required' ||
    whoopState === 'config_missing' ||
    (whoopState === 'partial' && !bodyLatestIsToday && !bodyLiveCycleEmpty);
  const summaryLine = (() => {
    const parts: string[] = [];
    if (appleHealthConnected) parts.push(Platform.OS === 'ios' ? 'Apple Health / HealthKit' : 'Health Connect');
    if (bodyAwaiting) parts.push('WHOOP · awaiting latest cycle');
    else if (whoopState === 'connected') parts.push('WHOOP');
    else if (whoopState === 'partial') parts.push('WHOOP · partial');
    if (parts.length === 0) return 'No sources connected yet';
    return parts.join(' · ');
  })();

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Health sources</Text>
      <Text style={styles.summaryLine}>{summaryLine}</Text>

      <Pressable
        style={[styles.manageBtn, needsAttention && styles.manageBtnAttention]}
        onPress={() => setSheetOpen(true)}
        accessibilityRole="button"
        accessibilityLabel="Manage health sources">
        <Text style={styles.manageBtnText}>
          {needsAttention ? 'Attention needed · Manage sources' : 'Manage health sources'}
        </Text>
      </Pressable>

      <HealthSourceSheet
        visible={sheetOpen}
        onClose={() => setSheetOpen(false)}
        busy={busy}
        appleHealthConnected={appleHealthConnected}
        healthDays={healthDays}
        healthLastSyncAt={healthLastSyncAt}
        whoopState={whoopState}
        whoop={whoop}
        isWhoopConnected={isWhoopConnected}
        onConnectAppleHealth={onConnectAppleHealth}
        onSyncAppleHealth={onSyncAppleHealth}
        onBackfillAppleHealth={onBackfillAppleHealth}
        onConnectHealthConnect={onConnectHealthConnect}
        onSyncHealthConnect={onSyncHealthConnect}
        onCheckWhoopStatus={onCheckWhoopStatus}
        onConnectWhoop={onConnectWhoop}
        onSyncWhoop={onSyncWhoop}
        onBackfillWhoop={onBackfillWhoop}
        onDisconnectWhoop={onDisconnectWhoop}
      />

      <Pressable
        style={styles.diagToggle}
        onPress={() => setShowDiag((v) => !v)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={showDiag ? 'Hide diagnostics' : 'Show diagnostics'}>
        <Text style={styles.diagToggleText}>
          {showDiag ? '▾ Hide diagnostics' : '▸ Show diagnostics'}
        </Text>
      </Pressable>
      {showDiag && (
        <View style={styles.idBlock}>
          <SafeSection label="identity-version">
            <IdentityVersion />
          </SafeSection>
          <SafeSection label="identity-channel">
            <IdentityChannel />
          </SafeSection>
          <SafeSection label="identity-update">
            <IdentityUpdate />
          </SafeSection>
          <SafeSection label="identity-createdAt">
            <IdentityCreatedAt />
          </SafeSection>
          <SafeSection label="identity-service">
            <IdentityService />
          </SafeSection>
          <SafeSection label="history-depth">
            <HistoryDepth />
          </SafeSection>
          <SafeSection label="whoop-label">
            <WhoopLabel state={whoopState} whoop={whoop} />
          </SafeSection>
          <SafeSection label="taps">
            <TapsBlock taps={taps} />
          </SafeSection>
        </View>
      )}
    </View>
  );
}

/**
 * Exposes the Apple Health / Health Connect history window currently
 * in use. Matches the "do not silently fall back to a shallow recent-
 * only window" requirement — if the last sync used 30 days, that's
 * what users see; if a 5-year backfill ran, it reflects that.
 */
function HistoryDepth() {
  const days = useHealthStore((s) => s.historyWindowDays);
  const lastBackfill = useHealthStore((s) => s.lastBackfillAt);
  const diag = useHealthStore((s) => s.lastSyncDiagnostics);
  const normalized = diag?.normalizedDays ?? 0;
  const windowLine = days != null ? `${days} days` : '(not synced yet)';
  const backfillLine = lastBackfill
    ? ` · last backfill ${formatLocalDateTime(lastBackfill)} local`
    : '';
  return (
    <>
      <Text style={styles.idLine}>history window: {windowLine}{backfillLine}</Text>
      <Text style={styles.idLine}>normalized days available: {normalized}</Text>
    </>
  );
}

// ── Identity sub-renderers (each in its own SafeSection) ─────────────

function IdentityVersion() {
  const appVersion = safeString(Application.nativeApplicationVersion, '?');
  const buildNumber = safeString(Application.nativeBuildVersion, '?');
  let runtimeVersion = '?';
  try { runtimeVersion = safeString(Updates.runtimeVersion as unknown, '?'); } catch { /* ignore */ }
  return (
    <Text style={styles.idLine}>
      v{appVersion} · build {buildNumber} · runtime {runtimeVersion}
    </Text>
  );
}

function IdentityChannel() {
  let channel = '(embedded)';
  try { channel = safeString(Updates.channel as unknown, '(embedded)'); } catch { /* ignore */ }
  return <Text style={styles.idLine}>channel: {channel}</Text>;
}

function IdentityUpdate() {
  let updateId = '(embedded)';
  try { updateId = safeString(Updates.updateId as unknown, '(embedded)'); } catch { /* ignore */ }
  const short = typeof updateId === 'string' && updateId.length > 8 ? updateId.slice(0, 8) : updateId;
  return <Text style={styles.idLine}>update: {short}…</Text>;
}

function IdentityCreatedAt() {
  let label = '(embedded)';
  try {
    const raw = Updates.createdAt;
    if (raw) {
      const d = raw instanceof Date ? raw : new Date(raw as never);
      const t = d.getTime();
      if (Number.isFinite(t)) {
        label = d.toISOString().slice(0, 19).replace('T', ' ');
      }
    }
  } catch { /* ignore */ }
  return <Text style={styles.idLine}>bundle at: {label}</Text>;
}

function IdentityService() {
  let kind = 'unknown';
  try {
    if (typeof rawGetHealthServiceKind === 'function') {
      const v = rawGetHealthServiceKind();
      if (typeof v === 'string') kind = v;
    }
  } catch { /* ignore */ }
  return <Text style={styles.idLine}>health service: {kind}</Text>;
}

function WhoopLabel({ state, whoop }: { state: string; whoop: WhoopStatus | null }) {
  let label = 'Unknown';
  try {
    switch (state) {
      case 'connected': {
        const missing = (whoop as unknown as { missingDomains?: unknown })?.missingDomains;
        const raw = whoop?.lastSyncAt;
        const syncLabel = typeof raw === 'string' && raw.length >= 16
          ? `last sync ${raw.slice(0, 16).replace('T', ' ')}`
          : 'sync needed';
        label = Array.isArray(missing) && missing.length > 0
          ? `Connected · ${syncLabel} · missing ${missing.join(', ')}`
          : `Connected · ${syncLabel}`;
        break;
      }
      case 'partial': {
        const missing = (whoop as unknown as { missingDomains?: unknown })?.missingDomains;
        label = Array.isArray(missing) && missing.length > 0
          ? `Partial sync · missing ${missing.join(', ')}`
          : 'Partial sync';
        break;
      }
      case 'auth_required': label = 'Not connected — ready to link'; break;
      case 'config_missing': label = 'Setup required'; break;
      case 'disconnected':  label = 'Disconnected'; break;
      case 'error':         label = 'Reconnect required (token expired)'; break;
      case 'loading':       label = 'Loading status…'; break;
      default:              label = 'Unknown';
    }
  } catch { /* keep default */ }
  return <Text style={styles.idLine}>WHOOP: {label}</Text>;
}

function TapsBlock({ taps }: { taps: TapLog }) {
  const any =
    taps.appleConnectAt || taps.appleSyncAt || taps.whoopStatusAt ||
    taps.whoopConnectAt || taps.whoopSyncAt || taps.whoopDisconnectAt;
  if (!any) return null;
  return (
    <>
      <Text style={styles.idLabel}>Last taps</Text>
      {taps.appleConnectAt && <Text style={styles.idLine}>AH connect: {safeSlice(taps.appleConnectAt, 11, 19)}</Text>}
      {taps.appleSyncAt && <Text style={styles.idLine}>AH sync: {safeSlice(taps.appleSyncAt, 11, 19)}</Text>}
      {taps.whoopStatusAt && <Text style={styles.idLine}>WHOOP status: {safeSlice(taps.whoopStatusAt, 11, 19)}</Text>}
      {taps.whoopConnectAt && <Text style={styles.idLine}>WHOOP connect: {safeSlice(taps.whoopConnectAt, 11, 19)}</Text>}
      {taps.whoopSyncAt && <Text style={styles.idLine}>WHOOP sync: {safeSlice(taps.whoopSyncAt, 11, 19)}</Text>}
      {taps.whoopDisconnectAt && <Text style={styles.idLine}>WHOOP disconnect: {safeSlice(taps.whoopDisconnectAt, 11, 19)}</Text>}
    </>
  );
}

function ActionButton({
  label,
  onPress,
  color,
  disabled,
}: {
  label: string;
  onPress?: () => void;
  color: string;
  disabled?: boolean;
}) {
  const safeOnPress = typeof onPress === 'function' ? onPress : () => {};
  return (
    <Pressable
      onPress={safeOnPress}
      disabled={disabled || typeof onPress !== 'function'}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: color, opacity: disabled ? 0.5 : pressed ? 0.75 : 1 },
      ]}
    >
      <Text style={styles.btnText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.06)',
    gap: 10,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.3)',
  },
  title: { fontSize: 15, fontWeight: '700' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  btn: {
    flexGrow: 1,
    flexBasis: '47%',
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 50,
  },
  btnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0a0a0a',
    textAlign: 'center',
  },
  idBlock: { gap: 2, marginTop: 4 },
  idLabel: {
    fontSize: 10, fontWeight: '600', opacity: 0.5,
    textTransform: 'uppercase', marginTop: 6,
  },
  idLine: { fontSize: 11, opacity: 0.7, fontFamily: 'SpaceMono' },
  sectionError: {
    padding: 6, borderRadius: 6,
    backgroundColor: 'rgba(255,107,107,0.1)',
    borderWidth: 1, borderColor: 'rgba(255,107,107,0.4)',
    gap: 2, marginVertical: 2,
  },
  sectionErrorLabel: { fontSize: 10, fontWeight: '700', color: '#ff6b6b', textTransform: 'uppercase' },
  sectionErrorMsg: { fontSize: 11, color: '#ff6b6b', fontFamily: 'SpaceMono' },
  errorCard: {
    padding: 14, borderRadius: 12,
    backgroundColor: 'rgba(255,107,107,0.08)',
    borderWidth: 1, borderColor: '#ff6b6b', gap: 6,
  },
  errorTitle: { fontSize: 14, fontWeight: '700', color: '#ff6b6b' },
  errorMsg: { fontSize: 13, fontFamily: 'SpaceMono', color: '#ff6b6b' },
  errorStack: { fontSize: 10, opacity: 0.6, fontFamily: 'SpaceMono' },
  summaryLine: { fontSize: 12, opacity: 0.65 },
  manageBtn: {
    backgroundColor: '#d4e157',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44,
  },
  manageBtnAttention: { backgroundColor: '#ffa500' },
  manageBtnText: { color: '#0a0a0a', fontSize: 14, fontWeight: '700' },
  diagToggle: { alignSelf: 'flex-start', paddingVertical: 4 },
  diagToggleText: { fontSize: 11, color: '#888' },
  // Source sheet
  sheetOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#0e0e0e',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: '88%',
    paddingBottom: 8,
  },
  sheetHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255,255,255,0.08)',
  },
  sheetTitle: { fontSize: 17, fontWeight: '700' },
  sheetClose: { fontSize: 14, color: '#d4e157', fontWeight: '600' },
  sheetScroll: { paddingBottom: 24 },
  sheetInlineCard: { paddingHorizontal: 16, paddingTop: 12 },
  sheetSectionHeader: {
    fontSize: 11,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 6,
  },
  sourceRow: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(255,255,255,0.06)',
    gap: 6,
  },
  sourceRowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  sourceName: { fontSize: 15, fontWeight: '600' },
  sourceChip: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    borderWidth: 1,
  },
  sourceChipText: { fontSize: 10, fontWeight: '700' },
  sourceMeta: { fontSize: 12, opacity: 0.55 },
  rowActions: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
    marginTop: 6,
  },
  rowBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.4)',
    minHeight: 36,
    justifyContent: 'center',
  },
  rowBtnPrimary: {
    backgroundColor: '#d4e157',
    borderColor: '#d4e157',
  },
  rowBtnDanger: {
    backgroundColor: 'rgba(255,107,107,0.12)',
    borderColor: 'rgba(255,107,107,0.5)',
  },
  rowBtnText: { fontSize: 12, fontWeight: '700', color: '#d4e157' },
  rowBtnTextPrimary: { color: '#0a0a0a' },
  rowBtnTextDanger: { color: '#ff6b6b' },
  fileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  fileName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#d4e157',
    padding: 0,
    margin: 0,
  },
  csvInput: {
    minHeight: 160,
    maxHeight: 220,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    backgroundColor: 'rgba(0,0,0,0.3)',
    padding: 10,
    color: '#e0e0e0',
    fontFamily: 'SpaceMono',
    fontSize: 10,
    textAlignVertical: 'top',
  },
});

// ── HealthSourceSheet ────────────────────────────────────────────────

function BackendSyncRow() {
  const persisting = useHealthStore((s) => s.persisting);
  const lastPersistedAt = useHealthStore((s) => s.lastPersistedAt);
  const lastPersistResult = useHealthStore((s) => s.lastPersistResult);
  const persistToBackend = useHealthStore((s) => s.persistToBackend);
  const storeError = useHealthStore((s) => s.error);
  const authStatus = useAuthStore((s) => s.status);
  const canPersist = useTierStore((s) => s.can)('backend_persistence');
  const nativeSourceLabel = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
  const [saving, setSaving] = useState<false | 'railway' | 'supabase'>(false);
  const [pressResult, setPressResult] = useState<
    {
      at: string;
      railway: { status: 'saved' | 'empty' | 'error'; lines: string[]; error?: string };
      supabase: { ok: boolean; recordCount?: number; dateRange?: string; error?: string };
    } | null
  >(null);

  const handlePress = useCallback(async () => {
    const startedAt = new Date().toISOString();
    setSaving('railway');
    setPressResult(null);
    let railwayLines: string[] = [];
    let railwayError: string | null = null;
    let railwayCalled = false;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { persistDurableToRailway } = require('../services/durable-persist');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const nutStore = require('../store/nutrition-store');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const hiitStore = require('../store/hiit-workout-store');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const trainingStore = require('../store/training-store');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const authMod = require('../store/auth-store');
      const uid = authMod?.useAuthStore?.getState?.()?.user?.id;
      const days = useHealthStore.getState().days;
      const nut = nutStore?.useNutritionStore?.getState?.();
      const hiitWorkouts = hiitStore?.useHIITWorkoutStore?.getState?.()?.workouts ?? [];
      const trainingSessions = trainingStore?.useTrainingStore?.getState?.()?.sessions ?? [];

      let athleteStateSnapshot: unknown = null;
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const appState = require('../services/app-athlete-state');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const whoopStore = require('../store/whoop-store');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const secureStorage = require('../store/secure-storage');
        const whoop = whoopStore?.useWhoopStore?.getState?.();
        const whoopCsv = await secureStorage.readStoredJson?.('whoop_csv_imported_v1').catch(() => null);
        athleteStateSnapshot = appState.buildAppAthleteState?.({
          todayIsoDate: new Date().toISOString().slice(0, 10),
          days,
          features: useHealthStore.getState().features,
          sessions: trainingSessions,
          whoopDay: whoop?.day ?? null,
          whoopFetchedAt: whoop?.fetchedAt ?? null,
          nutritionToday: nut?.today ?? null,
          nutritionTargets: nut?.targets ?? null,
          healthLastSyncAt: useHealthStore.getState().lastSyncAt,
          whoopCsv: whoopCsv ? {
            imported: !!whoopCsv.imported,
            rowCount: whoopCsv.totalRowsIngested ?? null,
            windowDays: null,
          } : null,
          whoopFetchStatus: whoop?.status,
        });
      } catch { /* non-fatal */ }

      if (uid) {
        railwayCalled = true;
        const railway = await persistDurableToRailway(
          uid, days, nut?.today ?? null, nut?.historyDays ?? [], hiitWorkouts, trainingSessions, athleteStateSnapshot,
        );
        if (railway.ok) {
          if (railway.daysPushed > 0) railwayLines.push(`${railway.daysPushed} health days`);
          if (railway.nutritionDaysPushed > 0) railwayLines.push(`${railway.nutritionDaysPushed} nutrition days`);
          if (railway.hiitWorkoutsPushed > 0) railwayLines.push(`${railway.hiitWorkoutsPushed} HIIT sessions`);
          if (railway.sessionsPushed > 0) railwayLines.push(`${railway.sessionsPushed} training sessions`);
          if (railway.athleteStateSnapshotPushed) railwayLines.push('athlete-state snapshot');
        } else {
          railwayError = railway.error ?? 'Railway ingest returned error';
        }
      } else {
        railwayError = 'Sign in required for Railway primary save';
      }
    } catch (e: any) {
      railwayError = e?.message ?? 'Railway fan-out threw';
    }

    setSaving('supabase');
    const ok = await persistToBackend();
    const railwayStatus: 'saved' | 'empty' | 'error' =
      railwayError != null ? 'error'
        : railwayLines.length > 0 ? 'saved'
          : railwayCalled ? 'empty' : 'error';
    const railwaySummary =
      railwayStatus === 'saved' ? `Railway primary saved: ${railwayLines.join(', ')}`
        : railwayStatus === 'empty' ? 'Railway primary: nothing new to push'
          : `Railway primary error: ${railwayError ?? 'unknown'}`;

    if (ok) {
      const next = useHealthStore.getState();
      setPressResult({
        at: startedAt,
        railway: { status: railwayStatus, lines: railwayLines, error: railwayError ?? undefined },
        supabase: {
          ok: true,
          recordCount: next.lastPersistResult?.recordCount ?? 0,
          dateRange: next.lastPersistResult?.dateRange ?? '—',
        },
      });
      Alert.alert('Backend Sync', `${railwaySummary}\nSupabase mirror: ${next.lastPersistResult?.recordCount ?? 0} days (${next.lastPersistResult?.dateRange ?? '—'})`);
    } else {
      const err = useHealthStore.getState().error ?? 'Unknown error';
      setPressResult({
        at: startedAt,
        railway: { status: railwayStatus, lines: railwayLines, error: railwayError ?? undefined },
        supabase: { ok: false, error: err },
      });
      Alert.alert(
        'Backend Sync',
        `${railwaySummary}\n\n${railwayStatus === 'saved' ? 'Your data is durable on Railway.' : 'Primary path unavailable too — see the Railway error above.'} Supabase mirror is configured · source-state mirror is live · full per-day metric mirror is still pending.`,
      );
    }
    setSaving(false);
  }, [persistToBackend]);

  if (authStatus !== 'member') return null;

  if (!canPersist) {
    return (
      <View style={styles.sourceRow}>
        <Text style={styles.sourceName}>Backend sync</Text>
        <Text style={styles.sourceMeta}>Save health data to your account with the Starter plan.</Text>
      </View>
    );
  }

  const err = (pressResult && !pressResult.supabase.ok ? (pressResult.supabase.error ?? '') : (storeError ?? '')) ?? '';
  const isJwtError = /jwt|signing|unauthor|401/i.test(err);

  return (
    <View style={styles.sourceRow}>
      <View style={styles.sourceRowHeader}>
        <Text style={styles.sourceName}>Backend sync</Text>
        <Pressable
          style={[styles.rowBtn, styles.rowBtnPrimary, (saving || persisting) && { opacity: 0.6 }]}
          onPress={handlePress}
          disabled={!!saving || persisting}
          accessibilityRole="button"
          accessibilityLabel="Save long-term health data">
          {saving || persisting ? (
            <ActivityIndicator size="small" color="#0a0a0a" />
          ) : (
            <Text style={[styles.rowBtnText, styles.rowBtnTextPrimary]}>Save long-term data</Text>
          )}
        </Pressable>
      </View>
      <Text style={styles.sourceMeta}>
        {saving === 'railway'
          ? `Saving Railway primary · pushing ${nativeSourceLabel} days, nutrition, sessions…`
          : saving === 'supabase'
            ? 'Saving Supabase mirror…'
            : lastPersistedAt
              ? `Last saved ${formatLocalDateTime(lastPersistedAt)}${lastPersistResult ? ` · ${lastPersistResult.recordCount} days` : ''}`
              : `Push ${nativeSourceLabel} days, nutrition, sessions, and athlete-state snapshot.`}
      </Text>
      {pressResult?.railway.status === 'saved' && (
        <Text style={[styles.sourceMeta, { color: '#4ade80', opacity: 1 }]}>
          Railway saved: {pressResult.railway.lines.join(', ')}
        </Text>
      )}
      {pressResult?.railway.status === 'empty' && (
        <Text style={styles.sourceMeta}>Railway primary: nothing new to push.</Text>
      )}
      {pressResult?.railway.status === 'error' && (
        <Text style={[styles.sourceMeta, { color: '#ff6b6b', opacity: 1 }]}>
          Railway error: {pressResult.railway.error ?? 'unknown'}
        </Text>
      )}
      {pressResult?.supabase.ok && (
        <Text style={[styles.sourceMeta, { color: '#4ade80', opacity: 1 }]}>
          Supabase mirror saved: {pressResult.supabase.recordCount} day{pressResult.supabase.recordCount === 1 ? '' : 's'}.
        </Text>
      )}
      {pressResult && !pressResult.supabase.ok && (
        <Text style={[styles.sourceMeta, { color: pressResult.railway.status === 'error' ? '#ff6b6b' : '#d4e157', opacity: 1 }]}>
          {pressResult.railway.status === 'error' ? 'Supabase mirror also blocked.' : 'Supabase mirror pending; Railway primary remains durable.'}
        </Text>
      )}
      {isJwtError && (
        <Text style={[styles.sourceMeta, { color: '#d4e157', opacity: 1 }]}>
          Supabase JWT key needs attention. Sign out/in after the backend key is fixed, then save again.
        </Text>
      )}
    </View>
  );
}

interface SheetProps {
  visible: boolean;
  onClose: () => void;
  busy: string | null;
  appleHealthConnected: boolean;
  healthDays: number;
  healthLastSyncAt: string | null;
  whoopState: string;
  whoop: WhoopStatus | null;
  isWhoopConnected: boolean;
  onConnectAppleHealth: () => void | Promise<void>;
  onSyncAppleHealth: () => void | Promise<void>;
  onBackfillAppleHealth: () => void | Promise<void>;
  // Android Health Connect handlers — distinct from the iOS Apple
  // Health handlers above. Sheet picks per-platform inside appleRow.
  onConnectHealthConnect: () => void | Promise<void>;
  onSyncHealthConnect: () => void | Promise<void>;
  onCheckWhoopStatus: () => void | Promise<void>;
  onConnectWhoop: () => void | Promise<void>;
  onSyncWhoop: () => void | Promise<void>;
  onBackfillWhoop: () => void | Promise<void>;
  onDisconnectWhoop: () => void | Promise<void>;
}

function HealthSourceSheet(props: SheetProps) {
  const {
    visible, onClose, busy,
    appleHealthConnected, healthDays, healthLastSyncAt,
    whoopState, whoop, isWhoopConnected,
    onConnectAppleHealth, onSyncAppleHealth, onBackfillAppleHealth,
    onConnectHealthConnect, onSyncHealthConnect,
    onCheckWhoopStatus, onConnectWhoop, onSyncWhoop, onBackfillWhoop, onDisconnectWhoop,
  } = props;

  // Compute what goes in each section — the whole point of the sheet
  // is that these classifications are truthful.
  const appleHealthStatus: 'connected' | 'attention' | 'available' =
    appleHealthConnected ? 'connected' : 'available';
  const nativePermissions = useHealthStore((s) => s.permissions);
  const nativeAnyAuthorized =
    !!nativePermissions?.permissions &&
    Object.values(nativePermissions.permissions).some((p) => p === 'authorized');

  // "Partial" is only truthful when real required fields are missing
  // beyond the natural latest-cycle delay. WHOOP scores a cycle after
  // the next sleep — so a latest-day that is TODAY with missing
  // recovery/HRV/sleep is expected and should render as
  // Connected · awaiting latest cycle rather than amber "partial".
  //
  // We check the live WhoopDay (from /data/today bridge) in addition
  // to the backend /status payload because the two can disagree:
  // /status may say 'connected' while /data/today returns an empty
  // in-progress cycle for today. Either signal is enough to flag it.
  const todayYmd = (() => { const d = new Date(); const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,'0'); const da = String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${da}`; })();
  const whoopDayLive = useWhoopStore((s) => s.day);
  // Prefer the live-day date from the WHOOP store when it's newer
  // than the backend /status payload's latestDayDate. The /status
  // endpoint can cache its value for up to an hour while /data/today
  // returns the freshest cycle — so the modal used to show yesterday
  // even when today's cycle had already scored.
  const statusLatestDate = whoop?.latestDayDate ?? null;
  const liveDate = whoopDayLive?.date ?? null;
  const effectiveLatestDate = liveDate && (!statusLatestDate || liveDate > statusLatestDate)
    ? liveDate
    : statusLatestDate;
  const latestIsToday = effectiveLatestDate === todayYmd;
  // Cycle is only "awaiting" when today's day row exists but
  // recovery AND sleep are both null (WHOOP hasn't scored yet). If
  // recovery_score or sleep is present, today IS scored — do not
  // flag as awaiting.
  const liveCycleScoredEmpty = whoopDayLive != null
    && whoopDayLive.date === todayYmd
    && whoopDayLive.recovery_score == null
    && whoopDayLive.sleep_hours == null;
  const isAwaitingTodaysCycle =
    (whoopState === 'partial' && latestIsToday && (whoopDayLive?.recovery_score ?? null) == null) ||
    liveCycleScoredEmpty;

  const whoopStatusBucket: 'connected' | 'attention' | 'available' =
    whoopState === 'connected' ? 'connected'
    : isAwaitingTodaysCycle ? 'connected'
    : whoopState === 'partial' || whoopState === 'error' ? 'attention'
    : isWhoopConnected ? 'connected' : 'available';

  const ageLabel = (iso: string | null): string => {
    if (!iso) return 'never synced';
    const ms = Date.now() - new Date(iso).getTime();
    if (!Number.isFinite(ms) || ms < 0) return 'unknown';
    const m = Math.round(ms / 60_000);
    if (m < 1) return 'synced just now';
    if (m < 60) return `synced ${m}m ago`;
    const h = Math.round(m / 60);
    if (h < 24) return `synced ${h}h ago`;
    return `synced ${Math.round(h / 24)}d ago`;
  };

  const samsungHcHint = Platform.OS === 'android'
    ? ' If you use Samsung Health or Galaxy Watch, enable Samsung Health → Health Connect sharing, then grant Health Connect permissions here.'
    : '';
  const nativeHealthHubLabel = Platform.OS === 'ios' ? 'Apple Health / HealthKit hub data' : 'Health Connect hub data';
  const nativeHealthMeta = appleHealthConnected
    ? `${nativeHealthHubLabel} · ${healthDays} day${healthDays === 1 ? '' : 's'} · ${ageLabel(healthLastSyncAt)}${samsungHcHint}`
    : healthLastSyncAt
      ? `${nativeHealthHubLabel} · synced but no recent records found · ${ageLabel(healthLastSyncAt)}${samsungHcHint}`
      : nativeAnyAuthorized
        ? `${nativeHealthHubLabel} · permission granted, sync needed.${samsungHcHint}`
        : `${nativeHealthHubLabel} · not connected yet.${samsungHcHint}`;
  const nativeHealthStatusLabel = appleHealthConnected
    ? 'Connected'
    : healthLastSyncAt
      ? 'Connected — no data'
      : nativeAnyAuthorized
        ? 'Sync needed'
        : 'Not connected';
  const nativeHealthStatusColor = appleHealthConnected
    ? '#4ade80'
    : healthLastSyncAt || nativeAnyAuthorized
      ? '#d4e157'
      : '#888';

  // Stale detection — only when the freshest known date is more than
  // 2 days behind local today. WHOOP normally scores overnight, so
  // a 1-day lag is expected ("awaiting today's cycle" below). 2+ days
  // means the pipeline has stopped — worth flagging distinctly.
  const daysSinceLatest = (() => {
    if (!effectiveLatestDate) return null;
    const [y, m, d] = effectiveLatestDate.split('-').map((x) => Number(x));
    if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return null;
    const latestMs = new Date(y, (m ?? 1) - 1, d ?? 1).getTime();
    const now = new Date();
    const todayMs = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    return Math.round((todayMs - latestMs) / 86_400_000);
  })();
  const isStaleBeyondWindow = typeof daysSinceLatest === 'number' && daysSinceLatest >= 2;

  const whoopMeta = (() => {
    // WHOOP Direct is positioned as optional live calibration — not a
    // core requirement. Every meta string leads with that framing so
    // users don't read a non-connected WHOOP row as "broken".
    const optionalPrefix = 'Optional live calibration · ';
    if (whoopState === 'connected' || whoopState === 'partial') {
      const latest = effectiveLatestDate ? ` · latest ${effectiveLatestDate}` : '';
      const missing = Array.isArray((whoop as any)?.missingDomains) ? (whoop as any).missingDomains : [];
      const missStr = missing.length > 0 && !isAwaitingTodaysCycle && !isStaleBeyondWindow ? ` · missing ${missing.join(', ')}` : '';
      const head = isStaleBeyondWindow
        ? 'Stale'
        : isAwaitingTodaysCycle
          ? 'Connected · awaiting today\u2019s cycle'
          : whoopState === 'partial' ? 'Partial sync' : 'Connected';
      return `${optionalPrefix}${head}${latest}${missStr}`;
    }
    if (whoopState === 'config_missing') return 'Optional live calibration · setup required on the backend';
    if (whoopState === 'auth_required') return 'Optional live calibration · not connected';
    if (whoopState === 'error') return 'Optional live calibration · reconnect required (token expired)';
    if (whoopState === 'loading') return 'Optional live calibration · loading status…';
    return 'Optional live calibration';
  })();

  // Partition rows.
  const connected: Array<React.ReactElement> = [];
  const attention: Array<React.ReactElement> = [];
  const available: Array<React.ReactElement> = [];

  // Platform-aware native health row. iOS routes through the
  // Apple-Health-specific handlers (which call HealthKit native);
  // Android routes through the Health Connect handlers added above
  // (which call react-native-health-connect via the platform-aware
  // useHealthStore.requestPermissions / syncData paths). Without
  // this split, an Android tap on "Connect" was firing the iOS
  // handler and showing "iOS only" alerts.
  const isIos = Platform.OS === 'ios';
  const appleRow = (
    <SourceSheetRow
      key="apple"
      name={isIos ? 'Apple Health / HealthKit' : 'Health Connect'}
      status={nativeHealthStatusLabel}
      statusColor={nativeHealthStatusColor}
      meta={nativeHealthMeta}
      actions={appleHealthConnected || healthLastSyncAt || nativeAnyAuthorized ? (isIos ? [
        {
          label: busy === 'apple-sync' ? 'Syncing…' : 'Sync',
          onPress: onSyncAppleHealth,
          disabled: busy != null,
          kind: 'primary',
        },
        {
          label: busy === 'apple-backfill' ? 'Enriching…' : 'Enrich history',
          onPress: onBackfillAppleHealth,
          disabled: busy != null,
          kind: 'secondary',
        },
        {
          label: 'Open Health settings',
          onPress: () => { Linking.openURL('x-apple-health://').catch(() => Linking.openSettings()); },
          disabled: busy != null,
          kind: 'secondary',
        },
      ] : [
        // Android — Health Connect connected actions.
        {
          label: busy === 'hc-sync' ? 'Syncing…' : 'Sync',
          onPress: onSyncHealthConnect,
          disabled: busy != null,
          kind: 'primary',
        },
        {
          label: 'Open Health Connect settings',
          onPress: () => { Linking.openSettings().catch(() => { /* no-op */ }); },
          disabled: busy != null,
          kind: 'secondary',
        },
      ]) : [
        {
          label: isIos
            ? (busy === 'apple-connect' ? 'Connecting…' : 'Connect')
            : (busy === 'hc-connect' ? 'Connecting…' : 'Connect'),
          onPress: isIos ? onConnectAppleHealth : onConnectHealthConnect,
          disabled: busy != null,
          kind: 'primary',
        },
      ]}
    />
  );

  const whoopRow = (
    <SourceSheetRow
      key="whoop"
      name="WHOOP Direct"
      status={
        isStaleBeyondWindow ? 'Stale'
        : whoopState === 'connected' ? 'Connected'
        : isAwaitingTodaysCycle ? 'Awaiting cycle'
        : whoopState === 'partial' ? 'Partial'
        : whoopState === 'error' ? 'Reconnect required'
        : whoopState === 'config_missing' ? 'Setup required'
        : whoopState === 'auth_required' ? 'Not connected'
        : 'Unknown'
      }
      statusColor={
        whoopState === 'connected' ? '#4ade80'
        : isAwaitingTodaysCycle ? '#4ade80'
        : whoopState === 'partial' ? '#ffa500'
        : whoopState === 'error' ? '#ff6b6b'
        : '#888'
      }
      meta={whoopMeta}
      actions={isWhoopConnected ? [
        // Connected state: only Sync + Disconnect are primary-facing.
        // Enrich history is secondary (optional deeper pull). No
        // "Check status" or "Connect" buttons — they confused users
        // who were already connected.
        {
          label: busy === 'whoop-sync' ? 'Syncing…' : 'Sync',
          onPress: onSyncWhoop,
          disabled: busy != null,
          kind: 'primary',
        },
        {
          label: busy === 'whoop-backfill' ? 'Enriching…' : 'Enrich history',
          onPress: onBackfillWhoop,
          disabled: busy != null,
          kind: 'secondary',
        },
        {
          label: busy === 'whoop-disconnect' ? 'Disconnecting…' : 'Disconnect',
          onPress: onDisconnectWhoop,
          disabled: busy != null,
          kind: 'danger',
        },
      ] : [
        // Not connected yet. Show Check status only when backend says
        // nothing — avoids asking for a redundant status probe when we
        // already know auth is required / config is missing.
        {
          label: busy === 'whoop-status' ? 'Checking…' : 'Check status',
          onPress: onCheckWhoopStatus,
          disabled: busy != null,
          kind: 'secondary',
          hidden: whoopState === 'config_missing' || whoopState === 'auth_required' || whoopState === 'error',
        },
        {
          label: busy === 'whoop-connect' ? 'Opening…' : (whoopState === 'error' ? 'Reconnect' : 'Connect'),
          onPress: onConnectWhoop,
          disabled: busy != null,
          kind: 'primary',
        },
      ]}
    />
  );

  if (appleHealthStatus === 'connected') connected.push(appleRow); else available.push(appleRow);
  if (whoopStatusBucket === 'connected') connected.push(whoopRow);
  else if (whoopStatusBucket === 'attention') attention.push(whoopRow);
  else available.push(whoopRow);

  // WHOOP CSV enrichment row — optional manual upload for deep
  // history + zones + richer analysis. Appears in "Connected" when
  // ever imported, otherwise in "Available to connect" with honest
  // "optional · not required" framing.
  const whoopCsvRow = <WhoopCsvRow key="whoop_csv" />;
  // Positioned below the WHOOP Direct row visually by pushing last
  // into each section.
  // `WhoopCsvRow` computes its own status via fetch; it renders into
  // connected or available based on its own hook state. To keep the
  // sheet's section partitioning deterministic we always place it in
  // "Available" here and let the row itself show the imported meta
  // line when appropriate — cleaner than passing a loading-state up
  // through this render function.
  available.push(whoopCsvRow);

  // Polar export historical training context (paste-only, repo-safe).
  // Sister of WhoopCsvRow but Polar-specific — parses Polar Flow CSV
  // or TCX and imports as historical training context only. Not a
  // recovery/readiness source.
  available.push(<PolarExportRow key="polar_export" />);
  available.push(<BackendSyncRow key="backend_sync" />);

  // Lightweight pointer for session-owned hardware so Bluetooth
  // capture stays anchored to the Train tab.
  available.push(
    <View key="others" style={styles.sourceRow}>
      <Text style={styles.sourceName}>Training hardware</Text>
      <Text style={styles.sourceMeta}>
        Bluetooth heart-rate straps and FTMS bikes/rowers/ski-ergs live on the Train tab so they pair as part of a session.
      </Text>
    </View>,
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.sheetOverlay}>
        <View style={styles.sheet}>
          <View style={styles.sheetHeaderRow}>
            <Text style={styles.sheetTitle}>Health connections</Text>
            <Pressable onPress={onClose} hitSlop={10} accessibilityRole="button" accessibilityLabel="Close">
              <Text style={styles.sheetClose}>Done</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.sheetScroll}>
            {Platform.OS === 'android' && (
              <View style={styles.sheetInlineCard}>
                <HealthConnectAvailabilityHint />
              </View>
            )}
            {connected.length > 0 && (
              <>
                <Text style={styles.sheetSectionHeader}>Connected</Text>
                {connected}
              </>
            )}
            {attention.length > 0 && (
              <>
                <Text style={[styles.sheetSectionHeader, { color: '#ffa500', opacity: 1 }]}>Attention needed</Text>
                {attention}
              </>
            )}
            {available.length > 0 && (
              <>
                <Text style={styles.sheetSectionHeader}>Available to connect</Text>
                {available}
                <View style={styles.sheetInlineCard}>
                  <SafeErrorBoundary label="Polar Direct card">
                    <PolarDirectCard />
                  </SafeErrorBoundary>
                </View>
              </>
            )}
          </ScrollView>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

interface SourceAction {
  label: string;
  onPress: () => void | Promise<void>;
  disabled?: boolean;
  kind: 'primary' | 'secondary' | 'danger';
  hidden?: boolean;
}

/**
 * WHOOP CSV — optional manual enrichment row. Always renders inside
 * the "Available to connect" section; the meta line changes once
 * something's been imported (e.g. "3,421 days imported · 2019-03 →
 * 2026-04 · last import 2d ago"). Tapping Import opens a paste-CSV
 * modal (works today without a new native build). A future build
 * with expo-document-picker can replace the modal with a real file
 * picker without touching the backend.
 */
/**
 * Lightweight content-based classification of a pasted CSV blob.
 * Mirrors the server's `classifyCsvContent` so the UI can show the
 * detected type immediately after paste, without waiting for upload.
 */
function classifyPastedCsv(name: string, text: string): 'recoveries' | 'sleeps' | 'workouts' | 'cycles' | 'journal' | 'unknown' {
  const base = (name ?? '').toLowerCase();
  if (base.includes('recover')) return 'recoveries';
  if (base.includes('sleep')) return 'sleeps';
  if (base.includes('workout') || base.includes('activity')) return 'workouts';
  if (base.includes('cycle') || base.includes('physiological')) return 'cycles';
  if (base.includes('journal')) return 'journal';
  const firstLine = (text.split(/\r?\n/, 1)[0] ?? '').toLowerCase();
  const has = (s: string) => firstLine.includes(s);
  if (has('recovery score')) return 'recoveries';
  if (has('asleep duration') || has('rem sleep') || has('sleep performance')) return 'sleeps';
  if (has('activity strain') || has('activity name') || has('workout type')) return 'workouts';
  if (has('day strain') || has('daily strain')) return 'cycles';
  if (has('journal')) return 'journal';
  return 'unknown';
}

interface PastedFile {
  id: string;
  name: string; // user-editable; prefilled from detection
  text: string;
  kind: ReturnType<typeof classifyPastedCsv>;
  /** Estimated data rows (lines - 1), just for the UI summary. */
  rowsEstimate: number;
}

function WhoopCsvRow() {
  return (
    <SafeErrorBoundary label="WHOOP import">
      <WhoopCsvRowInner />
    </SafeErrorBoundary>
  );
}

function WhoopCsvRowInner() {
  const userId = useAuthStore((s) => s.user?.id);
  const accessToken = useAuthStore((s) => s.session?.access_token);
  const cfg = useMemo(() => {
    try {
      const build = IntegrationsClient.buildIntegrationConfig;
      return typeof build === 'function' ? build(userId, accessToken) : null;
    } catch { return null; }
  }, [userId, accessToken]);
  const [status, setStatus] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [files, setFiles] = useState<PastedFile[]>([]);
  const [draftText, setDraftText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!cfg) return;
    try {
      const res = await getWhoopCsvStatus(cfg);
      if (res.ok) {
        setStatus(res.data);
        const rows = (res.data as any)?.totalRowsIngested ?? 0;
        const importedNow = (res.data as any)?.status === 'imported' && rows > 0;
        // Cache locally so SuggestedMetricsCard + other surfaces can
        // read the last-known import state without a network call.
        void writeStoredJson(WHOOP_CSV_CACHE_KEY, {
          imported: importedNow,
          totalRowsIngested: rows,
          updatedAt: new Date().toISOString(),
        } satisfies WhoopCsvCache).catch(() => {});
      }
    } catch { /* non-fatal */ }
  }, [cfg]);

  useEffect(() => {
    // Hydrate from cache first so the row can render imported/not
    // instantly on open, then refresh from the network.
    void (async () => {
      try {
        const cached = await readStoredJson<WhoopCsvCache>(WHOOP_CSV_CACHE_KEY);
        if (cached && cached.imported) {
          setStatus((prev: any) => prev ?? { status: 'imported', totalRowsIngested: cached.totalRowsIngested ?? 0 });
        }
      } catch { /* non-fatal */ }
      void refresh();
    })();
  }, [refresh]);

  const imported = status?.status === 'imported' && (status.totalRowsIngested ?? 0) > 0;
  const windowStart = status?.earliestDate;
  const windowEnd = status?.latestDate;
  const lastImportAt = status?.lastImportAt;
  const meta = imported
    ? `Historical WHOOP backfill · ${status.totalRowsIngested} day${status.totalRowsIngested === 1 ? '' : 's'} · ${windowStart ?? '—'} → ${windowEnd ?? '—'}${lastImportAt ? ` · last import ${new Date(lastImportAt).toLocaleDateString()}` : ''}`
    : 'Historical WHOOP backfill · optional · not required for normal sync';

  const addDraftFile = useCallback(() => {
    try {
      const text = draftText.trim();
      if (text.length === 0) {
        Alert.alert('No file selected', 'Paste CSV content first, or use the .zip picker above.');
        return;
      }
      // Hard cap: WHOOP single-domain CSVs are typically <2MB. Above
      // 2MB the paste path is unreliable on iOS UITextView and the
      // upload payload becomes huge; steer the user to the .zip path.
      if (text.length > 2 * 1024 * 1024) {
        Alert.alert(
          'Pasted CSV too large',
          'This paste is over 2 MB. Use the “Upload WHOOP CSV/zip” button above instead — the zip path handles full exports without freezing.',
        );
        return;
      }
      const kind = classifyPastedCsv('', text);
      const defaultName = kind === 'unknown' ? `file_${files.length + 1}.csv` : `${kind}.csv`;
      // Cap row-counting cost: above 256KB we estimate from byte size
      // (avg WHOOP row ~120 bytes) instead of splitting the full string.
      let rowsEstimate = 0;
      try {
        if (text.length <= 256 * 1024) {
          rowsEstimate = Math.max(0, text.split(/\r?\n/).filter((l) => l.length > 0).length - 1);
        } else {
          rowsEstimate = Math.max(0, Math.floor(text.length / 120) - 1);
        }
      } catch { rowsEstimate = 0; }
      setFiles((prev) => [
        ...prev,
        { id: `f_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, name: defaultName, text, kind, rowsEstimate },
      ]);
      setDraftText('');
    } catch (e: any) {
      Alert.alert('Couldn’t read file', e?.message ?? 'Try a smaller paste, or use the .zip picker above.');
    }
  }, [draftText, files.length]);

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const renameFile = useCallback((id: string, nextName: string) => {
    setFiles((prev) => prev.map((f) => {
      if (f.id !== id) return f;
      const kind = classifyPastedCsv(nextName, f.text);
      return { ...f, name: nextName, kind };
    }));
  }, []);

  const onImport = useCallback(async () => {
    if (!cfg) { Alert.alert('WHOOP CSV', 'Sign in first.'); return; }
    if (uploading) return;
    if (files.length === 0) {
      Alert.alert('WHOOP CSV', 'Add at least one CSV before uploading. Tap “+ Add file”.');
      return;
    }
    setUploading(true);
    try {
      const payload: Record<string, string> = {};
      for (const f of files) {
        // Guard against accidental duplicate filenames (user renamed two
        // blocks the same thing) by appending a suffix.
        let name = f.name.trim().length > 0 ? f.name.trim() : `${f.kind}.csv`;
        if (payload[name]) name = `${name.replace(/\.csv$/, '')}_${f.id.slice(-4)}.csv`;
        payload[name] = f.text;
      }
      // Token-presence diagnostics — never log the value. We log only:
      //   tokenLen     — non-zero proves the EAS env reached the bundle
      //   athleteIdLen — non-zero proves auth resolved
      //   endpoint     — confirms we're hitting the right host
      whoopTrace('paste_import_start', `tokenLen=${cfg.token?.length ?? 0} athleteIdLen=${cfg.athleteId?.length ?? 0} hasJwt=${!!cfg.supabaseAccessToken} base=${(cfg.baseUrl || '').replace(/^https?:\/\//, '')}`);
      const res = await uploadWhoopCsv(cfg, payload);
      whoopTrace('paste_import_done', `ok=${!!res.ok}`);
      if (!res.ok) {
        const raw = res.error ?? '';
        // Compact, non-scary copy. Detect 403/Forbidden specifically
        // because that's the symptom when an OTA bundled without the
        // EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN env (mobile sends an empty
        // header → backend rejects). Stash the raw blob in lastResult
        // so the diagnostics line still surfaces it for support.
        const isForbidden = /forbidden/i.test(raw) || /\b403\b/.test(raw);
        const friendly = isForbidden
          ? 'App auth did not match the backend. Reopen the app to refresh, then try again.'
          : 'Upload failed — backend rejected this request. Try again.';
        const diag = isForbidden ? 'Import endpoint returned 403.' : (raw ? raw.slice(0, 60) : 'unknown');
        setLastResult(`Upload failed: ${diag}`);
        Alert.alert(isForbidden ? 'Upload blocked' : 'Upload failed — try again', friendly);
        return;
      }
      const d = res.data as any;
      if (d?.skippedReason === 'duplicate-upload') {
        setLastResult('Same bundle already imported — nothing to do.');
        Alert.alert('WHOOP CSV', 'Same bundle already imported — nothing to do.');
      } else {
        const detected: Array<{ name: string; kind: string; rowCount: number }> = Array.isArray(d?.filesDetected) ? d.filesDetected : [];
        const skipped: Array<{ name: string; reason: string }> = Array.isArray(d?.filesSkipped) ? d.filesSkipped : [];
        const detectedLine = detected
          .filter((x) => x.kind !== 'unknown')
          .map((x) => `${x.kind} (${x.rowCount})`)
          .join(', ') || 'none recognised';
        const skippedLine = skipped.length > 0
          ? `\nSkipped: ${skipped.map((s) => `${s.name} — ${s.reason}`).join('; ')}`
          : '';
        const summary = `Imported as historical WHOOP context: ${detectedLine}\n${d.rowsNew} new day${d.rowsNew === 1 ? '' : 's'} · ${d.windowStart ?? '—'} → ${d.windowEnd ?? '—'}\nDomains: ${(d.domainsFilled ?? []).join(', ') || 'none'}${skippedLine}`;
        setLastResult(summary);
        Alert.alert('WHOOP history imported', summary);
        setFiles([]);
        setDraftText('');
        setModalOpen(false);
      }
      try { await refresh(); } catch { /* refresh failure non-fatal */ }
    } catch (e: any) {
      // Defensive: any sync throw or unhandled rejection above must
      // not propagate to the React event handler. Show compact copy.
      Alert.alert('Couldn’t parse this WHOOP export', e?.message ?? 'Unknown error.');
    } finally {
      setUploading(false);
    }
  }, [cfg, files, refresh, uploading]);

  return (
    <View style={styles.sourceRow}>
      <View style={styles.sourceRowHeader}>
        <Text style={styles.sourceName}>WHOOP export enrichment</Text>
        <View style={[styles.sourceChip, { borderColor: imported ? '#4ade80' : '#888' }]}>
          <Text style={[styles.sourceChipText, { color: imported ? '#4ade80' : '#888' }]}>
            {imported ? 'Imported' : 'Optional'}
          </Text>
        </View>
      </View>
      <Text style={styles.sourceMeta}>{meta}</Text>
      <Text style={[styles.sourceMeta, { opacity: 0.4 }]}>
        Historical WHOOP data for Readiness context. Imported as evidence — not live WHOOP Recovery. Optional: adds years of history + workouts + cycles + zones for richer context.
      </Text>
      {lastResult && (
        <Text style={[styles.sourceMeta, { color: '#4ade80' }]}>{lastResult}</Text>
      )}
      <Pressable
        onPress={async () => {
          try {
            const trace = (await readStoredJson<WhoopUploadTrace[]>(WHOOP_UPLOAD_TRACE_KEY)) ?? [];
            if (trace.length === 0) {
              Alert.alert('Upload trace', 'No trace yet. Tap “Upload WHOOP CSV/zip” first.');
              return;
            }
            const lines = trace
              .slice(-15)
              .map((t) => `${t.at.slice(11, 19)}  ${t.step}${t.detail ? ` · ${t.detail}` : ''}`)
              .join('\n');
            Alert.alert(`Upload trace (${trace.length})`, lines);
          } catch (e: any) {
            Alert.alert('Upload trace', e?.message ?? 'Could not read trace.');
          }
        }}
        hitSlop={6}>
        <Text style={[styles.sourceMeta, { opacity: 0.55, textDecorationLine: 'underline' }]}>
          Show last upload trace
        </Text>
      </Pressable>
      <View style={styles.rowActions}>
        <Pressable
          style={[styles.rowBtn, styles.rowBtnPrimary]}
          onPress={() => {
            try { setModalOpen(true); }
            catch (e: any) {
              Alert.alert('Could not open import sheet', e?.message ?? 'Reopen the app and try again.');
            }
          }}
          accessibilityRole="button"
          accessibilityLabel="Upload WHOOP CSV/zip">
          <Text style={[styles.rowBtnText, styles.rowBtnTextPrimary]}>
            {imported ? 'Import more WHOOP history' : 'Upload WHOOP CSV/zip'}
          </Text>
        </Pressable>
        {imported && cfg && (
          <Pressable
            style={[styles.rowBtn]}
            onPress={() => {
              Alert.alert(
                'Clear imported WHOOP export?',
                'Removes all CSV-ingested rows so you can re-import from scratch. WHOOP Direct API data is unaffected.',
                [
                  { text: 'Cancel', style: 'cancel' },
                  {
                    text: 'Clear imports',
                    style: 'destructive',
                    onPress: async () => {
                      try {
                        const res = await clearWhoopCsv(cfg);
                        if (res.ok) {
                          setLastResult('Cleared all WHOOP CSV imports.');
                          setStatus(null);
                          try { await writeStoredJson(WHOOP_CSV_CACHE_KEY, { imported: false, updatedAt: new Date().toISOString() } satisfies WhoopCsvCache); } catch { /* ignore */ }
                          await refresh();
                        } else {
                          Alert.alert('Clear failed', res.error ?? 'Unknown error.');
                        }
                      } catch (e: any) {
                        Alert.alert('Clear failed', e?.message ?? 'unknown');
                      }
                    },
                  },
                ],
              );
            }}
            accessibilityRole="button"
            accessibilityLabel="Clear WHOOP CSV imports">
            <Text style={styles.rowBtnText}>Clear imports</Text>
          </Pressable>
        )}
      </View>

      <Modal
        visible={modalOpen}
        transparent
        animationType="slide"
        onRequestClose={() => setModalOpen(false)}>
        <SafeAreaView style={styles.sheetOverlay}>
          <View style={styles.sheet}>
            <View style={styles.sheetHeaderRow}>
              <Text style={styles.sheetTitle}>Import WHOOP export · v3</Text>
              <Pressable onPress={() => setModalOpen(false)} hitSlop={10}>
                <Text style={styles.sheetClose}>Cancel</Text>
              </Pressable>
            </View>
            <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
              <Text style={styles.sourceMeta}>
                {'WHOOP app → Settings → Your Data → Export Data → download the zip → unzip on your phone (Files app) → open one CSV at a time → Select All → Copy → come back here and paste. The .zip picker is temporarily disabled (native crash on the current build); the next EAS build will re-enable it. Supported domains auto-detected: recoveries, sleeps, workouts, cycles. Optional · historical context for Readiness · not required for normal sync.'}
              </Text>

              {!ENABLE_WHOOP_FILE_PICKER && (
                <Text style={[styles.sourceMeta, { color: '#d4e157', textAlign: 'center' }]}>
                  File picker temporarily disabled in this build. Paste WHOOP CSV content below.
                </Text>
              )}

              {/* Native picker path. Flag-gated so the crashable
                  invocation cannot reach getDocumentAsync at all when
                  ENABLE_WHOOP_FILE_PICKER is false. The handler ALSO
                  re-checks the flag as a defense in depth — if the
                  Pressable somehow rendered (e.g. flag toggled mid-
                  session) the press still bails before any native
                  call. */}
              {ENABLE_WHOOP_FILE_PICKER && (
              <Pressable
                style={[styles.rowBtn, styles.rowBtnPrimary, { alignSelf: 'stretch' }]}
                onPress={async () => {
                  whoopTrace('btn_pressed');
                  if (!ENABLE_WHOOP_FILE_PICKER) {
                    whoopTrace('picker_flag_off');
                    Alert.alert('File picker disabled', 'Use the paste path below.');
                    return;
                  }
                  if (!cfg) { Alert.alert('WHOOP export', 'Sign in first.'); return; }
                  if (uploading) return; // re-tap guard
                  let picker: any = null;
                  let fs: any = null;
                  try { picker = require('expo-document-picker'); } catch (e: any) { whoopTrace('require_picker_failed', e?.message); picker = null; }
                  // SDK 54 moved the file-system legacy API to a
                  // sub-module. Prefer legacy (stable readAsStringAsync
                  // + getInfoAsync + EncodingType), fall back to the
                  // new module, then to null. Null → bail cleanly.
                  try { fs = require('expo-file-system/legacy'); } catch (e: any) { whoopTrace('require_fs_legacy_failed', e?.message); /* fall through */ }
                  if (!fs || typeof fs.readAsStringAsync !== 'function') {
                    try { fs = require('expo-file-system'); } catch (e: any) { whoopTrace('require_fs_failed', e?.message); fs = null; }
                  }
                  if (!picker || typeof picker.getDocumentAsync !== 'function' || !fs || typeof fs.readAsStringAsync !== 'function') {
                    whoopTrace('module_unavailable', `picker=${!!picker} fs=${!!fs}`);
                    Alert.alert(
                      'Zip upload not available on this build',
                      'The document picker or file reader isn\u2019t available in this build. Use the paste-per-file fallback below, or wait for the next TestFlight build.',
                    );
                    return;
                  }
                  // try/finally guarantees the uploading flag always
                  // clears, even on OOM or silent throws — previously
                  // a crash mid-upload would leave the button stuck.
                  try {
                    let res: any;
                    try {
                      whoopTrace('picker_open');
                      res = await picker.getDocumentAsync({
                        type: ['application/zip', 'application/x-zip-compressed', 'application/octet-stream', '*/*'],
                        copyToCacheDirectory: true,
                        multiple: false,
                      });
                      whoopTrace('picker_returned', `keys=${res ? Object.keys(res).join(',') : 'null'}`);
                    } catch (pickErr: any) {
                      // Picker launch itself threw (rare iOS scoped-
                      // URI case, permission deny). Alert + bail so
                      // button unsticks in finally.
                      whoopTrace('picker_threw', pickErr?.message);
                      Alert.alert('File picker error', pickErr?.message ?? 'Could not open the file picker.');
                      return;
                    }
                    const norm = normalizePickedWhoopFile(res);
                    if (norm.canceled) { whoopTrace('picker_canceled'); return; }
                    if (!norm.ok) {
                      whoopTrace('picker_invalid', norm.error);
                      const msg = norm.error === 'no_assets' ? 'No file was returned from the picker. Try again.'
                        : norm.error === 'no_uri' ? 'The picker returned a file with no readable path. Try copying it to Files first, then re-pick.'
                        : 'No file selected.';
                      Alert.alert(norm.error === 'no_uri' ? 'Couldn’t access selected file' : 'No file selected', msg);
                      return;
                    }
                    const uri = norm.uri!;
                    const name = norm.name ?? '';
                    const mimeType = norm.mimeType ?? '';
                    whoopTrace('picker_ok', `name=${name.slice(0, 40)} mime=${mimeType.slice(0, 40)} size=${norm.size ?? 'unknown'} scheme=${uri.split(':')[0]}`);
                    // Allow .zip or anything that looks like a zip MIME.
                    // Reject individual .csv explicitly with a useful
                    // pointer toward the paste-fallback path.
                    if (/\.csv$/i.test(name) || /text\/csv/i.test(mimeType)) {
                      Alert.alert('Pick the .zip, not a single CSV', 'Select the whole WHOOP export .zip. For a single CSV, use the paste-per-file path below.');
                      return;
                    }
                    if (!/\.zip$/i.test(name) && mimeType && !/zip/i.test(mimeType)) {
                      Alert.alert('Upload WHOOP CSV or zip export', `${name || 'File'} is not a WHOOP export zip.`);
                      return;
                    }
                    // Size guard: reading a huge file as base64 (which
                    // triples memory use) was the main crash vector.
                    // WHOOP exports are typically 5-30MB. Reject above
                    // 80MB with a clear message rather than OOMing.
                    let sizeBytes: number | null = norm.size ?? null;
                    try {
                      if (sizeBytes == null && typeof fs.getInfoAsync === 'function') {
                        const info = await fs.getInfoAsync(uri, { size: true });
                        if (info?.exists && typeof info.size === 'number') sizeBytes = info.size;
                      }
                    } catch (e: any) { whoopTrace('size_probe_failed', e?.message); }
                    whoopTrace('size_known', sizeBytes != null ? `${sizeBytes}` : 'null');
                    if (sizeBytes != null && sizeBytes > 80 * 1024 * 1024) {
                      Alert.alert(
                        'Zip too large',
                        `File is ${(sizeBytes / (1024 * 1024)).toFixed(1)} MB. Maximum supported is 80 MB. Export a shorter window from WHOOP (12-month blocks work best).`,
                      );
                      return;
                    }
                    setUploading(true);
                    whoopTrace('read_start');
                    // Read as base64. Large but bounded by the 80MB
                    // guard above. Still the most compatible path for
                    // the current backend route (takes `zipBase64`).
                    // Accept any encoding shape the installed
                    // expo-file-system version exposes (enum member,
                    // plain string, or missing).
                    const base64Encoding = fs.EncodingType?.Base64 ?? fs.EncodingType?.base64 ?? 'base64';
                    let base64: string | null = null;
                    try {
                      const raw = await fs.readAsStringAsync(uri, { encoding: base64Encoding });
                      base64 = typeof raw === 'string' ? raw : null;
                      whoopTrace('read_done', `b64_len=${base64?.length ?? 0}`);
                    } catch (readErr: any) {
                      whoopTrace('read_failed', readErr?.message);
                      Alert.alert('Couldn’t read file', readErr?.message ?? 'The file system refused to read this file. Try copying it to Files first, then re-pick.');
                      return;
                    }
                    if (!base64 || base64.length === 0) {
                      Alert.alert('Couldn’t parse this WHOOP export', 'The zip came back empty. Try re-exporting from WHOOP.');
                      return;
                    }
                    let upResp: any;
                    try {
                      whoopTrace('upload_start');
                      upResp = await uploadWhoopZip(cfg, base64);
                      whoopTrace('upload_done', `ok=${!!upResp?.ok}`);
                    } catch (upErr: any) {
                      whoopTrace('upload_threw', upErr?.message);
                      Alert.alert('Upload failed — try again', upErr?.message ?? 'Network error.');
                      return;
                    }
                    if (!upResp || !upResp.ok) {
                      const err = upResp?.error ?? 'Unknown error';
                      const aborted = /aborted|network\s+error|timeout/i.test(err);
                      Alert.alert(
                        aborted ? 'Upload timed out — try again' : 'Upload failed — try again',
                        aborted
                          ? `The upload didn't complete (${err}). Try again on Wi-Fi, or re-export a smaller window from WHOOP.`
                          : (err === 'Unknown error' ? 'Backend route may not be deployed yet.' : err),
                      );
                      return;
                    }
                    const d = upResp.data as any;
                    const detected: Array<{ name: string; kind: string; rowCount: number }> = Array.isArray(d?.filesDetected) ? d.filesDetected : [];
                    const skipped: Array<{ name: string; reason: string }> = Array.isArray(d?.filesSkipped) ? d.filesSkipped : [];
                    const detectedLine = detected.filter((x) => x.kind !== 'unknown').map((x) => `${x.kind} (${x.rowCount})`).join(', ') || 'none recognised';
                    const skippedLine = skipped.length > 0 ? `\nSkipped: ${skipped.map((s) => `${s.name} — ${s.reason}`).join('; ')}` : '';
                    const summary = `Imported as historical WHOOP context for Readiness:\nZip extracted ${d.zipFilesExtracted ?? '?'} CSV${(d.zipFilesExtracted ?? 0) === 1 ? '' : 's'}\n${detectedLine}\n${d.rowsNew} new day${d.rowsNew === 1 ? '' : 's'} · ${d.windowStart ?? '—'} → ${d.windowEnd ?? '—'}\nDomains: ${(d.domainsFilled ?? []).join(', ') || 'none'}${skippedLine}`;
                    setLastResult(summary);
                    Alert.alert('WHOOP history synced', summary);
                    try { await writeStoredJson(WHOOP_CSV_CACHE_KEY, { imported: (d.rowsNew ?? 0) > 0 || !!d.windowEnd, totalRowsIngested: d.rowsNew ?? 0, updatedAt: new Date().toISOString() } satisfies WhoopCsvCache); } catch { /* ignore */ }
                    setModalOpen(false);
                    await refresh();
                  } catch (e: any) {
                    whoopTrace('outer_catch', e?.message);
                    Alert.alert('Zip upload failed', e?.message ?? 'Unknown error reading or uploading the zip.');
                  } finally {
                    setUploading(false);
                    whoopTrace('flow_end');
                  }
                }}
                disabled={uploading}
                accessibilityRole="button"
                accessibilityLabel="Pick WHOOP export zip">
                <Text style={[styles.rowBtnText, styles.rowBtnTextPrimary]}>
                  {uploading ? 'Uploading · don\u2019t close the app…' : 'Upload WHOOP CSV/zip'}
                </Text>
              </Pressable>
              )}
              {uploading && (
                <Text style={[styles.sourceMeta, { color: '#d4e157', textAlign: 'center' }]}>
                  WHOOP exports can take 30-90s to transfer + extract on mobile. Keep the app in the foreground.
                </Text>
              )}

              <Text style={[styles.sheetSectionHeader, { textAlign: 'center' }]}>Paste WHOOP CSVs one at a time</Text>

              {files.length > 0 && (
                <View style={{ gap: 6 }}>
                  <Text style={styles.sheetSectionHeader}>Files to import ({files.length})</Text>
                  {files.map((f) => (
                    <View key={f.id} style={styles.fileRow}>
                      <View style={{ flex: 1, gap: 2 }}>
                        <TextInput
                          style={styles.fileName}
                          value={f.name}
                          onChangeText={(t) => renameFile(f.id, t)}
                          autoCorrect={false}
                          autoCapitalize="none"
                        />
                        <Text style={styles.sourceMeta}>
                          detected: {f.kind === 'unknown' ? 'unrecognised (will be skipped server-side)' : f.kind} · ~{f.rowsEstimate} rows
                        </Text>
                      </View>
                      <Pressable hitSlop={10} onPress={() => removeFile(f.id)}>
                        <Text style={{ color: '#ff6b6b', fontSize: 12, fontWeight: '700' }}>Remove</Text>
                      </Pressable>
                    </View>
                  ))}
                </View>
              )}

              <Text style={styles.sheetSectionHeader}>Paste CSV content</Text>
              <TextInput
                style={styles.csvInput}
                placeholder="Cycle end time,Recovery score %,HRV (ms),..."
                placeholderTextColor="#555"
                multiline
                value={draftText}
                onChangeText={(t) => {
                  // Hard backstop on TextInput content — iOS
                  // UITextView is unstable past ~2MB on multiline
                  // paste; lower the cap and steer to the .zip path
                  // for anything larger. The 8MB earlier cap was
                  // generous enough that paste-induced layout could
                  // still freeze the JS thread before the cap kicked
                  // in.
                  if (typeof t === 'string' && t.length > 2 * 1024 * 1024) {
                    setDraftText(t.slice(0, 2 * 1024 * 1024));
                    return;
                  }
                  setDraftText(t);
                }}
                maxLength={2 * 1024 * 1024}
                autoCorrect={false}
                autoCapitalize="none"
              />
              {draftText.length > 0 && (
                <Text style={styles.sourceMeta}>
                  {(() => {
                    // Bound the per-keystroke cost: classify only the
                    // first 4KB (header + a few rows) and skip the live
                    // row-count for huge pastes — splitting a multi-MB
                    // string on every keystroke is what crashes the JS
                    // thread when the user pastes a real WHOOP CSV.
                    const head = draftText.slice(0, 4096);
                    const detected = classifyPastedCsv('', head);
                    const HUGE = draftText.length > 256 * 1024;
                    const rows = HUGE
                      ? '~ many'
                      : `~${Math.max(0, draftText.split(/\r?\n/).filter((l) => l.length > 0).length - 1)}`;
                    return `Detected: ${detected} · ${rows} rows${HUGE ? ' (large paste — prefer .zip path above)' : ''}`;
                  })()}
                </Text>
              )}
              <Pressable
                style={[styles.rowBtn, styles.rowBtnPrimary, { alignSelf: 'stretch', opacity: draftText.trim().length === 0 ? 0.5 : 1 }]}
                disabled={draftText.trim().length === 0}
                onPress={() => {
                  if (draftText.trim().length === 0) return;
                  addDraftFile();
                }}>
                <Text style={[styles.rowBtnText, styles.rowBtnTextPrimary]}>
                  {draftText.trim().length === 0 ? '+ Add file (paste CSV above first)' : '+ Add file to import list'}
                </Text>
              </Pressable>

              <Pressable
                style={[styles.rowBtn, styles.rowBtnPrimary, { alignSelf: 'stretch', marginTop: 8, opacity: uploading || files.length === 0 ? 0.5 : 1 }]}
                onPress={onImport}
                disabled={uploading || files.length === 0}>
                <Text style={[styles.rowBtnText, styles.rowBtnTextPrimary]}>
                  {uploading ? 'Uploading…' : files.length > 0 ? `Import pasted WHOOP CSV (${files.length})` : 'Import pasted WHOOP CSV — add a file first'}
                </Text>
              </Pressable>

              <Text style={[styles.sourceMeta, { opacity: 0.45 }]}>
                A future build will add a native file picker (expo-document-picker) so you can select files directly from iOS Files instead of pasting. Until then, pasting is the only supported path — import is still incremental + dedup'd so re-pasting the same file does nothing.
              </Text>
            </ScrollView>
          </View>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

/**
 * Polar export historical training import — paste-only.
 *
 * Sister of WhoopCsvRow. Polar Flow's "Export account data" is one
 * file per training session (CSV or TCX). This row accepts a single
 * paste, runs the shared parser, shows a preview, and POSTs the
 * normalised PolarSession[] to the backend ingest endpoint when the
 * user taps Import.
 *
 * Provenance: every session is stamped `source: 'polar_export'` and is
 * historical training context only — never a recovery/readiness signal.
 * Health Connect remains the primary live Android path.
 */
function PolarExportRow() {
  return (
    <SafeErrorBoundary label="Polar export import">
      <PolarExportRowInner />
    </SafeErrorBoundary>
  );
}

function PolarExportRowInner() {
  const userId = useAuthStore((s) => s.user?.id);
  const accessToken = useAuthStore((s) => s.session?.access_token);
  const [draftText, setDraftText] = useState('');
  const [parsed, setParsed] = useState<{ sessions: PolarSession[]; format: string; diagnostics: string[] } | null>(null);
  const [importing, setImporting] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [showPaste, setShowPaste] = useState(false);

  const onParse = useCallback(() => {
    const text = draftText.trim();
    if (!text) {
      Alert.alert('Nothing to parse', 'Paste a Polar Flow CSV or TCX export first.');
      return;
    }
    if (text.length > 8 * 1024 * 1024) {
      Alert.alert('Paste too large', 'Polar exports paste up to ~8 MB. Split into per-session files.');
      return;
    }
    const result = parsePolarExport(text);
    setParsed({ sessions: result.sessions, format: result.format, diagnostics: result.diagnostics });
    if (!result.ok) {
      const msg = result.diagnostics.join('\n') || 'Could not identify Polar export shape.';
      Alert.alert('Polar import — needs a closer look', msg);
    }
  }, [draftText]);

  const onImport = useCallback(async () => {
    if (!parsed || parsed.sessions.length === 0 || importing) return;
    setImporting(true);
    try {
      const apiBase = process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '';
      const athleteMemoryToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
      const athleteId = userId ?? process.env.EXPO_PUBLIC_ATHLETE_ID ?? '';
      if (!apiBase || !athleteMemoryToken || !athleteId) {
        throw new Error('Backend config missing — sign in and retry.');
      }
      const res = await fetch(`${apiBase.replace(/\/$/, '')}/${athleteId}/polar-export/import`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-athlete-memory-token': athleteMemoryToken,
          ...(accessToken ? { authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({ sessions: parsed.sessions }),
      });
      const json: any = await res.json().catch(() => ({}));
      if (!res.ok || json?.ok === false) {
        throw new Error(json?.error ?? `Import failed (${res.status})`);
      }
      const summary = `${json.imported ?? 0} new · ${json.deduped ?? 0} dedup'd · ${parsed.sessions.length} parsed (${parsed.format}).`;
      setLastResult(summary);
      Alert.alert('Polar import complete', summary);
      setDraftText('');
      setParsed(null);
      setShowPaste(false);
    } catch (e: any) {
      Alert.alert('Polar import failed', e?.message ?? 'Unknown error.');
    } finally {
      setImporting(false);
    }
  }, [parsed, importing, userId, accessToken]);

  const sessionsCount = parsed?.sessions.length ?? 0;
  const dateRange = (() => {
    if (!parsed || parsed.sessions.length === 0) return null;
    const starts = parsed.sessions.map((s) => s.startTime).filter((s): s is string => !!s).sort();
    if (starts.length === 0) return null;
    return `${starts[0].slice(0, 10)} → ${starts[starts.length - 1].slice(0, 10)}`;
  })();
  const fieldsFound = (() => {
    if (!parsed || parsed.sessions.length === 0) return [];
    const present = new Set<string>();
    for (const s of parsed.sessions) {
      if (s.hrAvg != null || s.hrMax != null) present.add('HR');
      if (s.calories != null) present.add('calories');
      if (s.distanceKm != null) present.add('distance');
      if (s.cadenceAvg != null) present.add('cadence');
      if (s.speedAvgKmh != null) present.add('speed');
      if (s.powerAvgW != null) present.add('power');
    }
    return Array.from(present);
  })();

  return (
    <View style={styles.sourceRow}>
      <View style={styles.sourceRowHeader}>
        <Text style={styles.sourceName}>Polar export import</Text>
        <View style={[styles.sourceChip, { borderColor: parsed?.sessions.length ? '#d4e157' : '#888' }]}>
          <Text style={[styles.sourceChipText, { color: parsed?.sessions.length ? '#d4e157' : '#888' }]}>
            {parsed?.sessions.length ? 'Preview' : 'Optional'}
          </Text>
        </View>
      </View>
      <Text style={styles.sourceMeta}>
        Paste Polar Flow CSV/TCX export for historical training context. Recovery/readiness still uses your other sources — Polar export is evidence-only.
      </Text>
      <Text style={[styles.sourceMeta, { opacity: 0.45 }]}>
        For now, Polar users can sync through {Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect'}. Polar Direct with richer Polar-specific fields is planned for a later release. FIT files are not yet supported — export TCX or CSV.
      </Text>

      {!showPaste ? (
        <Pressable
          style={[styles.rowBtn, { alignSelf: 'flex-start', marginTop: 6 }]}
          onPress={() => setShowPaste(true)}>
          <Text style={styles.rowBtnText}>Paste Polar export</Text>
        </Pressable>
      ) : (
        <>
          <TextInput
            style={[styles.csvInput, { marginTop: 6 }]}
            multiline
            placeholder="Paste Polar Flow CSV or TCX content here…"
            placeholderTextColor="#666"
            value={draftText}
            onChangeText={(t) => {
              if (typeof t === 'string' && t.length > 2 * 1024 * 1024) {
                setDraftText(t.slice(0, 2 * 1024 * 1024));
                return;
              }
              setDraftText(t);
            }}
            maxLength={2 * 1024 * 1024}
            autoCorrect={false}
            autoCapitalize="none"
          />
          <View style={styles.rowActions}>
            <Pressable style={styles.rowBtn} onPress={onParse}>
              <Text style={styles.rowBtnText}>Parse / preview</Text>
            </Pressable>
            <Pressable
              style={[styles.rowBtn, styles.rowBtnPrimary, !sessionsCount && { opacity: 0.4 }]}
              disabled={!sessionsCount || importing}
              onPress={onImport}>
              <Text style={styles.rowBtnText}>{importing ? 'Importing…' : `Import ${sessionsCount || ''}`.trim()}</Text>
            </Pressable>
            <Pressable style={[styles.rowBtn, styles.rowBtnDanger]} onPress={() => { setDraftText(''); setParsed(null); setShowPaste(false); }}>
              <Text style={styles.rowBtnText}>Cancel</Text>
            </Pressable>
          </View>
          {parsed && (
            <Text style={[styles.sourceMeta, { marginTop: 4 }]}>
              {sessionsCount > 0
                ? `Parsed ${sessionsCount} session${sessionsCount === 1 ? '' : 's'} (${parsed.format})${dateRange ? ` · ${dateRange}` : ''}${fieldsFound.length ? ` · fields: ${fieldsFound.join(', ')}` : ''}`
                : `No sessions parsed. ${parsed.diagnostics.join(' ') || 'Try a different file.'}`}
            </Text>
          )}
        </>
      )}
      {lastResult && (
        <Text style={[styles.sourceMeta, { marginTop: 4, opacity: 0.55 }]}>{lastResult}</Text>
      )}
    </View>
  );
}

function SourceSheetRow({
  name, status, statusColor, meta, actions,
}: {
  name: string;
  status: string;
  statusColor: string;
  meta: string;
  actions: SourceAction[];
}) {
  const visibleActions = actions.filter((a) => !a.hidden);
  return (
    <View style={styles.sourceRow}>
      <View style={styles.sourceRowHeader}>
        <Text style={styles.sourceName}>{name}</Text>
        <View style={[styles.sourceChip, { borderColor: statusColor }]}>
          <Text style={[styles.sourceChipText, { color: statusColor }]}>{status}</Text>
        </View>
      </View>
      <Text style={styles.sourceMeta}>{meta}</Text>
      {visibleActions.length > 0 && (
        <View style={styles.rowActions}>
          {visibleActions.map((a, i) => (
            <Pressable
              key={`${a.label}-${i}`}
              style={[
                styles.rowBtn,
                a.kind === 'primary' && styles.rowBtnPrimary,
                a.kind === 'danger' && styles.rowBtnDanger,
                a.disabled && { opacity: 0.4 },
              ]}
              onPress={() => { void a.onPress(); }}
              disabled={a.disabled}
              accessibilityRole="button"
              accessibilityLabel={`${name} ${a.label}`}>
              <Text style={[
                styles.rowBtnText,
                a.kind === 'primary' && styles.rowBtnTextPrimary,
                a.kind === 'danger' && styles.rowBtnTextDanger,
              ]}>
                {a.label}
              </Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}
