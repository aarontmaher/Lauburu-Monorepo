/**
 * Backend module barrel — re-exports all contracts and services
 * for the cached-artifact-first athlete intelligence backend.
 */

// Contracts
export * from './contracts/whoop-raw.types';
export * from './contracts/normalized-daily.types';
export * from './contracts/refresh-artifacts.types';
export * from './contracts/freshness.types';
export * from './contracts/seeded-athlete-state.types';
export * from './contracts/seed-mode.types';
export * from './contracts/ai-context.types';
export * from './contracts/nutrition-raw.types';
export * from './contracts/coach-answer.types';
export * from './contracts/health-source-raw.types';
export * from './contracts/cronometer.types';
export * from './contracts/machine-connection.types';
export * from './contracts/nutrition-evidence-ingest.types';
export * from './contracts/session-log.types';
export * from './contracts/backlog-analysis.types';
export { compareHiitWorkouts } from './services/hiit/compare-hiit-workouts';
export { ingestSessionLog, ingestAndNormalizeSessionLog } from './services/session/ingest-session-log';
export { DefaultCronometerAdapter, normalizeCronometerDaily } from './services/cronometer/cronometer-adapter';

// Services
export { ingestWhoopDay, ingestWhoopBatch } from './services/whoop/ingest-whoop';
export { ingestNutritionDay, ingestNutritionBatch, isNutritionIngestConfirmed } from './services/nutrition/ingest-nutrition';
export { applyNutritionToNormalized } from './services/nutrition/normalize-nutrition';
export type { WhoopMcpDayPayload } from './services/whoop/ingest-whoop';
export { normalizeWhoopDay, normalizeWhoopBatch } from './services/normalize/normalize-daily-metrics';
export { ingestHealthSourceDay, normalizeHealthSourceDay } from './services/health-source/ingest-health-source';
export { buildMultiSourceHealth } from './services/health-source/build-multi-source-health';
export { buildDailyRefreshArtifact } from './services/refresh/build-daily-refresh';
export type { BuildDailyRefreshInput } from './services/refresh/build-daily-refresh';
export { buildWeeklySynthesisArtifact } from './services/refresh/build-weekly-synthesis';
export type { BuildWeeklySynthesisInput } from './services/refresh/build-weekly-synthesis';
export { shouldReadLiveWhoop } from './services/freshness/should-read-live-whoop';
export { readAthleteState } from './services/orchestrate/read-athlete-state';
export type {
  AthleteStateStore,
  LiveWhoopReader,
  ReadAthleteStateRequest,
  ReadAthleteStateResult,
} from './services/orchestrate/read-athlete-state';
export { applyPromotion } from './services/promote/apply-promotion';
export type { PromotionRequest, PromotionResult, PromotionOutcome } from './services/promote/apply-promotion';
export { initializeAthlete } from './services/initialize/initialize-athlete';
export type { InitializeAthleteInput, InitializeAthleteResult } from './services/initialize/initialize-athlete';
export { deriveHealthCheck } from './services/health-check/derive-health-check';
export type { AthleteHealthCheck, AthleteMode, DeriveHealthCheckInput } from './services/health-check/derive-health-check';
export { buildCoachAnswer } from './services/coach/build-coach-answer';
export { analyseReadiness } from './services/readiness/analyse-readiness';
export type { ReadinessAnalysisInput, ReadinessAnalysisResult, ReadinessLevel, ReadinessMode } from './services/readiness/analyse-readiness';
export { analyseContextualReadiness } from './services/readiness/analyse-contextual-readiness';
export type { ContextualReadinessInput, ContextualReadinessResult, ContextualReadinessLevel, ContextualSignal } from './services/readiness/analyse-contextual-readiness';
export { findTrendCandidates } from './services/backlog/find-trend-candidates';
export type { FindTrendCandidatesInput } from './services/backlog/find-trend-candidates';
export { buildCohortComparisonForTrend, buildBacklogCohortComparison } from './services/backlog/build-cohort-comparison';
export { runBacklogAnalysis, discoverAthleteSources } from './services/backlog/run-backlog-analysis';
export type { BacklogStore, BacklogBuilders } from './services/backlog/run-backlog-analysis';
