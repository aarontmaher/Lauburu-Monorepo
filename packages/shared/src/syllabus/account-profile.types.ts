/**
 * Athlete account profile — compact public shape for mobile.
 * Contains belt rank and syllabus relationship.
 * Separate from private athlete memory (baselines, artifacts, etc).
 */

import type { BeltLevel } from './types';

export interface AthleteAccountProfile {
  athleteId: string;
  /** Current belt rank. */
  beltRank: BeltLevel;
  /** When the belt was last assessed/updated. */
  beltUpdatedAt: string | null;
  /** Whether belt was self-reported or system-verified. */
  beltSource: 'self_reported' | 'coach_verified' | 'default';
  /** Compact syllabus relationship. */
  syllabus: {
    /** Which belt syllabus is being tracked. */
    trackingBelt: BeltLevel;
    /** Total requirements for that belt. */
    totalRequirements: number;
    /** How many have any progress. */
    startedCount: number;
    /** How many are demonstrated or verified. */
    demonstratedCount: number;
  } | null;
}
