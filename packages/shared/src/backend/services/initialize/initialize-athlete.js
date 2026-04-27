"use strict";
/**
 * Athlete initialization — bootstraps stable memory for a new athlete
 * from their first batch of normalized metrics.
 *
 * This is the ONLY path for creating initial stable memory.
 * It computes baselines from available data and creates an empty
 * pattern/hypothesis/protocol state. The athlete can then participate
 * in daily refresh and weekly synthesis flows.
 *
 * Does NOT require pre-existing seeded state.
 * Does NOT require live WHOOP — works from any normalized metrics.
 * Does NOT auto-promote anything — creates a blank slate with baselines.
 *
 * Internal-only: called by /v1/internal/athletes/:athleteId/initialize
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.initializeAthlete = initializeAthlete;
const config_1 = require("../../../athlete-memory/config");
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function mean(values) {
    const valid = values.filter((v) => v != null);
    if (valid.length === 0)
        return null;
    return Math.round((valid.reduce((a, b) => a + b, 0) / valid.length) * 100) / 100;
}
// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------
/**
 * Bootstrap an athlete's stable memory from normalized metrics.
 * Pure function — does NOT write to storage. The caller persists.
 */
function initializeAthlete(input) {
    const { athleteId, history } = input;
    const now = new Date().toISOString();
    const warnings = [];
    if (history.length === 0) {
        return {
            ok: false,
            athleteId,
            memory: null,
            baseline: null,
            confidence: 'low',
            dataWindowDays: 0,
            warnings: ['No normalized metrics available. Cannot initialize.'],
        };
    }
    const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date));
    const windowDays = sorted.length;
    if (windowDays < 3) {
        warnings.push(`Only ${windowDays} day(s) of data. Baselines will be very provisional.`);
    }
    else if (windowDays < 14) {
        warnings.push(`${windowDays} days of data. Baselines are provisional until 14+ days accumulate.`);
    }
    // Compute baselines from all available data
    const baseline = {
        computedAt: now,
        dataWindowDays: windowDays,
        recoveryBaseline: mean(sorted.map((d) => d.recoveryScore)),
        hrvBaseline: mean(sorted.map((d) => d.hrvMs)),
        restingHrBaseline: mean(sorted.map((d) => d.restingHrBpm)),
        sleepBaseline: mean(sorted.map((d) => d.totalSleepHours)),
        strainBaseline: mean(sorted.map((d) => d.dailyStrain)),
        thresholds: config_1.ATHLETE_BASELINE_THRESHOLDS,
        ruleBasis: [
            `Initial baseline from ${windowDays} days of normalized metrics.`,
            windowDays < 14 ? 'Provisional — will stabilize with more data.' : 'Reasonable initial baseline.',
        ],
    };
    // Check which fields are actually populated
    if (baseline.recoveryBaseline == null)
        warnings.push('No recovery data available for baseline.');
    if (baseline.hrvBaseline == null)
        warnings.push('No HRV data available for baseline.');
    if (baseline.restingHrBaseline == null)
        warnings.push('No resting HR data available for baseline.');
    if (baseline.sleepBaseline == null)
        warnings.push('No sleep data available for baseline.');
    const confidence = windowDays >= 14 ? 'high' : windowDays >= 7 ? 'medium' : 'low';
    const memory = {
        athleteId,
        updatedAt: now,
        physiologyBaseline: baseline,
        observedPatterns: [],
        activeHypotheses: [],
        activeProtocols: [],
        currentBlockSummary: `Initialized from ${windowDays} days of data. Baselines are ${confidence === 'high' ? 'stable' : 'provisional'}.`,
        nextSevenDayDecisionRules: [],
        latestDailyRefreshAt: null,
        latestWeeklySynthesisAt: null,
    };
    return {
        ok: true,
        athleteId,
        memory,
        baseline,
        confidence,
        dataWindowDays: windowDays,
        warnings,
    };
}
