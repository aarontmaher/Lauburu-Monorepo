import type { KnowledgeDocument } from '../types';

export const evidenceAwareAiMeaningDoc: KnowledgeDocument = {
  id: 'kb-what-evidence-aware-ai-should-mean-in-this-app',
  version: 1,
  canonicalSlug: 'what-evidence-aware-ai-should-mean-in-this-app',
  title: 'What evidence-aware AI should mean in this app',
  documentType: 'concept',
  category: 'non_technique_product_reasoning',
  subcategories: ['ai_modes', 'non_technique_coaching'],
  summary:
    'Evidence-aware AI should mean broader non-technique coaching that can be grounded in science, pooled user-pattern summaries, internal coaching context, and app context, while staying explicit about what is not live yet.',
  detailedBody:
    'Current mobile code already models three AI modes and evidence-aware request scaffolding in `apps/mobile/src/services/evidence-aware-ai.ts`. The intended product meaning is broader coaching reasoning, not technique lookup. The future backend should use this meaning to route requests across evidence buckets, but the current app only previews policy and builds a structured request packet.',
  keyPoints: [
    'evidence-aware AI is for non-technique coaching questions',
    'it should combine multiple grounding buckets when they are actually available',
    'the current app slice is request scaffolding, not a live answer engine',
  ],
  sourceOrigin: 'product_direction',
  sourceAuthority: 'product_intended',
  confidence: 'high',
  confidenceNotes:
    'Aligned with current mobile service contracts and product direction, but backend retrieval is not implemented yet.',
  evidenceBucket: 'internal_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'intended_direction',
  implementationStatus: 'app_scaffold_only',
  applicableSurfaces: ['home', 'evidence_aware_ai'],
  relatedFeatures: ['evidence_aware_ai', 'non_technique_coaching'],
  relatedEntities: ['AiMode', 'EvidenceAwareTopic', 'AiRequestPolicy'],
  retrievalTags: ['ai', 'evidence-aware', 'non-technique', 'grounding'],
  openQuestions: [
    'what backend answer contract should be returned to the app',
    'how science and pooled-user corpora should be ranked against app context',
  ],
  doNotOverclaim: [
    'do not describe the current app as if it already returns in-app AI answers',
    'do not describe science or pooled-user grounding as live retrieval unless the backend actually used those sources',
  ],
  reviewOwner: 'product-engineering',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 14,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
