import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
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
import { useAuditEventStore } from '../../src/store/audit-event-store';
import { useDevUnlockStore } from '../../src/store/dev-unlock-store';
import { isExpoGo } from '../../src/services/expo-detect';
import { AthleteCapabilitySummary } from '../../src/components/AthleteCapabilitySummary';
import { NutritionCard } from '../../src/components/NutritionCard';
import { getSeedBackendStatusCopy } from '../../src/services/athlete-capability-display';
import { MemoryProposalReview } from '../../src/components/MemoryProposalReview';
import { SyncDiagnosticsCard } from '../../src/components/SyncDiagnosticsCard';
import { HealthKitDebugCard } from '../../src/components/HealthKitDebugCard';
import { HealthActionsPanel } from '../../src/components/HealthActionsPanel';
import { SafeErrorBoundary } from '../../src/components/SafeErrorBoundary';
import { useWhoopStore } from '../../src/store/whoop-store';
import { getNativeHealthSourceCopy, getReadinessSeedBadge } from '../../src/services/health-source-ui';
import {
  buildConditioningImportSummaries,
  CONDITIONING_IMPORT_COPY,
  friendlySourceApp,
  sourceTypeLabel,
  type ConditioningImportSummary,
} from '../../src/services/conditioning-imports';
import type { HealthMetricType, PermissionStatus, DailyMetrics, DerivedFeatures, CoachingResponse } from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';

const ADMIN_EMAILS = new Set(['aaron.t.maher@gmail.com']);

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
      <Text style={styles.cardTitle}>Recovery metrics — {today.date}</Text>
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
                  <Text style={styles.workoutSource}>{friendlySourceApp(w.source)}</Text>
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

function ConditioningImportsCard({
  summaries,
  sourceType,
}: {
  summaries: ConditioningImportSummary[];
  sourceType: 'apple_health' | 'health_connect';
}) {
  const visible = summaries.slice(0, 3);
  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>{CONDITIONING_IMPORT_COPY.title}</Text>
        <Text style={styles.importBadge}>{sourceTypeLabel(sourceType)}</Text>
      </View>
      <Text style={styles.importBody}>{CONDITIONING_IMPORT_COPY.body}</Text>
      <Text style={styles.importSubtle}>{CONDITIONING_IMPORT_COPY.examples}</Text>

      {visible.length > 0 ? (
        <View style={styles.importList}>
          {visible.map((item, index) => (
            <View key={`${item.startTime ?? 'workout'}-${index}`} style={styles.importRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.importName}>
                  {item.workoutType === 'unknown' ? 'Conditioning' : item.workoutType.replace('_', ' ')}
                </Text>
                <Text style={styles.importSource}>Workout summary imported · {item.provenanceLabel}</Text>
                {item.missingIntervalLabel && (
                  <Text style={styles.importMissing}>{item.missingIntervalLabel}</Text>
                )}
              </View>
              <View style={styles.importMetaCol}>
                <Text style={styles.importMeta}>{item.durationMin}min</Text>
                {(item.calories || item.distanceM) ? (
                  <Text style={styles.importMeta}>
                    {item.calories ? `${Math.round(item.calories)}cal` : ''}
                    {item.calories && item.distanceM ? ' · ' : ''}
                    {item.distanceM ? `${(item.distanceM / 1000).toFixed(1)}km` : ''}
                  </Text>
                ) : null}
                {(item.avgHr || item.maxHr) ? (
                  <Text style={styles.importMeta}>
                    {item.avgHr ? `${Math.round(item.avgHr)} avg HR` : ''}
                    {item.avgHr && item.maxHr ? ' · ' : ''}
                    {item.maxHr ? `${Math.round(item.maxHr)} max` : ''}
                  </Text>
                ) : null}
              </View>
            </View>
          ))}
        </View>
      ) : (
        <Text style={styles.importMissing}>
          No conditioning workouts imported yet. Sync after your workout app writes
          to {sourceTypeLabel(sourceType)}.
        </Text>
      )}

      <Text style={styles.importSubtle}>{CONDITIONING_IMPORT_COPY.future}</Text>
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
  const whoopDay = useWhoopStore((s) => s.day);
  const whoopFetchedAt = useWhoopStore((s) => s.fetchedAt);
  const seedBadge = getReadinessSeedBadge({
    hasLiveWhoopRecovery: whoopDay?.recovery_score != null,
    confidenceLevel: insights.readiness === 'grey' ? 'low' : null,
  });
  const statusColors: Record<string, string> = {
    good: '#4ade80',
    caution: '#d4e157',
    warning: '#ff6b6b',
    neutral: '#999',
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Grappler Readiness</Text>
        <View style={[styles.seedBadge, seedBadge.provisional ? styles.seedBadgeProvisional : styles.seedBadgeLive]}>
          <Text style={[styles.seedBadgeText, seedBadge.provisional ? styles.seedBadgeTextSeed : styles.seedBadgeTextLive]}>
            {seedBadge.provisional ? 'Seed / provisional' : seedBadge.label}
          </Text>
        </View>
      </View>

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
      <Text style={styles.seedNoteText}>
        {seedBadge.note}
        {whoopFetchedAt && !seedBadge.provisional ? ` WHOOP checked ${new Date(whoopFetchedAt).toLocaleTimeString()}.` : ''}
      </Text>
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

function PlannedHealthContextCard({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  const items = [
    {
      title: 'Blood test upload',
      body: 'Planned file/context import. Not connected and not used for readiness yet.',
    },
    {
      title: 'DEXA upload',
      body: 'Planned body-composition context. No upload flow in this build.',
    },
    {
      title: 'Journal / check-in',
      body: 'Planned journal expansion. Check-in and manual training logs remain available now.',
    },
  ];
  return (
    <View style={styles.card}>
      <Pressable
        style={styles.cardHeaderRow}
        onPress={onToggle}
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide planned health context' : 'Show planned health context'}>
        <Text style={styles.cardTitle}>Planned health context</Text>
        <View style={styles.headerRightRow}>
          <Text style={styles.importBadge}>Planned</Text>
          <Text style={styles.disclosureChevron}>{open ? 'Hide' : 'Show'}</Text>
        </View>
      </Pressable>
      <Text style={styles.importSubtle}>
        Future context only. No upload flow here and no readiness change.
      </Text>
      {open && (
        <View style={styles.plannedList}>
          {items.map((item) => (
            <View key={item.title} style={styles.plannedRow}>
              <Text style={styles.plannedTitle}>{item.title}</Text>
              <Text style={styles.plannedBody}>{item.body}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

// --- Expo Go notice ---

function ExpoGoNotice() {
  return (
    <View style={styles.expoGoCard}>
      <Text style={styles.expoGoTitle}>Preview build needed</Text>
      <Text style={styles.expoGoBody}>
        Health sync needs the installed preview app. Training logs,
        coaching, and check-ins still work here.
      </Text>
    </View>
  );
}

// --- Main screen ---

export default function HealthScreen() {
  // Inline source-info card collapse state. Default false because the
  // platform-name card duplicates info already shown by HealthActions
  // Panel. Testers can expand it for the no-data guidance / error
  // detail when debugging.
  const [sourceInfoOpen, setSourceInfoOpen] = useState(false);
  const [plannedContextOpen, setPlannedContextOpen] = useState(false);
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
  const devUnlocked = useDevUnlockStore((s) => s.unlocked);
  const userEmail = user?.email?.toLowerCase() ?? null;
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail);
  const showDeveloperDiagnostics = isAdmin || (__DEV__ && devUnlocked);
  const hasImportedHistory = useHealthStore(
    (s) => s.historyWindowDays != null || (s.lastSyncDiagnostics?.normalizedDays ?? 0) > 0,
  );
  const conditioningSourceType = Platform.OS === 'ios' ? 'apple_health' : 'health_connect';
  const conditioningImports = useMemo(
    () => buildConditioningImportSummaries(
      days.flatMap((day) => day.workouts ?? []),
      conditioningSourceType,
    ).slice(0, 8),
    [days, conditioningSourceType],
  );

  const inExpoGo = isExpoGo();
  const nativeCopy = useMemo(() => getNativeHealthSourceCopy(Platform.OS), []);

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
  //
  // Platform-specific availability source:
  //   - iOS: `nativeAvailable` (the live HealthKit probe via
  //     refreshNativeAvailability) is the right signal.
  //   - Android: `nativeAvailable` stays null because the iOS-only
  //     refresh path doesn't run; instead we read `permissions?.
  //     available` from the platform-aware health-store, which
  //     reflects Health Connect's getSdkStatus() probe.
  // Use a ref to fire-once per platform-availability state so the
  // store doesn't fill with duplicate events on every re-render.
  const auditFiredRef = useRef(false);
  useEffect(() => {
    if (auditFiredRef.current) return;
    let availability: boolean | null = null;
    if (Platform.OS === 'ios') {
      // iOS: wait for the live native probe to settle.
      if (nativeAvailable == null) return;
      availability = nativeAvailable;
    } else if (Platform.OS === 'android') {
      // Android: read from the health-store permissions snapshot. The
      // store calls health.android.ts isAvailable() during
      // checkPermissions() (which runs in the same useEffect block
      // above). When `permissions` is non-null, we have a definitive
      // probe result; before that, wait.
      if (permissions == null) return;
      availability = !!permissions.available;
    } else {
      return;
    }
    auditFiredRef.current = true;
    const platform = Platform.OS === 'ios' ? 'ios' : 'android';
    const sourceId = Platform.OS === 'ios' ? 'apple_health' : 'health_connect';
    const sourceLabel = nativeCopy.sourceName;
    void useAuditEventStore.getState().add({
      platform,
      appVersion: Application.nativeApplicationVersion ?? null,
      buildNumber: Application.nativeBuildVersion ?? null,
      screen: '(tabs)/health',
      eventType: availability ? 'health_source_visible' : 'health_source_missing',
      severity: availability ? 'info' : 'warning',
      sourceId,
      sourceState: availability ? 'native_available' : 'native_unavailable',
      userVisibleMessage: availability
        ? `${sourceLabel} card is visible on this device.`
        : `${sourceLabel} not available on this device.`,
    });
  }, [nativeAvailable, permissions, nativeCopy.sourceName]); // eslint-disable-line react-hooks/exhaustive-deps

  const platformName = nativeCopy.sourceName;
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

      {showDeveloperDiagnostics && Platform.OS === 'ios' && <HealthKitDebugDisclosure />}

      {isExpoGo() && <ExpoGoNotice />}

      {/* Source info — folded behind a dev-only collapsed disclosure. The
          platform-name + status pill, sync button, and no-data
          guidance all already exist on AppleHealthCard / HealthActions
          Panel; this disclosure preserves the legacy detail (notably
          the iOS-specific "no data found" guidance + error line) for
          tester debugging without making the Health tab look like a
          duplicate dashboard. */}
      {showDeveloperDiagnostics && (
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
            {Platform.OS === 'ios'
              ? 'Tap Manage health sources above to connect. Lauburu appears in iOS Settings → Health → Data Access & Devices after you grant at least one metric.'
              : 'Tap Manage health sources above to connect. Health Connect will ask which metrics Lauburu can read.'}
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
      )}

      {/* Permissions detail — collapsed by default. The list is
          verbose and dominated the page; summary chip + disclosure
          keeps the info available without clutter. */}
      {showDeveloperDiagnostics && permissions && permissions.permissions && isAvailable && (
        <PermissionsDisclosure permissions={permissions.permissions} />
      )}

      {/* Today's recovery metrics */}
      {today && (
        <SafeErrorBoundary label="Today card">
          <TodayCard today={today} />
        </SafeErrorBoundary>
      )}

      {/* Nutrition — promoted here from the old mid-page slot so it's
          discoverable right under the source/connection area. The card
          exposes Search food / Barcode / Manual / Usual routine / AI
          photo modes and feeds the merged nutrition summary + Coach
          read-path on every add. */}
      <SafeErrorBoundary label="Nutrition card">
        <NutritionCard />
      </SafeErrorBoundary>

      <SafeErrorBoundary label="Conditioning imports">
        <ConditioningImportsCard
          summaries={conditioningImports}
          sourceType={conditioningSourceType}
        />
      </SafeErrorBoundary>

      {/* Provisional/app-owned readiness */}
      {insights && (
        <SafeErrorBoundary label="Insights card">
          <InsightsCard insights={insights} />
        </SafeErrorBoundary>
      )}

      <SafeErrorBoundary label="Planned health context">
        <PlannedHealthContextCard
          open={plannedContextOpen}
          onToggle={() => setPlannedContextOpen((v) => !v)}
        />
      </SafeErrorBoundary>

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

      {/* Source-management cards (Apple Health / Health Connect,
          Backend Sync, WHOOP, Polar, exports) live inside the
          Manage health sources sheet above. Keep this feed focused on
          status, nutrition, coaching, trends, and history. */}

      {/* Memory proposal review — shows trend candidates + weekly promotion candidates */}
      {showDeveloperDiagnostics && isMember && (
        <SafeErrorBoundary label="Memory proposal review">
          <MemoryProposalReview />
        </SafeErrorBoundary>
      )}

      {showDeveloperDiagnostics && (
        <SafeErrorBoundary label="Sync diagnostics card">
          <SyncDiagnosticsCard />
        </SafeErrorBoundary>
      )}

      {/* 7-day trends */}
      {features && (
        <SafeErrorBoundary label="Trends card">
          <TrendsCard features={features} />
        </SafeErrorBoundary>
      )}

      {/* Backend sync now lives inside Manage health sources. */}

      {/* Recent days */}
      {days.length > 0 && (
        <SafeErrorBoundary label="Recent days card">
          <RecentDays days={days} />
        </SafeErrorBoundary>
      )}

      {/* The old per-source status card was removed from the main tab.
          The import-history summary stays visible without re-listing
          every source-management action. */}
      {hasImportedHistory && (
        <SafeErrorBoundary label="Data sources history">
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Imported history</Text>
            <DataSourcesHistorySummary />
          </View>
        </SafeErrorBoundary>
      )}
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
  headerRightRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  importBadge: {
    fontSize: 11,
    fontWeight: '700',
    color: '#d4e157',
    textTransform: 'uppercase',
  },
  importBody: { fontSize: 13, opacity: 0.72, lineHeight: 18 },
  importSubtle: { fontSize: 12, opacity: 0.5, lineHeight: 17 },
  disclosureChevron: { fontSize: 12, color: '#d4e157' },
  importList: { gap: 8 },
  importRow: {
    flexDirection: 'row',
    gap: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  importName: { fontSize: 13, fontWeight: '700', textTransform: 'capitalize' },
  importSource: { fontSize: 11, opacity: 0.55, marginTop: 2 },
  importMissing: { fontSize: 11, opacity: 0.5, marginTop: 3, lineHeight: 15 },
  importMetaCol: { alignItems: 'flex-end' as const, gap: 1, maxWidth: 112 },
  importMeta: { fontSize: 11, opacity: 0.58, textAlign: 'right' as const },
  plannedList: { gap: 8 },
  plannedRow: {
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
    gap: 2,
  },
  plannedTitle: { fontSize: 13, fontWeight: '700' },
  plannedBody: { fontSize: 12, opacity: 0.55, lineHeight: 16 },

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
  seedBadge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  seedBadgeProvisional: { borderColor: '#d4e157', backgroundColor: 'rgba(212,225,87,0.08)' },
  seedBadgeLive: { borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.08)' },
  seedBadgeText: { fontSize: 11, fontWeight: '700' },
  seedBadgeTextSeed: { color: '#d4e157' },
  seedBadgeTextLive: { color: '#4ade80' },
  seedNoteText: { fontSize: 12, opacity: 0.62, lineHeight: 17 },
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
