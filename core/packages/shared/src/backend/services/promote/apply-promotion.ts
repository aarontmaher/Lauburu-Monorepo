/**
 * Explicit promotion — applies a selected weekly promotion candidate
 * to stable athlete memory.
 *
 * This is the ONLY path that mutates stable memory.
 * Daily refresh and weekly synthesis NEVER call this.
 * Promotion requires explicit candidate selection and passes
 * through eligibility and approval checks.
 *
 * Internal-only: called by /v1/internal/athletes/:athleteId/promote
 */

import type { PromotionCandidate, ArtifactConfidence } from '../../contracts/refresh-artifacts.types';
import type { AthleteMemoryRecord, AthleteObservedPattern } from '../../../athlete-memory/types';

// ---------------------------------------------------------------------------
// Input / output
// ---------------------------------------------------------------------------

export interface PromotionRequest {
  athleteId: string;
  /** Index of the candidate in the weekly artifact's promotionCandidates array. */
  candidateIndex: number;
  /** The candidate being promoted (for verification). */
  candidate: PromotionCandidate;
  /** Who approved this promotion. */
  approvedBy: string;
}

export type PromotionOutcome = 'promoted' | 'rejected_not_eligible' | 'rejected_approval_required' | 'rejected_target_unknown';

export interface PromotionResult {
  outcome: PromotionOutcome;
  reason: string;
  targetDoc: string;
  candidateStatement: string;
  /** The updated memory record (only set if promoted). */
  updatedMemory: AthleteMemoryRecord | null;
}

// ---------------------------------------------------------------------------
// Promotion logic
// ---------------------------------------------------------------------------

/**
 * Apply a promotion candidate to stable memory.
 *
 * Pure function — takes current memory + candidate, returns new memory or rejection.
 * Does NOT write to storage. The caller persists the result.
 */
export function applyPromotion(
  request: PromotionRequest,
  currentMemory: AthleteMemoryRecord,
): PromotionResult {
  const { candidate, approvedBy } = request;

  // Guard: must be eligible
  if (!candidate.eligible) {
    return {
      outcome: 'rejected_not_eligible',
      reason: candidate.rejectionReason ?? 'Candidate is not eligible for promotion.',
      targetDoc: candidate.targetDoc,
      candidateStatement: candidate.candidateStatement,
      updatedMemory: null,
    };
  }

  // Guard: if approval required, must have approver
  if (candidate.approvalRequired && !approvedBy) {
    return {
      outcome: 'rejected_approval_required',
      reason: 'This candidate requires explicit approval. Provide approvedBy.',
      targetDoc: candidate.targetDoc,
      candidateStatement: candidate.candidateStatement,
      updatedMemory: null,
    };
  }

  // Apply based on target doc
  const now = new Date().toISOString();

  switch (candidate.targetDoc) {
    case 'recurring_patterns': {
      const newPattern: AthleteObservedPattern = {
        key: `promoted_${now.slice(0, 10)}_${currentMemory.observedPatterns.length}`,
        label: candidate.candidateStatement,
        observationCount: 1,
        active: true,
        evidence: [
          `Promoted from weekly synthesis (${candidate.evidenceWindow.start}–${candidate.evidenceWindow.end})`,
          `Evidence strength: ${candidate.evidenceStrength}`,
          `Approved by: ${approvedBy}`,
        ],
        confidence: candidate.evidenceStrength,
        ruleBasis: ['explicit_promotion_from_weekly_synthesis'],
      };

      const updatedMemory: AthleteMemoryRecord = {
        ...currentMemory,
        updatedAt: now,
        observedPatterns: [...currentMemory.observedPatterns, newPattern],
      };

      return {
        outcome: 'promoted',
        reason: `Pattern promoted to recurring_patterns. Approved by ${approvedBy}.`,
        targetDoc: candidate.targetDoc,
        candidateStatement: candidate.candidateStatement,
        updatedMemory,
      };
    }

    case 'baseline_profile': {
      // Baseline recomputation is flagged but the actual recompute
      // happens via the existing baseline builder — promotion here
      // marks the memory as needing recomputation.
      const updatedMemory: AthleteMemoryRecord = {
        ...currentMemory,
        updatedAt: now,
        currentBlockSummary: `${currentMemory.currentBlockSummary} [Baseline recomputation approved ${now.slice(0, 10)} by ${approvedBy}]`,
      };

      return {
        outcome: 'promoted',
        reason: `Baseline recomputation flagged. Approved by ${approvedBy}.`,
        targetDoc: candidate.targetDoc,
        candidateStatement: candidate.candidateStatement,
        updatedMemory,
      };
    }

    default:
      return {
        outcome: 'rejected_target_unknown',
        reason: `Unknown target doc: ${candidate.targetDoc}`,
        targetDoc: candidate.targetDoc,
        candidateStatement: candidate.candidateStatement,
        updatedMemory: null,
      };
  }
}
