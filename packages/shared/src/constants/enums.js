"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryItemStatus = exports.MemoryItemType = exports.ReadinessState = exports.FilterMode = exports.ProgressStatus = exports.UserRole = exports.HealthProvider = void 0;
/** Health data providers — matches website PROVIDERS */
exports.HealthProvider = {
    WHOOP: 'whoop',
    APPLE_HEALTH: 'apple_health',
    HEALTH_CONNECT: 'health_connect',
    GARMIN: 'garmin',
    POLAR: 'polar',
    CRONOMETER: 'cronometer',
    MANUAL: 'manual',
};
/** User roles — matches website ROLES */
exports.UserRole = {
    USER: 'user',
    TESTER: 'tester',
    COACH: 'coach',
    OPERATOR: 'operator',
    ADMIN: 'admin',
};
/** Technique progress status */
exports.ProgressStatus = {
    NONE: 'none',
    DRILLING: 'drilling',
    LEARNED: 'learned',
};
/** Filter modes */
exports.FilterMode = {
    ALL: 'all',
    DRILLING: 'drilling',
    LEARNED: 'learned',
    MY_GAME: 'my_game',
};
/** Readiness states — matches website readiness_state enum */
exports.ReadinessState = {
    EXCELLENT: 'excellent',
    GOOD: 'good',
    UNBALANCED: 'unbalanced',
    UNKNOWN: 'unknown',
};
/** Shared memory item types — matches website */
exports.MemoryItemType = {
    FACT: 'FACT',
    CONTEXT: 'CONTEXT',
    SUBSTANCE_EVENT: 'SUBSTANCE_EVENT',
    INSIGHT: 'INSIGHT',
    RULE: 'RULE',
    QUESTION: 'QUESTION',
};
/** Shared memory item statuses — matches website */
exports.MemoryItemStatus = {
    CANDIDATE: 'CANDIDATE',
    UNDER_REVIEW: 'UNDER_REVIEW',
    REVIEWED: 'REVIEWED',
    APPROVED: 'APPROVED',
    REJECTED: 'REJECTED',
    SUPERSEDED: 'SUPERSEDED',
    RESOLVED: 'RESOLVED',
};
