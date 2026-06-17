import type { KnowledgeDocument } from '../types';

export const scienceVsAppContextDoc: KnowledgeDocument = {
  id: 'kb-what-should-be-science-backed-vs-app-context-backed',
  version: 1,
  canonicalSlug: 'what-should-be-science-backed-vs-app-context-backed',
  title: 'What should be science-backed versus app-context-backed',
  documentType: 'guidance',
  category: 'science_questions_to_support',
  subcategories: ['grounding_boundaries', 'evidence_selection'],
  summary:
    'Future evidence-aware AI should use science for claims about recovery, load, adherence, and intervention effects, while app-context knowledge should explain feature behavior, routing, implementation status, and product policy.',
  detailedBody:
    'This document is guidance for future retrieval. It does not claim that a science corpus is loaded today. Instead, it defines the retrieval boundary: use science-backed sources for physiological or behavioral claims, and app-context/internal-context docs for implementation, workflow, and monetization behavior.',
  keyPoints: [
    'science should support general coaching claims where evidence exists',
    'app context should support implementation and workflow truth',
    'internal context should support product philosophy and policy intent',
  ],
  sourceOrigin: 'internal_reasoning',
  sourceAuthority: 'manual_curated',
  confidence: 'medium',
  confidenceNotes:
    'This is a curated retrieval policy guide, not a claim that science ingestion is already live.',
  evidenceBucket: 'science',
  evidenceStrength: 'expert_consensus',
  truthStatus: 'context_only',
  implementationStatus: 'not_started',
  applicableSurfaces: ['evidence_aware_ai', 'shared_backend', 'all'],
  relatedFeatures: ['knowledge_base', 'evidence_aware_ai', 'retrieval_routing'],
  relatedEntities: ['science', 'app_context', 'internal_context', 'user_patterns'],
  retrievalTags: ['science', 'grounding', 'retrieval-policy'],
  openQuestions: [
    'how science summaries should be authored, reviewed, and versioned',
  ],
  doNotOverclaim: [
    'do not imply this repo already contains a live science-summary corpus',
  ],
  reviewOwner: 'platform-engineering',
  lastReviewed: '2026-04-12',
  reviewCadenceDays: 30,
  status: 'active',
  createdAt: '2026-04-12',
  updatedAt: '2026-04-12',
  supersedes: [],
  vectorId: null,
};
