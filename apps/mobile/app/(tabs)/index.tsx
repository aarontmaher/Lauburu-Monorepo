import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, ScrollView, ActivityIndicator, Pressable, TextInput, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';
import { useHealthStore } from '../../src/store/health-store';
import { useTrainingStore } from '../../src/store/training-store';
import { useWhoopStore } from '../../src/store/whoop-store';
import { useNutritionStore } from '../../src/store/nutrition-store';
import { usePreferencesStore } from '../../src/store/preferences-store';
import { useCoachingCasesStore } from '../../src/store/coaching-cases-store';
import { useFeedbackStore } from '../../src/store/feedback-store';
import {
  useReferenceProgressStore,
  buildTechniqueProgressKey,
  parseProgressKey,
  type ProgressStatus,
} from '../../src/store/reference-progress-store';
import { buildLastHIITHomeNote } from '../../src/services/hiit-home-note';
import {
  ATHLETE_CAPABILITY_COPY,
  formatSeedWhoopLabel,
} from '../../src/services/athlete-capability-display';
import { useProgress } from '../../src/hooks/useProgress';
import { AthleteCapabilitySummary } from '../../src/components/AthleteCapabilitySummary';
import { BacklogAnalysisCard } from '../../src/components/BacklogAnalysisCard';
import { SuggestedMetricsCard } from '../../src/components/SuggestedMetricsCard';
import { AthleteStateStrip } from '../../src/components/AthleteStateStrip';
import { REFERENCE_SECTIONS } from '../../src/data/reference-seed';
import { REFERENCE_TECHNIQUES } from '../../src/data/reference-techniques';
import type { ReadinessLevel, DailyCoachingBrief } from '@lauburu/shared';
import {
  SESSION_TYPE_LABELS,
  buildDailyCoachingBrief,
  getTodayPlan,
} from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function GuestBanner() {
  const router = useRouter();
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Welcome to Lauburu</Text>
      <Text style={styles.cardBody}>
        Create an account to save your training, health sync, and AI Coach history.
      </Text>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 4 }}>
        <Pressable
          style={{
            flex: 1,
            paddingVertical: 12,
            borderRadius: 10,
            backgroundColor: '#d4e157',
            alignItems: 'center',
          }}
          onPress={() => router.push({ pathname: '/(tabs)/settings', params: { auth: 'sign_up' } })}>
          <Text style={{ color: '#0b0b0b', fontWeight: '700', fontSize: 14 }}>Create account</Text>
        </Pressable>
        <Pressable
          style={{
            flex: 1,
            paddingVertical: 12,
            borderRadius: 10,
            backgroundColor: 'rgba(255,255,255,0.06)',
            borderWidth: 1,
            borderColor: 'rgba(255,255,255,0.16)',
            alignItems: 'center',
          }}
          onPress={() => router.push({ pathname: '/(tabs)/settings', params: { auth: 'sign_in' } })}>
          <Text style={{ color: '#f5f7f9', fontWeight: '700', fontSize: 14 }}>Sign in</Text>
        </Pressable>
      </View>
    </View>
  );
}

type TechniqueRecommendation = {
  section: string;
  position: string;
  role: string;
  heading: string;
  technique: string;
  reason: string;
};

const POSITION_META = (() => {
  const map = new Map<string, {
    section: string;
    builtOut: boolean;
    headings: ReadonlyArray<string>;
    perspectives: ReadonlyArray<string>;
  }>();
  for (const section of REFERENCE_SECTIONS) {
    for (const position of section.positions) {
      map.set(position.name, {
        section: section.label,
        builtOut: !!position.built_out,
        headings: position.headings,
        perspectives: position.perspectives,
      });
    }
  }
  return map;
})();

const GENERIC_TECHNIQUE_LABELS = new Set(['Defence', 'Subtopic', '`']);

function lookupPositionTechniques(
  positionName: string,
): Record<string, Record<string, string[]>> | null {
  const direct = REFERENCE_TECHNIQUES[positionName];
  if (direct) return direct;
  const withYou = REFERENCE_TECHNIQUES[`${positionName} (You)`];
  if (withYou) return withYou;
  return null;
}

function normalizeHeading(heading: string): string {
  return heading.split('/')[0]!.trim().toLowerCase();
}

function techniquesForHeading(
  positionTechs: Record<string, Record<string, string[]>> | null,
  role: string,
  heading: string,
): string[] {
  if (!positionTechs) return [];
  const roleMap = positionTechs[role];
  if (!roleMap) return [];
  if (roleMap[heading]) return roleMap[heading];
  const want = normalizeHeading(heading);
  for (const key of Object.keys(roleMap)) {
    if (normalizeHeading(key) === want) return roleMap[key];
  }
  return [];
}

function parseTransitionEdges(labels: string[]): Array<{ label: string; destination: string }> {
  const edges: Array<{ label: string; destination: string }> = [];
  for (const raw of labels) {
    const idx = raw.indexOf('→');
    if (idx < 0) continue;
    const label = raw.slice(0, idx).trim();
    const destination = raw.slice(idx + 1).trim();
    if (!label || !destination) continue;
    edges.push({ label, destination });
  }
  return edges;
}

function headingPriority(
  heading: string,
  goal: ReturnType<typeof usePreferencesStore.getState>['preferences']['goal'],
): number {
  const normalized = normalizeHeading(heading);
  let score = 0;
  if (normalized === 'offence') score += 8;
  else if (normalized === 'control') score += 6;
  else if (normalized === 'setups') score += 5;
  else if (normalized === 'submissions') score += 7;
  else if (normalized === 'defence') score += 2;

  if (goal === 'competition' && (normalized === 'offence' || normalized === 'submissions')) {
    score += 5;
  } else if (goal === 'skill_development' && (normalized === 'control' || normalized === 'setups')) {
    score += 3;
  }
  return score;
}

function chooseRoleForPosition(positionName: string): string | null {
  const meta = POSITION_META.get(positionName);
  const techs = lookupPositionTechniques(positionName);
  if (!meta || !techs) return null;

  let bestRole: string | null = null;
  let bestScore = -1;
  for (const role of meta.perspectives) {
    let score = 0;
    for (const heading of meta.headings) {
      if (heading === 'Offensive transitions') continue;
      score += techniquesForHeading(techs, role, heading).filter(
        (label) => !GENERIC_TECHNIQUE_LABELS.has(label),
      ).length;
    }
    if (score > bestScore) {
      bestScore = score;
      bestRole = role;
    }
  }
  return bestRole;
}

function buildNextTechniqueRecommendation(args: {
  progressMap: Record<string, ProgressStatus>;
  updatedAtMap: Record<string, string>;
  goal: ReturnType<typeof usePreferencesStore.getState>['preferences']['goal'];
}): TechniqueRecommendation | null {
  const { progressMap, updatedAtMap, goal } = args;
  const seedScores = new Map<string, number>();
  const seedReasons = new Map<string, string[]>();
  const learnedCounts = new Map<string, number>();
  const roleCounts = new Map<string, number>();

  const addSeed = (
    position: string,
    role: string,
    score: number,
    reason: string,
  ) => {
    const key = `${position}|${role}`;
    seedScores.set(key, (seedScores.get(key) ?? 0) + score);
    const reasons = seedReasons.get(key) ?? [];
    if (!reasons.includes(reason)) reasons.push(reason);
    seedReasons.set(key, reasons);
    roleCounts.set(key, (roleCounts.get(key) ?? 0) + 1);
  };

  for (const [key, status] of Object.entries(progressMap)) {
    const parsed = parseProgressKey(key);
    if (!parsed) continue;
    const seedWeight =
      status === 'drilling' ? 42 : status === 'learned' ? 24 : 12;
    if (parsed.kind === 'tech') {
      addSeed(
        parsed.position,
        parsed.role,
        seedWeight,
        status === 'drilling'
          ? `you're drilling from ${parsed.position}`
          : status === 'learned'
            ? `you already know core material from ${parsed.position}`
            : `you're tracking options from ${parsed.position}`,
      );
      if (status === 'learned') {
        learnedCounts.set(
          parsed.position,
          (learnedCounts.get(parsed.position) ?? 0) + 1,
        );
      }
    } else {
      addSeed(
        parsed.sourcePosition,
        parsed.sourceRole,
        seedWeight,
        status === 'drilling'
          ? `you're drilling transitions out of ${parsed.sourcePosition}`
          : `you've built familiarity around ${parsed.sourcePosition}`,
      );
      const destRole = chooseRoleForPosition(parsed.destination);
      if (destRole) {
        addSeed(
          parsed.destination,
          destRole,
          Math.max(8, seedWeight - 10),
          `${parsed.label} connects naturally into ${parsed.destination}`,
        );
      }
    }
  }

  const recentBoosts = [14, 10, 7, 5, 3];
  const recentEntries = Object.entries(updatedAtMap)
    .map(([key, iso]) => ({ key, ts: Date.parse(iso) }))
    .filter((entry) => Number.isFinite(entry.ts))
    .sort((a, b) => b.ts - a.ts)
    .slice(0, recentBoosts.length);

  recentEntries.forEach((entry, idx) => {
    const parsed = parseProgressKey(entry.key);
    if (!parsed) return;
    const boost = recentBoosts[idx] ?? 0;
    if (parsed.kind === 'tech') {
      addSeed(parsed.position, parsed.role, boost, `you touched ${parsed.position} recently`);
    } else {
      addSeed(
        parsed.sourcePosition,
        parsed.sourceRole,
        boost,
        `you touched ${parsed.sourcePosition} recently`,
      );
      const destRole = chooseRoleForPosition(parsed.destination);
      if (destRole) {
        addSeed(
          parsed.destination,
          destRole,
          Math.max(2, Math.floor(boost / 2)),
          `${parsed.destination} is adjacent to your recent work`,
        );
      }
    }
  });

  const topGamePositions = [...learnedCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  for (const [position, count] of topGamePositions) {
    const role = [...roleCounts.keys()]
      .find((key) => key.startsWith(`${position}|`))
      ?.split('|')[1] ?? chooseRoleForPosition(position);
    if (!role) continue;
    addSeed(
      position,
      role,
      8 + count * 2,
      `most of your learned game is already around ${position}`,
    );
  }

  const candidateMap = new Map<string, TechniqueRecommendation & { score: number }>();

  const considerTechnique = (
    section: string,
    position: string,
    role: string,
    heading: string,
    technique: string,
    score: number,
    reason: string,
  ) => {
    const key = buildTechniqueProgressKey(section, position, role, heading, technique);
    const status = progressMap[key] ?? 'none';
    if (status === 'drilling' || status === 'learned') return;
    let adjusted = score + headingPriority(heading, goal);
    if (status === 'tracking') adjusted += 10;
    adjusted += Math.min(learnedCounts.get(position) ?? 0, 3) * 2;
    const existing = candidateMap.get(key);
    if (!existing || adjusted > existing.score) {
      candidateMap.set(key, {
        section,
        position,
        role,
        heading,
        technique,
        reason,
        score: adjusted,
      });
    }
  };

  for (const [seedKey, seedScore] of seedScores.entries()) {
    const [position, role] = seedKey.split('|');
    const meta = POSITION_META.get(position);
    const techs = lookupPositionTechniques(position);
    if (!meta || !techs) continue;

    const seedReason = seedReasons.get(seedKey)?.[0] ?? `your work is already centered on ${position}`;
    for (const heading of meta.headings) {
      if (heading === 'Offensive transitions') continue;
      for (const technique of techniquesForHeading(techs, role, heading)) {
        if (GENERIC_TECHNIQUE_LABELS.has(technique)) continue;
        considerTechnique(
          meta.section,
          position,
          role,
          heading,
          technique,
          seedScore,
          `It fits because ${seedReason}.`,
        );
      }
    }

    const transitions = parseTransitionEdges(
      techniquesForHeading(techs, role, 'Offensive transitions'),
    );
    for (const edge of transitions) {
      const destMeta = POSITION_META.get(edge.destination);
      const destRole = chooseRoleForPosition(edge.destination);
      const destTechs = lookupPositionTechniques(edge.destination);
      if (!destMeta || !destRole || !destTechs) continue;
      for (const heading of destMeta.headings) {
        if (heading === 'Offensive transitions') continue;
        for (const technique of techniquesForHeading(destTechs, destRole, heading)) {
          if (GENERIC_TECHNIQUE_LABELS.has(technique)) continue;
          considerTechnique(
            destMeta.section,
            edge.destination,
            destRole,
            heading,
            technique,
            seedScore + 14,
            `It builds naturally off ${position} through ${edge.label}.`,
          );
        }
      }
    }
  }

  const ranked = [...candidateMap.values()].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (a.position !== b.position) return a.position.localeCompare(b.position);
    return a.technique.localeCompare(b.technique);
  });
  if (ranked.length > 0) {
    const { score: _score, ...best } = ranked[0]!;
    return best;
  }

  for (const [position, meta] of POSITION_META.entries()) {
    if (!meta.builtOut) continue;
    const role = chooseRoleForPosition(position);
    const techs = lookupPositionTechniques(position);
    if (!role || !techs) continue;
    for (const heading of meta.headings) {
      if (heading === 'Offensive transitions') continue;
      const technique = techniquesForHeading(techs, role, heading).find(
        (label) => !GENERIC_TECHNIQUE_LABELS.has(label),
      );
      if (technique) {
        return {
          section: meta.section,
          position,
          role,
          heading,
          technique,
          reason: 'This is a solid built-out starting point until more of your own game is tracked.',
        };
      }
    }
  }

  return null;
}

function CoachingHistoryEntryCard() {
  const router = useRouter();
  const cases = useCoachingCasesStore((s) => s.cases);
  const helped = cases.filter((c) => c.usefulness === 'helped').length;
  return (
    <Pressable
      style={styles.referenceCard}
      onPress={() => router.push('/coaching-history')}>
      <View style={styles.referenceHeader}>
        <Text style={styles.cardTitle}>Coaching history</Text>
        <Text style={styles.referenceChevron}>→</Text>
      </View>
      <Text style={styles.cardBody}>
        {cases.length === 0
          ? 'No cases yet. Use the AI launcher to start one.'
          : `${cases.length} saved ${cases.length === 1 ? 'case' : 'cases'}${helped > 0 ? ` · ${helped} marked helpful` : ''}.`}
      </Text>
    </Pressable>
  );
}

function NutritionHeadline() {
  const today = useNutritionStore((s) => s.today);
  const targets = useNutritionStore((s) => s.targets);
  if (!today) return null;
  const cal = today.calories_kcal;
  const protein = today.protein_g;
  if (cal == null && protein == null) return null;
  const calDisplay =
    cal != null
      ? targets?.calories_kcal
        ? `${Math.round(cal)} / ${Math.round(targets.calories_kcal)} kcal`
        : `${Math.round(cal)} kcal`
      : '—';
  const proteinDisplay =
    protein != null
      ? targets?.protein_g
        ? ` · ${Math.round(protein)} / ${Math.round(targets.protein_g)}g protein`
        : ` · ${Math.round(protein)}g protein`
      : '';
  // Bodyweight-relative protein-per-kg — the most useful fueling number
  // for a strength/grappling athlete. Shown inline when both weight +
  // protein are logged today. Green ≥1.6 g/kg, amber 1.2–1.6, red <1.2.
  const perKgDisplay = (() => {
    const w = (today as any).body_weight_kg as number | undefined;
    if (w == null || w <= 0 || protein == null) return null;
    const perKg = protein / w;
    return `${perKg.toFixed(1)} g/kg`;
  })();
  const waterDisplay = today.water_ml ? ` · ${Math.round(today.water_ml / 100) / 10}L` : '';
  return (
    <View style={styles.fuelHeadline}>
      <Text style={styles.fuelLabel}>Today's fuel</Text>
      <Text style={styles.fuelValue}>
        {calDisplay}
        {proteinDisplay}
        {perKgDisplay ? ` · ${perKgDisplay}` : ''}
        {waterDisplay}
      </Text>
    </View>
  );
}

/**
 * Compact Home-screen chip showing Apple Health / Health Connect
 * connection state at a glance — matches the "source-status must be
 * truthful on Home" requirement. Only renders when we have real
 * synced data, so it never lies.
 */
function AppleHealthHeadline() {
  const days = useHealthStore((s) => s.days);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const historyWindowDays = useHealthStore((s) => s.historyWindowDays);
  const lastBackfillAt = useHealthStore((s) => s.lastBackfillAt);
  const isIos = Platform.OS === 'ios';
  if (!lastSyncAt || days.length === 0) return null;
  const label = isIos ? 'Apple Health' : 'Health Connect';
  const window = historyWindowDays != null ? `${historyWindowDays}d` : '—';
  const ageMin = Math.max(0, Math.round((Date.now() - new Date(lastSyncAt).getTime()) / 60_000));
  const recency = ageMin < 1 ? 'synced just now' : ageMin < 60 ? `synced ${ageMin}m ago` : ageMin < 1440 ? `synced ${Math.round(ageMin / 60)}h ago` : `synced ${Math.round(ageMin / 1440)}d ago`;
  const backfillNote = lastBackfillAt ? ' · backfilled' : '';
  return (
    <View style={styles.fuelHeadline}>
      <Text style={styles.fuelLabel}>{label}</Text>
      <Text style={styles.fuelValue}>
        {days.length} days · {window} window · {recency}{backfillNote}
      </Text>
    </View>
  );
}

function WhoopHeadline() {
  // Home no longer surfaces a standalone WHOOP recovery/seed
  // headline. WHOOP remains an optional reference/calibration source
  // that can be viewed under the Health → WHOOP card. Custom
  // readiness on the Home strip is the visible product score now.
  // Keeping this component as an explicit no-op preserves call sites
  // without prop-drilling churn.
  // Still trigger the background fetch so calibration data arrives
  // and feeds AppAthleteState — silent fetch only.
  const status = useWhoopStore((s) => s.status);
  const fetchToday = useWhoopStore((s) => s.fetchToday);
  useEffect(() => {
    if (status === 'idle') fetchToday();
  }, [status, fetchToday]);
  return null;
}

const INTENSITY_LABEL: Record<string, string> = {
  light: 'Light',
  moderate: 'Moderate',
  hard: 'Hard',
};

const MODE_LABEL: Record<string, string> = {
  grappling: 'Grappling',
  hiit: 'HIIT',
  zone2: 'Zone 2',
  weights: 'Weights',
  rest: 'Rest',
};

/**
 * Today's Coach — unified daily guidance card that prefers WHOOP recovery
 * over HealthKit when present, falls back to insights when WHOOP is absent,
 * and shows today's plan + intensity recommendation + explainable reasons.
 */
/**
 * Banner shown above the Today's Coach card when the user has a
 * previously-started "Ask ChatGPT" case that hasn't been captured yet.
 * Asks the three-button question "How did that go?" and completes the
 * case with the chosen usefulness verdict. Dismiss = drop the draft
 * without saving (useful if the user never actually asked ChatGPT).
 */
function PendingFollowupBanner() {
  const pending = useCoachingCasesStore((s) => s.pending);
  const completePending = useCoachingCasesStore((s) => s.completePending);
  const dismissPending = useCoachingCasesStore((s) => s.dismissPending);
  // Optional "What did ChatGPT say?" free-text captured alongside the
  // usefulness verdict. Stored locally until a verdict button is tapped,
  // then passed through to completePending(outcomeSummary). Cleared
  // automatically when the banner unmounts (pending goes null).
  const [outcomeNotes, setOutcomeNotes] = useState('');
  // Optional "Did you follow it?" tri-state — null = not answered,
  // true = followed the advice, false = did not follow. Threaded
  // through to completePending() as the third argument so the case
  // record carries both the verdict and the compliance signal.
  // Compliance-without-verdict is the most interesting learning
  // signal: "I did what it said but it didn't help" vs "I ignored
  // it and was fine anyway" are different failure modes.
  const [followed, setFollowed] = useState<boolean | null>(null);
  if (!pending) return null;

  const handleComplete = (
    usefulness: 'helped' | 'neutral' | 'unhelpful',
  ) => {
    const trimmed = outcomeNotes.trim();
    completePending(
      usefulness,
      trimmed || undefined,
      followed ?? undefined,
    );
    setOutcomeNotes('');
    setFollowed(null);
  };
  const handleDismiss = () => {
    setOutcomeNotes('');
    setFollowed(null);
    dismissPending();
  };

  return (
    <View style={styles.followupBanner}>
      <Text style={styles.followupTitle}>
        You used AI Coach earlier — how did it go?
      </Text>
      <TextInput
        style={styles.followupNotesInput}
        value={outcomeNotes}
        onChangeText={setOutcomeNotes}
        placeholder="What did AI Coach suggest? (optional — paste the key recommendation)"
        placeholderTextColor="#666"
        multiline
        textAlignVertical="top"
        maxLength={2000}
      />
      {/* Did you follow it? — tri-state toggle. Independent of the
          usefulness verdict so we can distinguish "followed and it
          helped" from "ignored and was fine anyway". Optional — the
          user can leave it unset and still log a verdict. */}
      <View style={styles.followupFollowedRow}>
        <Text style={styles.followupFollowedLabel}>Did you follow it?</Text>
        <Pressable
          onPress={() => setFollowed(followed === true ? null : true)}
          style={[
            styles.followupToggleBtn,
            followed === true && styles.followupToggleBtnYesOn,
          ]}>
          <Text
            style={[
              styles.followupToggleBtnText,
              followed === true && styles.followupToggleBtnYesOnText,
            ]}>
            Yes
          </Text>
        </Pressable>
        <Pressable
          onPress={() => setFollowed(followed === false ? null : false)}
          style={[
            styles.followupToggleBtn,
            followed === false && styles.followupToggleBtnNoOn,
          ]}>
          <Text
            style={[
              styles.followupToggleBtnText,
              followed === false && styles.followupToggleBtnNoOnText,
            ]}>
            No
          </Text>
        </Pressable>
      </View>
      <View style={styles.followupActions}>
        <Pressable
          style={styles.followupBtnHelp}
          onPress={() => handleComplete('helped')}>
          <Text style={styles.followupBtnHelpText}>Helped</Text>
        </Pressable>
        <Pressable
          style={styles.followupBtnNeutral}
          onPress={() => handleComplete('neutral')}>
          <Text style={styles.followupBtnNeutralText}>Neutral</Text>
        </Pressable>
        <Pressable
          style={styles.followupBtnNo}
          onPress={() => handleComplete('unhelpful')}>
          <Text style={styles.followupBtnNoText}>Not useful</Text>
        </Pressable>
        <Pressable
          style={styles.followupBtnDismiss}
          onPress={handleDismiss}>
          <Text style={styles.followupBtnDismissText}>Dismiss</Text>
        </Pressable>
      </View>
    </View>
  );
}

function TodayCoachCard() {
  const router = useRouter();
  const whoopDay = useWhoopStore((s) => s.day);
  const whoopStatus = useWhoopStore((s) => s.status);
  const fetchWhoop = useWhoopStore((s) => s.fetchToday);
  const coaching = useHealthStore((s) => s.coaching);
  const insights = useHealthStore((s) => s.insights);
  const sessions = useTrainingStore((s) => s.sessions);
  const preferences = usePreferencesStore((s) => s.preferences);
  const schedule = preferences.schedule;
  const progressMap = useReferenceProgressStore((s) => s.progress);
  const updatedAtMap = useReferenceProgressStore((s) => s.updatedAt);
  const nutritionToday = useNutritionStore((s) => s.today);
  const nutritionTargets = useNutritionStore((s) => s.targets);
  const nutritionHistory = useNutritionStore((s) => s.historyDays);

  useEffect(() => {
    if (whoopStatus === 'idle') fetchWhoop();
  }, [whoopStatus, fetchWhoop]);

  const briefInputs = useMemo(() => {
    const todayIsoDate = new Date().toISOString().slice(0, 10);
    const todayPlan = getTodayPlan(schedule);
    return {
      whoopDay,
      insights,
      todayPlan,
      recentSessions: sessions,
      todayIsoDate,
      nutritionToday,
      nutritionTargets,
      nutritionHistory,
    };
  }, [
    whoopDay,
    insights,
    sessions,
    schedule,
    nutritionToday,
    nutritionTargets,
    nutritionHistory,
  ]);

  const brief = useMemo<DailyCoachingBrief>(() => {
    return buildDailyCoachingBrief(briefInputs);
  }, [briefInputs]);

  // Compact continuity cue from the most recent HIIT session within
  // the last 3 days. Priority: retrospective PR beat → vs-last delta
  // → interpretive coaching note. Null when nothing meaningful exists
  // (the UI branch then renders nothing). Computed from sessions[]
  // directly so it never races with the ephemeral save/timer handoff
  // state that lives in Train.
  const lastHIITHomeNote = useMemo(() => {
    return buildLastHIITHomeNote({
      sessions,
      todayIsoDate: briefInputs.todayIsoDate,
      whoopRecovery: whoopDay?.recovery_score ?? undefined,
      suggestedIntensity: brief.suggested_intensity,
      maxAgeDays: 3,
    });
  }, [sessions, briefInputs.todayIsoDate, whoopDay, brief.suggested_intensity]);

  const nextTechnique = useMemo(() => {
    return buildNextTechniqueRecommendation({
      progressMap,
      updatedAtMap,
      goal: preferences.goal,
    });
  }, [progressMap, updatedAtMap, preferences.goal]);
  const color = READINESS_COLORS[brief.readiness];
  const platformHealthLabel = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
  const sourceLabel =
    brief.primary_source === 'whoop'
      ? ATHLETE_CAPABILITY_COPY.whoopSourceLabel
      : brief.primary_source === 'insights'
        ? platformHealthLabel
        : 'no source';

  return (
    <View style={styles.card}>
      <View style={styles.coachHeaderRow}>
        <Text style={styles.cardTitle}>Today's Coach</Text>
        <Text style={styles.coachSourceLabel}>from {sourceLabel}</Text>
      </View>

      <View style={styles.readinessRow}>
        <View style={[styles.readinessDot, { backgroundColor: color }]} />
        <Text style={[styles.readinessLabel, { color }]}>{brief.headline}</Text>
      </View>

      {/* Only badge as "missing native readiness" when we literally
          don't have a recovery_score yet. When WHOOP is connected and
          has scored the cycle, this badge is stale and misleading. */}
      {brief.primary_source === 'whoop' && whoopDay?.recovery_score == null && (
        <AthleteCapabilitySummary mode="missing_whoop_native" showNote={false} />
      )}

      {/* Plan hint — real schedule for today (with times if set) */}
      {brief.plan_hint ? (
        <View style={styles.coachPlanRow}>
          <Text style={styles.coachPlanLabel}>Plan</Text>
          <Text style={styles.coachPlanValue}>{brief.plan_hint}</Text>
        </View>
      ) : (
        <View style={styles.coachPlanRow}>
          <Text style={styles.coachPlanLabel}>Plan</Text>
          <Text style={styles.coachPlanValueMuted}>
            Rest day — no sessions scheduled
          </Text>
        </View>
      )}

      {/* Suggested intensity + modes */}
      <View style={styles.coachSuggestionRow}>
        <View style={styles.coachChip}>
          <Text style={styles.coachChipLabel}>Intensity</Text>
          <Text style={styles.coachChipValue}>
            {INTENSITY_LABEL[brief.suggested_intensity]}
          </Text>
        </View>
        {brief.suggested_modes.length > 0 && (
          <View style={styles.coachChip}>
            <Text style={styles.coachChipLabel}>Good for</Text>
            <Text style={styles.coachChipValue}>
              {brief.suggested_modes.slice(0, 3).map((m) => MODE_LABEL[m]).join(' · ')}
            </Text>
          </View>
        )}
      </View>

      {/* Load interpretation — strain as a coaching word, not /21 */}
      {brief.load_band !== 'unknown' && (
        <Text style={styles.coachLoadLine}>{brief.load_line}</Text>
      )}

      {/* Reasons — explainability */}
      {brief.reasons.length > 0 && (
        <View style={styles.coachReasons}>
          {brief.reasons.map((r, i) => (
            <Text key={i} style={styles.coachReasonItem}>
              • {r}
            </Text>
          ))}
        </View>
      )}

      {nextTechnique && (
        <View style={styles.nextTechniqueBlock}>
          <Text style={styles.nextTechniqueLabel}>Work on this next</Text>
          <Text style={styles.nextTechniqueName}>{nextTechnique.technique}</Text>
          <Text style={styles.nextTechniqueMeta}>
            {nextTechnique.position} · {nextTechnique.role} · {nextTechnique.heading}
          </Text>
          <Text style={styles.nextTechniqueReason}>{nextTechnique.reason}</Text>
          <Pressable
            style={styles.nextTechniqueBtn}
            onPress={() =>
              router.navigate({
                pathname: '/reference',
                params: {
                  focus: nextTechnique.position,
                  focusRole: nextTechnique.role,
                  focusHeading: nextTechnique.heading,
                  focusTechnique: nextTechnique.technique,
                  focusReason: nextTechnique.reason,
                  focusSource: 'coach',
                  focusNonce: `${Date.now()}`,
                },
              })
            }>
            <Text style={styles.nextTechniqueBtnText}>Open Reference →</Text>
          </Pressable>
        </View>
      )}

      {/* Last HIIT continuity cue — PR beat, vs-last delta, or
          machine-metrics-aware coaching note from the most recent
          HIIT session within the last 3 days. Null-safe: the whole
          block is hidden when no meaningful signal exists, so
          non-HIIT users and HIIT users on rest cycles see Home
          identical to before. Valence-aware styling picks up on
          the 🏆 PR beat and the +/- delta prefixes. */}
      {lastHIITHomeNote && (
        <View style={styles.lastHIITNoteBlock}>
          <Text style={styles.lastHIITNoteLabel}>From your last HIIT</Text>
          <Text
            style={[
              styles.lastHIITNoteText,
              lastHIITHomeNote.startsWith('🏆') && styles.lastHIITNotePr,
              lastHIITHomeNote.startsWith('+') && styles.lastHIITNoteUp,
              lastHIITHomeNote.startsWith('-') && styles.lastHIITNoteDown,
              lastHIITHomeNote === 'matched last' && styles.lastHIITNoteMatched,
            ]}>
            {lastHIITHomeNote}
          </Text>
        </View>
      )}

      {/* WHOOP-specific missing-workout hint hidden — WHOOP is now
          an optional background reference, not the visible product
          source. Workout missingness is surfaced via Custom readiness
          confidence on the Home strip. */}

      {/* Empty-state fallback — sync Apple Health is the primary
          live source; WHOOP only matters when calibration is desired. */}
      {brief.primary_source === 'none' && (
        <Text style={styles.cardBody}>
          Sync {platformHealthLabel} or log a session to get personalized guidance. WHOOP reference is optional.
        </Text>
      )}
    </View>
  );
}

function ProgressCard() {
  const { drilling, learned, loading, error } = useProgress();

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Progress</Text>
      {loading ? (
        <ActivityIndicator size="small" color="#d4e157" />
      ) : error ? (
        <Text style={styles.cardError}>{error}</Text>
      ) : (
        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{drilling}</Text>
            <Text style={styles.statLabel}>Drilling</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{learned}</Text>
            <Text style={styles.statLabel}>Learned</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{drilling + learned}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
        </View>
      )}
    </View>
  );
}

function RecentActivityCard() {
  const aiContext = useHealthStore((s) => s.aiContext);

  if (!aiContext || aiContext.recent_workouts.length === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recent Activity</Text>
        <Text style={styles.cardBody}>
          Log a session from the Train tab or sync Apple Health / Health Connect. Saved sessions show up here instantly.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recent Activity</Text>
      {aiContext.recent_workouts.slice(0, 5).map((w, i) => (
        <View key={i} style={styles.activityRow}>
          <View>
            <Text style={styles.activityName}>
              {w.name}
              {w.is_grappling ? ' 🥋' : ''}
            </Text>
            <Text style={styles.activityDate}>{w.date}</Text>
          </View>
          <Text style={styles.activityMeta}>
            {w.duration_min}min
            {w.calories ? ` · ${Math.round(w.calories)}cal` : ''}
          </Text>
        </View>
      ))}
    </View>
  );
}

function TrainingContextCard() {
  const coaching = useHealthStore((s) => s.coaching);
  const insights = useHealthStore((s) => s.insights);
  const sessions = useTrainingStore((s) => s.sessions);
  const todayStr = new Date().toISOString().slice(0, 10);
  const todaySessions = sessions.filter((s) => s.date === todayStr);

  if (!coaching && todaySessions.length === 0) return null;

  const hasCoaching = coaching && coaching.readiness.level !== 'grey';

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Context</Text>

      {/* Plan status */}
      {hasCoaching && coaching.plan && coaching.plan.status !== 'no_plan' && (
        <Text style={styles.cardBody}>{coaching.plan.summary}</Text>
      )}

      {/* Load + grappling */}
      {hasCoaching && (
        <>
          <Text style={styles.cardBody}>{coaching.training_load.summary}</Text>
          {coaching.grappling.suggestion ? (
            <Text style={styles.suggestion}>{coaching.grappling.suggestion}</Text>
          ) : null}
        </>
      )}

      {/* Why this recommendation */}
      {insights && insights.recommendation.reasons.length > 0 && (
        <View style={styles.whySection}>
          <Text style={styles.whyLabel}>Why</Text>
          {insights.recommendation.reasons.slice(0, 3).map((r, i) => (
            <Text key={i} style={styles.whyItem}>• {r}</Text>
          ))}
        </View>
      )}

      {/* Today's sessions */}
      {todaySessions.length > 0 && (
        <View style={styles.todayBadge}>
          <Text style={styles.todayBadgeText}>
            Today: {todaySessions.map((s) => SESSION_TYPE_LABELS[s.type]).join(', ')}
          </Text>
        </View>
      )}
    </View>
  );
}

export default function HomeScreen() {
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const isMember = status === 'member';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>Lauburu Grappling Map</Text>
        <Text style={styles.subtitle}>
          {isMember ? 'Your training companion' : 'Your training companion'}
        </Text>
      </View>

      {/* First-run tour is now a global full-screen modal in _layout.tsx */}

      {!isMember && <GuestBanner />}

      {/* Readiness — primary Home surface. App-owned readiness band
          + sources. Promoted above coach/insights/training-context
          so the visible product score is the first thing users see
          after the header on every Home open. */}
      {isMember && <AthleteStateStrip />}

      {/* First-run backlog analysis permission + summary card. Renders
          only when signed in; hides itself when status is 'skipped'
          or when there's nothing to show. The card handles its own
          data lifecycle via useBacklogAnalysisStore. */}
      {isMember && <BacklogAnalysisCard />}

      {/* Pending coaching-case follow-up — only appears when the user
          has an un-captured "Ask ChatGPT" draft. */}
      {isMember && <PendingFollowupBanner />}

      {/* Today's Coach — unified daily guidance (plan + insights) */}
      {isMember && <TodayCoachCard />}

      {/* Tiny backend-fed WHOOP metrics chip — shown only when data is ready */}
      {isMember && <WhoopHeadline />}

      {/* Apple Health / Health Connect at-a-glance chip — shown only
          when we have real synced data, so it never lies. */}
      {isMember && <AppleHealthHeadline />}

      {/* Tiny nutrition chip — shown only when the user has logged fuel today */}
      {isMember && <NutritionHeadline />}

      {isMember && <TrainingContextCard />}

      {isMember && <ProgressCard />}

      {isMember && <RecentActivityCard />}
      {/* Coaching history — only shown when signed in since cases are
          per-user and secureStorage-backed. Visible even when the list
          is empty so the user can discover the feature. */}
      {isMember && <CoachingHistoryEntryCard />}

      {/* Suggested metrics — optional blind-spot prompts. Self-gated:
          only renders when at least one suggestion is justified. */}
      {isMember && <SuggestedMetricsCard />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16 },
  header: { marginBottom: 8 },
  title: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 16, opacity: 0.6, marginTop: 4 },
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  cardBody: { fontSize: 14, opacity: 0.7, lineHeight: 20 },
  cardError: { fontSize: 14, color: '#ff6b6b' },

  // Readiness
  readinessRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  readinessDot: { width: 12, height: 12, borderRadius: 6 },
  readinessLabel: { fontSize: 20, fontWeight: '700' },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 4,
  },
  metricItem: { alignItems: 'center', gap: 2 },
  metricValue: { fontSize: 16, fontWeight: '700', color: '#d4e157' },
  metricLabel: { fontSize: 10, opacity: 0.5 },
  signalsRow: { gap: 2, marginTop: 4 },
  signalPositive: { fontSize: 12, color: '#4ade80', opacity: 0.8 },
  signalConcern: { fontSize: 12, color: '#ff8a80', opacity: 0.8 },
  syncNote: { fontSize: 10, opacity: 0.3, marginTop: 4 },

  // Progress
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 8,
  },
  stat: { alignItems: 'center', gap: 4 },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#d4e157' },
  statLabel: { fontSize: 13, opacity: 0.6 },

  // Activity
  activityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  activityName: { fontSize: 14 },
  activityDate: { fontSize: 11, opacity: 0.4 },
  activityMeta: { fontSize: 12, opacity: 0.5 },

  // Training context
  todayBadge: {
    backgroundColor: 'rgba(212,225,87,0.1)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  todayBadgeText: { fontSize: 12, color: '#d4e157', fontWeight: '600' },
  suggestion: { fontSize: 13, color: '#a8b84a', opacity: 0.9, lineHeight: 18 },
  whySection: { gap: 2, marginTop: 4, paddingTop: 6, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)' },
  whyLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5 },
  whyItem: { fontSize: 12, opacity: 0.6, lineHeight: 16 },

  // Today's Coach
  coachHeaderRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  coachSourceLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  coachPlanRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingTop: 6,
    paddingBottom: 2,
  },
  coachPlanLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    width: 44,
    paddingTop: 2,
  },
  coachPlanValue: { fontSize: 13, flex: 1, lineHeight: 18 },
  coachPlanValueMuted: { fontSize: 13, flex: 1, lineHeight: 18, opacity: 0.4 },
  coachSuggestionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 4,
  },
  coachChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(212,225,87,0.08)',
    gap: 2,
  },
  coachChipLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  coachChipValue: { fontSize: 13, color: '#d4e157', fontWeight: '600' },
  coachReasons: { gap: 2, marginTop: 4 },
  coachReasonItem: { fontSize: 11, opacity: 0.5, lineHeight: 15 },
  nextTechniqueBlock: {
    marginTop: 8,
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.16)',
    gap: 4,
  },
  nextTechniqueLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  nextTechniqueName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#e6ec9a',
  },
  nextTechniqueMeta: {
    fontSize: 12,
    opacity: 0.62,
    lineHeight: 17,
  },
  nextTechniqueReason: {
    fontSize: 12,
    lineHeight: 17,
    opacity: 0.78,
  },
  nextTechniqueBtn: {
    alignSelf: 'flex-start',
    marginTop: 2,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  nextTechniqueBtnText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#d4e157',
  },
  coachMissingHint: {
    fontSize: 11,
    opacity: 0.5,
    marginTop: 4,
    fontStyle: 'italic',
  },
  coachLoadLine: {
    fontSize: 12,
    opacity: 0.6,
    marginTop: 6,
    lineHeight: 17,
  },

  // Last HIIT continuity cue block
  lastHIITNoteBlock: {
    marginTop: 8,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(212,225,87,0.4)',
    gap: 2,
  },
  lastHIITNoteLabel: {
    fontSize: 10,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  lastHIITNoteText: {
    fontSize: 12,
    color: '#c4cdd8',
    lineHeight: 17,
    fontWeight: '500',
  },
  lastHIITNotePr: {
    color: '#ffd866',
    fontWeight: '700',
  },
  lastHIITNoteUp: { color: '#4ade80' },
  lastHIITNoteDown: { color: '#ff8a80' },
  lastHIITNoteMatched: { color: '#d4e157' },

  // Ask ChatGPT fallback
  askAiBlock: { marginTop: 10, gap: 8 },
  askAiQuestionInput: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 12,
    color: '#e6ecf3',
    backgroundColor: 'rgba(255,255,255,0.04)',
    minHeight: 48,
    lineHeight: 17,
  },
  askAiBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.3)',
    backgroundColor: 'rgba(212,225,87,0.04)',
    alignSelf: 'flex-start',
  },
  askAiBtnSending: {
    opacity: 0.5,
    borderColor: 'rgba(212,225,87,0.15)',
  },
  askAiBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  evidenceAiBlock: {
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(123,196,255,0.22)',
    backgroundColor: 'rgba(123,196,255,0.05)',
    gap: 8,
  },
  evidenceAiTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#b8dcff',
  },
  evidenceAiBody: {
    fontSize: 12,
    lineHeight: 17,
    color: '#d6e5f5',
    opacity: 0.86,
  },
  evidenceAiChipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  evidenceAiModeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  evidenceAiChip: {
    paddingVertical: 5,
    paddingHorizontal: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.14)',
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  evidenceAiChipActive: {
    borderColor: 'rgba(123,196,255,0.5)',
    backgroundColor: 'rgba(123,196,255,0.14)',
  },
  evidenceAiChipText: {
    fontSize: 11,
    color: '#b8c4d0',
    fontWeight: '600',
  },
  evidenceAiChipTextActive: {
    color: '#b8dcff',
  },
  evidenceAiUsingLine: {
    fontSize: 11,
    color: '#9bb7d1',
    opacity: 0.9,
  },
  evidenceAiPolicyLine: {
    fontSize: 11,
    lineHeight: 16,
    color: '#cfdcf0',
    opacity: 0.88,
  },
  evidenceAiAllowanceCard: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 3,
  },
  evidenceAiAllowanceTitle: {
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: '#8fb3d1',
    opacity: 0.8,
  },
  evidenceAiAllowanceState: {
    fontSize: 12,
    fontWeight: '700',
    color: '#e6ecf3',
  },
  evidenceAiAllowanceBody: {
    fontSize: 11,
    lineHeight: 16,
    color: '#bfd0e3',
    opacity: 0.88,
  },
  evidenceAiAllowanceUpgrade: {
    fontSize: 11,
    lineHeight: 16,
    color: '#d4e157',
    opacity: 0.95,
  },
  evidenceAiFeatureStateCard: {
    paddingVertical: 2,
    gap: 2,
  },
  evidenceAiFeatureStateLine: {
    fontSize: 11,
    lineHeight: 16,
    color: '#d6e5f5',
    opacity: 0.88,
  },
  evidenceAiChoiceCard: {
    paddingTop: 2,
    gap: 6,
  },
  evidenceAiChoiceTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#e6ecf3',
  },
  evidenceAiChoiceRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  evidenceAiChoiceBtn: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.22)',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  evidenceAiChoiceBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#d4e157',
  },
  evidenceAiChoiceNote: {
    fontSize: 11,
    lineHeight: 16,
    color: '#cfdcf0',
    opacity: 0.84,
  },

  // Pending follow-up banner
  followupBanner: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 10,
  },
  followupTitle: { fontSize: 13, color: '#e6ecf3', fontWeight: '600' },
  followupNotesInput: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    padding: 10,
    fontSize: 12,
    color: '#e6ecf3',
    backgroundColor: 'rgba(255,255,255,0.04)',
    minHeight: 60,
    lineHeight: 17,
  },
  followupActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  followupBtnHelp: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(74,222,128,0.15)',
    borderWidth: 1,
    borderColor: '#4ade80',
  },
  followupBtnHelpText: { color: '#4ade80', fontSize: 12, fontWeight: '600' },
  followupBtnNeutral: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.08)',
  },
  followupBtnNeutralText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  followupBtnNo: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ff8a80',
    backgroundColor: 'rgba(255,138,128,0.08)',
  },
  followupBtnNoText: { color: '#ff8a80', fontSize: 12, fontWeight: '600' },
  followupBtnDismiss: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#444',
  },
  followupBtnDismissText: { color: '#888', fontSize: 11 },
  followupFollowedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  followupFollowedLabel: {
    fontSize: 11,
    color: '#b0b8c3',
    opacity: 0.7,
  },
  followupToggleBtn: {
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#444',
  },
  followupToggleBtnText: { color: '#888', fontSize: 11, fontWeight: '600' },
  followupToggleBtnYesOn: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.15)',
  },
  followupToggleBtnYesOnText: { color: '#4ade80' },
  followupToggleBtnNoOn: {
    borderColor: '#ff8a80',
    backgroundColor: 'rgba(255,138,128,0.12)',
  },
  followupToggleBtnNoOnText: { color: '#ff8a80' },

  // Compact linked-entry card
  referenceCard: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.05)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 6,
  },
  referenceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  referenceChevron: { fontSize: 20, color: '#d4e157', opacity: 0.6 },

  // WHOOP headline
  whoopHeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  whoopDot: { width: 10, height: 10, borderRadius: 5 },
  whoopLabel: { fontSize: 14, fontWeight: '600' },
  whoopMeta: { fontSize: 12, opacity: 0.5, marginLeft: 'auto' },

  // Nutrition headline
  fuelHeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  fuelLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  fuelValue: { fontSize: 13, color: '#d4e157', fontWeight: '600', marginLeft: 'auto' },
});
