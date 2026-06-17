/**
 * Canonical knowledge-base schema for Lauburu's future evidence-aware AI.
 *
 * This module is shared-first on purpose:
 * - mobile code can use it to assemble safe request context
 * - backend retrieval code can use it to load/query the same corpus
 * - future vector indexing can attach to the same document model
 *
 * Non-goals for this slice:
 * - no fake vector search
 * - no fake science corpus
 * - no fake pooled-user-data summaries
 * - no overclaiming backend capabilities that do not exist yet
 */

// ---------------------------------------------------------------------------
// Evidence buckets
// ---------------------------------------------------------------------------

export type EvidenceBucket =
  | 'science'
  | 'user_patterns'
  | 'internal_context'
  | 'app_context';

// ---------------------------------------------------------------------------
// Document architecture
// ---------------------------------------------------------------------------

export type KnowledgeDocumentType =
  | 'concept'
  | 'policy'
  | 'workflow'
  | 'implementation_note'
  | 'authority_map'
  | 'boundary'
  | 'guidance'
  | 'open_question';

export type KnowledgeCategory =
  | 'coaching_philosophy'
  | 'non_technique_product_reasoning'
  | 'ai_policy_and_access_rules'
  | 'monetization_rules'
  | 'user_behavior_and_feedback_themes'
  | 'internal_product_decisions'
  | 'app_feature_behavior'
  | 'repo_and_implementation_guidance'
  | 'science_questions_to_support'
  | 'backend_truth_and_data_surfaces'
  | 'open_questions_and_unknowns';

export type KnowledgeTruthStatus =
  | 'implemented_truth'
  | 'intended_direction'
  | 'pending_backend'
  | 'open_question'
  | 'context_only'
  | 'deprecated';

export type KnowledgeImplementationStatus =
  | 'live_verified'
  | 'shared_contract_only'
  | 'app_scaffold_only'
  | 'partially_wired'
  | 'not_started'
  | 'deprecated';

export type KnowledgeSourceOrigin =
  | 'repo_code'
  | 'repo_docs'
  | 'product_direction'
  | 'internal_reasoning'
  | 'manual_summary';

export type KnowledgeSourceAuthority =
  | 'repo_verified'
  | 'product_intended'
  | 'internal_reasoning_only'
  | 'manual_curated'
  | 'unknown';

export type KnowledgeConfidence = 'high' | 'medium' | 'low';

export type EvidenceStrength =
  | 'not_applicable'
  | 'anecdotal'
  | 'weak'
  | 'moderate'
  | 'strong'
  | 'expert_consensus';

export type AppSurface =
  | 'home'
  | 'reference'
  | 'train'
  | 'health'
  | 'feedback'
  | 'settings'
  | 'map_3d'
  | 'coaching_history'
  | 'evidence_aware_ai'
  | 'shared_backend'
  | 'all';

export type AiModeCompat = 'standard' | 'evidence_aware' | 'premium_research';

export type KnowledgeDocumentStatus = 'active' | 'draft' | 'archived';

// ---------------------------------------------------------------------------
// Core document schema
// ---------------------------------------------------------------------------

export interface KnowledgeDocument {
  id: string;
  version: number;
  canonicalSlug: string;
  title: string;
  documentType: KnowledgeDocumentType;
  category: KnowledgeCategory;
  subcategories: string[];
  summary: string;
  detailedBody: string;
  keyPoints: string[];
  sourceOrigin: KnowledgeSourceOrigin;
  sourceAuthority: KnowledgeSourceAuthority;
  confidence: KnowledgeConfidence;
  confidenceNotes: string;
  evidenceBucket: EvidenceBucket;
  evidenceStrength: EvidenceStrength;
  truthStatus: KnowledgeTruthStatus;
  implementationStatus: KnowledgeImplementationStatus;
  applicableSurfaces: AppSurface[];
  relatedFeatures: string[];
  relatedEntities: string[];
  retrievalTags: string[];
  openQuestions: string[];
  doNotOverclaim: string[];
  reviewOwner: string;
  lastReviewed: string;
  reviewCadenceDays: number | null;
  status: KnowledgeDocumentStatus;
  createdAt: string;
  updatedAt: string;
  supersedes: string[];
  vectorId: string | null;
}

// ---------------------------------------------------------------------------
// Retrieval
// ---------------------------------------------------------------------------

export interface KnowledgeQuery {
  category?: KnowledgeCategory;
  documentType?: KnowledgeDocumentType;
  truthStatus?: KnowledgeTruthStatus[];
  evidenceBucket?: EvidenceBucket;
  applicableSurface?: AppSurface;
  retrievalTags?: string[];
  relatedFeatures?: string[];
  sourceAuthority?: KnowledgeSourceAuthority[];
  implementationStatus?: KnowledgeImplementationStatus[];
  limit?: number;
}

export interface KnowledgeResult {
  document: KnowledgeDocument;
  score: number;
  matchedFilters: string[];
}

export interface KnowledgeRetrievalResponse {
  ok: boolean;
  results: KnowledgeResult[];
  totalMatched: number;
  method: 'deterministic' | 'vector' | 'hybrid';
  retrievedAt: string;
}

export interface KnowledgeContextPacket {
  query: KnowledgeQuery;
  retrieval: KnowledgeRetrievalResponse;
  documents: Array<{
    id: string;
    title: string;
    category: KnowledgeCategory;
    documentType: KnowledgeDocumentType;
    truthStatus: KnowledgeTruthStatus;
    implementationStatus: KnowledgeImplementationStatus;
    evidenceBucket: EvidenceBucket;
    sourceAuthority: KnowledgeSourceAuthority;
    summary: string;
    keyPoints: string[];
    doNotOverclaim: string[];
    openQuestions: string[];
  }>;
}
