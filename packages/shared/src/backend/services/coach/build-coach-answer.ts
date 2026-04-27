/**
 * Coach answer builder — classifies a question, routes to domain,
 * and produces a typed answer card from the canonical ai-context.
 *
 * First-pass domains: HIIT, nutrition, recovery, training, general.
 * Uses seed-mode-safe rules — does not invent WHOOP-native readiness.
 *
 * Pure function. No network calls. No side effects.
 */

import type {
  CoachDomain,
  CoachAnswerResponse,
  CoachAnswerBody,
  CoachAnswerStatus,
  CoachConfidence,
} from '../../contracts/coach-answer.types';
import type { AthleteAiContextResponse, NutritionDailySummary } from '../../contracts/ai-context.types';
import type { DailyRefreshArtifact, WeeklySynthesisArtifact } from '../../contracts/refresh-artifacts.types';

// ---------------------------------------------------------------------------
// Question classification
// ---------------------------------------------------------------------------

const HIIT_KEYWORDS = ['hiit', 'interval', 'conditioning', 'assault bike', 'tabata', 'emom', 'amrap', 'cardio', 'sprint', 'watts', 'drop off', 'drop-off', 'fatigue', 'set compare', 'last time', 'heart rate higher', 'rower', 'bike'];
const NUTRITION_KEYWORDS = ['eat', 'food', 'calories', 'protein', 'carbs', 'fat', 'nutrition', 'diet', 'meal', 'macro', 'fuel', 'barcode', 'photo', 'cronometer', 'scanned'];
const RECOVERY_KEYWORDS = ['recovery', 'recovered', 'rest', 'sleep', 'hrv', 'resting heart', 'strain', 'readiness', 'tired', 'fatigued', 'whoop', 'day state', 'day score'];
const TRAINING_KEYWORDS = ['train', 'session', 'drill', 'grappling', 'rolling', 'sparring', 'lifting', 'weights', 'technique', 'plan'];
const SOURCE_STATUS_KEYWORDS = ['apple health', 'healthkit', 'health connect', 'android health', 'cronometer', 'polar', 'polar flow', 'polar via health connect', 'samsung', 'samsung health', 'galaxy watch', 'connected', 'data source', 'what data', 'missing data', 'what is missing', 'which source', 'what health data', 'what has health connect contributed', 'what should i track', 'how does my training look', 'training look today'];

function hasAny(text: string, keywords: string[]): boolean {
  return keywords.some((k) => text.includes(k));
}

function uniqueStrings(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.filter((value): value is string => typeof value === 'string' && value.length > 0))];
}

function classifyQuestion(question: string, topicHint?: string): { domain: CoachDomain; questionClass: string } {
  const q = question.toLowerCase();

  if (topicHint) {
    if (['hiit', 'conditioning'].includes(topicHint)) return { domain: 'hiit', questionClass: 'hiit_topic_hint' };
    if (['nutrition', 'diet'].includes(topicHint)) return { domain: 'nutrition', questionClass: 'nutrition_topic_hint' };
    if (['recovery'].includes(topicHint)) return { domain: 'recovery', questionClass: 'recovery_topic_hint' };
    if (['training', 'technique'].includes(topicHint)) return { domain: 'training', questionClass: 'training_topic_hint' };
  }

  if (HIIT_KEYWORDS.some((k) => q.includes(k))) return { domain: 'hiit', questionClass: 'hiit_keyword_match' };
  if (NUTRITION_KEYWORDS.some((k) => q.includes(k))) return { domain: 'nutrition', questionClass: 'nutrition_keyword_match' };
  if (RECOVERY_KEYWORDS.some((k) => q.includes(k))) return { domain: 'recovery', questionClass: 'recovery_keyword_match' };
  if (TRAINING_KEYWORDS.some((k) => q.includes(k))) return { domain: 'training', questionClass: 'training_keyword_match' };

  return { domain: 'general', questionClass: 'general_fallback' };
}

// ---------------------------------------------------------------------------
// Domain answer builders
// ---------------------------------------------------------------------------

function buildHiitAnswer(
  ctx: AthleteAiContextResponse,
  question: string,
): { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[] } {
  const daily = ctx.dailyArtifact as DailyRefreshArtifact | null;
  const safeFor = ctx.capability?.safeFor ?? [];
  const q = question.toLowerCase();
  const missingWhoop = ctx.capability?.missingWhoopNativeFields ?? [];
  const asksReadiness = hasAny(q, ['should i do hiit today', 'am i recovered enough', 'recovered enough', 'hrv', 'strain', 'readiness', 'ready for hiit', 'ready for', 'sprint today', 'go hard today']);
  const asksFormat = hasAny(q, ['format', 'protocol', 'tabata', 'emom', 'amrap', 'assault bike', 'bike', 'rower', 'zone 2', 'progression', 'regression', 'interval']);
  const asksSaferFallback = hasAny(q, ['safer', 'fallback', 'lower-risk', 'easier option', 'zone 2']);
  const asksProgress = hasAny(q, ['compare', 'last time', 'drop off', 'drop-off', 'fatigue', 'watts', 'heart rate higher', 'hr higher', 'set compare']);

  // Check if WHOOP-native READINESS fields (recovery, sleep, strain) are present.
  // Workouts being stale does not block readiness — only recovery/sleep/strain matter.
  // The liveReadiness object (from analyseReadiness()) provides a structured verdict
  // when a user has fresh direct WHOOP (bridge OR direct OAuth).
  const liveReadiness = (ctx as any).liveReadiness as {
    mode: 'live' | 'seed' | 'unavailable';
    level: 'green' | 'yellow' | 'red' | 'blocked';
    confidence: 'low' | 'medium' | 'high';
    interpretation: string;
    metrics: { recoveryScore: number | null; hrvMs: number | null; dailyStrain: number | null; sleepHours: number | null };
    guardrails: string[];
    missingness: string[];
    contextUsed: string[];
    sourceFields: string[];
  } | null | undefined;
  const readinessCriticalMissing = missingWhoop.filter(
    (f) => f === 'recovery' || f === 'sleep' || f === 'strain',
  );
  const hasLiveRecovery = (liveReadiness?.mode === 'live' && liveReadiness.level !== 'blocked')
    || (daily != null && readinessCriticalMissing.length === 0 && !ctx.seedMode);

  // HIIT progress questions — use recent workouts from ai-context
  if (asksProgress) {
    const hiitProgress = (ctx as any).hiitProgressSummary;
    const recentHIIT = (ctx as any).recentHIITWorkouts;
    if (!recentHIIT || recentHIIT.length === 0) {
      return {
        answer: {
          short: 'No HIIT workout history available yet.',
          why: 'Log a HIIT session first to enable set-to-set and session-to-session comparisons.',
          nextStep: 'Complete a workout with set data to start tracking HIIT progress.',
          missingnessNote: 'No HIIT workout records found.',
        },
        status: 'insufficient_data',
        confidence: 'low',
        sources: [],
        missingFields: ['hiit_workout_records'],
      };
    }
    const latest = recentHIIT[0];
    const parts: string[] = [`Latest: ${latest.protocolFormat} on ${latest.machineType}`];
    if (latest.avgWatts != null) parts.push(`${latest.avgWatts}W avg`);
    if (latest.totalCalories != null) parts.push(`${latest.totalCalories} cal`);
    if (hiitProgress?.wattsDropOffPct != null) parts.push(`drop-off: ${hiitProgress.wattsDropOffPct}%`);
    if (hiitProgress?.avgWattsDelta != null) parts.push(`vs last: ${hiitProgress.avgWattsDelta > 0 ? '+' : ''}${hiitProgress.avgWattsDelta}W`);
    return {
      answer: {
        short: parts.join(' · '),
        why: hiitProgress?.hrDriftPct != null ? `HR drift: ${hiitProgress.hrDriftPct}% across sets.` : 'Set-level detail available from workout records.',
        nextStep: 'Ask about a specific metric (watts, HR, drop-off) for more detail.',
        missingnessNote: latest.avgWatts == null ? 'Watts data not available — manual entry or machine connection needed.' : null,
      },
      status: 'answered',
      confidence: latest.avgWatts != null ? 'medium' : 'low',
      sources: ['hiit_workout_records'],
      missingFields: latest.avgWatts == null ? ['watts'] : [],
    };
  }

  if (asksReadiness && !hasLiveRecovery) {
    // ── Contextual readiness from hub data (HC / Samsung / Polar)
    // When no live WHOOP but Health Connect / Samsung / Polar hub data
    // is fresh, provide a useful contextual summary. Explicitly NOT a
    // clearance — just "here's what I can see from your connected hubs."
    const multiSrc = (ctx as any).multiSourceHealth;
    const hcInfo = multiSrc?.health_connect;
    const samsungInfo = multiSrc?.samsung_health_via_health_connect;
    const polarViaHcInfo = multiSrc?.polar_via_health_connect;
    const anyHubConnected = hcInfo?.status === 'fresh' || samsungInfo?.status === 'fresh' || polarViaHcInfo?.status === 'fresh';

    if (anyHubConnected) {
      // Use the structured contextualReadiness if available (preferred)
      const ctxReady = (ctx as any).contextualReadiness as {
        mode: 'contextual';
        level: 'looks_good' | 'moderate' | 'caution' | 'insufficient';
        confidence: 'low' | 'medium' | 'high';
        summary: string;
        signals: Array<{ domain: string; label: string; direction: string }>;
        gaps: string[];
        disclaimer: string;
        whoopWouldAdd: string[];
      } | null | undefined;

      if (ctxReady && ctxReady.level !== 'insufficient') {
        const levelAdvice =
          ctxReady.level === 'looks_good' ? 'Hub signals support training today. Use for moderate-to-hard sessions with your own judgment.' :
          ctxReady.level === 'moderate' ? 'Mixed hub signals — moderate training is reasonable, but listen to your body.' :
          'Multiple caution signals from your hubs — consider lighter training or active rest.';
        const signalSummary = ctxReady.signals.slice(0, 3).map(s => s.label).join(' · ');
        const gapNote = ctxReady.whoopWouldAdd.length > 0
          ? `Direct WHOOP would add: ${ctxReady.whoopWouldAdd.slice(0, 2).join(', ')}.`
          : '';
        return {
          answer: {
            short: `${ctxReady.summary} ${levelAdvice}`,
            why: signalSummary || 'Based on available hub data.',
            nextStep: gapNote || 'Keep logging. Ask about specific metrics for detail.',
            missingnessNote: `${ctxReady.disclaimer}${ctxReady.gaps.length > 0 ? ' Gaps: ' + ctxReady.gaps[0] : ''}`,
          },
          status: 'downgraded',
          confidence: ctxReady.confidence,
          sources: ['contextual_readiness_analysis', 'health_hub_data'],
          missingFields: ctxReady.whoopWouldAdd.length > 0 ? ['direct_whoop_for_deeper_readiness'] : [],
        };
      }

      // Fallback: simple hub summary when contextualReadiness not available
      const hubSources: string[] = [];
      if (hcInfo?.status === 'fresh') hubSources.push('Health Connect');
      if (samsungInfo?.status === 'fresh') hubSources.push('Samsung Health via HC');
      if (polarViaHcInfo?.status === 'fresh') hubSources.push('Polar via HC');
      const norm = ctx.normalizedDay;
      const sleepNote = norm?.totalSleepHours != null ? `Sleep: ${norm.totalSleepHours.toFixed(1)}h. ` : '';
      const rhrNote = norm?.restingHrBpm != null ? `Resting HR: ${norm.restingHrBpm} bpm. ` : '';
      const stepsNote = (norm as any)?.stepCount != null ? `Steps today: ${(norm as any).stepCount}. ` : '';
      const dataLine = `${sleepNote}${rhrNote}${stepsNote}`.trim() || 'Some data available.';

      return {
        answer: {
          short: `Contextual readiness from ${hubSources.join(' + ')}: ${dataLine} This is training context — not a direct readiness clearance.`,
          why: 'Health hubs provide sleep, heart rate, workout, and activity context. They cannot replace direct WHOOP for deeper readiness.',
          nextStep: 'For deeper readiness, connect WHOOP directly. Meanwhile, use this context for training decisions.',
          missingnessNote: 'Contextual readiness only — no direct WHOOP recovery/HRV/strain.',
        },
        status: 'downgraded',
        confidence: 'medium',
        sources: ['contextual_hub_readiness', ...hubSources.map(s => s.toLowerCase().replace(/ /g, '_'))],
        missingFields: ['direct_whoop_for_deeper_readiness'],
      };
    }

    // No hub data available — fall back to flat rejection.
    const seedRecoveryVal = ctx.normalizedDay?.recoveryScore;
    const seedContext = seedRecoveryVal != null
      ? ` Seed recovery is ${Math.round(seedRecoveryVal)}% — use as context only.`
      : '';
    return {
      answer: {
        short: ctx.seedMode
          ? `I cannot clear you for HIIT from seed-mode data alone.${seedContext}`
          : 'WHOOP-native readiness fields are incomplete — cannot clear for high intensity.',
        why: 'Direct readiness clearance requires fresh live recovery, HRV, and strain — not seed snapshots.',
        nextStep: 'Ask for a safer conditioning option or a grappling-friendly interval format instead.',
        missingnessNote: 'Live readiness unavailable: needs fresh recovery, HRV, strain.',
      },
      status: 'downgraded',
      confidence: 'low',
      sources: seedRecoveryVal != null ? ['normalized_daily_metrics'] : ['daily_refresh_artifact'],
      missingFields: ['live_recovery', 'live_hrv', 'live_strain'],
    };
  }

  // When liveReadiness is in 'live' mode and the user is asking about
  // readiness, use its structured interpretation directly — it has
  // already run the full analyseReadiness() pipeline including
  // recovery/HRV/strain evaluation, support context, and guardrails.
  if (asksReadiness && liveReadiness?.mode === 'live' && liveReadiness.level !== 'blocked') {
    const m = liveReadiness.metrics;
    return {
      answer: {
        short: liveReadiness.interpretation,
        why: liveReadiness.contextUsed.length > 0
          ? `Support context: ${liveReadiness.contextUsed.slice(0, 2).join(' ')}`
          : `Based on direct WHOOP fields: ${liveReadiness.sourceFields.join(', ')}.`,
        nextStep:
          liveReadiness.level === 'green' ? 'You\'re cleared for higher-intensity HIIT today.' :
          liveReadiness.level === 'yellow' ? 'Moderate conditioning is fine; avoid maximal efforts.' :
          'Keep it light — active rest or zone 2 only.',
        missingnessNote: liveReadiness.missingness.length > 0
          ? `Still missing: ${liveReadiness.missingness.join(', ')}. ${liveReadiness.guardrails[0]}`
          : liveReadiness.guardrails[0],
      },
      status: 'answered',
      confidence: liveReadiness.confidence,
      sources: ['live_readiness_analysis', 'whoop_direct'],
      missingFields: liveReadiness.missingness,
    };
  }

  if (!daily) {
    return {
      answer: {
        short: 'HIIT guidance is available but today\'s daily artifact is missing.',
        why: 'Without a current daily refresh, intensity recommendations are less precise.',
        nextStep: 'Try a moderate-intensity session or wait for today\'s data to sync.',
        missingnessNote: 'No daily refresh artifact for today.',
      },
      status: 'downgraded',
      confidence: 'low',
      sources: ['weekly_synthesis'],
      missingFields: ['daily_refresh_artifact'],
    };
  }

  const gate = daily.sessionGate;
  const risk = daily.rollingRiskLevel;
  const dayState = daily.dayState;
  const dailyMissing = uniqueStrings(daily.coverage?.missingFields ?? []);

  if (!hasLiveRecovery && (asksFormat || asksSaferFallback)) {
    const saferFormat = asksSaferFallback
      ? 'Zone 2 bike, row, or brisk incline walk for 20-30 minutes.'
      : gate.maxIntensity === 'hard'
        ? '6-10 rounds of 30s hard / 90s easy on a bike or rower.'
      : gate.maxIntensity === 'moderate'
          ? '6-8 rounds of 20s strong / 100s easy, or tempo intervals below all-out pace.'
          : 'Zone 2 only today, not HIIT.';
    return {
      answer: {
        short: saferFormat,
        why: `Seed mode can support format guidance, but not direct readiness clearance. ${daily.primaryRecommendation.guidance}`,
        nextStep: gate.maxIntensity === 'light' || gate.maxIntensity === 'rest_only'
          ? 'Keep conditioning conversational today.'
          : `Stay within ${gate.maxIntensity} intensity and stop if the effort drifts into maximal sprinting.`,
        missingnessNote: missingWhoop.length > 0 ? `Missing: ${missingWhoop.join(', ')}` : null,
      },
      status: 'downgraded',
      confidence: 'low',
      sources: ['daily_refresh_artifact'],
      missingFields: uniqueStrings([...missingWhoop, ...dailyMissing]),
    };
  }

  if (gate.gate === 'blocked' || dayState === 'blocked') {
    return {
      answer: {
        short: 'Rest is recommended today. Skip HIIT.',
        why: `Rolling risk is ${risk}. ${daily.primaryRecommendation.reasons.slice(0, 2).join('. ')}.`,
        nextStep: 'Focus on mobility or a light walk instead.',
        missingnessNote: null,
      },
      status: 'answered',
      confidence: 'medium',
      sources: ['daily_refresh_artifact'],
      missingFields: dailyMissing,
    };
  }

  if (dayState === 'red') {
    return {
      answer: {
        short: 'Keep conditioning very light today.',
        why: `Day state is red (score ${daily.dayScore}). ${daily.keyDrivers.slice(0, 2).join('. ')}.`,
        nextStep: 'Zone 2 only — easy bike or walk. No intervals.',
        missingnessNote: ctx.seedMode ? 'Based on seed data, not live WHOOP.' : null,
      },
      status: 'answered',
      confidence: ctx.seedMode ? 'low' : 'medium',
      sources: ['daily_refresh_artifact'],
      missingFields: uniqueStrings([...dailyMissing, ...(ctx.seedMode ? missingWhoop : [])]),
    };
  }

  if (dayState === 'yellow') {
    return {
      answer: {
        short: 'Moderate HIIT is fine. Avoid maximal efforts.',
        why: `Day state is yellow (score ${daily.dayScore}). ${daily.primaryRecommendation.guidance}`,
        nextStep: `Allowed: ${gate.allowedTypes.slice(0, 3).join(', ')}. Max intensity: ${gate.maxIntensity}.`,
        missingnessNote: ctx.seedMode ? 'Based on seed data, not live WHOOP.' : null,
      },
      status: 'answered',
      confidence: ctx.seedMode ? 'low' : 'medium',
      sources: ['daily_refresh_artifact'],
      missingFields: uniqueStrings([...dailyMissing, ...(ctx.seedMode ? missingWhoop : [])]),
    };
  }

  return {
    answer: {
      short: 'Green light for hard conditioning today.',
      why: `Day state is green (score ${daily.dayScore}). Recovery supports high-intensity work.`,
      nextStep: `Go for it: ${gate.allowedTypes.slice(0, 4).join(', ')}. Allowed intensity: ${gate.maxIntensity}.`,
      missingnessNote: ctx.seedMode ? 'Based on seed data, not live WHOOP.' : null,
    },
    status: 'answered',
    confidence: ctx.seedMode ? 'medium' : 'high',
    sources: ['daily_refresh_artifact'],
    missingFields: uniqueStrings([...dailyMissing, ...(ctx.seedMode ? missingWhoop : [])]),
  };
}

function buildNutritionAnswer(
  ctx: AthleteAiContextResponse,
  question: string,
): { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[] } {
  const nutr = ctx.nutritionDailySummary;
  const q = question.toLowerCase();
  const nutritionSources = (ctx as any).nutritionSources as string[] | undefined;

  // Cronometer-specific questions
  const asksCronometer = hasAny(q, ['cronometer', 'is cronometer connected', 'cronometer connected', 'cronometer log', 'cronometer sync']);
  if (asksCronometer) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const cronometerStatus = multiSrc?.cronometer?.status ?? 'not_connected';
    const cronometerConnected = cronometerStatus === 'fresh' || cronometerStatus === 'stale';

    if (!cronometerConnected) {
      const cronometerReason = multiSrc?.cronometer?.reason as string | undefined;
      // Detect auth states from the reason prefix
      const isAuthRequired = cronometerReason?.includes('auth_required');
      const isAuthExpired = cronometerReason?.includes('auth_expired');

      const statusLabel = isAuthExpired
        ? 'Cronometer authorization has expired.'
        : isAuthRequired
          ? 'Cronometer credentials are configured but the API is not yet operational.'
          : 'Cronometer is not connected.';
      const whyLabel = isAuthExpired
        ? 'The Cronometer session token expired. Re-authenticate to resume syncing.'
        : isAuthRequired
          ? 'Credentials are present but Cronometer API access is not yet available for third-party apps.'
          : 'Cronometer does not currently offer a public API for third-party apps.';
      const nextLabel = isAuthExpired
        ? 'Re-authenticate with Cronometer, or use manual entry / barcode scan.'
        : 'Use manual nutrition entry, barcode scanning, or AI photo logging instead.';

      return {
        answer: {
          short: statusLabel,
          why: whyLabel,
          nextStep: nextLabel,
          missingnessNote: `Cronometer: ${isAuthExpired ? 'auth_expired' : isAuthRequired ? 'auth_required' : 'not_connected'}.`,
        },
        status: 'answered',
        confidence: 'high',
        sources: ['source_health_records'],
        missingFields: ['cronometer_connection'],
      };
    }

    // Cronometer is connected — report what it logged
    if (nutr && nutr.coverage !== 'none') {
      const parts: string[] = [];
      if (nutr.calories != null) parts.push(`${Math.round(nutr.calories)} kcal`);
      if (nutr.proteinGrams != null) parts.push(`${Math.round(nutr.proteinGrams)}g protein`);
      if (nutr.carbGrams != null) parts.push(`${Math.round(nutr.carbGrams)}g carbs`);
      if (nutr.fatGrams != null) parts.push(`${Math.round(nutr.fatGrams)}g fat`);
      const missing = nutr.missingFields;
      return {
        answer: {
          short: `Cronometer logged: ${parts.join(', ')}.`,
          why: missing.length > 0
            ? `Partial: ${missing.join(', ')} not logged in Cronometer.`
            : 'Full macro coverage from Cronometer.',
          nextStep: missing.length > 0
            ? `Log ${missing.join(' and ')} to complete the picture.`
            : 'Nutrition tracking is complete for today.',
          missingnessNote: missing.length > 0 ? `Missing: ${missing.join(', ')}` : null,
        },
        status: 'answered',
        confidence: 'medium',
        sources: ['cronometer', 'normalized_daily_metrics'],
        missingFields: missing,
      };
    }

    return {
      answer: {
        short: 'Cronometer is connected but no data logged for today.',
        why: 'The connection is active but Cronometer has no entries for this date.',
        nextStep: 'Log meals in Cronometer or use manual entry here.',
        missingnessNote: 'Connected but no data for today.',
      },
      status: 'downgraded',
      confidence: 'medium',
      sources: ['cronometer', 'source_health_records'],
      missingFields: ['nutrition_log'],
    };
  }

  // General nutrition source questions
  if (hasAny(q, ['barcode', 'scanned', 'photo', 'where is my nutrition', 'nutrition source', 'what data is confirmed', 'confirmed nutrition'])) {
    const sources = nutritionSources ?? [];
    if (sources.length === 0) {
      return {
        answer: {
          short: 'No nutrition data logged today.',
          why: 'Nutrition data comes from manual entry, barcode scans (confirmed only), Cronometer, or AI photo estimates (confirmed only). None are active.',
          nextStep: 'Log food manually or scan a barcode to start building nutrition data.',
          missingnessNote: 'No active nutrition sources.',
        },
        status: 'insufficient_data',
        confidence: 'medium',
        sources: ['source_health_records'],
        missingFields: ['nutrition_source'],
      };
    }
    return {
      answer: {
        short: `Active nutrition sources: ${sources.join(', ')}.`,
        why: 'Only confirmed entries enter the nutrition total. Unconfirmed barcode/photo proposals do not count until reviewed.',
        nextStep: sources.includes('cronometer') ? 'Cronometer is syncing live.' : 'Scan a barcode or log manually to add more entries.',
        missingnessNote: null,
      },
      status: 'answered',
      confidence: 'medium',
      sources: ['source_health_records', 'normalized_daily_metrics'],
      missingFields: [],
    };
  }

  // Completeness / missingness questions
  if (hasAny(q, ['complete', 'missing', 'what is missing', 'log complete', 'nutrition complete', 'all logged'])) {
    if (!nutr || nutr.coverage === 'none') {
      return {
        answer: {
          short: 'No nutrition data logged today.',
          why: 'Log meals via manual entry, barcode scan, or Cronometer to start building nutrition context.',
          nextStep: 'Open the Nutrition card and log your first meal.',
          missingnessNote: 'No nutrition data at all.',
        },
        status: 'insufficient_data',
        confidence: 'high',
        sources: [],
        missingFields: ['calories', 'protein', 'carbs', 'fat'],
      };
    }
    const missing = nutr.missingFields;
    if (missing.length === 0) {
      return {
        answer: {
          short: 'Nutrition log is complete for today.',
          why: `Full macro coverage: calories, protein, carbs, fat.${nutr.sourceState ? ` Source: ${nutr.sourceState}.` : ''}`,
          nextStep: 'All macros are logged. You can update individual entries if needed.',
          missingnessNote: null,
        },
        status: 'answered',
        confidence: 'high',
        sources: ['normalized_daily_metrics'],
        missingFields: [],
      };
    }
    return {
      answer: {
        short: `Nutrition log is partial. Missing: ${missing.join(', ')}.`,
        why: `${4 - missing.length} of 4 core macros logged.${nutr.sourceState ? ` Source: ${nutr.sourceState}.` : ''}`,
        nextStep: `Log ${missing.join(' and ')} to complete the picture.`,
        missingnessNote: `Missing: ${missing.join(', ')}`,
      },
      status: 'downgraded',
      confidence: 'medium',
      sources: ['normalized_daily_metrics'],
      missingFields: missing,
    };
  }

  if (hasAny(q, ['hurt my recovery', 'help my recovery', 'recovery', 'why was recovery low', 'did nutrition affect'])) {
    return {
      answer: {
        short: 'I cannot claim a nutrition-to-recovery cause from the current data.',
        why: 'Nutrition coverage can summarize what was logged, but it does not establish causality for recovery outcomes.',
        nextStep: 'Ask for today\'s intake summary, biggest macro gap, or training-fueling context instead.',
        missingnessNote: 'Causal recovery attribution is not supported here.',
      },
      status: 'insufficient_data',
      confidence: 'low',
      sources: ['normalized_daily_metrics'],
      missingFields: ['causal_recovery_evidence'],
    };
  }

  if (!nutr || nutr.coverage === 'none') {
    return {
      answer: {
        short: 'No nutrition data is logged for today.',
        why: 'Nutrition context requires confirmed food log entries from manual input, barcode scan, or Cronometer.',
        nextStep: 'Log today\'s meals to get nutrition-aware coaching.',
        missingnessNote: 'No nutrition data available. Log food to enable this.',
      },
      status: 'insufficient_data',
      confidence: 'low',
      sources: [],
      missingFields: ['nutrition_log'],
    };
  }

  const missing = nutr.missingFields;
  const isPartial = nutr.coverage === 'partial';

  const parts: string[] = [];
  if (nutr.calories != null) parts.push(`${Math.round(nutr.calories)} kcal`);
  if (nutr.proteinGrams != null) parts.push(`${Math.round(nutr.proteinGrams)}g protein`);
  if (nutr.carbGrams != null) parts.push(`${Math.round(nutr.carbGrams)}g carbs`);
  if (nutr.fatGrams != null) parts.push(`${Math.round(nutr.fatGrams)}g fat`);

  const sourceNote = nutritionSources?.length
    ? ` Source: ${nutritionSources.join(', ')}.`
    : '';

  return {
    answer: {
      short: `Today's intake: ${parts.join(', ')}.`,
      why: isPartial
        ? `Partial nutrition data — ${missing.join(', ')} not logged.${sourceNote}`
        : `Full macro coverage from today's food log.${sourceNote}`,
      nextStep: isPartial
        ? `Log ${missing.join(' and ')} for a complete picture.`
        : 'On track. Check protein target vs training load if relevant.',
      missingnessNote: isPartial ? `Missing: ${missing.join(', ')}` : null,
    },
    status: isPartial ? 'downgraded' : 'answered',
    confidence: isPartial ? 'low' : 'medium',
    sources: ['normalized_daily_metrics'],
    missingFields: isPartial ? missing : [],
  };
}

function buildRecoveryAnswer(
  ctx: AthleteAiContextResponse,
): { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[] } {
  const missingWhoop = ctx.capability?.missingWhoopNativeFields ?? [];
  const seedRecovery = ctx.normalizedDay?.recoveryScore ?? null;
  const seedHrv = ctx.normalizedDay?.hrvMs ?? null;
  const seedSleep = ctx.normalizedDay?.totalSleepHours ?? null;

  if (ctx.capability?.notSafeFor?.includes('display_recovery_score_as_live')) {
    // Seed WHOOP data may still be available — show it as context
    if (seedRecovery != null) {
      const parts: string[] = [`Seed recovery: ${Math.round(seedRecovery)}%`];
      if (seedHrv != null) parts.push(`HRV ${Math.round(seedHrv)}ms`);
      if (seedSleep != null) parts.push(`sleep ${seedSleep.toFixed(1)}h`);
      return {
        answer: {
          short: `Your seed WHOOP snapshot shows ${Math.round(seedRecovery)}% recovery.`,
          why: `${parts.join(' · ')}. This is seed-backed context, not fresh live readiness.`,
          nextStep: 'Use as context only. Direct WHOOP readiness interpretation requires fresh live fields.',
          missingnessNote: 'Live readiness unavailable: needs fresh recovery, HRV, strain, and sleep.',
        },
        status: 'downgraded',
        confidence: 'medium',
        sources: ['normalized_daily_metrics'],
        missingFields: ['live_recovery', 'live_hrv', 'live_strain'],
      };
    }
    return {
      answer: {
        short: 'No WHOOP recovery data available.',
        why: 'WHOOP-native recovery fields are missing. No seed or live data found.',
        nextStep: 'Use the weekly trend summary for directional guidance instead.',
        missingnessNote: 'Missing: live recovery, HRV, strain.',
      },
      status: 'downgraded',
      confidence: 'low',
      sources: ctx.weeklyArtifact ? ['weekly_synthesis_artifact'] : [],
      missingFields: ['live_recovery', 'live_hrv', 'live_strain'],
    };
  }

  const daily = ctx.dailyArtifact as DailyRefreshArtifact | null;
  const weekly = ctx.weeklyArtifact as WeeklySynthesisArtifact | null;

  if (!daily && weekly) {
    // Fall back to weekly trends instead of insufficient_data
    return {
      answer: {
        short: weekly.dominantDriver
          ? `Recovery trend this week: ${weekly.dominantDriver}.`
          : `${weekly.dailyArtifactCount} days tracked this week.`,
        why: `${weekly.improved?.length ? `Improved: ${weekly.improved[0]}.` : ''}${weekly.worsened?.length ? ` Watch: ${weekly.worsened[0]}.` : ''} No daily artifact for today.`,
        nextStep: weekly.nextWeekGuidance?.[0]?.guidance ?? 'Wait for today\'s daily refresh.',
        missingnessNote: 'Daily artifact missing — using weekly recovery trends.',
      },
      status: 'downgraded',
      confidence: 'low',
      sources: ['weekly_synthesis_artifact'],
      missingFields: ['daily_refresh_artifact'],
    };
  }

  if (!daily) {
    return {
      answer: {
        short: 'No data available for recovery assessment.',
        why: 'Neither daily nor weekly artifacts exist yet.',
        nextStep: 'Sync WHOOP data to build recovery context.',
        missingnessNote: 'Both daily and weekly artifacts missing.',
      },
      status: 'insufficient_data',
      confidence: 'low',
      sources: [],
      missingFields: ['daily_refresh_artifact', 'weekly_synthesis_artifact'],
    };
  }

  return {
    answer: {
      short: `Day state: ${daily.dayState} (score ${daily.dayScore}).`,
      why: daily.primaryRecommendation.reasons.slice(0, 3).join('. ') + '.',
      nextStep: daily.primaryRecommendation.guidance,
      missingnessNote: ctx.seedMode ? 'Seed-backed — not live WHOOP.' : null,
    },
    status: 'answered',
    confidence: ctx.seedMode ? 'low' : 'medium',
    sources: ['daily_refresh_artifact'],
    missingFields: ctx.seedMode ? uniqueStrings(missingWhoop) : [],
  };
}

function buildTrainingAnswer(
  ctx: AthleteAiContextResponse,
  question: string,
): { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[]; upgradeHint: string | null } {
  const daily = ctx.dailyArtifact as DailyRefreshArtifact | null;
  const weekly = ctx.weeklyArtifact as WeeklySynthesisArtifact | null;
  const sources: string[] = [];

  if (daily) {
    sources.push('daily_refresh_artifact');
    const gate = daily.sessionGate;
    const patterns = daily.activePatterns?.map((p) => p.label).slice(0, 2) ?? [];

    return {
      answer: {
        short: `${daily.dayState} day (score ${daily.dayScore}). ${gate.maxIntensity} intensity allowed.`,
        why: patterns.length > 0
          ? `Active patterns: ${patterns.join(', ')}. ${daily.primaryRecommendation.guidance}`
          : daily.primaryRecommendation.guidance,
        nextStep: `Allowed today: ${gate.allowedTypes.slice(0, 4).join(', ')}.${gate.cautions.length > 0 ? ` Caution: ${gate.cautions[0]}` : ''}`,
        missingnessNote: ctx.seedMode ? 'Seed-backed — session permissions are directional.' : null,
      },
      status: 'answered',
      confidence: ctx.seedMode ? 'low' : 'medium',
      sources,
      missingFields: uniqueStrings([
        ...(daily.coverage?.missingFields ?? []),
        ...(ctx.seedMode ? ctx.capability?.missingWhoopNativeFields ?? [] : []),
      ]),
      upgradeHint: ctx.seedMode ? 'Live WHOOP would strengthen session gating accuracy.' : null,
    };
  }

  if (weekly) {
    sources.push('weekly_synthesis_artifact');
    return {
      answer: {
        short: weekly.dominantDriver
          ? `This week's dominant driver: ${weekly.dominantDriver}.`
          : `${weekly.dailyArtifactCount} days tracked this week.`,
        why: `Weekly confidence: ${weekly.confidence}.${weekly.improved?.length ? ` Improved: ${weekly.improved[0]}.` : ''}${weekly.worsened?.length ? ` Watch: ${weekly.worsened[0]}.` : ''}`,
        nextStep: weekly.nextWeekGuidance?.[0]?.guidance ?? 'Continue current approach.',
        missingnessNote: 'No daily artifact for today — using weekly trends.',
      },
      status: 'downgraded',
      confidence: 'low',
      sources,
      missingFields: ['daily_refresh_artifact'],
      upgradeHint: 'Daily refresh + live WHOOP would enable session-specific guidance.',
    };
  }

  return {
    answer: {
      short: ctx.blockSummary ?? 'Training guidance requires more data.',
      why: 'No daily or weekly artifacts available for session-level recommendations.',
      nextStep: 'Sync WHOOP data or log a session to build context.',
      missingnessNote: 'Both daily and weekly artifacts missing.',
    },
    status: 'insufficient_data',
    confidence: 'low',
    sources: ctx.blockSummary ? ['stable_memory'] : [],
    missingFields: ['daily_refresh_artifact', 'weekly_synthesis_artifact'],
    upgradeHint: 'Connect WHOOP + run daily refresh for full training guidance.',
  };
}

function buildGeneralAnswer(
  ctx: AthleteAiContextResponse,
  question: string,
): { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[]; upgradeHint: string | null } {
  const q = question.toLowerCase();
  const weekly = ctx.weeklyArtifact as WeeklySynthesisArtifact | null;
  const blockSummary = ctx.blockSummary;

  // First-run / backlog analysis questions. These are always answered
  // cautiously as provisional — never stable truths. The backlog
  // summary, when present, carries the "data found / early patterns /
  // what's missing" shape. Without a summary, Coach invites the user
  // to run analysis or keep logging.
  if (hasAny(q, [
    'what have you learned',
    'what do you know about me',
    'what data do you have',
    'patterns are emerging',
    'what is missing from my profile',
    'what should i track next',
    'how does my training compare',
    'can you make this a memory',
    'what coach can tell',
  ])) {
    const summary = (ctx as any).backlogSummary as {
      dataFound?: { normalizedDays?: number; hiitSessions?: number; whoopDays?: number; healthConnectDays?: number; polarViaHealthConnectDays?: number; cronometerDays?: number; manualNutritionDays?: number; grapplingSessions?: number };
      earlyPatterns?: string[];
      whatsMissing?: string[];
      safeNextSteps?: string[];
      reviewableMemoryCandidateIds?: string[];
      comparison?: { comparisonType?: string; statement?: string };
      confidence?: 'low' | 'medium' | 'high';
      generatedAt?: string;
    } | null | undefined;

    if (!summary) {
      return {
        answer: {
          short: 'I have not analysed your history yet.',
          why: 'Backlog analysis runs only after you grant permission. Until then I can answer single-question context but I have no "what I know so far" summary.',
          nextStep: 'Tap "Analyse my history" on the Coach setup card to let me scan connected sources for early patterns.',
          missingnessNote: 'Nothing stored yet — no provisional patterns, no memory proposals.',
        },
        status: 'insufficient_data',
        confidence: 'high',
        sources: ['backlog_analysis_status'],
        missingFields: ['backlog_summary'],
        upgradeHint: null,
      };
    }

    const df = summary.dataFound ?? {};
    const patterns = summary.earlyPatterns ?? [];
    const missing = summary.whatsMissing ?? [];
    const nextSteps = summary.safeNextSteps ?? [];
    const comp = summary.comparison;

    const dataFoundBits = [
      df.normalizedDays ? `${df.normalizedDays} logged days` : null,
      df.hiitSessions ? `${df.hiitSessions} HIIT sessions` : null,
      df.grapplingSessions ? `${df.grapplingSessions} grappling sessions` : null,
      df.whoopDays ? `${df.whoopDays} days with WHOOP` : null,
      df.healthConnectDays ? `${df.healthConnectDays} Health Connect days` : null,
      df.polarViaHealthConnectDays ? `${df.polarViaHealthConnectDays} Polar-via-HC days` : null,
      df.cronometerDays ? `${df.cronometerDays} Cronometer days` : null,
      df.manualNutritionDays ? `${df.manualNutritionDays} manual nutrition days` : null,
    ].filter(Boolean);

    const whyPieces: string[] = [];
    if (patterns.length > 0) whyPieces.push(`Early patterns: ${patterns.slice(0, 3).join(' · ')}`);
    if (comp && comp.comparisonType && comp.comparisonType !== 'none' && comp.statement) {
      whyPieces.push(`Comparison: ${comp.statement}`);
    }
    if (missing.length > 0) whyPieces.push(`What's missing: ${missing.slice(0, 3).join(' · ')}`);

    return {
      answer: {
        short: dataFoundBits.length > 0
          ? `I found ${dataFoundBits.join(', ')}. These are provisional patterns, not stable conclusions.`
          : 'I ran the backlog scan but found very little data yet. Keep logging and re-run from Settings.',
        why: whyPieces.join(' — ') || 'Short history — patterns will sharpen as more data arrives.',
        nextStep: nextSteps[0] ?? 'Keep logging. Re-run backlog analysis later to refresh.',
        missingnessNote: `Provisional summary (confidence: ${summary.confidence ?? 'low'}). No stable memory has been written.`,
      },
      status: 'answered',
      confidence: summary.confidence ?? 'low',
      sources: ['backlog_analysis_summary', 'trend_candidates'],
      missingFields: missing.length > 0 ? ['some_sources_not_connected'] : [],
      upgradeHint: (summary.reviewableMemoryCandidateIds?.length ?? 0) > 0
        ? 'Some early patterns cleared the bar for review — open Settings → Memory proposals to approve or reject.'
        : null,
    };
  }

  // Polar-specific question — distinguishes direct Polar (scaffold) from
  // Polar-via-Health-Connect (real indirect path once Polar Flow is set
  // up to write to HC on the device). Both must be answered truthfully:
  // never claim direct Polar if only HC-mediated Polar data exists, and
  // never claim Polar via HC if no Polar-origin HC records are on file.
  if (hasAny(q, ['polar', 'is polar connected', 'polar connected', 'polar contributed', 'can you use my polar', 'hiit based on polar'])) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const polarInfo = multiSrc?.polar;
    const polarViaHcInfo = multiSrc?.polar_via_health_connect;
    const directPolarStatus = polarInfo?.status ?? 'not_connected';
    const directPolarConnected = directPolarStatus === 'fresh' || directPolarStatus === 'stale';
    const viaHcStatus = polarViaHcInfo?.status ?? 'not_connected';
    const viaHcConnected = viaHcStatus === 'fresh' || viaHcStatus === 'stale';
    const viaHcCoverage: string[] = polarViaHcInfo?.coverage ?? polarViaHcInfo?.domainsAvailable ?? [];
    const viaHcLast = polarViaHcInfo?.lastIngestAt ?? null;
    const sourceApp = polarViaHcInfo?.sourceApp ?? 'Polar Flow';

    if (!directPolarConnected && viaHcConnected) {
      return {
        answer: {
          short: `Polar data is coming through Health Connect (${sourceApp}).`,
          why: viaHcCoverage.length > 0
            ? `Polar-origin Health Connect records cover: ${viaHcCoverage.join(', ')}.`
            : 'Polar-origin Health Connect records are present but no specific domains have enough coverage yet.',
          nextStep: 'Ask about session heart rate, recent workouts, or training history. Direct Polar (AccessLink) is not live yet, so readiness cannot be cleared from Polar alone.',
          missingnessNote: 'Direct Polar adapter: not connected. Readiness still requires direct WHOOP.',
        },
        status: 'answered',
        confidence: 'high',
        sources: ['polar_via_health_connect_source_health', 'source_health_records'],
        missingFields: ['direct_polar_auth'],
        upgradeHint: null,
      };
    }

    if (!directPolarConnected && !viaHcConnected) {
      return {
        answer: {
          short: 'Polar is not connected.',
          why: polarInfo?.reason
            ?? 'Direct Polar adapter is not live yet. No Polar-origin records have come through Health Connect either.',
          nextStep: 'If you use Polar Flow, open it on Android, enable "Write to Health Connect" in Flow settings, then grant Health Connect permissions and sync here. Direct Polar (AccessLink) is not available yet.',
          missingnessNote: 'Polar: not_connected (direct scaffold + no via-HC records).',
        },
        status: 'answered',
        confidence: 'high',
        sources: ['source_health_records'],
        missingFields: ['polar_adapter', 'polar_via_health_connect_records'],
        upgradeHint: null,
      };
    }
    // (Future) If Polar ever becomes connected directly, fall through to data summary.
  }

  // Apple Health — iPhone-first path
  if (hasAny(q, ['apple health', 'healthkit', 'apple watch health', 'iphone health'])) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const ahInfo = multiSrc?.apple_health;
    const ahStatus = ahInfo?.status ?? 'not_connected';
    const ahConnected = ahStatus === 'fresh' || ahStatus === 'stale';
    const ahLast = ahInfo?.lastIngestAt ?? null;

    if (ahConnected) {
      return {
        answer: {
          short: `Apple Health is connected${ahLast ? ` (last sync ${ahLast.slice(0, 10)})` : ''}.`,
          why: 'Apple Health provides sleep, workouts, steps, heart rate, resting HR, and active calories as training context. It does not provide direct WHOOP-style readiness clearance.',
          nextStep: 'Ask about sleep trends, training load, or contextual readiness for a hub-based assessment.',
          missingnessNote: 'Apple Health feeds contextual readiness — not direct physiological clearance.',
        },
        status: 'answered',
        confidence: 'high',
        sources: ['apple_health_source_health'],
        missingFields: [],
        upgradeHint: null,
      };
    }

    return {
      answer: {
        short: 'Apple Health is not connected.',
        why: 'No Apple Health records have been synced to the backend. Grant HealthKit permissions in the app and sync from the Health tab.',
        nextStep: 'Open the Health tab → grant Apple Health permissions → sync. On iPhone, Apple Health is the primary health data path.',
        missingnessNote: 'Apple Health: not_connected. HealthKit authorization may be needed.',
      },
      status: 'answered',
      confidence: 'high',
      sources: ['source_health_records'],
      missingFields: ['apple_health_sync'],
      upgradeHint: null,
    };
  }

  // Samsung Health — via Health Connect only
  if (hasAny(q, ['samsung', 'samsung health', 'galaxy watch', 'galaxy health'])) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const samsungInfo = multiSrc?.samsung_health_via_health_connect;
    const samsungStatus = samsungInfo?.status ?? 'not_connected';
    const samsungConnected = samsungStatus === 'fresh' || samsungStatus === 'stale';
    const samsungCoverage: string[] = samsungInfo?.coverage ?? samsungInfo?.domainsAvailable ?? [];
    const samsungLast = samsungInfo?.lastIngestAt ?? null;

    // Check for direct Samsung Health SDK path too
    const samsungDirectInfo = multiSrc?.samsung_health_direct;
    const directAvailable = samsungDirectInfo?.status === 'fresh' || samsungDirectInfo?.status === 'stale';

    if (samsungConnected && samsungCoverage.length > 0) {
      const directNote = directAvailable
        ? ' Direct Samsung Health SDK is also connected for richer data.'
        : ' Direct Samsung Health SDK is available as a future upgrade for additional data types (stress, blood oxygen, detailed sleep stages).';
      return {
        answer: {
          short: `Samsung Health data is coming through Health Connect. Domains: ${samsungCoverage.join(', ')}.${samsungLast ? ` Last sync: ${samsungLast.slice(0, 10)}.` : ''}`,
          why: `Samsung Health writes to Health Connect on Android 14+.${directNote}`,
          nextStep: 'Ask about sleep, workouts, steps, or heart rate for Samsung-sourced context. Readiness requires direct WHOOP.',
          missingnessNote: 'Samsung Health does not unlock readiness. Only direct WHOOP recovery/HRV/strain can do that.',
        },
        status: 'answered',
        confidence: 'high',
        sources: directAvailable
          ? ['samsung_health_via_health_connect_source_health', 'samsung_health_direct_source_health']
          : ['samsung_health_via_health_connect_source_health'],
        missingFields: [],
        upgradeHint: null,
      };
    }

    return {
      answer: {
        short: 'Samsung Health is not connected.',
        why: 'No Samsung Health records have arrived through Health Connect. If you use Samsung Health, make sure Health Connect sync is enabled in Samsung Health settings.',
        nextStep: 'Open Samsung Health → Settings → Connected services → Health Connect → enable sync for exercise, heart rate, sleep, steps, calories. A direct Samsung Health SDK path is also planned for the future.',
        missingnessNote: 'Samsung Health: not_connected. Via Health Connect is the recommended path.',
      },
      status: 'answered',
      confidence: 'high',
      sources: ['source_health_records'],
      missingFields: ['samsung_health_via_health_connect_records'],
      upgradeHint: null,
    };
  }

  // Health Connect / Android Health specific question
  if (hasAny(q, ['health connect', 'android health', 'what has android health contributed'])) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const hcInfo = multiSrc?.health_connect;
    const hcStatus = hcInfo?.status ?? 'not_connected';
    const hcLastIngest = hcInfo?.lastIngestAt ?? null;

    if (hcStatus === 'not_connected' || hcStatus === 'missing') {
      return {
        answer: {
          short: 'Android Health Connect has not synced yet.',
          why: hcInfo?.reason ?? 'No Health Connect backend ingest on record. Local permission alone does not count — data must be synced to the backend.',
          nextStep: 'Grant Health Connect permissions and trigger a sync from the Health tab.',
          missingnessNote: 'Health Connect: not_connected (no backend ingest).',
        },
        status: 'insufficient_data',
        confidence: 'high',
        sources: ['source_health_records'],
        missingFields: ['health_connect_ingest'],
        upgradeHint: null,
      };
    }

    // Health Connect has data — contextual only, never unlocks readiness.
    // If Polar Flow is routing data through HC, mention that explicitly so
    // the user knows which parts of the HC feed came from Polar.
    const coverage = hcInfo?.coverage ?? hcInfo?.domainsAvailable ?? [];
    const polarViaHcInfo = multiSrc?.polar_via_health_connect;
    const polarViaHcConnected = polarViaHcInfo?.status === 'fresh' || polarViaHcInfo?.status === 'stale';
    const polarCoverage: string[] = polarViaHcInfo?.coverage ?? polarViaHcInfo?.domainsAvailable ?? [];
    const label = hcStatus === 'fresh' ? 'connected' : hcStatus === 'stale' ? 'stale' : hcStatus;
    const polarSuffix = polarViaHcConnected && polarCoverage.length > 0
      ? ` Polar Flow is writing to Health Connect (${polarCoverage.join(', ')}).`
      : '';
    return {
      answer: {
        short: `Android Health Connect: ${label}${hcLastIngest ? ` (last sync ${hcLastIngest.slice(0, 10)})` : ''}.${polarSuffix}`,
        why: `Health Connect provides ${coverage.length > 0 ? coverage.join(', ') : 'sleep, steps, workouts, heart data'} as context. It does not unlock WHOOP-native readiness.${polarSuffix}`,
        nextStep: 'Ask about today\'s training or nutrition; readiness clearance still requires fresh direct WHOOP data.',
        missingnessNote: 'Live WHOOP readiness still unavailable without WHOOP recovery/HRV/strain.',
      },
      status: 'answered',
      confidence: 'medium',
      sources: polarViaHcConnected
        ? ['health_connect_source_health', 'polar_via_health_connect_source_health']
        : ['health_connect_source_health'],
      missingFields: [],
      upgradeHint: null,
    };
  }

  // "What should I track next?" — hub-first guidance
  if (hasAny(q, ['what should i track', 'what to track next', 'track next'])) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const missing: string[] = [];
    const connected: string[] = [];
    for (const [provider, info] of Object.entries(multiSrc ?? {})) {
      const s = info as { status: string };
      if (s.status === 'fresh' || s.status === 'stale') connected.push(provider);
      else if (provider !== 'garmin' && provider !== 'polar' && provider !== 'concept2_logbook') missing.push(provider);
    }
    const suggestions: string[] = [];
    if (!connected.includes('health_connect') && !connected.includes('apple_health'))
      suggestions.push('Connect Apple Health or Health Connect for sleep, workouts, and heart-rate context.');
    if (!connected.includes('samsung_health_via_health_connect') && missing.includes('samsung_health_via_health_connect'))
      suggestions.push('If you use Samsung Health, enable Health Connect sync in Samsung Health settings.');
    if (!(ctx as any).recentHIITWorkouts?.length)
      suggestions.push('Log a HIIT session with set data to enable workout-to-workout comparison.');
    if (!ctx.normalizedDay?.nutritionCalories)
      suggestions.push('Log food today (manual, barcode, or photo) to start nutrition context.');
    if (suggestions.length === 0) suggestions.push('Keep logging consistently. More days = sharper patterns.');
    return {
      answer: {
        short: suggestions[0],
        why: connected.length > 0 ? `Connected: ${connected.join(', ')}.` : 'No health sources connected yet.',
        nextStep: suggestions.length > 1 ? suggestions.slice(1).join(' ') : 'Keep logging.',
        missingnessNote: missing.length > 0 ? `Not connected: ${missing.slice(0, 4).join(', ')}.` : null,
      },
      status: connected.length > 0 ? 'answered' : 'insufficient_data',
      confidence: 'medium',
      sources: ['source_health_records'],
      missingFields: missing.slice(0, 4),
      upgradeHint: null,
    };
  }

  // "How does my training look today?" — hub contextual summary
  if (hasAny(q, ['how does my training look', 'training look today', 'how am i doing today'])) {
    const ctxReady = (ctx as any).contextualReadiness as {
      mode: 'contextual'; level: string; confidence: string; summary: string;
      signals: Array<{ label: string }>; gaps: string[];
    } | null | undefined;
    if (ctxReady && ctxReady.level !== 'insufficient') {
      return {
        answer: {
          short: ctxReady.summary,
          why: ctxReady.signals.slice(0, 3).map(s => s.label).join(' · '),
          nextStep: ctxReady.gaps.length > 0 ? ctxReady.gaps[0] : 'Ask about specific metrics for detail.',
          missingnessNote: 'Contextual view from health hubs — not a direct physiological assessment.',
        },
        status: 'answered',
        confidence: ctxReady.confidence as any,
        sources: ['contextual_readiness_analysis'],
        missingFields: [],
        upgradeHint: null,
      };
    }
    return {
      answer: {
        short: 'Not enough health data to summarize your training today.',
        why: 'Connect Apple Health (iPhone) or Health Connect (Android) and sync to start getting daily context.',
        nextStep: 'Grant health permissions and sync from the Health tab.',
        missingnessNote: 'No hub data available for contextual summary.',
      },
      status: 'insufficient_data',
      confidence: 'low',
      sources: [],
      missingFields: ['health_hub_data'],
      upgradeHint: null,
    };
  }

  // Source-status questions get a dedicated answer
  if (hasAny(q, SOURCE_STATUS_KEYWORDS)) {
    const multiSrc = (ctx as any).multiSourceHealth;
    const parts: string[] = [];
    const missing: string[] = [];
    if (multiSrc) {
      for (const [provider, info] of Object.entries(multiSrc)) {
        const s = info as { status: string; upstream?: string };
        if (s.status === 'fresh') parts.push(`${provider}: connected`);
        else if (s.status === 'stale') parts.push(`${provider}: stale`);
        else missing.push(provider);
      }
    }
    const missingWhoop = ctx.capability?.missingWhoopNativeFields ?? [];
    return {
      answer: {
        short: parts.length > 0 ? `Sources: ${parts.join(', ')}.` : 'No health sources are connected yet.',
        why: missing.length > 0 ? `Not connected: ${missing.join(', ')}.` : 'All checked sources have data.',
        nextStep: missingWhoop.length > 0 ? `Missing WHOOP-native: ${missingWhoop.join(', ')}.` : 'Source coverage looks complete for current features.',
        missingnessNote: missing.length > 0 ? `Unconnected: ${missing.join(', ')}` : null,
      },
      status: parts.length > 0 ? 'answered' : 'insufficient_data',
      confidence: 'medium',
      sources: ['source_health_records'],
      missingFields: missing,
      upgradeHint: missing.includes('cronometer') ? 'Connect Cronometer for nutrition-aware coaching.' : null,
    };
  }

  return {
    answer: {
      short: blockSummary ?? 'Ask about training, recovery, nutrition, or HIIT for a specific answer.',
      why: weekly
        ? `This week: ${weekly.dailyArtifactCount} days tracked.${weekly.dominantDriver ? ` Driver: ${weekly.dominantDriver}.` : ''}${weekly.improved?.length ? ` Improved: ${weekly.improved[0]}.` : ''}`
        : 'Limited context — log more data for better answers.',
      nextStep: weekly?.nextWeekGuidance?.[0]?.guidance ?? 'Try a more specific question.',
      missingnessNote: ctx.seedMode ? 'Seed-backed — directional only.' : null,
    },
    status: weekly ? 'answered' : 'downgraded',
    confidence: 'low',
    sources: weekly ? ['weekly_synthesis_artifact', 'stable_memory'] : ['stable_memory'],
    missingFields: weekly ? [] : ['weekly_synthesis_artifact'],
    upgradeHint: ctx.seedMode ? 'Live WHOOP + full daily coverage would strengthen all answers.' : null,
  };
}

// ---------------------------------------------------------------------------
// Main builder
// ---------------------------------------------------------------------------

export function buildCoachAnswer(
  question: string,
  aiContext: AthleteAiContextResponse,
  topicHint?: string,
): CoachAnswerResponse {
  const { domain, questionClass } = classifyQuestion(question, topicHint);
  const mode = aiContext.capability?.mode ?? 'seed_partial';

  let result: { answer: CoachAnswerBody; status: CoachAnswerStatus; confidence: CoachConfidence; sources: string[]; missingFields: string[]; upgradeHint?: string | null };

  switch (domain) {
    case 'hiit':
      result = buildHiitAnswer(aiContext, question);
      break;
    case 'nutrition':
      result = buildNutritionAnswer(aiContext, question);
      break;
    case 'recovery':
      result = buildRecoveryAnswer(aiContext);
      break;
    case 'training':
      result = buildTrainingAnswer(aiContext, question);
      break;
    case 'general':
    default:
      result = buildGeneralAnswer(aiContext, question);
      break;
  }

  const safetyFlags: string[] = [];
  if (aiContext.seedMode) safetyFlags.push('seed_mode');
  if (aiContext.provisionalUntilDirectWhoop) safetyFlags.push('provisional_until_whoop');
  if ((aiContext.capability?.missingWhoopNativeFields ?? []).length > 0) safetyFlags.push('missing_whoop_fields');
  if (result.status === 'downgraded') safetyFlags.push('answer_downgraded');
  if (result.status === 'insufficient_data') safetyFlags.push('insufficient_data');

  // Guarantee all render-critical fields are stable (never undefined)
  const answer: CoachAnswerBody = {
    short: result.answer.short ?? 'No answer available.',
    why: result.answer.why ?? '',
    nextStep: result.answer.nextStep ?? '',
    missingnessNote: result.answer.missingnessNote ?? null,
  };

  return {
    ok: true,
    domain: domain ?? 'general',
    mode: mode ?? 'seed_partial',
    questionClass: questionClass ?? 'unknown',
    status: result.status ?? 'unsupported',
    answer,
    confidence: result.confidence ?? 'low',
    sourceDependencies: result.sources ?? [],
    missingFields: result.missingFields ?? [],
    safetyFlags: safetyFlags ?? [],
    upgradeHint: result.upgradeHint ?? (aiContext.seedMode ? 'Live WHOOP connection would improve this answer.' : null),
  };
}
