"use strict";
/**
 * Seed syllabus — starter white belt requirements mapped to
 * canonical reference positions and techniques.
 *
 * This is the SHARED curriculum definition. It is NOT athlete-specific.
 * All athletes see the same syllabus requirements. Progress is tracked
 * separately in AthleteSyllabusProgress.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.SEED_SYLLABUS = void 0;
function req(id, label, opts = {}) {
    return Object.assign({ id,
        label, type: 'technique', priority: 'core', description: null, sectionId: null, positionName: null, heading: null, techniqueName: null, role: null, progressKey: null }, opts);
}
function techReq(id, label, section, position, role, heading, technique, priority = 'core') {
    return req(id, label, {
        type: 'technique',
        priority,
        sectionId: section,
        positionName: position,
        heading,
        techniqueName: technique,
        role,
        progressKey: `tech|${section}|${position}|${role}|${heading}|${technique}`,
    });
}
function posReq(id, label, section, position, priority = 'core') {
    return req(id, label, {
        type: 'position',
        priority,
        sectionId: section,
        positionName: position,
    });
}
function conceptReq(id, label, description, priority = 'core') {
    return req(id, label, {
        type: 'concept',
        priority,
        description,
    });
}
exports.SEED_SYLLABUS = {
    schemaVersion: 1,
    updatedAt: '2026-04-13',
    belts: [
        {
            belt: 'white',
            title: 'White Belt Fundamentals',
            requirementCount: 0, // set below
            requirements: [
                // ── Positions to know ──────────────────────────────
                posReq('w-pos-mount', 'Mount awareness', 'dominant_positions', 'Mount'),
                posReq('w-pos-side-control', 'Side control awareness', 'dominant_positions', 'Side control'),
                posReq('w-pos-back', 'Back control awareness', 'dominant_positions', 'Back control'),
                posReq('w-pos-closed-guard', 'Closed guard awareness', 'guard', 'Closed guard'),
                posReq('w-pos-half-guard', 'Half guard awareness', 'guard', 'Half guard'),
                // ── Core techniques ────────────────────────────────
                // Mount escapes
                techReq('w-mount-upa', 'Upa escape from mount', 'dominant_positions', 'Mount', 'Defender', 'Defence/Escapes', 'Upa escape'),
                techReq('w-mount-elbow', 'Elbow-knee escape from mount', 'dominant_positions', 'Mount', 'Defender', 'Defence/Escapes', 'Elbow-knee escape'),
                // Side control escapes
                techReq('w-sc-frame', 'Framing from side control', 'dominant_positions', 'Side control', 'Defender', 'Defence/Escapes', 'Frame and reguard'),
                // Guard basics
                techReq('w-cg-armbar', 'Armbar from closed guard', 'guard', 'Closed guard', 'Attacker', 'Submissions', 'Armbar'),
                techReq('w-cg-triangle', 'Triangle from closed guard', 'guard', 'Closed guard', 'Attacker', 'Submissions', 'Triangle'),
                techReq('w-cg-scissor', 'Scissor sweep', 'guard', 'Closed guard', 'Attacker', 'Offence', 'Scissor sweep'),
                techReq('w-cg-hip-bump', 'Hip bump sweep', 'guard', 'Closed guard', 'Attacker', 'Offence', 'Hip bump sweep'),
                // Guard passing
                techReq('w-cg-pass', 'Standing guard break and pass', 'guard', 'Closed guard', 'Defender', 'Defence/Escapes', 'Standing break', 'recommended'),
                // Back escapes
                techReq('w-back-escape', 'Back escape fundamentals', 'dominant_positions', 'Back control', 'Defender', 'Defence/Escapes', 'Back escape'),
                // Takedowns
                techReq('w-td-double', 'Double leg takedown', 'wrestling', 'Double leg', 'Attacker', 'Offence', 'Double leg', 'recommended'),
                // ── Concepts ───────────────────────────────────────
                conceptReq('w-concept-posture', 'Posture management', 'Understanding when to maintain or break posture in each position.'),
                conceptReq('w-concept-base', 'Base and balance', 'Keeping a stable base to prevent sweeps and maintain position.'),
                conceptReq('w-concept-frames', 'Framing principles', 'Using frames to create space and prevent advancement.'),
                conceptReq('w-concept-guard-retention', 'Guard retention basics', 'Recovering guard when it is being passed.'),
                // ── Sparring ───────────────────────────────────────
                req('w-spar-positional', 'Positional sparring from mount', {
                    type: 'sparring',
                    priority: 'recommended',
                    description: 'Start from mount (top and bottom). Practice maintaining and escaping.',
                }),
            ],
        },
    ],
};
// Set requirementCount
for (const belt of exports.SEED_SYLLABUS.belts) {
    belt.requirementCount = belt.requirements.length;
}
