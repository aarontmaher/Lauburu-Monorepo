"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ATHLETE_MEMORY_UPDATE_POLICY = exports.ATHLETE_SYMPTOM_OVERRIDE_POLICY = exports.ATHLETE_REBOUND_PROTOCOL = exports.ATHLETE_SESSION_CLASSIFICATION_MODEL = exports.ATHLETE_ROLLING_3_DAY_RISK_MODEL = exports.ATHLETE_DAILY_DECISION_ENGINE_CONFIG = exports.ATHLETE_BASELINE_THRESHOLDS = void 0;
exports.ATHLETE_BASELINE_THRESHOLDS = {
    modelVersion: 'v1_relative_baseline_thresholds',
    recoveryBelowBaseline: { cautionPct: 0.9, warningPct: 0.8 },
    hrvBelowBaseline: { cautionPct: 0.9, warningPct: 0.82 },
    restingHrAboveBaseline: { cautionPct: 1.06, warningPct: 1.12 },
    sleepBelowBaseline: { cautionPct: 0.92, warningPct: 0.85 },
    strainAboveBaseline: { cautionPct: 1.08, warningPct: 1.16 },
};
exports.ATHLETE_DAILY_DECISION_ENGINE_CONFIG = {
    modelVersion: 'v1_daily_decision_engine',
    thresholds: exports.ATHLETE_BASELINE_THRESHOLDS,
    greenCutoff: 70,
    yellowCutoff: 45,
    falseGreenRiskFloor: 45,
    delayedCrashRiskFloor: 60,
};
exports.ATHLETE_ROLLING_3_DAY_RISK_MODEL = {
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
exports.ATHLETE_SESSION_CLASSIFICATION_MODEL = {
    modelVersion: 'v1_session_classification',
    greenAllowed: ['hard_sparring', 'competition_rounds', 'grappling_volume', 'lifting', 'conditioning'],
    yellowAllowed: ['technical_grappling', 'moderate_lifting', 'zone2_conditioning', 'mobility'],
    redAllowed: ['technical_grappling', 'mobility', 'walk'],
    blockedAllowed: ['mobility', 'walk', 'rest'],
    riskyWhenFatigued: ['hard_sparring', 'competition_rounds', 'conditioning'],
};
exports.ATHLETE_REBOUND_PROTOCOL = {
    modelVersion: 'v1_rebound_protocol',
    minimumRecoveryPctOfBaseline: 1.03,
    minimumSleepPctOfBaseline: 1.02,
    maximumRiskScoreForRebound: 35,
};
exports.ATHLETE_SYMPTOM_OVERRIDE_POLICY = {
    modelVersion: 'v1_symptom_override_policy',
    severeSymptomsBlockAll: ['fever', 'flu', 'acute_injury', 'migraine'],
    cautionSymptomsForceLightOnly: ['sore_throat', 'headache', 'doms', 'poor_appetite'],
};
exports.ATHLETE_MEMORY_UPDATE_POLICY = {
    modelVersion: 'v1_memory_update_policy',
    thresholdReviewWeeklyOnly: true,
    patternPromotionMinimumObservations: 3,
    hypothesisExpiryDays: 14,
};
