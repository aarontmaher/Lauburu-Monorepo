import {
  ATHLETE_DAILY_DECISION_ENGINE_CONFIG,
  ATHLETE_MEMORY_UPDATE_POLICY,
  ATHLETE_REBOUND_PROTOCOL,
  ATHLETE_ROLLING_3_DAY_RISK_MODEL,
  ATHLETE_SESSION_CLASSIFICATION_MODEL,
  ATHLETE_SYMPTOM_OVERRIDE_POLICY,
} from './config';
import type { DailyMetrics } from '../types/health';
import type {
  AthleteActiveHypothesis,
  AthleteBinarySignal,
  AthleteConfidence,
  AthleteDailyRefreshArtifact,
  AthleteDailyRefreshResult,
  AthleteDecisionGuidance,
  AthleteDayClassification,
  AthleteExpiringInterpretation,
  AthleteMemoryRecord,
  AthleteMemoryReviewFlag,
  AthleteMetricAggregate,
  AthleteMetricComparison,
  AthleteObservedPattern,
  AthleteProtocolOrExperiment,
  AthleteRefreshInput,
  AthleteRollingRisk,
  AthleteSessionPermissionLevel,
  AthleteSessionPermissionBucket,
  AthleteSessionPermissions,
  AthleteSourceState,
  AthleteSymptomOverrideState,
  AthleteWarningFlag,
  AthleteWeeklyReviewCandidate,
  AthleteWeeklySynthesisArtifact,
  AthleteWeeklySynthesisInput,
  AthleteWeeklySynthesisResult,
  AthleteWindowSummary,
} from './types';

function sortDays(history: DailyMetrics[]): DailyMetrics[] {
  return [...history].sort((a, b) => a.date.localeCompare(b.date));
}

function parseDay(date: string): Date {
  return new Date(`${date}T00:00:00.000Z`);
}

function offsetDay(date: string, offset: number): string {
  const d = parseDay(date);
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0, 10);
}

function addDays(date: string, days: number): string {
  return offsetDay(date, days);
}

function inclusiveWindow(history: DailyMetrics[], endDate: string, days: number) {
  const start = offsetDay(endDate, -(days - 1));
  return history.filter((day) => day.date >= start && day.date <= endDate);
}

function mean(nums: Array<number | undefined | null>): number | null {
  const valid = nums.filter((n): n is number => n != null);
  if (!valid.length) return null;
  return Math.round((valid.reduce((sum, n) => sum + n, 0) / valid.length) * 100) / 100;
}

function aggregateWindow(days: DailyMetrics[]): AthleteMetricAggregate {
  return {
    recoveryMean: mean(days.map((d) => d.recovery_score)),
    hrvMean: mean(days.map((d) => d.hrv_ms)),
    restingHrMean: mean(days.map((d) => d.resting_hr)),
    sleepMean: mean(days.map((d) => d.sleep_hours)),
    strainMean: mean(days.map((d) => d.daily_strain)),
    workoutCount: days.reduce((sum, d) => sum + (d.workouts?.length ?? 0), 0),
    grapplingCount: days.reduce(
      (sum, d) =>
        sum +
        (d.workouts?.filter((w) => w.is_grappling).length ?? 0) +
        (d.grappling_session ? 1 : 0),
      0,
    ),
    restDays: days.filter((d) => !d.workouts?.length && !d.grappling_session).length,
    daysWithData: days.length,
  };
}

function compareMetric(
  metric: AthleteMetricComparison['metric'],
  currentValue: number | null,
  baselineValue: number | null,
  interpretation: string,
): AthleteMetricComparison {
  const delta =
    currentValue != null && baselineValue != null
      ? Math.round((currentValue - baselineValue) * 100) / 100
      : null;
  const deltaPct =
    delta != null && baselineValue != null && baselineValue !== 0
      ? Math.round((delta / baselineValue) * 10000) / 100
      : null;
  const direction =
    delta == null ? 'unknown' : Math.abs(delta) < 0.01 ? 'flat' : delta > 0 ? 'up' : 'down';
  return { metric, currentValue, baselineValue, delta, deltaPct, direction, interpretation };
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function confidenceFromCount(count: number): AthleteConfidence {
  if (count >= 3) return 'high';
  if (count >= 2) return 'medium';
  return 'low';
}

function coverageConfidence(sourceState: AthleteSourceState, historyDays: number): AthleteConfidence {
  if (sourceState.status !== 'ready') return 'low';
  if (sourceState.missingInputs.length > 0 || historyDays < 14) return 'medium';
  return 'high';
}

function buildPhysiologyBaseline(history: DailyMetrics[], generatedAt: string) {
  const baselineWindow = history.slice(-Math.min(history.length, 90));
  return {
    computedAt: generatedAt,
    dataWindowDays: baselineWindow.length,
    recoveryBaseline: mean(baselineWindow.map((d) => d.recovery_score)),
    hrvBaseline: mean(baselineWindow.map((d) => d.hrv_ms)),
    restingHrBaseline: mean(baselineWindow.map((d) => d.resting_hr)),
    sleepBaseline: mean(baselineWindow.map((d) => d.sleep_hours)),
    strainBaseline: mean(baselineWindow.map((d) => d.daily_strain)),
    thresholds: ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds,
    ruleBasis: [
      'Baselines are rolling means over up to 90 days of private athlete history.',
      'Thresholds are athlete-relative rather than absolute generic wellness cutoffs.',
    ],
  };
}

function pctOfBaseline(value: number | null, baseline: number | null): number | null {
  if (value == null || baseline == null || baseline === 0) return null;
  return value / baseline;
}

function multipleOfBaseline(value: number | null, baseline: number | null): number | null {
  return pctOfBaseline(value, baseline);
}

export function classifyDayState(
  latest: DailyMetrics,
  baseline: ReturnType<typeof buildPhysiologyBaseline>,
): AthleteDayClassification {
  let score = 50;
  const reasons: string[] = [];

  const recoveryRatio = pctOfBaseline(latest.recovery_score ?? null, baseline.recoveryBaseline);
  if (recoveryRatio != null) {
    if (recoveryRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.recoveryBelowBaseline.warningPct) {
      score -= 20;
      reasons.push('Recovery is materially below personal baseline.');
    } else if (recoveryRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.recoveryBelowBaseline.cautionPct) {
      score -= 10;
      reasons.push('Recovery is below personal baseline.');
    } else if (recoveryRatio >= 1.05) {
      score += 10;
      reasons.push('Recovery is above personal baseline.');
    }
  }

  const hrvRatio = pctOfBaseline(latest.hrv_ms ?? null, baseline.hrvBaseline);
  if (hrvRatio != null) {
    if (hrvRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.hrvBelowBaseline.warningPct) {
      score -= 15;
      reasons.push('HRV is materially suppressed versus baseline.');
    } else if (hrvRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.hrvBelowBaseline.cautionPct) {
      score -= 8;
      reasons.push('HRV is below baseline.');
    }
  }

  const rhrRatio = multipleOfBaseline(latest.resting_hr ?? null, baseline.restingHrBaseline);
  if (rhrRatio != null) {
    if (rhrRatio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.restingHrAboveBaseline.warningPct) {
      score -= 15;
      reasons.push('Resting HR is materially elevated above baseline.');
    } else if (rhrRatio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.restingHrAboveBaseline.cautionPct) {
      score -= 8;
      reasons.push('Resting HR is elevated above baseline.');
    }
  }

  const sleepRatio = pctOfBaseline(latest.sleep_hours ?? null, baseline.sleepBaseline);
  if (sleepRatio != null) {
    if (sleepRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.sleepBelowBaseline.warningPct) {
      score -= 12;
      reasons.push('Sleep is materially below baseline.');
    } else if (sleepRatio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.sleepBelowBaseline.cautionPct) {
      score -= 6;
      reasons.push('Sleep is below baseline.');
    } else if (sleepRatio >= 1.03) {
      score += 5;
      reasons.push('Sleep is above baseline.');
    }
  }

  const strainRatio = multipleOfBaseline(latest.daily_strain ?? null, baseline.strainBaseline);
  if (strainRatio != null) {
    if (strainRatio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.strainAboveBaseline.warningPct) {
      score -= 12;
      reasons.push('Strain is materially above baseline.');
    } else if (strainRatio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.strainAboveBaseline.cautionPct) {
      score -= 6;
      reasons.push('Strain is above baseline.');
    }
  }

  const state =
    score >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.greenCutoff
      ? 'green'
      : score >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.yellowCutoff
        ? 'yellow'
        : 'red';

  return {
    state,
    score,
    reasons,
    confidence: reasons.length >= 3 ? 'high' : reasons.length >= 2 ? 'medium' : 'low',
    ruleBasis: [
      ATHLETE_DAILY_DECISION_ENGINE_CONFIG.modelVersion,
      ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.modelVersion,
    ],
  };
}

export function computeRollingRisk(
  recent3Days: DailyMetrics[],
  baseline: ReturnType<typeof buildPhysiologyBaseline>,
): AthleteRollingRisk {
  let score = 0;
  const drivers: string[] = [];
  const latest3 = recent3Days.slice(-ATHLETE_ROLLING_3_DAY_RISK_MODEL.windowDays);
  const lowRecoveryDays = latest3.filter((d) => {
    const ratio = pctOfBaseline(d.recovery_score ?? null, baseline.recoveryBaseline);
    return ratio != null && ratio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.recoveryBelowBaseline.cautionPct;
  }).length;
  if (lowRecoveryDays >= 2) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.lowRecoveryWeight;
    drivers.push('Multiple recent low-recovery days.');
  }
  const lowHrvDays = latest3.filter((d) => {
    const ratio = pctOfBaseline(d.hrv_ms ?? null, baseline.hrvBaseline);
    return ratio != null && ratio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.hrvBelowBaseline.cautionPct;
  }).length;
  if (lowHrvDays >= 2) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.lowHrvWeight;
    drivers.push('Multiple recent low-HRV days.');
  }
  const highRhrDays = latest3.filter((d) => {
    const ratio = multipleOfBaseline(d.resting_hr ?? null, baseline.restingHrBaseline);
    return ratio != null && ratio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.restingHrAboveBaseline.cautionPct;
  }).length;
  if (highRhrDays >= 2) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.highRestingHrWeight;
    drivers.push('Resting HR has stayed elevated.');
  }
  const lowSleepDays = latest3.filter((d) => {
    const ratio = pctOfBaseline(d.sleep_hours ?? null, baseline.sleepBaseline);
    return ratio != null && ratio <= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.sleepBelowBaseline.cautionPct;
  }).length;
  if (lowSleepDays >= 2) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.lowSleepWeight;
    drivers.push('Sleep has stayed below baseline.');
  }
  const highStrainDays = latest3.filter((d) => {
    const ratio = multipleOfBaseline(d.daily_strain ?? null, baseline.strainBaseline);
    return ratio != null && ratio >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.strainAboveBaseline.cautionPct;
  }).length;
  if (highStrainDays >= 2) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.highStrainWeight;
    drivers.push('Strain has stayed elevated.');
  }
  const consecutiveTrainingDays = latest3.filter(
    (d) => (d.workouts?.length ?? 0) > 0 || d.grappling_session != null,
  ).length;
  if (consecutiveTrainingDays === latest3.length && latest3.length === 3) {
    score += ATHLETE_ROLLING_3_DAY_RISK_MODEL.consecutiveLoadWeight;
    drivers.push('No rest day in the rolling three-day window.');
  }
  const level =
    score >= ATHLETE_ROLLING_3_DAY_RISK_MODEL.highRiskCutoff
      ? 'high'
      : score >= ATHLETE_ROLLING_3_DAY_RISK_MODEL.elevatedRiskCutoff
        ? 'elevated'
        : score >= 20
          ? 'moderate'
          : 'low';

  return {
    windowDays: 3,
    score,
    level,
    drivers,
    confidence: confidenceFromCount(drivers.length),
    ruleBasis: [ATHLETE_ROLLING_3_DAY_RISK_MODEL.modelVersion],
  };
}

export function detectFalseGreenLight(
  dayClassification: AthleteDayClassification,
  rollingRisk: AthleteRollingRisk,
): AthleteBinarySignal {
  const active =
    dayClassification.state === 'green' &&
    rollingRisk.score >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.falseGreenRiskFloor;
  return {
    active,
    reasons: active
      ? ['Day looks green in isolation, but rolling risk remains elevated.']
      : [],
    confidence: active ? 'medium' : 'low',
    ruleBasis: ['false_green_requires_green_day_plus_elevated_rolling_risk'],
  };
}

export function detectDelayedCrashBuild(
  rollingRisk: AthleteRollingRisk,
): AthleteBinarySignal {
  const active =
    rollingRisk.score >= ATHLETE_DAILY_DECISION_ENGINE_CONFIG.delayedCrashRiskFloor;
  return {
    active,
    reasons: active ? ['Recent load/recovery pattern suggests delayed fatigue risk.'] : [],
    confidence: active ? 'medium' : 'low',
    ruleBasis: ['delayed_crash_requires_high_rolling_risk'],
  };
}

export function applySymptomOverride(
  symptoms: string[] | undefined,
): AthleteSymptomOverrideState {
  const normalized = (symptoms ?? []).map((item) => item.toLowerCase());
  const severe = normalized.filter((symptom) =>
    ATHLETE_SYMPTOM_OVERRIDE_POLICY.severeSymptomsBlockAll.includes(symptom),
  );
  if (severe.length) {
    return {
      status: 'blocked',
      matchedSymptoms: severe,
      confidence: 'high',
      ruleBasis: [ATHLETE_SYMPTOM_OVERRIDE_POLICY.modelVersion, 'severe symptoms block training'],
    };
  }
  const caution = normalized.filter((symptom) =>
    ATHLETE_SYMPTOM_OVERRIDE_POLICY.cautionSymptomsForceLightOnly.includes(symptom),
  );
  if (caution.length) {
    return {
      status: 'light_only',
      matchedSymptoms: caution,
      confidence: 'medium',
      ruleBasis: [ATHLETE_SYMPTOM_OVERRIDE_POLICY.modelVersion, 'caution symptoms force light-only day'],
    };
  }
  return {
    status: 'none',
    matchedSymptoms: [],
    confidence: 'low',
    ruleBasis: [ATHLETE_SYMPTOM_OVERRIDE_POLICY.modelVersion],
  };
}

export function classifySessionPermissions(
  dayClassification: AthleteDayClassification,
  rollingRisk: AthleteRollingRisk,
  falseGreenLight: AthleteBinarySignal,
  delayedCrashBuild: AthleteBinarySignal,
  symptomOverride: AthleteSymptomOverrideState,
): AthleteSessionPermissions {
  const addBuckets = (
    labels: string[],
    level: AthleteSessionPermissionLevel,
    reasons: string[],
  ): AthleteSessionPermissionBucket[] => labels.map((label) => ({ label, level, reasons }));

  let allowedLabels = ATHLETE_SESSION_CLASSIFICATION_MODEL.greenAllowed;
  if (dayClassification.state === 'yellow') allowedLabels = ATHLETE_SESSION_CLASSIFICATION_MODEL.yellowAllowed;
  if (dayClassification.state === 'red') allowedLabels = ATHLETE_SESSION_CLASSIFICATION_MODEL.redAllowed;
  if (symptomOverride.status === 'blocked' || dayClassification.state === 'blocked') {
    allowedLabels = ATHLETE_SESSION_CLASSIFICATION_MODEL.blockedAllowed;
  } else if (symptomOverride.status === 'light_only') {
    allowedLabels = ['mobility', 'walk', 'technical_grappling'];
  }

  const riskyLabels =
    falseGreenLight.active || delayedCrashBuild.active || rollingRisk.level === 'high'
      ? ATHLETE_SESSION_CLASSIFICATION_MODEL.riskyWhenFatigued
      : [];

  const bannedLabels = uniqueStrings(
    ATHLETE_SESSION_CLASSIFICATION_MODEL.greenAllowed.filter((label) => !allowedLabels.includes(label)).filter((label) => riskyLabels.includes(label) || symptomOverride.status !== 'none'),
  );

  return {
    allowed: addBuckets(allowedLabels, 'allowed', [...dayClassification.reasons]),
    risky: addBuckets(
      uniqueStrings(riskyLabels.filter((label) => !allowedLabels.includes(label))),
      'risky',
      [...rollingRisk.drivers, ...falseGreenLight.reasons, ...delayedCrashBuild.reasons],
    ),
    banned: addBuckets(
      uniqueStrings(bannedLabels),
      'banned',
      symptomOverride.matchedSymptoms.length
        ? [`Symptom override: ${symptomOverride.matchedSymptoms.join(', ')}`]
        : ['Current day/risk state does not support these sessions.'],
    ),
    confidence: coverageConfidence(
      {
        sourceType: 'mixed',
        status: 'ready',
        authState: 'unknown',
        latestDataDate: null,
        fallbackReason: 'none',
        sourceCoverage: [],
        missingInputs: [],
        confidence: 'low',
        ruleBasis: [],
      },
      allowedLabels.length,
    ),
    ruleBasis: [ATHLETE_SESSION_CLASSIFICATION_MODEL.modelVersion],
  };
}

function buildPatterns(
  latest: DailyMetrics,
  last7: AthleteMetricAggregate,
  baseline: ReturnType<typeof buildPhysiologyBaseline>,
  rollingRisk: AthleteRollingRisk,
): AthleteObservedPattern[] {
  const patterns: AthleteObservedPattern[] = [];
  if (rollingRisk.level === 'high' || rollingRisk.level === 'elevated') {
    patterns.push({
      key: 'accumulated_fatigue',
      label: 'Accumulated fatigue pressure is active',
      observationCount: 1,
      active: true,
      evidence: rollingRisk.drivers,
      confidence: rollingRisk.confidence,
      ruleBasis: rollingRisk.ruleBasis,
    });
  }
  if (
    last7.sleepMean != null &&
    baseline.sleepBaseline != null &&
    last7.sleepMean < baseline.sleepBaseline * ATHLETE_DAILY_DECISION_ENGINE_CONFIG.thresholds.sleepBelowBaseline.cautionPct
  ) {
    patterns.push({
      key: 'sleep_drag',
      label: 'Recent sleep is below baseline',
      observationCount: 1,
      active: true,
      evidence: [`7-day sleep mean ${last7.sleepMean}h vs baseline ${baseline.sleepBaseline}h`],
      confidence: 'medium',
      ruleBasis: ['sleep baseline comparison'],
    });
  }
  if (
    latest.recovery_score != null &&
    baseline.recoveryBaseline != null &&
    latest.recovery_score > baseline.recoveryBaseline * ATHLETE_REBOUND_PROTOCOL.minimumRecoveryPctOfBaseline
  ) {
    patterns.push({
      key: 'readiness_rebound',
      label: 'Readiness rebound is showing',
      observationCount: 1,
      active: true,
      evidence: ['Latest recovery is above rebound threshold.'],
      confidence: 'low',
      ruleBasis: [ATHLETE_REBOUND_PROTOCOL.modelVersion],
    });
  }
  return patterns;
}

function buildHypotheses(
  patterns: AthleteObservedPattern[],
  generatedAt: string,
): AthleteActiveHypothesis[] {
  const expiresAt = addDays(generatedAt.slice(0, 10), ATHLETE_MEMORY_UPDATE_POLICY.hypothesisExpiryDays);
  return patterns.map((pattern) => ({
    key: `hypothesis_${pattern.key}`,
    statement:
      pattern.key === 'accumulated_fatigue'
        ? 'Accumulated training load is currently outpacing recovery capacity.'
        : pattern.key === 'sleep_drag'
          ? 'Sub-baseline sleep is contributing to weaker readiness.'
          : pattern.label,
    status: 'active',
    supportingSignals: pattern.evidence,
    expiresAt,
    confidence: pattern.confidence,
    ruleBasis: pattern.ruleBasis,
  }));
}

function buildWarningFlags(
  sourceState: AthleteSourceState,
  falseGreenLight: AthleteBinarySignal,
  delayedCrashBuild: AthleteBinarySignal,
): AthleteWarningFlag[] {
  const flags: AthleteWarningFlag[] = [];
  if (sourceState.status !== 'ready') {
    flags.push({
      level: 'warning',
      label: `Source fallback active: ${sourceState.fallbackReason}`,
      confidence: 'high',
      ruleBasis: ['source_state'],
    });
  }
  if (falseGreenLight.active) {
    flags.push({
      level: 'watch',
      label: 'False green-light risk is active.',
      confidence: falseGreenLight.confidence,
      ruleBasis: falseGreenLight.ruleBasis,
    });
  }
  if (delayedCrashBuild.active) {
    flags.push({
      level: 'warning',
      label: 'Delayed crash build risk is active.',
      confidence: delayedCrashBuild.confidence,
      ruleBasis: delayedCrashBuild.ruleBasis,
    });
  }
  return flags;
}

export function determineMemoryReviewFlags(
  patterns: AthleteObservedPattern[],
  weeklyOnly: boolean,
  sourceState: AthleteSourceState,
): AthleteMemoryReviewFlag[] {
  const flags: AthleteMemoryReviewFlag[] = [];
  if (weeklyOnly && patterns.length >= ATHLETE_MEMORY_UPDATE_POLICY.patternPromotionMinimumObservations) {
    flags.push({
      level: 'weekly_review',
      label: 'Observed patterns are stable enough to review for promotion.',
      confidence: 'medium',
      ruleBasis: [ATHLETE_MEMORY_UPDATE_POLICY.modelVersion],
    });
  }
  if (sourceState.status !== 'ready') {
    flags.push({
      level: 'weekly_review',
      label: 'Source fallback was active; review before changing stable memory.',
      confidence: 'high',
      ruleBasis: ['degraded source blocks automatic memory mutation'],
    });
  }
  return flags;
}

function buildExpiringInterpretations(
  kind: AthleteExpiringInterpretation['kind'],
  generatedAt: string,
  entries: string[],
  basis: string[],
): AthleteExpiringInterpretation[] {
  return entries.map((summary, index) => ({
    key: `${kind}_interpretation_${index + 1}`,
    kind,
    summary,
    generatedAt,
    expiresAt: addDays(generatedAt.slice(0, 10), kind === 'daily' ? 2 : 7),
    confidence: 'medium',
    ruleBasis: basis,
  }));
}

function buildComparisons(
  current: AthleteMetricAggregate,
  baseline: ReturnType<typeof buildPhysiologyBaseline>,
  label: string,
): AthleteMetricComparison[] {
  return [
    compareMetric('recovery', current.recoveryMean, baseline.recoveryBaseline, `${label} recovery vs physiology baseline`),
    compareMetric('hrv', current.hrvMean, baseline.hrvBaseline, `${label} HRV vs physiology baseline`),
    compareMetric('resting_hr', current.restingHrMean, baseline.restingHrBaseline, `${label} resting HR vs physiology baseline`),
    compareMetric('sleep', current.sleepMean, baseline.sleepBaseline, `${label} sleep vs physiology baseline`),
    compareMetric('strain', current.strainMean, baseline.strainBaseline, `${label} strain vs physiology baseline`),
    compareMetric('workouts', current.workoutCount, null, `${label} workout density vs baseline is not yet modeled`),
    compareMetric('grappling_sessions', current.grapplingCount, null, `${label} grappling density vs baseline is not yet modeled`),
  ];
}

export function buildDailyAthleteRefreshArtifact(
  input: AthleteRefreshInput,
): AthleteDailyRefreshResult {
  const history = sortDays(input.history);
  if (!history.length) throw new Error(`No athlete history available for ${input.athleteId}.`);
  const sourceDate = input.asOfDate ?? history[history.length - 1].date;
  const asOfHistory = history.filter((day) => day.date <= sourceDate);
  if (!asOfHistory.length) throw new Error(`No athlete history exists on or before ${sourceDate}.`);
  const generatedAt = input.generatedAt ?? new Date(`${sourceDate}T12:00:00.000Z`).toISOString();
  const expiresAt = new Date(`${sourceDate}T23:59:59.000Z`).toISOString();
  const latest = asOfHistory[asOfHistory.length - 1];
  const baseline = input.priorMemory?.physiologyBaseline ?? buildPhysiologyBaseline(asOfHistory, generatedAt);
  const rollingSummaries: AthleteWindowSummary[] = ([7, 14, 30] as const).map((windowDays) => ({
    windowDays,
    anchorDate: latest.date,
    metrics: aggregateWindow(inclusiveWindow(asOfHistory, latest.date, windowDays)),
  }));
  const rollingRisk = computeRollingRisk(inclusiveWindow(asOfHistory, latest.date, 3), baseline);
  const dayClassification = classifyDayState(latest, baseline);
  const falseGreenLight = detectFalseGreenLight(dayClassification, rollingRisk);
  const delayedCrashBuild = detectDelayedCrashBuild(rollingRisk);
  const symptomOverride = applySymptomOverride(input.reportedSymptoms);
  const sessionPermissions = classifySessionPermissions(
    symptomOverride.status === 'blocked'
      ? { ...dayClassification, state: 'blocked' }
      : dayClassification,
    rollingRisk,
    falseGreenLight,
    delayedCrashBuild,
    symptomOverride,
  );
  const patterns = buildPatterns(latest, rollingSummaries[0].metrics, baseline, rollingRisk);
  const hypotheses = buildHypotheses(patterns, generatedAt);
  const warningFlags = buildWarningFlags(input.sourceState, falseGreenLight, delayedCrashBuild);
  const memoryReviewFlags = determineMemoryReviewFlags(
    patterns,
    ATHLETE_MEMORY_UPDATE_POLICY.thresholdReviewWeeklyOnly,
    input.sourceState,
  );
  const nextBestAction: AthleteDecisionGuidance = {
    horizon: 'next_1_3_days',
    guidance:
      symptomOverride.status === 'blocked'
        ? 'Do not train until symptom override clears.'
        : dayClassification.state === 'green'
          ? 'Train normally, but respect rolling risk if it rises tomorrow.'
          : dayClassification.state === 'yellow'
            ? 'Bias toward technical work and moderate load.'
            : 'Protect recovery and avoid high-intensity sessions.',
    reasons: uniqueStrings([
      ...dayClassification.reasons,
      ...rollingRisk.drivers,
      ...symptomOverride.matchedSymptoms,
    ]),
    confidence: coverageConfidence(input.sourceState, asOfHistory.length),
    ruleBasis: uniqueStrings([
      ...dayClassification.ruleBasis,
      ...rollingRisk.ruleBasis,
      ...symptomOverride.ruleBasis,
    ]),
  };

  const dailyRefresh: AthleteDailyRefreshArtifact = {
    athleteId: input.athleteId,
    generatedAt,
    expiresAt,
    sourceDate: latest.date,
    sourceState: input.sourceState,
    sourceCoverage: input.sourceState.sourceCoverage,
    missingInputs: input.sourceState.missingInputs,
    confidence: coverageConfidence(input.sourceState, asOfHistory.length),
    ruleBasis: ['daily artifact is deterministic and does not mutate stable thresholds'],
    rawInputs: {
      latest: {
        date: latest.date,
        recoveryScore: latest.recovery_score ?? null,
        hrvMs: latest.hrv_ms ?? null,
        restingHr: latest.resting_hr ?? null,
        sleepHours: latest.sleep_hours ?? null,
        dailyStrain: latest.daily_strain ?? null,
        workoutCount: latest.workouts?.length ?? 0,
        grapplingToday:
          (latest.workouts?.some((w) => w.is_grappling) ?? false) || latest.grappling_session != null,
      },
      rollingSummaries,
    },
    dayClassification,
    rollingRisk,
    falseGreenLight,
    delayedCrashBuild,
    symptomOverride,
    sessionPermissions,
    nextBestAction,
    keyDrivers: uniqueStrings([...dayClassification.reasons, ...rollingRisk.drivers]),
    warningFlags,
    recurringPatternsActive: patterns,
    activeHypotheses: hypotheses,
    expiringInterpretations: buildExpiringInterpretations(
      'daily',
      generatedAt,
      [
        nextBestAction.guidance,
        ...(falseGreenLight.active ? ['False green-light conditions are active today.'] : []),
        ...(delayedCrashBuild.active ? ['Delayed-crash risk is building.'] : []),
      ],
      uniqueStrings([...nextBestAction.ruleBasis, ...warningFlags.flatMap((flag) => flag.ruleBasis)]),
    ),
    memoryReviewFlags,
  };

  const updatedMemory: AthleteMemoryRecord = {
    athleteId: input.athleteId,
    updatedAt: generatedAt,
    physiologyBaseline: baseline,
    observedPatterns: patterns,
    activeHypotheses: hypotheses,
    activeProtocols: input.priorMemory?.activeProtocols ?? [],
    currentBlockSummary: nextBestAction.guidance,
    nextSevenDayDecisionRules: [
      {
        horizon: 'next_3_7_days',
        guidance: dayClassification.state === 'green'
          ? 'Hold normal load unless rolling risk or symptoms worsen.'
          : 'Keep the next week conservative until recovery signals normalize.',
        reasons: nextBestAction.reasons,
        confidence: nextBestAction.confidence,
        ruleBasis: nextBestAction.ruleBasis,
      },
    ],
    latestDailyRefreshAt: generatedAt,
    latestWeeklySynthesisAt: input.priorMemory?.latestWeeklySynthesisAt ?? null,
  };

  return { dailyRefresh, updatedMemory };
}

function startOfWeek(date: string): string {
  const d = parseDay(date);
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - day + 1);
  return d.toISOString().slice(0, 10);
}

function weekKeyFromDate(date: string): string {
  return `${startOfWeek(date)}__${date}`;
}

function aggregateFromDailyRefreshes(dailies: AthleteDailyRefreshArtifact[]): AthleteMetricAggregate {
  return {
    recoveryMean: mean(dailies.map((d) => d.rawInputs.latest.recoveryScore)),
    hrvMean: mean(dailies.map((d) => d.rawInputs.latest.hrvMs)),
    restingHrMean: mean(dailies.map((d) => d.rawInputs.latest.restingHr)),
    sleepMean: mean(dailies.map((d) => d.rawInputs.latest.sleepHours)),
    strainMean: mean(dailies.map((d) => d.rawInputs.latest.dailyStrain)),
    workoutCount: dailies.reduce((sum, d) => sum + d.rawInputs.latest.workoutCount, 0),
    grapplingCount: dailies.reduce((sum, d) => sum + (d.rawInputs.latest.grapplingToday ? 1 : 0), 0),
    restDays: dailies.filter((d) => d.rawInputs.latest.workoutCount === 0 && !d.rawInputs.latest.grapplingToday).length,
    daysWithData: dailies.length,
  };
}

function aggregatePatterns(dailies: AthleteDailyRefreshArtifact[]): AthleteObservedPattern[] {
  const map = new Map<string, AthleteObservedPattern>();
  dailies.flatMap((d) => d.recurringPatternsActive).forEach((pattern) => {
    const existing = map.get(pattern.key);
    if (!existing) {
      map.set(pattern.key, { ...pattern, observationCount: 1 });
      return;
    }
    existing.observationCount += 1;
    existing.evidence = uniqueStrings([...existing.evidence, ...pattern.evidence]);
    existing.confidence = confidenceFromCount(existing.observationCount);
  });
  return [...map.values()].sort((a, b) => b.observationCount - a.observationCount).slice(0, 4);
}

function rollForwardHypotheses(
  dailies: AthleteDailyRefreshArtifact[],
  priorMemory: AthleteMemoryRecord | null | undefined,
): { carryForward: AthleteActiveHypothesis[]; retired: AthleteActiveHypothesis[] } {
  const latest = dailies[dailies.length - 1];
  const currentKeys = new Set((latest?.activeHypotheses ?? []).map((item) => item.key));
  return {
    carryForward: (latest?.activeHypotheses ?? []).map((item) => ({ ...item, status: 'carry_forward' })),
    retired: (priorMemory?.activeHypotheses ?? [])
      .filter((item) => !currentKeys.has(item.key))
      .map((item) => ({ ...item, status: 'retired' })),
  };
}

function buildWeeklyReviewCandidate(
  candidate: string | null,
  reason: string,
): AthleteWeeklyReviewCandidate | null {
  if (!candidate) return null;
  return {
    candidate,
    reason,
    confidence: 'medium',
    ruleBasis: ['weekly review candidate derived from stored daily artifacts'],
  };
}

export function buildWeeklyAthleteSynthesisArtifact(
  input: AthleteWeeklySynthesisInput,
): AthleteWeeklySynthesisResult {
  const history = sortDays(input.history);
  if (!history.length) throw new Error(`No athlete history available for ${input.athleteId}.`);
  const weekEnd = input.asOfDate ?? history[history.length - 1].date;
  const weekStart = startOfWeek(weekEnd);
  const dailies = input.dailyRefreshes
    .filter((daily) => daily.sourceDate >= weekStart && daily.sourceDate <= weekEnd)
    .sort((a, b) => a.sourceDate.localeCompare(b.sourceDate));
  if (!dailies.length) throw new Error(`No daily artifacts available for week ending ${weekEnd}.`);
  const generatedAt = input.generatedAt ?? new Date(`${weekEnd}T18:00:00.000Z`).toISOString();
  const expiresAt = addDays(weekEnd, 7);
  const sourceState = dailies[dailies.length - 1].sourceState;
  const baseline = input.priorMemory?.physiologyBaseline ?? buildPhysiologyBaseline(history, generatedAt);
  const sevenDaySummary = aggregateFromDailyRefreshes(dailies);
  const fourteenDayAggregate = aggregateWindow(inclusiveWindow(history, weekEnd, 14));
  const strongestPatterns = aggregatePatterns(dailies);
  const hypothesisProgress = rollForwardHypotheses(dailies, input.priorMemory);
  const improved = buildExpiringInterpretations(
    'weekly',
    generatedAt,
    buildComparisons(sevenDaySummary, baseline, 'Week')
      .filter((item) => (item.metric === 'recovery' || item.metric === 'hrv' || item.metric === 'sleep') && item.direction === 'up')
      .map((item) => item.interpretation),
    ['weekly improved rollup'],
  );
  const worsened = buildExpiringInterpretations(
    'weekly',
    generatedAt,
    buildComparisons(sevenDaySummary, baseline, 'Week')
      .filter((item) => (item.metric === 'resting_hr' || item.metric === 'strain') ? item.direction === 'up' : item.direction === 'down')
      .map((item) => item.interpretation),
    ['weekly worsened rollup'],
  );
  const unusual = buildExpiringInterpretations(
    'weekly',
    generatedAt,
    dailies.flatMap((daily) => daily.warningFlags.map((flag) => flag.label)).slice(0, 3),
    ['weekly unusual rollup'],
  );
  const likelyDrivers = buildExpiringInterpretations(
    'weekly',
    generatedAt,
    uniqueStrings(
      strongestPatterns.flatMap((pattern) => pattern.evidence).concat(
        hypothesisProgress.carryForward.flatMap((hypothesis) => hypothesis.supportingSignals),
      ),
    ).slice(0, 4),
    ['weekly driver rollup'],
  );
  const dominantDriver = likelyDrivers[0]?.summary ?? null;
  const nextThreeToSevenDayGuidance: AthleteDecisionGuidance[] = [
    {
      horizon: 'next_3_7_days',
      guidance:
        dominantDriver != null
          ? `Plan next week around ${dominantDriver.toLowerCase()}.`
          : 'Use the latest daily refresh and keep next week conservative until more data accumulates.',
      reasons: uniqueStrings([
        ...strongestPatterns.map((pattern) => pattern.label),
        ...hypothesisProgress.carryForward.map((hypothesis) => hypothesis.statement),
      ]).slice(0, 3),
      confidence: coverageConfidence(sourceState, dailies.length),
      ruleBasis: ['weekly guidance derives from stored daily artifacts'],
    },
  ];

  const weeklySynthesis: AthleteWeeklySynthesisArtifact = {
    athleteId: input.athleteId,
    generatedAt,
    expiresAt,
    weekKey: weekKeyFromDate(weekEnd),
    weekStart,
    weekEnd,
    sourceState,
    sourceCoverage: sourceState.sourceCoverage,
    missingInputs: sourceState.missingInputs,
    confidence: coverageConfidence(sourceState, dailies.length),
    ruleBasis: ['weekly synthesis is derived from stored daily artifacts plus 14-day context'],
    derivedFromDailyRefreshDates: dailies.map((daily) => daily.sourceDate),
    sevenDaySummary,
    fourteenDayComparison: [
      compareMetric('recovery', sevenDaySummary.recoveryMean, fourteenDayAggregate.recoveryMean, '7 day vs 14 day recovery'),
      compareMetric('hrv', sevenDaySummary.hrvMean, fourteenDayAggregate.hrvMean, '7 day vs 14 day HRV'),
      compareMetric('resting_hr', sevenDaySummary.restingHrMean, fourteenDayAggregate.restingHrMean, '7 day vs 14 day resting HR'),
      compareMetric('sleep', sevenDaySummary.sleepMean, fourteenDayAggregate.sleepMean, '7 day vs 14 day sleep'),
      compareMetric('strain', sevenDaySummary.strainMean, fourteenDayAggregate.strainMean, '7 day vs 14 day strain'),
      compareMetric('workouts', sevenDaySummary.workoutCount, fourteenDayAggregate.workoutCount, '7 day vs 14 day workouts'),
      compareMetric('grappling_sessions', sevenDaySummary.grapplingCount, fourteenDayAggregate.grapplingCount, '7 day vs 14 day grappling'),
    ],
    baselineComparisons: buildComparisons(sevenDaySummary, baseline, 'Week'),
    dominantDriver,
    strongestPatterns,
    improved,
    worsened,
    unusual,
    likelyDrivers,
    nextThreeToSevenDayGuidance,
    carryForwardHypotheses: hypothesisProgress.carryForward,
    retiredHypotheses: hypothesisProgress.retired,
    largestRiskNextWeek: buildWeeklyReviewCandidate(
      worsened[0]?.summary ?? strongestPatterns.find((pattern) => pattern.key === 'accumulated_fatigue')?.label ?? null,
      'Highest-risk item from weekly deterioration and active fatigue patterns.',
    ),
    largestOpportunityNextWeek: buildWeeklyReviewCandidate(
      improved[0]?.summary ?? strongestPatterns.find((pattern) => pattern.key === 'readiness_rebound')?.label ?? null,
      'Best near-term opportunity from this week’s improvements.',
    ),
    thresholdReviewCandidate: buildWeeklyReviewCandidate(
      sourceState.status === 'ready' && strongestPatterns.some((pattern) => pattern.observationCount >= ATHLETE_MEMORY_UPDATE_POLICY.patternPromotionMinimumObservations)
        ? 'threshold_model_review'
        : null,
      'Repeated patterns should be reviewed weekly before changing stable thresholds.',
    ),
    sessionReclassificationCandidate: buildWeeklyReviewCandidate(
      dailies.some((daily) => daily.falseGreenLight.active) ? 'session_gate_review' : null,
      'False green-light days suggest current session permissions may be too permissive.',
    ),
    patternShiftCandidate: buildWeeklyReviewCandidate(
      strongestPatterns.length ? strongestPatterns[0].label : null,
      'Most repeated weekly pattern to review for promotion or retirement.',
    ),
    decisionRuleMisclassifications: dailies
      .filter((daily) => daily.falseGreenLight.active)
      .map((daily) => ({
        candidate: daily.sourceDate,
        reason: 'Day classified green while rolling risk stayed elevated.',
        confidence: daily.falseGreenLight.confidence,
        ruleBasis: daily.falseGreenLight.ruleBasis,
      })),
  };

  const updatedMemory: AthleteMemoryRecord = {
    athleteId: input.athleteId,
    updatedAt: generatedAt,
    physiologyBaseline: baseline,
    observedPatterns: strongestPatterns,
    activeHypotheses: hypothesisProgress.carryForward,
    activeProtocols: input.priorMemory?.activeProtocols ?? [],
    currentBlockSummary: nextThreeToSevenDayGuidance[0].guidance,
    nextSevenDayDecisionRules: nextThreeToSevenDayGuidance,
    latestDailyRefreshAt: input.priorMemory?.latestDailyRefreshAt ?? dailies[dailies.length - 1].generatedAt,
    latestWeeklySynthesisAt: generatedAt,
  };

  return { weeklySynthesis, updatedMemory };
}

export const generateAthleteDailyRefresh = buildDailyAthleteRefreshArtifact;
export const generateAthleteWeeklySynthesis = buildWeeklyAthleteSynthesisArtifact;
