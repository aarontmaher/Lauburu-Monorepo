import type { DailyMetrics } from '../types/health';

export type AthleteConfidence = 'high' | 'medium' | 'low';
export type AthleteInterpretationKind = 'daily' | 'weekly';
export type AthleteSessionPermissionLevel = 'allowed' | 'risky' | 'banned';
export type AthleteDayState = 'green' | 'yellow' | 'red' | 'blocked';
export type AthleteRollingRiskLevel = 'low' | 'moderate' | 'elevated' | 'high';
export type AthleteSourceType = 'whoop_live' | 'cached_history_file' | 'mixed';
export type AthleteSourceStatus = 'ready' | 'degraded' | 'unavailable';
export type AthleteSourceAuthState =
  | 'authenticated'
  | 'missing'
  | 'stale'
  | 'unknown';
export type AthleteSourceFallbackReason =
  | 'none'
  | 'whoop_mcp_auth_not_restored'
  | 'live_source_unavailable'
  | 'cached_history_only'
  | 'partial_source_coverage';

export interface AthleteRuleMeta {
  confidence: AthleteConfidence;
  ruleBasis: string[];
}

export interface AthleteSourceState extends AthleteRuleMeta {
  sourceType: AthleteSourceType;
  status: AthleteSourceStatus;
  authState: AthleteSourceAuthState;
  latestDataDate: string | null;
  fallbackReason: AthleteSourceFallbackReason;
  sourceCoverage: string[];
  missingInputs: string[];
}

export interface AthleteThresholdBand {
  cautionPct: number;
  warningPct: number;
}

/**
 * Canonical threshold system:
 * athlete-relative thresholds anchored to personal baselines.
 * This wins over coarse absolute thresholds because the product goal
 * is individualized long-history performance tracking.
 */
export interface AthleteBaselineThresholds {
  modelVersion: 'v1_relative_baseline_thresholds';
  recoveryBelowBaseline: AthleteThresholdBand;
  hrvBelowBaseline: AthleteThresholdBand;
  restingHrAboveBaseline: AthleteThresholdBand;
  sleepBelowBaseline: AthleteThresholdBand;
  strainAboveBaseline: AthleteThresholdBand;
}

export interface AthleteDailyDecisionEngineConfig {
  modelVersion: 'v1_daily_decision_engine';
  thresholds: AthleteBaselineThresholds;
  greenCutoff: number;
  yellowCutoff: number;
  falseGreenRiskFloor: number;
  delayedCrashRiskFloor: number;
}

export interface AthleteRolling3DayRiskModel {
  modelVersion: 'v1_rolling_3_day_risk';
  windowDays: 3;
  lowRecoveryWeight: number;
  lowHrvWeight: number;
  highRestingHrWeight: number;
  lowSleepWeight: number;
  highStrainWeight: number;
  consecutiveLoadWeight: number;
  elevatedRiskCutoff: number;
  highRiskCutoff: number;
}

export interface AthleteSessionClassificationModel {
  modelVersion: 'v1_session_classification';
  greenAllowed: string[];
  yellowAllowed: string[];
  redAllowed: string[];
  blockedAllowed: string[];
  riskyWhenFatigued: string[];
}

export interface AthleteReboundProtocol {
  modelVersion: 'v1_rebound_protocol';
  minimumRecoveryPctOfBaseline: number;
  minimumSleepPctOfBaseline: number;
  maximumRiskScoreForRebound: number;
}

export interface AthleteSymptomOverridePolicy {
  modelVersion: 'v1_symptom_override_policy';
  severeSymptomsBlockAll: string[];
  cautionSymptomsForceLightOnly: string[];
}

export interface AthleteMemoryUpdatePolicy {
  modelVersion: 'v1_memory_update_policy';
  thresholdReviewWeeklyOnly: true;
  patternPromotionMinimumObservations: number;
  hypothesisExpiryDays: number;
}

export interface AthletePhysiologyBaseline {
  computedAt: string;
  dataWindowDays: number;
  recoveryBaseline: number | null;
  hrvBaseline: number | null;
  restingHrBaseline: number | null;
  sleepBaseline: number | null;
  strainBaseline: number | null;
  thresholds: AthleteBaselineThresholds;
  ruleBasis: string[];
}

export interface AthleteObservedPattern extends AthleteRuleMeta {
  key: string;
  label: string;
  observationCount: number;
  active: boolean;
  evidence: string[];
}

export interface AthleteActiveHypothesis extends AthleteRuleMeta {
  key: string;
  statement: string;
  status: 'active' | 'carry_forward' | 'retired';
  supportingSignals: string[];
  expiresAt: string;
}

export interface AthleteExpiringInterpretation extends AthleteRuleMeta {
  key: string;
  kind: AthleteInterpretationKind;
  summary: string;
  generatedAt: string;
  expiresAt: string;
}

export interface AthleteProtocolOrExperiment extends AthleteRuleMeta {
  key: string;
  kind: 'supplement' | 'protocol' | 'experiment';
  label: string;
  status: 'active' | 'paused' | 'completed' | 'abandoned';
  startedAt: string;
  plannedReviewAt: string | null;
  expectedOutcome: string;
  observedEffects: string[];
}

export interface AthleteMetricAggregate {
  recoveryMean: number | null;
  hrvMean: number | null;
  restingHrMean: number | null;
  sleepMean: number | null;
  strainMean: number | null;
  workoutCount: number;
  grapplingCount: number;
  restDays: number;
  daysWithData: number;
}

export interface AthleteMetricComparison {
  metric:
    | 'recovery'
    | 'hrv'
    | 'resting_hr'
    | 'sleep'
    | 'strain'
    | 'workouts'
    | 'grappling_sessions';
  currentValue: number | null;
  baselineValue: number | null;
  delta: number | null;
  deltaPct: number | null;
  direction: 'up' | 'down' | 'flat' | 'unknown';
  interpretation: string;
}

export interface AthleteWindowSummary {
  windowDays: 7 | 14 | 30;
  anchorDate: string;
  metrics: AthleteMetricAggregate;
}

export interface AthleteRawDailyInputs {
  latest: {
    date: string;
    recoveryScore: number | null;
    hrvMs: number | null;
    restingHr: number | null;
    sleepHours: number | null;
    dailyStrain: number | null;
    workoutCount: number;
    grapplingToday: boolean;
  };
  rollingSummaries: AthleteWindowSummary[];
}

export interface AthleteDayClassification extends AthleteRuleMeta {
  state: AthleteDayState;
  score: number;
  reasons: string[];
}

export interface AthleteRollingRisk extends AthleteRuleMeta {
  windowDays: 3;
  score: number;
  level: AthleteRollingRiskLevel;
  drivers: string[];
}

export interface AthleteBinarySignal extends AthleteRuleMeta {
  active: boolean;
  reasons: string[];
}

export interface AthleteSymptomOverrideState extends AthleteRuleMeta {
  status: 'none' | 'light_only' | 'blocked';
  matchedSymptoms: string[];
}

export interface AthleteSessionPermissionBucket {
  label: string;
  level: AthleteSessionPermissionLevel;
  reasons: string[];
}

export interface AthleteSessionPermissions extends AthleteRuleMeta {
  allowed: AthleteSessionPermissionBucket[];
  risky: AthleteSessionPermissionBucket[];
  banned: AthleteSessionPermissionBucket[];
}

export interface AthleteWarningFlag extends AthleteRuleMeta {
  level: 'warning' | 'watch' | 'info';
  label: string;
}

export interface AthleteMemoryReviewFlag extends AthleteRuleMeta {
  level: 'weekly_review' | 'pattern_review' | 'session_review';
  label: string;
}

export interface AthleteDecisionGuidance extends AthleteRuleMeta {
  horizon: 'next_1_3_days' | 'next_3_7_days';
  guidance: string;
  reasons: string[];
}

export interface AthleteDailyRefreshArtifact {
  athleteId: string;
  generatedAt: string;
  expiresAt: string;
  sourceDate: string;
  sourceState: AthleteSourceState;
  sourceCoverage: string[];
  missingInputs: string[];
  confidence: AthleteConfidence;
  ruleBasis: string[];
  rawInputs: AthleteRawDailyInputs;
  dayClassification: AthleteDayClassification;
  rollingRisk: AthleteRollingRisk;
  falseGreenLight: AthleteBinarySignal;
  delayedCrashBuild: AthleteBinarySignal;
  symptomOverride: AthleteSymptomOverrideState;
  sessionPermissions: AthleteSessionPermissions;
  nextBestAction: AthleteDecisionGuidance;
  keyDrivers: string[];
  warningFlags: AthleteWarningFlag[];
  recurringPatternsActive: AthleteObservedPattern[];
  activeHypotheses: AthleteActiveHypothesis[];
  expiringInterpretations: AthleteExpiringInterpretation[];
  memoryReviewFlags: AthleteMemoryReviewFlag[];
}

export interface AthleteWeeklyReviewCandidate extends AthleteRuleMeta {
  candidate: string;
  reason: string;
}

export interface AthleteWeeklySynthesisArtifact {
  athleteId: string;
  generatedAt: string;
  expiresAt: string;
  weekKey: string;
  weekStart: string;
  weekEnd: string;
  sourceState: AthleteSourceState;
  sourceCoverage: string[];
  missingInputs: string[];
  confidence: AthleteConfidence;
  ruleBasis: string[];
  derivedFromDailyRefreshDates: string[];
  sevenDaySummary: AthleteMetricAggregate;
  fourteenDayComparison: AthleteMetricComparison[];
  baselineComparisons: AthleteMetricComparison[];
  dominantDriver: string | null;
  strongestPatterns: AthleteObservedPattern[];
  improved: AthleteExpiringInterpretation[];
  worsened: AthleteExpiringInterpretation[];
  unusual: AthleteExpiringInterpretation[];
  likelyDrivers: AthleteExpiringInterpretation[];
  nextThreeToSevenDayGuidance: AthleteDecisionGuidance[];
  carryForwardHypotheses: AthleteActiveHypothesis[];
  retiredHypotheses: AthleteActiveHypothesis[];
  largestRiskNextWeek: AthleteWeeklyReviewCandidate | null;
  largestOpportunityNextWeek: AthleteWeeklyReviewCandidate | null;
  thresholdReviewCandidate: AthleteWeeklyReviewCandidate | null;
  sessionReclassificationCandidate: AthleteWeeklyReviewCandidate | null;
  patternShiftCandidate: AthleteWeeklyReviewCandidate | null;
  decisionRuleMisclassifications: AthleteWeeklyReviewCandidate[];
}

export interface AthleteMemoryRecord {
  athleteId: string;
  updatedAt: string;
  physiologyBaseline: AthletePhysiologyBaseline;
  observedPatterns: AthleteObservedPattern[];
  activeHypotheses: AthleteActiveHypothesis[];
  activeProtocols: AthleteProtocolOrExperiment[];
  currentBlockSummary: string;
  nextSevenDayDecisionRules: AthleteDecisionGuidance[];
  latestDailyRefreshAt: string | null;
  latestWeeklySynthesisAt: string | null;
}

export interface AthleteRefreshInput {
  athleteId: string;
  history: DailyMetrics[];
  sourceState: AthleteSourceState;
  generatedAt?: string;
  priorMemory?: AthleteMemoryRecord | null;
  asOfDate?: string;
  reportedSymptoms?: string[];
}

export interface AthleteDailyRefreshResult {
  dailyRefresh: AthleteDailyRefreshArtifact;
  updatedMemory: AthleteMemoryRecord;
}

export interface AthleteWeeklySynthesisInput extends AthleteRefreshInput {
  dailyRefreshes: AthleteDailyRefreshArtifact[];
}

export interface AthleteWeeklySynthesisResult {
  weeklySynthesis: AthleteWeeklySynthesisArtifact;
  updatedMemory: AthleteMemoryRecord;
}
