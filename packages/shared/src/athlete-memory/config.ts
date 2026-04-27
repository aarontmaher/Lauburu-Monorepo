import type {
  AthleteBaselineThresholds,
  AthleteDailyDecisionEngineConfig,
  AthleteMemoryUpdatePolicy,
  AthleteReboundProtocol,
  AthleteRolling3DayRiskModel,
  AthleteSessionClassificationModel,
  AthleteSymptomOverridePolicy,
} from './types';

export const ATHLETE_BASELINE_THRESHOLDS: AthleteBaselineThresholds = {
  modelVersion: 'v1_relative_baseline_thresholds',
  recoveryBelowBaseline: { cautionPct: 0.9, warningPct: 0.8 },
  hrvBelowBaseline: { cautionPct: 0.9, warningPct: 0.82 },
  restingHrAboveBaseline: { cautionPct: 1.06, warningPct: 1.12 },
  sleepBelowBaseline: { cautionPct: 0.92, warningPct: 0.85 },
  strainAboveBaseline: { cautionPct: 1.08, warningPct: 1.16 },
};

export const ATHLETE_DAILY_DECISION_ENGINE_CONFIG: AthleteDailyDecisionEngineConfig = {
  modelVersion: 'v1_daily_decision_engine',
  thresholds: ATHLETE_BASELINE_THRESHOLDS,
  greenCutoff: 70,
  yellowCutoff: 45,
  falseGreenRiskFloor: 45,
  delayedCrashRiskFloor: 60,
};

export const ATHLETE_ROLLING_3_DAY_RISK_MODEL: AthleteRolling3DayRiskModel = {
  modelVersion: 'v1_rolling_3_day_risk',
  windowDays: 3,
  lowRecoveryWeight: 20,
  lowHrvWeight: 20,
  highRestingHrWeight: 18,
  lowSleepWeight: 14,
  highStrainWeight: 14,
  consecutiveLoadWeight: 14,
  elevatedRiskCutoff: 40,
  highRiskCutoff: 65,
};

export const ATHLETE_SESSION_CLASSIFICATION_MODEL: AthleteSessionClassificationModel = {
  modelVersion: 'v1_session_classification',
  greenAllowed: ['hard_sparring', 'competition_rounds', 'grappling_volume', 'lifting', 'conditioning'],
  yellowAllowed: ['technical_grappling', 'moderate_lifting', 'zone2_conditioning', 'mobility'],
  redAllowed: ['technical_grappling', 'mobility', 'walk'],
  blockedAllowed: ['mobility', 'walk', 'rest'],
  riskyWhenFatigued: ['hard_sparring', 'competition_rounds', 'conditioning'],
};

export const ATHLETE_REBOUND_PROTOCOL: AthleteReboundProtocol = {
  modelVersion: 'v1_rebound_protocol',
  minimumRecoveryPctOfBaseline: 1.03,
  minimumSleepPctOfBaseline: 1.02,
  maximumRiskScoreForRebound: 35,
};

export const ATHLETE_SYMPTOM_OVERRIDE_POLICY: AthleteSymptomOverridePolicy = {
  modelVersion: 'v1_symptom_override_policy',
  severeSymptomsBlockAll: ['fever', 'flu', 'acute_injury', 'migraine'],
  cautionSymptomsForceLightOnly: ['sore_throat', 'headache', 'doms', 'poor_appetite'],
};

export const ATHLETE_MEMORY_UPDATE_POLICY: AthleteMemoryUpdatePolicy = {
  modelVersion: 'v1_memory_update_policy',
  thresholdReviewWeeklyOnly: true,
  patternPromotionMinimumObservations: 3,
  hypothesisExpiryDays: 14,
};
