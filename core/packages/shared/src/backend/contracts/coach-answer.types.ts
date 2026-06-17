/**
 * Coach answer contract — the canonical typed answer object
 * the backend returns for a single Coach question turn.
 *
 * Mobile renders this directly as an answer card.
 * The backend composes it from ai-context + domain routing.
 */

export type CoachDomain = 'hiit' | 'nutrition' | 'recovery' | 'training' | 'general';
export type CoachAnswerStatus = 'answered' | 'downgraded' | 'insufficient_data' | 'unsupported';
export type CoachConfidence = 'high' | 'medium' | 'low' | 'speculative';

export interface CoachAnswerBody {
  /** One-sentence direct answer. */
  short: string;
  /** Brief explanation of why. */
  why: string;
  /** Suggested next action. */
  nextStep: string;
  /** Note about what data was missing, if any. */
  missingnessNote: string | null;
}

export interface CoachAnswerResponse {
  ok: boolean;
  /** Which domain the question was routed to. */
  domain: CoachDomain;
  /** Seed/live mode at answer time. */
  mode: 'seed_partial' | 'live_partial' | 'live_ready' | 'uninitialized';
  /** How the question was classified. */
  questionClass: string;
  /** Answer status. */
  status: CoachAnswerStatus;
  /** The answer card content. */
  answer: CoachAnswerBody;
  /** Confidence in this answer. */
  confidence: CoachConfidence;
  /** What data sources contributed. */
  sourceDependencies: string[];
  /** Machine-readable missing or partial fields affecting the answer. */
  missingFields: string[];
  /** Safety/honesty flags the UI should display. */
  safetyFlags: string[];
  /** What would make this answer stronger (null when fully live). */
  upgradeHint: string | null;
}

export interface CoachQuestionRequest {
  athleteId: string;
  question: string;
  /** Optional topic hint from the UI. */
  topic?: string;
}
