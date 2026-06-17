import type { KnowledgeDocument } from '../types';

export const monetizationModelDoc: KnowledgeDocument = {
  id: 'kb-ai-monetization-model-included-daily-use-feature-protection-upgrade-pay-per-use',
  version: 1,
  canonicalSlug:
    'ai-monetization-model-included-daily-use-feature-protection-upgrade-pay-per-use',
  title:
    'AI monetization model: included daily use, feature protection, upgrade, and pay-per-use',
  documentType: 'policy',
  category: 'monetization_rules',
  subcategories: ['included_access', 'pay_per_use', 'feature_protection'],
  summary:
    'The current intended AI monetization model combines included daily access, feature-protected usage, upgrade paths, and pay-per-use overflow, but only the app-side policy contract exists today.',
  detailedBody:
    'Current mobile policy models included access states, feature buckets, downgrade paths, upgrade recommendations, and pay-per-use eligibility. That is useful as a shared contract shape, but backend enforcement, counters, checkout, and settlement are not implemented yet.',
  keyPoints: [
    'the contract supports both upgrade and pay-per-use paths',
    'feature protection is meant to preserve essential coaching access',
    'backend enforcement and commerce completion are still pending',
  ],
  sourceOrigin: 'internal_reasoning',
  sourceAuthority: 'product_intended',
  confidence: 'high',
  confidenceNotes:
    'The direction is clear in mobile policy code and product requests, but backend enforcement does not exist yet.',
  evidenceBucket: 'internal_context',
  evidenceStrength: 'not_applicable',
  truthStatus: 'intended_direction',
  implementationStatus: 'app_scaffold_only',
  applicableSurfaces: ['home', 'settings', 'evidence_aware_ai', 'shared_backend'],
  relatedFeatures: ['evidence_aware_ai', 'membership_upgrade', 'pay_per_use_ai'],
  relatedEntities: ['AiAccessResolution', 'AiFeatureBucket', 'purchaseOfferType'],
  retrievalTags: ['monetization', 'daily-use', 'upgrade', 'pay-per-use'],
  openQuestions: [
    'how backend settlement should attach to access resolution states',
    'how plan gating and daily exhaustion should be represented distinctly in backend results',
  ],
  doNotOverclaim: [
    'do not present pay-per-use eligibility as a completed purchase',
    'do not present included exhaustion as backend-tracked unless server data exists',
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
