import type { KnowledgeDocument } from '../types';

export const appFirstPrioritiesDoc: KnowledgeDocument = {
  id: 'kb-app-first-priorities',
  version: 1,
  canonicalSlug: 'app-first-priorities',
  title: 'App-first priorities for shared AI and knowledge work',
  documentType: 'guidance',
  category: 'internal_product_decisions',
  subcategories: ['mobile_priority', 'shared_foundation'],
  summary:
    'The current product priority is to make the mobile app useful first while building shared contracts that a later backend retrieval/orchestration layer can consume without rework.',
  detailedBody:
    'Current repo direction prioritizes mobile-visible product work, but shared modules should carry the durable schema and retrieval contracts that future backend services will reuse. The safe interpretation is: build honest shared foundations now, keep backend-future claims explicit, and do not force the mobile app to invent fake server truth just to look complete.',
  keyPoints: [
    'mobile product surfaces are the first consumer of shared knowledge contracts',
    'shared modules should define durable types and deterministic retrieval helpers',
    'backend-future capability must stay clearly labeled as pending or intended',
  ],
  sourceOrigin: 'product_direction',
  sourceAuthority: 'product_intended',
  confidence: 'high',
  confidenceNotes:
    'Aligned with current repo direction and the existing app-first feature work.',
  evidenceBucket: 'internal_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'intended_direction',
  implementationStatus: 'shared_contract_only',
  applicableSurfaces: ['home', 'reference', 'settings', 'shared_backend', 'all'],
  relatedFeatures: ['knowledge_base', 'evidence_aware_ai'],
  relatedEntities: ['packages/shared', 'apps/mobile'],
  retrievalTags: ['app-first', 'shared-foundation', 'mobile-priority'],
  openQuestions: [
    'which backend execution surface will consume the shared knowledge contracts first',
  ],
  doNotOverclaim: [
    'do not describe shared knowledge types as if they already imply live backend retrieval',
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
