"use strict";
/**
 * Derive syllabus progress from existing reference progress store data.
 *
 * This bridges the reference-progress-store (which tracks individual
 * technique drilling/learned/tracking status) with the syllabus system
 * (which tracks belt requirements).
 *
 * Pure function — no side effects, no storage reads.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.deriveSyllabusProgress = deriveSyllabusProgress;
/**
 * Derive syllabus progress for an athlete from their reference
 * progress map and the shared syllabus definition.
 *
 * @param athleteId - The athlete ID.
 * @param belt - The belt definition to track against.
 * @param progressMap - The athlete's reference progress (key → status).
 */
function deriveSyllabusProgress(athleteId, belt, progressMap) {
    const now = new Date().toISOString();
    const items = belt.requirements.map((req) => {
        const mapped = mapRequirementToProgress(req, progressMap);
        return {
            requirementId: req.id,
            status: mapped.status,
            updatedAt: now,
            notes: mapped.notes,
            derivedFromReferenceProgress: mapped.derived,
        };
    });
    const summary = {
        total: items.length,
        notStarted: items.filter((i) => i.status === 'not_started').length,
        inProgress: items.filter((i) => i.status === 'in_progress').length,
        demonstrated: items.filter((i) => i.status === 'demonstrated').length,
        verified: items.filter((i) => i.status === 'verified').length,
    };
    return {
        athleteId,
        currentBelt: belt.belt,
        updatedAt: now,
        items,
        summary,
    };
}
function mapRequirementToProgress(req, progressMap) {
    // If the requirement has a direct progressKey mapping
    if (req.progressKey) {
        const refStatus = progressMap[req.progressKey];
        if (refStatus) {
            return {
                status: refStatusToSyllabusStatus(refStatus),
                notes: `Derived from reference progress: ${refStatus}`,
                derived: true,
            };
        }
    }
    // For position-level requirements, check if any technique in that position is tracked
    if (req.type === 'position' && req.sectionId && req.positionName) {
        const prefix = `tech|${req.sectionId}|${req.positionName}|`;
        const matchingKeys = Object.keys(progressMap).filter((k) => k.startsWith(prefix));
        const statuses = matchingKeys.map((k) => progressMap[k]).filter(Boolean);
        if (statuses.some((s) => s === 'learned')) {
            return { status: 'demonstrated', notes: 'Has learned techniques in this position.', derived: true };
        }
        if (statuses.some((s) => s === 'drilling')) {
            return { status: 'in_progress', notes: 'Currently drilling techniques in this position.', derived: true };
        }
        if (statuses.some((s) => s === 'tracking')) {
            return { status: 'in_progress', notes: 'Tracking techniques in this position.', derived: true };
        }
    }
    // Concept and sparring requirements can't be derived from reference progress
    return { status: 'not_started', notes: null, derived: false };
}
function refStatusToSyllabusStatus(refStatus) {
    switch (refStatus) {
        case 'drilling': return 'in_progress';
        case 'learned': return 'demonstrated';
        case 'tracking': return 'in_progress';
        default: return 'not_started';
    }
}
