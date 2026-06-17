import type { KnowledgeDocument } from '../types';

export const coachingPhilosophyDoc: KnowledgeDocument = {
  id: 'kb-coaching-philosophy-performance-adherence-and-uncertainty',
  version: 1,
  canonicalSlug: 'coaching-philosophy-performance-adherence-and-uncertainty',
  title: 'Coaching philosophy: performance, adherence, and uncertainty',
  documentType: 'concept',
  category: 'coaching_philosophy',
  subcategories: ['performance', 'adherence', 'uncertainty'],
  summary:
    'The intended coaching stance is pragmatic: balance performance, recovery, and adherence, and stay explicit when recommendations are uncertain or data quality is limited.',
  detailedBody:
    'Current shared coaching code already encodes readiness, load, sleep, and confidence concepts. Product direction also emphasizes uncertainty-aware coaching rather than overconfident prescriptions. This document captures that philosophy as retrieval context for future non-technique AI.',
  keyPoints: [
    'coaching should optimize for sustainable adherence, not just intensity',
    'uncertainty should be surfaced instead of hidden',
    'performance and recovery need to be balanced against available evidence and user context',
  ],
  sourceOrigin: 'product_direction',
  sourceAuthority: 'product_intended',
  confidence: 'medium',
  confidenceNotes:
    'Grounded in shared coaching concepts and product direction, but this is still a philosophy document rather than a fully encoded rule set.',
  evidenceBucket: 'internal_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'context_only',
  implementationStatus: 'partially_wired',
  applicableSurfaces: ['home', 'health', 'evidence_aware_ai', 'all'],
  relatedFeatures: ['daily_coaching', 'feedback_capture', 'evidence_aware_ai'],
  relatedEntities: ['confidence', 'readiness', 'adherence'],
  retrievalTags: ['coaching', 'adherence', 'uncertainty', 'performance'],
  openQuestions: [
    'how much of this philosophy should become explicit backend reasoning prompts versus hard rules',
  ],
  doNotOverclaim: [
    'do not describe this philosophy as a complete backend reasoning engine',
  ],
  reviewOwner: 'product-coaching',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 30,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
