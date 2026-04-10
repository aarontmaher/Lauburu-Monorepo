export { normalizeDayFromSamples, normalizeHealthData } from './normalize';
export { deriveFeatures, computeFlags } from './derive-features';
export type { HealthFlag } from './derive-features';
export { toBackendPayload } from './persist';
export { buildAIHealthContext } from './ai-context';
export type { AIHealthContext } from './ai-context';
export { generateInsights } from './insights';
export type { TrainingInsight, ReadinessLevel } from './insights';
export { exportAIPayload } from './ai-payload';
export type { AIPayload } from './ai-payload';
export { generateCoaching } from './coaching';
export type { CoachingResponse } from './coaching';
export { mergeTrainingSessions } from './merge-training';
export { summarizeSession } from './session-summary';
export type { SessionSummary, SessionKind, SessionShape } from './session-summary';
export {
  buildDailyCoachingBrief,
  suggestTrainIntensity,
  suggestHIITProtocol,
} from './coach-layer';
export type {
  DailyCoachingBrief,
  WhoopSnapshot,
  PrimaryReadinessSource,
  CoachedMode,
  LoadBand,
  BuildDailyCoachingBriefInputs,
  HIITProtocolSuggestion,
} from './coach-layer';
export { assembleTrainingExample } from './training-example';
export { buildDayPlanSummary, getDayOfWeek } from './plan-status';
export type { PlannedWithStatus, DayPlanSummary, DayPlanStatus, PlannedSessionStatus } from './plan-status';
export { HR_ZONES, REST_COLOR, getHRZone, getHRZoneColor, estimateMaxHR } from './hr-zones';
export type { HRZone } from './hr-zones';
