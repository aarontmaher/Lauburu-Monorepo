import type { KnowledgeDocument } from '../types';

export const nonTechniqueVsReferenceDoc: KnowledgeDocument = {
  id: 'kb-how-non-technique-ai-differs-from-technique-reference-flows',
  version: 1,
  canonicalSlug: 'how-non-technique-ai-differs-from-technique-reference-flows',
  title: 'How non-technique AI differs from technique Reference flows',
  documentType: 'guidance',
  category: 'app_feature_behavior',
  subcategories: ['reference', 'ai_boundary'],
  summary:
    'Non-technique AI is for broader reasoning about recovery, load, adherence, scheduling, and coaching context; Reference remains the technique/navigation system for positions, headings, and transitions.',
  detailedBody:
    'Current mobile product already separates these surfaces: `reference.tsx` owns technique content and graph navigation, while the Home evidence-aware AI block explicitly labels itself as non-technique discussion mode. Future backend AI should keep that boundary rather than answering technique lookup with the non-technique corpus.',
  keyPoints: [
    'Reference is the technique authority surface',
    'evidence-aware AI should not replace Reference',
    'non-technique AI should route to broader coaching reasoning',
  ],
  sourceOrigin: 'repo_code',
  sourceAuthority: 'repo_verified',
  confidence: 'high',
  confidenceNotes: 'Verified from current Home and Reference screen behavior.',
  evidenceBucket: 'app_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'implemented_truth',
  implementationStatus: 'live_verified',
  applicableSurfaces: ['home', 'reference', 'evidence_aware_ai'],
  relatedFeatures: ['reference', 'evidence_aware_ai', 'coaching_recommendation'],
  relatedEntities: ['reference.tsx', 'index.tsx', 'map-3d.tsx'],
  retrievalTags: ['reference', 'non-technique', 'boundary', 'routing'],
  openQuestions: [
    'whether some future backend orchestration should hand technique questions back to Reference or a technique-specific retrieval layer',
  ],
  doNotOverclaim: [
    'do not use the non-technique knowledge base as if it were a technique corpus',
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
