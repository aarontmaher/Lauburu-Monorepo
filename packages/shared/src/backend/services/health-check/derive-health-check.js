"use strict";
/**
 * Athlete health-check — one canonical backend summary that tells the
 * mobile app whether this athlete is in seed mode or live mode, what
 * sources are available, what artifacts are fresh, and what the API AI
 * is safe to do right now.
 *
 * Pure function — reads from existing backend state, derives everything.
 * Does NOT write anything. Does NOT call live WHOOP.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.deriveHealthCheck = deriveHealthCheck;
// ---------------------------------------------------------------------------
// Derivation
// ---------------------------------------------------------------------------
function deriveHealthCheck(input) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p;
    const { athleteId, today, dailyArtifact, weeklyArtifact, stableMemory, whoopHealth } = input;
    const now = new Date().toISOString();
    // Mode derivation
    const hasMemory = stableMemory != null;
    const whoopFresh = (whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.freshnessStatus) === 'fresh';
    const whoopConnected = whoopHealth != null && whoopHealth.upstreamStatus !== 'unknown';
    const dailyFreshToday = (dailyArtifact === null || dailyArtifact === void 0 ? void 0 : dailyArtifact.sourceDate) === today;
    const hasSeedMarker = (dailyArtifact === null || dailyArtifact === void 0 ? void 0 : dailyArtifact.seedMode) === true;
    let mode;
    if (!hasMemory) {
        mode = 'uninitialized';
    }
    else if (whoopFresh && dailyFreshToday && !hasSeedMarker) {
        mode = 'live_ready';
    }
    else if (whoopConnected && !whoopFresh) {
        mode = 'live_partial';
    }
    else {
        mode = 'seed_partial';
    }
    const seedMode = mode === 'seed_partial' || mode === 'uninitialized';
    const provisionalUntilDirectWhoop = !whoopFresh;
    // Source health
    const coverageByDomain = [];
    const missingFields = [];
    const domainMap = (_a = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.coverageByDomain) !== null && _a !== void 0 ? _a : {};
    for (const [domain, info] of Object.entries(domainMap)) {
        const domInfo = info;
        coverageByDomain.push({
            domain,
            lastDate: domInfo.lastDate,
            status: (_b = domInfo.status) !== null && _b !== void 0 ? _b : 'missing',
        });
        if (domInfo.status === 'missing' || domInfo.status === 'stale') {
            missingFields.push(domain);
        }
    }
    // Standard WHOOP domains we expect
    for (const expected of ['recovery', 'sleep', 'strain', 'workouts']) {
        if (!coverageByDomain.some((d) => d.domain === expected)) {
            coverageByDomain.push({ domain: expected, lastDate: null, status: 'not_configured' });
            missingFields.push(expected);
        }
    }
    // Artifact freshness
    const dailySummary = {
        type: 'daily',
        available: dailyArtifact != null,
        sourceDate: (_c = dailyArtifact === null || dailyArtifact === void 0 ? void 0 : dailyArtifact.sourceDate) !== null && _c !== void 0 ? _c : null,
        isFreshForToday: dailyFreshToday,
        confidence: (_d = dailyArtifact === null || dailyArtifact === void 0 ? void 0 : dailyArtifact.confidence) !== null && _d !== void 0 ? _d : null,
    };
    const weeklySummary = {
        type: 'weekly',
        available: weeklyArtifact != null,
        sourceDate: (_e = weeklyArtifact === null || weeklyArtifact === void 0 ? void 0 : weeklyArtifact.weekEnd) !== null && _e !== void 0 ? _e : null,
        isFreshForToday: weeklyArtifact != null, // weekly is valid for the whole week
        confidence: (_f = weeklyArtifact === null || weeklyArtifact === void 0 ? void 0 : weeklyArtifact.confidence) !== null && _f !== void 0 ? _f : null,
    };
    // Safe/not-safe derivation
    const safeFor = [];
    const notSafeFor = [];
    if (hasMemory)
        safeFor.push('read_stable_memory');
    if (weeklyArtifact)
        safeFor.push('read_weekly_trends');
    if (dailyArtifact)
        safeFor.push('read_daily_artifact');
    if (dailyFreshToday)
        safeFor.push('display_todays_readiness');
    if (mode === 'live_ready')
        safeFor.push('full_coaching_recommendations');
    if (!hasMemory)
        notSafeFor.push('any_coaching_behavior');
    if (!dailyFreshToday)
        notSafeFor.push('display_todays_readiness_as_current');
    if (seedMode)
        notSafeFor.push('claim_live_whoop_backed_analysis');
    if (missingFields.includes('recovery'))
        notSafeFor.push('display_recovery_score_as_live');
    if (missingFields.includes('strain'))
        notSafeFor.push('display_strain_as_live');
    // Recommended read order
    const recommendedReadOrder = [
        dailyFreshToday ? 'daily_refresh_artifact (fresh)' : dailyArtifact ? 'daily_refresh_artifact (stale)' : null,
        weeklyArtifact ? 'weekly_synthesis_artifact' : null,
        hasMemory ? 'stable_athlete_memory' : null,
        'normalized_daily_metrics',
        'raw_source_records',
        provisionalUntilDirectWhoop ? null : 'live_whoop (if freshness allows)',
    ].filter(Boolean);
    // Transition state
    const lastTransitionAttempt = {
        attempted: (whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.lastFailedIngestAt) != null || (whoopFresh && !hasSeedMarker),
        succeededAt: whoopFresh && !hasSeedMarker ? (_g = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.lastSuccessfulIngestAt) !== null && _g !== void 0 ? _g : null : null,
        failedAt: (_h = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.lastFailedIngestAt) !== null && _h !== void 0 ? _h : null,
        failedReason: (_j = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.degradedReason) !== null && _j !== void 0 ? _j : null,
    };
    return {
        athleteId,
        checkedAt: now,
        mode,
        seedMode,
        provisionalUntilDirectWhoop,
        sourceHealth: {
            whoop: {
                connected: whoopConnected,
                freshnessStatus: (_k = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.freshnessStatus) !== null && _k !== void 0 ? _k : 'not_configured',
                upstreamStatus: (_l = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.upstreamStatus) !== null && _l !== void 0 ? _l : 'unknown',
                lastIngestAt: (_m = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.lastSuccessfulIngestAt) !== null && _m !== void 0 ? _m : null,
                degradedReason: (_o = whoopHealth === null || whoopHealth === void 0 ? void 0 : whoopHealth.degradedReason) !== null && _o !== void 0 ? _o : null,
            },
            coverageByDomain,
        },
        artifacts: {
            daily: dailySummary,
            weekly: weeklySummary,
            stableMemoryPresent: hasMemory,
            stableMemoryUpdatedAt: (_p = stableMemory === null || stableMemory === void 0 ? void 0 : stableMemory.updatedAt) !== null && _p !== void 0 ? _p : null,
        },
        missingWhoopNativeFields: missingFields,
        safeFor,
        notSafeFor,
        recommendedReadOrder,
        lastTransitionAttempt,
    };
}
