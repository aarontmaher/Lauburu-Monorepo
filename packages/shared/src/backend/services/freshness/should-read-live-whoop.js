"use strict";
/**
 * Freshness decision policy — determines whether a live WHOOP
 * read is allowed for a given request.
 *
 * This is the single enforcement point. The API orchestration
 * layer must call this before any live WHOOP access. The chat/
 * runtime layer must NEVER bypass this to hit WHOOP directly.
 *
 * Live WHOOP is allowed ONLY when one of four conditions is met:
 *   1. The latest daily artifact has expired (freshUntil < now)
 *   2. Cached normalized data is missing a field the caller needs
 *   3. Source health indicates failed or incomplete ingest
 *   4. The user explicitly requested real-time data
 *
 * All other reads come from cached artifacts.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.shouldReadLiveWhoop = shouldReadLiveWhoop;
/**
 * Evaluate whether a live WHOOP read is allowed.
 * Pure function — no network calls, no side effects.
 */
function shouldReadLiveWhoop(input, nowIso) {
    var _a;
    const now = nowIso !== null && nowIso !== void 0 ? nowIso : new Date().toISOString();
    // Condition 4: user explicitly requested real-time data
    if (input.userRequestedRealtime) {
        return {
            liveReadAllowed: true,
            reason: 'User explicitly requested real-time WHOOP data.',
            trigger: 'user_requested',
        };
    }
    // Condition 1: latest artifact has expired
    if (input.latestArtifactFreshUntil != null && now > input.latestArtifactFreshUntil) {
        return {
            liveReadAllowed: true,
            reason: `Daily artifact expired at ${input.latestArtifactFreshUntil}.`,
            trigger: 'artifact_expired',
        };
    }
    // Condition 2: cached data is missing a required field
    if (input.requiredFields.length > 0) {
        const missing = input.requiredFields.filter((f) => !input.cachedPresentFields.includes(f));
        if (missing.length > 0) {
            return {
                liveReadAllowed: true,
                reason: `Cached data missing required fields: ${missing.join(', ')}.`,
                trigger: 'missing_required_field',
            };
        }
    }
    // Condition 3: source health indicates failure or incomplete ingest
    if (input.sourceHealth) {
        const sh = input.sourceHealth;
        if (sh.upstreamStatus === 'down' || sh.upstreamStatus === 'degraded') {
            return {
                liveReadAllowed: true,
                reason: `Source health is ${sh.upstreamStatus}: ${(_a = sh.degradedReason) !== null && _a !== void 0 ? _a : 'unknown reason'}.`,
                trigger: 'source_unhealthy',
            };
        }
        if (sh.freshnessStatus === 'expired' || sh.freshnessStatus === 'missing') {
            return {
                liveReadAllowed: true,
                reason: `Source freshness is ${sh.freshnessStatus}.`,
                trigger: 'source_unhealthy',
            };
        }
    }
    // No condition met — deny live read
    return {
        liveReadAllowed: false,
        reason: 'Cached artifacts are fresh and complete. Live WHOOP read not needed.',
        trigger: 'denied',
    };
}
