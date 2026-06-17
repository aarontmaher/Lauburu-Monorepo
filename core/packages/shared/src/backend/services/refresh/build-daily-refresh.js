"use strict";
/**
 * Daily refresh artifact builder — Layer 3 (interpreted).
 *
 * Consumes:
 *   - NormalizedDailyMetrics (Layer 2, interpretation-free)
 *   - AthletePhysiologyBaseline (Layer 4, stable memory)
 *   - AthleteDailyDecisionEngineConfig (typed thresholds)
 *
 * Produces:
 *   - DailyRefreshArtifact (Layer 3, athlete-relative interpretation)
 *
 * This is where baseline-dependent flags live. The normalized layer
 * has none. All interpretation — readiness classification, risk
 * scoring, session gating, pattern detection — happens here.
 *
 * Non-negotiable:
 *   - This function NEVER mutates stable memory.
 *   - Missing normalized fields stay explicitly missing in the artifact.
 *   - Every recommendation carries confidence, evidence basis, and coverage.
 *   - Provenance traces back to normalized and raw record IDs.
 *
 * Internal-only: called by /v1/internal/jobs/daily-refresh.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildDailyRefreshArtifact = buildDailyRefreshArtifact;
const config_1 = require("../../../athlete-memory/config");
const DERIVATION_VERSION = 'daily_refresh_v1';
let _idCounter = 0;
function generateId(date) {
    return `dra_${date}_${Date.now()}_${++_idCounter}`;
}
// ---------------------------------------------------------------------------
// Baseline comparison (all interpretation lives HERE, not in normalized)
// ---------------------------------------------------------------------------
function compareToBaseline(metric, unit, current, baseline, invertDelta = false) {
    if (current == null) {
        return { metric, value: null, unit, baselineValue: baseline, deltaPct: null, status: 'missing' };
    }
    if (baseline == null || baseline === 0) {
        return { metric, value: current, unit, baselineValue: null, deltaPct: null, status: 'normal' };
    }
    const raw = ((current - baseline) / baseline) * 100;
    const deltaPct = Math.round(raw * 10) / 10;
    // For resting HR: higher = worse. For others: lower = worse.
    const isWorse = invertDelta ? deltaPct > 0 : deltaPct < 0;
    const isElevated = invertDelta ? deltaPct > 0 : false;
    const isSuppressed = !invertDelta ? deltaPct < 0 : false;
    const absD = Math.abs(deltaPct);
    let status = 'normal';
    if (absD > 10)
        status = isWorse ? (isSuppressed ? 'suppressed' : 'elevated') : 'normal';
    else if (absD > 5)
        status = isWorse ? (isSuppressed ? 'suppressed' : 'elevated') : 'normal';
    return { metric, value: current, unit, baselineValue: baseline, deltaPct, status };
}
// ---------------------------------------------------------------------------
// Day state classification
// ---------------------------------------------------------------------------
function classifyDay(facts, config, today, baseline) {
    let score = 50;
    const reasons = [];
    const t = config.thresholds;
    function ratio(current, base) {
        if (current == null || base == null || base === 0)
            return null;
        return current / base;
    }
    const recoveryR = ratio(today.recoveryScore, baseline.recoveryBaseline);
    if (recoveryR != null) {
        if (recoveryR <= t.recoveryBelowBaseline.warningPct) {
            score -= 20;
            reasons.push('Recovery materially below baseline');
        }
        else if (recoveryR <= t.recoveryBelowBaseline.cautionPct) {
            score -= 10;
            reasons.push('Recovery below baseline');
        }
        else if (recoveryR >= 1.05) {
            score += 10;
            reasons.push('Recovery above baseline');
        }
    }
    const hrvR = ratio(today.hrvMs, baseline.hrvBaseline);
    if (hrvR != null) {
        if (hrvR <= t.hrvBelowBaseline.warningPct) {
            score -= 15;
            reasons.push('HRV materially suppressed');
        }
        else if (hrvR <= t.hrvBelowBaseline.cautionPct) {
            score -= 8;
            reasons.push('HRV below baseline');
        }
    }
    const rhrR = ratio(today.restingHrBpm, baseline.restingHrBaseline);
    if (rhrR != null) {
        if (rhrR >= t.restingHrAboveBaseline.warningPct) {
            score -= 15;
            reasons.push('Resting HR materially elevated');
        }
        else if (rhrR >= t.restingHrAboveBaseline.cautionPct) {
            score -= 8;
            reasons.push('Resting HR elevated');
        }
    }
    const sleepR = ratio(today.totalSleepHours, baseline.sleepBaseline);
    if (sleepR != null) {
        if (sleepR <= t.sleepBelowBaseline.warningPct) {
            score -= 12;
            reasons.push('Sleep materially below baseline');
        }
        else if (sleepR <= t.sleepBelowBaseline.cautionPct) {
            score -= 6;
            reasons.push('Sleep below baseline');
        }
        else if (sleepR >= 1.03) {
            score += 5;
            reasons.push('Sleep above baseline');
        }
    }
    score = Math.max(0, Math.min(100, score));
    const state = score >= config.greenCutoff ? 'green'
        : score >= config.yellowCutoff ? 'yellow'
            : 'red';
    return { state, score, reasons };
}
// ---------------------------------------------------------------------------
// Rolling 3-day risk
// ---------------------------------------------------------------------------
function computeRollingRisk(recent, baseline, config, thresholds) {
    let score = 0;
    const drivers = [];
    const window = recent.slice(-config.windowDays);
    function countBelow(extract, base, threshold) {
        if (base == null)
            return 0;
        return window.filter((d) => {
            const v = extract(d);
            return v != null && v / base <= threshold;
        }).length;
    }
    function countAbove(extract, base, threshold) {
        if (base == null)
            return 0;
        return window.filter((d) => {
            const v = extract(d);
            return v != null && v / base >= threshold;
        }).length;
    }
    if (countBelow((d) => d.recoveryScore, baseline.recoveryBaseline, thresholds.recoveryBelowBaseline.cautionPct) >= 2) {
        score += config.lowRecoveryWeight;
        drivers.push('Multiple low-recovery days');
    }
    if (countBelow((d) => d.hrvMs, baseline.hrvBaseline, thresholds.hrvBelowBaseline.cautionPct) >= 2) {
        score += config.lowHrvWeight;
        drivers.push('Multiple low-HRV days');
    }
    if (countAbove((d) => d.restingHrBpm, baseline.restingHrBaseline, thresholds.restingHrAboveBaseline.cautionPct) >= 2) {
        score += config.highRestingHrWeight;
        drivers.push('Resting HR stayed elevated');
    }
    if (countBelow((d) => d.totalSleepHours, baseline.sleepBaseline, thresholds.sleepBelowBaseline.cautionPct) >= 2) {
        score += config.lowSleepWeight;
        drivers.push('Sleep stayed below baseline');
    }
    const consecutiveTraining = window.filter((d) => d.workoutCount > 0).length;
    if (consecutiveTraining === window.length && window.length >= 3) {
        score += config.consecutiveLoadWeight;
        drivers.push('No rest day in rolling window');
    }
    const level = score >= config.highRiskCutoff ? 'high'
        : score >= config.elevatedRiskCutoff ? 'elevated'
            : score >= 20 ? 'moderate'
                : 'low';
    return { level, score, drivers };
}
// ---------------------------------------------------------------------------
// Session gating
// ---------------------------------------------------------------------------
function buildSessionGate(dayState, riskLevel) {
    if (riskLevel === 'high') {
        return { gate: 'blocked', allowedTypes: ['rest', 'mobility'], maxIntensity: 'rest_only', cautions: ['High rolling risk'] };
    }
    switch (dayState) {
        case 'green':
            return { gate: 'green', allowedTypes: ['grappling', 'strength', 'conditioning', 'technique'], maxIntensity: 'hard', cautions: [] };
        case 'yellow':
            return { gate: 'yellow', allowedTypes: ['technique', 'moderate_lifting', 'zone2', 'mobility'], maxIntensity: 'moderate', cautions: ['Moderate readiness'] };
        case 'red':
            return { gate: 'red', allowedTypes: ['technique', 'mobility', 'walk'], maxIntensity: 'light', cautions: ['Low readiness'] };
        default:
            return { gate: 'blocked', allowedTypes: ['rest', 'mobility'], maxIntensity: 'rest_only', cautions: ['Blocked state'] };
    }
}
// ---------------------------------------------------------------------------
// Recommendation
// ---------------------------------------------------------------------------
function buildRecommendation(dayState, reasons, riskDrivers, confidence) {
    const guidanceMap = {
        green: 'Train normally. Respect rolling risk if it rises tomorrow.',
        yellow: 'Bias toward technical work and moderate load.',
        red: 'Protect recovery. Avoid high-intensity sessions.',
        blocked: 'Rest day strongly recommended.',
    };
    return {
        guidance: guidanceMap[dayState],
        reasons: [...reasons, ...riskDrivers].slice(0, 5),
        evidenceBasis: [
            'Day classification from athlete-relative thresholds (v1)',
            'Rolling 3-day risk from multi-metric convergence (v1)',
            `Based on ${reasons.length} baseline comparison signals`,
        ],
        confidence,
    };
}
// ---------------------------------------------------------------------------
// Main builder
// ---------------------------------------------------------------------------
/**
 * Build a DailyRefreshArtifact from normalized metrics + athlete baseline.
 *
 * Pure function. Never mutates stable memory. Never calls live WHOOP.
 * All interpretation that depends on athlete baselines happens here,
 * not in the normalized layer.
 */
function buildDailyRefreshArtifact(input) {
    var _a, _b;
    const { today, recent3Days, baseline } = input;
    const config = (_a = input.engineConfig) !== null && _a !== void 0 ? _a : config_1.ATHLETE_DAILY_DECISION_ENGINE_CONFIG;
    const riskConfig = (_b = input.riskConfig) !== null && _b !== void 0 ? _b : config_1.ATHLETE_ROLLING_3_DAY_RISK_MODEL;
    const now = new Date().toISOString();
    // Baseline-compared facts (THIS is where baseline flags live)
    const facts = [
        compareToBaseline('recovery', '%', today.recoveryScore, baseline.recoveryBaseline),
        compareToBaseline('hrv', 'ms', today.hrvMs, baseline.hrvBaseline),
        compareToBaseline('resting_hr', 'bpm', today.restingHrBpm, baseline.restingHrBaseline, true),
        compareToBaseline('sleep', 'h', today.totalSleepHours, baseline.sleepBaseline),
        compareToBaseline('strain', '', today.dailyStrain, baseline.strainBaseline, true),
        compareToBaseline('spo2', '%', today.spo2Pct, null),
        compareToBaseline('respiratory_rate', 'rpm', today.respiratoryRate, null),
    ];
    // Day classification
    const day = classifyDay(facts, config, today, baseline);
    // Rolling risk
    const risk = computeRollingRisk(recent3Days, baseline, riskConfig, config.thresholds);
    // Session gate
    const sessionGate = buildSessionGate(day.state, risk.level);
    // Coverage
    const coverage = {
        presentCount: today.presentFields.length,
        totalExpected: today.presentFields.length + today.missingFields.length,
        missingFields: today.missingFields,
        status: today.completeness,
    };
    // Confidence
    const confidence = coverage.status === 'complete' && baseline.dataWindowDays >= 14 ? 'high'
        : coverage.status !== 'minimal' && baseline.dataWindowDays >= 7 ? 'medium'
            : 'low';
    // Provenance
    const sourceRefs = [
        { layer: 'normalized', recordId: today.id, fieldPath: null, date: today.date },
        ...today.sourceRefs,
    ];
    const provenance = {
        sourceRefs,
        normalizedRecordIds: [today.id, ...recent3Days.map((d) => d.id)],
        rawRecordIds: [...new Set([...today.sourceRecordIds, ...recent3Days.flatMap((d) => d.sourceRecordIds)])],
    };
    // Patterns (simple — detected from facts, not from history scan)
    const activePatterns = [];
    if (risk.level === 'elevated' || risk.level === 'high') {
        activePatterns.push({ key: 'accumulated_fatigue', label: 'Accumulated fatigue pressure', observationCount: risk.drivers.length, confidence: risk.level === 'high' ? 'high' : 'medium' });
    }
    const sleepFact = facts.find((f) => f.metric === 'sleep');
    if (sleepFact && sleepFact.status === 'suppressed') {
        activePatterns.push({ key: 'sleep_deficit', label: 'Sleep below baseline', observationCount: 1, confidence: 'medium' });
    }
    // Warning flags
    const warningFlags = [];
    if (risk.level === 'high')
        warningFlags.push({ level: 'warning', label: 'High rolling risk' });
    if (risk.level === 'elevated')
        warningFlags.push({ level: 'watch', label: 'Elevated rolling risk' });
    facts.filter((f) => f.status === 'suppressed' || f.status === 'elevated').forEach((f) => {
        warningFlags.push({ level: 'watch', label: `${f.metric} is ${f.status} vs baseline` });
    });
    if (today.missingFields.length > 0) {
        warningFlags.push({ level: 'info', label: `Missing: ${today.missingFields.join(', ')}` });
    }
    // Key drivers
    const keyDrivers = [...new Set([...day.reasons, ...risk.drivers])].slice(0, 5);
    // Fresh until end of source date
    const freshUntil = `${today.date}T23:59:59.000Z`;
    return {
        id: generateId(today.date),
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        derivationVersion: DERIVATION_VERSION,
        athleteId: today.athleteId,
        sourceDate: today.date,
        generatedAt: now,
        freshUntil,
        dayState: day.state,
        dayScore: day.score,
        rollingRiskLevel: risk.level,
        rollingRiskScore: risk.score,
        rollingRiskDrivers: risk.drivers,
        facts,
        primaryRecommendation: buildRecommendation(day.state, day.reasons, risk.drivers, confidence),
        sessionGate,
        activePatterns,
        warningFlags,
        keyDrivers,
        confidence,
        coverage,
        provenance,
        evidenceBasis: [
            `Day classification: ${config.thresholds.modelVersion}`,
            `Rolling risk: ${riskConfig.modelVersion}`,
            `Baseline window: ${baseline.dataWindowDays} days`,
            `Data completeness: ${coverage.status} (${coverage.presentCount}/${coverage.totalExpected})`,
        ],
    };
}
