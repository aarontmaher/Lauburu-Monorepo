/**
 * Daily and weekly refresh artifact types — Layer 3 (interpreted).
 *
 * This is the default AI read path. These artifacts contain
 * athlete-relative interpretation: baseline comparisons,
 * readiness classification, risk scoring, session gating,
 * pattern detection, and coaching guidance.
 *
 * Every artifact carries confidence, coverage, freshness,
 * and evidence basis so the AI can reason safely under
 * incomplete data.
 */

import type { SourceRef } from './whoop-raw.types';

// ── Confidence & coverage ─────────────────────────────────────

export type ArtifactConfidence = 'high' | 'medium' | 'low';

export interface ArtifactCoverage {
  /** How many of the expected input fields were present. */
  presentCount: number;
  totalExpected: number;
  /** Which fields were missing. */
  missingFields: string[];
  /** Status label. */
  status: 'complete' | 'partial' | 'minimal';
}

export interface ArtifactProvenance {
  /** Structured source references. */
  sourceRefs: SourceRef[];
  /** Which normalized record IDs fed this artifact. */
  normalizedRecordIds: string[];
  /** Which raw record IDs (transitive). */
  rawRecordIds: string[];
}

// ── Daily refresh artifact ────────────────────────────────────

export type DayState = 'green' | 'yellow' | 'red' | 'blocked';
export type RiskLevel = 'low' | 'moderate' | 'elevated' | 'high';

export interface DailyRefreshFact {
  metric: string;
  value: number | null;
  unit: string;
  baselineValue: number | null;
  deltaPct: number | null;
  status: 'normal' | 'elevated' | 'suppressed' | 'missing';
}

export interface DailyRefreshRecommendation {
  guidance: string;
  reasons: string[];
  /** What evidence supports this recommendation. */
  evidenceBasis: string[];
  confidence: ArtifactConfidence;
}

export interface DailyRefreshArtifact {
  /** Unique immutable ID. */
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;
  /** Which version of the refresh pipeline produced this. */
  derivationVersion: string;

  athleteId: string;
  /** The date this artifact describes. */
  sourceDate: string;
  /** When this artifact was generated. */
  generatedAt: string;
  /** After this timestamp, consider the artifact expired. */
  freshUntil: string;

  // ── Classification (athlete-relative) ───────────────────────
  dayState: DayState;
  dayScore: number;
  rollingRiskLevel: RiskLevel;
  rollingRiskScore: number;
  rollingRiskDrivers: string[];

  // ── Facts (baseline-compared) ───────────────────────────────
  facts: DailyRefreshFact[];

  // ── Recommendations ─────────────────────────────────────────
  primaryRecommendation: DailyRefreshRecommendation;
  sessionGate: {
    gate: DayState;
    allowedTypes: string[];
    maxIntensity: 'hard' | 'moderate' | 'light' | 'rest_only';
    cautions: string[];
  };

  // ── Patterns & warnings ─────────────────────────────────────
  activePatterns: Array<{
    key: string;
    label: string;
    observationCount: number;
    confidence: ArtifactConfidence;
  }>;
  warningFlags: Array<{
    level: 'warning' | 'watch' | 'info';
    label: string;
  }>;
  keyDrivers: string[];

  // ── Confidence & coverage ───────────────────────────────────
  confidence: ArtifactConfidence;
  coverage: ArtifactCoverage;
  provenance: ArtifactProvenance;

  /** Human-readable evidence basis for the overall artifact. */
  evidenceBasis: string[];
}

// ── Weekly synthesis artifact ─────────────────────────────────

export interface WeeklyTrend {
  metric: string;
  weekMean: number | null;
  baselineValue: number | null;
  deltaPct: number | null;
  trend: 'improving' | 'declining' | 'stable' | 'insufficient_data';
}

export interface PromotionCandidate {
  /** Which stable memory doc this would update. */
  targetDoc: string;
  /** What the promotion would state. */
  candidateStatement: string;
  /** Date window the evidence comes from. */
  evidenceWindow: { start: string; end: string };
  /** Strength of the evidence. */
  evidenceStrength: ArtifactConfidence;
  /** Whether the candidate meets promotion criteria. */
  eligible: boolean;
  /** Whether human approval is required. */
  approvalRequired: boolean;
  /** Why this was rejected, if applicable. */
  rejectionReason: string | null;
}

export interface WeeklySynthesisArtifact {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;
  derivationVersion: string;

  athleteId: string;
  weekStart: string;
  weekEnd: string;
  generatedAt: string;
  freshUntil: string;

  /** How many daily artifacts contributed. */
  dailyArtifactCount: number;
  dailyArtifactIds: string[];
  missingDays: string[];

  // ── Trends ──────────────────────────────────────────────────
  trends: WeeklyTrend[];
  dominantDriver: string | null;

  // ── Session summary ─────────────────────────────────────────
  sessions: {
    totalCount: number;
    grapplingCount: number;
    restDays: number;
  };

  // ── Interpretations ─────────────────────────────────────────
  improved: string[];
  worsened: string[];
  unusual: string[];
  likelyDrivers: string[];

  // ── Guidance ────────────────────────────────────────────────
  nextWeekGuidance: DailyRefreshRecommendation[];

  // ── Promotion candidates ────────────────────────────────────
  promotionCandidates: PromotionCandidate[];

  // ── Confidence & coverage ───────────────────────────────────
  confidence: ArtifactConfidence;
  coverage: ArtifactCoverage;
  provenance: ArtifactProvenance;
  evidenceBasis: string[];
}
