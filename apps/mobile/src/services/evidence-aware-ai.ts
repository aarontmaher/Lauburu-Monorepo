import type {
  AIPayload,
  CoachingPreferences,
  CoachingResponse,
  DailyCoachingBrief,
  NextDayCheckin,
  RecommendationFeedback,
  Tier,
  TrainingSession,
} from '@lauburu/shared';
import { minimumTierFor } from '@lauburu/shared';
import {
  parseProgressKey,
  type ProgressStatus,
} from '../store/reference-progress-store';

export type EvidenceAwareTopic =
  | 'recovery'
  | 'training_load'
  | 'adherence'
  | 'habit_building'
  | 'scheduling'
  | 'coaching_guidance'
  | 'product_guidance';

export type AiMode = 'standard' | 'evidence' | 'premium_research';
export type AiBudgetClass = 'safe' | 'moderate' | 'premium';
export type AiPolicyStatus = 'allowed' | 'downgraded' | 'blocked';
export type AiFeatureBucket =
  | 'core_coaching'
  | 'habit_recovery'
  | 'advanced_analysis';
export type AiAccessResolution =
  | 'included'
  | 'downgraded'
  | 'upgrade_required'
  | 'pay_per_use_available'
  | 'purchase_required'
  | 'blocked';
export type AiDailyUsageClass =
  | 'daily_standard'
  | 'daily_evidence'
  | 'daily_premium';
export type AiDailyAllowanceState =
  | 'available_today'
  | 'limited_today'
  | 'fallback_today'
  | 'unavailable_today';
export type AiRemainingDailyAllowance =
  | 'not_tracked_locally'
  | 'available'
  | 'limited'
  | 'exhausted';

export interface AiRequestPolicy {
  requestedMode: AiMode;
  effectiveMode: AiMode;
  requestedFeatureBucket: AiFeatureBucket;
  resolvedFeatureBucket: AiFeatureBucket;
  status: AiPolicyStatus;
  accessResolution: AiAccessResolution;
  budgetClass: AiBudgetClass;
  downgradeAllowed: boolean;
  fallbackMode: AiMode | null;
  requiredPlan: Tier;
  currentPlan: Tier;
  policyReason: string;
  blockReason: string | null;
  downgradeReason: string | null;
  dailyCapScope: 'daily_member_allowance';
  dailyUsageClass: AiDailyUsageClass;
  dailyAllowanceState: AiDailyAllowanceState;
  remainingDailyAllowance: AiRemainingDailyAllowance;
  resetAt: 'local_midnight';
  borrowFromSharedPool: boolean;
  preservesProtectedBuckets: boolean;
  preservedAllowanceNotice: string | null;
  includedAccess: 'included_today' | 'included_limited' | 'included_exhausted';
  payPerUseAllowed: boolean;
  paidOverrideEligible: boolean;
  purchaseFallbackAllowed: boolean;
  purchaseReason: string | null;
  purchaseOfferType: 'one_off_ai_top_up' | 'premium_analysis_pass' | null;
  monetizationPath:
    | 'included_membership'
    | 'downgraded_included'
    | 'membership_upgrade'
    | 'pay_per_use'
    | 'hybrid_choice'
    | 'blocked';
  upgradeRecommended: boolean;
  upgradeHint: string | null;
}

export interface EvidenceAwareLocalContext {
  local_date: string;
  readiness: {
    level: DailyCoachingBrief['readiness'];
    headline: string;
    suggested_intensity: DailyCoachingBrief['suggested_intensity'];
    plan_hint: string | null;
    reasons: string[];
  };
  recovery: {
    whoop_recovery: number | null;
    sleep_hours: number | null;
    resting_hr: number | null;
    daily_strain: number | null;
    hrv_ms: number | null;
  };
  training_summary: {
    sessions_7d: number;
    hard_sessions_3d: number;
    grappling_sessions_7d: number;
    last_session:
      | {
          date: string;
          type: string;
          intensity: string;
          duration_min: number;
        }
      | null;
  };
  preferences: {
    goal: CoachingPreferences['goal'];
    recovery_conservatism: CoachingPreferences['recovery_conservatism'];
    tone: CoachingPreferences['tone'];
    sessions_planned_today: number;
    enabled_sessions_7d: number;
  };
  coaching_context: {
    local_coaching_summary: string | null;
    local_grappling_focus: string | null;
    recent_ai_payload_generated_at: string | null;
  };
  adherence: {
    latest_recommendation_feedback:
      | {
          date: string;
          followed: RecommendationFeedback['followed'];
          accuracy: number;
          usefulness: number;
        }
      | null;
    latest_checkin:
      | {
          training_date: string;
          recovery_feel: NextDayCheckin['recovery_feel'];
          recommendation_accuracy: NextDayCheckin['recommendation_accuracy'];
          injury_flag: boolean;
        }
      | null;
  };
  progress_summary: {
    drilling: number;
    learned: number;
    tracking: number;
    recent_focus_positions: string[];
  };
  nutrition_summary: {
    date: string | null;
    source: string | null;
    confirmed: boolean;
    calories_kcal: number | null;
    protein_g: number | null;
    carbs_g: number | null;
    fat_g: number | null;
    fibre_g: number | null;
    water_ml: number | null;
    body_weight_kg: number | null;
    missing_fields: string[];
    targets: {
      calories_kcal: number | null;
      protein_g: number | null;
      water_ml: number | null;
    } | null;
  } | null;
  /** App-owned normalized analysis. Device-agnostic. Coach should
   *  reason over this layer rather than raw vendor recovery/strain
   *  scores. Vendor scores are inputs — not the whole brain. */
  app_athlete_state: import('./app-athlete-state').AppAthleteState | null;
}

export interface EvidenceAwareAiRequest {
  mode: 'non_technique_ai';
  ai_mode: AiMode;
  question: string;
  topic: EvidenceAwareTopic;
  science_required: true;
  include_user_pattern_data: true;
  include_internal_context: true;
  include_local_app_context: true;
  requested_grounding: Array<
    'science' | 'user_patterns' | 'internal_context' | 'app_context'
  >;
  policy: AiRequestPolicy;
  local_context: EvidenceAwareLocalContext;
}

export interface BuildEvidenceAwareAiRequestInputs {
  question: string | null;
  topic: EvidenceAwareTopic;
  requestedMode: AiMode;
  currentPlan: Tier;
  downgradeAllowed: boolean;
  todayIsoDate: string;
  brief: DailyCoachingBrief;
  whoopDay: {
    recovery_score?: number | null;
    sleep_hours?: number | null;
    resting_hr?: number | null;
    daily_strain?: number | null;
    hrv_ms?: number | null;
  } | null;
  sessions: TrainingSession[];
  preferences: CoachingPreferences;
  aiPayload: AIPayload | null;
  coaching: CoachingResponse | null;
  latestRecommendationFeedback: RecommendationFeedback | null;
  latestCheckin: NextDayCheckin | null;
  progressMap: Record<string, ProgressStatus>;
  updatedAtMap: Record<string, string>;
  nutritionToday?: {
    date: string;
    source: string;
    confirmed: boolean;
    calories_kcal: number | null;
    protein_g: number | null;
    carbs_g: number | null;
    fat_g: number | null;
    fibre_g: number | null;
    water_ml: number | null;
    body_weight_kg?: number | null;
    missingFields?: string[];
  } | null;
  nutritionTargets?: {
    calories_kcal: number | null;
    protein_g: number | null;
    water_ml: number | null;
  } | null;
  appAthleteState?: import('./app-athlete-state').AppAthleteState | null;
}

export interface EvidenceAwareAiRequestPacketResult {
  request: EvidenceAwareAiRequest;
  text: string;
  policy: AiRequestPolicy;
}

const MODE_REQUIRED_PLAN: Record<AiMode, Tier> = {
  standard: 'free',
  evidence: minimumTierFor('hosted_ai_coaching'),
  premium_research: minimumTierFor('advanced_ai_insights'),
};

const MODE_BUDGET_CLASS: Record<AiMode, AiBudgetClass> = {
  standard: 'safe',
  evidence: 'moderate',
  premium_research: 'premium',
};

const MODE_DAILY_USAGE_CLASS: Record<AiMode, AiDailyUsageClass> = {
  standard: 'daily_standard',
  evidence: 'daily_evidence',
  premium_research: 'daily_premium',
};

function featureBucketForRequest(
  topic: EvidenceAwareTopic,
  mode: AiMode,
): AiFeatureBucket {
  if (mode === 'premium_research') return 'advanced_analysis';
  if (
    topic === 'recovery' ||
    topic === 'adherence' ||
    topic === 'habit_building'
  ) {
    return 'habit_recovery';
  }
  return mode === 'evidence' ? 'advanced_analysis' : 'core_coaching';
}

function payPerUseAllowedForRequest(
  requestedFeatureBucket: AiFeatureBucket,
  requestedMode: AiMode,
): boolean {
  if (requestedMode === 'standard') return false;
  return requestedFeatureBucket === 'advanced_analysis';
}

const TIER_ORDER: Tier[] = ['free', 'low_cost', 'pro', 'ai_premium'];

function tierAtLeast(current: Tier, required: Tier): boolean {
  return TIER_ORDER.indexOf(current) >= TIER_ORDER.indexOf(required);
}

function resolveAiRequestPolicy(args: {
  topic: EvidenceAwareTopic;
  requestedMode: AiMode;
  currentPlan: Tier;
  downgradeAllowed: boolean;
}): AiRequestPolicy {
  const { topic, requestedMode, currentPlan, downgradeAllowed } = args;
  const requiredPlan = MODE_REQUIRED_PLAN[requestedMode];
  const requestedFeatureBucket = featureBucketForRequest(topic, requestedMode);
  const payPerUseAllowed = payPerUseAllowedForRequest(
    requestedFeatureBucket,
    requestedMode,
  );
  if (tierAtLeast(currentPlan, requiredPlan)) {
    const resolvedFeatureBucket = featureBucketForRequest(topic, requestedMode);
    return {
      requestedMode,
      effectiveMode: requestedMode,
      requestedFeatureBucket,
      resolvedFeatureBucket,
      status: 'allowed',
      accessResolution: 'included',
      budgetClass: MODE_BUDGET_CLASS[requestedMode],
      downgradeAllowed,
      fallbackMode: null,
      requiredPlan,
      currentPlan,
      policyReason:
        requestedMode === 'standard'
          ? 'Using standard coach mode.'
          : requestedMode === 'evidence'
            ? 'Using evidence-aware coaching mode.'
            : 'Using premium research mode.',
      blockReason: null,
      downgradeReason: null,
      dailyCapScope: 'daily_member_allowance',
      dailyUsageClass: MODE_DAILY_USAGE_CLASS[requestedMode],
      dailyAllowanceState:
        requestedMode === 'standard' ? 'available_today' : 'limited_today',
      remainingDailyAllowance: 'not_tracked_locally',
      resetAt: 'local_midnight',
      borrowFromSharedPool: requestedMode !== 'standard',
      preservesProtectedBuckets: requestedMode !== 'standard',
      preservedAllowanceNotice:
        requestedMode === 'standard'
          ? null
          : 'Core daily coaching can stay protected even when advanced analysis is limited.',
      includedAccess:
        requestedMode === 'standard' ? 'included_today' : 'included_limited',
      payPerUseAllowed,
      paidOverrideEligible: false,
      purchaseFallbackAllowed: false,
      purchaseReason: null,
      purchaseOfferType: null,
      monetizationPath: 'included_membership',
      upgradeRecommended: requestedMode !== 'standard',
      upgradeHint:
        requestedMode === 'premium_research'
          ? 'Upgrade for more daily premium AI access.'
          : requestedMode === 'evidence'
            ? 'Upgrade for more daily evidence-aware access.'
            : null,
    };
  }

  if (downgradeAllowed) {
    const fallbackMode: AiMode =
      requestedMode === 'premium_research' ? 'evidence' : 'standard';
    const fallbackRequiredPlan = MODE_REQUIRED_PLAN[fallbackMode];
    if (tierAtLeast(currentPlan, fallbackRequiredPlan)) {
      const resolvedFeatureBucket = featureBucketForRequest(topic, fallbackMode);
      return {
        requestedMode,
        effectiveMode: fallbackMode,
        requestedFeatureBucket,
        resolvedFeatureBucket,
        status: 'downgraded',
        accessResolution: payPerUseAllowed ? 'pay_per_use_available' : 'downgraded',
        budgetClass: MODE_BUDGET_CLASS[fallbackMode],
        downgradeAllowed,
        fallbackMode,
        requiredPlan,
        currentPlan,
        policyReason: `Requested ${requestedMode.replace('_', ' ')} mode, using ${fallbackMode.replace('_', ' ')} mode instead.`,
        blockReason: null,
        downgradeReason: `${requestedMode === 'premium_research' ? 'Premium research mode' : 'Evidence-aware mode'} is unavailable on the current plan.`,
        dailyCapScope: 'daily_member_allowance',
        dailyUsageClass: MODE_DAILY_USAGE_CLASS[fallbackMode],
        dailyAllowanceState: 'fallback_today',
        remainingDailyAllowance: 'not_tracked_locally',
        resetAt: 'local_midnight',
        borrowFromSharedPool: false,
        preservesProtectedBuckets: true,
        preservedAllowanceNotice:
          'Advanced analysis can downgrade to preserve protected coaching access for today.',
        includedAccess: 'included_exhausted',
        payPerUseAllowed,
        paidOverrideEligible: payPerUseAllowed,
        purchaseFallbackAllowed: payPerUseAllowed,
        purchaseReason: payPerUseAllowed
          ? `Today's included ${requestedMode === 'premium_research' ? 'premium analysis' : 'advanced analysis'} is unavailable on the current plan or protected daily allowance.`
          : null,
        purchaseOfferType:
          requestedMode === 'premium_research'
            ? 'premium_analysis_pass'
            : payPerUseAllowed
              ? 'one_off_ai_top_up'
              : null,
        monetizationPath: payPerUseAllowed
          ? 'hybrid_choice'
          : 'downgraded_included',
        upgradeRecommended: true,
        upgradeHint: `Upgrade for more daily ${requestedMode === 'premium_research' ? 'premium' : 'evidence-aware'} AI access.`,
      };
    }
  }

  return {
    requestedMode,
    effectiveMode: 'standard',
    requestedFeatureBucket,
    resolvedFeatureBucket: 'core_coaching',
    status: 'blocked',
    accessResolution: payPerUseAllowed ? 'pay_per_use_available' : 'upgrade_required',
    budgetClass: 'safe',
    downgradeAllowed,
    fallbackMode: downgradeAllowed ? 'standard' : null,
    requiredPlan,
    currentPlan,
    policyReason: `${requestedMode.replace('_', ' ')} mode is blocked by the current plan and budget policy.`,
    blockReason:
      requestedMode === 'premium_research'
        ? 'Premium research mode requires AI Premium access.'
        : 'Evidence-aware mode requires AI Premium access.',
    downgradeReason: downgradeAllowed
      ? 'Fallback is available, but no lower paid mode is allowed on this plan.'
      : null,
    dailyCapScope: 'daily_member_allowance',
    dailyUsageClass: MODE_DAILY_USAGE_CLASS.standard,
    dailyAllowanceState: 'unavailable_today',
    remainingDailyAllowance: 'not_tracked_locally',
    resetAt: 'local_midnight',
    borrowFromSharedPool: false,
    preservesProtectedBuckets: true,
    preservedAllowanceNotice:
      'Protected coaching access is kept separate from advanced analysis where policy allows.',
    includedAccess: 'included_exhausted',
    payPerUseAllowed,
    paidOverrideEligible: payPerUseAllowed,
    purchaseFallbackAllowed: payPerUseAllowed,
    purchaseReason: payPerUseAllowed
      ? `Included ${requestedMode === 'premium_research' ? 'premium analysis' : 'advanced analysis'} is unavailable here, but one-off paid access can be offered.`
      : null,
    purchaseOfferType:
      requestedMode === 'premium_research'
        ? 'premium_analysis_pass'
        : payPerUseAllowed
          ? 'one_off_ai_top_up'
          : null,
    monetizationPath: payPerUseAllowed ? 'hybrid_choice' : 'membership_upgrade',
    upgradeRecommended: true,
    upgradeHint: `Upgrade for more daily ${requestedMode === 'premium_research' ? 'premium' : 'evidence-aware'} AI access.`,
  };
}

export function previewAiRequestPolicy(args: {
  topic: EvidenceAwareTopic;
  requestedMode: AiMode;
  currentPlan: Tier;
  downgradeAllowed: boolean;
}): AiRequestPolicy {
  return resolveAiRequestPolicy(args);
}

export function buildDailyAiFeatureSummary(policy: AiRequestPolicy): string[] {
  const lines = ['Coaching available today'];
  if (policy.requestedFeatureBucket === 'advanced_analysis') {
    if (policy.status === 'allowed') {
      lines.push('Advanced analysis available today');
    } else {
      lines.push('Advanced analysis unavailable today');
      lines.push('Standard guidance still available');
    }
  } else if (policy.status === 'downgraded') {
    lines.push('Standard guidance still available');
  }
  if (policy.upgradeHint) lines.push('Upgrade for more daily AI across features');
  return lines;
}

function buildProgressSummary(
  progressMap: Record<string, ProgressStatus>,
  updatedAtMap: Record<string, string>,
): EvidenceAwareLocalContext['progress_summary'] {
  const counts = { drilling: 0, learned: 0, tracking: 0 };
  for (const status of Object.values(progressMap)) {
    if (status === 'drilling') counts.drilling += 1;
    else if (status === 'learned') counts.learned += 1;
    else if (status === 'tracking') counts.tracking += 1;
  }

  const recentFocusPositions = Array.from(
    new Set(
      Object.entries(updatedAtMap)
        .map(([key, iso]) => ({ parsed: parseProgressKey(key), ts: Date.parse(iso) }))
        .filter((entry) => entry.parsed && Number.isFinite(entry.ts))
        .sort((a, b) => b.ts - a.ts)
        .map((entry) =>
          entry.parsed?.kind === 'tech'
            ? entry.parsed.position
            : entry.parsed?.sourcePosition ?? null,
        )
        .filter((value): value is string => !!value)
        .slice(0, 3),
    ),
  );

  return { ...counts, recent_focus_positions: recentFocusPositions };
}

function countHardSessionsSince(
  sessions: TrainingSession[],
  todayIsoDate: string,
  windowDays: number,
): number {
  const floor = new Date(`${todayIsoDate}T00:00:00`);
  floor.setDate(floor.getDate() - windowDays);
  const floorIso = floor.toISOString().slice(0, 10);
  return sessions.filter(
    (session) =>
      session.date >= floorIso &&
      session.date <= todayIsoDate &&
      session.intensity === 'hard',
  ).length;
}

function countSessionsSince(
  sessions: TrainingSession[],
  todayIsoDate: string,
  windowDays: number,
): number {
  const floor = new Date(`${todayIsoDate}T00:00:00`);
  floor.setDate(floor.getDate() - windowDays);
  const floorIso = floor.toISOString().slice(0, 10);
  return sessions.filter(
    (session) => session.date >= floorIso && session.date <= todayIsoDate,
  ).length;
}

export function buildEvidenceAwareAiRequestPacket(
  inputs: BuildEvidenceAwareAiRequestInputs,
): EvidenceAwareAiRequestPacketResult {
  const question =
    inputs.question?.trim() ||
    'Given this context, what should I do next and why?';
  const sessionsPlannedToday = inputs.brief.planned_count ?? 0;
  const enabledSessions7d = Object.values(inputs.preferences.schedule).reduce(
    (sum, day) => sum + day.filter((session) => session.enabled).length,
    0,
  );
  const sessions7d = countSessionsSince(inputs.sessions, inputs.todayIsoDate, 7);
  const hardSessions3d = countHardSessionsSince(
    inputs.sessions,
    inputs.todayIsoDate,
    3,
  );
  const grapplingSessions7d = inputs.sessions.filter((session) => {
    if (session.date > inputs.todayIsoDate) return false;
    const floor = new Date(`${inputs.todayIsoDate}T00:00:00`);
    floor.setDate(floor.getDate() - 7);
    return (
      session.date >= floor.toISOString().slice(0, 10) &&
      session.type.toLowerCase().includes('grap')
    );
  }).length;
  const lastSession = [...inputs.sessions]
    .sort((a, b) => b.date.localeCompare(a.date))
    .at(0);
  const policy = resolveAiRequestPolicy({
    topic: inputs.topic,
    requestedMode: inputs.requestedMode,
    currentPlan: inputs.currentPlan,
    downgradeAllowed: inputs.downgradeAllowed,
  });
  const localContext: EvidenceAwareLocalContext = {
    local_date: inputs.todayIsoDate,
    readiness: {
      level: inputs.brief.readiness,
      headline: inputs.brief.headline,
      suggested_intensity: inputs.brief.suggested_intensity,
      plan_hint: inputs.brief.plan_hint ?? null,
      reasons: inputs.brief.reasons.slice(0, 3),
    },
    recovery: {
      whoop_recovery: inputs.whoopDay?.recovery_score ?? null,
      sleep_hours: inputs.whoopDay?.sleep_hours ?? null,
      resting_hr: inputs.whoopDay?.resting_hr ?? null,
      daily_strain: inputs.whoopDay?.daily_strain ?? null,
      hrv_ms: inputs.whoopDay?.hrv_ms ?? null,
    },
    training_summary: {
      sessions_7d: sessions7d,
      hard_sessions_3d: hardSessions3d,
      grappling_sessions_7d: grapplingSessions7d,
      last_session: lastSession
        ? {
            date: lastSession.date,
            type: lastSession.type,
            intensity: lastSession.intensity,
            duration_min: lastSession.duration_min,
          }
        : null,
    },
    preferences: {
      goal: inputs.preferences.goal,
      recovery_conservatism: inputs.preferences.recovery_conservatism,
      tone: inputs.preferences.tone,
      sessions_planned_today: sessionsPlannedToday,
      enabled_sessions_7d: enabledSessions7d,
    },
    coaching_context: {
      local_coaching_summary: inputs.coaching?.today_recommendation.detail ?? null,
      local_grappling_focus: inputs.coaching?.grappling.suggestion ?? null,
      recent_ai_payload_generated_at: inputs.aiPayload?.generated_at ?? null,
    },
    adherence: {
      latest_recommendation_feedback: inputs.latestRecommendationFeedback
        ? {
            date: inputs.latestRecommendationFeedback.date,
            followed: inputs.latestRecommendationFeedback.followed,
            accuracy: inputs.latestRecommendationFeedback.accuracy,
            usefulness: inputs.latestRecommendationFeedback.usefulness,
          }
        : null,
      latest_checkin: inputs.latestCheckin
        ? {
            training_date: inputs.latestCheckin.training_date,
            recovery_feel: inputs.latestCheckin.recovery_feel,
            recommendation_accuracy:
              inputs.latestCheckin.recommendation_accuracy,
            injury_flag: inputs.latestCheckin.injury_flag,
          }
        : null,
    },
    progress_summary: buildProgressSummary(
      inputs.progressMap,
      inputs.updatedAtMap,
    ),
    nutrition_summary: inputs.nutritionToday
      ? {
          date: inputs.nutritionToday.date,
          source: inputs.nutritionToday.source,
          confirmed: inputs.nutritionToday.confirmed,
          calories_kcal: inputs.nutritionToday.calories_kcal,
          protein_g: inputs.nutritionToday.protein_g,
          carbs_g: inputs.nutritionToday.carbs_g,
          fat_g: inputs.nutritionToday.fat_g,
          fibre_g: inputs.nutritionToday.fibre_g,
          water_ml: inputs.nutritionToday.water_ml,
          body_weight_kg: (inputs.nutritionToday as any).body_weight_kg ?? null,
          missing_fields: inputs.nutritionToday.missingFields ?? [],
          targets: inputs.nutritionTargets ?? null,
        }
      : null,
    app_athlete_state: inputs.appAthleteState ?? null,
  };

  const request: EvidenceAwareAiRequest = {
    mode: 'non_technique_ai',
    ai_mode: policy.effectiveMode,
    question,
    topic: inputs.topic,
    science_required: true,
    include_user_pattern_data: true,
    include_internal_context: true,
    include_local_app_context: true,
    requested_grounding: [
      'science',
      'user_patterns',
      'internal_context',
      'app_context',
    ],
    policy,
    local_context: localContext,
  };

  // Human-readable summary of the app-owned analysis layer. This is
  // what a human (or ChatGPT reading the shared message) will glance
  // at first — the full structured JSON is still appended below for
  // reliable parsing, but the header gives someone a quick read on
  // why the AI is about to answer a given way.
  const aas = localContext.app_athlete_state;
  const nativeHealthRole = aas ? aas.source_roles.native_health : null;
  const athleteSummary = aas && nativeHealthRole ? [
    '',
    'App-owned athlete analysis (device-agnostic):',
    `  Recovery: ${aas.recovery_context.band}${aas.recovery_context.score_0_100 != null ? ` (${aas.recovery_context.score_0_100}/100)` : ''} — ${aas.recovery_context.note}`,
    `  Load: ${aas.load_context.band} · ${aas.load_context.sessions_7d}/7d · ${aas.load_context.hard_sessions_3d} hard in 3d · ${aas.load_context.consecutive_hard_days} consecutive hard days`,
    `  Sleep: ${aas.sleep_adequacy.band}${aas.sleep_adequacy.hours_last_night != null ? ` (${aas.sleep_adequacy.hours_last_night.toFixed(1)}h)` : ''}`,
    `  Fueling: ${aas.fueling_adequacy.band}${aas.fueling_adequacy.calories_vs_target_pct != null ? ` (cal ${aas.fueling_adequacy.calories_vs_target_pct}% of target)` : ''}${aas.fueling_adequacy.protein_vs_target_pct != null ? ` · protein ${aas.fueling_adequacy.protein_vs_target_pct}%` : ''}`,
    `  Hydration: ${aas.hydration_adequacy.band}${aas.hydration_adequacy.water_ml_today != null ? ` (${aas.hydration_adequacy.water_ml_today}ml)` : ''}`,
    `  Acute fatigue: ${aas.acute_fatigue.band} — ${aas.acute_fatigue.note}`,
    `  Chronic load trend: ${aas.chronic_load_trend.direction}`,
    `  Confidence: ${aas.readiness_confidence.level} (${aas.readiness_confidence.value})${aas.readiness_confidence.reasons_for_low.length > 0 ? ` — missing: ${aas.readiness_confidence.reasons_for_low.join('; ')}` : ''}`,
    `  Recovery inputs used: ${aas.recovery_context.contributing_sources.join(', ') || 'none'}${aas.recovery_context.uses_vendor_score ? ' (incl. vendor score as one weighted input)' : ''}`,
    '',
    'Three-layer source roles (not rankings — different jobs):',
    `  ${nativeHealthRole.label}: ${nativeHealthRole.role}${nativeHealthRole.role === 'broad_baseline' ? ` · ${nativeHealthRole.history_depth_days} days of history` : ''}${nativeHealthRole.covers_today ? ' · covers today' : ''}`,
    `  WHOOP Direct: ${aas.source_roles.whoop_direct.role}${aas.source_roles.whoop_direct.latest_cycle_date ? ` · latest cycle ${aas.source_roles.whoop_direct.latest_cycle_date}` : ''}`,
    `  WHOOP export: ${aas.source_roles.whoop_csv.role}${aas.source_roles.whoop_csv.imported_rows ? ` · ${aas.source_roles.whoop_csv.imported_rows} rows` : ''}`,
    `  Role conventions: ${nativeHealthRole.label} = broad baseline + history; WHOOP Direct = authoritative live/current state; WHOOP export = optional deeper historical enrichment. All three coexist — none overrides the others. Today\u2019s scored state prefers WHOOP; days WHOOP missed fall back to ${nativeHealthRole.label}; long baselines use the full merged record.`,
  ].join('\n') : '';

  const text = [
    'Lauburu cost-aware non-technique AI request',
    '',
    'This is an app-generated request scaffold for broader coaching questions.',
    'Requested grounding: science, pooled user patterns, internal coaching context, local app context.',
    'This request includes policy gating for plan tier, budget class, and graceful downgrade behavior.',
    'Do not answer as technique instruction unless the user explicitly asks for technique content.',
    '',
    `Requested mode: ${policy.requestedMode}`,
    `Effective mode: ${policy.effectiveMode}`,
    `Policy status: ${policy.status}`,
    `Budget class: ${policy.budgetClass}`,
    `Policy note: ${policy.policyReason}`,
    athleteSummary,
    '',
    'Structured request:',
    JSON.stringify(request, null, 2),
  ].join('\n');

  return { request, text, policy };
}
