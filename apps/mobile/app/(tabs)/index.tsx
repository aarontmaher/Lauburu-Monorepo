import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, ScrollView, ActivityIndicator, Pressable, Share, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';
import { useHealthStore } from '../../src/store/health-store';
import { useTrainingStore } from '../../src/store/training-store';
import { useWhoopStore } from '../../src/store/whoop-store';
import { useNutritionStore } from '../../src/store/nutrition-store';
import { usePreferencesStore } from '../../src/store/preferences-store';
import { useCoachingCasesStore } from '../../src/store/coaching-cases-store';
import { useProgress } from '../../src/hooks/useProgress';
import {
  REFERENCE_TOTAL_POSITIONS,
  REFERENCE_BUILT_OUT_COUNT,
  REFERENCE_SECTIONS,
} from '../../src/data/reference-seed';
import type { ReadinessLevel, DailyCoachingBrief } from '@lauburu/shared';
import {
  SESSION_TYPE_LABELS,
  buildDailyCoachingBrief,
  buildCoachingPromptPacket,
  getTodayPlan,
} from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function GuestBanner() {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Welcome to Lauburu</Text>
      <Text style={styles.cardBody}>
        Sign in on Settings to save your training data and get personalized coaching.
      </Text>
    </View>
  );
}

function ReferenceEntryCard() {
  const router = useRouter();
  return (
    <Pressable
      style={styles.referenceCard}
      onPress={() => router.push('/reference')}>
      <View style={styles.referenceHeader}>
        <Text style={styles.cardTitle}>Reference</Text>
        <Text style={styles.referenceChevron}>→</Text>
      </View>
      <Text style={styles.cardBody}>
        Browse the canonical Grappling Map structure: {REFERENCE_SECTIONS.length} sections,{' '}
        {REFERENCE_TOTAL_POSITIONS} positions, {REFERENCE_BUILT_OUT_COUNT} built out.
      </Text>
    </Pressable>
  );
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
          ? 'No cases yet. Ask ChatGPT from the coach card above to start one.'
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
  // When targets are set, surface the "X / Y" progress form so the
  // Home chip mirrors the percent-of-target badges on the Health tab's
  // NutritionCard. Falls back to the plain value when no target exists.
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
  return (
    <View style={styles.fuelHeadline}>
      <Text style={styles.fuelLabel}>Today's fuel</Text>
      <Text style={styles.fuelValue}>
        {calDisplay}
        {proteinDisplay}
      </Text>
    </View>
  );
}

function WhoopHeadline() {
  const status = useWhoopStore((s) => s.status);
  const day = useWhoopStore((s) => s.day);
  const fetchToday = useWhoopStore((s) => s.fetchToday);

  useEffect(() => {
    if (status === 'idle') fetchToday();
  }, [status, fetchToday]);

  if (status !== 'ready' || !day || day.recovery_score == null) return null;

  const score = day.recovery_score;
  const color =
    score >= 67 ? '#4ade80' : score >= 34 ? '#d4e157' : '#ff6b6b';
  const label = score >= 67 ? 'Recovered' : score >= 34 ? 'Moderate' : 'Low';

  return (
    <View style={styles.whoopHeadline}>
      <View style={[styles.whoopDot, { backgroundColor: color }]} />
      <Text style={[styles.whoopLabel, { color }]}>
        WHOOP {score}% · {label}
      </Text>
      {day.daily_strain != null && (
        <Text style={styles.whoopMeta}>
          strain {day.daily_strain.toFixed(1)}
        </Text>
      )}
    </View>
  );
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
        You asked ChatGPT earlier — how did it go?
      </Text>
      <TextInput
        style={styles.followupNotesInput}
        value={outcomeNotes}
        onChangeText={setOutcomeNotes}
        placeholder="What did ChatGPT say? (optional — paste the key recommendation)"
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
  const whoopDay = useWhoopStore((s) => s.day);
  const whoopStatus = useWhoopStore((s) => s.status);
  const fetchWhoop = useWhoopStore((s) => s.fetchToday);
  const insights = useHealthStore((s) => s.insights);
  const sessions = useTrainingStore((s) => s.sessions);
  const schedule = usePreferencesStore((s) => s.preferences.schedule);
  const nutritionToday = useNutritionStore((s) => s.today);
  const nutritionTargets = useNutritionStore((s) => s.targets);
  const nutritionHistory = useNutritionStore((s) => s.historyDays);
  const startPendingCase = useCoachingCasesStore((s) => s.startPending);
  // Optional user-typed question carried into the prompt packet's
  // "My question" section. Empty = default fallback "Given the context
  // above, what should I actually do today?" inside the packet builder.
  const [userQuestion, setUserQuestion] = useState('');

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

  /**
   * Ask ChatGPT fallback — builds a structured prompt packet from the
   * same inputs the coach card is already reading, opens the native
   * share sheet so the user can pick ChatGPT/Claude/any installed app
   * or copy to clipboard, and saves a pending draft case via the
   * coaching-cases-store so the Home banner can prompt for outcome
   * capture when the user returns.
   *
   * Zero new deps, zero native modules — Share.share is core RN.
   * Zero paid API calls. The handoff is honest: the app prepares the
   * context, the user + their chosen AI do the actual thinking, the
   * outcome comes back via the follow-up banner.
   */
  const handleAskChatGPT = async () => {
    // Thread the user's typed question through the shared packet
    // builder via its optional `userQuestion` input. Empty string
    // means the builder falls back to its default generic prompt
    // ("Given the context above, what should I actually do today?")
    // so the feature is strictly additive — existing "just tap the
    // button" flow continues to work.
    const trimmedQuestion = userQuestion.trim();
    const { text, context } = buildCoachingPromptPacket({
      ...briefInputs,
      userQuestion: trimmedQuestion || null,
    });
    try {
      await Share.share({
        message: text,
        title: 'Lauburu coaching context',
      });
      // Regardless of which share target the user picked, save the
      // draft so the follow-up banner appears next time.
      startPendingCase({
        context,
        prompt_packet: text,
        source: 'external_chatgpt',
      });
      // Clear the question once it's been captured into the case
      // so the field is empty for the next ask.
      setUserQuestion('');
    } catch {
      // Share dismissed or failed — don't save a draft, and don't
      // clear the question so the user can retry without retyping.
    }
  };

  const color = READINESS_COLORS[brief.readiness];
  const sourceLabel =
    brief.primary_source === 'whoop'
      ? 'WHOOP'
      : brief.primary_source === 'insights'
        ? 'Apple Health'
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

      {/* Honest WHOOP missing-workout hint */}
      {brief.whoop_workouts_missing_today && (
        <Text style={styles.coachMissingHint}>
          Today's WHOOP workout hasn't synced yet — recovery and sleep are logged.
        </Text>
      )}

      {/* Empty-state fallback */}
      {brief.primary_source === 'none' && (
        <Text style={styles.cardBody}>
          Connect WHOOP on the backend or sync Apple Health to get personalized
          guidance.
        </Text>
      )}

      {/* Ask ChatGPT fallback — optional user-question textarea threaded
          through the shared packet builder + the button that opens the
          native share sheet. Intentionally positioned at the bottom of
          the card so it's available but never crowds out the app's own
          guidance. The textarea is optional; leaving it blank falls
          back to the shared builder's default generic prompt. */}
      <View style={styles.askAiBlock}>
        <TextInput
          style={styles.askAiQuestionInput}
          value={userQuestion}
          onChangeText={setUserQuestion}
          placeholder="What do you want to ask? (optional)"
          placeholderTextColor="#666"
          multiline
          textAlignVertical="top"
          maxLength={500}
        />
        <Pressable style={styles.askAiBtn} onPress={handleAskChatGPT}>
          <Text style={styles.askAiBtnText}>Ask ChatGPT for a second opinion →</Text>
        </Pressable>
      </View>
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
          Recent workouts will appear here after syncing health data.
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
          {isMember ? `Signed in as ${user?.email}` : 'Your training companion'}
        </Text>
      </View>

      {!isMember && <GuestBanner />}

      {/* Pending coaching-case follow-up — only appears when the user
          has an un-captured "Ask ChatGPT" draft. */}
      {isMember && <PendingFollowupBanner />}

      {/* Today's Coach — unified daily guidance (WHOOP + plan + insights) */}
      {isMember && <TodayCoachCard />}

      {/* Tiny backend-fed WHOOP metrics chip — shown only when data is ready */}
      {isMember && <WhoopHeadline />}

      {/* Tiny nutrition chip — shown only when the user has logged fuel today */}
      {isMember && <NutritionHeadline />}

      {isMember && <TrainingContextCard />}

      {isMember && <ProgressCard />}

      {isMember && <RecentActivityCard />}

      {/* Reference — always visible entry point, even for guests */}
      <ReferenceEntryCard />

      {/* Coaching history — only shown when signed in since cases are
          per-user and secureStorage-backed. Visible even when the list
          is empty so the user can discover the feature. */}
      {isMember && <CoachingHistoryEntryCard />}
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
  askAiBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },

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

  // Reference entry card
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
