import { useEffect, useState } from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  TextInput,
  Alert,
  ActivityIndicator,
  Linking,
  Platform,
} from 'react-native';
import * as Application from 'expo-application';
import Constants from 'expo-constants';
import { useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { useAppTourStore } from '../../src/components/AppTour';
import { useAuthStore } from '../../src/store/auth-store';
import { useDevUnlockStore } from '../../src/store/dev-unlock-store';
import { useBacklogAnalysisStore } from '../../src/store/backlog-analysis-store';
import { usePreferencesStore } from '../../src/store/preferences-store';
import { useConsentStore } from '../../src/store/consent-store';
import { useTierStore } from '../../src/store/tier-store';
import { useNutritionStore } from '../../src/store/nutrition-store';
import { useProfile } from '../../src/hooks/useProfile';
import {
  BELT_SYLLABUS,
  type BeltLevel as LocalBeltLevel,
} from '../../src/data/belt-syllabus';
import {
  buildTechniqueProgressKey,
  useReferenceProgressStore,
  type ProgressStatus,
} from '../../src/store/reference-progress-store';
import {
  DEFAULT_PREFERENCES, TIER_INFO, CAPABILITY_INFO, getTierCapabilities, minimumTierFor,
  DAYS_ORDER, DAY_LABELS, SCHEDULE_SESSION_LABELS, countPlannedSessions,
  GRAPPLING_SCHEDULE_SUBTYPE_LABELS, GRAPPLING_SCHEDULE_SUBTYPES,
} from '@lauburu/shared';
import type {
  CoachingPreferences, Tier, Capability, DayOfWeek, ScheduleSessionType, GrapplingScheduleSubtype,
} from '@lauburu/shared';

// ---------------------------------------------------------------------------
// Reusable components
// ---------------------------------------------------------------------------

function SettingsRow({
  label,
  value,
  onLongPress,
  onPress,
}: {
  label: string;
  value: string;
  onLongPress?: () => void;
  onPress?: () => void;
}) {
  if (onLongPress || onPress) {
    return (
      <Pressable
        style={styles.row}
        onLongPress={onLongPress}
        delayLongPress={800}
        onPress={onPress}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowValue}>{value}</Text>
      </Pressable>
    );
  }
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

function formatBeltRank(currentBelt: string | null): string {
  if (!currentBelt) return 'Not set';
  return `${currentBelt.charAt(0).toUpperCase()}${currentBelt.slice(1)} belt`;
}

function formatMembershipStatus(membershipStatus: string | null | undefined): string {
  if (!membershipStatus) return 'Member';
  return membershipStatus
    .split('_')
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

function isLocalBeltLevel(value: string | null | undefined): value is LocalBeltLevel {
  return value === 'white' || value === 'blue' || value === 'purple' || value === 'brown' || value === 'black';
}

function displayBuildValue(value: unknown): string {
  if (typeof value === 'string' && value.trim().length > 0) return value;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return 'Unavailable';
}

function getAppBuildInfo() {
  const expoConfig = Constants.expoConfig;
  const platformLabel =
    Platform.OS === 'ios' ? 'iOS'
    : Platform.OS === 'android' ? 'Android'
    : Platform.OS;
  const androidVersionCode = expoConfig?.android?.versionCode;
  const iosBuildNumber = expoConfig?.ios?.buildNumber;
  return {
    platform: platformLabel,
    version: displayBuildValue(Application.nativeApplicationVersion ?? expoConfig?.version),
    build: displayBuildValue(Application.nativeBuildVersion),
    androidVersionCode: displayBuildValue(
      Platform.OS === 'android'
        ? Application.nativeBuildVersion ?? androidVersionCode
        : androidVersionCode,
    ),
    iosBuildNumber: displayBuildValue(
      Platform.OS === 'ios'
        ? Application.nativeBuildVersion ?? iosBuildNumber
        : iosBuildNumber,
    ),
  };
}

function formatSyllabusSummary(
  belt: string | null | undefined,
  progress: Record<string, ProgressStatus>,
): string | null {
  if (!isLocalBeltLevel(belt)) return null;
  const items = BELT_SYLLABUS.filter((item) => item.belt === belt);
  if (items.length === 0) return null;

  let started = 0;
  let learned = 0;
  for (const item of items) {
    const key = buildTechniqueProgressKey(
      item.section,
      item.position,
      item.role,
      item.heading,
      item.technique,
    );
    const status = progress[key] ?? 'none';
    if (status !== 'none') started += 1;
    if (status === 'learned') learned += 1;
  }

  return `${belt.charAt(0).toUpperCase()}${belt.slice(1)} syllabus · ${started}/${items.length} started · ${learned} learned`;
}

function PrefPillRow<T extends string>({
  label,
  options,
  labels,
  value,
  onChange,
}: {
  label: string;
  options: T[];
  labels: Record<T, string>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.prefRow}>
      <Text style={styles.prefLabel}>{label}</Text>
      <View style={styles.pillRow}>
        {options.map((opt) => (
          <Pressable
            key={opt}
            style={[styles.pill, value === opt && styles.pillActive]}
            onPress={() => onChange(opt)}>
            <Text style={[styles.pillText, value === opt && styles.pillTextActive]}>
              {labels[opt]}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Auth section
// ---------------------------------------------------------------------------

function AuthForm() {
  const signIn = useAuthStore((s) => s.signIn);
  const signUp = useAuthStore((s) => s.signUp);
  const signInWithApple = useAuthStore((s) => s.signInWithApple);
  const requestPasswordReset = useAuthStore((s) => s.requestPasswordReset);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [resetBusy, setResetBusy] = useState(false);
  const [appleBusy, setAppleBusy] = useState(false);
  const [appleVisible, setAppleVisible] = useState(false);
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  // Apple Sign-In availability probe runs once on mount. Hides the
  // button entirely until the next native build ships
  // expo-apple-authentication. No "Coming soon" stub — just absent.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mod = require('../../src/services/social-auth');
        const ok = typeof mod.appleSignInAvailable === 'function'
          ? await mod.appleSignInAvailable()
          : false;
        if (!cancelled) setAppleVisible(Boolean(ok));
      } catch { /* social-auth or native module missing — keep hidden */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async () => {
    if (!email || !password) return;
    setBusy(true);
    const error =
      mode === 'login'
        ? await signIn(email, password)
        : await signUp(email, password);
    setBusy(false);
    if (error) {
      Alert.alert(mode === 'login' ? 'Sign In Failed' : 'Sign Up Failed', error);
    }
    // On success, onAuthStateChange updates the store and the form is replaced.
  };

  const handleApple = async () => {
    if (appleBusy) return;
    setAppleBusy(true);
    const error = await signInWithApple();
    setAppleBusy(false);
    if (error) Alert.alert('Apple Sign-In', error);
  };

  const handleForgotPassword = async () => {
    const trimmed = email.trim();
    if (trimmed.length === 0) {
      Alert.alert('Forgot password', 'Type your email above first, then tap Forgot password.');
      return;
    }
    setResetBusy(true);
    const error = await requestPasswordReset(trimmed);
    setResetBusy(false);
    if (error) Alert.alert('Couldn\u2019t send reset email', error);
    else Alert.alert('Check your email', 'We sent a password reset link to your email.');
  };

  return (
    <View style={styles.authForm}>
      {appleVisible && (
        <>
          <Pressable
            style={[styles.button, { backgroundColor: '#000' }, appleBusy && styles.buttonDisabled]}
            onPress={handleApple}
            disabled={appleBusy}>
            {appleBusy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={[styles.buttonText, { color: '#fff' }]}> Sign in with Apple</Text>
            )}
          </Pressable>
          <Text style={styles.switchText}>or use email</Text>
        </>
      )}
      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor="#666"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        textContentType="emailAddress"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#666"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        textContentType="password"
      />
      <Pressable
        style={[styles.button, busy && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={busy || !email || !password}>
        {busy ? (
          <ActivityIndicator color="#0a0a0a" />
        ) : (
          <Text style={styles.buttonText}>
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </Text>
        )}
      </Pressable>
      <Pressable onPress={() => setMode(mode === 'login' ? 'signup' : 'login')}>
        <Text style={styles.switchText}>
          {mode === 'login'
            ? "Don't have an account? Sign up"
            : 'Already have an account? Sign in'}
        </Text>
      </Pressable>
      {mode === 'login' && (
        <Pressable onPress={handleForgotPassword} disabled={resetBusy}>
          <Text style={[styles.switchText, { opacity: resetBusy ? 0.5 : 0.85 }]}>
            {resetBusy ? 'Sending reset email…' : 'Forgot password?'}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

function SignedInSection() {
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const { profile, loading, error } = useProfile();
  const progress = useReferenceProgressStore((s) => s.progress);
  const syllabusSummary = formatSyllabusSummary(profile?.current_belt, progress);

  const handleSignOut = () => {
    Alert.alert('Log out?', undefined, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log Out', style: 'destructive', onPress: signOut },
    ]);
  };

  return (
    <>
      <SettingsRow
        label="Status"
        value={loading ? 'Loading…' : formatMembershipStatus(profile?.membership_status)}
      />
      <SettingsRow label="Email" value={user?.email ?? '—'} />
      <SettingsRow
        label="Belt rank"
        value={
          loading
            ? 'Loading…'
            : error
              ? 'Unavailable'
              : formatBeltRank(profile?.current_belt ?? null)
        }
      />
      {syllabusSummary ? (
        <SettingsRow label="Syllabus" value={syllabusSummary} />
      ) : null}
      <BacklogReRunRow />
      <Pressable style={styles.buttonDanger} onPress={handleSignOut}>
        <Text style={styles.buttonDangerText}>Sign Out</Text>
      </Pressable>
    </>
  );
}

/**
 * "Analyse history again" — surfaces re-run + current status summary.
 * Respects the current userId/athleteId (via the store) and never
 * silently overwrites stable memory. Also shows the last run
 * timestamp + current state so users know what they're doing.
 */
function BacklogReRunRow() {
  const status = useBacklogAnalysisStore((s) => s.status);
  const record = useBacklogAnalysisStore((s) => s.record);
  const starting = useBacklogAnalysisStore((s) => s.starting);
  const start = useBacklogAnalysisStore((s) => s.start);
  const refresh = useBacklogAnalysisStore((s) => s.refresh);

  const onPress = () => {
    Alert.alert(
      'Analyse history again?',
      'Coach will re-read your connected sources for the last 30 days and update provisional patterns. Stable memory is never changed without your approval.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Analyse', onPress: () => void start({ windowDays: 30 }) },
      ],
    );
  };

  const label =
    status === 'not_started' ? 'Analyse my history' :
    status === 'running' ? 'Analysis running…' :
    status === 'failed' ? 'Retry analysis' :
    'Analyse history again';

  const lastRun = record?.analysisCompletedAt
    ? `Last run ${record.analysisCompletedAt.slice(0, 10)} · ${record.recordsAnalysed} records` :
    status === 'skipped' ? 'Skipped — run it any time.' : 'Not run yet.';

  return (
    <View style={{ gap: 6, marginBottom: 12 }}>
      <SettingsRow label="Coach backlog" value={lastRun} />
      <Pressable
        style={[styles.button, (starting || status === 'running') && styles.buttonDisabled]}
        onPress={onPress}
        disabled={starting || status === 'running'}>
        <Text style={styles.buttonText}>
          {starting ? 'Starting…' : label}
        </Text>
      </Pressable>
      <Pressable onPress={() => void refresh()} hitSlop={6}>
        <Text style={{ fontSize: 12, color: '#888', textAlign: 'center' }}>
          Refresh status
        </Text>
      </Pressable>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Coaching preferences section
// ---------------------------------------------------------------------------

function PreferencesSection() {
  const prefs = usePreferencesStore((s) => s.preferences);
  const update = usePreferencesStore((s) => s.update);
  const reset = usePreferencesStore((s) => s.reset);

  const isDefault =
    JSON.stringify(prefs) === JSON.stringify(DEFAULT_PREFERENCES);

  return (
    <>
      <PrefPillRow
        label="Recovery approach"
        options={['conservative', 'moderate', 'aggressive'] as const}
        labels={{
          conservative: 'Conservative',
          moderate: 'Balanced',
          aggressive: 'Aggressive',
        }}
        value={prefs.recovery_conservatism}
        onChange={(v) => update({ recovery_conservatism: v })}
      />

      <PrefPillRow
        label="Training bias"
        options={['err_on_rest', 'balanced', 'train_through'] as const}
        labels={{
          err_on_rest: 'Rest-first',
          balanced: 'Balanced',
          train_through: 'Train through',
        }}
        value={prefs.hard_day_bias}
        onChange={(v) => update({ hard_day_bias: v })}
      />

      <PrefPillRow
        label="Goal"
        options={[
          'skill_development',
          'competition',
          'general_fitness',
          'weight_management',
        ] as const}
        labels={{
          skill_development: 'Skill',
          competition: 'Competition',
          general_fitness: 'Fitness',
          weight_management: 'Weight',
        }}
        value={prefs.goal}
        onChange={(v) => update({ goal: v })}
      />

      <PrefPillRow
        label="Coaching tone"
        options={['direct', 'encouraging', 'analytical'] as const}
        labels={{
          direct: 'Direct',
          encouraging: 'Encouraging',
          analytical: 'Analytical',
        }}
        value={prefs.tone}
        onChange={(v) => update({ tone: v })}
      />

      <ScheduleEditor />

      <NutritionTargetsEditor />

      <Pressable
        style={[styles.row, { justifyContent: 'space-between' }]}
        onPress={() => update({ comp_prep: !prefs.comp_prep })}>
        <Text style={styles.rowLabel}>Competition prep mode</Text>
        <Text style={[styles.rowValue, prefs.comp_prep && { color: '#d4e157' }]}>
          {prefs.comp_prep ? 'ON' : 'OFF'}
        </Text>
      </Pressable>

      {!isDefault && (
        <Pressable style={styles.resetButton} onPress={reset}>
          <Text style={styles.resetText}>Reset to Defaults</Text>
        </Pressable>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Data & Privacy
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Schedule Editor
// ---------------------------------------------------------------------------

const SCHEDULE_TYPES: ScheduleSessionType[] = [
  'grappling', 'conditioning', 'recovery', 'other',
];

/**
 * Normalize a user-typed time string into a canonical HH:MM.
 * Accepts "7", "7:30", "730", "19:5", "19:30", with or without colon.
 * Returns '' (empty) if the input cannot be parsed into a valid 24h time.
 * Never throws — invalid input becomes empty (no time set), which the
 * schedule model already treats as "no time" for backward compatibility.
 */
function normalizeTimeInput(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return '';
  // Strip everything that isn't a digit or colon
  const cleaned = trimmed.replace(/[^\d:]/g, '');
  let hours: string;
  let minutes: string;
  if (cleaned.includes(':')) {
    const [h, m = ''] = cleaned.split(':');
    hours = h;
    minutes = m;
  } else if (cleaned.length <= 2) {
    hours = cleaned;
    minutes = '00';
  } else {
    // e.g. "730" → 7:30, "1930" → 19:30
    hours = cleaned.slice(0, cleaned.length - 2);
    minutes = cleaned.slice(-2);
  }
  const h = parseInt(hours, 10);
  const m = parseInt(minutes || '0', 10);
  if (Number.isNaN(h) || Number.isNaN(m)) return '';
  if (h < 0 || h > 23 || m < 0 || m > 59) return '';
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function TimeField({
  value,
  onCommit,
}: {
  value: string | undefined;
  onCommit: (normalized: string) => void;
}) {
  const [text, setText] = useState(value ?? '');
  const display = text;
  return (
    <TextInput
      style={styles.scheduleTimeInput}
      value={display}
      placeholder="--:--"
      placeholderTextColor="#555"
      keyboardType="numbers-and-punctuation"
      maxLength={5}
      onChangeText={setText}
      onBlur={() => {
        const normalized = normalizeTimeInput(text);
        setText(normalized);
        if (normalized !== (value ?? '')) {
          onCommit(normalized);
        }
      }}
    />
  );
}

function ScheduleEditor() {
  const prefs = usePreferencesStore((s) => s.preferences);
  const addSess = usePreferencesStore((s) => s.addSession);
  const removeSess = usePreferencesStore((s) => s.removeSession);
  const toggleSess = usePreferencesStore((s) => s.toggleSession);
  const updateSess = usePreferencesStore((s) => s.updateSession);
  const [expandedDay, setExpandedDay] = useState<DayOfWeek | null>(null);
  const [addingType, setAddingType] = useState<ScheduleSessionType>('grappling');

  /**
   * Render a planned session as a label for the collapsed day summary.
   * Grappling with a subtype shows the subtype name only (the parent
   * category is implied), otherwise shows the top-level label.
   */
  const plannedLabel = (s: { type: ScheduleSessionType; grappling_subtype?: GrapplingScheduleSubtype }) => {
    if (s.type === 'grappling' && s.grappling_subtype) {
      return GRAPPLING_SCHEDULE_SUBTYPE_LABELS[s.grappling_subtype];
    }
    return SCHEDULE_SESSION_LABELS[s.type] ?? s.type;
  };

  return (
    <View style={styles.prefRow}>
      <Text style={styles.prefLabel}>
        Weekly schedule ({countPlannedSessions(prefs.schedule)} sessions)
      </Text>

      {DAYS_ORDER.map((day) => {
        const sessions = prefs.schedule[day];
        const isExpanded = expandedDay === day;
        return (
          <View key={day}>
            <Pressable
              style={[styles.scheduleDayRow, isExpanded && styles.scheduleDayRowExpanded]}
              onPress={() => setExpandedDay(isExpanded ? null : day)}>
              <Text style={styles.scheduleDayName}>{DAY_LABELS[day]}</Text>
              <Text style={styles.scheduleDayCount}>
                {sessions.filter((s) => s.enabled).length > 0
                  ? sessions
                      .filter((s) => s.enabled)
                      .map((s) => {
                        const label = plannedLabel(s);
                        return s.time ? `${s.time} ${label}` : label;
                      })
                      .join(' · ')
                  : 'Rest'}
              </Text>
              <Text style={styles.scheduleChevron}>{isExpanded ? '▾' : '▸'}</Text>
            </Pressable>

            {isExpanded && (
              <View style={styles.scheduleDayExpanded}>
                {sessions.map((s) => (
                  <View key={s.id} style={styles.scheduleSessionBlock}>
                    <View style={styles.scheduleSessionRow}>
                      <Pressable onPress={() => toggleSess(day, s.id)}>
                        <Text style={[styles.scheduleSessionCheck, !s.enabled && { opacity: 0.3 }]}>
                          {s.enabled ? '✓' : '○'}
                        </Text>
                      </Pressable>
                      <Text style={[styles.scheduleSessionName, !s.enabled && { opacity: 0.3 }]}>
                        {plannedLabel(s)}
                      </Text>
                      <TimeField
                        value={s.time}
                        onCommit={(t) => updateSess(day, s.id, { time: t })}
                      />
                      <Pressable onPress={() => removeSess(day, s.id)} hitSlop={6}>
                        <Text style={styles.scheduleRemove}>✕</Text>
                      </Pressable>
                    </View>

                    {/* Grappling subtype picker — only for grappling sessions */}
                    {s.type === 'grappling' && (
                      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                        <View style={styles.pillRow}>
                          {GRAPPLING_SCHEDULE_SUBTYPES.map((gs) => {
                            const isActive = s.grappling_subtype === gs;
                            return (
                              <Pressable
                                key={gs}
                                style={[styles.pillSmall, isActive && styles.pillActive]}
                                onPress={() =>
                                  updateSess(day, s.id, {
                                    grappling_subtype: isActive ? undefined : gs,
                                  })
                                }>
                                <Text
                                  style={[
                                    styles.pillSmallText,
                                    isActive && styles.pillTextActive,
                                  ]}>
                                  {GRAPPLING_SCHEDULE_SUBTYPE_LABELS[gs]}
                                </Text>
                              </Pressable>
                            );
                          })}
                        </View>
                      </ScrollView>
                    )}
                  </View>
                ))}

                {/* Add session */}
                <View style={styles.scheduleAddRow}>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                    <View style={styles.pillRow}>
                      {SCHEDULE_TYPES.map((st) => (
                        <Pressable
                          key={st}
                          style={[styles.pillSmall, addingType === st && styles.pillActive]}
                          onPress={() => setAddingType(st)}>
                          <Text style={[styles.pillSmallText, addingType === st && styles.pillTextActive]}>
                            {SCHEDULE_SESSION_LABELS[st]}
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  </ScrollView>
                  <Pressable
                    style={styles.scheduleAddBtn}
                    onPress={() => addSess(day, addingType)}>
                    <Text style={styles.scheduleAddBtnText}>+ Add</Text>
                  </Pressable>
                </View>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

/**
 * Daily nutrition targets editor — lightweight Settings section that
 * writes through `useNutritionStore.setTargets()`. When targets land,
 * the existing NutritionCard's "% of target" badges light up instantly;
 * clearing targets (Clear button) hides the badges without touching any
 * logged values. Uses local draft state so the user can edit all four
 * fields before committing with Save.
 */
function NutritionTargetsEditor() {
  const targets = useNutritionStore((s) => s.targets);
  const setTargets = useNutritionStore((s) => s.setTargets);

  const [draftCalories, setDraftCalories] = useState(
    targets?.calories_kcal?.toString() ?? '',
  );
  const [draftProtein, setDraftProtein] = useState(
    targets?.protein_g?.toString() ?? '',
  );
  const [draftCarbs, setDraftCarbs] = useState(
    targets?.carbs_g?.toString() ?? '',
  );
  const [draftFat, setDraftFat] = useState(targets?.fat_g?.toString() ?? '');
  const [dirty, setDirty] = useState(false);

  const parseOpt = (s: string): number | undefined => {
    if (!s.trim()) return undefined;
    const n = Number(s);
    return Number.isFinite(n) ? n : undefined;
  };

  const handleSave = () => {
    const next = {
      calories_kcal: parseOpt(draftCalories),
      protein_g: parseOpt(draftProtein),
      carbs_g: parseOpt(draftCarbs),
      fat_g: parseOpt(draftFat),
    };
    // If every field parses to undefined, treat it as a clear.
    const anySet = Object.values(next).some((v) => v != null);
    setTargets(anySet ? next : null);
    setDirty(false);
  };

  const handleClear = () => {
    setDraftCalories('');
    setDraftProtein('');
    setDraftCarbs('');
    setDraftFat('');
    setTargets(null);
    setDirty(false);
  };

  const hasAnyDraft =
    draftCalories.trim() !== '' ||
    draftProtein.trim() !== '' ||
    draftCarbs.trim() !== '' ||
    draftFat.trim() !== '';
  const hasAnySaved = !!targets;

  return (
    <View style={styles.prefRow}>
      <Text style={styles.prefLabel}>
        Daily nutrition targets
        {!hasAnySaved ? <Text style={styles.prefLabelMuted}> · not set</Text> : null}
      </Text>
      <Text style={styles.targetsHint}>
        Used by the Nutrition card on the Health tab to show % of target
        for today's calories and macros.
      </Text>
      <View style={styles.targetsGrid}>
        <View style={styles.targetsField}>
          <Text style={styles.targetsFieldLabel}>Calories (kcal)</Text>
          <TextInput
            style={styles.targetsInput}
            value={draftCalories}
            onChangeText={(t) => {
              setDraftCalories(t);
              setDirty(true);
            }}
            keyboardType="number-pad"
            placeholder="—"
            placeholderTextColor="#555"
          />
        </View>
        <View style={styles.targetsField}>
          <Text style={styles.targetsFieldLabel}>Protein (g)</Text>
          <TextInput
            style={styles.targetsInput}
            value={draftProtein}
            onChangeText={(t) => {
              setDraftProtein(t);
              setDirty(true);
            }}
            keyboardType="number-pad"
            placeholder="—"
            placeholderTextColor="#555"
          />
        </View>
        <View style={styles.targetsField}>
          <Text style={styles.targetsFieldLabel}>Carbs (g)</Text>
          <TextInput
            style={styles.targetsInput}
            value={draftCarbs}
            onChangeText={(t) => {
              setDraftCarbs(t);
              setDirty(true);
            }}
            keyboardType="number-pad"
            placeholder="—"
            placeholderTextColor="#555"
          />
        </View>
        <View style={styles.targetsField}>
          <Text style={styles.targetsFieldLabel}>Fat (g)</Text>
          <TextInput
            style={styles.targetsInput}
            value={draftFat}
            onChangeText={(t) => {
              setDraftFat(t);
              setDirty(true);
            }}
            keyboardType="number-pad"
            placeholder="—"
            placeholderTextColor="#555"
          />
        </View>
      </View>
      <View style={styles.targetsActions}>
        {(hasAnySaved || hasAnyDraft) && (
          <Pressable style={styles.targetsClearBtn} onPress={handleClear}>
            <Text style={styles.targetsClearText}>Clear</Text>
          </Pressable>
        )}
        {dirty && (
          <Pressable style={styles.targetsSaveBtn} onPress={handleSave}>
            <Text style={styles.targetsSaveText}>Save targets</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

function ConsentToggle({
  label,
  description,
  value,
  onChange,
  required,
}: {
  label: string;
  description: string;
  value: boolean;
  onChange: (v: boolean) => void;
  required?: boolean;
}) {
  return (
    <Pressable
      style={styles.consentRow}
      onPress={() => !required && onChange(!value)}>
      <View style={styles.consentText}>
        <Text style={styles.consentLabel}>
          {label}
          {required ? ' (required)' : ''}
        </Text>
        <Text style={styles.consentDesc}>{description}</Text>
      </View>
      <View
        style={[
          styles.consentToggle,
          value && styles.consentToggleOn,
        ]}>
        <Text style={styles.consentToggleText}>{value ? 'ON' : 'OFF'}</Text>
      </View>
    </Pressable>
  );
}

function ConsentSection() {
  const consent = useConsentStore((s) => s.consent);
  const updateConsent = useConsentStore((s) => s.updateConsent);
  const revokeAll = useConsentStore((s) => s.revokeAll);
  const restoreDefaults = useConsentStore((s) => s.restoreDefaults);

  const handleRevokeAll = () => {
    Alert.alert(
      'Revoke Data Consent',
      'This will stop all data collection for coaching improvement. Your existing data will be flagged for deletion.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Revoke All', style: 'destructive', onPress: revokeAll },
      ],
    );
  };

  if (consent.revoked) {
    return (
      <View style={styles.consentRevokedCard}>
        <Text style={styles.consentRevokedText}>
          All data-use consent has been revoked. No training examples will be collected or used.
        </Text>
        <Pressable style={styles.button} onPress={restoreDefaults}>
          <Text style={styles.buttonText}>Restore Defaults</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <>
      <Text style={styles.consentIntro}>
        Your health and training data is used to provide personalized coaching.
        You control how your data is used beyond your own account.
      </Text>

      <ConsentToggle
        label="Personal coaching"
        description="Use your data to improve recommendations for you. Data stays in your account."
        value={consent.personal_coaching}
        onChange={(v) => updateConsent({ personal_coaching: v })}
      />

      <ConsentToggle
        label="Improve global models"
        description="Allow de-identified data to improve coaching for all users. Your identity is stripped."
        value={consent.deidentified_models}
        onChange={(v) => updateConsent({ deidentified_models: v })}
      />

      <ConsentToggle
        label="Research & analytics"
        description="Allow aggregated, anonymous data for research. No individual records are exposed."
        value={consent.analytics_research}
        onChange={(v) => updateConsent({ analytics_research: v })}
      />

      <Pressable style={styles.resetButton} onPress={handleRevokeAll}>
        <Text style={[styles.resetText, { color: '#ff6b6b' }]}>
          Revoke All Data Consent
        </Text>
      </Pressable>
    </>
  );
}

// ---------------------------------------------------------------------------
// Tier & Capabilities
// ---------------------------------------------------------------------------

const ALL_TIERS: Tier[] = ['free', 'low_cost', 'pro', 'ai_premium'];

function TierSection() {
  const effectiveTier = useTierStore((s) => s.effectiveTier());
  const devOverride = useTierStore((s) => s.devOverride);
  const setDevOverride = useTierStore((s) => s.setDevOverride);
  const capabilities = useTierStore((s) => s.capabilities());
  const tierInfo = TIER_INFO[effectiveTier];

  // Group capabilities by tier for display
  const enabledCaps = capabilities;
  const allCaps: Capability[] = [
    'local_coaching', 'manual_training_log', 'feedback_capture',
    'local_health_view', 'basic_insights', 'health_sync',
    'backend_persistence', 'export_ai_payload', 'preference_coaching',
    'training_history', 'byo_ai', 'advanced_reports', 'cronometer_sync',
    // 'ergzone_sync' intentionally hidden — ErgZone is not a supported
    // integration path. Machine input flows through our own BLE/FTMS
    // capture (see Machine capture card in Health → Integrations).
    'data_export_full', 'model_training_participation',
    'hosted_ai_coaching', 'daily_ai_recommendations',
    'advanced_ai_insights', 'priority_model_training',
  ];
  const disabledCaps = allCaps.filter((c) => !enabledCaps.includes(c));

  return (
    <>
      <View style={styles.tierHeader}>
        <Text style={[styles.tierBadge, { color: tierInfo.color, borderColor: tierInfo.color }]}>
          {tierInfo.label}
        </Text>
        <Text style={styles.tierNote}>
          {devOverride ? '(dev override)' : ''}
        </Text>
      </View>

      {/* Enabled capabilities */}
      <View style={styles.capList}>
        {enabledCaps.slice(0, 8).map((cap) => {
          const info = CAPABILITY_INFO[cap];
          return (
            <View key={cap} style={styles.capRow}>
              <Text style={styles.capEnabled}>✓</Text>
              <Text style={styles.capLabel}>{info.label}</Text>
            </View>
          );
        })}
        {enabledCaps.length > 8 && (
          <Text style={styles.capMore}>+{enabledCaps.length - 8} more</Text>
        )}
      </View>

      {/* Hidden premium capabilities */}
      {disabledCaps.length > 0 && (
        <View style={styles.capList}>
          <Text style={styles.capSectionLabel}>Premium</Text>
          {disabledCaps.slice(0, 5).map((cap) => {
            const info = CAPABILITY_INFO[cap];
            const minTier = minimumTierFor(cap);
            return (
              <View key={cap} style={styles.capRow}>
                <Text style={styles.capLocked}>✗</Text>
                <Text style={styles.capLabelLocked}>{info.label}</Text>
                <Text style={styles.capTierReq}>{TIER_INFO[minTier].label}</Text>
              </View>
            );
          })}
          {disabledCaps.length > 5 && (
            <Text style={styles.capMore}>+{disabledCaps.length - 5} more in higher tiers</Text>
          )}
        </View>
      )}

      {/* Dev tier override */}
      <View style={styles.devSection}>
        <Text style={styles.devLabel}>Dev Override</Text>
        <View style={styles.pillRow}>
          <Pressable
            style={[styles.pill, devOverride === null && styles.pillActive]}
            onPress={() => setDevOverride(null)}>
            <Text style={[styles.pillText, devOverride === null && styles.pillTextActive]}>
              None
            </Text>
          </Pressable>
          {ALL_TIERS.map((t) => (
            <Pressable
              key={t}
              style={[styles.pill, devOverride === t && { borderColor: TIER_INFO[t].color, backgroundColor: TIER_INFO[t].color + '15' }]}
              onPress={() => setDevOverride(t)}>
              <Text
                style={[styles.pillText, devOverride === t && { color: TIER_INFO[t].color, fontWeight: '600' }]}>
                {TIER_INFO[t].label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>
    </>
  );
}

// Main screen
// ---------------------------------------------------------------------------

function ReplayTourButton() {
  const replay = useAppTourStore((s) => s.replay);
  return (
    <Pressable style={styles.row} onPress={replay}>
      <Text style={styles.rowLabel}>Replay app tour</Text>
      <Text style={styles.rowValue}>Walk through all features</Text>
    </Pressable>
  );
}

/**
 * Admin gate for the tester-tools section. The recent-feedback viewer
 * hits an unauthenticated /api/feedback/recent endpoint, so all tester
 * submissions are visible to whoever can reach it. Until the viewer is
 * moved behind a real admin auth surface, gate the entry point to the
 * account that actually reviews feedback.
 */
const ADMIN_EMAILS = new Set(['aaron.t.maher@gmail.com']);

function TesterToolsSection() {
  const router = useRouter();
  return (
    <Pressable
      style={styles.row}
      onPress={() => router.push('/feedback-viewer')}
      accessibilityRole="button"
      accessibilityLabel="Open recent tester feedback viewer"
    >
      <Text style={styles.rowLabel}>Recent feedback</Text>
      <Text style={styles.rowValue}>View tester reports in-app</Text>
    </Pressable>
  );
}

export default function SettingsScreen() {
  const router = useRouter();
  const status = useAuthStore((s) => s.status);
  const userEmail = useAuthStore((s) => s.user?.email ?? null);
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail.toLowerCase());
  const devUnlocked = useDevUnlockStore((s) => s.unlocked);
  const unlockDevTools = useDevUnlockStore((s) => s.unlock);
  const localDevAccess = __DEV__ && devUnlocked;
  const showDevTools = isAdmin || localDevAccess;
  const buildInfo = getAppBuildInfo();
  const versionTapsRef = useState({ count: 0, ts: 0 })[0];
  const handleVersionTap = () => {
    if (showDevTools) return; // already unlocked, do nothing
    const now = Date.now();
    if (now - versionTapsRef.ts > 3000) versionTapsRef.count = 0;
    versionTapsRef.ts = now;
    versionTapsRef.count += 1;
    if (versionTapsRef.count >= 7) {
      versionTapsRef.count = 0;
      void unlockDevTools();
      Alert.alert('Developer tools unlocked', 'Open Settings → About → Developer tools.');
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Settings</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        {status === 'member' ? <SignedInSection /> : <AuthForm />}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Coaching Preferences</Text>
        <PreferencesSection />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Subscription & Features</Text>
        <TierSection />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data & Privacy</Text>
        <ConsentSection />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Help</Text>
        <ReplayTourButton />
      </View>

      {isAdmin && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Tester tools</Text>
          <TesterToolsSection />
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <SettingsRow label="Platform" value={buildInfo.platform} />
        <SettingsRow
          label="Version"
          value={buildInfo.version}
          onPress={handleVersionTap}
          onLongPress={showDevTools ? () => router.push('/admin-dev') : undefined}
        />
        <SettingsRow label="Build" value={buildInfo.build} />
        <SettingsRow
          label="Android version code"
          value={buildInfo.androidVersionCode}
        />
        <SettingsRow
          label="iOS build number"
          value={buildInfo.iosBuildNumber}
        />
        <SettingsRow label="Website" value="lauburugrapplingmap.com" />
        <Pressable
          style={styles.row}
          onPress={() => Linking.openURL('https://www.lauburugrapplingmap.com/privacy/')}
          accessibilityRole="link"
          accessibilityLabel="Open privacy policy in browser">
          <Text style={styles.rowLabel}>Privacy policy</Text>
          <Text style={[styles.rowValue, { color: '#d4e157' }]}>Open</Text>
        </Pressable>
        <Pressable
          style={styles.row}
          onPress={() => Linking.openURL('https://www.lauburugrapplingmap.com/account-deletion/')}
          accessibilityRole="link"
          accessibilityLabel="Open data deletion request page in browser">
          <Text style={styles.rowLabel}>Request account / data deletion</Text>
          <Text style={[styles.rowValue, { color: '#d4e157' }]}>Open</Text>
        </Pressable>
        {showDevTools ? (
          <Pressable style={styles.row} onPress={() => router.push('/admin-dev')}>
            <Text style={styles.rowLabel}>Developer tools</Text>
            <Text style={[styles.rowValue, { color: '#d4e157' }]}>Open</Text>
          </Pressable>
        ) : __DEV__ ? (
          <Pressable
            style={styles.row}
            onPress={() => {
              Alert.alert(
                'Project owner mode',
                'This enables the Lauburu Admin / Dev Control Center on this device — workflow triggers, backend status, prompt library. Only the project owner should enable this. Continue?',
                [
                  { text: 'Cancel', style: 'cancel' },
                  {
                    text: 'Enable on this device',
                    style: 'destructive',
                    onPress: async () => {
                      await unlockDevTools();
                      Alert.alert('Developer tools enabled', 'A Developer tools row now appears here. Open it any time, or use the wrench Dev FAB.');
                    },
                  },
                ],
              );
            }}>
            <Text style={[styles.rowLabel, { opacity: 0.55 }]}>Project owner mode</Text>
            <Text style={[styles.rowValue, { opacity: 0.45 }]}>Off</Text>
          </Pressable>
        ) : null}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  // Bottom padding clears the global AI/Feedback/Dev FAB stack so
  // About rows are not covered when scrolled to the foot.
  content: { padding: 20, gap: 24, paddingBottom: 200 },
  heading: { fontSize: 24, fontWeight: '700' },
  section: { gap: 12 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    opacity: 0.5,
    letterSpacing: 1,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  rowLabel: { fontSize: 16, flexShrink: 1, paddingRight: 12 },
  rowValue: { fontSize: 14, opacity: 0.5, flexShrink: 1, textAlign: 'right' },
  authForm: { gap: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  button: {
    backgroundColor: '#d4e157',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#0a0a0a', fontSize: 16, fontWeight: '600' },
  buttonDanger: {
    borderWidth: 1,
    borderColor: '#ff4444',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  buttonDangerText: { color: '#ff4444', fontSize: 16, fontWeight: '600' },
  switchText: {
    textAlign: 'center',
    color: '#d4e157',
    fontSize: 14,
    paddingVertical: 4,
  },

  // Preferences
  prefRow: { gap: 8 },
  prefLabel: { fontSize: 14 },
  prefLabelMuted: { fontSize: 12, opacity: 0.4, fontWeight: '400' },

  // Nutrition targets editor
  targetsHint: { fontSize: 11, opacity: 0.5, lineHeight: 16 },
  targetsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  targetsField: { flexBasis: '48%', maxWidth: '48%', gap: 4 },
  targetsFieldLabel: {
    fontSize: 11,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  targetsInput: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 14,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  targetsActions: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'flex-end',
  },
  targetsClearBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#666',
  },
  targetsClearText: { color: '#999', fontSize: 12 },
  targetsSaveBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    backgroundColor: '#d4e157',
  },
  targetsSaveText: { color: '#0a0a0a', fontSize: 12, fontWeight: '700' },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  pill: {
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  pillText: { fontSize: 13, color: '#999' },
  pillTextActive: { color: '#d4e157', fontWeight: '600' },
  resetButton: {
    borderWidth: 1,
    borderColor: '#666',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  resetText: { color: '#999', fontSize: 14 },

  // Consent
  consentIntro: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
  consentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 12,
  },
  consentText: { flex: 1, gap: 2 },
  consentLabel: { fontSize: 14, fontWeight: '600' },
  consentDesc: { fontSize: 12, opacity: 0.5, lineHeight: 16 },
  consentToggle: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#666',
  },
  consentToggleOn: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.15)',
  },
  consentToggleText: { fontSize: 12, fontWeight: '600', color: '#999' },
  consentRevokedCard: {
    padding: 16,
    borderRadius: 10,
    backgroundColor: 'rgba(255,107,107,0.1)',
    borderWidth: 1,
    borderColor: '#ff6b6b',
    gap: 12,
  },
  consentRevokedText: { fontSize: 13, color: '#ff6b6b', lineHeight: 18 },

  // Tier
  tierHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  tierBadge: {
    fontSize: 16,
    fontWeight: '700',
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 10,
  },
  tierNote: { fontSize: 12, opacity: 0.4 },
  capList: { gap: 4 },
  capSectionLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 4 },
  capRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  capEnabled: { fontSize: 13, color: '#4ade80', width: 18 },
  capLocked: { fontSize: 13, color: '#666', width: 18 },
  capLabel: { fontSize: 13, flex: 1 },
  capLabelLocked: { fontSize: 13, opacity: 0.4, flex: 1 },
  capTierReq: { fontSize: 10, opacity: 0.3 },
  capMore: { fontSize: 11, opacity: 0.3, paddingLeft: 26 },
  devSection: { gap: 6, marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)' },
  devLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5 },

  // Schedule editor
  scheduleDayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    marginBottom: 2,
    gap: 8,
  },
  scheduleDayRowExpanded: { backgroundColor: 'rgba(212,225,87,0.06)', borderBottomLeftRadius: 0, borderBottomRightRadius: 0 },
  scheduleDayName: { fontSize: 14, fontWeight: '600', width: 36 },
  scheduleDayCount: { flex: 1, fontSize: 12, opacity: 0.6 },
  scheduleChevron: { fontSize: 12, opacity: 0.4 },
  scheduleDayExpanded: {
    backgroundColor: 'rgba(255,255,255,0.02)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
    marginBottom: 2,
    gap: 6,
  },
  scheduleSessionBlock: { gap: 6 },
  scheduleSessionRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scheduleSessionCheck: { fontSize: 16, color: '#4ade80', width: 20 },
  scheduleSessionName: { flex: 1, fontSize: 13 },
  scheduleTimeInput: {
    width: 60,
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.04)',
    color: '#f0f0f0',
    fontSize: 13,
    textAlign: 'center',
  },
  scheduleRemove: { fontSize: 14, color: '#ff6b6b', padding: 4 },
  scheduleAddRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  scheduleAddBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: 'rgba(212,225,87,0.15)',
  },
  scheduleAddBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  pillSmall: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillSmallText: { fontSize: 11, color: '#999' },
});
