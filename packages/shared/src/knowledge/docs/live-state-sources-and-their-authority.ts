import type { KnowledgeDocument } from '../types';

export const liveStateSourcesDoc: KnowledgeDocument = {
  id: 'kb-live-state-sources-and-their-authority',
  version: 1,
  canonicalSlug: 'live-state-sources-and-their-authority',
  title: 'Live state sources and their authority',
  documentType: 'authority_map',
  category: 'backend_truth_and_data_surfaces',
  subcategories: ['source_authority', 'state_ownership'],
  summary:
    'Different subsystems own different truths: shared code owns domain rules, mobile stores own local state and persistence, and backend truth for evidence retrieval and commerce is not yet implemented.',
  detailedBody:
    'Verified authority map: `packages/shared/src/health/*` owns reusable health/coaching transforms; mobile Zustand stores own persisted local state and hydration; `apps/mobile/src/services/evidence-aware-ai.ts` owns app-side AI policy scaffolding; no current repo module owns authoritative backend evidence retrieval, science ingestion, pooled-user summaries, or purchase settlement.',
  keyPoints: [
    'shared code owns domain transforms',
    'mobile stores own local persisted state',
    'backend evidence retrieval is currently unowned in live code',
  ],
  sourceOrigin: 'repo_code',
  sourceAuthority: 'repo_verified',
  confidence: 'high',
  confidenceNotes: 'Derived from current repo structure and inspected code paths.',
  evidenceBucket: 'app_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'implemented_truth',
  implementationStatus: 'live_verified',
  applicableSurfaces: ['shared_backend', 'all'],
  relatedFeatures: ['health_pipeline', 'knowledge_base', 'ai_policy'],
  relatedEntities: ['packages/shared', 'apps/mobile/src/store', 'apps/mobile/src/services'],
  retrievalTags: ['authority', 'ownership', 'state-sources', 'repo'],
  openQuestions: [
    'which backend module will become authoritative for retrieval and evidence assembly',
  ],
  doNotOverclaim: [
    'do not treat app-side policy code as backend usage truth',
  ],
  reviewOwner: 'platform-engineering',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 21,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
