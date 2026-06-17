import type { KnowledgeDocument } from '../types';

export const homeCoachingDoc: KnowledgeDocument = {
  id: 'kb-how-home-coaching-currently-works',
  version: 1,
  canonicalSlug: 'how-home-coaching-currently-works',
  title: 'How Home coaching currently works',
  documentType: 'workflow',
  category: 'app_feature_behavior',
  subcategories: ['home', 'coaching_workflow'],
  summary:
    'Home assembles a daily coaching brief from local health, training, schedule, and nutrition inputs, then layers optional external AI prompt generation and follow-up capture on top.',
  detailedBody:
    'Verified flow: Home builds `briefInputs`, calls `buildDailyCoachingBrief()` from shared code, renders the resulting coaching card, and optionally generates external share-sheet prompt packets. The second-opinion flow stores pending/completed cases in `coaching-cases-store.ts`.',
  keyPoints: [
    'the shared health/coaching pipeline powers the daily brief',
    'Home is currently a composition layer plus some screen-local orchestration',
    'external AI handoff is optional and not the same as in-app answer generation',
  ],
  sourceOrigin: 'repo_code',
  sourceAuthority: 'repo_verified',
  confidence: 'high',
  confidenceNotes: 'Verified against current Home screen and coaching-case store.',
  evidenceBucket: 'app_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'implemented_truth',
  implementationStatus: 'live_verified',
  applicableSurfaces: ['home', 'coaching_history'],
  relatedFeatures: ['daily_coaching', 'coaching_cases', 'evidence_aware_ai'],
  relatedEntities: ['TodayCoachCard', 'buildDailyCoachingBrief', 'coaching-cases-store'],
  retrievalTags: ['home', 'workflow', 'coaching'],
  openQuestions: [
    'how much Home scoring/orchestration should move into services to reduce file risk',
  ],
  doNotOverclaim: [
    'do not imply that Home already runs backend evidence retrieval for its coaching card',
  ],
  reviewOwner: 'mobile-engineering',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 21,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
