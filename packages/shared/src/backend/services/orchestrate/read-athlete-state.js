"use strict";
/**
 * Read orchestrator — enforces cached-artifact-first read order.
 *
 * This is the SINGLE entry point for athlete state reads. All
 * callers (chat, API, jobs) go through this. No caller may
 * bypass this to hit normalized, raw, or live WHOOP directly.
 *
 * Read order (strictly enforced):
 *   1. latest daily_refresh_artifact
 *   2. latest weekly_synthesis_artifact
 *   3. stable private athlete memory
 *   4. normalized_daily_metrics (only if artifact lacks required fields)
 *   5. raw source records (only if normalized lacks required fields)
 *   6. live WHOOP (only if freshness policy explicitly allows)
 *
 * The orchestrator returns a typed result indicating which layers
 * were consulted and why, so callers and the AI can reason about
 * data provenance and freshness without guessing.
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.readAthleteState = readAthleteState;
const should_read_live_whoop_1 = require("../freshness/should-read-live-whoop");
// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------
function todayDate() {
    return new Date().toISOString().slice(0, 10);
}
/**
 * Read athlete state through the enforced cache-first order.
 *
 * This function is the ONLY way backend callers should read
 * athlete state. It guarantees the read order is respected
 * and returns full provenance of which layers were used.
 */
function readAthleteState(request, store, liveReader) {
    return __awaiter(this, void 0, void 0, function* () {
        var _a, _b, _c;
        const { athleteId, requiredFields = [], userRequestedRealtime = false } = request;
        const date = (_a = request.date) !== null && _a !== void 0 ? _a : todayDate();
        const layers = [];
        let stillMissing = [...requiredFields];
        function markResolved(fields) {
            stillMissing = stillMissing.filter((f) => !fields.includes(f));
        }
        // ── Step 1: Daily artifact ──────────────────────────────────
        const dailyArtifact = yield store.getLatestDailyRefresh(athleteId);
        const dailyUsable = dailyArtifact != null && dailyArtifact.sourceDate === date;
        layers.push({
            layer: 'daily_artifact',
            reason: dailyUsable
                ? 'Fresh daily artifact for target date'
                : dailyArtifact
                    ? `Daily artifact exists but for ${dailyArtifact.sourceDate}, not ${date}`
                    : 'No daily artifact',
            hit: dailyUsable,
        });
        if (dailyUsable) {
            // The daily artifact's coverage tells us what's present
            const artifactFields = dailyArtifact.facts
                .filter((f) => f.status !== 'missing')
                .map((f) => f.metric);
            markResolved(artifactFields);
        }
        // ── Step 2: Weekly artifact ─────────────────────────────────
        const weeklyArtifact = yield store.getLatestWeeklySynthesis(athleteId);
        const weeklyUsable = weeklyArtifact != null;
        layers.push({
            layer: 'weekly_artifact',
            reason: weeklyUsable
                ? `Weekly artifact for ${weeklyArtifact.weekStart}–${weeklyArtifact.weekEnd}`
                : 'No weekly artifact',
            hit: weeklyUsable,
        });
        // ── Step 3: Stable memory ───────────────────────────────────
        const stableMemory = yield store.getStableMemory(athleteId);
        layers.push({
            layer: 'stable_memory',
            reason: stableMemory ? `Updated ${stableMemory.updatedAt}` : 'No stable memory',
            hit: stableMemory != null,
        });
        // ── Step 4: Normalized (only if artifact insufficient) ──────
        let normalizedDay = null;
        if (stillMissing.length > 0 || !dailyUsable) {
            normalizedDay = yield store.getNormalizedDay(athleteId, date);
            const normHit = normalizedDay != null;
            layers.push({
                layer: 'normalized',
                reason: normHit
                    ? `Normalized record for ${date}`
                    : `No normalized record for ${date}`,
                hit: normHit,
            });
            if (normHit) {
                markResolved(normalizedDay.presentFields);
            }
        }
        // ── Step 5: Raw (only if normalized insufficient) ───────────
        if (stillMissing.length > 0) {
            const rawDay = yield store.getRawDay(athleteId, date);
            layers.push({
                layer: 'raw',
                reason: rawDay
                    ? `Raw record for ${date}`
                    : `No raw record for ${date}`,
                hit: rawDay != null,
            });
            // Raw doesn't directly resolve required fields (it's not
            // normalized), but its existence informs freshness decisions.
        }
        // ── Step 6: Live WHOOP (only if freshness policy allows) ────
        let liveWhoopRead = false;
        let freshnessDecision = null;
        if (stillMissing.length > 0 || !dailyUsable || userRequestedRealtime) {
            const sourceHealth = yield store.getSourceHealth(athleteId, 'whoop');
            freshnessDecision = (0, should_read_live_whoop_1.shouldReadLiveWhoop)({
                latestArtifactFreshUntil: (_b = dailyArtifact === null || dailyArtifact === void 0 ? void 0 : dailyArtifact.freshUntil) !== null && _b !== void 0 ? _b : null,
                sourceHealth,
                userRequestedRealtime,
                requiredFields,
                cachedPresentFields: (_c = normalizedDay === null || normalizedDay === void 0 ? void 0 : normalizedDay.presentFields) !== null && _c !== void 0 ? _c : [],
            });
            if (freshnessDecision.liveReadAllowed && liveReader) {
                const liveResult = yield liveReader.fetchAndNormalize(athleteId, date);
                liveWhoopRead = true;
                layers.push({
                    layer: 'live_whoop',
                    reason: `Live read: ${freshnessDecision.reason}`,
                    hit: liveResult != null,
                });
                if (liveResult) {
                    normalizedDay = liveResult;
                    markResolved(liveResult.presentFields);
                }
            }
            else {
                layers.push({
                    layer: 'live_whoop',
                    reason: freshnessDecision.liveReadAllowed
                        ? 'Live read allowed but no reader provided'
                        : `Denied: ${freshnessDecision.reason}`,
                    hit: false,
                });
            }
        }
        // ── Resolve confidence ──────────────────────────────────────
        let confidence = 'low';
        if (dailyUsable && dailyArtifact.confidence === 'high') {
            confidence = 'high';
        }
        else if (dailyUsable) {
            confidence = dailyArtifact.confidence;
        }
        else if (normalizedDay && normalizedDay.completeness === 'complete') {
            confidence = 'medium';
        }
        return {
            athleteId,
            date,
            dailyArtifact: dailyUsable ? dailyArtifact : null,
            weeklyArtifact,
            stableMemory,
            normalizedDay,
            layersConsulted: layers,
            liveWhoopRead,
            freshnessDecision,
            confidence,
            stillMissing,
        };
    });
}
