import { useState, useMemo, useEffect, useRef } from 'react';
import {
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Alert,
  Keyboard,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { LiveHrPill } from '../../src/components/LiveHrPill';
import { TrainMachineSection } from '../../src/components/TrainMachineSection';
import { WeeklyScheduleEditor } from '../../src/components/WeeklyScheduleEditor';
import { useTrainingStore } from '../../src/store/training-store';
import { useHealthStore } from '../../src/store/health-store';
import { useAuthStore } from '../../src/store/auth-store';
import { useWhoopStore } from '../../src/store/whoop-store';
import { useMachineStore } from '../../src/store/machine-store';
import { useHIITProtocolsStore, buildProgressionDelta, detectNewBest } from '../../src/store/hiit-protocols-store';
import type { SavedHIITProtocol, SavedHIITProtocolMetrics } from '../../src/store/hiit-protocols-store';
import { useHIITWorkoutStore } from '../../src/store/hiit-workout-store';
import type { HIITWorkoutRecord, HIITSetMetrics } from '@lauburu/shared';
import { modalitySupportsMachineData } from '../../src/services/machine-connector';
import { ATHLETE_CAPABILITY_COPY } from '../../src/services/athlete-capability-display';
import { ReferencePositionPicker } from '../../src/components/ReferencePositionPicker';
import type { SessionType, SessionIntensity, TrainingSession, ConditioningSubtype, ConditioningDetail, Modality, LiftingFocus, DayPlanSummary, SessionSegment, PartnerFormat, SessionSummary, SegmentType, MachineMetrics, WorkoutSource } from '@lauburu/shared';
import {
  SESSION_TYPE_LABELS, INTENSITY_LABELS, TAG_OPTIONS,
  CONDITIONING_SUBTYPE_LABELS, MODALITY_LABELS, LIFTING_FOCUS_LABELS,
  RESPIRATORY_DEVICE_LABELS, PARTNER_FORMAT_LABELS,
  buildDayPlanSummary, SCHEDULE_SESSION_LABELS,
  SESSION_PRESETS, SEGMENT_TYPE_LABELS, createDefaultSegments,
  summarizeSession, suggestTrainIntensity, suggestHIITProtocol,
  buildIntervalCoachingNote,
} from '@lauburu/shared';
import type { IntervalCoachingContext } from '@lauburu/shared';
import { usePreferencesStore } from '../../src/store/preferences-store';
import { useTimerStore } from '../../src/store/timer-store';
import type { TimerConfig } from '../../src/store/timer-store';
import { useRouter } from 'expo-router';

const SESSION_TYPES: SessionType[] = ['class', 'sparring', 'drilling', 'wrestling', 'comp', 'open_mat', 'conditioning', 'other'];
const INTENSITIES: SessionIntensity[] = ['light', 'moderate', 'hard'];
const DURATION_PRESETS = [30, 45, 60, 90, 120];

const INTENSITY_COLORS: Record<string, string> = {
  light: '#4ade80',
  moderate: '#d4e157',
  hard: '#ff6b6b',
};

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function formatDateLabel(date: string): string {
  const today = todayDate();
  if (date === today) return 'Today';
  if (date === daysAgo(1)) return 'Yesterday';
  const d = new Date(date + 'T12:00:00');
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

/**
 * Format a SavedHIITProtocolMetrics.captured_at ISO timestamp into
 * a compact relative label for the My HIIT Library browser — "today",
 * "yesterday", "3d ago", "2w ago". Returns an empty string on parse
 * failure so the UI can safely suppress the line.
 */
function formatCapturedAtRelative(isoTimestamp: string, nowMs: number): string {
  const captured = Date.parse(isoTimestamp);
  if (!Number.isFinite(captured)) return '';
  const ageMs = nowMs - captured;
  if (ageMs < 0) return 'today'; // clock skew — treat future as now
  const day = 24 * 60 * 60 * 1000;
  const days = Math.floor(ageMs / day);
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

/**
 * Format a SavedHIITProtocolMetrics snapshot into a compact multi-
 * field line suitable for the My HIIT Library browser rows. Shows
 * all meaningful fields (not capped at 3 like the pill formatter)
 * because rows have more horizontal room than pills. Returns an
 * empty string when no numeric field is populated.
 */
function formatLibraryMetricsLine(
  m: SavedHIITProtocolMetrics | undefined,
): string {
  if (!m) return '';
  const parts: string[] = [];
  if (m.distance_m != null) {
    if (m.distance_m >= 1000) {
      parts.push(`${(m.distance_m / 1000).toFixed(1)}km`);
    } else {
      parts.push(`${Math.round(m.distance_m)}m`);
    }
  }
  if (m.avg_power_w != null) parts.push(`${Math.round(m.avg_power_w)}W`);
  if (m.calories != null) parts.push(`${Math.round(m.calories)}kcal`);
  if (m.kilojoules != null) parts.push(`${Math.round(m.kilojoules)}kJ`);
  if (m.avg_hr_bpm != null) parts.push(`${Math.round(m.avg_hr_bpm)}bpm`);
  if (m.duration_min != null) parts.push(`${Math.round(m.duration_min)}min`);
  return parts.join(' · ');
}

/**
 * Days-ago threshold below which a saved protocol's best_metrics is
 * still considered a "recent PR" worth surfacing on the pill. Beyond
 * this window the 🏆 badge stops rendering — an eight-week-old PR is
 * history, not a live target, and showing it on every pill forever
 * would dilute the signal.
 */
const PR_BADGE_MAX_AGE_DAYS = 14;

/**
 * Window (in days, measured from expiry) during which a PR shows a
 * behavioral "fades in Nd" countdown instead of just the badge.
 * Chosen at 3 so the nudge only appears in the last ~20% of the
 * PR's life — enough runway to plan a session that defends or
 * beats it, without turning every pill into a countdown sign.
 */
const PR_FADE_COUNTDOWN_WARNING_DAYS = 3;

/**
 * Check whether a saved protocol has a best_metrics snapshot that is
 * (a) populated with at least one PR-eligible field and (b) captured
 * within the PR_BADGE_MAX_AGE_DAYS window. Pure function — no date
 * side effects beyond reading `now`.
 */
function hasRecentPR(
  best: SavedHIITProtocolMetrics | undefined,
  nowMs: number,
): boolean {
  if (!best) return false;
  // Must carry at least one PR-eligible field. Avg HR and duration
  // are intentionally excluded — see PR_ELIGIBLE_FIELDS in the store.
  const hasPRField =
    best.distance_m != null ||
    best.avg_power_w != null ||
    best.calories != null ||
    best.kilojoules != null;
  if (!hasPRField) return false;
  const capturedMs = Date.parse(best.captured_at);
  if (!Number.isFinite(capturedMs)) return false;
  const ageDays = (nowMs - capturedMs) / (24 * 60 * 60 * 1000);
  return ageDays >= 0 && ageDays <= PR_BADGE_MAX_AGE_DAYS;
}

/**
 * Compute a compact "PR fades …" countdown string when a saved
 * protocol's PR is inside the fade-warning window (the last
 * PR_FADE_COUNTDOWN_WARNING_DAYS days of the 14-day recency window).
 * Returns null otherwise so the UI can safely suppress the line.
 *
 * Behavior:
 * - Must pass hasRecentPR first (PR exists + within 14-day window).
 * - daysRemaining is floor-based so a PR captured exactly 11 days
 *   ago (daysRemaining = 3) triggers the countdown; a 10-day-old
 *   PR does not.
 * - Wording scales with remaining days:
 *     0  → "PR fades today"
 *     1  → "PR fades tomorrow"
 *     2  → "PR fades in 2d"
 *     3  → "PR fades in 3d"
 * - Capped at PR_FADE_COUNTDOWN_WARNING_DAYS so the nudge never
 *   appears earlier — noise prevention.
 *
 * Pure function — no mutation, no side effects beyond reading
 * `nowMs` the caller passes in.
 */
function getPRFadeCountdown(
  best: SavedHIITProtocolMetrics | undefined,
  nowMs: number,
): string | null {
  if (!hasRecentPR(best, nowMs)) return null;
  const capturedMs = Date.parse(best!.captured_at);
  // hasRecentPR already verified Date.parse — this re-parse is cheap.
  const ageDays = (nowMs - capturedMs) / (24 * 60 * 60 * 1000);
  const daysRemainingRaw = PR_BADGE_MAX_AGE_DAYS - ageDays;
  const daysRemaining = Math.max(0, Math.floor(daysRemainingRaw));
  if (daysRemaining > PR_FADE_COUNTDOWN_WARNING_DAYS) return null;
  if (daysRemaining === 0) return 'PR fades today';
  if (daysRemaining === 1) return 'PR fades tomorrow';
  return `PR fades in ${daysRemaining}d`;
}

/**
 * Format a saved-HIIT-protocol last-session metrics snapshot into a
 * compact "last: 5.2km · 185W · 18min" line for the Train saved-
 * protocol pill. Picks at most 3 fields in priority order so the pill
 * stays readable. Returns an empty string when nothing meaningful is
 * present — the caller should not render the line in that case.
 */
function formatSavedProtocolLastMetrics(
  m: SavedHIITProtocolMetrics | undefined,
): string {
  if (!m) return '';
  const parts: string[] = [];
  // Priority 1: distance — most universal output metric.
  if (m.distance_m != null) {
    if (m.distance_m >= 1000) {
      parts.push(`${(m.distance_m / 1000).toFixed(1)}km`);
    } else {
      parts.push(`${Math.round(m.distance_m)}m`);
    }
  }
  // Priority 2: avg power — the key HIIT effort signal.
  if (m.avg_power_w != null && parts.length < 3) {
    parts.push(`${Math.round(m.avg_power_w)}W`);
  }
  // Priority 3: calories (or kJ fallback) — a universal effort proxy
  // when no power is available.
  if (m.avg_power_w == null && parts.length < 3) {
    if (m.calories != null) parts.push(`${Math.round(m.calories)}kcal`);
    else if (m.kilojoules != null) parts.push(`${Math.round(m.kilojoules)}kJ`);
  }
  // Priority 4: avg HR when still under the cap — physiology-only
  // fallback for non-power modalities.
  if (parts.length < 3 && m.avg_hr_bpm != null) {
    parts.push(`${Math.round(m.avg_hr_bpm)}bpm`);
  }
  // Priority 5: duration, always last — provides a floor metric so
  // even duration-only snapshots render something.
  if (parts.length < 3 && m.duration_min != null) {
    parts.push(`${Math.round(m.duration_min)}min`);
  }
  return parts.length > 0 ? `last: ${parts.join(' · ')}` : '';
}

// ---------------------------------------------------------------------------
// Selector row — compact stacked selector with AI suggestion
// ---------------------------------------------------------------------------

function SelectorRow<T extends string>({
  label,
  options,
  labels,
  value,
  onChange,
  suggestion,
  suggestionLabel,
}: {
  label: string;
  options: T[];
  labels: Record<T, string>;
  value: T;
  onChange: (v: T) => void;
  suggestion?: T;
  suggestionLabel?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.selectorRow}>
      <Pressable style={styles.selectorHeader} onPress={() => setExpanded(!expanded)}>
        <Text style={styles.selectorLabel}>{label}</Text>
        <View style={styles.selectorValueRow}>
          <Text style={styles.selectorValue}>{labels[value]}</Text>
          <Text style={styles.selectorChevron}>{expanded ? '▾' : '▸'}</Text>
        </View>
      </Pressable>

      {suggestion && suggestion !== value && (
        <Pressable style={styles.aiSuggestionBubble} onPress={() => { onChange(suggestion); setExpanded(false); }}>
          <Text style={styles.aiSuggestionText}>
            AI coach suggestion: {suggestionLabel ?? labels[suggestion]}
          </Text>
        </Pressable>
      )}

      {expanded && (
        <View style={styles.selectorOptions}>
          {options.map((opt) => (
            <Pressable
              key={opt}
              style={[styles.selectorOption, value === opt && styles.selectorOptionActive]}
              onPress={() => { onChange(opt); setExpanded(false); }}>
              <Text style={[styles.selectorOptionText, value === opt && styles.selectorOptionTextActive]}>
                {labels[opt]}
              </Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Entry form
// ---------------------------------------------------------------------------

function EntryForm({
  editing,
  initialMode,
  onDone,
}: {
  editing: TrainingSession | null;
  /** Optional pre-seeded mode from the Train tab's session-type
   *  chips. Ignored when editing an existing session. */
  initialMode?: 'grappling' | 'hiit' | 'zone2' | 'weights' | null;
  /**
   * Called after a successful submit. Optional `progressionDelta`
   * carries a compact "progression vs last" string when the session
   * updated a saved protocol that already had a prior snapshot; the
   * parent uses this to decorate the post-save success banner. Null
   * when no delta is meaningful (first-ever session for the protocol,
   * non-HIIT session, no comparable fields).
   *
   * `newBestLabel` is the stronger positive-reinforcement signal —
   * set when the current session beat a PR-eligible field on the
   * matched protocol's prior best_metrics snapshot. Rendered above
   * the delta line in the banner when present.
   */
  onDone: (
    progressionDelta?: string | null,
    newBestLabel?: string | null,
  ) => void;
}) {
  const addSession = useTrainingStore((s) => s.addSession);
  const editSession = useTrainingStore((s) => s.editSession);
  const syncData = useHealthStore((s) => s.syncData);
  const insights = useHealthStore((s) => s.insights);
  const user = useAuthStore((s) => s.user);
  const timerSetup = useTimerStore((s) => s.setup);
  const router = useRouter();

  // Reactive AI intensity suggestion — reads WHOOP + insights + recent load
  const whoopDay = useWhoopStore((s) => s.day);
  const recentSessions = useTrainingStore((s) => s.sessions);
  const aiIntensity = useMemo(
    () =>
      suggestTrainIntensity({
        whoopDay,
        insights,
        recentSessions,
        todayIsoDate: todayDate(),
      }),
    [whoopDay, insights, recentSessions],
  );

  // Recovery-aware HIIT protocol suggestion — only computed when relevant,
  // but useMemo keeps it stable across renders.
  const hiitSuggestion = useMemo(
    () =>
      suggestHIITProtocol({
        whoopDay,
        insights,
        recentSessions,
        todayIsoDate: todayDate(),
      }),
    [whoopDay, insights, recentSessions],
  );

  // Most recent previous HIIT session (for the Repeat-last quick action).
  const lastHIITSession = useMemo(() => {
    return [...recentSessions]
      .filter(
        (s) =>
          s.type === 'conditioning' &&
          s.conditioning?.subtype === 'hiit' &&
          s.conditioning.interval != null,
      )
      .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  }, [recentSessions]);

  // Top-level mode: Grappling / HIIT / Steady State / Weights
  type TopMode = 'grappling' | 'hiit' | 'zone2' | 'weights' | null;
  const [topMode, setTopMode] = useState<TopMode>(
    editing ? (editing.type === 'conditioning'
      ? (editing.conditioning?.subtype === 'weight_training' ? 'weights'
        : editing.conditioning?.subtype === 'zone2' || editing.conditioning?.subtype === 'steady_state' || editing.conditioning?.subtype === 'recovery_cardio' ? 'zone2'
        : 'hiit')
      : 'grappling')
    : (initialMode ?? null),
  );
  // When the Train tab pre-seeds a mode via the session-type chips,
  // run the same cascading initialisation `selectTopMode` runs (sets
  // sessionType, condSubtype, default segments, default duration,
  // etc.). Fires exactly once on mount so manual re-selects still work.
  const initialModeAppliedRef = useRef(false);

  const [sessionType, setSessionType] = useState<SessionType>(editing?.type ?? 'class');
  const [intensity, setIntensity] = useState<SessionIntensity>(editing?.intensity ?? 'moderate');
  const [duration, setDuration] = useState(editing?.duration_min ?? 60);
  const [rounds, setRounds] = useState(editing?.rounds?.toString() ?? '');
  const [rpe, setRpe] = useState(editing?.rpe?.toString() ?? '');
  const [notes, setNotes] = useState(editing?.notes ?? '');
  const [selectedTags, setSelectedTags] = useState<string[]>(editing?.tags ?? ['no-gi']);

  const [condSubtype, setCondSubtype] = useState<ConditioningSubtype>(
    editing?.conditioning?.subtype ?? 'hiit',
  );
  const [condModality, setCondModality] = useState<Modality>(
    editing?.conditioning?.modality ?? 'assault_bike',
  );
  const [workDur, setWorkDur] = useState(editing?.conditioning?.interval?.work_duration_s?.toString() ?? '30');
  const [restDur, setRestDur] = useState(editing?.conditioning?.interval?.rest_duration_s?.toString() ?? '30');
  const [intervalRounds, setIntervalRounds] = useState(editing?.conditioning?.interval?.rounds?.toString() ?? '10');
  const [intervalLabel, setIntervalLabel] = useState(editing?.conditioning?.interval?.label ?? '');
  const [liftFocus, setLiftFocus] = useState<LiftingFocus>(
    editing?.conditioning?.weight_training?.focus ?? 'strength',
  );

  // Respiratory state
  const [respType, setRespType] = useState<import('@lauburu/shared').RespiratoryType>(
    editing?.conditioning?.respiratory?.respiratory_type ?? 'inspiratory',
  );
  const [respDevice, setRespDevice] = useState<import('@lauburu/shared').RespiratoryDevice>(
    (editing?.conditioning?.respiratory?.device_used as any) ?? 'none',
  );
  const [respResistance, setRespResistance] = useState(editing?.conditioning?.respiratory?.resistance_level?.toString() ?? '');
  const [respBreaths, setRespBreaths] = useState(editing?.conditioning?.respiratory?.breaths?.toString() ?? '30');
  const [respSets, setRespSets] = useState(editing?.conditioning?.respiratory?.sets?.toString() ?? '3');
  const [respTiming, setRespTiming] = useState<'pre_training' | 'post_training' | 'standalone'>(
    editing?.conditioning?.respiratory?.timing ?? 'standalone',
  );

  // Machine-data entry — optional numbers read off a cardio machine
  // (distance, calories, power, cadence, HR). Complementary to WHOOP:
  // WHOOP gives readiness and post-session strain; the machine gives
  // the in-session output detail WHOOP cannot see.
  const [machineSource, setMachineSource] = useState<WorkoutSource>(
    editing?.conditioning?.source ?? 'phone_timer',
  );
  const [mDistance, setMDistance] = useState(
    editing?.conditioning?.machine_metrics?.distance_m?.toString() ?? '',
  );
  const [mCalories, setMCalories] = useState(
    editing?.conditioning?.machine_metrics?.calories?.toString() ?? '',
  );
  const [mAvgPower, setMAvgPower] = useState(
    editing?.conditioning?.machine_metrics?.avg_power_w?.toString() ?? '',
  );
  const [mAvgCadence, setMAvgCadence] = useState(
    editing?.conditioning?.machine_metrics?.avg_cadence?.toString() ?? '',
  );
  const [mAvgHr, setMAvgHr] = useState(
    editing?.conditioning?.machine_metrics?.avg_hr_bpm?.toString() ?? '',
  );
  const [mMaxHr, setMMaxHr] = useState(
    editing?.conditioning?.machine_metrics?.max_hr_bpm?.toString() ?? '',
  );
  // Extended machine fields — modality-specific. Added in the HIIT
  // machine-metrics first-slice 02 batch.
  const [mMaxPower, setMMaxPower] = useState(
    editing?.conditioning?.machine_metrics?.max_power_w?.toString() ?? '',
  );
  const [mKilojoules, setMKilojoules] = useState(
    editing?.conditioning?.machine_metrics?.kilojoules?.toString() ?? '',
  );
  const [mAvgPace, setMAvgPace] = useState(
    editing?.conditioning?.machine_metrics?.avg_pace_s?.toString() ?? '',
  );
  const [mAvgSpeed, setMAvgSpeed] = useState(
    editing?.conditioning?.machine_metrics?.avg_speed_kmh?.toString() ?? '',
  );
  const [mMaxSpeed, setMMaxSpeed] = useState(
    editing?.conditioning?.machine_metrics?.max_speed_kmh?.toString() ?? '',
  );
  const [mStrokes, setMStrokes] = useState(
    editing?.conditioning?.machine_metrics?.strokes?.toString() ?? '',
  );

  // Machine-store write + recall — lets the user reuse previous machine
  // metrics across sessions, complementary to Repeat last HIIT.
  const lastMachineMetrics = useMachineStore((s) => s.lastSessionMetrics);
  const lastMachineSource = useMachineStore((s) => s.lastSessionSource);
  const setLastSessionMetrics = useMachineStore((s) => s.setLastSessionMetrics);

  // HIIT saved protocols — named library of recurring interval recipes.
  // Quick-tap recall from a pill strip, auto-saved on every HIIT log
  // that carries a user-provided label.
  const savedHIITProtocols = useHIITProtocolsStore((s) => s.protocols);
  const saveHIITProtocol = useHIITProtocolsStore((s) => s.saveProtocol);
  const saveHIITWorkout = useHIITWorkoutStore((s) => s.saveWorkout);
  const removeHIITProtocol = useHIITProtocolsStore((s) => s.removeProtocol);
  // Local toggle for the expanded "My HIIT library" browser —
  // collapsed by default so the fast pill-strip recall path is
  // the first thing the user sees. Persists nothing; each fresh
  // Train visit starts collapsed.
  const [showHIITLibrary, setShowHIITLibrary] = useState(false);

  const isConditioning = sessionType === 'conditioning';
  const isInterval = isConditioning && ['hiit', 'intervals', 'sprint_intervals', 'circuit'].includes(condSubtype);
  const isWeightTraining = isConditioning && condSubtype === 'weight_training';
  const isRespiratory = isConditioning && ['respiratory_training', 'breathing_warmup', 'recovery_breathing'].includes(condSubtype);
  const [showMore, setShowMore] = useState(false);

  // Segment state — auto-populated for grappling
  const [segments, setSegments] = useState<SessionSegment[]>(editing?.segments ?? []);
  const [expandedSegId, setExpandedSegId] = useState<string | null>(null);

  const addSegment = (type: import('@lauburu/shared').SegmentType) => {
    setSegments((prev) => [
      ...prev,
      { id: `seg-${Date.now()}`, type, duration_min: 15, tags: [] },
    ]);
  };

  const removeSegment = (id: string) => {
    setSegments((prev) => prev.filter((s) => s.id !== id));
    if (expandedSegId === id) setExpandedSegId(null);
  };

  const updateSegment = (id: string, updates: Partial<SessionSegment>) => {
    setSegments((prev) => prev.map((s) => s.id === id ? { ...s, ...updates } : s));
  };

  useEffect(() => {
    if (initialModeAppliedRef.current) return;
    if (!editing && initialMode) {
      initialModeAppliedRef.current = true;
      selectTopMode(initialMode);
    }
  }, [editing, initialMode]);

  // Top mode handlers
  const selectTopMode = (mode: TopMode) => {
    setTopMode(mode);
    if (mode === 'grappling') {
      setSessionType('class');
      // Auto-detect common structure
      if (segments.length === 0 && !editing) {
        setSegments(createDefaultSegments());
      }
    } else if (mode === 'hiit') {
      setSessionType('conditioning');
      setCondSubtype('hiit');
      // Modality stays as user-selected (default assault_bike is fine for cardio HIIT)
    } else if (mode === 'zone2') {
      setSessionType('conditioning');
      setCondSubtype('zone2');
      setDuration(30);
    } else if (mode === 'weights') {
      setSessionType('conditioning');
      setCondSubtype('weight_training');
      setDuration(45);
      // Lifting modality — barbell is the sensible default
      setCondModality('barbell');
    }
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const buildConditioning = (): ConditioningDetail | undefined => {
    if (!isConditioning) return undefined;
    const detail: ConditioningDetail = {
      subtype: condSubtype,
      // Modality is only meaningful for cardio-style work, not lifting
      ...(isWeightTraining ? {} : { modality: condModality }),
    };
    if (isInterval) {
      detail.interval = {
        work_duration_s: parseInt(workDur, 10) || 30,
        rest_duration_s: parseInt(restDur, 10) || 30,
        rounds: parseInt(intervalRounds, 10) || 10,
        ...(intervalLabel.trim() ? { label: intervalLabel.trim() } : {}),
      };
    }
    if (isWeightTraining) {
      detail.weight_training = { focus: liftFocus };
    }
    if (isRespiratory) {
      detail.respiratory = {
        respiratory_type: respType,
        device_used: respDevice !== 'none' ? respDevice : undefined,
        resistance_level: respResistance ? parseInt(respResistance, 10) : undefined,
        breaths: respBreaths ? parseInt(respBreaths, 10) : undefined,
        sets: respSets ? parseInt(respSets, 10) : undefined,
        timing: respTiming,
      };
    }
    // Machine metrics — only attach if the user actually entered something.
    // Every field is optional, and we never synthesise values.
    const parseOptInt = (s: string) => {
      if (!s) return undefined;
      const n = parseInt(s, 10);
      return Number.isFinite(n) ? n : undefined;
    };
    const parseOptFloat = (s: string) => {
      if (!s) return undefined;
      const n = parseFloat(s);
      return Number.isFinite(n) ? n : undefined;
    };
    const metrics: MachineMetrics = {
      distance_m: parseOptInt(mDistance),
      calories: parseOptInt(mCalories),
      kilojoules: parseOptInt(mKilojoules),
      avg_power_w: parseOptInt(mAvgPower),
      max_power_w: parseOptInt(mMaxPower),
      avg_cadence: parseOptInt(mAvgCadence),
      avg_pace_s: parseOptInt(mAvgPace),
      avg_speed_kmh: parseOptFloat(mAvgSpeed),
      max_speed_kmh: parseOptFloat(mMaxSpeed),
      strokes: parseOptInt(mStrokes),
      avg_hr_bpm: parseOptInt(mAvgHr),
      max_hr_bpm: parseOptInt(mMaxHr),
    };
    const hasAnyMetric = Object.values(metrics).some((v) => v != null);
    if (hasAnyMetric) {
      detail.machine_metrics = metrics;
      // If the user entered machine numbers, the source defaults to
      // manual entry unless they explicitly picked something else.
      detail.source =
        machineSource === 'phone_timer' ? 'manual_machine_entry' : machineSource;
    } else {
      detail.source = machineSource;
    }
    return detail;
  };

  // Derive total duration from the most specific source available.
  // - Grappling with segments → sum of segment durations (segments are source of truth)
  // - HIIT with interval config → (work + rest) × rounds, rounded up to minutes
  // - Everything else → the user-entered top-level duration
  const derivedDuration = (() => {
    if (topMode === 'grappling' && segments.length > 0) {
      return segments.reduce((acc, s) => acc + (s.duration_min || 0), 0);
    }
    if (topMode === 'hiit' || (isInterval && !editing)) {
      const w = parseInt(workDur, 10) || 30;
      const r = parseInt(restDur, 10) || 30;
      const n = parseInt(intervalRounds, 10) || 10;
      return Math.max(1, Math.ceil(((w + r) * n) / 60));
    }
    return duration;
  })();

  const handleSubmit = () => {
    Keyboard.dismiss();
    const input = {
      date: editing?.date ?? todayDate(),
      type: sessionType,
      intensity,
      duration_min: derivedDuration,
      rounds: rounds ? parseInt(rounds, 10) : undefined,
      rpe: rpe ? parseInt(rpe, 10) : undefined,
      tags: selectedTags,
      notes,
      conditioning: buildConditioning(),
      segments: segments.length > 0 ? segments : undefined,
      preset_id: undefined,
    };

    if (editing) {
      editSession(editing.id, input);
    } else {
      addSession(input);
    }

    // If this session actually carried machine metrics, cache them on the
    // machine-store so the next session can reuse them via "Repeat last
    // machine metrics". Provenance follows the session's source.
    if (input.conditioning?.machine_metrics) {
      setLastSessionMetrics(
        input.conditioning.machine_metrics,
        input.conditioning.source ?? 'manual_machine_entry',
      );
    }

    // If this is a HIIT session WITH a user-provided protocol label,
    // auto-save (or bump the existing entry) in the HIIT protocols
    // library so the user can recall this recipe with a single tap
    // from the pill strip on their next session. Dedupe by normalized
    // label, MRU ordering, cap at 12 entries — all handled by the
    // store action. Pass the session's machine metrics + duration so
    // the saved protocol carries a "last: 5.2km · 185W · 18min"
    // target-to-beat snapshot.
    //
    // Compute a progression delta BEFORE calling saveHIITProtocol by
    // capturing the existing protocol's `last_metrics` snapshot first
    // (saveHIITProtocol will overwrite it with the current session's
    // numbers). The delta is then passed through onDone so the parent
    // screen's success banner can show "+400m vs last" / "matched last"
    // as immediate progression feedback.
    const iv = input.conditioning?.interval;
    let progressionDelta: string | null = null;
    let newBestLabel: string | null = null;
    if (iv && iv.label && iv.label.trim().length > 0) {
      const normLabel = iv.label.trim().toLowerCase();
      const priorProtocol = savedHIITProtocols.find(
        (p) => p.label.trim().toLowerCase() === normLabel,
      );
      // Snapshot BOTH prior last_metrics and prior best_metrics before
      // saveHIITProtocol runs — it mutates both fields on the matched
      // entry. The delta helper reads last_metrics (vs-last signal);
      // detectNewBest reads best_metrics (PR signal).
      const priorLastMetrics = priorProtocol?.last_metrics;
      const priorBestMetrics = priorProtocol?.best_metrics;

      saveHIITProtocol({
        label: iv.label,
        work_s: iv.work_duration_s,
        rest_s: iv.rest_duration_s,
        rounds: iv.rounds,
        modality: input.conditioning?.modality,
        metrics: input.conditioning?.machine_metrics,
        duration_min: input.duration_min,
      });

      progressionDelta = buildProgressionDelta(
        {
          metrics: input.conditioning?.machine_metrics,
          duration_min: input.duration_min,
        },
        priorLastMetrics,
      );
      newBestLabel = detectNewBest(
        { metrics: input.conditioning?.machine_metrics },
        priorBestMetrics,
      );
    }

    // Build and persist a full HIITWorkoutRecord if this is a HIIT session.
    if (isInterval && iv) {
      const now = new Date().toISOString();
      const workSets = iv.rounds;
      const workDur = iv.work_duration_s;
      const restDur = iv.rest_duration_s;
      const mm = input.conditioning?.machine_metrics;
      const sets: HIITSetMetrics[] = [];
      for (let i = 0; i < workSets; i++) {
        sets.push({
          setIndex: i * 2,
          type: 'work',
          durationSeconds: workDur,
          avgWatts: mm?.avg_power_w ?? null,
          peakWatts: null,
          calories: mm?.calories != null ? Math.round(mm.calories / workSets) : null,
          hrMin: null,
          hrMax: null,
          hrAvg: mm?.avg_hr_bpm ?? null,
          distanceM: mm?.distance_m != null ? Math.round(mm.distance_m / workSets) : null,
          avgCadence: null,
        });
        if (i < workSets - 1) {
          sets.push({
            setIndex: i * 2 + 1,
            type: 'rest',
            durationSeconds: restDur,
            avgWatts: null, peakWatts: null, calories: null,
            hrMin: null, hrMax: null, hrAvg: null,
            distanceM: null, avgCadence: null,
          });
        }
      }
      const totalDur = workSets * workDur + (workSets - 1) * restDur;
      const protocolFormat = `${workDur}:${restDur}`;

      // BLE live-session fallback: if the user had an HR strap or
      // FTMS machine streaming during this session but didn't enter
      // HR/watts manually, ble-connect has been buffering samples
      // into a session ring. Use those to fill avgHr/peakHr/avgWatts
      // so the saved record reflects the live capture. Manual-entry
      // values still win when present.
      let liveAvgHr: number | null = null;
      let livePeakHr: number | null = null;
      let liveAvgPower: number | null = null;
      let livePeakPower: number | null = null;
      let liveAvgCadence: number | null = null;
      let liveDistanceM: number | null = null;
      let liveEnergyKcal: number | null = null;
      let liveEnergyKj: number | null = null;
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const ble = require('../../src/services/ble-connect');
        if (typeof ble?.getSessionStats === 'function') {
          const stats = ble.getSessionStats();
          if (stats && stats.sampleCount > 0) {
            liveAvgHr = stats.avgHrBpm ?? null;
            livePeakHr = stats.peakHrBpm ?? null;
            liveAvgPower = stats.avgPowerW ?? null;
            livePeakPower = stats.peakPowerW ?? null;
            liveAvgCadence = stats.avgCadenceRpm ?? null;
            liveDistanceM = stats.totalDistanceM ?? null;
            liveEnergyKcal = stats.totalEnergyKcal ?? null;
            liveEnergyKj = stats.totalEnergyKj ?? null;
          }
        }
      } catch { /* ble module not linked — safe fallback */ }

      // Track whether each field came from a live BLE strap/machine
      // vs manual entry. Any of HR / watts / cadence / distance /
      // calories being live-sourced flips the record to ble_live.
      const hrFromLive = (mm?.avg_hr_bpm == null) && (liveAvgHr != null);
      const wattsFromLive = (mm?.avg_power_w == null) && (liveAvgPower != null);
      const cadenceFromLive = (mm?.avg_cadence == null) && (liveAvgCadence != null);
      const distanceFromLive = (mm?.distance_m == null) && (liveDistanceM != null && liveDistanceM > 0);
      const caloriesFromLive = (mm?.calories == null) && (liveEnergyKcal != null && liveEnergyKcal > 0);
      const anyLive = hrFromLive || wattsFromLive || cadenceFromLive || distanceFromLive || caloriesFromLive;

      const workout: HIITWorkoutRecord = {
        id: `hiit-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        athleteId: user?.id ?? 'unknown',
        date: now.slice(0, 10),
        createdAt: now,
        templateId: iv.label?.trim() || null,
        protocolFormat: protocolFormat as any,
        machineType: (input.conditioning?.modality as any) ?? 'manual',
        machineProvider: anyLive ? 'ble_live' as any : 'manual',
        sets,
        totalSets: sets.length,
        workSets,
        restSets: sets.filter((s) => s.type === 'rest').length,
        totalDurationSeconds: totalDur,
        totalCalories: mm?.calories ?? liveEnergyKcal,
        totalWorkKj: mm?.kilojoules ?? liveEnergyKj,
        avgWatts: mm?.avg_power_w ?? liveAvgPower,
        peakWatts: livePeakPower,
        avgHr: mm?.avg_hr_bpm ?? liveAvgHr,
        peakHr: livePeakHr,
        source: anyLive ? 'ble_live' as any : 'manual',
        sourceRecordIds: [],
        // Flag the "connected but no samples" case explicitly so Recent
        // Sessions + Coach can see the intent even when live data
        // never arrived (Echo Bike didn't respond to FTMS wake, HR
        // strap dropped before samples, etc.). No fake metrics.
        missingFields: ((): any[] => {
          const out: any[] = [];
          try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const ble = require('../../src/services/ble-connect');
            const bleState = ble?.getBleMachineState?.();
            const machineBound = !!bleState?.machineDevice;
            const hrBound = !!bleState?.hrDevice;
            if ((machineBound || hrBound) && !anyLive) {
              out.push('connected_no_samples');
            }
          } catch { /* ignore */ }
          return out;
        })(),
      };
      // Clear the session ring so the next session doesn't inherit
      // old samples. Defensive: we already just read from it.
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const ble = require('../../src/services/ble-connect');
        if (typeof ble?.clearSession === 'function') ble.clearSession();
      } catch { /* ignore */ }
      const comparison = saveHIITWorkout(workout);
      // Explicit post-save confirmation so the tap result is never
      // silent. Captures the PR / delta info from the comparison
      // return value and the basic session totals so the user sees
      // what was persisted + what happened to Recent Days / Coach.
      try {
        const lines: string[] = [];
        lines.push(`Saved. ${workout.totalSets} set${workout.totalSets === 1 ? '' : 's'} · ${Math.max(1, Math.round((workout.totalDurationSeconds ?? 0) / 60))} min total`);
        // Summarize BLE capture scope so the user knows exactly what
        // was auto-filled vs entered manually.
        if (anyLive) {
          const captured: string[] = [];
          if (hrFromLive) captured.push('HR');
          if (wattsFromLive) captured.push('watts');
          if (cadenceFromLive) captured.push('cadence');
          if (distanceFromLive) captured.push('distance');
          if (caloriesFromLive) captured.push('calories');
          lines.push(`Captured live ${captured.join(' + ')} from BLE`);
        } else {
          // Surface "connected but no samples" explicitly so the user
          // understands why the saved session has no live metrics.
          try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const ble = require('../../src/services/ble-connect');
            const bleState = ble?.getBleMachineState?.();
            if (bleState?.machineDevice && (bleState.status === 'connected' || bleState.status === 'receiving_data')) {
              lines.push(`BLE machine connected but no live samples arrived — saved manual session only.`);
            } else if (bleState?.hrDevice) {
              lines.push(`HR strap bound but no samples arrived — saved manual session only.`);
            }
          } catch { /* ignore */ }
        }
        if (distanceFromLive && liveDistanceM != null) {
          lines.push(`Distance: ${(liveDistanceM / 1000).toFixed(2)} km · from strap/machine`);
        }
        if (cadenceFromLive && liveAvgCadence != null) {
          lines.push(`Avg cadence: ${liveAvgCadence} rpm · from strap/machine`);
        }
        if (workout.totalCalories) lines.push(`Calories: ${Math.round(workout.totalCalories)}`);
        if (workout.avgWatts) lines.push(`Avg watts: ${Math.round(workout.avgWatts)}${workout.peakWatts ? ` · peak ${Math.round(workout.peakWatts)}` : ''}${wattsFromLive ? ' · from strap/machine' : ''}`);
        if (workout.avgHr) lines.push(`Avg HR: ${Math.round(workout.avgHr)}${workout.peakHr ? ` · peak ${Math.round(workout.peakHr)}` : ''}${hrFromLive ? ' · from strap/machine' : ''}`);
        if (comparison) {
          if (typeof comparison.avgWattsDelta === 'number' && Math.abs(comparison.avgWattsDelta) >= 1) {
            lines.push(`vs last: ${comparison.avgWattsDelta > 0 ? '+' : ''}${Math.round(comparison.avgWattsDelta)} avg watts`);
          }
          if (typeof comparison.totalCaloriesDelta === 'number' && Math.abs(comparison.totalCaloriesDelta) >= 5) {
            lines.push(`vs last: ${comparison.totalCaloriesDelta > 0 ? '+' : ''}${Math.round(comparison.totalCaloriesDelta)} cal`);
          }
          if (typeof comparison.avgHrDelta === 'number' && Math.abs(comparison.avgHrDelta) >= 2) {
            lines.push(`vs last: ${comparison.avgHrDelta > 0 ? '+' : ''}${Math.round(comparison.avgHrDelta)} bpm avg HR`);
          }
          const wd = (comparison as any).wattsDropOffPct;
          if (typeof wd === 'number' && wd >= 5) {
            lines.push(`Fatigue: ${Math.round(wd)}% power drop-off across sets`);
          }
          const hd = (comparison as any).hrDriftPct;
          if (typeof hd === 'number' && hd >= 3) {
            lines.push(`HR drift: +${Math.round(hd)}% across sets`);
          }
        } else if (workout.templateId) {
          lines.push('First session on this protocol — baseline recorded.');
        }
        lines.push('');
        lines.push('Now visible in Recent Days + Coach.');
        Alert.alert('HIIT saved', lines.join('\n'));
      } catch { /* silent fallback — save already succeeded */ }
    }

    if (user?.id) syncData(user.id).catch(() => {});
    onDone(progressionDelta, newBestLabel);
  };

  return (
    <View style={styles.formSection}>
      {/* Top-level choice */}
      {!editing && !topMode && (
        <View style={styles.quickGrid}>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('grappling')}>
            <Text style={styles.quickBtnEmoji}>🥋</Text>
            <Text style={styles.quickBtnText}>Grappling</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('hiit')}>
            <Text style={styles.quickBtnEmoji}>⚡</Text>
            <Text style={styles.quickBtnText}>HIIT</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('zone2')}>
            <Text style={styles.quickBtnEmoji}>🫀</Text>
            <Text style={styles.quickBtnText}>Steady State</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('weights')}>
            <Text style={styles.quickBtnEmoji}>🏋️</Text>
            <Text style={styles.quickBtnText}>Weights</Text>
          </Pressable>
        </View>
      )}

      {/* Mode header — tap to change */}
      {topMode && !editing && (
        <Pressable onPress={() => setTopMode(null)}>
          <Text style={styles.modeHeader}>
            {topMode === 'grappling' ? '🥋 Grappling'
              : topMode === 'hiit' ? '⚡ HIIT'
              : topMode === 'weights' ? '🏋️ Weights'
              : '🫀 Steady State'}
            <Text style={styles.modeChange}> (change)</Text>
          </Text>
        </Pressable>
      )}

      {/* Grappling — auto-detected structure, editable */}
      {topMode === 'grappling' && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Session parts</Text>
          <Text style={styles.segmentHint}>
            {segments.length > 0 ? 'Tap to relabel · expand for details' : 'Common structure auto-filled'}
          </Text>

          {/* Editable segment cards */}
          {segments.map((seg, i) => {
            const isExpanded = expandedSegId === seg.id;
            return (
              <View key={seg.id}>
                {/* Compact row — tap type to cycle, tap card to expand */}
                <Pressable
                  style={[styles.segmentRow, isExpanded && styles.segmentRowExpanded]}
                  onPress={() => setExpandedSegId(isExpanded ? null : seg.id)}>
                  <Text style={styles.segmentNum}>{i + 1}</Text>
                  <View style={styles.segmentInfo}>
                    <Text style={styles.segmentType}>{SEGMENT_TYPE_LABELS[seg.type]}</Text>
                    <Text style={styles.segmentMeta}>
                      {seg.duration_min}min
                      {seg.partner_format ? ` · ${PARTNER_FORMAT_LABELS[seg.partner_format]}` : ''}
                      {seg.rounds ? ` · ${seg.rounds}rds` : ''}
                    </Text>
                    {seg.map_ref?.position_key && (
                      <Text style={styles.segmentMapRef}>
                        ↳ {seg.map_ref.position_key}
                      </Text>
                    )}
                  </View>
                  <Text style={styles.segmentChevron}>{isExpanded ? '▾' : '▸'}</Text>
                  <Pressable onPress={() => removeSegment(seg.id)} hitSlop={8}>
                    <Text style={styles.segmentRemove}>✕</Text>
                  </Pressable>
                </Pressable>

                {/* Expanded detail — progressive disclosure */}
                {isExpanded && (
                  <View style={styles.segmentDetail}>
                    {/* Quick relabel */}
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      <View style={styles.pillRow}>
                        {(['technique', 'drilling', 'positional', 'wrestling', 'takedowns',
                          'live_rounds', 'open_mat', 'comp_prep', 'conditioning_finisher', 'other'] as import('@lauburu/shared').SegmentType[]).map((st) => (
                          <Pressable
                            key={st}
                            style={[styles.pillSmall, seg.type === st && styles.pillActive]}
                            onPress={() => updateSegment(seg.id, { type: st })}>
                            <Text style={[styles.pillSmallText, seg.type === st && styles.pillTextActive]}>
                              {SEGMENT_TYPE_LABELS[st]}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                    </ScrollView>

                    {/* Duration — typed */}
                    <View style={styles.rowInputs}>
                      <View style={styles.halfInput}>
                        <Text style={styles.sectionLabel}>Duration (min)</Text>
                        <TextInput
                          style={styles.input}
                          value={String(seg.duration_min)}
                          onChangeText={(t) => updateSegment(seg.id, { duration_min: parseInt(t, 10) || 0 })}
                          keyboardType="number-pad"
                          placeholder="15"
                          placeholderTextColor="#666"
                        />
                      </View>
                    </View>

                    {/* Partner format */}
                    <View>
                      <Text style={styles.sectionLabel}>Format</Text>
                      <View style={styles.pillRow}>
                        {(['group_training', 'one_partner', 'rotating_partners', 'solo'] as PartnerFormat[]).map((pf) => (
                          <Pressable key={pf}
                            style={[styles.pillSmall, seg.partner_format === pf && styles.pillActive]}
                            onPress={() => updateSegment(seg.id, { partner_format: seg.partner_format === pf ? undefined : pf })}>
                            <Text style={[styles.pillSmallText, seg.partner_format === pf && styles.pillTextActive]}>
                              {PARTNER_FORMAT_LABELS[pf]}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                    </View>

                    {/* Rounds + round length — only meaningful for live-type segments */}
                    {(['live_rounds', 'comp_prep', 'wrestling', 'positional'] as SegmentType[]).includes(seg.type) && (
                      <View style={styles.rowInputs}>
                        <View style={styles.halfInput}>
                          <Text style={styles.sectionLabel}>Rounds</Text>
                          <TextInput
                            style={styles.input}
                            value={seg.rounds ? String(seg.rounds) : ''}
                            onChangeText={(t) => updateSegment(seg.id, { rounds: t ? parseInt(t, 10) || undefined : undefined })}
                            keyboardType="number-pad"
                            placeholder="—"
                            placeholderTextColor="#666"
                          />
                        </View>
                        <View style={styles.halfInput}>
                          <Text style={styles.sectionLabel}>Round length (min)</Text>
                          <TextInput
                            style={styles.input}
                            value={seg.round_length_min ? String(seg.round_length_min) : ''}
                            onChangeText={(t) => updateSegment(seg.id, { round_length_min: t ? parseInt(t, 10) || undefined : undefined })}
                            keyboardType="number-pad"
                            placeholder="—"
                            placeholderTextColor="#666"
                          />
                        </View>
                      </View>
                    )}

                    {/* Reference position link — optional, links the segment
                        to a canonical Grappling Map position via
                        SessionSegment.map_ref.position_key. Collapsed until
                        tapped so the normal logging flow stays clean. */}
                    <ReferencePositionPicker
                      value={seg.map_ref?.position_key}
                      onChange={(name) =>
                        updateSegment(seg.id, {
                          map_ref: name
                            ? { ...(seg.map_ref ?? {}), position_key: name }
                            : undefined,
                        })
                      }
                    />

                    {/* Topic worked — free text; stays for non-canonical notes */}
                    <TextInput
                      style={styles.input}
                      placeholder="Free notes (topic, context, partner, etc.)"
                      placeholderTextColor="#555"
                      value={seg.topic_worked ?? ''}
                      onChangeText={(t) => updateSegment(seg.id, { topic_worked: t || undefined })}
                    />
                  </View>
                )}
              </View>
            );
          })}

          {/* Add segment — compact */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.pillRow}>
              {(['technique', 'drilling', 'positional', 'wrestling', 'takedowns',
                'live_rounds', 'conditioning_finisher'] as import('@lauburu/shared').SegmentType[]).map((st) => (
                <Pressable key={st} style={styles.pillSmall} onPress={() => addSegment(st)}>
                  <Text style={styles.pillSmallText}>+ {SEGMENT_TYPE_LABELS[st]}</Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        </View>
      )}

      {/* HIIT — direct work/rest/rounds entry, recovery-aware suggestion,
          and a quick Repeat-last-HIIT action that reuses the exact
          protocol (and label) of the most recent logged HIIT session. */}
      {topMode === 'hiit' && (
        <View style={styles.section}>
          <Pressable
            style={styles.aiSuggestionBubble}
            onPress={() => {
              setWorkDur(String(hiitSuggestion.work_s));
              setRestDur(String(hiitSuggestion.rest_s));
              setIntervalRounds(String(hiitSuggestion.rounds));
            }}>
            <Text style={styles.aiSuggestionText}>
              Suggested: {hiitSuggestion.label} — {hiitSuggestion.reason}
            </Text>
          </Pressable>

          {lastHIITSession?.conditioning?.interval && (
            <Pressable
              style={styles.repeatBtn}
              onPress={() => {
                const iv = lastHIITSession.conditioning!.interval!;
                setWorkDur(String(iv.work_duration_s));
                setRestDur(String(iv.rest_duration_s));
                setIntervalRounds(String(iv.rounds));
                setIntervalLabel(iv.label ?? '');
                if (lastHIITSession.conditioning!.modality) {
                  setCondModality(lastHIITSession.conditioning!.modality);
                }
              }}>
              <Text style={styles.repeatBtnText}>
                ↺ Repeat last HIIT ·{' '}
                {lastHIITSession.conditioning.interval.label ??
                  `${lastHIITSession.conditioning.interval.work_duration_s}/${lastHIITSession.conditioning.interval.rest_duration_s} × ${lastHIITSession.conditioning.interval.rounds}`}
              </Text>
            </Pressable>
          )}

          {/* Saved protocols — named library recalled with one tap.
              Rendered only when the store has entries. Tap a pill to
              fill in work/rest/rounds/label/modality; long-press to
              remove the protocol from the library. Auto-saved on
              session log when the current protocol has a label. */}
          {savedHIITProtocols.length > 0 && (() => {
            // Compute "now" once outside the map so every pill's
            // recency check uses the same reference. Cheap — Date.now
            // is a single syscall and the pill list is tiny (max 12).
            const nowMs = Date.now();
            // Shared recall handler used by both pill tap and library
            // row tap so the two surfaces never drift.
            const recallProtocol = (p: SavedHIITProtocol) => {
              setWorkDur(String(p.work_s));
              setRestDur(String(p.rest_s));
              setIntervalRounds(String(p.rounds));
              setIntervalLabel(p.label);
              if (p.modality) setCondModality(p.modality);
            };
            return (
              <View style={styles.savedProtocolsBlock}>
                <View style={styles.savedProtocolsHeaderRow}>
                  <Text style={styles.savedProtocolsLabel}>Saved protocols</Text>
                  <Pressable
                    onPress={() => setShowHIITLibrary((v) => !v)}
                    style={styles.libraryToggleBtn}>
                    <Text style={styles.libraryToggleBtnText}>
                      {showHIITLibrary ? 'Hide library ▴' : 'Browse library ▾'}
                    </Text>
                  </Pressable>
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View style={styles.pillRow}>
                    {savedHIITProtocols.map((p) => {
                      const lastMetricsLine = formatSavedProtocolLastMetrics(
                        p.last_metrics,
                      );
                      const recentPR = hasRecentPR(p.best_metrics, nowMs);
                      return (
                        <Pressable
                          key={p.id}
                          style={[
                            styles.savedProtocolPill,
                            recentPR && styles.savedProtocolPillPR,
                          ]}
                          onPress={() => recallProtocol(p)}
                          onLongPress={() => removeHIITProtocol(p.id)}
                          delayLongPress={500}>
                          <View style={styles.savedProtocolPillNameRow}>
                            <Text
                              style={styles.savedProtocolPillName}
                              numberOfLines={1}>
                              {p.label}
                            </Text>
                            {recentPR && (
                              <Text style={styles.savedProtocolPillBadge}>
                                🏆
                              </Text>
                            )}
                          </View>
                          <Text style={styles.savedProtocolPillDetail}>
                            {p.work_s}/{p.rest_s} × {p.rounds}
                          </Text>
                          {lastMetricsLine.length > 0 && (
                            <Text style={styles.savedProtocolPillTarget}>
                              {lastMetricsLine}
                            </Text>
                          )}
                        </Pressable>
                      );
                    })}
                  </View>
                </ScrollView>
                <Text style={styles.savedProtocolsHint}>
                  Long-press a protocol to remove it.
                </Text>

                {/* My HIIT library — full-width expanded view.
                    Toggled via Browse library, collapsed by default
                    so the pill strip stays the primary fast-path.
                    Each row shows the label + PR badge, schedule,
                    modality, last-session and best-ever metric
                    lines side-by-side with captured-at relative
                    dates, a Recall button, and a Remove button. */}
                {showHIITLibrary && (
                  <View style={styles.libraryList}>
                    {savedHIITProtocols.map((p) => {
                      const recentPR = hasRecentPR(p.best_metrics, nowMs);
                      const fadeCountdown = getPRFadeCountdown(
                        p.best_metrics,
                        nowMs,
                      );
                      const lastLine = formatLibraryMetricsLine(p.last_metrics);
                      const bestLine = formatLibraryMetricsLine(p.best_metrics);
                      const lastAge =
                        p.last_metrics?.captured_at
                          ? formatCapturedAtRelative(
                              p.last_metrics.captured_at,
                              nowMs,
                            )
                          : '';
                      const bestAge =
                        p.best_metrics?.captured_at
                          ? formatCapturedAtRelative(
                              p.best_metrics.captured_at,
                              nowMs,
                            )
                          : '';
                      return (
                        <View
                          key={p.id}
                          style={[
                            styles.libraryRow,
                            recentPR && styles.libraryRowPR,
                          ]}>
                          <View style={styles.libraryRowHeader}>
                            <Text
                              style={styles.libraryRowLabel}
                              numberOfLines={1}>
                              {p.label}
                            </Text>
                            {recentPR && (
                              <Text style={styles.libraryRowBadge}>🏆</Text>
                            )}
                          </View>
                          <Text style={styles.libraryRowSchedule}>
                            {p.work_s}s / {p.rest_s}s × {p.rounds}
                            {p.modality ? ` · ${MODALITY_LABELS[p.modality]}` : ''}
                            {p.use_count > 0 ? ` · ${p.use_count}× logged` : ''}
                          </Text>

                          {/* Last session — always rendered when any
                              snapshot exists, falls back to a muted
                              "no data yet" line otherwise. */}
                          <View style={styles.libraryRowMetricBlock}>
                            <Text style={styles.libraryRowMetricLabel}>
                              LAST{lastAge ? ` · ${lastAge}` : ''}
                            </Text>
                            {lastLine.length > 0 ? (
                              <Text style={styles.libraryRowMetricValue}>
                                {lastLine}
                              </Text>
                            ) : (
                              <Text style={styles.libraryRowMetricMuted}>
                                no machine data yet
                              </Text>
                            )}
                          </View>

                          {/* Best ever — only shown when best_metrics
                              is populated. No fake placeholder when
                              absent — honest about missing data. */}
                          {p.best_metrics && bestLine.length > 0 && (
                            <View style={styles.libraryRowMetricBlock}>
                              <Text style={styles.libraryRowMetricLabel}>
                                BEST EVER{bestAge ? ` · ${bestAge}` : ''}
                              </Text>
                              <Text style={styles.libraryRowMetricValuePR}>
                                {bestLine}
                              </Text>
                              {/* PR fade countdown — behavioral nudge
                                  surfaced only in the last 3 days of
                                  the 14-day recency window. Renders
                                  amber italic to signal time pressure
                                  without screaming at the user. */}
                              {fadeCountdown && (
                                <Text style={styles.libraryRowFadeCountdown}>
                                  ⏳ {fadeCountdown} — defend or beat it
                                </Text>
                              )}
                            </View>
                          )}

                          {/* Actions — Recall + Remove */}
                          <View style={styles.libraryRowActions}>
                            <Pressable
                              style={styles.libraryRowRecallBtn}
                              onPress={() => recallProtocol(p)}>
                              <Text style={styles.libraryRowRecallBtnText}>
                                ↺ Recall
                              </Text>
                            </Pressable>
                            <Pressable
                              style={styles.libraryRowRemoveBtn}
                              onPress={() => removeHIITProtocol(p.id)}>
                              <Text style={styles.libraryRowRemoveBtnText}>
                                Remove
                              </Text>
                            </Pressable>
                          </View>
                        </View>
                      );
                    })}
                  </View>
                )}
              </View>
            );
          })()}

          <TextInput
            style={styles.input}
            placeholder="Protocol label (optional) — Tabata, Bike HIIT, etc."
            placeholderTextColor="#555"
            value={intervalLabel}
            onChangeText={setIntervalLabel}
          />
        </View>
      )}

      {/* Steady State */}
      {topMode === 'zone2' && (
        <SelectorRow
          label="Type"
          options={['zone2', 'tempo', 'recovery_cardio'] as ConditioningSubtype[]}
          labels={{ zone2: 'Zone 2', tempo: 'Tempo', recovery_cardio: 'Recovery Session' } as any}
          value={condSubtype}
          onChange={setCondSubtype as any}
          suggestion={'zone2' as any}
          suggestionLabel="Zone 2 builds aerobic base"
        />
      )}

      {/* Weights — focus + custom duration */}
      {topMode === 'weights' && (
        <>
          <SelectorRow
            label="Focus"
            options={['strength', 'functional_muscle', 'rehab'] as LiftingFocus[]}
            labels={LIFTING_FOCUS_LABELS as any}
            value={liftFocus}
            onChange={setLiftFocus as any}
            suggestion={'strength' as any}
            suggestionLabel="Strength matches your training goal"
          />
          <View style={styles.selectorRow}>
            <View style={styles.selectorHeader}>
              <Text style={styles.selectorLabel}>Duration</Text>
              <TextInput
                style={[styles.input, { width: 80, marginLeft: 8 }]}
                value={String(duration)}
                onChangeText={(t) => setDuration(parseInt(t, 10) || 0)}
                keyboardType="number-pad"
                placeholder="45"
                placeholderTextColor="#666"
              />
              <Text style={styles.selectorLabel}> min</Text>
            </View>
          </View>
        </>
      )}

      {/* AI suggestion — shown after mode selection */}
      {topMode && !editing && (
        <View style={styles.suggestionCard}>
          <Text style={styles.suggestionLabel}>AI coach suggestion</Text>
          <Text style={styles.suggestionText}>
            {topMode === 'hiit' ? `${ATHLETE_CAPABILITY_COPY.seedSuggestionLabel} 30/30 intervals are a reasonable match today.`
              : topMode === 'zone2' ? `${ATHLETE_CAPABILITY_COPY.seedSuggestionLabel} Zone 2 for 30min as a lower-risk aerobic option.`
              : topMode === 'weights' ? `${ATHLETE_CAPABILITY_COPY.seedSuggestionLabel} moderate lifting today instead of a hard session.`
              : 'Your usual structure looks good for today.'}
          </Text>
          <Text style={styles.suggestionNote}>Edit the plan to match what you actually did.</Text>
        </View>
      )}

      {/* Full type selector for editing */}
      {editing && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Type</Text>
          <View style={styles.pillRow}>
            {SESSION_TYPES.map((t) => (
              <Pressable
                key={t}
                style={[styles.pill, sessionType === t && styles.pillActive]}
                onPress={() => setSessionType(t)}>
                <Text style={[styles.pillText, sessionType === t && styles.pillTextActive]}>
                  {SESSION_TYPE_LABELS[t]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* Conditioning subtype — only for editing or when not using top-mode flow */}
      {isConditioning && editing && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Cardio</Text>
          <View style={styles.pillRow}>
            {(['hiit', 'intervals', 'sprint_intervals', 'steady_state', 'zone2', 'tempo', 'circuit', 'recovery_cardio'] as ConditioningSubtype[]).map((st) => (
              <Pressable
                key={st}
                style={[styles.pill, condSubtype === st && styles.pillActive]}
                onPress={() => setCondSubtype(st)}>
                <Text style={[styles.pillText, condSubtype === st && styles.pillTextActive]}>
                  {CONDITIONING_SUBTYPE_LABELS[st]}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={[styles.sectionLabel, { marginTop: 8 }]}>Strength / Recovery</Text>
          <View style={styles.pillRow}>
            {(['weight_training', 'mobility', 'respiratory_training', 'other'] as ConditioningSubtype[]).map((st) => (
              <Pressable
                key={st}
                style={[styles.pill, condSubtype === st && styles.pillActive]}
                onPress={() => setCondSubtype(st)}>
                <Text style={[styles.pillText, condSubtype === st && styles.pillTextActive]}>
                  {CONDITIONING_SUBTYPE_LABELS[st]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* === Everything below only shows after a top-level choice === */}

      {/* Modality — selector row */}
      {topMode && isConditioning && !isWeightTraining && !isRespiratory && (
        <SelectorRow
          label="Modality"
          options={['assault_bike', 'rower', 'skierg', 'running', 'bike', 'bodyweight', 'kettlebell', 'other'] as Modality[]}
          labels={MODALITY_LABELS as any}
          value={condModality}
          onChange={setCondModality as any}
          suggestion={'assault_bike' as any}
          suggestionLabel="Assault Bike for your session type"
        />
      )}

      {/* Interval detail — always editable */}
      {isInterval && (
        <View style={styles.rowInputs}>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Work (s)</Text>
            <TextInput
              style={styles.input}
              value={workDur}
              onChangeText={setWorkDur}
              keyboardType="number-pad"
              placeholder="30"
              placeholderTextColor="#666"
            />
          </View>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Rest (s)</Text>
            <TextInput
              style={styles.input}
              value={restDur}
              onChangeText={setRestDur}
              keyboardType="number-pad"
              placeholder="30"
              placeholderTextColor="#666"
            />
          </View>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Rounds</Text>
            <TextInput
              style={styles.input}
              value={intervalRounds}
              onChangeText={setIntervalRounds}
              keyboardType="number-pad"
              placeholder="10"
              placeholderTextColor="#666"
            />
          </View>
        </View>
      )}

      {/* Weight training focus */}
      {isWeightTraining && editing && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Focus</Text>
          <View style={styles.pillRow}>
            {(['strength', 'functional_muscle', 'rehab'] as LiftingFocus[]).map((f) => (
              <Pressable
                key={f}
                style={[styles.pill, liftFocus === f && styles.pillActive]}
                onPress={() => setLiftFocus(f)}>
                <Text style={[styles.pillText, liftFocus === f && styles.pillTextActive]}>
                  {LIFTING_FOCUS_LABELS[f]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* Respiratory detail */}
      {isRespiratory && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Device</Text>
          <View style={styles.pillRow}>
            {(['none', 'airofit', 'wello2', 'other'] as import('@lauburu/shared').RespiratoryDevice[]).map((d) => (
              <Pressable
                key={d}
                style={[styles.pill, respDevice === d && styles.pillActive]}
                onPress={() => setRespDevice(d)}>
                <Text style={[styles.pillText, respDevice === d && styles.pillTextActive]}>
                  {RESPIRATORY_DEVICE_LABELS[d]}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.sectionLabel}>Breathing Type</Text>
          <View style={styles.pillRow}>
            {(['inspiratory', 'expiratory', 'mixed'] as const).map((t) => (
              <Pressable
                key={t}
                style={[styles.pill, respType === t && styles.pillActive]}
                onPress={() => setRespType(t)}>
                <Text style={[styles.pillText, respType === t && styles.pillTextActive]}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.sectionLabel}>Timing</Text>
          <View style={styles.pillRow}>
            {(['pre_training', 'post_training', 'standalone'] as const).map((t) => (
              <Pressable
                key={t}
                style={[styles.pill, respTiming === t && styles.pillActive]}
                onPress={() => setRespTiming(t)}>
                <Text style={[styles.pillText, respTiming === t && styles.pillTextActive]}>
                  {t === 'pre_training' ? 'Pre-training' : t === 'post_training' ? 'Post-training' : 'Standalone'}
                </Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.rowInputs}>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Breaths</Text>
              <TextInput style={styles.input} value={respBreaths} onChangeText={setRespBreaths} keyboardType="number-pad" placeholder="30" placeholderTextColor="#666" />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Sets</Text>
              <TextInput style={styles.input} value={respSets} onChangeText={setRespSets} keyboardType="number-pad" placeholder="3" placeholderTextColor="#666" />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Resistance</Text>
              <TextInput style={styles.input} value={respResistance} onChangeText={setRespResistance} keyboardType="number-pad" placeholder="—" placeholderTextColor="#666" />
            </View>
          </View>
        </View>
      )}

      {/* Machine data (optional) — WHOOP does not expose machine-level
          output, so this is where the user captures distance, calories,
          power, cadence, HR etc. Only shown for cardio modes that could
          plausibly expose machine metrics. Lifting + respiratory + rest
          modes hide this section entirely. */}
      {topMode && isConditioning && !isWeightTraining && !isRespiratory &&
        modalitySupportsMachineData(condModality) && (
        <View style={styles.section}>
          <View style={styles.machineHeaderRow}>
            <Text style={styles.sectionLabel}>Machine data (optional)</Text>
            <Text style={styles.machineSourceHint}>
              {(() => {
                if (machineSource === 'manual_machine_entry') return 'Manual';
                if (machineSource === 'machine_connected') {
                  try {
                    // eslint-disable-next-line @typescript-eslint/no-require-imports
                    const ble = require('../../src/services/ble-connect');
                    const state = ble?.getBleMachineState?.();
                    if (state?.status === 'receiving_data') return 'Live · streaming';
                    if (state?.machineDevice || state?.hrDevice) return 'Live · waiting';
                  } catch { /* ignore */ }
                  return 'Live · no device';
                }
                return 'Phone timer';
              })()}
            </Text>
          </View>

          {/* Source row — phone timer / manual / live BLE. Live BLE
              is available now (Build 11+); auto-fill happens at save
              time via the ble-connect session ring. When no machine
              is bound we still let the user pre-select Live BLE so
              the chosen source matches the intent; the helper text
              below points them at Machine capture to pair. */}
          <View style={styles.pillRow}>
            {(['phone_timer', 'manual_machine_entry', 'machine_connected'] as WorkoutSource[]).map(
              (src) => {
                const isActive = machineSource === src;
                return (
                  <Pressable
                    key={src}
                    style={[styles.pillSmall, isActive && styles.pillActive]}
                    onPress={() => setMachineSource(src)}>
                    <Text style={[styles.pillSmallText, isActive && styles.pillTextActive]}>
                      {src === 'phone_timer'
                        ? 'Phone timer'
                        : src === 'manual_machine_entry'
                          ? 'Manual'
                          : 'Live BLE'}
                    </Text>
                  </Pressable>
                );
              },
            )}
          </View>
          {machineSource === 'machine_connected' && (() => {
            // Compact live-capture status so the user knows whether
            // the BLE ring is actively capturing. Reads from the
            // ble-connect module directly — no state subscription
            // needed for this static render; the chip re-renders on
            // re-entry of the Train tab.
            let liveLine = 'Connect a machine in Machine capture above to capture live metrics.';
            try {
              // eslint-disable-next-line @typescript-eslint/no-require-imports
              const ble = require('../../src/services/ble-connect');
              const state = ble?.getBleMachineState?.();
              // Gate the "will auto-fill" promise behind actual sample
              // arrival. Previously the line claimed auto-fill as soon
              // as the bike was paired — but if FTMS notifications
              // never arrived (Echo / Assault quirk, missing wake),
              // Save landed with zero metrics and the copy felt like
              // a lie. Read the live session stats to decide copy.
              let sampleCount = 0;
              try {
                const stats = ble?.getSessionStats?.();
                if (stats && typeof stats.sampleCount === 'number') sampleCount = stats.sampleCount;
              } catch { /* ignore */ }
              if (state?.machineDevice) {
                liveLine = sampleCount > 0
                  ? `Capturing live from ${state.machineDevice.name} (${sampleCount} samples). Save will attach HR / watts / cadence.`
                  : `Connected to ${state.machineDevice.name}. Start pedaling — metrics attach once samples arrive. You can still save the manual session.`;
              } else if (state?.hrDevice) {
                liveLine = sampleCount > 0
                  ? `HR strap streaming (${state.hrDevice.name}). Save will attach HR. Connect a machine for watts + cadence.`
                  : `HR strap bound (${state.hrDevice.name}). No samples yet — start the session. Connect a machine for watts + cadence.`;
              }
            } catch { /* ignore */ }
            return (
              <Text style={[styles.machineSourceHint, { marginTop: 4 }]}>{liveLine}</Text>
            );
          })()}

          {/* Manual-entry fields — collapsible area, modality-aware.
              Each modality shows only the fields the machine would plausibly
              expose, so a rower gets pace + strokes and a bike gets
              power + cadence without either looking at irrelevant rows. */}
          {machineSource === 'manual_machine_entry' && (
            <>
              {/* Repeat-last-machine — only when the machine-store has a
                  previous cached metrics record. Analogous to Repeat last HIIT. */}
              {lastMachineMetrics && (
                <Pressable
                  style={styles.repeatBtn}
                  onPress={() => {
                    const m = lastMachineMetrics;
                    if (m.distance_m != null) setMDistance(String(m.distance_m));
                    if (m.calories != null) setMCalories(String(m.calories));
                    if (m.kilojoules != null) setMKilojoules(String(m.kilojoules));
                    if (m.avg_power_w != null) setMAvgPower(String(m.avg_power_w));
                    if (m.max_power_w != null) setMMaxPower(String(m.max_power_w));
                    if (m.avg_cadence != null) setMAvgCadence(String(m.avg_cadence));
                    if (m.avg_pace_s != null) setMAvgPace(String(m.avg_pace_s));
                    if (m.avg_speed_kmh != null) setMAvgSpeed(String(m.avg_speed_kmh));
                    if (m.max_speed_kmh != null) setMMaxSpeed(String(m.max_speed_kmh));
                    if (m.strokes != null) setMStrokes(String(m.strokes));
                    if (m.avg_hr_bpm != null) setMAvgHr(String(m.avg_hr_bpm));
                    if (m.max_hr_bpm != null) setMMaxHr(String(m.max_hr_bpm));
                  }}>
                  <Text style={styles.repeatBtnText}>
                    ↺ Repeat last machine metrics
                    {lastMachineSource ? ` · ${lastMachineSource === 'machine_connected' ? 'live' : 'manual'}` : ''}
                  </Text>
                </Pressable>
              )}

              {/* Always-relevant fields — distance / calories. Shown for
                  every cardio modality. */}
              <View style={styles.rowInputs}>
                <View style={styles.halfInput}>
                  <Text style={styles.sectionLabel}>Distance (m)</Text>
                  <TextInput
                    style={styles.input}
                    value={mDistance}
                    onChangeText={setMDistance}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#666"
                  />
                </View>
                <View style={styles.halfInput}>
                  <Text style={styles.sectionLabel}>Calories</Text>
                  <TextInput
                    style={styles.input}
                    value={mCalories}
                    onChangeText={setMCalories}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#666"
                  />
                </View>
              </View>

              {/* Bike / Assault bike → power + cadence pair */}
              {(condModality === 'assault_bike' || condModality === 'bike') && (
                <>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Avg power (W)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgPower}
                        onChangeText={setMAvgPower}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Max power (W)</Text>
                      <TextInput
                        style={styles.input}
                        value={mMaxPower}
                        onChangeText={setMMaxPower}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                  </View>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Avg cadence (rpm)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgCadence}
                        onChangeText={setMAvgCadence}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput} />
                  </View>
                </>
              )}

              {/* Rower → pace + strokes + kilojoules */}
              {condModality === 'rower' && (
                <>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Avg pace (s/500m)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgPace}
                        onChangeText={setMAvgPace}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Strokes</Text>
                      <TextInput
                        style={styles.input}
                        value={mStrokes}
                        onChangeText={setMStrokes}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                  </View>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Avg stroke rate (spm)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgCadence}
                        onChangeText={setMAvgCadence}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>kJ</Text>
                      <TextInput
                        style={styles.input}
                        value={mKilojoules}
                        onChangeText={setMKilojoules}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                  </View>
                </>
              )}

              {/* SkiErg → pace + kilojoules */}
              {condModality === 'skierg' && (
                <View style={styles.rowInputs}>
                  <View style={styles.halfInput}>
                    <Text style={styles.sectionLabel}>Avg pace (s/500m)</Text>
                    <TextInput
                      style={styles.input}
                      value={mAvgPace}
                      onChangeText={setMAvgPace}
                      keyboardType="number-pad"
                      placeholder="—"
                      placeholderTextColor="#666"
                    />
                  </View>
                  <View style={styles.halfInput}>
                    <Text style={styles.sectionLabel}>kJ</Text>
                    <TextInput
                      style={styles.input}
                      value={mKilojoules}
                      onChangeText={setMKilojoules}
                      keyboardType="number-pad"
                      placeholder="—"
                      placeholderTextColor="#666"
                    />
                  </View>
                </View>
              )}

              {/* Treadmill / running → speed + cadence */}
              {condModality === 'running' && (
                <>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Avg speed (km/h)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgSpeed}
                        onChangeText={setMAvgSpeed}
                        keyboardType="numbers-and-punctuation"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Max speed (km/h)</Text>
                      <TextInput
                        style={styles.input}
                        value={mMaxSpeed}
                        onChangeText={setMMaxSpeed}
                        keyboardType="numbers-and-punctuation"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                  </View>
                  <View style={styles.rowInputs}>
                    <View style={styles.halfInput}>
                      <Text style={styles.sectionLabel}>Cadence (spm)</Text>
                      <TextInput
                        style={styles.input}
                        value={mAvgCadence}
                        onChangeText={setMAvgCadence}
                        keyboardType="number-pad"
                        placeholder="—"
                        placeholderTextColor="#666"
                      />
                    </View>
                    <View style={styles.halfInput} />
                  </View>
                </>
              )}

              {/* HR pair — always shown last, plausible on any cardio modality
                  whether read off the machine or a paired chest strap. */}
              <View style={styles.rowInputs}>
                <View style={styles.halfInput}>
                  <Text style={styles.sectionLabel}>Avg HR (bpm)</Text>
                  <TextInput
                    style={styles.input}
                    value={mAvgHr}
                    onChangeText={setMAvgHr}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#666"
                  />
                </View>
                <View style={styles.halfInput}>
                  <Text style={styles.sectionLabel}>Max HR (bpm)</Text>
                  <TextInput
                    style={styles.input}
                    value={mMaxHr}
                    onChangeText={setMMaxHr}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#666"
                  />
                </View>
              </View>

              <Text style={styles.machineComplementHint}>
                Machine metrics give the in-session output that complements your readiness — Apple Health and recent training context only see big-picture signals.
              </Text>
            </>
          )}
        </View>
      )}

      {/* Intensity — only after selection. AI suggestion is reactive. */}
      {(topMode || editing) && (
        <SelectorRow
          label="Intensity"
          options={INTENSITIES}
          labels={INTENSITY_LABELS as Record<string, string>}
          value={intensity}
          onChange={setIntensity as any}
          suggestion={aiIntensity.intensity}
          suggestionLabel={`${INTENSITY_LABELS[aiIntensity.intensity]} — ${aiIntensity.reason}`}
        />
      )}

      {/* Duration — typed input for Zone 2 only. Grappling derives from segments;
          HIIT derives from work/rest/rounds; Weights has its own input. */}
      {(topMode || editing) && topMode !== 'weights' && topMode !== 'hiit' && topMode !== 'grappling' && (
      <View style={styles.selectorRow}>
        <View style={styles.selectorHeader}>
          <Text style={styles.selectorLabel}>Duration</Text>
          <View style={styles.selectorValueRow}>
            <TextInput
              style={[styles.input, { width: 70, textAlign: 'center', paddingVertical: 6 }]}
              value={String(duration)}
              onChangeText={(t) => setDuration(parseInt(t, 10) || 0)}
              keyboardType="number-pad"
              placeholder="30"
              placeholderTextColor="#666"
            />
            <Text style={styles.selectorLabel}> min</Text>
          </View>
        </View>
        {topMode === 'zone2' && (
          <View style={styles.aiSuggestionBubble}>
            <Text style={styles.aiSuggestionText}>
              AI coach suggestion: 30min for aerobic base building
            </Text>
          </View>
        )}
      </View>
      )}

      {/* Derived total readout — Grappling (from segments) and HIIT (from work/rest/rounds) */}
      {topMode && (topMode === 'grappling' || topMode === 'hiit') && (
        <View style={styles.derivedTotalRow}>
          <Text style={styles.derivedTotalLabel}>
            {topMode === 'grappling' ? 'Total from segments' : 'Total from intervals'}
          </Text>
          <Text style={styles.derivedTotalValue}>{derivedDuration} min</Text>
        </View>
      )}

      {/* More options — only after selection */}
      {(topMode || editing) && <Pressable onPress={() => setShowMore(!showMore)}>
        <Text style={styles.moreToggle}>
          {showMore ? '▾ Less options' : '▸ More options (tags, RPE, notes)'}
        </Text>
      </Pressable>}

      {(topMode || editing) && showMore && (
        <>
          {/* Tags */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>Tags</Text>
            <View style={styles.pillRow}>
              {TAG_OPTIONS.map((tag) => (
                <Pressable
                  key={tag}
                  style={[styles.pill, selectedTags.includes(tag) && styles.pillActive]}
                  onPress={() => toggleTag(tag)}>
                  <Text style={[styles.pillText, selectedTags.includes(tag) && styles.pillTextActive]}>
                    {tag}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          {/* Rounds + RPE */}
          <View style={styles.rowInputs}>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Rounds</Text>
              <TextInput
                style={styles.input}
                placeholder="—"
                placeholderTextColor="#666"
                value={rounds}
                onChangeText={setRounds}
                keyboardType="number-pad"
              />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>RPE (1-10)</Text>
              <TextInput
                style={styles.input}
                placeholder="—"
                placeholderTextColor="#666"
                value={rpe}
                onChangeText={setRpe}
                keyboardType="number-pad"
              />
            </View>
          </View>

          {/* Notes */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>Notes</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Techniques worked, how it felt..."
              placeholderTextColor="#666"
              value={notes}
              onChangeText={setNotes}
              multiline
              textAlignVertical="top"
            />
          </View>
        </>
      )}

      {/* Submit + Start Timer — only after selection */}
      {(topMode || editing) && <View style={styles.submitRow}>
        <Pressable style={[styles.submitButton, { flex: 1 }]} onPress={handleSubmit}>
          <Text style={styles.submitText}>
            {editing ? 'Save Changes' : 'Log Session'}
          </Text>
        </Pressable>

        {isConditioning && !editing && (
          <Pressable
            style={styles.timerButton}
            onPress={() => {
              const timerMode = isInterval ? 'interval'
                : ['steady_state', 'zone2', 'tempo'].includes(condSubtype) ? 'duration'
                : 'stopwatch';
              const trimmedIvLabel = intervalLabel.trim();
              const cfg: TimerConfig = {
                mode: timerMode,
                subtype: condSubtype,
                modality: condModality,
                work_s: isInterval ? parseInt(workDur, 10) || 30 : undefined,
                rest_s: isInterval ? parseInt(restDur, 10) || 30 : undefined,
                rounds: isInterval ? parseInt(intervalRounds, 10) || 10 : undefined,
                total_s: timerMode === 'duration' ? duration * 60 : undefined,
                label: trimmedIvLabel.length > 0 ? trimmedIvLabel : undefined,
              };
              timerSetup(cfg);
              router.push('/timer');
            }}>
            <Text style={styles.timerButtonText}>Start Timer</Text>
          </Pressable>
        )}
      </View>}

      {editing && (
        <Pressable style={styles.cancelButton} onPress={() => onDone()}>
          <Text style={styles.cancelText}>Cancel</Text>
        </Pressable>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Session card
// ---------------------------------------------------------------------------

function SessionCard({
  session,
  onEdit,
  onDelete,
  coachingCtx,
}: {
  session: TrainingSession;
  onEdit: () => void;
  onDelete: () => void;
  /**
   * Optional daily coaching context used only to build the interpretive
   * post-session note. Parent passes this only when the session is
   * today (historical sessions get undefined — using today's WHOOP to
   * interpret a week-old session would be dishonest).
   */
  coachingCtx?: IntervalCoachingContext;
}) {
  const summary = useMemo(() => summarizeSession(session), [session]);
  const coachingNote = useMemo(
    () => buildIntervalCoachingNote(session, coachingCtx),
    [session, coachingCtx],
  );

  const handleDelete = () => {
    Alert.alert(
      'Delete Session',
      `Delete ${SESSION_TYPE_LABELS[session.type]} on ${session.date}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: onDelete },
      ],
    );
  };

  return (
    <View style={styles.sessionCard}>
      <View style={styles.sessionHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.sessionType}>{summary.headline}</Text>
          <Text style={styles.sessionMeta}>
            <Text style={{ color: INTENSITY_COLORS[session.intensity] }}>
              {session.intensity}
            </Text>
            {summary.sparring_minutes ? ` · ${summary.sparring_minutes}min live` : ''}
            {session.rpe ? ` · RPE ${session.rpe}` : ''}
          </Text>
        </View>
        <View style={styles.sessionActions}>
          <Pressable onPress={onEdit} style={styles.actionBtn}>
            <Text style={styles.actionText}>Edit</Text>
          </Pressable>
          <Pressable onPress={handleDelete} style={styles.actionBtn}>
            <Text style={[styles.actionText, { color: '#ff6b6b' }]}>Delete</Text>
          </Pressable>
        </View>
      </View>
      {session.conditioning && (
        <Text style={styles.sessionCondDetail}>
          {CONDITIONING_SUBTYPE_LABELS[session.conditioning.subtype]}
          {session.conditioning.interval?.label
            ? ` · ${session.conditioning.interval.label}`
            : ''}
          {session.conditioning.modality ? ` · ${MODALITY_LABELS[session.conditioning.modality]}` : ''}
          {session.conditioning.interval
            ? ` · ${session.conditioning.interval.work_duration_s}s/${session.conditioning.interval.rest_duration_s}s × ${session.conditioning.interval.rounds}`
            : ''}
          {session.conditioning.weight_training
            ? ` · ${LIFTING_FOCUS_LABELS[session.conditioning.weight_training.focus]}`
            : ''}
          {session.conditioning.machine_metrics
            ? (() => {
                const m = session.conditioning.machine_metrics;
                const parts: string[] = [];
                if (m.distance_m != null) parts.push(`${m.distance_m}m`);
                if (m.calories != null) parts.push(`${m.calories}kcal`);
                if (m.kilojoules != null) parts.push(`${m.kilojoules}kJ`);
                if (m.avg_power_w != null) parts.push(`${m.avg_power_w}W avg`);
                if (m.max_power_w != null) parts.push(`${m.max_power_w}W peak`);
                if (m.avg_pace_s != null) parts.push(`${m.avg_pace_s}s pace`);
                if (m.avg_speed_kmh != null) parts.push(`${m.avg_speed_kmh}km/h`);
                if (m.strokes != null) parts.push(`${m.strokes} strokes`);
                if (m.avg_hr_bpm != null) parts.push(`${m.avg_hr_bpm}bpm avg`);
                if (m.max_hr_bpm != null) parts.push(`${m.max_hr_bpm}bpm peak`);
                return parts.length ? ` · ${parts.join(' · ')}` : '';
              })()
            : ''}
        </Text>
      )}
      {summary.interval_takeaway && (
        <Text style={styles.sessionTakeaway}>{summary.interval_takeaway}</Text>
      )}
      {coachingNote && (
        <Text style={styles.sessionCoachingNote}>{coachingNote}</Text>
      )}
      {session.segments && session.segments.length > 0 && (
        <Text style={styles.sessionSegments}>
          {session.segments.map((s) => SEGMENT_TYPE_LABELS[s.type]).join(' → ')}
        </Text>
      )}
      {session.segments && session.segments.some((s) => s.map_ref?.position_key) && (
        <Text style={styles.sessionMapRefs}>
          Positions: {session.segments
            .map((s) => s.map_ref?.position_key)
            .filter((k): k is string => !!k)
            .join(' · ')}
        </Text>
      )}
      {session.tags.length > 0 && (
        <Text style={styles.sessionTags}>{session.tags.join(' · ')}</Text>
      )}
      {session.notes ? (
        <Text style={styles.sessionNotes}>{session.notes}</Text>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Today's plan card with quick-log
// ---------------------------------------------------------------------------

function TodayPlanCard({
  onQuickLog,
}: {
  onQuickLog: (type: SessionType, intensity: SessionIntensity) => void;
}) {
  const schedule = usePreferencesStore((s) => s.preferences.schedule);
  const sessions = useTrainingStore((s) => s.sessions);
  const summary = buildDayPlanSummary(todayDate(), schedule, sessions);

  if (summary.status === 'rest_day' || summary.status === 'no_plan') {
    return (
      <View style={styles.planCard}>
        <Text style={styles.planTitle}>Today's Plan</Text>
        <Text style={styles.planEmpty}>
          {summary.status === 'rest_day' ? 'Rest day — no sessions planned.' : 'No sessions planned.'}
        </Text>
      </View>
    );
  }

  const statusColors: Record<string, string> = {
    completed: '#4ade80',
    missed: '#ff6b6b',
    upcoming: '#d4e157',
  };
  const statusIcons: Record<string, string> = {
    completed: '✓',
    missed: '✕',
    upcoming: '○',
  };

  return (
    <View style={styles.planCard}>
      <View style={styles.planHeader}>
        <Text style={styles.planTitle}>Today's Plan</Text>
        <Text style={styles.planCount}>
          {summary.completedCount}/{summary.plannedCount}
        </Text>
      </View>
      {summary.planned.map((p) => (
        <View key={p.planned.id} style={styles.planRow}>
          <Text style={[styles.planIcon, { color: statusColors[p.status] }]}>
            {statusIcons[p.status]}
          </Text>
          <View style={styles.planInfo}>
            <Text style={[styles.planType, p.status === 'completed' && styles.planCompleted]}>
              {SCHEDULE_SESSION_LABELS[p.planned.type] ?? p.planned.type}
              {p.planned.time ? ` · ${p.planned.time}` : ''}
            </Text>
          </View>
          {p.status === 'upcoming' && (
            <Pressable
              style={styles.quickLogBtn}
              onPress={() => onQuickLog(
                p.planned.type as SessionType,
                p.planned.intensity ?? 'moderate',
              )}>
              <Text style={styles.quickLogText}>Log</Text>
            </Pressable>
          )}
          {p.status === 'completed' && (
            <Text style={styles.planDoneLabel}>Done</Text>
          )}
        </View>
      ))}
      {summary.unplannedSessions.length > 0 && (
        <Text style={styles.planExtra}>
          +{summary.unplannedSessions.length} unplanned session{summary.unplannedSessions.length !== 1 ? 's' : ''}
        </Text>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function TrainScreen() {
  const sessions = useTrainingStore((s) => s.sessions);
  const removeSession = useTrainingStore((s) => s.removeSession);
  const syncData = useHealthStore((s) => s.syncData);
  const user = useAuthStore((s) => s.user);
  const addSession = useTrainingStore((s) => s.addSession);
  const whoopDayForCoaching = useWhoopStore((s) => s.day);
  const [editingSession, setEditingSession] = useState<TrainingSession | null>(null);
  const [showForm, setShowForm] = useState(false);
  // Top-level session-type chip selection. Drives whether the
  // exercise-machine connect card renders (HIIT / Steady state only)
  // and seeds the EntryForm's initial mode so the picker doesn't ask
  // again. Cleared when the form is dismissed.
  const [pendingMode, setPendingMode] = useState<'grappling' | 'hiit' | 'zone2' | 'weights' | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [lastLoggedHeadline, setLastLoggedHeadline] = useState<string | null>(null);
  // Compact "progression vs last" string returned from the EntryForm
  // submit path when a HIIT session updated a saved protocol that
  // already had a prior snapshot. Null for non-HIIT sessions, first-
  // ever HIIT sessions on a new protocol, or sessions with no
  // comparable numeric fields.
  const [lastLoggedDelta, setLastLoggedDelta] = useState<string | null>(null);
  // Personal-best celebration label — set when the just-logged HIIT
  // session beat a PR-eligible field on the matched protocol's
  // prior best_metrics snapshot. Null for non-HIIT sessions, first-
  // ever sessions on a new protocol, or sessions that didn't beat
  // any prior record.
  const [lastLoggedNewBest, setLastLoggedNewBest] = useState<string | null>(null);

  // Ephemeral handoff from the timer completion path — set by
  // timer.tsx when a HIIT session is logged through the live timer.
  // Consumed here via the effect below and then cleared so a later
  // Train visit doesn't re-show a stale banner.
  const pendingTimerLog = useHIITProtocolsStore((s) => s.pendingTimerLog);
  const clearPendingTimerLog = useHIITProtocolsStore((s) => s.clearPendingTimerLog);

  // Today's coaching context used to interpret today's logged HIIT
  // sessions in SessionCard. Historical sessions deliberately receive
  // `undefined` — today's WHOOP recovery is not a valid signal for a
  // session logged a week ago, and the note-builder falls back to
  // session-internal signals (HR zone, metrics-only) in that case.
  const todayCoachingCtx = useMemo<IntervalCoachingContext | undefined>(() => {
    const recovery = whoopDayForCoaching?.recovery_score;
    if (recovery == null) return undefined;
    // Lightweight recovery → suggested-intensity bucket. Mirrors the
    // shape of coach-layer.readinessToIntensity without requiring the
    // full daily brief. Green/yellow/red thresholds match the WHOOP
    // industry convention used elsewhere in the app.
    let suggestedIntensity: SessionIntensity;
    if (recovery >= 67) suggestedIntensity = 'hard';
    else if (recovery >= 34) suggestedIntensity = 'moderate';
    else suggestedIntensity = 'light';
    return { whoopRecovery: recovery, suggestedIntensity };
  }, [whoopDayForCoaching]);

  const todayIsoDateForCtx = todayDate();

  // Quick-log: prefill form from planned session
  const handleQuickLog = (type: SessionType, intensity: SessionIntensity) => {
    addSession({
      date: todayDate(),
      type,
      intensity,
      duration_min: 60,
    });
    if (user?.id) syncData(user.id).catch(() => {});
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  // Group sessions by date (last 7 days)
  const groupedSessions = useMemo(() => {
    const sevenDaysAgo = daysAgo(7);
    const recent = sessions
      .filter((s) => s.date >= sevenDaysAgo)
      .sort((a, b) => b.date.localeCompare(a.date) || b.created_at.localeCompare(a.created_at));

    const groups: { date: string; label: string; sessions: TrainingSession[] }[] = [];
    let currentDate = '';
    for (const s of recent) {
      if (s.date !== currentDate) {
        currentDate = s.date;
        groups.push({ date: s.date, label: formatDateLabel(s.date), sessions: [] });
      }
      groups[groups.length - 1].sessions.push(s);
    }
    return groups;
  }, [sessions]);

  const schedule = usePreferencesStore((s) => s.preferences.schedule);

  const handleFormDone = (
    progressionDelta?: string | null,
    newBestLabel?: string | null,
  ) => {
    setEditingSession(null);
    // Close the form on successful submit so the always-visible
    // session-type chip row reappears. User can pick a fresh mode
    // for the next session in one tap.
    setShowForm(false);
    setPendingMode(null);
    setSubmitted(true);
    // Pick the most-recently created session to render its headline.
    // Extend with a plan-alignment clause using buildDayPlanSummary — the
    // user instantly sees whether what they just logged matches their plan.
    const latest = [...sessions].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
    if (latest) {
      const base = summarizeSession(latest).headline;
      const dayPlan = buildDayPlanSummary(latest.date, schedule, sessions);
      let suffix = '';
      if (dayPlan.status === 'on_plan' && dayPlan.completedCount > 0) {
        suffix = ' · matches today\'s plan';
      } else if (dayPlan.status === 'over_plan') {
        suffix = ' · off-plan session';
      } else if (dayPlan.status === 'under_plan') {
        const remaining = dayPlan.plannedCount - dayPlan.completedCount;
        if (remaining > 0) {
          suffix = ` · ${remaining} more planned today`;
        }
      }
      setLastLoggedHeadline(base + suffix);
    } else {
      setLastLoggedHeadline(null);
    }
    setLastLoggedDelta(progressionDelta ?? null);
    setLastLoggedNewBest(newBestLabel ?? null);
    setTimeout(() => setSubmitted(false), 3500);
  };

  // Consume the ephemeral timer-log handoff. When timer.tsx finishes
  // a HIIT session and stashes `pendingTimerLog`, this effect pops
  // the same success banner + delta line the in-form submit path
  // uses, then clears the handoff so subsequent Train visits don't
  // re-show a stale delta. Intentionally leaves `showForm` /
  // `editingSession` untouched — the user may have left the Train
  // form mid-entry before tapping Start Timer, and we don't want to
  // reset their state.
  useEffect(() => {
    if (pendingTimerLog == null) return;
    const delta = pendingTimerLog.delta;
    const newBestLabel = pendingTimerLog.newBestLabel;

    // Compose the banner headline from the most recent training
    // session — the timer path has just added it via addSession, so
    // it sits at the top of the sessions array by created_at.
    const latest = [...sessions].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    )[0];
    if (latest) {
      const base = summarizeSession(latest).headline;
      const dayPlan = buildDayPlanSummary(latest.date, schedule, sessions);
      let suffix = '';
      if (dayPlan.status === 'on_plan' && dayPlan.completedCount > 0) {
        suffix = ' · matches today\'s plan';
      } else if (dayPlan.status === 'over_plan') {
        suffix = ' · off-plan session';
      } else if (dayPlan.status === 'under_plan') {
        const remaining = dayPlan.plannedCount - dayPlan.completedCount;
        if (remaining > 0) {
          suffix = ` · ${remaining} more planned today`;
        }
      }
      setLastLoggedHeadline(base + suffix);
    } else {
      setLastLoggedHeadline('timer session');
    }

    setLastLoggedDelta(delta);
    setLastLoggedNewBest(newBestLabel);
    setSubmitted(true);
    // Clear the handoff immediately so re-entering Train later
    // (e.g. tab switch) does not re-trigger this effect.
    clearPendingTimerLog();
    const t = setTimeout(() => setSubmitted(false), 3500);
    return () => clearTimeout(t);
    // Intentionally only depends on pendingTimerLog identity — we
    // want exactly one banner pop per timer completion.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingTimerLog]);

  const handleEdit = (session: TrainingSession) => {
    setEditingSession(session);
    setShowForm(true);
  };

  const handleDelete = (id: string) => {
    removeSession(id);
    if (user?.id) syncData(user.id).catch(() => {});
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Log Training</Text>

      {/* Live HR / power chip — appears only when a BLE HR or FTMS
          stream is actually flowing. Self-hides after 6s of no
          samples. Build 9+ only. */}
      <LiveHrPill />

      {/* Machine capture is exercise-machine specific (FTMS bikes,
          rowers, ski-ergs, BLE HR straps). It is NOT how to connect
          Apple Health / Health Connect / WHOOP / Polar — those live
          on the Health tab. So only render this card after the user
          picks HIIT or Steady state. */}
      {showForm && (pendingMode === 'hiit' || pendingMode === 'zone2') && (
        <View style={styles.machineConnectWrap}>
          <Text style={styles.machineConnectHeading}>Connect exercise machine</Text>
          <Text style={styles.machineConnectSubcopy}>
            Optional for bikes, rowers, ski-ergs, or Bluetooth heart-rate straps during this session.
          </Text>
          <TrainMachineSection />
        </View>
      )}

      {submitted && !editingSession && (
        <View style={styles.successBanner}>
          <Text style={styles.successText}>
            Logged: {lastLoggedHeadline ?? 'session — coaching updated'}
          </Text>
          {lastLoggedNewBest && (
            <Text style={styles.successNewBest}>{lastLoggedNewBest}</Text>
          )}
          {lastLoggedDelta && (
            <Text
              style={[
                styles.successDelta,
                lastLoggedDelta.startsWith('+') && styles.successDeltaUp,
                lastLoggedDelta.startsWith('-') && styles.successDeltaDown,
                lastLoggedDelta === 'matched last' && styles.successDeltaMatched,
              ]}>
              Progression: {lastLoggedDelta}
            </Text>
          )}
        </View>
      )}

      {/* Today's plan with quick-log */}
      <TodayPlanCard onQuickLog={handleQuickLog} />

      <WeeklyScheduleEditor />


      {/* Session type picker — always visible at the top of the
          Train tab so users don't need to tap a "Log session" button
          first. Tapping a chip opens the form pre-seeded for that
          mode. Hidden when an existing form is open or while editing
          an existing session. */}
      {!showForm && (
        <View style={styles.sessionTypeRow}>
          <Pressable
            style={styles.sessionTypeChip}
            onPress={() => { setPendingMode('grappling'); setShowForm(true); }}>
            <Text style={styles.sessionTypeChipText}>🥋 Grappling</Text>
          </Pressable>
          <Pressable
            style={styles.sessionTypeChip}
            onPress={() => { setPendingMode('hiit'); setShowForm(true); }}>
            <Text style={styles.sessionTypeChipText}>⚡ HIIT</Text>
          </Pressable>
          <Pressable
            style={styles.sessionTypeChip}
            onPress={() => { setPendingMode('zone2'); setShowForm(true); }}>
            <Text style={styles.sessionTypeChipText}>🚴 Steady state</Text>
          </Pressable>
          <Pressable
            style={styles.sessionTypeChip}
            onPress={() => { setPendingMode('weights'); setShowForm(true); }}>
            <Text style={styles.sessionTypeChipText}>🏋️ Weights</Text>
          </Pressable>
        </View>
      )}

      {/* Entry form */}
      {showForm && (
        <EntryForm
          editing={editingSession}
          initialMode={pendingMode}
          onDone={handleFormDone}
        />
      )}

      {/* History */}
      {groupedSessions.length > 0 && (
        <View style={styles.historySection}>
          <Text style={styles.historyTitle}>Recent Sessions</Text>
          {groupedSessions.map((group) => (
            <View key={group.date} style={styles.dateGroup}>
              <Text style={styles.dateLabel}>{group.label}</Text>
              {group.sessions.map((s) => (
                <SessionCard
                  key={s.id}
                  session={s}
                  onEdit={() => handleEdit(s)}
                  onDelete={() => handleDelete(s.id)}
                  coachingCtx={
                    s.date === todayIsoDateForCtx ? todayCoachingCtx : undefined
                  }
                />
              ))}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },

  formSection: { gap: 16 },
  section: { gap: 8 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    opacity: 0.5,
    letterSpacing: 0.5,
  },

  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  pill: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  pillText: { fontSize: 14, color: '#999' },
  pillTextActive: { color: '#d4e157', fontWeight: '600' },

  rowInputs: { flexDirection: 'row', gap: 12 },
  halfInput: { flex: 1, gap: 8 },

  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  textArea: { minHeight: 80 },

  // Presets
  presetRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  presetCard: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 2,
    minWidth: '30%',
  },
  presetCardActive: { borderColor: '#d4e157', backgroundColor: 'rgba(212,225,87,0.08)' },
  presetLabel: { fontSize: 13, fontWeight: '600', color: '#ccc' },
  presetLabelActive: { color: '#d4e157' },
  presetDesc: { fontSize: 10, opacity: 0.5 },
  presetDur: { fontSize: 10, opacity: 0.4 },

  // Segments
  segmentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    marginBottom: 4,
  },
  segmentNum: { fontSize: 12, fontWeight: '700', color: '#555', width: 16 },
  segmentInfo: { flex: 1 },
  segmentType: { fontSize: 13, fontWeight: '600' },
  segmentMeta: { fontSize: 11, opacity: 0.5 },
  segmentMapRef: { fontSize: 11, color: '#d4e157', opacity: 0.8, marginTop: 2 },
  segmentRowExpanded: { borderBottomLeftRadius: 0, borderBottomRightRadius: 0, marginBottom: 0 },
  segmentChevron: { fontSize: 12, opacity: 0.4, marginRight: 4 },
  segmentRemove: { fontSize: 13, color: '#ff6b6b', padding: 4 },
  segmentDetail: {
    backgroundColor: 'rgba(255,255,255,0.02)',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
    marginBottom: 4,
    gap: 8,
  },
  segmentHint: { fontSize: 12, opacity: 0.4, marginBottom: 4 },
  addSegRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  pillSmall: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: 12, borderWidth: 1, borderColor: '#444' },
  pillSmallText: { fontSize: 11, color: '#999' },
  scheduleAddBtn: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: 6, backgroundColor: 'rgba(212,225,87,0.15)' },
  scheduleAddBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  modeHeader: { fontSize: 18, fontWeight: '700', color: '#d4e157', paddingVertical: 4 },
  modeChange: { fontSize: 12, fontWeight: '400', color: '#888' },

  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, justifyContent: 'center' },
  quickRow: { flexDirection: 'row', gap: 10, justifyContent: 'center' },

  // AI coach suggestion
  suggestionCard: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 4,
  },
  suggestionLabel: { fontSize: 11, color: '#d4e157', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  suggestionText: { fontSize: 13, color: '#ccc', lineHeight: 18 },
  suggestionNote: { fontSize: 11, opacity: 0.4 },
  protocolNote: { fontSize: 12, opacity: 0.5, marginTop: 4 },

  // Stacked selector row
  selectorRow: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: 10,
    padding: 12,
    gap: 8,
  },
  selectorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectorLabel: { fontSize: 14, opacity: 0.6 },
  selectorValueRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  selectorValue: { fontSize: 15, fontWeight: '600', color: '#d4e157' },
  selectorChevron: { fontSize: 12, opacity: 0.4 },
  selectorOptions: { gap: 2 },
  selectorOption: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  selectorOptionActive: { backgroundColor: 'rgba(212,225,87,0.1)' },
  selectorOptionText: { fontSize: 14, color: '#999' },
  selectorOptionTextActive: { color: '#d4e157', fontWeight: '600' },
  aiSuggestionBubble: {
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  aiSuggestionText: { fontSize: 11, color: '#d4e157', opacity: 0.8 },
  repeatBtn: {
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.4)',
    backgroundColor: 'rgba(212,225,87,0.04)',
  },
  repeatBtnText: { fontSize: 12, color: '#d4e157', fontWeight: '500' },
  savedProtocolsBlock: {
    gap: 6,
    marginTop: 2,
  },
  savedProtocolsLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  savedProtocolPill: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.35)',
    backgroundColor: 'rgba(212,225,87,0.05)',
    marginRight: 6,
    minWidth: 110,
    maxWidth: 200,
  },
  // Subtle gold-tinted border + fill when the protocol carries a
  // recent PR. Additive on top of the base pill so the recall tap
  // target, backgrounds, and layout remain identical — no layout
  // shift between PR-marked and plain pills.
  savedProtocolPillPR: {
    borderColor: 'rgba(255,216,102,0.6)',
    backgroundColor: 'rgba(255,216,102,0.08)',
  },
  savedProtocolPillNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: 'transparent',
  },
  savedProtocolPillName: {
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '600',
    flexShrink: 1,
  },
  savedProtocolPillBadge: {
    fontSize: 11,
  },
  savedProtocolPillDetail: {
    fontSize: 10,
    color: '#d4e157',
    opacity: 0.65,
    marginTop: 2,
  },
  savedProtocolPillTarget: {
    fontSize: 10,
    color: '#b0b8c3',
    opacity: 0.75,
    marginTop: 2,
    fontStyle: 'italic',
  },
  savedProtocolsHint: {
    fontSize: 10,
    opacity: 0.4,
    fontStyle: 'italic',
  },
  savedProtocolsHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'transparent',
  },
  libraryToggleBtn: {
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  libraryToggleBtnText: {
    fontSize: 11,
    color: '#d4e157',
    fontWeight: '600',
  },

  // My HIIT Library — full-width expanded browser
  libraryList: {
    marginTop: 8,
    gap: 8,
  },
  libraryRow: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: '#2a2f38',
    gap: 6,
  },
  libraryRowPR: {
    borderColor: 'rgba(255,216,102,0.5)',
    backgroundColor: 'rgba(255,216,102,0.06)',
  },
  libraryRowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'transparent',
  },
  libraryRowLabel: {
    fontSize: 15,
    color: '#e6ecf3',
    fontWeight: '700',
    flexShrink: 1,
  },
  libraryRowBadge: { fontSize: 14 },
  libraryRowSchedule: {
    fontSize: 11,
    color: '#b0b8c3',
    opacity: 0.7,
  },
  libraryRowMetricBlock: {
    marginTop: 2,
    backgroundColor: 'transparent',
  },
  libraryRowMetricLabel: {
    fontSize: 9,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  libraryRowMetricValue: {
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '600',
    marginTop: 1,
  },
  libraryRowMetricValuePR: {
    fontSize: 12,
    color: '#ffd866',
    fontWeight: '700',
    marginTop: 1,
  },
  libraryRowFadeCountdown: {
    fontSize: 11,
    color: '#ffa94d',
    fontWeight: '600',
    fontStyle: 'italic',
    marginTop: 3,
  },
  libraryRowMetricMuted: {
    fontSize: 11,
    opacity: 0.35,
    fontStyle: 'italic',
    marginTop: 1,
  },
  libraryRowActions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 6,
    backgroundColor: 'transparent',
  },
  libraryRowRecallBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.08)',
    alignItems: 'center',
  },
  libraryRowRecallBtnText: {
    color: '#d4e157',
    fontSize: 12,
    fontWeight: '600',
  },
  libraryRowRemoveBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#444',
    alignItems: 'center',
  },
  libraryRowRemoveBtnText: { color: '#888', fontSize: 12 },
  derivedTotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.02)',
  },
  derivedTotalLabel: { fontSize: 12, opacity: 0.5, textTransform: 'uppercase', letterSpacing: 0.5 },
  derivedTotalValue: { fontSize: 14, fontWeight: '600', color: '#d4e157' },
  machineHeaderRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  machineSourceHint: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  machineComplementHint: {
    fontSize: 11,
    fontStyle: 'italic',
    opacity: 0.4,
    marginTop: 4,
    lineHeight: 15,
  },
  quickBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 4,
  },
  quickBtnEmoji: { fontSize: 24 },
  quickBtnText: { fontSize: 13, fontWeight: '600', color: '#ccc' },
  moreToggle: { fontSize: 13, color: '#888', paddingVertical: 4 },
  submitRow: { flexDirection: 'row', gap: 10 },
  submitButton: {
    backgroundColor: '#d4e157',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  submitText: { color: '#0a0a0a', fontSize: 17, fontWeight: '700' },
  timerButton: {
    backgroundColor: '#4ade80',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  timerButtonText: { color: '#0a0a0a', fontSize: 15, fontWeight: '700' },

  cancelButton: {
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#666',
  },
  cancelText: { color: '#999', fontSize: 15 },

  successBanner: {
    backgroundColor: 'rgba(74,222,128,0.15)',
    borderWidth: 1,
    borderColor: '#4ade80',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
    gap: 4,
  },
  successText: { color: '#4ade80', fontSize: 14, fontWeight: '600' },
  successNewBest: {
    fontSize: 14,
    fontWeight: '800',
    color: '#ffd866',
    letterSpacing: 0.3,
  },
  successDelta: {
    fontSize: 12,
    fontWeight: '600',
    color: '#b0b8c3',
  },
  successDeltaUp: { color: '#4ade80' },
  successDeltaDown: { color: '#ff8a80' },
  successDeltaMatched: { color: '#d4e157' },

  // History
  historySection: { gap: 12, marginTop: 8 },
  historyTitle: { fontSize: 18, fontWeight: '600' },
  dateGroup: { gap: 8 },
  dateLabel: { fontSize: 14, fontWeight: '600', opacity: 0.6 },

  // Session card
  sessionCard: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 6,
  },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  sessionType: { fontSize: 15, fontWeight: '600' },
  sessionMeta: { fontSize: 13, opacity: 0.7, marginTop: 2 },
  sessionActions: { flexDirection: 'row', gap: 12 },
  actionBtn: { paddingVertical: 2, paddingHorizontal: 4 },
  actionText: { fontSize: 13, color: '#d4e157' },
  sessionCondDetail: { fontSize: 12, color: '#d4e157', opacity: 0.7 },
  sessionTakeaway: { fontSize: 12, color: '#d4e157', opacity: 0.85, fontWeight: '500' },
  sessionCoachingNote: {
    fontSize: 12,
    color: '#b0b8c3',
    opacity: 0.85,
    lineHeight: 17,
    marginTop: 2,
    fontStyle: 'italic',
  },
  sessionSegments: { fontSize: 12, color: '#64b5f6', opacity: 0.7 },
  sessionMapRefs: { fontSize: 11, color: '#d4e157', opacity: 0.7, fontStyle: 'italic' },

  // Top-level session-type picker on the Train tab
  sessionTypeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  sessionTypeChip: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.28)',
    flexGrow: 1,
    flexBasis: '47%',
    alignItems: 'center',
  },
  sessionTypeChipText: { fontSize: 14, fontWeight: '700', color: '#dce97b' },

  machineConnectWrap: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    gap: 6,
  },
  machineConnectHeading: { fontSize: 14, fontWeight: '700' },
  machineConnectSubcopy: { fontSize: 12, opacity: 0.6, lineHeight: 16 },

  weeklyScheduleCard: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  weeklyScheduleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  weeklyScheduleTitle: { fontSize: 15, fontWeight: '700' },
  weeklyScheduleEdit: { fontSize: 13, fontWeight: '700', color: '#d4e157' },
  weeklyScheduleEmpty: { fontSize: 12, opacity: 0.6, lineHeight: 17 },
  weeklyScheduleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  weeklyScheduleCell: {
    alignItems: 'center',
    flex: 1,
    paddingVertical: 4,
  },
  weeklyScheduleDay: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    opacity: 0.55,
  },
  weeklyScheduleCount: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.4)',
    marginTop: 2,
  },
  weeklyScheduleCountActive: { color: '#d4e157', fontWeight: '700' },

  // Plan card
  planCard: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  planHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  planTitle: { fontSize: 16, fontWeight: '600' },
  planCount: { fontSize: 14, color: '#d4e157', fontWeight: '600' },
  planEmpty: { fontSize: 13, opacity: 0.5 },
  planRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
  planIcon: { fontSize: 16, width: 20, textAlign: 'center' },
  planInfo: { flex: 1 },
  planType: { fontSize: 14 },
  planCompleted: { opacity: 0.5, textDecorationLine: 'line-through' },
  planDoneLabel: { fontSize: 11, color: '#4ade80', opacity: 0.7 },
  planExtra: { fontSize: 12, opacity: 0.5, marginTop: 2 },
  quickLogBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: 'rgba(212,225,87,0.15)',
  },
  quickLogText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  showFormBtn: {
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#444',
    borderStyle: 'dashed',
    alignItems: 'center',
  },
  showFormText: { color: '#999', fontSize: 15 },
  sessionTags: { fontSize: 12, opacity: 0.5 },
  sessionNotes: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
});
