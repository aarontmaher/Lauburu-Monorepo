import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Platform,
  Alert,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import * as Application from 'expo-application';
import { useHealthStore } from '../../src/store/health-store';
import { useAuthStore } from '../../src/store/auth-store';
import { useTierStore } from '../../src/store/tier-store';
import { useAuditEventStore } from '../../src/store/audit-event-store';
import { isExpoGo } from '../../src/services/expo-detect';
import { AthleteCapabilitySummary } from '../../src/components/AthleteCapabilitySummary';
import { NutritionCard } from '../../src/components/NutritionCard';
import { getSeedBackendStatusCopy } from '../../src/services/athlete-capability-display';
import { PolarCard } from '../../src/components/PolarCard';
import {
  AppleHealthCard,
  PolarDirectCard,
  WhoopDirectCard,
  HealthConnectProvenanceCard,
  SamsungHealthCard,
} from '../../src/components/IntegrationCards';
import { HealthConnectAvailabilityHint } from '../../src/components/HealthConnectAvailabilityHint';
import { MemoryProposalReview } from '../../src/components/MemoryProposalReview';
import { SyncDiagnosticsCard } from '../../src/components/SyncDiagnosticsCard';
import { HealthKitDebugCard } from '../../src/components/HealthKitDebugCard';
import { HealthActionsPanel } from '../../src/components/HealthActionsPanel';
import { SafeErrorBoundary } from '../../src/components/SafeErrorBoundary';
import { useWhoopStore } from '../../src/store/whoop-store';
import type { HealthMetricType, PermissionStatus, DailyMetrics, DerivedFeatures, CoachingResponse } from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';

// --- Permission status row ---

const STATUS_LABELS: Record<PermissionStatus, { text: string; color: string }> = {
  authorized: { text: 'Authorized', color: '#4ade80' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  not_determined: { text: 'Not requested', color: '#d4e157' },
  unavailable: { text: 'Unavailable', color: '#666' },
};

const METRIC_LABELS: Record<HealthMetricType, string> = {
  heart_rate: 'Heart Rate',
  resting_heart_rate: 'Resting Heart Rate',
  hrv: 'Heart Rate Variability',
  sleep: 'Sleep',
  steps: 'Steps',
  active_calories: 'Active Calories',
  workouts: 'Workouts',
};

const WHOOP_STALE_HOURS = 6;

function whoopSourceStatus(
  whoopStatus: 'idle' | 'loading' | 'ready' | 'error',
  sourceUpdatedAt: string | null,
  hasCachedDay: boolean,
): string {
  if (whoopStatus === 'error') {
    return hasCachedDay ? 'degraded_backend' : 'backend_error';
  }
  if (whoopStatus === 'idle' || whoopStatus === 'loading') return 'checking_backend';
  if (!sourceUpdatedAt) return 'seed_backend';
  const updatedAt = new Date(sourceUpdatedAt).getTime();
  if (Number.isNaN(updatedAt)) return 'seed_backend';
  const ageMs = Date.now() - updatedAt;
  return ageMs > WHOOP_STALE_HOURS * 60 * 60 * 1000
    ? 'stale_seed_backend'
    : 'fresh_seed_backend';
}

function PermissionRow({
  metric,
  status,
}: {
  metric: HealthMetricType;
  status: PermissionStatus;
}) {
  const info = STATUS_LABELS[status];
  return (
    <View style={styles.permRow}>
      <Text style={styles.permLabel}>{METRIC_LABELS[metric]}</Text>
      <Text style={[styles.permStatus, { color: info.color }]}>{info.text}</Text>
    </View>
  );
}

// --- Today's metrics card ---

function TodayCard({ today }: { today: DailyMetrics }) {
  // Prefer WHOOP's real strain from the live day object when available
  // over Apple Health's active-cal/100 proxy (which pegs to 21 on any
  // high-activity day and has no relationship to actual WHOOP strain).
  const whoopDay = useWhoopStore((s) => s.day);
  const whoopStrainToday = whoopDay?.date === today.date ? whoopDay.daily_strain : null;
  const hasWhoopStrain = typeof whoopStrainToday === 'number';
  const showProxyStrain = !hasWhoopStrain && today.daily_strain != null && today.daily_strain < 21;
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Today — {today.date}</Text>
      <View style={styles.metricsGrid}>
        <MetricBox label="Resting HR" value={today.resting_hr} unit="bpm" />
        <MetricBox label="HRV" value={today.hrv_ms} unit="ms" />
        <MetricBox label="Sleep" value={today.sleep_hours} unit="hrs" />
        <MetricBox label="Active Cal" value={today.active_calories} unit="kcal" />
        {hasWhoopStrain && (
          <MetricBox
            label="WHOOP strain"
            value={whoopStrainToday}
            unit=""
          />
        )}
        {showProxyStrain && (
          <MetricBox
            label="Day load (est.)"
            value={today.daily_strain}
            unit=""
          />
        )}
      </View>
      {today.workouts && today.workouts.length > 0 && (
        <View style={styles.workoutSection}>
          <Text style={styles.workoutHeader}>
            Workouts ({today.workouts.length})
          </Text>
          {today.workouts.map((w, i) => (
            <View key={i} style={styles.workoutRow}>
              <View>
                <Text style={styles.workoutName}>
                  {w.sport_label ?? w.type}
                  {w.is_grappling ? ' 🥋' : ''}
                </Text>
                {w.source ? (
                  <Text style={styles.workoutSource}>{w.source}</Text>
                ) : null}
              </View>
              <View style={styles.workoutMetaCol}>
                <Text style={styles.workoutMeta}>
                  {w.duration_min}min
                  {w.calories ? ` · ${Math.round(w.calories)}cal` : ''}
                </Text>
                {(w.avg_hr || w.distance_m) ? (
                  <Text style={styles.workoutMeta}>
                    {w.avg_hr ? `${Math.round(w.avg_hr)}bpm avg` : ''}
                    {w.avg_hr && w.distance_m ? ' · ' : ''}
                    {w.distance_m ? `${(w.distance_m / 1000).toFixed(1)}km` : ''}
                  </Text>
                ) : null}
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function MetricBox({
  label,
  value,
  unit,
}: {
  label: string;
  value?: number;
  unit: string;
}) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>
        {value != null ? String(Math.round(value * 10) / 10) : '—'}
      </Text>
      <Text style={styles.metricUnit}>{unit}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

// --- Recent days list ---

function RecentDays({ days }: { days: DailyMetrics[] }) {
  const recent = days.slice(-7).reverse();
  if (recent.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recent Days</Text>
      {recent.map((day) => {
        // Compact row: date · RHR · sleep · HRV · strain. Missing
        // fields render as em-dash (or are dropped when trailing) so
        // the row never breaks layout and stays readable whether a
        // full set or just a couple of fields are present. Strain
        // prefers the day's real daily_strain (WHOOP-sourced when
        // merged); when it's only the Apple Health proxy pegged to
        // 21, show "—" rather than the misleading cap value.
        const rhr = day.resting_hr ? `${Math.round(day.resting_hr)} bpm` : '—';
        const sleep = day.sleep_hours ? `${(Math.round(day.sleep_hours * 10) / 10).toFixed(1)}h` : '—';
        const hrv = day.hrv_ms ? `${Math.round(day.hrv_ms)} ms` : '—';
        const strainVal = day.daily_strain;
        const strain = strainVal == null
          ? '—'
          : strainVal >= 20.9
            ? '—'
            : strainVal.toFixed(1);
        return (
          <View key={day.date} style={styles.dayRow}>
            <Text style={styles.dayDate}>{day.date}</Text>
            <Text style={styles.dayMetrics}>
              {rhr} · {sleep} · {hrv} HRV · strain {strain}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

// --- Main screen ---

// --- Coaching card (structured training guidance) ---

function CoachingCard({ coaching }: { coaching: CoachingResponse }) {
  const statusColors: Record<string, string> = {
    recovered: '#4ade80',
    recovering: '#d4e157',
    fatigued: '#ff6b6b',
    unknown: '#666',
    good: '#4ade80',
    adequate: '#d4e157',
    poor: '#ff6b6b',
    balanced: '#4ade80',
    high: '#d4e157',
    low: '#999',
    overreaching: '#ff6b6b',
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Coaching</Text>
      <AthleteCapabilitySummary mode="missing_whoop_native" showNote={false} />

      {/* Today's recommendation */}
      <View style={styles.coachSection}>
        <Text style={styles.coachSectionLabel}>Today</Text>
        <Text style={styles.coachDetail}>{coaching.today_recommendation.detail}</Text>
      </View>

      {/* Recovery + Sleep + Load row */}
      <View style={styles.coachStatusRow}>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.recovery.status] }]}>
            {coaching.recovery.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Recovery</Text>
        </View>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.sleep.status] }]}>
            {coaching.sleep.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Sleep</Text>
        </View>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.training_load.status] }]}>
            {coaching.training_load.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Load</Text>
        </View>
      </View>

      {/* Grappling guidance */}
      <View style={styles.coachSection}>
        <Text style={styles.coachSectionLabel}>Grappling</Text>
        <Text style={styles.coachBody}>{coaching.grappling.summary}</Text>
        <Text style={styles.coachSuggestion}>{coaching.grappling.suggestion}</Text>
      </View>

      {/* Plan status */}
      {coaching.plan && coaching.plan.status !== 'no_plan' && (
        <View style={styles.coachSection}>
          <Text style={styles.coachSectionLabel}>Schedule</Text>
          <Text style={styles.coachBody}>{coaching.plan.summary}</Text>
        </View>
      )}

      {/* Recovery actions */}
      {coaching.recovery.actions.length > 0 && (
        <View style={styles.coachSection}>
          <Text style={styles.coachSectionLabel}>Recovery Actions</Text>
          {coaching.recovery.actions.map((a, i) => (
            <Text key={i} style={styles.coachAction}>• {a}</Text>
          ))}
        </View>
      )}

      {/* Preference effects */}
      {coaching.preference_effects && coaching.preference_effects.length > 0 && (
        <View style={styles.coachPrefs}>
          {coaching.preference_effects.map((e, i) => (
            <Text key={i} style={styles.coachPrefText}>⚙ {e}</Text>
          ))}
        </View>
      )}

      {/* Confidence */}
      <Text style={styles.coachConfidence}>
        Confidence: {coaching.confidence.level} — {coaching.confidence.note}
      </Text>
    </View>
  );
}

// --- Insights card (main training guidance) ---

import type { TrainingInsight, ReadinessLevel } from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function InsightsCard({ insights }: { insights: TrainingInsight }) {
  const color = READINESS_COLORS[insights.readiness];
  const statusColors: Record<string, string> = {
    good: '#4ade80',
    caution: '#d4e157',
    warning: '#ff6b6b',
    neutral: '#999',
  };

  return (
    <View style={styles.card}>
      {/* Readiness header */}
      <View style={styles.readinessHeader}>
        <View style={[styles.readinessDot, { backgroundColor: color }]} />
        <View style={styles.readinessText}>
          <Text style={[styles.readinessLabel, { color }]}>
            {insights.readiness_label}
          </Text>
          <Text style={styles.readinessSummary}>
            {insights.recommendation.summary}
          </Text>
        </View>
      </View>

      {/* Key metrics row */}
      {insights.key_metrics.length > 0 && (
        <View style={styles.keyMetricsRow}>
          {insights.key_metrics.map((m, i) => (
            <View key={i} style={styles.keyMetric}>
              <Text style={[styles.keyMetricValue, { color: statusColors[m.status] }]}>
                {m.value}
              </Text>
              <Text style={styles.keyMetricLabel}>{m.label}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Reasons */}
      {insights.recommendation.reasons.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.recommendation.reasons.map((r, i) => (
            <Text key={i} style={styles.reasonText}>• {r}</Text>
          ))}
        </View>
      )}

      {/* Positives */}
      {insights.positives.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.positives.map((p, i) => (
            <Text key={i} style={[styles.reasonText, { color: '#4ade80' }]}>
              ✓ {p}
            </Text>
          ))}
        </View>
      )}

      {/* Concerns */}
      {insights.concerns.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.concerns.map((c, i) => (
            <Text key={i} style={[styles.reasonText, { color: '#ff6b6b' }]}>
              ⚠ {c}
            </Text>
          ))}
        </View>
      )}

      {/* Data note */}
      <Text style={styles.dataNoteText}>{insights.data_note}</Text>
    </View>
  );
}

// --- Flags card ---

function FlagsCard({ flags }: { flags: HealthFlag[] }) {
  if (flags.length === 0) return null;
  const colors: Record<string, string> = {
    warning: '#ff6b6b',
    info: '#d4e157',
    positive: '#4ade80',
  };
  const icons: Record<string, string> = {
    warning: '⚠',
    info: 'ℹ',
    positive: '✓',
  };
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Flags</Text>
      {flags.map((f, i) => (
        <Text key={i} style={[styles.flagText, { color: colors[f.type] }]}>
          {icons[f.type]} {f.label}
        </Text>
      ))}
    </View>
  );
}

// --- Trends card ---

const TREND_ARROWS: Record<string, string> = {
  improving: '↑',
  declining: '↓',
  stable: '→',
  increasing: '↑',
  decreasing: '↓',
};
const TREND_COLORS: Record<string, string> = {
  improving: '#4ade80',
  declining: '#ff6b6b',
  stable: '#999',
  increasing: '#d4e157',
  decreasing: '#4ade80', // decreasing strain is good
};

function TrendsCard({ features }: { features: DerivedFeatures }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>7-Day Trends</Text>
      <View style={styles.trendsGrid}>
        <TrendItem
          label="Recovery"
          trend={features.recovery_trend}
          value={features.last_7d_recovery_mean}
          unit="%"
        />
        <TrendItem
          label="Strain"
          trend={features.strain_trend}
          value={features.last_7d_strain_mean}
          unit=""
        />
        <TrendItem
          label="HRV"
          trend={features.baseline_hrv_mean != null ? 'stable' : 'stable'}
          value={features.baseline_hrv_mean}
          unit="ms"
        />
        <TrendItem
          label="Sleep"
          trend={features.baseline_sleep_mean != null ? 'stable' : 'stable'}
          value={features.baseline_sleep_mean}
          unit="h"
        />
      </View>
      <View style={styles.trendMeta}>
        <Text style={styles.trendMetaText}>
          {features.workouts} workouts · {features.grappling_sessions} grappling
        </Text>
        <Text style={styles.trendMetaText}>
          Sources: {(features.provenance ?? []).join(', ') || 'none'}
        </Text>
      </View>
    </View>
  );
}

function TrendItem({
  label,
  trend,
  value,
  unit,
}: {
  label: string;
  trend: string;
  value: number | null;
  unit: string;
}) {
  const arrow = TREND_ARROWS[trend] ?? '→';
  const color = TREND_COLORS[trend] ?? '#999';
  return (
    <View style={styles.trendItem}>
      <Text style={styles.trendLabel}>{label}</Text>
      <Text style={[styles.trendValue, { color }]}>
        {value != null ? `${Math.round(value * 10) / 10}${unit}` : '—'}
        {' '}
        {arrow}
      </Text>
    </View>
  );
}

// --- Backend sync card ---

function BackendSyncCard() {
  const persisting = useHealthStore((s) => s.persisting);
  const lastPersistedAt = useHealthStore((s) => s.lastPersistedAt);
  const lastPersistResult = useHealthStore((s) => s.lastPersistResult);
  const persistToBackend = useHealthStore((s) => s.persistToBackend);
  const storeError = useHealthStore((s) => s.error);
  const authStatus = useAuthStore((s) => s.status);
  const canPersist = useTierStore((s) => s.can)('backend_persistence');
  // Local in-progress state — flips true the instant the button is
  // pressed so the user gets immediate feedback. Previously we only
  // observed the health-store `persisting` flag, which doesn't flip
  // true until AFTER the Railway fan-out completes, making the button
  // look idle for the 2-5s Railway phase.
  const [saving, setSaving] = useState<false | 'railway' | 'supabase'>(false);
  // pressResult now tracks both halves of the fan-out independently.
  // Previously only Supabase success/failure was rendered — which read
  // as "Save failed" in red even when Railway primary had succeeded.
  // Splitting the state lets the UI show "Railway primary saved · N
  // items" in green while the Supabase line states its exact blocker.
  // Three-state Railway result (ok+items / ok+empty / errored) means we
  // can render all combinations truthfully: green when either path
  // saved, red only when an actual error happened, yellow when the
  // Supabase mirror is the only block, and neutral when there was
  // genuinely nothing to push.
  const [pressResult, setPressResult] = useState<
    {
      at: string;
      railway: { status: 'saved' | 'empty' | 'error'; lines: string[]; error?: string };
      supabase: { ok: boolean; recordCount?: number; dateRange?: string; error?: string };
    } | null
  >(null);

  const handlePress = useCallback(async () => {
    const startedAt = new Date().toISOString();
    // Flip local saving state BEFORE any await so the button re-renders
    // on the next frame. Health-store's own `persisting` only covers
    // the Supabase leg and would leave the button looking idle during
    // the Railway fan-out. Clear any prior result so stale green/red
    // lines don't linger while the new save runs.
    setSaving('railway');
    setPressResult(null);
    // STEP 1: Always run the Railway durable-persist path first. It's
    // independent of Supabase's JWT flip and authenticated via the
    // internal token — so even when the Supabase mirror is blocked,
    // Save to Account still pushes Apple Health days + nutrition +
    // HIIT sessions to the primary durable layer. This is what the
    // AI actually learns from.
    let railwayLines: string[] = [];
    let railwayError: string | null = null;
    let railwayCalled = false;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { persistDurableToRailway } = require('../../src/services/durable-persist');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const nutStore = require('../../src/store/nutrition-store');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const hiitStore = require('../../src/store/hiit-workout-store');
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const trainingStore = require('../../src/store/training-store');
      const authMod = require('../../src/store/auth-store');
      const uid = authMod?.useAuthStore?.getState?.()?.user?.id;
      const days = useHealthStore.getState().days;
      const nut = nutStore?.useNutritionStore?.getState?.();
      const hiitWorkouts = hiitStore?.useHIITWorkoutStore?.getState?.()?.workouts ?? [];
      const trainingSessions = trainingStore?.useTrainingStore?.getState?.()?.sessions ?? [];

      // Assemble the AppAthleteState snapshot so the merged, device-
      // agnostic interpretation (recovery/load/sleep/fueling/source-
      // roles) is persisted alongside raw days. Without this, AI
      // learning only sees ingest — not the app's own reasoning.
      let athleteStateSnapshot: unknown = null;
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const appState = require('../../src/services/app-athlete-state');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const whoopStore = require('../../src/store/whoop-store');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const secureStorage = require('../../src/store/secure-storage');
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
      } catch { /* non-fatal — snapshot is optional */ }

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
      // Swallowing this previously made the UI report "nothing new to
      // push" when the fan-out helper actually threw — a silent lie.
      railwayError = e?.message ?? 'Railway fan-out threw';
    }

    // STEP 2: Try the Supabase /health-import mirror. Under the new
    // JWT Signing Keys model, signing-key issues surface as 401s; the
    // app shows the JWT-Keys hint banner. Success = redundant backup.
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
      const supaLine = `Supabase mirror: ${next.lastPersistResult?.recordCount ?? 0} days (${next.lastPersistResult?.dateRange ?? '—'})`;
      Alert.alert('Backend Sync', `${railwaySummary}\n${supaLine}`);
    } else {
      const err = useHealthStore.getState().error ?? 'Unknown error';
      setPressResult({
        at: startedAt,
        railway: { status: railwayStatus, lines: railwayLines, error: railwayError ?? undefined },
        supabase: { ok: false, error: err },
      });
      Alert.alert('Backend Sync',
        `${railwaySummary}\n\n${railwayStatus === 'saved' ? 'Your data is durable on Railway.' : 'Primary path unavailable too — see the Railway error above.'} Supabase mirror is configured · source-state mirror is live · full per-day metric mirror is still pending. Railway primary remains the durable source.`,
      );
    }
    // Flip button back to idle only when the whole fan-out (both legs)
    // has landed a final result.
    setSaving(false);
  }, [persistToBackend]);

  if (authStatus !== 'member') return null;

  if (!canPersist) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Cloud Sync</Text>
        <Text style={styles.gateText}>
          Save health data to your account with the Starter plan.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Backend Sync</Text>
        <Pressable
          style={[styles.syncButton, (saving || persisting) && { opacity: 0.7 }]}
          onPress={handlePress}
          disabled={!!saving || persisting}>
          {saving ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <ActivityIndicator size="small" color="#d4e157" />
              <Text style={[styles.syncButtonText, { fontSize: 11 }]}>
                {saving === 'railway' ? 'Saving Railway…' : 'Saving Supabase…'}
              </Text>
            </View>
          ) : persisting ? (
            <ActivityIndicator size="small" color="#d4e157" />
          ) : (
            <Text style={styles.syncButtonText}>Save long-term data</Text>
          )}
        </Pressable>
      </View>
      {saving && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 }}>
          <ActivityIndicator size="small" color="#d4e157" />
          <Text style={[styles.syncTimestamp, { color: '#d4e157' }]}>
            {saving === 'railway'
              ? 'Saving Railway primary · pushing Apple Health days, nutrition, sessions…'
              : 'Saving Supabase mirror · attempting redundant backup…'}
          </Text>
        </View>
      )}
      {pressResult?.railway.status === 'saved' && (
        <Text style={[styles.syncTimestamp, { color: '#4ade80' }]}>
          ✓ Synced to Railway this push · {pressResult.railway.lines.join(', ')} (server dedupes by date)
        </Text>
      )}
      {pressResult?.railway.status === 'empty' && (
        <Text style={styles.syncTimestamp}>
          Railway primary: nothing new to push.
        </Text>
      )}
      {pressResult?.railway.status === 'error' && (
        <Text style={[styles.syncTimestamp, { color: '#ff6b6b' }]}>
          Railway primary error: {pressResult.railway.error ?? 'unknown'}
        </Text>
      )}
      {pressResult?.supabase.ok && (
        <Text style={[styles.syncTimestamp, { color: '#4ade80', opacity: 0.8 }]}>
          ✓ Supabase mirror saved: {pressResult.supabase.recordCount} day{pressResult.supabase.recordCount === 1 ? '' : 's'} ({pressResult.supabase.dateRange})
        </Text>
      )}
      {pressResult && !pressResult.supabase.ok && (
        <Text style={[styles.syncTimestamp, {
          // Yellow when Supabase is the only block and Railway saved —
          // this is the steady-state we expect until the JWT flip.
          // Red only when both paths failed, because that IS a real
          // total-failure worth flagging.
          color: pressResult.railway.status === 'error' ? '#ff6b6b' : '#d4e157',
        }]}>
          {pressResult.railway.status === 'error'
            ? 'Supabase mirror also blocked'
            : 'Supabase mirror configured · source-state live · per-day mirror pending'}
        </Text>
      )}
      {!saving && lastPersistedAt && (
        <Text style={styles.syncTimestamp}>
          Last saved: {new Date(lastPersistedAt).toLocaleString()}
          {lastPersistResult
            ? ` · ${lastPersistResult.recordCount} days (${lastPersistResult.dateRange})`
            : ''}
        </Text>
      )}
      {!saving && !lastPersistedAt && !pressResult && (
        <>
          <Text style={styles.syncTimestamp}>
            {'Your Apple Health days, nutrition history, HIIT + training sessions, and the merged athlete-state snapshot already stream to the durable backend layer — they survive reinstall and feed long-term AI learning.'}
          </Text>
          <Text style={[styles.syncTimestamp, { opacity: 0.5 }]}>
            {'Tap Save long-term data to push a fresh local snapshot to Railway. The server dedupes by date so re-pushing is safe and never overwrites older history.'}
          </Text>
        </>
      )}
      {/* Supabase JWT algorithm mismatch is an admin-side blocker —
          surface it explicitly so the user knows no amount of tapping
          will fix it until the dashboard knob flips. Apple Health →
          Coach still works via the Railway /ingest path regardless. */}
      {(() => {
        const err = (pressResult && !pressResult.supabase.ok ? (pressResult.supabase.error ?? '') : (storeError ?? '')) ?? '';
        const isJwtError = /jwt|signing|unauthor|401/i.test(err);
        if (!isJwtError) {
          if (storeError && !pressResult) {
            return (
              <Text style={[styles.syncTimestamp, { color: '#ff6b6b' }]}>
                Previous error: {storeError}
              </Text>
            );
          }
          return null;
        }
        return (
          <View style={{
            marginTop: 6, padding: 10, borderRadius: 8,
            backgroundColor: 'rgba(255,107,107,0.08)',
            borderWidth: 1, borderColor: 'rgba(255,107,107,0.25)', gap: 4,
          }}>
            <Text style={{ color: '#ff6b6b', fontSize: 12, fontWeight: '700' }}>
              Supabase JWT key needs attention
            </Text>
            <Text style={{ color: '#e0e0e0', fontSize: 12, lineHeight: 16 }}>
              The Supabase mirror rejected this access token.{'\n'}
              {'\n'}
              Operator steps:{'\n'}
              1. Supabase dashboard → Project Settings → JWT Keys: confirm an active signing key exists. If you recently rotated to a standby, the old token can't verify until the standby is promoted.{'\n'}
              2. Sign out and sign back in on this device so the next access-token is signed by the active key.{'\n'}
              3. Tap Save to Account again.
            </Text>
            <Text style={{ color: '#888', fontSize: 11, lineHeight: 14 }}>
              Apple Health → Coach still works via the Railway /ingest pipeline regardless — this blocker only affects the direct-to-Supabase persist path.
            </Text>
          </View>
        );
      })()}
    </View>
  );
}

// --- Expo Go notice ---

function ExpoGoNotice() {
  return (
    <View style={styles.expoGoCard}>
      <Text style={styles.expoGoTitle}>Expo Go Mode</Text>
      <Text style={styles.expoGoBody}>
        Native health sync (HealthKit / Health Connect) requires a development
        build. Manual training logging, coaching, and check-ins work here.
      </Text>
      <Text style={styles.expoGoCommand}>
        npx expo prebuild --clean{'\n'}npx expo run:ios
      </Text>
    </View>
  );
}

// --- Main screen ---

export default function HealthScreen() {
  // Inline source-info card collapse state. Default false because the
  // platform-name card duplicates info already shown by HealthActions
  // Panel + AppleHealthCard above. Testers can expand it for the
  // no-data guidance / error detail when debugging.
  const [sourceInfoOpen, setSourceInfoOpen] = useState(false);
  const permissions = useHealthStore((s) => s.permissions);
  const syncing = useHealthStore((s) => s.syncing);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const today = useHealthStore((s) => s.today);
  const days = useHealthStore((s) => s.days);
  const features = useHealthStore((s) => s.features);
  const flags = useHealthStore((s) => s.flags);
  const insights = useHealthStore((s) => s.insights);
  const coaching = useHealthStore((s) => s.coaching);
  const error = useHealthStore((s) => s.error);
  const polarViaHc = useHealthStore((s) => s.polarViaHc);
  const samsungViaHc = useHealthStore((s) => s.samsungHealthViaHc);
  const checkPermissions = useHealthStore((s) => s.checkPermissions);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);
  const syncData = useHealthStore((s) => s.syncData);
  const whoopStatus = useWhoopStore((s) => s.status);
  const whoopSourceUpdatedAt = useWhoopStore((s) => s.day?.source_updated_at ?? null);
  const whoopHasDay = useWhoopStore((s) => s.day != null);

  const authStatus = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const isMember = authStatus === 'member';

  const inExpoGo = isExpoGo();

  // Live native-availability probe so the UI reflects actual HealthKit
  // state without waiting for the async store checkPermissions to
  // settle — which was causing "Not set up" to stick even after the
  // module loaded successfully.
  const [nativeAvailable, setNativeAvailable] = useState<boolean | null>(null);
  const refreshNativeAvailability = useCallback(() => {
    if (inExpoGo || Platform.OS !== 'ios') {
      setNativeAvailable(null);
      return;
    }
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { getHealthKitNativeDebug } = require('../../src/services/health.ios');
      const d = getHealthKitNativeDebug();
      setNativeAvailable(d.isHealthDataAvailableResult ?? null);
    } catch {
      setNativeAvailable(null);
    }
  }, [inExpoGo]);

  useEffect(() => {
    refreshNativeAvailability();
    if (!inExpoGo) {
      checkPermissions();
    }
  }, [checkPermissions, inExpoGo, refreshNativeAvailability]);

  // First audit capture site — `health_source_visible` on Health-tab
  // mount per platform. Lets Aaron + the connector see post-build
  // that the un-gated primary card is actually surfacing on a real
  // device (vs a tier-store regression that hid it again). Local-
  // only, no raw health values, no network call. Capped at 200 in
  // the store so the buffer never grows unbounded.
  // Fires once on first ready render — depends on `nativeAvailable`
  // settling to a definitive boolean so the snapshot reflects the
  // device's true probe result.
  useEffect(() => {
    if (nativeAvailable == null) return;
    const platform = Platform.OS === 'ios' ? 'ios' : Platform.OS === 'android' ? 'android' : 'unknown';
    const sourceId = Platform.OS === 'ios' ? 'apple_health' : Platform.OS === 'android' ? 'health_connect' : null;
    void useAuditEventStore.getState().add({
      platform,
      appVersion: Application.nativeApplicationVersion ?? null,
      buildNumber: Application.nativeBuildVersion ?? null,
      screen: '(tabs)/health',
      eventType: nativeAvailable ? 'health_source_visible' : 'health_source_missing',
      severity: nativeAvailable ? 'info' : 'warning',
      sourceId,
      sourceState: nativeAvailable ? 'native_available' : 'native_unavailable',
      userVisibleMessage: nativeAvailable
        ? `${Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect'} card is visible on this device.`
        : `${Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect'} not available on this device.`,
    });
    // Intentional: capture only on the first definitive nativeAvailable
    // value. Toggling it later (extremely rare on a real device) is
    // a separate event class we'll wire when the rest of the capture
    // sites land.
  }, [nativeAvailable]); // eslint-disable-line react-hooks/exhaustive-deps

  const platformName = Platform.OS === 'ios' ? 'Apple HealthKit' : 'Health Connect';
  // isAvailable prefers the live native probe on iOS — if HealthKit is
  // ready on the device, the UI must not claim "not linked", even if
  // the zustand permissions state hasn't populated yet.
  const isAvailable = useMemo(() => {
    if (inExpoGo) return false;
    if (Platform.OS === 'ios' && nativeAvailable != null) return nativeAvailable;
    return permissions?.available ?? false;
  }, [inExpoGo, nativeAvailable, permissions?.available]);
  const anyAuthorized = inExpoGo
    ? false
    : permissions && permissions.permissions
      ? Object.values(permissions.permissions).some((s) => s === 'authorized')
      : false;

  // handleConnect removed — the top HealthActionsPanel owns the connect
  // path. Keeping a second Connect button here created two UX truths
  // (top panel surfaced native errors; middle button did not) and made
  // the middle card look unresponsive.

  const handleSync = () => {
    // eslint-disable-next-line no-console
    console.log('[AppleHealth] Sync tapped', { inExpoGo, isAvailable });
    if (inExpoGo) {
      Alert.alert('Expo Go', 'Sync requires a native build. Install the preview build.');
      return;
    }
    if (user?.id) syncData(user.id);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Health</Text>

      {/* TOP action panel — unmistakable buttons for Apple Health +
          WHOOP, plus a visible identity line (app version + build +
          EAS update ID + channel + bundle timestamp) so we can prove
          which code is actually running. Placed before every other
          card so no debug panel or source card can cover it. */}
      <SafeErrorBoundary label="Health actions panel">
        <HealthActionsPanel />
      </SafeErrorBoundary>

      {/* HealthKit module-load / build diagnostics — collapsed by
          default so it doesn't dominate the main screen. Testers can
          still expand it when debugging. */}
      {Platform.OS === 'ios' && <HealthKitDebugDisclosure />}

      {isExpoGo() && <ExpoGoNotice />}

      {/* Source info — folded behind a collapsed disclosure. The
          platform-name + status pill, sync button, and no-data
          guidance all already exist on AppleHealthCard / HealthActions
          Panel; this disclosure preserves the legacy detail (notably
          the iOS-specific "no data found" guidance + error line) for
          tester debugging without making the Health tab look like a
          duplicate dashboard. */}
      <View style={styles.card}>
        <Pressable
          onPress={() => setSourceInfoOpen((v) => !v)}
          hitSlop={6}
          accessibilityRole="button"
          accessibilityLabel={sourceInfoOpen ? `Hide ${platformName} detail` : `Show ${platformName} detail`}
          style={styles.cardHeaderRow}>
          <Text style={styles.cardTitle}>{platformName}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text
              style={[
                styles.availBadge,
                { color: isAvailable ? (anyAuthorized ? '#4ade80' : '#d4e157') : '#888' },
              ]}>
              {isAvailable
                ? anyAuthorized
                  ? lastSyncAt && days.length > 0
                    ? 'Connected'
                    : lastSyncAt
                      ? 'Connected — no data'
                      : 'Permission granted — sync needed'
                  : 'Ready to connect'
                : 'Not available'}
            </Text>
            <Text style={{ fontSize: 12, color: '#d4e157' }}>{sourceInfoOpen ? '▾' : '▸'}</Text>
          </View>
        </Pressable>

        {sourceInfoOpen && (<>
        {!isAvailable && !inExpoGo && Platform.OS === 'ios' && (
          <Text style={styles.unavailNote}>
            HealthKit reports as unavailable on this device. Open iOS Settings → Health and confirm Apple Health is available, then reopen Lauburu and tap Connect Apple Health at the top of this tab.
          </Text>
        )}

        {!isAvailable && !inExpoGo && Platform.OS !== 'ios' && (
          <Text style={styles.unavailNote}>
            Health Connect isn't connected here. Requires Android 14+ or the Health Connect app.
          </Text>
        )}

        {isAvailable && !anyAuthorized && (
          <Text style={styles.connectNote}>
            Tap Manage health sources above to connect. Lauburu appears in iOS Settings → Health → Data Access & Devices after you grant at least one metric.
          </Text>
        )}

        {isAvailable && anyAuthorized && (
          <>
            <View style={styles.syncRow}>
              <View>
                <Text style={styles.syncLabel}>
                  {syncing
                    ? 'Syncing health data...'
                    : lastSyncAt
                      ? days.length > 0
                        ? `Connected — last sync ${new Date(lastSyncAt).toLocaleTimeString()}`
                        : `Connected — last sync ${new Date(lastSyncAt).toLocaleTimeString()} (no data found)`
                      : 'Permission granted — tap Sync Now'}
                </Text>
                {days.length > 0 && !syncing && (
                  <Text style={styles.syncDayCount}>
                    {days.length} day{days.length !== 1 ? 's' : ''} of data
                  </Text>
                )}
              </View>
              <Pressable
                style={[styles.syncButton, syncing && { opacity: 0.5 }]}
                onPress={handleSync}
                disabled={syncing}>
                {syncing ? (
                  <ActivityIndicator size="small" color="#d4e157" />
                ) : (
                  <Text style={styles.syncButtonText}>
                    {lastSyncAt ? 'Refresh' : 'Sync Now'}
                  </Text>
                )}
              </Pressable>
            </View>

            {days.length === 0 && !syncing && lastSyncAt && (
              <View style={{ gap: 6 }}>
                <Text style={styles.noDataNote}>
                  No health records found in the last 30 days.
                </Text>
                {Platform.OS === 'android' && (
                  <Text style={styles.noDataNote}>
                    If you use Samsung Health:{'\n'}
                    1. Open Samsung Health → Settings → Health Connect{'\n'}
                    2. Tap "App permissions" → allow Samsung Health to share data{'\n'}
                    3. Go back to Samsung Health main screen to trigger a sync{'\n'}
                    4. Return here and tap Refresh{'\n\n'}
                    If you use another health app (Fitbit, Garmin, etc.):{'\n'}
                    Check that it writes to Health Connect in its settings.
                  </Text>
                )}
                {Platform.OS === 'ios' && (
                  <Text style={styles.noDataNote}>
                    Make sure Apple Health has data. Open the iOS Health app → Browse → check that metrics like Sleep, Steps, or Heart Rate have recent entries.
                  </Text>
                )}
              </View>
            )}

            {authStatus !== 'member' && (
              <Text style={styles.guestWarning}>
                Sign in to save health data to your account.
              </Text>
            )}
          </>
        )}

        {/* Only show the error line for genuine runtime errors. The
            "Health service unavailable" placeholder is already conveyed
            by the red Not Available badge + the explanatory note above,
            so duplicating it as a red error line reads like a crash. */}
        {error && error !== 'Health service unavailable' && (
          <Text style={styles.errorText}>{error}</Text>
        )}
        </>)}
      </View>

      {/* Permissions detail — collapsed by default. The list is
          verbose and dominated the page; summary chip + disclosure
          keeps the info available without clutter. */}
      {permissions && permissions.permissions && isAvailable && (
        <PermissionsDisclosure permissions={permissions.permissions} />
      )}

      {/* Nutrition — promoted here from the old mid-page slot so it's
          discoverable right under the source/connection area. The card
          exposes Search food / Barcode / Manual / Usual routine / AI
          photo modes and feeds the merged nutrition summary + Coach
          read-path on every add. */}
      <SafeErrorBoundary label="Nutrition card">
        <NutritionCard />
      </SafeErrorBoundary>

      {/* Training insights — main guidance card */}
      {insights && (
        <SafeErrorBoundary label="Insights card">
          <InsightsCard insights={insights} />
        </SafeErrorBoundary>
      )}

      {/* Structured coaching */}
      {coaching && coaching.readiness?.level !== 'grey' && (
        <SafeErrorBoundary label="Coaching card">
          <CoachingCard coaching={coaching} />
        </SafeErrorBoundary>
      )}

      {/* Flags */}
      {flags.length > 0 && (
        <SafeErrorBoundary label="Flags card">
          <FlagsCard flags={flags} />
        </SafeErrorBoundary>
      )}

      {/* Today's data */}
      {today && (
        <SafeErrorBoundary label="Today card">
          <TodayCard today={today} />
        </SafeErrorBoundary>
      )}

      {/* Legacy unified WhoopCard removed — WhoopDirectCard below is
          the canonical WHOOP Direct surface (status pill + sync +
          backfill + disconnect actions + truthful copy). Removing the
          duplicate de-clutters the Health feed without losing any
          user-facing functionality; readiness/today still displays
          via TodayCard. */}

      {/* Nutrition is app-first: Apple Health dietary import + manual
          + search + barcode + AI photo. Rendered much higher on this
          tab — it's one of the most-used surfaces, so it sits right
          under the source/connection area, not buried at the bottom. */}

      {/* ── Primary / relevant source cards ─────────────────────
          Shown by default:
          - Apple Health card on iOS, Samsung/HC cards on Android
          - WHOOP Direct (proprietary readiness — keep regardless of OS)
          - Polar cards only when Polar-via-HC provenance was actually
            detected or the user tapped Connect
          Cronometer + Concept2 + FTMS/BLE machine capture are all OUT
          of the Health screen. Machine capture moved to the Train tab
          where it belongs as part of session execution. Cronometer and
          Concept2 are not in the active product path. */}
      {/* PRIMARY platform health source. NOT tier-gated — Apple
          Health on iOS and Health Connect on Android are the
          baseline product, available to every signed-in user
          regardless of tier. Tier gating goes around AI narrative
          / paid features, never the primary source connection. */}
      {Platform.OS === 'ios' && (
        <SafeErrorBoundary label="Apple Health card">
          <AppleHealthCard />
        </SafeErrorBoundary>
      )}
      {Platform.OS === 'android' && (
        <SafeErrorBoundary label="Health Connect availability hint">
          <HealthConnectAvailabilityHint />
        </SafeErrorBoundary>
      )}
      {Platform.OS === 'android' && (
        <SafeErrorBoundary label="Samsung Health card">
          <SamsungHealthCard />
        </SafeErrorBoundary>
      )}
      {/* WHOOP Direct + Polar Direct moved into the "More sources"
          disclosure to keep the default Health view focused on the
          platform's primary source (Apple Health on iOS, Health
          Connect / Samsung on Android). They surface at the top here
          ONLY when there's already an active connection or detected
          provenance — never as default clutter for users who don't
          use those services. */}
      {isMember && whoopStatus === 'ready' && (
        <SafeErrorBoundary label="WHOOP Direct card">
          <WhoopDirectCard />
        </SafeErrorBoundary>
      )}
      {isMember && polarViaHc?.detected && (
        <SafeErrorBoundary label="Polar card">
          <PolarCard viaHealthConnect={polarViaHc} />
        </SafeErrorBoundary>
      )}
      {/* Health Connect provenance card — Android-only + only when
          provenance was actually detected. Hiding on iOS unconditionally. */}
      {isMember && Platform.OS === 'android' && (polarViaHc?.detected || samsungViaHc?.detected) && (
        <SafeErrorBoundary label="Health Connect provenance card">
          <HealthConnectProvenanceCard />
        </SafeErrorBoundary>
      )}

      {/* Machine capture is owned by the Train tab, not Health.
          Pair BLE HR strap / FTMS machine, see live HR/power, and
          save sessions all happen in Train. Health stays focused on
          Apple Health / WHOOP / enrichment / source status. */}

      {/* Long-term data sync — relocated into the connection-sources
          area so it sits next to Apple Health / WHOOP / Polar / CSV
          import rather than dominating the main metrics feed. Railway
          primary save lives here; Supabase mirror remains optional
          redundancy. */}
      <SafeErrorBoundary label="Backend sync card">
        <BackendSyncCard />
      </SafeErrorBoundary>

      {/* Advanced — reserved for future advanced source info. Empty
          for now since Cronometer/Concept2/machine capture are all
          out of the health-source path. Kept as a placeholder if we
          need to reintroduce an advanced diagnostic later. */}
      {isMember && (
        <OtherSourcesDisclosure
          polarDetected={!!polarViaHc?.detected}
          samsungDetected={!!samsungViaHc?.detected}
          whoopConnected={whoopStatus === 'ready'}
        />
      )}

      {/* Memory proposal review — shows trend candidates + weekly promotion candidates */}
      {isMember && (
        <SafeErrorBoundary label="Memory proposal review">
          <MemoryProposalReview />
        </SafeErrorBoundary>
      )}

      {/* Sync diagnostics — tester-facing, collapsible */}
      <SafeErrorBoundary label="Sync diagnostics card">
        <SyncDiagnosticsCard />
      </SafeErrorBoundary>

      {/* 7-day trends */}
      {features && (
        <SafeErrorBoundary label="Trends card">
          <TrendsCard features={features} />
        </SafeErrorBoundary>
      )}

      {/* Backend sync moved up into the connection-sources area. */}

      {/* Recent days */}
      {days.length > 0 && (
        <SafeErrorBoundary label="Recent days card">
          <RecentDays days={days} />
        </SafeErrorBoundary>
      )}

      {/* "Data Sources" status duplicate-card removed — the same per-
          source status (Apple Health / Health Connect / WHOOP Direct /
          Samsung via HC / Polar via HC) is already shown by the
          source-specific cards higher up in the connections area. The
          import-history summary that lived in this card is preserved
          in a compact strip below so the totals/window remain visible
          without re-listing every source. */}
      <SafeErrorBoundary label="Data sources history">
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Imported history</Text>
          <DataSourcesHistorySummary />
        </View>
      </SafeErrorBoundary>
    </ScrollView>
  );
}

type DataStatus =
  | 'live'
  | 'authorized_no_data'
  | 'not_connected'
  | 'unavailable'
  | 'denied'
  | 'via_website'
  | 'future';

const DATA_STATUS_LABELS: Record<DataStatus, { text: string; color: string }> = {
  live: { text: 'Live', color: '#4ade80' },
  authorized_no_data: { text: 'Connected — no data yet', color: '#d4e157' },
  not_connected: { text: 'Not connected', color: '#999' },
  unavailable: { text: 'Not available', color: '#666' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  via_website: { text: 'Via website sync', color: '#d4e157' },
  future: { text: 'Coming soon', color: '#555' },
};

function StatusRow({ label, status }: { label: string; status: DataStatus }) {
  const info = DATA_STATUS_LABELS[status];
  return (
    <View style={styles.sourceRow}>
      <Text style={styles.sourceName}>{label}</Text>
      <View style={styles.statusDotRow}>
        <View style={[styles.statusDotSmall, { backgroundColor: info.color }]} />
        <Text style={[styles.sourceStatus, { color: info.color }]}>{info.text}</Text>
      </View>
    </View>
  );
}

/**
 * Derives the Health Connect source-row status from mobile-only signals.
 * Intentionally stricter than just "authorized=true" — Health Connect is
 * only "connected" once at least one sync has succeeded and surfaced
 * data. Permission-granted-without-sync is its own state; it must not
 * display as connected because the backend hasn't received an ingest.
 */
/**
 * Derives Apple Health source-row status with sync-awareness.
 * Same pattern as Health Connect — permission alone is not "connected."
 */
/**
 * Small summary strip under the Data Sources header that exposes the
 * current history depth in use. Per-source rows show connection state;
 * this strip shows how deep the data actually goes, so users and Coach
 * can tell whether the AI is reasoning on 30d / 365d / 5y of history.
 */
function DataSourcesHistorySummary() {
  const historyWindowDays = useHealthStore((s) => s.historyWindowDays);
  const lastBackfillAt = useHealthStore((s) => s.lastBackfillAt);
  const normalizedDays = useHealthStore((s) => s.lastSyncDiagnostics?.normalizedDays ?? 0);
  if (historyWindowDays == null && normalizedDays === 0) return null;
  const window = historyWindowDays != null ? `${historyWindowDays}d` : '—';
  const backfill = lastBackfillAt
    ? ` · last backfill ${new Date(lastBackfillAt).toLocaleDateString()}`
    : '';
  return (
    <Text style={styles.sourceGroupLabel}>
      history window: {window} · {normalizedDays} days normalized{backfill}
    </Text>
  );
}

function deriveAppleHealthRowStatus(input: {
  isAvailable: boolean;
  anyAuthorized: boolean;
  syncing: boolean;
  lastSyncAt: string | null;
  hasAnyDays: boolean;
  error: string | null;
}): string {
  if (!input.isAvailable) return 'not_set_up';
  // Successful sync wins over a stale error. The store's single `error`
  // field is shared between sync + persist paths — so a failed backend
  // persist used to flip this row to "error_retry" even when the
  // on-device Apple Health sync itself succeeded. If we have synced
  // records AND a lastSyncAt stamp, treat the source as connected.
  if (input.error && !(input.hasAnyDays && input.lastSyncAt)) return 'error_retry';
  if (input.syncing) return 'syncing';
  if (!input.anyAuthorized) return 'available';
  if (!input.lastSyncAt) return 'permission_granted_sync_needed';
  if (!input.hasAnyDays) return 'partial_missing';
  return 'connected_last_synced';
}

function deriveHealthConnectRowStatus(input: {
  isAvailable: boolean;
  anyAuthorized: boolean;
  syncing: boolean;
  lastSyncAt: string | null;
  hasAnyDays: boolean;
  error: string | null;
}): string {
  if (!input.isAvailable) return 'not_set_up';
  if (input.error && !(input.hasAnyDays && input.lastSyncAt)) return 'error_retry';
  if (input.syncing) return 'syncing';
  if (!input.anyAuthorized) return 'available';
  if (!input.lastSyncAt) return 'permission_granted_sync_needed';
  if (!input.hasAnyDays) return 'partial_missing';
  return 'connected_last_synced';
}

function SourceRow({
  name,
  status,
}: {
  name: string;
  status: string;
}) {
  const labels: Record<string, { text: string; color: string }> = {
    connected: { text: 'Connected', color: '#4ade80' },
    available: { text: 'Available', color: '#a8b84a' },
    not_available: { text: 'Not available', color: '#666' },
    not_set_up: { text: 'Not set up', color: '#888' },
    supported: { text: 'Native', color: '#4ade80' },
    ios_only: { text: 'iOS only', color: '#555' },
    android_only: { text: 'Android only here', color: '#555' },
    checking_backend: getSeedBackendStatusCopy('checking_backend'),
    seed_backend: getSeedBackendStatusCopy('seed_backend'),
    fresh_seed_backend: getSeedBackendStatusCopy('fresh_seed_backend'),
    stale_seed_backend: getSeedBackendStatusCopy('stale_seed_backend'),
    degraded_backend: getSeedBackendStatusCopy('degraded_backend'),
    backend_error: { text: 'Backend error', color: '#ff6b6b' },
    not_connected_backend: { text: 'Not connected yet', color: '#888' },
    scaffolded: { text: 'Scaffolded', color: '#7a8b3a' },
    coming_soon: { text: 'Coming soon', color: '#555' },
    permission_granted_sync_needed: { text: 'Permission granted — sync needed', color: '#d4e157' },
    syncing: { text: 'Syncing…', color: '#d4e157' },
    connected_last_synced: { text: 'Connected · recently synced', color: '#4ade80' },
    partial_missing: { text: 'Partial — some data missing', color: '#d4e157' },
    error_retry: { text: 'Error — tap to retry', color: '#ff6b6b' },
    polar_scaffold: { text: 'Direct Polar not live yet', color: '#888' },
    polar_via_hc_detected: { text: 'Polar via Health Connect detected', color: '#4ade80' },
    polar_via_hc_partial: { text: 'Partial Polar data via Health Connect', color: '#d4e157' },
    samsung_via_hc_detected: { text: 'Samsung Health via Health Connect', color: '#4ade80' },
    samsung_via_hc_partial: { text: 'Partial Samsung data via HC', color: '#d4e157' },
    config_check_needed: { text: 'Check integration card below', color: '#666' },
    ble_not_linked: { text: 'Machine capture lives in Train tab', color: '#888' },
    ble_ready: { text: 'Ready to scan', color: '#d4e157' },
    ble_scanning: { text: 'Scanning…', color: '#d4e157' },
    ble_connected: { text: 'Connected', color: '#4ade80' },
    ble_manual_fallback: { text: 'Manual fallback', color: '#a8b84a' },
  };
  const info = labels[status] ?? { text: status, color: '#666' };
  return (
    <View style={styles.sourceRow}>
      <Text style={styles.sourceName}>{name}</Text>
      <Text style={[styles.sourceStatus, { color: info.color }]}>{info.text}</Text>
    </View>
  );
}

/**
 * Compact disclosure reserved for future advanced source diagnostics.
 * Empty by design right now — Cronometer and Concept2 are out of the
 * active product path; machine capture moved to the Train tab where
 * session execution owns it.
 */
function PermissionsDisclosure({ permissions }: { permissions: Record<string, PermissionStatus> }) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(permissions) as [HealthMetricType, PermissionStatus][];
  const authorized = entries.filter(([, s]) => s === 'authorized').length;
  const summary = `${authorized}/${entries.length} metrics authorized`;
  return (
    <View style={[styles.card, { gap: 6 }]}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide permissions detail' : 'Show permissions detail'}
        style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={styles.cardTitle}>Permissions</Text>
        <Text style={{ fontSize: 12, color: '#d4e157' }}>{open ? '▾ Hide' : `▸ ${summary}`}</Text>
      </Pressable>
      {open && (
        <View style={{ gap: 4, marginTop: 4 }}>
          {entries.map(([metric, status]) => (
            <PermissionRow key={metric} metric={metric} status={status} />
          ))}
        </View>
      )}
    </View>
  );
}

function HealthKitDebugDisclosure() {
  const [open, setOpen] = useState(false);
  return (
    <View style={[styles.card, { gap: 6 }]}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide HealthKit debug' : 'Show HealthKit debug'}
        style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={styles.cardTitle}>HealthKit debug</Text>
        <Text style={{ fontSize: 12, color: '#d4e157' }}>{open ? '▾ Hide' : '▸ Show'}</Text>
      </Pressable>
      {!open && (
        <Text style={styles.gateText}>
          Module-load + build-number diagnostics for testers. Expand if Connect/Sync misbehaves.
        </Text>
      )}
      {open && (
        <SafeErrorBoundary label="HealthKit debug">
          <HealthKitDebugCard />
        </SafeErrorBoundary>
      )}
    </View>
  );
}

function OtherSourcesDisclosure({
  polarDetected,
  samsungDetected: _samsungDetected,
  whoopConnected,
}: {
  polarDetected: boolean;
  samsungDetected: boolean;
  whoopConnected: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <View style={[styles.card, { gap: 6 }]}>
      <Pressable
        onPress={() => setOpen((v) => !v)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide more sources' : 'Show more sources'}
        style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={styles.cardTitle}>More sources</Text>
        <Text style={{ fontSize: 12, color: '#d4e157' }}>{open ? '▾ Hide' : '▸ Add another source'}</Text>
      </Pressable>
      {!open && (
        <Text style={styles.gateText}>
          Add WHOOP, Polar, or other less-common sources. Bluetooth machine capture lives in the Train tab.
        </Text>
      )}
      {open && (
        <View style={{ gap: 12, marginTop: 6 }}>
          {!whoopConnected && (
            <SafeErrorBoundary label="WHOOP Direct card">
              <WhoopDirectCard />
            </SafeErrorBoundary>
          )}
          {!polarDetected && (
            <SafeErrorBoundary label="Polar Direct card">
              <PolarDirectCard />
            </SafeErrorBoundary>
          )}
          <Text style={styles.gateText}>
            Bluetooth heart-rate straps and FTMS bikes/rowers/ski-ergs live on the Train tab so they pair as part of a session. Cronometer and Concept2 are not in the active product path.
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },

  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },

  availBadge: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  unavailNote: { fontSize: 13, opacity: 0.6, lineHeight: 18 },

  connectButton: {
    backgroundColor: '#d4e157',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  connectText: { color: '#0a0a0a', fontSize: 16, fontWeight: '600' },

  syncRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  syncLabel: { fontSize: 13, opacity: 0.6 },
  syncButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#d4e157',
  },
  syncButtonText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },

  guestWarning: {
    fontSize: 12,
    color: '#d4e157',
    opacity: 0.8,
  },

  errorText: { fontSize: 13, color: '#ff6b6b' },

  // Permissions
  permRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  permLabel: { fontSize: 14 },
  permStatus: { fontSize: 13, fontWeight: '600' },

  // Today's metrics
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metricBox: {
    width: '30%',
    alignItems: 'center',
    gap: 2,
    paddingVertical: 8,
  },
  metricValue: { fontSize: 24, fontWeight: '700', color: '#d4e157' },
  metricUnit: { fontSize: 11, opacity: 0.5 },
  metricLabel: { fontSize: 11, opacity: 0.6, textAlign: 'center' },

  // Workouts
  workoutSection: { gap: 6, marginTop: 4 },
  workoutHeader: { fontSize: 14, fontWeight: '600', opacity: 0.8 },
  workoutRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  workoutName: { fontSize: 13 },
  workoutSource: { fontSize: 10, opacity: 0.35, marginTop: 1 },
  workoutMetaCol: { alignItems: 'flex-end' as const, gap: 1 },
  workoutMeta: { fontSize: 12, opacity: 0.5 },

  // Recent days
  dayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.04)',
  },
  dayDate: { fontSize: 13, fontWeight: '600' },
  dayMetrics: { fontSize: 12, opacity: 0.6 },

  // Sources
  sourceGroupLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 8,
  },
  sourceList: { gap: 6 },
  sourceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  sourceName: { fontSize: 14 },
  sourceStatus: { fontSize: 13, fontWeight: '600' },
  statusDotRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  statusDotSmall: { width: 6, height: 6, borderRadius: 3 },
  syncTimestamp: { fontSize: 11, opacity: 0.4, marginTop: 4 },

  // Insights
  readinessHeader: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  readinessDot: { width: 14, height: 14, borderRadius: 7, marginTop: 3 },
  readinessText: { flex: 1, gap: 4 },
  readinessLabel: { fontSize: 18, fontWeight: '700' },
  readinessSummary: { fontSize: 14, opacity: 0.8, lineHeight: 20 },
  keyMetricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
    marginTop: 4,
  },
  keyMetric: { alignItems: 'center', gap: 2 },
  keyMetricValue: { fontSize: 18, fontWeight: '700' },
  keyMetricLabel: { fontSize: 11, opacity: 0.5 },
  reasonsList: { gap: 3, marginTop: 2 },
  reasonText: { fontSize: 13, opacity: 0.8, lineHeight: 18 },
  dataNoteText: { fontSize: 11, opacity: 0.35, marginTop: 6 },

  // Coaching
  coachSection: { gap: 4 },
  coachSectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase' as const,
    opacity: 0.5,
    letterSpacing: 0.5,
  },
  coachDetail: { fontSize: 14, opacity: 0.85, lineHeight: 20 },
  coachBody: { fontSize: 13, opacity: 0.7 },
  coachSuggestion: { fontSize: 13, color: '#d4e157', opacity: 0.9 },
  coachStatusRow: {
    flexDirection: 'row' as const,
    justifyContent: 'space-around' as const,
    paddingVertical: 8,
  },
  coachStatusItem: { alignItems: 'center' as const, gap: 2 },
  coachStatusValue: { fontSize: 14, fontWeight: '700', textTransform: 'capitalize' as const },
  coachStatusLabel: { fontSize: 10, opacity: 0.5 },
  coachAction: { fontSize: 13, opacity: 0.7, lineHeight: 18 },
  coachPrefs: { gap: 2, marginTop: 4 },
  coachPrefText: { fontSize: 11, color: '#d4e157', opacity: 0.6 },
  coachConfidence: { fontSize: 10, opacity: 0.3, marginTop: 6 },
  gateText: { fontSize: 13, opacity: 0.5, lineHeight: 18 },
  connectNote: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
  syncDayCount: { fontSize: 11, opacity: 0.4, marginTop: 2 },
  noDataNote: { fontSize: 13, opacity: 0.5, lineHeight: 18, fontStyle: 'italic' },

  // Expo Go
  expoGoCard: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.2)',
    gap: 8,
  },
  expoGoTitle: { fontSize: 16, fontWeight: '600', color: '#d4e157' },
  expoGoBody: { fontSize: 13, opacity: 0.7, lineHeight: 18 },
  expoGoCommand: {
    fontSize: 11,
    fontFamily: 'SpaceMono',
    opacity: 0.5,
    backgroundColor: 'rgba(0,0,0,0.3)',
    padding: 8,
    borderRadius: 6,
    overflow: 'hidden',
  },

  // Flags
  flagText: { fontSize: 13, lineHeight: 18 },

  // Trends
  trendsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  trendItem: { width: '45%', gap: 2 },
  trendLabel: { fontSize: 12, opacity: 0.6 },
  trendValue: { fontSize: 16, fontWeight: '600' },
  trendMeta: { marginTop: 8, gap: 2 },
  trendMetaText: { fontSize: 11, opacity: 0.4 },
});
