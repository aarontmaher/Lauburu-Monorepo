import type { KnowledgeDocument } from '../types';
import { appFirstPrioritiesDoc } from './app-first-priorities';
import { evidenceAwareAiMeaningDoc } from './what-evidence-aware-ai-should-mean-in-this-app';
import { backendTruthDoc } from './what-the-app-should-never-overclaim-about-backend-truth';
import { liveStateSourcesDoc } from './live-state-sources-and-their-authority';
import { nonTechniqueVsReferenceDoc } from './how-non-technique-ai-differs-from-technique-reference-flows';
import { homeCoachingDoc } from './how-home-coaching-currently-works';
import { referenceCoachedLandingDoc } from './reference-coached-landing-workflow';
import { monetizationModelDoc } from './ai-monetization-model-included-daily-use-feature-protection-upgrade-pay-per-use';
import { scienceVsAppContextDoc } from './what-should-be-science-backed-vs-app-context-backed';
import { coachingPhilosophyDoc } from './coaching-philosophy-performance-adherence-and-uncertainty';

export const seedKnowledgeDocuments: KnowledgeDocument[] = [
  appFirstPrioritiesDoc,
  evidenceAwareAiMeaningDoc,
  backendTruthDoc,
  liveStateSourcesDoc,
  nonTechniqueVsReferenceDoc,
  homeCoachingDoc,
  referenceCoachedLandingDoc,
  monetizationModelDoc,
  scienceVsAppContextDoc,
  coachingPhilosophyDoc,
];
