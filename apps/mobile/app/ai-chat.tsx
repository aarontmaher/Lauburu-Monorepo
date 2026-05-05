/**
 * AI Chat modal — global coach/assistant surface.
 * Opens from the floating AI FAB on any screen.
 *
 * Display context: fetched from backend `/ai-context` (one call).
 * Prompt building: still uses local stores for detailed data
 * (sessions, preferences, progress) since Share.share() needs
 * the full packet and the backend doesn't serve raw prompt inputs.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  StyleSheet,
  TextInput,
  Pressable,
  Share,
  KeyboardAvoidingView,
  Keyboard,
  Platform,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../src/store/auth-store';
import { useHealthStore } from '../src/store/health-store';
import { useTrainingStore } from '../src/store/training-store';
import { usePreferencesStore } from '../src/store/preferences-store';
import { useWhoopStore } from '../src/store/whoop-store';
import { useNutritionStore } from '../src/store/nutrition-store';
import { useCoachingCasesStore } from '../src/store/coaching-cases-store';
import { useTierStore } from '../src/store/tier-store';
import {
  buildEvidenceAwareAiRequestPacket,
  type EvidenceAwareTopic,
} from '../src/services/evidence-aware-ai';
import { buildAppAthleteState } from '../src/services/app-athlete-state';
import { AthleteStateStrip } from '../src/components/AthleteStateStrip';
import {
  buildCoachingPromptPacket,
  buildDailyCoachingBrief,
  getTodayPlan,
  suggestHIITProtocol,
} from '@lauburu/shared';
import {
  buildAthleteMemoryClientConfig,
  fetchAiContext,
  fetchCoachAnswer,
  type AthleteAiContextResponse,
  type CoachAnswerResponse,
} from '../src/services/athlete-memory-client';
import {
  readStoredJson,
  writeStoredJson,
} from '../src/store/secure-storage';

type CoachAnswerCard = {
  id: string;
  question: string;
  domain: CoachAnswerResponse['domain'];
  questionClass: string | null;
  short: string;
  why: string;
  nextStep: string;
  missingnessNote: string | null;
  confidence: CoachAnswerResponse['confidence'] | null;
  degraded: boolean;
  status: CoachAnswerResponse['status'];
  badge: string;
  tone: 'supported' | 'downgraded' | 'insufficient_data' | 'unsupported';
};

function safeHumanize(value: string | null | undefined, fallback: string): string {
  if (typeof value !== 'string' || value.trim().length === 0) return fallback;
  return value.replace(/_/g, ' ');
}

function normalizeStoredAnswerCard(raw: unknown): CoachAnswerCard | null {
  if (!raw || typeof raw !== 'object') return null;
  const value = raw as Partial<CoachAnswerCard>;
  if (typeof value.id !== 'string' || typeof value.question !== 'string') return null;
  return {
    id: value.id,
    question: value.question,
    domain: value.domain ?? 'general',
    questionClass: typeof value.questionClass === 'string' ? value.questionClass : null,
    short: typeof value.short === 'string' && value.short.length > 0
      ? value.short
      : 'Answer unavailable.',
    why: typeof value.why === 'string' && value.why.length > 0
      ? value.why
      : 'Coach context was partially available.',
    nextStep: typeof value.nextStep === 'string' && value.nextStep.length > 0
      ? value.nextStep
      : 'Ask a narrower follow-up question.',
    missingnessNote: typeof value.missingnessNote === 'string' ? value.missingnessNote : null,
    confidence: value.confidence ?? null,
    degraded: Boolean(value.degraded),
    status: value.status ?? 'downgraded',
    badge: typeof value.badge === 'string' && value.badge.length > 0
      ? value.badge
      : 'coach',
    tone: value.tone ?? 'downgraded',
  };
}

const TOPIC_OPTIONS: Array<{ value: EvidenceAwareTopic; label: string }> = [
  { value: 'recovery', label: 'Recovery' },
  { value: 'training_load', label: 'Load' },
  { value: 'adherence', label: 'Adherence' },
  { value: 'coaching_guidance', label: 'Coaching' },
];

const ANSWER_HISTORY_KEY = 'ai_coach_answers_v1';

export default function AiChatScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [question, setQuestion] = useState('');
  const [sending, setSending] = useState(false);
  const [topic, setTopic] = useState<EvidenceAwareTopic>('coaching_guidance');
  const [answers, setAnswers] = useState<CoachAnswerCard[]>([]);
  const [answersHydrated, setAnswersHydrated] = useState(false);

  // ── Backend AI context (one-call display source) ──────────
  const [aiCtx, setAiCtx] = useState<AthleteAiContextResponse | null>(null);
  const [aiCtxLoading, setAiCtxLoading] = useState(true);
  const [aiCtxError, setAiCtxError] = useState<string | null>(null);
  const [answerError, setAnswerError] = useState<string | null>(null);

  const authUserId = useAuthStore((s) => s.user?.id);
  const authAccessToken = useAuthStore((s) => s.session?.access_token ?? null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setAiCtxLoading(true);
      const config = buildAthleteMemoryClientConfig(authUserId, authAccessToken);
      if (!config) {
        // No signed-in user — do not read anyone else's data.
        setAiCtx(null);
        setAiCtxError('Sign in to see your personalized coaching context.');
        setAiCtxLoading(false);
        return;
      }
      const { data, error } = await fetchAiContext(config);
      if (cancelled) return;
      // If the backend rejects auth (401) or ownership (403), clear context
      // so we don't show anyone's cached seed data. Show an explicit state.
      if (error && (/\b401\b/.test(error) || /\b403\b/.test(error))) {
        setAiCtx(null);
        setAiCtxError('Session expired or missing. Sign in again to see your context.');
      } else {
        setAiCtx(data);
        setAiCtxError(error);
      }
      setAiCtxLoading(false);
    })();
    return () => { cancelled = true; };
  }, [authUserId, authAccessToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const stored = await readStoredJson<CoachAnswerCard[]>(ANSWER_HISTORY_KEY);
      if (cancelled) return;
      if (Array.isArray(stored)) {
        setAnswers(stored.map(normalizeStoredAnswerCard).filter(Boolean).slice(0, 6) as CoachAnswerCard[]);
      }
      setAnswersHydrated(true);
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!answersHydrated) return;
    void writeStoredJson(ANSWER_HISTORY_KEY, answers.slice(0, 6));
  }, [answers, answersHydrated]);

  // ── Local stores (for prompt building — Share.share needs full detail) ──
  const whoopDay = useWhoopStore((s) => s.day);
  const insights = useHealthStore((s) => s.insights);
  const aiPayload = useHealthStore((s) => s.aiPayload);
  const coaching = useHealthStore((s) => s.coaching);
  const sessions = useTrainingStore((s) => s.sessions);
  const preferences = usePreferencesStore((s) => s.preferences);
  const effectiveTier = useTierStore((s) => s.effectiveTier);
  const startPendingCase = useCoachingCasesStore((s) => s.startPending);
  const pendingCase = useCoachingCasesStore((s) => s.pending);
  const scrollRef = useRef<import('react-native').ScrollView | null>(null);
  const nutritionToday = useNutritionStore((s) => s.today);
  const nutritionTargets = useNutritionStore((s) => s.targets);
  const nutritionHistory = useNutritionStore((s) => s.historyDays);

  const currentTier = effectiveTier();
  const todayIsoDate = new Date().toISOString().slice(0, 10);
  const todayPlan = getTodayPlan(preferences.schedule);
  const todayPlanLabel = todayPlan.length > 0
    ? todayPlan.map((s) => s.type.replace('_', ' ')).join(', ')
    : 'Rest day';
  const recentSessions = useMemo(() => sessions.slice(-7), [sessions]);

  const briefInputs = {
    whoopDay, insights, todayPlan, recentSessions: sessions,
    todayIsoDate,
    nutritionToday: (nutritionToday as any) ?? null,
    nutritionTargets: (nutritionTargets as any) ?? null,
    nutritionHistory: (nutritionHistory as any) ?? [],
  };

  // ── Display state derived from backend context ──────────────
  const mode = aiCtx?.capability?.mode ?? 'seed_partial';
  const safeFor = aiCtx?.capability?.safeFor ?? [];
  const notSafeFor = aiCtx?.capability?.notSafeFor ?? [];
  const missingWhoop = aiCtx?.capability?.missingWhoopNativeFields ?? [];
  const seedMode = aiCtx?.seedMode ?? true;
  const dailyArtifact = aiCtx?.dailyArtifact ?? null;
  const weeklyArtifact = aiCtx?.weeklyArtifact ?? null;
  const normalizedDay = aiCtx?.normalizedDay ?? null;
  const nutritionSummary = aiCtx?.nutritionDailySummary ?? null;
  const dailyGuidance = dailyArtifact?.nextBestAction.guidance ?? null;
  const weeklyGuidance = weeklyArtifact?.nextThreeToSevenDayGuidance?.[0]?.guidance ?? null;
  const sourceDegraded = aiCtx?.sourceHealth?.status === 'degraded';
  const hiitSuggestion = useMemo(
    () =>
      suggestHIITProtocol({
        whoopDay,
        insights,
        recentSessions: sessions,
        todayIsoDate,
      }),
    [whoopDay, insights, sessions, todayIsoDate],
  );
  const conditioningAccess = useMemo(() => {
    const permissions = dailyArtifact?.sessionPermissions;
    if (!permissions) return { label: 'Conditioning guidance available', detail: dailyGuidance };
    const allowed = permissions.allowed.find((bucket) =>
      bucket.label.toLowerCase().includes('conditioning'),
    );
    if (allowed) {
      return {
        label: `Conditioning ${allowed.level.replace(/_/g, ' ')}`,
        detail: allowed.reasons[0] ?? dailyGuidance,
      };
    }
    const risky = permissions.risky.find((bucket) =>
      bucket.label.toLowerCase().includes('conditioning'),
    );
    if (risky) {
      return {
        label: `Conditioning ${risky.level.replace(/_/g, ' ')}`,
        detail: risky.reasons[0] ?? dailyGuidance,
      };
    }
    const banned = permissions.banned.find((bucket) =>
      bucket.label.toLowerCase().includes('conditioning'),
    );
    if (banned) {
      return {
        label: `Conditioning ${banned.level.replace(/_/g, ' ')}`,
        detail: banned.reasons[0] ?? dailyGuidance,
      };
    }
    return { label: 'Conditioning guidance available', detail: dailyGuidance };
  }, [dailyArtifact?.sessionPermissions, dailyGuidance]);
  const hiitQuickAsks = useMemo(() => {
    const prompts = [
      'Should I do HIIT today?',
      'Give me a safer conditioning option for today.',
      `What interval format fits grappling best right now: ${hiitSuggestion.label}?`,
    ];
    if (dailyGuidance) {
      prompts.unshift(`Use this daily guidance to shape a HIIT answer: ${dailyGuidance}`);
    }
    return prompts.slice(0, 4);
  }, [dailyGuidance, hiitSuggestion.label]);

  const starterPrompts = useMemo(() => {
    const prompts: string[] = [];
    if (todayPlan.length > 0) prompts.push(`How should I handle my ${todayPlanLabel} session today?`);
    if (coaching?.grappling.suggestion) prompts.push(`Turn this into a drill plan: ${coaching.grappling.suggestion}`);
    prompts.push('What should I prioritize today: recovery, drilling, or a hard session?');
    if (nutritionToday) {
      prompts.push('How did I eat today vs what I need?');
    } else {
      prompts.push('What should I track next for better fueling guidance?');
    }
    prompts.push('Help me plan the rest of this training week.');
    return prompts.slice(0, 3);
  }, [coaching?.grappling.suggestion, todayPlan.length, todayPlanLabel, nutritionToday]);

  // Newest answer now lives at the END of the array (chat-style
  // ordering). followUpPrompts keys off the most recent answer.
  const latestAnswer = answers[answers.length - 1] ?? null;
  const followUpPrompts = useMemo(() => {
    if (!latestAnswer) return [] as string[];
    if (latestAnswer.status === 'insufficient_data' || latestAnswer.status === 'unsupported') {
      return [
        'What should I log next so your answer gets better?',
        'Give me a safer low-certainty option anyway.',
      ];
    }
    if (/nutrition|protein|calorie|macro/i.test(latestAnswer.question)) {
      return [
        'What is the simplest nutrition target for the rest of today?',
        'How should I adjust dinner if training is still ahead?',
      ];
    }
    if (/hiit|interval|conditioning|sprint|bike|rower/i.test(latestAnswer.question)) {
      return [
        'Shorten that HIIT option if today feels worse than expected.',
        'Give me a lower-risk conditioning fallback instead.',
      ];
    }
    return [
      'Make that advice more conservative.',
      'Turn that into one simple next step.',
    ];
  }, [latestAnswer]);

  const mapAnswerTone = (status: CoachAnswerResponse['status']): CoachAnswerCard['tone'] => {
    switch (status) {
      case 'answered':
        return 'supported';
      case 'downgraded':
        return 'downgraded';
      case 'insufficient_data':
        return 'insufficient_data';
      case 'unsupported':
      default:
        return 'unsupported';
    }
  };

  const mapAnswerBadge = (answer: CoachAnswerResponse): string => {
    if (answer.status === 'answered') return `${answer.domain} · ${answer.mode === 'live_ready' ? 'live' : 'seed'}`;
    if (answer.status === 'downgraded') return `${answer.domain} · partial`;
    if (answer.status === 'insufficient_data') return `${answer.domain} · limited`;
    return `${answer.domain} · unsupported`;
  };

  const handleShare = async (promptOverride?: string) => {
    if (sending) return;
    setSending(true);
    const trimmed = (promptOverride ?? question).trim();
    const { context } = buildCoachingPromptPacket({ ...briefInputs, userQuestion: trimmed || null });
    const days = useHealthStore.getState().days;
    const features = useHealthStore.getState().features;
    const healthLastSyncAt = useHealthStore.getState().lastSyncAt;
    const whoopFetchedAt = useWhoopStore.getState().fetchedAt;
    // Hydrate WHOOP CSV status from local cache so source_roles shows
    // the third layer when it's been imported. Cache is written by the
    // WhoopCsvRow on backend refresh; null = not imported.
    let whoopCsvState: { imported: boolean; rowCount: number | null; windowDays: null } | null = null;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { readStoredJson } = require('../src/store/secure-storage');
      const cached = await readStoredJson('whoop_csv_imported_v1');
      if (cached && typeof cached === 'object' && (cached as any).imported === true) {
        whoopCsvState = {
          imported: true,
          rowCount: (cached as any).totalRowsIngested ?? null,
          windowDays: null,
        };
      }
    } catch { /* ignore */ }
    const polarViaHcForCoach = useHealthStore.getState().polarViaHc;
    const samsungViaHcForCoach = useHealthStore.getState().samsungHealthViaHc;
    const appAthleteState = buildAppAthleteState({
      todayIsoDate,
      days,
      features,
      sessions,
      whoopDay: whoopDay as any,
      whoopFetchedAt,
      nutritionToday: (nutritionToday as any) ?? null,
      nutritionTargets: (nutritionTargets as any) ?? null,
      nutritionHistory: (nutritionHistory as any) ?? null,
      healthLastSyncAt,
      whoopCsv: whoopCsvState,
      whoopFetchStatus: useWhoopStore.getState().status,
      polarPresence: polarViaHcForCoach?.detected ? {
        detected: true,
        viaHealthConnect: true,
        daysWithRecords: polarViaHcForCoach.daysWithRecords ?? null,
      } : null,
      samsungPresence: samsungViaHcForCoach?.detected ? {
        detected: true,
        daysWithRecords: samsungViaHcForCoach.daysWithRecords ?? null,
      } : null,
    });
    const { text } = buildEvidenceAwareAiRequestPacket({
      question: trimmed || null, topic, requestedMode: 'evidence',
      currentPlan: currentTier, downgradeAllowed: true, todayIsoDate,
      brief: buildDailyCoachingBrief(briefInputs), whoopDay, sessions, preferences,
      aiPayload, coaching, latestRecommendationFeedback: null, latestCheckin: null,
      progressMap: {}, updatedAtMap: {},
      nutritionToday: (nutritionToday as any) ?? null,
      nutritionTargets: (nutritionTargets as any) ?? null,
      appAthleteState,
    });
    try {
      await Share.share({ message: text, title: 'Lauburu AI Coach request' });
      startPendingCase({ context, prompt_packet: text, source: 'external_chatgpt' });
    } catch {
      // dismissed
    } finally {
      setSending(false);
    }
  };

  const handleSend = async () => {
    if (sending) return;
    setSending(true);
    setAnswerError(null);
    const trimmed = question.trim();
    if (!trimmed) {
      setSending(false);
      return;
    }
      const coachConfig = buildAthleteMemoryClientConfig(authUserId, authAccessToken);
      if (!coachConfig) {
        setAnswerError('Sign in to ask the Coach.');
        setSending(false);
        return;
      }
      // Build the app-owned device-agnostic athlete state from merged
      // store data and send it alongside the question so the backend
      // can reason over our normalized layer, not raw vendor scores.
      // Refresh today's Apple Health dietary totals before assembling
      // the Coach context. Without this await, the Coach request is
      // built against whatever nutrition-store.today happens to hold
      // from the background health-sync — which may still be null if
      // the sync hasn't finished since app launch, causing Coach to
      // reply "no nutrition data logged for today" even when Apple
      // Health has the records. Bounded to ~2s so the send still
      // feels responsive if HealthKit is slow.
      if (Platform.OS === 'ios') {
        try {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const hkMod = require('../src/services/health.ios');
          if (typeof hkMod?.fetchDietaryDailyTotals === 'function') {
            const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
            const todayEnd = new Date(); todayEnd.setHours(23, 59, 59, 999);
            const totals = await Promise.race([
              hkMod.fetchDietaryDailyTotals({ start: todayStart, end: todayEnd }),
              new Promise((resolve) => setTimeout(() => resolve(null), 2000)),
            ]) as any;
            if (totals && (totals.calories_kcal || totals.protein_g)) {
              const { meal_count: _mc, first_meal_at: _fm, last_meal_at: _lm, ...recordTotals } = totals;
              // eslint-disable-next-line @typescript-eslint/no-require-imports
              const ns = require('../src/store/nutrition-store');
              const merge = ns?.useNutritionStore?.getState?.()?.mergeHubDailyTotals;
              if (typeof merge === 'function') {
                merge(todayIsoDate, recordTotals, 'apple_health');
              }
            }
          }
        } catch { /* non-fatal — Coach will use store snapshot */ }
      }
      // Re-read nutrition-store AFTER the merge above so the Coach
      // context reflects the freshest totals, not the stale selector
      // snapshot captured when the component rendered.
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const freshNutritionToday = (() => {
        try {
          const ns = require('../src/store/nutrition-store');
          return ns?.useNutritionStore?.getState?.()?.today ?? null;
        } catch { return null; }
      })();
      const nutritionTodayForCoach = freshNutritionToday ?? nutritionToday;
      const daysForCoach = useHealthStore.getState().days;
      const featuresForCoach = useHealthStore.getState().features;
      const healthLastSyncAtForCoach = useHealthStore.getState().lastSyncAt;
      const whoopFetchedAtForCoach = useWhoopStore.getState().fetchedAt;
      // Hydrate WHOOP CSV cache for the Coach backend request so
      // source_roles reflects the third layer.
      let whoopCsvStateForCoach: { imported: boolean; rowCount: number | null; windowDays: null } | null = null;
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { readStoredJson } = require('../src/store/secure-storage');
        const cached = await readStoredJson('whoop_csv_imported_v1');
        if (cached && typeof cached === 'object' && (cached as any).imported === true) {
          whoopCsvStateForCoach = {
            imported: true,
            rowCount: (cached as any).totalRowsIngested ?? null,
            windowDays: null,
          };
        }
      } catch { /* ignore */ }
      const polarViaHcForCoachReq = useHealthStore.getState().polarViaHc;
      const samsungViaHcForCoachReq = useHealthStore.getState().samsungHealthViaHc;
      const appAthleteStateForCoach = buildAppAthleteState({
        todayIsoDate,
        days: daysForCoach,
        features: featuresForCoach,
        sessions,
        whoopDay: whoopDay as any,
        whoopFetchedAt: whoopFetchedAtForCoach,
        nutritionToday: (nutritionTodayForCoach as any) ?? null,
        nutritionTargets: (nutritionTargets as any) ?? null,
        nutritionHistory: (nutritionHistory as any) ?? null,
        healthLastSyncAt: healthLastSyncAtForCoach,
        whoopCsv: whoopCsvStateForCoach,
        whoopFetchStatus: useWhoopStore.getState().status,
        polarPresence: polarViaHcForCoachReq?.detected ? {
          detected: true,
          viaHealthConnect: true,
          daysWithRecords: polarViaHcForCoachReq.daysWithRecords ?? null,
        } : null,
        samsungPresence: samsungViaHcForCoachReq?.detected ? {
          detected: true,
          daysWithRecords: samsungViaHcForCoachReq.daysWithRecords ?? null,
        } : null,
      });
      const sessionSummary = {
        last_7d_count: sessions.filter((s) => {
          const floor = new Date(todayIsoDate); floor.setDate(floor.getDate() - 7);
          return s.date >= floor.toISOString().slice(0, 10) && s.date <= todayIsoDate;
        }).length,
        last_session: sessions[0] ? { date: sessions[0].date, type: sessions[0].type, intensity: sessions[0].intensity } : null,
      };

      // Nutrition history — last 14 days of confirmed daily totals. The
      // backend already stores these (per-user on Railway) but the
      // Coach.ask handler doesn't fan-out to fetch them, so attaching
      // inline lets trend-aware answers ("protein has been consistently
      // under target this week") become possible TODAY without a
      // backend deploy. Trimmed to the 14 most recent days to keep
      // request size bounded.
      const nutritionHistoryForCoach = (() => {
        try {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const ns = require('../src/store/nutrition-store');
          const hist = ns?.useNutritionStore?.getState?.()?.historyDays ?? [];
          // Widened 14 → 60 days so trend answers can reach a month-
          // over-month comparison. Per-day record is small; even 60
          // rows stays well under any reasonable Coach request cap.
          return Array.isArray(hist) ? hist.slice(-60) : [];
        } catch { return []; }
      })();

      // Recent sessions — last 10 grappling / conditioning / HIIT rows
      // so Coach can compare today's answer against the last couple of
      // weeks of actual training. Field list intentionally compact.
      const recentSessionsForCoach = sessions.slice(0, 30).map((s) => ({
        date: s.date,
        type: s.type,
        intensity: s.intensity,
        duration_min: s.duration_min,
        rpe: s.rpe ?? null,
        preset_id: s.preset_id ?? null,
      }));

      // HIIT history — the saved-HIIT protocol store carries per-set
      // metrics Coach can use for workout-to-workout comparison.
      const hiitHistoryForCoach = (() => {
        try {
          // eslint-disable-next-line @typescript-eslint/no-require-imports
          const hiitStore = require('../src/store/hiit-workout-store');
          const workouts = hiitStore?.useHIITWorkoutStore?.getState?.()?.workouts ?? [];
          return Array.isArray(workouts)
            ? workouts.slice(0, 8).map((w: any) => ({
                id: w.id,
                date: w.date,
                templateId: w.templateId,
                protocolFormat: w.protocolFormat,
                totalSets: w.totalSets,
                avgWatts: w.avgWatts,
                peakWatts: w.peakWatts,
                avgHr: w.avgHr,
                peakHr: w.peakHr,
                totalDurationSeconds: w.totalDurationSeconds,
                totalCalories: w.totalCalories,
              }))
            : [];
        } catch { return []; }
      })();

      // WHOOP CSV coverage — surface the deeper-enrichment signal so
      // Coach knows it's reasoning with 90d of export history, not
      // just the live-cycle day.
      const whoopCsvCoverageForCoach = whoopCsvStateForCoach
        ? { imported: whoopCsvStateForCoach.imported, row_count: whoopCsvStateForCoach.rowCount }
        : null;

      const { data, error } = await fetchCoachAnswer(coachConfig, {
      question: trimmed,
      topic,
      app_athlete_state: appAthleteStateForCoach,
      nutrition_today: nutritionTodayForCoach ?? null,
      nutrition_targets: nutritionTargets ?? null,
      session_summary: sessionSummary,
      nutrition_history: nutritionHistoryForCoach,
      recent_sessions: recentSessionsForCoach,
      hiit_history: hiitHistoryForCoach,
      whoop_csv_coverage: whoopCsvCoverageForCoach,
      // Platform hint so the backend can filter cross-platform
      // guidance (e.g. never tell an iPhone user to "Grant Health
      // Connect permissions"). Safe to add — older backends ignore.
      platform: Platform.OS,
    });
    if (!data) {
      setAnswerError(error ?? 'Coach answer unavailable.');
      setSending(false);
      return;
    }
    // Platform-aware + relevance-aware rewrite:
    //   - on iPhone, strip Android/Health Connect/Samsung phrasing
    //   - when the user's actual stack is Apple Health + WHOOP, strip
    //     Polar/Garmin/Fitbit ecosystem asks since they're not part
    //     of this user's current relevant setup
    // The backend still emits these because it doesn't yet consume
    // the platform hint we now send. Mobile-side filter keeps the
    // displayed answer coherent with the device + connected sources.
    // Live connected-signal snapshots so the rewriter can suppress
    // "WHOOP not connected" / "Apple Health not connected" type
    // sentences when those sources ARE connected locally but the
    // backend's cached source-health view still says otherwise.
    const whoopIsConnected = (() => {
      try {
        const s = useWhoopStore.getState();
        return s.status === 'ready' || s.status === 'loading' || s.day != null || s.fetchedAt != null;
      } catch { return false; }
    })();
    const appleHealthHasData = (() => {
      try { return (useHealthStore.getState().days?.length ?? 0) > 0; } catch { return false; }
    })();
    const rewrite = (s: string | null | undefined): string => {
      if (typeof s !== 'string' || s.length === 0) return s ?? '';
      let out = s;
      if (Platform.OS === 'ios') {
        // Snake_case tokens the backend sometimes emits in source-health
        // text: "polar_via_health_connect not connected", "health_connect
        // not connected", "samsung_health_via_health_connect not
        // connected". \b doesn't work inside snake_case (underscore is
        // a word char), so use explicit boundaries.
        out = out
          .replace(/\bsamsung_health_via_health_connect\b[^.?!]*[.?!]?/gi, '')
          .replace(/\bpolar_via_health_connect\b[^.?!]*[.?!]?/gi, '')
          .replace(/\bhealth_connect\b[^.?!]*[.?!]?/gi, '')
          .replace(/Android Health Connect/gi, 'Apple Health')
          .replace(/Health Connect/g, 'Apple Health')
          .replace(/Samsung Health/gi, 'Apple Health')
          .replace(/\bSync Health Connect on Android\b[^.?!]*[.?!]?/gi, '');
      }
      // Remove irrelevant-ecosystem sentences when Apple Health +
      // WHOOP are the user's setup.
      out = out
        .replace(/[^.?!]*\b(Polar|Garmin|Fitbit|Oura|ErgData|MyFitnessPal|Cronometer)\b[^.?!]*[.?!]/g, '');
      // Suppress source-state sentences that disagree with local truth.
      // If WHOOP is connected locally but the backend is echoing a
      // stale "WHOOP not connected" / "no whoop source-health record"
      // line, strip that sentence rather than show the contradiction.
      if (whoopIsConnected) {
        out = out
          .replace(/[^.?!]*\b(no\s+whoop\s+source[-\s]?health|whoop[-_\s]?source[-\s]?health\s+record|WHOOP\s+not\s+connected|whoop_not_connected)\b[^.?!]*[.?!]?/gi, '');
      }
      if (appleHealthHasData && Platform.OS === 'ios') {
        out = out.replace(/[^.?!]*\bApple\s+Health\s+not\s+connected\b[^.?!]*[.?!]?/gi, '');
      }
      // Local nutrition truth wins over backend staleness. If we know
      // the user has nutrition logged today (or Apple Health dietary
      // was synced), strip any backend sentence that claims otherwise.
      const nutritionLoggedLocally = (() => {
        try {
          // Read the freshest store state rather than the closure's
          // selector snapshot. If the user logged a food (energy drink,
          // meal) immediately before asking Coach, the selector may
          // still hold the pre-add value while the store is current —
          // which used to make the rewriter miss the strip and
          // surface a stale "no nutrition data logged" sentence.
          const t: any = nutritionTodayForCoach ?? (nutritionToday as any) ?? null;
          if (!t) return false;
          return t.calories_kcal != null || t.protein_g != null || t.carbs_g != null || t.fat_g != null || t.water_ml != null;
        } catch { return false; }
      })();
      if (nutritionLoggedLocally) {
        out = out
          .replace(/[^.?!]*\bno\s+nutrition\s+data\s+(?:is\s+)?logged[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\bno\s+nutrition\s+logged\b[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\bnutrition\s+not\s+logged\b[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\bno\s+food\s+logged\b[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\bno\s+fuel\s+logged\b[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\byou\s+haven[''’]?t\s+logged\s+any\s+(?:nutrition|food|fuel)\b[^.?!]*[.?!]?/gi, '')
          .replace(/[^.?!]*\bnothing\s+logged\s+for\s+(?:nutrition|food|fuel)\b[^.?!]*[.?!]?/gi, '');
      }
      out = out
        .replace(/Apple Health or Apple Health/g, 'Apple Health')
        .replace(/Apple Health \/ Apple Health/g, 'Apple Health')
        .replace(/\s{2,}/g, ' ')
        .trim();
      return out.length === 0 ? '' : out;
    };
    // Build a local fallback from AppAthleteState in case the rewriter
    // strips the Coach response down to nothing (happens when every
    // sentence the backend emits is platform/ecosystem/source-state
    // text we've judged irrelevant). Better to show grounded local
    // summary than an empty card. Uses recovery_context + load_context
    // + fueling_adequacy from the state we just sent to the backend.
    const localFallback = (() => {
      const aas: any = appAthleteStateForCoach;
      if (!aas) return null;
      const recBand = aas?.recovery_context?.band;
      const recScore = aas?.recovery_context?.score_0_100;
      const loadBand = aas?.load_context?.band;
      const fuelBand = aas?.fueling_adequacy?.band;
      const fuelNote = aas?.fueling_adequacy?.note;
      const recNote = aas?.recovery_context?.note;
      // Label as "Readiness" (the app's blended custom score) rather
      // than "Recovery" so users don't confuse it with WHOOP's native
      // recovery score rendered in the WHOOP card.
      const short = recScore != null
        ? `Readiness ${recBand} (${recScore}/100) · Load ${loadBand} · Fueling ${fuelBand}`
        : `Readiness ${recBand} · Load ${loadBand} · Fueling ${fuelBand}`;
      const why = [recNote, fuelNote].filter((s) => typeof s === 'string' && s.length > 0).join(' ');
      const nextStep = aas?.readiness_confidence?.reasons_for_low?.[0] ?? 'Keep logging; Coach sharpens with more recent data.';
      return { short, why, nextStep };
    })();
    const rewrittenShort = rewrite(data.answer.short);
    const rewrittenWhy = rewrite(data.answer.why);
    const rewrittenNext = rewrite(data.answer.nextStep);
    const rewrittenAll = `${rewrittenShort} ${rewrittenWhy} ${rewrittenNext}`.trim();
    const useLocal = rewrittenAll.length < 12 && localFallback != null;

    const answer: CoachAnswerCard = {
      id: `${Date.now()}-${data.domain}`,
      question: trimmed,
      domain: data.domain,
      questionClass: data.questionClass,
      short: useLocal ? localFallback!.short : rewrittenShort,
      why: useLocal ? localFallback!.why : rewrittenWhy,
      nextStep: useLocal ? localFallback!.nextStep : rewrittenNext,
      missingnessNote: rewrite(data.answer.missingnessNote),
      confidence: data.confidence,
      degraded: data.status === 'downgraded' || data.safetyFlags.includes('answer_downgraded'),
      status: data.status,
      badge: mapAnswerBadge(data),
      tone: mapAnswerTone(data.status),
    };
    // Append at the end so answers read top→bottom like a chat feed
    // (oldest at top, newest at bottom). The ScrollView auto-scrolls
    // to the bottom on content-size change so the latest answer is
    // always visible without manual scrolling.
    setAnswers((current) => [...current.filter((entry) => entry.question !== trimmed), answer].slice(-6));
    setQuestion('');
    setSending(false);
    // Drop the keyboard so the new answer is fully visible without
    // the user having to tap away.
    Keyboard.dismiss();
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 8 : 0}>
      <View style={[styles.header, { paddingTop: Math.max(insets.top, 12) }]}>
        <Text style={styles.headerTitle}>AI Coach</Text>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={styles.headerClose}>Done</Text>
        </Pressable>
      </View>

      <ScrollView
        ref={scrollRef}
        style={styles.body}
        contentContainerStyle={styles.bodyContent}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={() => {
          // Bottom-anchored like a normal chat: when answers or
          // input area grow, scroll to the bottom so the user sees
          // the latest content without manual scrolling.
          if (answers.length > 0) {
            scrollRef.current?.scrollToEnd({ animated: true });
          }
        }}>
        {/* Loading / offline / answer error — kept compact and
            only shown when actually needed. No always-on capability
            badge; the AthleteStateStrip below carries the source
            state already. */}
        {aiCtxLoading && (
          <View style={styles.capBadge}>
            <ActivityIndicator size="small" color="#d4e157" />
            <Text style={styles.capText}>Loading coach context...</Text>
          </View>
        )}
        {aiCtxError && (
          <View style={styles.capBadge}>
            <Text style={[styles.capText, { color: '#ff6b6b' }]}>Offline — using local context</Text>
          </View>
        )}
        {answerError && (
          <View style={styles.capBadge}>
            <Text style={[styles.capText, { color: '#ff8a80' }]}>{answerError}</Text>
          </View>
        )}

        {/* One athlete summary — app-owned device-agnostic analysis.
            Covers recovery, load, sleep, fueling, hydration, acute
            fatigue, confidence, and missingness. This is THE one
            summary card for the Coach screen. No separate capability
            badge, no safe-for card, no duplicate context card. */}
        <AthleteStateStrip />

        {/* ── Pending follow-up ── */}
        {pendingCase && (
          <View style={styles.pendingWrap}>
            <Pressable style={styles.pendingChip} onPress={() => setQuestion(
              pendingCase.context.user_question
                ? `Follow up: ${pendingCase.context.user_question}`
                : 'Follow up on my earlier coaching prompt.'
            )}>
              <Text style={styles.pendingText}>Continue pending case</Text>
            </Pressable>
          </View>
        )}

        {/* Starter prompts — shown only when there are no answers
            yet. Once the user has started a conversation, the chips
            disappear so the answer history is the focus. */}
        {answers.length === 0 && starterPrompts.map((p) => (
          <Pressable key={p} style={styles.starterChip} onPress={() => setQuestion(p)}>
            <Text style={styles.starterText}>{p}</Text>
          </Pressable>
        ))}

        {/* Topic chips — only when no answers yet, same rationale */}
        {answers.length === 0 && (
          <View style={styles.topicRow}>
            {TOPIC_OPTIONS.map((t) => (
              <Pressable
                key={t.value}
                style={[styles.topicChip, topic === t.value && styles.topicChipActive]}
                onPress={() => setTopic(t.value)}>
                <Text style={[styles.topicText, topic === t.value && styles.topicTextActive]}>
                  {t.label}
                </Text>
              </Pressable>
            ))}
          </View>
        )}

        {answers.length > 0 && (
          <View style={styles.answerSection}>
            <View style={styles.answerHeaderRow}>
              <Text style={styles.sectionTitle}>Answers</Text>
              <Pressable onPress={() => setAnswers([])} hitSlop={8}>
                <Text style={styles.answerClearText}>Clear</Text>
              </Pressable>
            </View>
            {answers.map((answer) => (
              <AnswerBlock
                key={answer.id}
                answer={answer}
                onShare={() => handleShare(answer.question)}
              />
            ))}
            {latestAnswer && followUpPrompts.length > 0 && (
              <View style={styles.followUpRow}>
                {followUpPrompts.slice(0, 2).map((prompt) => (
                  <Pressable
                    key={prompt}
                    style={styles.followUpChipCompact}
                    onPress={() => setQuestion(prompt)}>
                    <Text style={styles.followUpTextCompact} numberOfLines={1} ellipsizeMode="tail">{prompt}</Text>
                  </Pressable>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>

      <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        <TextInput
          style={styles.input}
          value={question}
          onChangeText={setQuestion}
          placeholder="Ask about training, recovery, or technique"
          placeholderTextColor="#666"
          multiline
          maxLength={500}
          scrollEnabled
          // iOS: move the keyboard to a clean dismiss-on-drag — prevents
          // the long-message-typed-then-keyboard-stays case where the
          // input bottom edge is hidden because the soft keyboard +
          // input region together exceed the safe area.
          textAlignVertical="top"
          autoCorrect
          blurOnSubmit={false}
        />
        <Pressable
          style={[styles.sendBtn, sending && styles.sendBtnDisabled]}
          onPress={handleSend}
          disabled={sending}>
          <Text style={styles.sendBtnText}>{sending ? '...' : 'Ask'}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

/**
 * Cleaner answer card. The visible default is:
 *   - You: <question> bubble (right-aligned)
 *   - AI: <short> headline + <nextStep> recommendation
 * Why-bullets, missingness, and "Share full context" sit behind a
 * "View details" disclosure so the card reads as chat-style
 * takeaways rather than a wall of text.
 */
function AnswerBlock({
  answer,
  onShare,
}: {
  answer: CoachAnswerCard;
  onShare: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const whyBullets = (answer.why ?? '')
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .slice(0, 4);
  const hasDetails = whyBullets.length > 0 || (!!answer.missingnessNote && answer.missingnessNote.trim().length > 4);

  // Share is only worth surfacing when the answer is genuinely
  // partial / insufficient — that's when forwarding the full context
  // to ChatGPT/Claude/Codex helps. For supported answers the Share
  // button is noise. Hidden in details either way.
  const shareWorthShowing = answer.tone !== 'supported';

  return (
    <View style={styles.answerBlockWrap}>
      <Text style={styles.speakerLabelYou}>You asked</Text>
      <View style={styles.questionBubble}>
        <Text style={styles.questionBubbleText} numberOfLines={3} ellipsizeMode="tail">
          {answer.question}
        </Text>
      </View>
      <Text style={styles.speakerLabelCoach}>Coach answered</Text>
      <View style={styles.answerCardClean}>
        {answer.short && answer.short.trim().length > 0 && (
          <Text style={styles.answerShort}>{answer.short}</Text>
        )}
        {answer.nextStep && answer.nextStep.trim().length > 0 && (
          <Text style={styles.answerNextClean}>→ {answer.nextStep}</Text>
        )}
        {hasDetails && (
          <Pressable onPress={() => setExpanded((v) => !v)} hitSlop={6}>
            <Text style={styles.detailsToggle}>
              {expanded
                ? '▾ Hide details'
                : `▸ View details${whyBullets.length > 0 ? ` · ${whyBullets.length} ${whyBullets.length === 1 ? 'finding' : 'findings'}` : ''}`}
            </Text>
          </Pressable>
        )}
        {expanded && hasDetails && (
          <View style={{ gap: 6 }}>
            {whyBullets.length > 0 && (
              <View style={{ gap: 2 }}>
                {whyBullets.map((b, i) => (
                  <Text key={i} style={styles.answerWhy}>• {b}</Text>
                ))}
              </View>
            )}
            {answer.missingnessNote && answer.missingnessNote.trim().length > 4 && (
              <Text style={styles.answerMissing}>{answer.missingnessNote}</Text>
            )}
            {shareWorthShowing && (
              <Pressable onPress={onShare} hitSlop={6}>
                <Text style={styles.shareInline}>Share full context externally</Text>
              </Pressable>
            )}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0e0e0e' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 16, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#f5f7f9' },
  headerClose: { fontSize: 15, fontWeight: '600', color: '#d4e157' },
  body: { flex: 1 },
  bodyContent: { padding: 14, gap: 10 },

  capBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 8, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.08)', borderWidth: 1, borderColor: 'rgba(212,225,87,0.2)',
  },
  capMode: { fontSize: 11, fontWeight: '800', color: '#d4e157', textTransform: 'uppercase' },
  capText: { fontSize: 12, color: '#ccc' },

  safeCard: { gap: 6 },
  safeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  safeChip: {
    paddingVertical: 4, paddingHorizontal: 8, borderRadius: 6,
    backgroundColor: 'rgba(212,225,87,0.1)', borderWidth: 1, borderColor: 'rgba(212,225,87,0.2)',
  },
  safeChipText: { fontSize: 11, fontWeight: '600', color: '#d4e157' },
  notSafeText: { fontSize: 11, color: '#999' },
  hiitCard: {
    padding: 12,
    borderRadius: 10,
    gap: 8,
    backgroundColor: 'rgba(212,225,87,0.07)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.18)',
  },
  hiitHeadline: {
    fontSize: 13,
    fontWeight: '700',
    color: '#f5f7f9',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#f5f7f9',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },

  ctxCard: {
    padding: 12, borderRadius: 10, gap: 4,
    backgroundColor: 'rgba(255,255,255,0.03)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)',
  },
  ctxLine: { fontSize: 12, color: '#d7d9dc' },
  ctxMissing: { fontSize: 11, color: '#ff6b6b', marginTop: 2 },

  pendingWrap: { gap: 8 },
  pendingChip: {
    paddingVertical: 8, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.1)', borderWidth: 1, borderColor: 'rgba(212,225,87,0.2)',
  },
  pendingText: { fontSize: 12, fontWeight: '600', color: '#d4e157' },

  starterChip: {
    paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', backgroundColor: 'rgba(255,255,255,0.03)',
  },
  starterList: { gap: 8 },
  starterText: { fontSize: 13, color: '#eef1f3', lineHeight: 18 },
  answerSection: { gap: 10 },
  answerHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  answerClearText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#aab0b5',
  },
  answerCard: {
    padding: 12,
    borderRadius: 12,
    gap: 8,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
  },
  answerRowTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 8,
  },
  answerQuestion: {
    fontSize: 12,
    color: '#aab0b5',
    flex: 1,
  },
  answerQuestionCompact: {
    fontSize: 11,
    color: '#aab0b5',
    opacity: 0.7,
    marginBottom: 2,
  },
  answerStatusChip: {
    fontSize: 10,
    fontWeight: '800',
    textTransform: 'uppercase',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  answerStatusSupported: {
    color: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.12)',
  },
  answerStatusDowngraded: {
    color: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.12)',
  },
  answerStatusInsufficient: {
    color: '#ffb3b3',
    backgroundColor: 'rgba(255,107,107,0.12)',
  },
  answerShort: {
    fontSize: 14,
    lineHeight: 20,
    color: '#f5f7f9',
    fontWeight: '700',
  },
  answerWhy: {
    fontSize: 12,
    lineHeight: 18,
    color: '#d0d4d7',
  },
  answerNext: {
    fontSize: 12,
    lineHeight: 18,
    color: '#d4e157',
  },
  answerMetaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  answerMetaChip: {
    fontSize: 11,
    color: '#bfc4c8',
    textTransform: 'uppercase',
  },
  answerMissing: {
    fontSize: 11,
    lineHeight: 16,
    color: '#ffb3b3',
  },
  followUpWrap: { gap: 8 },
  followUpLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#d7d9dc',
  },
  followUpRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  followUpChip: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  followUpText: {
    fontSize: 12,
    color: '#eef1f3',
    lineHeight: 16,
  },
  secondaryShareBtn: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.1)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.18)',
  },
  secondaryShareText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#d4e157',
  },

  topicRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  topicChip: {
    paddingVertical: 5, paddingHorizontal: 10, borderRadius: 8,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.12)', backgroundColor: 'rgba(255,255,255,0.04)',
  },
  topicChipActive: { borderColor: 'rgba(212,225,87,0.4)', backgroundColor: 'rgba(212,225,87,0.12)' },
  topicText: { fontSize: 12, fontWeight: '600', color: '#aaa' },
  topicTextActive: { color: '#d4e157' },

  inputBar: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    paddingHorizontal: 12, paddingTop: 10,
    borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)',
    backgroundColor: '#0e0e0e',
  },
  input: {
    flex: 1, minHeight: 44, maxHeight: 140,
    paddingHorizontal: 12, paddingVertical: 10, borderRadius: 12,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', backgroundColor: 'rgba(255,255,255,0.04)',
    color: '#f5f7f9', fontSize: 14, lineHeight: 20,
  },
  // Cleaner answer card pieces — used by AnswerBlock above.
  answerBlockWrap: { gap: 4 },
  speakerLabelYou: {
    alignSelf: 'flex-end',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: '#9aa0a4',
    paddingRight: 4,
  },
  speakerLabelCoach: {
    alignSelf: 'flex-start',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: '#d4e157',
    paddingLeft: 4,
    marginTop: 4,
  },
  questionBubble: {
    alignSelf: 'flex-end',
    maxWidth: '85%',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 14,
    backgroundColor: 'rgba(212,225,87,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.25)',
  },
  questionBubbleText: {
    fontSize: 13,
    color: '#eef1f3',
    fontWeight: '600',
  },
  answerCardClean: {
    padding: 11,
    borderRadius: 12,
    gap: 6,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
  },
  answerHeaderTag: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
    backgroundColor: 'rgba(212,225,87,0.14)',
  },
  answerTagText: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: '#d4e157',
  },
  answerNextClean: {
    fontSize: 13,
    lineHeight: 19,
    color: '#d4e157',
    fontWeight: '600',
  },
  detailsToggle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#9aa0a4',
    paddingTop: 2,
  },
  shareInline: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9aa0a4',
    paddingTop: 4,
  },
  followUpChipCompact: {
    flexShrink: 1,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  followUpTextCompact: {
    fontSize: 12,
    color: '#d7d9dc',
  },
  sendBtn: {
    height: 44, paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center',
    borderRadius: 12, backgroundColor: '#d4e157',
  },
  sendBtnDisabled: { opacity: 0.5 },
  sendBtnText: { color: '#0b0b0b', fontSize: 14, fontWeight: '700' },
});
