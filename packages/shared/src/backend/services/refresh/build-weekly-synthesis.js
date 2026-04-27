"use strict";
/**
 * Weekly synthesis artifact builder — Layer 3 (interpreted).
 *
 * Consumes:
 *   - DailyRefreshArtifact[] (Layer 3, 7 days of daily artifacts)
 *   - AthletePhysiologyBaseline (Layer 4, stable memory)
 *
 * Produces:
 *   - WeeklySynthesisArtifact (Layer 3, weekly rollup)
 *
 * Non-negotiable:
 *   - Never mutates stable memory.
 *   - May produce PromotionCandidates but NEVER auto-promotes.
 *   - Promotion candidates are explicit typed records, not side-effects.
 *   - Every output carries confidence, coverage, provenance, evidence basis.
 *   - Missing daily artifacts stay explicit in missingDays.
 *
 * Internal-only: called by /v1/internal/jobs/weekly-synthesis.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildWeeklySynthesisArtifact = buildWeeklySynthesisArtifact;
const DERIVATION_VERSION = 'weekly_synthesis_v1';
let _idCounter = 0;
function generateId(weekStart) {
    return `wsa_${weekStart}_${Date.now()}_${++_idCounter}`;
}
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function allDatesInWeek(start, end) {
    const dates = [];
    const d = new Date(`${start}T00:00:00Z`);
    const endD = new Date(`${end}T00:00:00Z`);
    while (d <= endD) {
        dates.push(d.toISOString().slice(0, 10));
        d.setUTCDate(d.getUTCDate() + 1);
    }
    return dates;
}
function mean(values) {
    const valid = values.filter((v) => v != null);
    if (valid.length === 0)
        return null;
    return Math.round((valid.reduce((a, b) => a + b, 0) / valid.length) * 100) / 100;
}
function extractMetricValues(artifacts, metric) {
    return artifacts.map((a) => {
        var _a;
        const fact = a.facts.find((f) => f.metric === metric);
        return (_a = fact === null || fact === void 0 ? void 0 : fact.value) !== null && _a !== void 0 ? _a : null;
    });
}
function computeTrend(values, invertForBetter = false) {
    const valid = values.filter((v) => v != null);
    if (valid.length < 3)
        return 'insufficient_data';
    const mid = Math.floor(valid.length / 2);
    const firstHalf = valid.slice(0, mid);
    const secondHalf = valid.slice(mid);
    const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    if (avgFirst === 0)
        return 'stable';
    const pctChange = ((avgSecond - avgFirst) / Math.abs(avgFirst)) * 100;
    // For resting HR: lower is better, so invert
    const effective = invertForBetter ? -pctChange : pctChange;
    if (effective > 3)
        return 'improving';
    if (effective < -3)
        return 'declining';
    return 'stable';
}
// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------
function buildTrends(artifacts, baseline) {
    const metrics = [
        { metric: 'recovery', baselineVal: baseline.recoveryBaseline, invertTrend: false },
        { metric: 'hrv', baselineVal: baseline.hrvBaseline, invertTrend: false },
        { metric: 'resting_hr', baselineVal: baseline.restingHrBaseline, invertTrend: true },
        { metric: 'sleep', baselineVal: baseline.sleepBaseline, invertTrend: false },
        { metric: 'strain', baselineVal: baseline.strainBaseline, invertTrend: true },
    ];
    return metrics.map(({ metric, baselineVal, invertTrend }) => {
        const values = extractMetricValues(artifacts, metric);
        const weekMean = mean(values);
        const deltaPct = weekMean != null && baselineVal != null && baselineVal !== 0
            ? Math.round(((weekMean - baselineVal) / Math.abs(baselineVal)) * 1000) / 10
            : null;
        return {
            metric,
            weekMean,
            baselineValue: baselineVal,
            deltaPct,
            trend: computeTrend(values, invertTrend),
        };
    });
}
// ---------------------------------------------------------------------------
// Interpretations
// ---------------------------------------------------------------------------
function buildInterpretations(trends, artifacts) {
    var _a;
    const improved = [];
    const worsened = [];
    for (const t of trends) {
        if (t.trend === 'improving' && t.deltaPct != null) {
            improved.push(`${t.metric} improving (week mean ${t.deltaPct > 0 ? '+' : ''}${t.deltaPct}% vs baseline)`);
        }
        if (t.trend === 'declining' && t.deltaPct != null) {
            worsened.push(`${t.metric} declining (week mean ${t.deltaPct > 0 ? '+' : ''}${t.deltaPct}% vs baseline)`);
        }
    }
    // Unusual: days where warning flags fired
    const unusual = [...new Set(artifacts.flatMap((a) => a.warningFlags.filter((w) => w.level === 'warning').map((w) => w.label)))].slice(0, 3);
    // Likely drivers: most common key drivers across the week
    const driverCounts = new Map();
    for (const a of artifacts) {
        for (const d of a.keyDrivers) {
            driverCounts.set(d, ((_a = driverCounts.get(d)) !== null && _a !== void 0 ? _a : 0) + 1);
        }
    }
    const likelyDrivers = [...driverCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
        .map(([d]) => d);
    return { improved, worsened, unusual, likelyDrivers };
}
// ---------------------------------------------------------------------------
// Promotion candidates — explicit, typed, never auto-promoted
// ---------------------------------------------------------------------------
function buildPromotionCandidates(trends, artifacts, weekStart, weekEnd) {
    var _a;
    const candidates = [];
    const window = { start: weekStart, end: weekEnd };
    // Check if a pattern appeared consistently (3+ days)
    const patternCounts = new Map();
    for (const a of artifacts) {
        for (const p of a.activePatterns) {
            patternCounts.set(p.key, ((_a = patternCounts.get(p.key)) !== null && _a !== void 0 ? _a : 0) + 1);
        }
    }
    for (const [key, count] of patternCounts) {
        if (count >= 3) {
            candidates.push({
                targetDoc: 'recurring_patterns',
                candidateStatement: `Pattern "${key}" observed ${count}/${artifacts.length} days this week`,
                evidenceWindow: window,
                evidenceStrength: count >= 5 ? 'high' : 'medium',
                eligible: count >= 3,
                approvalRequired: true,
                rejectionReason: null,
            });
        }
    }
    // Check if baseline may need recalculation
    const recoveryTrend = trends.find((t) => t.metric === 'recovery');
    if (recoveryTrend && recoveryTrend.deltaPct != null && Math.abs(recoveryTrend.deltaPct) > 15) {
        candidates.push({
            targetDoc: 'baseline_profile',
            candidateStatement: `Recovery mean shifted ${recoveryTrend.deltaPct > 0 ? '+' : ''}${recoveryTrend.deltaPct}% from baseline — consider recomputing`,
            evidenceWindow: window,
            evidenceStrength: 'medium',
            eligible: true,
            approvalRequired: true,
            rejectionReason: null,
        });
    }
    return candidates;
}
// ---------------------------------------------------------------------------
// Guidance
// ---------------------------------------------------------------------------
function buildNextWeekGuidance(trends, interp, confidence) {
    const guidance = [];
    const recoveryTrend = trends.find((t) => t.metric === 'recovery');
    const sleepTrend = trends.find((t) => t.metric === 'sleep');
    if ((recoveryTrend === null || recoveryTrend === void 0 ? void 0 : recoveryTrend.trend) === 'declining') {
        guidance.push({
            guidance: 'Recovery trended down this week. Prioritize rest and reduce session intensity.',
            reasons: interp.worsened.slice(0, 2),
            evidenceBasis: [`Recovery trend: ${recoveryTrend.trend}`, `Week mean delta: ${recoveryTrend.deltaPct}%`],
            confidence,
        });
    }
    if ((sleepTrend === null || sleepTrend === void 0 ? void 0 : sleepTrend.trend) === 'declining') {
        guidance.push({
            guidance: 'Sleep trended below baseline. Protect sleep opportunity before adding training load.',
            reasons: [`Sleep week mean ${sleepTrend.deltaPct}% vs baseline`],
            evidenceBasis: [`Sleep trend: ${sleepTrend.trend}`],
            confidence,
        });
    }
    if (guidance.length === 0) {
        const dominant = interp.likelyDrivers[0];
        guidance.push({
            guidance: dominant
                ? `Continue current approach. Monitor: ${dominant}.`
                : 'Continue current training approach.',
            reasons: interp.likelyDrivers.slice(0, 2),
            evidenceBasis: ['No strong directional trend detected'],
            confidence,
        });
    }
    return guidance;
}
// ---------------------------------------------------------------------------
// Main builder
// ---------------------------------------------------------------------------
/**
 * Build a WeeklySynthesisArtifact from stored daily artifacts + baseline.
 *
 * Pure function. NEVER mutates stable memory. May produce
 * PromotionCandidates but NEVER auto-promotes them.
 */
function buildWeeklySynthesisArtifact(input) {
    var _a, _b;
    const { athleteId, weekStart, weekEnd, dailyArtifacts, baseline } = input;
    const now = new Date().toISOString();
    // Sort daily artifacts by date
    const sorted = [...dailyArtifacts].sort((a, b) => a.sourceDate.localeCompare(b.sourceDate));
    // Find missing days
    const expectedDays = allDatesInWeek(weekStart, weekEnd);
    const presentDays = new Set(sorted.map((a) => a.sourceDate));
    const missingDays = expectedDays.filter((d) => !presentDays.has(d));
    // Trends
    const trends = buildTrends(sorted, baseline);
    const dominantDriver = (_b = (_a = trends
        .filter((t) => t.trend === 'declining' && t.deltaPct != null)
        .sort((a, b) => Math.abs(b.deltaPct) - Math.abs(a.deltaPct))[0]) === null || _a === void 0 ? void 0 : _a.metric) !== null && _b !== void 0 ? _b : null;
    // Sessions
    const sessions = {
        totalCount: sorted.reduce((n, a) => {
            const wFact = a.facts.find((f) => f.metric === 'strain');
            return n + (wFact && wFact.value != null && wFact.value > 0 ? 1 : 0);
        }, 0),
        grapplingCount: sorted.filter((a) => a.sessionGate.allowedTypes.some((t) => t.includes('grappling'))).length,
        restDays: sorted.filter((a) => a.dayState === 'red' || a.dayState === 'blocked').length,
    };
    // Interpretations
    const interp = buildInterpretations(trends, sorted);
    // Coverage
    const totalMissing = [...new Set(sorted.flatMap((a) => a.coverage.missingFields))];
    const coverage = {
        presentCount: sorted.length,
        totalExpected: expectedDays.length,
        missingFields: totalMissing,
        status: sorted.length >= 5 ? 'complete' : sorted.length >= 3 ? 'partial' : 'minimal',
    };
    // Confidence
    const confidence = coverage.status === 'complete' && baseline.dataWindowDays >= 14 ? 'high'
        : coverage.status !== 'minimal' ? 'medium'
            : 'low';
    // Provenance
    const provenance = {
        sourceRefs: sorted.map((a) => ({
            layer: 'artifact',
            recordId: a.id,
            fieldPath: null,
            date: a.sourceDate,
        })),
        normalizedRecordIds: [...new Set(sorted.flatMap((a) => a.provenance.normalizedRecordIds))],
        rawRecordIds: [...new Set(sorted.flatMap((a) => a.provenance.rawRecordIds))],
    };
    // Guidance
    const nextWeekGuidance = buildNextWeekGuidance(trends, interp, confidence);
    // Promotion candidates
    const promotionCandidates = buildPromotionCandidates(trends, sorted, weekStart, weekEnd);
    // Fresh for 7 days from week end
    const freshUntilDate = new Date(`${weekEnd}T00:00:00Z`);
    freshUntilDate.setUTCDate(freshUntilDate.getUTCDate() + 7);
    const freshUntil = freshUntilDate.toISOString();
    return {
        id: generateId(weekStart),
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        derivationVersion: DERIVATION_VERSION,
        athleteId,
        weekStart,
        weekEnd,
        generatedAt: now,
        freshUntil,
        dailyArtifactCount: sorted.length,
        dailyArtifactIds: sorted.map((a) => a.id),
        missingDays,
        trends,
        dominantDriver,
        sessions,
        improved: interp.improved,
        worsened: interp.worsened,
        unusual: interp.unusual,
        likelyDrivers: interp.likelyDrivers,
        nextWeekGuidance,
        promotionCandidates,
        confidence,
        coverage,
        provenance,
        evidenceBasis: [
            `${DERIVATION_VERSION}`,
            `${sorted.length}/${expectedDays.length} daily artifacts`,
            `Baseline window: ${baseline.dataWindowDays} days`,
            missingDays.length > 0 ? `Missing: ${missingDays.join(', ')}` : 'Full week coverage',
        ],
    };
}
