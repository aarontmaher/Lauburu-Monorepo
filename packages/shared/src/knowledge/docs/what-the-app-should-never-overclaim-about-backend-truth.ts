import type { KnowledgeDocument } from '../types';

export const backendTruthDoc: KnowledgeDocument = {
  id: 'kb-what-the-app-should-never-overclaim-about-backend-truth',
  version: 1,
  canonicalSlug: 'what-the-app-should-never-overclaim-about-backend-truth',
  title: 'What the app should never overclaim about backend truth',
  documentType: 'boundary',
  category: 'backend_truth_and_data_surfaces',
  subcategories: ['truth_boundary', 'safe_claims'],
  summary:
    'The app should not claim live backend retrieval, authoritative cap enforcement, completed checkout, science ingestion, or pooled-user analysis unless those systems actually exist and were used.',
  detailedBody:
    'Current repo state verifies app-side policy scaffolding and request generation, but not backend retrieval or commerce settlement. This boundary should remain explicit in UI, prompts, and internal knowledge docs so provisional behavior is not misrepresented as live backend truth.',
  keyPoints: [
    'request scaffolding is not backend retrieval',
    'policy preview is not authoritative metering',
    'pay-per-use eligibility is not completed payment',
  ],
  sourceOrigin: 'repo_code',
  sourceAuthority: 'repo_verified',
  confidence: 'high',
  confidenceNotes:
    'Verified against current shared and mobile code: no backend retrieval module or commerce completion path exists yet.',
  evidenceBucket: 'app_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'implemented_truth',
  implementationStatus: 'live_verified',
  applicableSurfaces: ['home', 'evidence_aware_ai', 'shared_backend', 'all'],
  relatedFeatures: ['evidence_aware_ai', 'knowledge_base', 'monetization_policy'],
  relatedEntities: ['Share.share', 'evidence-aware-ai.ts', 'tier-store'],
  retrievalTags: ['backend-truth', 'overclaim', 'safety', 'authority'],
  openQuestions: [
    'what backend surface will become the first authoritative retrieval endpoint',
  ],
  doNotOverclaim: [
    'do not claim vector search is live',
    'do not claim pooled-user summaries are live',
    'do not claim daily usage counts are authoritative',
    'do not claim checkout or purchase completion is wired',
  ],
  reviewOwner: 'platform-engineering',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 14,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
