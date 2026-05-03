/**
 * AthleteStateStrip — compact visual summary of the app-owned
 * device-agnostic AppAthleteState.
 *
 * The point of this component is to make visible that the app has its
 * OWN interpretation of recovery / load / fueling — independent from
 * whichever device is currently connected. Vendor scores are inputs,
 * not the whole brain.
 *
 * Hides itself when no meaningful signals exist yet.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useHealthStore } from '../store/health-store';
import { useWhoopStore } from '../store/whoop-store';
import { useNutritionStore } from '../store/nutrition-store';
import { useTrainingStore } from '../store/training-store';
import { useAuthStore } from '../store/auth-store';
import { buildAppAthleteState, type AppAthleteState } from '../services/app-athlete-state';
import { syncAppAthleteStateSnapshotToAiBackend } from '../services/ai-hiit-sync';
import { readStoredJson, writeStoredJson } from '../store/secure-storage';

// Local cache of the last assembled AppAthleteState snapshot keyed to
// the current user. Lets Home render a grounded app-analysis card on
// cold start after reinstall, even before Apple Health sync and WHOOP
// fetch complete. The cache is per-device (secureStorage) and written
// with the signed-in user.id as the key so a different account on the
// same device never reads another user's snapshot. Superseded the
// moment live data reassembles the state — treat as warm-cache bridge,
// not durable truth.
const LAST_STATE_KEY_PREFIX = 'last_app_athlete_state_v1__';
const lastStateKey = (uid: string) => `${LAST_STATE_KEY_PREFIX}${uid}`;

const WHOOP_CSV_CACHE_KEY = 'whoop_csv_imported_v1';
type WhoopCsvCache = { imported: boolean; totalRowsIngested?: number; updatedAt: string };

function bandColor(b: string): string {
  if (b === 'high') return '#4ade80';
  if (b === 'mid') return '#d4e157';
  if (b === 'low' || b === 'over') return '#ff6b6b';
  if (b === 'at_target') return '#4ade80';
  if (b === 'under') return '#d4e157';
  return '#666';
}

function bandLabel(b: string): string {
  if (b === 'at_target') return 'on target';
  if (b === 'unknown') return '—';
  return b;
}

export function AthleteStateStrip() {
  const days = useHealthStore((s) => s.days);
  const features = useHealthStore((s) => s.features);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const whoopDay = useWhoopStore((s) => s.day);
  const whoopFetchedAt = useWhoopStore((s) => s.fetchedAt);
  const whoopFetchStatus = useWhoopStore((s) => s.status);
  const nutritionToday = useNutritionStore((s) => s.today);
  const nutritionTargets = useNutritionStore((s) => s.targets);
  const nutritionHistoryDays = useNutritionStore((s) => s.historyDays);
  const polarViaHc = useHealthStore((s) => s.polarViaHc);
  const samsungViaHc = useHealthStore((s) => s.samsungHealthViaHc);
  const sessions = useTrainingStore((s) => s.sessions);

  const [whoopCsv, setWhoopCsv] = useState<WhoopCsvCache | null>(null);
  const [cachedSnapshot, setCachedSnapshot] = useState<AppAthleteState | null>(null);
  useEffect(() => {
    void (async () => {
      try {
        const cached = await readStoredJson<WhoopCsvCache>(WHOOP_CSV_CACHE_KEY);
        setWhoopCsv(cached ?? null);
      } catch { /* ignore */ }
    })();
  }, []);
  const userIdForCache = useAuthStore((s) => s.user?.id ?? null);
  useEffect(() => {
    if (!userIdForCache) { setCachedSnapshot(null); return; }
    void (async () => {
      try {
        const cached = await readStoredJson<{ capturedAt: string; snapshot: AppAthleteState }>(lastStateKey(userIdForCache));
        if (cached?.snapshot) setCachedSnapshot(cached.snapshot);
      } catch { /* ignore */ }
    })();
  }, [userIdForCache]);

  const state: AppAthleteState = useMemo(() => {
    return buildAppAthleteState({
      todayIsoDate: new Date().toISOString().slice(0, 10),
      days,
      features,
      sessions,
      whoopDay: whoopDay as any,
      whoopFetchedAt,
      nutritionToday: (nutritionToday as any) ?? null,
      nutritionTargets: (nutritionTargets as any) ?? null,
      nutritionHistory: (nutritionHistoryDays as any) ?? null,
      healthLastSyncAt: lastSyncAt,
      whoopCsv: whoopCsv ? {
        imported: whoopCsv.imported,
        rowCount: whoopCsv.totalRowsIngested ?? null,
        windowDays: null,
      } : null,
      whoopFetchStatus,
      polarPresence: polarViaHc?.detected ? {
        detected: true,
        viaHealthConnect: true,
        daysWithRecords: polarViaHc.daysWithRecords ?? null,
      } : null,
      samsungPresence: samsungViaHc?.detected ? {
        detected: true,
        daysWithRecords: samsungViaHc.daysWithRecords ?? null,
      } : null,
    });
  }, [days, features, sessions, whoopDay, whoopFetchedAt, whoopFetchStatus, nutritionToday, nutritionTargets, nutritionHistoryDays, lastSyncAt, whoopCsv, polarViaHc, samsungViaHc]);

  // Hide when literally nothing useful yet. But: if we have a warm
  // cached snapshot from a previous session, surface that instead of
  // nothing — reinstall/cold-boot users shouldn't see a blank Home
  // while Apple Health + WHOOP finish syncing.
  const liveAllUnknown = state.recovery_context.band === 'unknown'
    && state.load_context.band === 'unknown'
    && state.fueling_adequacy.band === 'unknown';
  const effectiveState: AppAthleteState = liveAllUnknown && cachedSnapshot ? cachedSnapshot : state;
  const allUnknown = liveAllUnknown && cachedSnapshot == null;

  // Durable snapshot auto-push. Fires when the merged state materially
  // changes (band transitions in any of the headline axes) and at most
  // once per 10 minutes. Gives Coach + AI learning a durable artifact
  // without waiting for the user to tap Save to Account.
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const lastPushedAtRef = useRef<number>(0);
  const lastSignatureRef = useRef<string>('');
  useEffect(() => {
    // Push only the LIVE state (never the warm-cache). If live is
    // still unknown, skip push entirely — we don't want to upload a
    // cached snapshot that's really just yesterday's read.
    if (liveAllUnknown || !userId) return;
    const signature = [
      state.recovery_context.band,
      state.load_context.band,
      state.sleep_adequacy.band,
      state.fueling_adequacy.band,
      state.acute_fatigue.band,
      state.readiness_confidence.level,
    ].join('|');
    const now = Date.now();
    const tenMin = 10 * 60 * 1000;
    const changed = signature !== lastSignatureRef.current;
    const stale = now - lastPushedAtRef.current > tenMin;
    if (!changed && !stale) return;
    lastSignatureRef.current = signature;
    // Only mark pushed on success — so a 404 during the Railway-not-
    // deployed window lets the next render retry automatically once
    // the route lands.
    void syncAppAthleteStateSnapshotToAiBackend(userId, state)
      .then((ok) => { if (ok) lastPushedAtRef.current = now; })
      .catch(() => {});
    // Always write the local warm-cache, regardless of backend push
    // outcome. This is the part that survives reinstall and makes the
    // first render after app cold-start useful instead of blank.
    void writeStoredJson(lastStateKey(userId), { capturedAt: new Date().toISOString(), snapshot: state } as unknown as object).catch(() => {});
  }, [userId, liveAllUnknown, state]);

  if (allUnknown) return null;

  return (
    <View style={styles.card}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>Readiness</Text>
        {/* Surface confidence only when it isn't already high — there's
            no value broadcasting "high confidence". The Health tab
            still shows full provenance + per-source coverage. */}
        {effectiveState.readiness_confidence.level !== 'high' && (
          <Text style={styles.sub}>
            {effectiveState.readiness_confidence.level} confidence
          </Text>
        )}
      </View>
      {/* Headline band is the app's OWN derived readiness — blended
          from Apple Health baselines, WHOOP Direct when scored,
          WHOOP CSV enrichment when imported, plus recent training
          and fueling context. It is NOT the WHOOP native recovery
          score. The WHOOP card renders WHOOP-native recovery
          separately and keeps that label. */}
      <View style={styles.row}>
        <Band label="Readiness" band={effectiveState.recovery_context.band} score={effectiveState.recovery_context.score_0_100} />
        <Band label="Load" band={effectiveState.load_context.band} score={null} extra={`${effectiveState.load_context.sessions_7d}/7d`} />
        <Band label="Fueling" band={effectiveState.fueling_adequacy.band} score={effectiveState.fueling_adequacy.calories_vs_target_pct} pctUnit />
        <Band label="Sleep" band={effectiveState.sleep_adequacy.band} score={effectiveState.sleep_adequacy.hours_last_night ?? null} extra="h" />
      </View>
      {effectiveState.readiness_confidence.reasons_for_low.length > 0 && (
        <Text style={styles.missing}>
          Missing: {effectiveState.readiness_confidence.reasons_for_low.join(' · ')}
        </Text>
      )}
      <Text style={styles.note}>{effectiveState.recovery_context.note}</Text>
      {/* Load + fueling notes when they add information. The recovery
          note already covers the general situation; these surface
          acute/chronic load patterns + fueling adequacy when worth it. */}
      {effectiveState.load_context.band === 'over' && (
        <Text style={styles.noteAmber}>{effectiveState.load_context.note}</Text>
      )}
      {(effectiveState.fueling_adequacy.band === 'low' || effectiveState.fueling_adequacy.band === 'mid') && (
        <Text style={effectiveState.fueling_adequacy.band === 'low' ? styles.noteRed : styles.note}>
          Fueling: {effectiveState.fueling_adequacy.note}
        </Text>
      )}
      {effectiveState.acute_fatigue.band === 'high' && (
        <Text style={styles.noteAmber}>Acute fatigue: {effectiveState.acute_fatigue.note}</Text>
      )}
      {/* Compact source-detail line — Apple Health is named as the
          primary live source; WHOOP is summarised as an optional
          calibration/reference layer rather than a visible recovery
          source. Never surfaces the WHOOP recovery score on Home. */}
      {(() => {
        const sr = effectiveState.source_roles;
        const parts: string[] = [];
        if (sr.apple_health.role === 'broad_baseline') {
          // The `apple_health` source-role slot covers both iOS Apple
          // Health and Android Health Connect — they're the same
          // platform-native broad health source role. Label per OS.
          const nativeLabel = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
          parts.push(`${nativeLabel} · ${sr.apple_health.history_depth_days}d baseline`);
        }
        const whoopContributes =
          sr.whoop_direct.role === 'live_current'
          || sr.whoop_direct.role === 'awaiting_cycle'
          || sr.whoop_csv.role === 'deeper_enrichment';
        if (whoopContributes) parts.push('Includes optional WHOOP reference');
        if (sr.polar.role === 'training_evidence') parts.push('Polar training evidence');
        if (sr.samsung_health.role === 'broad_baseline_via_hc') parts.push('Samsung Health via HC');
        if (parts.length === 0) return null;
        return <Text style={styles.sourceRoles}>{parts.join(' · ')}</Text>;
      })()}
    </View>
  );
}

function Band({ label, band, score, extra, pctUnit }: { label: string; band: string; score: number | null; extra?: string; pctUnit?: boolean }) {
  const color = bandColor(band);
  const value = score == null ? (extra ?? bandLabel(band)) : `${score}${pctUnit ? '%' : extra ? extra : ''}`;
  return (
    <View style={styles.band}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.bandLabel}>{label}</Text>
      <Text style={[styles.bandValue, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.04)',
    gap: 8,
  },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  title: { fontSize: 14, fontWeight: '700' },
  sub: { fontSize: 10, opacity: 0.5, textTransform: 'uppercase', letterSpacing: 0.5 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  band: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  bandLabel: { fontSize: 12, opacity: 0.7 },
  bandValue: { fontSize: 13, fontWeight: '700' },
  missing: { fontSize: 11, opacity: 0.55 },
  note: { fontSize: 12, opacity: 0.75, lineHeight: 16 },
  noteAmber: { fontSize: 12, color: '#d4e157', lineHeight: 16, opacity: 0.85 },
  noteRed: { fontSize: 12, color: '#ff6b6b', lineHeight: 16, opacity: 0.9 },
  sourceRoles: { fontSize: 10, opacity: 0.45, marginTop: 2, letterSpacing: 0.3 },
});
