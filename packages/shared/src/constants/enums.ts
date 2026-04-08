/** Health data providers — matches website PROVIDERS */
export const HealthProvider = {
  WHOOP: 'whoop',
  APPLE_HEALTH: 'apple_health',
  GARMIN: 'garmin',
  POLAR: 'polar',
  CRONOMETER: 'cronometer',
  MANUAL: 'manual',
} as const;
export type HealthProvider = (typeof HealthProvider)[keyof typeof HealthProvider];

/** User roles — matches website ROLES */
export const UserRole = {
  USER: 'user',
  TESTER: 'tester',
  COACH: 'coach',
  OPERATOR: 'operator',
  ADMIN: 'admin',
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

/** Technique progress status */
export const ProgressStatus = {
  NONE: 'none',
  DRILLING: 'drilling',
  LEARNED: 'learned',
} as const;
export type ProgressStatus = (typeof ProgressStatus)[keyof typeof ProgressStatus];

/** Filter modes */
export const FilterMode = {
  ALL: 'all',
  DRILLING: 'drilling',
  LEARNED: 'learned',
  MY_GAME: 'my_game',
} as const;
export type FilterMode = (typeof FilterMode)[keyof typeof FilterMode];

/** Readiness states — matches website readiness_state enum */
export const ReadinessState = {
  EXCELLENT: 'excellent',
  GOOD: 'good',
  UNBALANCED: 'unbalanced',
  UNKNOWN: 'unknown',
} as const;
export type ReadinessState = (typeof ReadinessState)[keyof typeof ReadinessState];

/** Shared memory item types — matches website */
export const MemoryItemType = {
  FACT: 'FACT',
  CONTEXT: 'CONTEXT',
  SUBSTANCE_EVENT: 'SUBSTANCE_EVENT',
  INSIGHT: 'INSIGHT',
  RULE: 'RULE',
  QUESTION: 'QUESTION',
} as const;
export type MemoryItemType = (typeof MemoryItemType)[keyof typeof MemoryItemType];

/** Shared memory item statuses — matches website */
export const MemoryItemStatus = {
  CANDIDATE: 'CANDIDATE',
  UNDER_REVIEW: 'UNDER_REVIEW',
  REVIEWED: 'REVIEWED',
  APPROVED: 'APPROVED',
  REJECTED: 'REJECTED',
  SUPERSEDED: 'SUPERSEDED',
  RESOLVED: 'RESOLVED',
} as const;
export type MemoryItemStatus =
  (typeof MemoryItemStatus)[keyof typeof MemoryItemStatus];
