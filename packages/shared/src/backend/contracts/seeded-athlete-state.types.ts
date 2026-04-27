import type {
  AthleteBaselineThresholds,
  AthleteObservedPattern,
  AthletePhysiologyBaseline,
} from '../../athlete-memory/types';
import type { ArtifactConfidence } from './refresh-artifacts.types';

export interface SeededBaselineProfile {
  athleteId: string;
  generatedAt: string;
  source: 'stable_memory_seed';
  baselineProfile: AthletePhysiologyBaseline;
  missingSourceCaveats: string[];
}

export interface SeededBaselineThresholds {
  athleteId: string;
  generatedAt: string;
  source: 'stable_memory_seed';
  thresholds: AthleteBaselineThresholds;
  basedOnComputedAt: string | null;
  missingSourceCaveats: string[];
}

export interface SeededRecurringPatternCandidate {
  key: string;
  label: string;
  observationCount: number;
  confidence: ArtifactConfidence;
  evidenceWindow: {
    start: string;
    end: string;
  };
  eligibleForPromotion: boolean;
  caveats: string[];
}

export interface SeededRecurringPatternsCandidates {
  athleteId: string;
  generatedAt: string;
  source: 'weekly_synthesis_seed';
  candidates: SeededRecurringPatternCandidate[];
  observedPatternsSnapshot: AthleteObservedPattern[];
  missingSourceCaveats: string[];
}

export interface SeededCurrentBlockSummary {
  athleteId: string;
  generatedAt: string;
  summary: string;
  confidence: ArtifactConfidence;
  sourceDate: string | null;
  weekKey: string | null;
  caveats: string[];
}
