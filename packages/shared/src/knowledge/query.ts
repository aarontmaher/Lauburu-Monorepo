import type {
  KnowledgeConfidence,
  KnowledgeContextPacket,
  KnowledgeDocument,
  KnowledgeQuery,
  KnowledgeResult,
  KnowledgeRetrievalResponse,
} from './types';
import { loadKnowledgeDocuments } from './load';

const CONFIDENCE_RANK: Record<KnowledgeConfidence, number> = {
  low: 0,
  medium: 1,
  high: 2,
};

function includesAll(docValues: string[], required: string[]): boolean {
  return required.every((value) => docValues.includes(value));
}

function matchesQuery(doc: KnowledgeDocument, query: KnowledgeQuery): boolean {
  if (query.category && doc.category !== query.category) return false;
  if (query.documentType && doc.documentType !== query.documentType) return false;
  if (
    query.truthStatus &&
    query.truthStatus.length > 0 &&
    !query.truthStatus.includes(doc.truthStatus)
  ) {
    return false;
  }
  if (query.evidenceBucket && doc.evidenceBucket !== query.evidenceBucket) return false;
  if (
    query.applicableSurface &&
    !doc.applicableSurfaces.includes(query.applicableSurface) &&
    !doc.applicableSurfaces.includes('all')
  ) {
    return false;
  }
  if (
    query.retrievalTags &&
    query.retrievalTags.length > 0 &&
    !includesAll(doc.retrievalTags, query.retrievalTags)
  ) {
    return false;
  }
  if (
    query.relatedFeatures &&
    query.relatedFeatures.length > 0 &&
    !includesAll(doc.relatedFeatures, query.relatedFeatures)
  ) {
    return false;
  }
  if (
    query.sourceAuthority &&
    query.sourceAuthority.length > 0 &&
    !query.sourceAuthority.includes(doc.sourceAuthority)
  ) {
    return false;
  }
  if (
    query.implementationStatus &&
    query.implementationStatus.length > 0 &&
    !query.implementationStatus.includes(doc.implementationStatus)
  ) {
    return false;
  }
  return true;
}

function getMatchedFilters(doc: KnowledgeDocument, query: KnowledgeQuery): string[] {
  const matched: string[] = [];
  if (query.category && doc.category === query.category) matched.push('category');
  if (query.documentType && doc.documentType === query.documentType) {
    matched.push('documentType');
  }
  if (
    query.truthStatus &&
    query.truthStatus.length > 0 &&
    query.truthStatus.includes(doc.truthStatus)
  ) {
    matched.push('truthStatus');
  }
  if (query.evidenceBucket && doc.evidenceBucket === query.evidenceBucket) {
    matched.push('evidenceBucket');
  }
  if (
    query.applicableSurface &&
    (doc.applicableSurfaces.includes(query.applicableSurface) ||
      doc.applicableSurfaces.includes('all'))
  ) {
    matched.push('applicableSurface');
  }
  if (
    query.retrievalTags &&
    query.retrievalTags.length > 0 &&
    includesAll(doc.retrievalTags, query.retrievalTags)
  ) {
    matched.push('retrievalTags');
  }
  if (
    query.relatedFeatures &&
    query.relatedFeatures.length > 0 &&
    includesAll(doc.relatedFeatures, query.relatedFeatures)
  ) {
    matched.push('relatedFeatures');
  }
  if (
    query.sourceAuthority &&
    query.sourceAuthority.length > 0 &&
    query.sourceAuthority.includes(doc.sourceAuthority)
  ) {
    matched.push('sourceAuthority');
  }
  if (
    query.implementationStatus &&
    query.implementationStatus.length > 0 &&
    query.implementationStatus.includes(doc.implementationStatus)
  ) {
    matched.push('implementationStatus');
  }
  return matched;
}

function score(doc: KnowledgeDocument, query: KnowledgeQuery): number {
  let value = 0.1;
  value += getMatchedFilters(doc, query).length * 0.12;
  value += CONFIDENCE_RANK[doc.confidence] * 0.05;
  if (doc.truthStatus === 'implemented_truth') value += 0.05;
  if (doc.truthStatus === 'pending_backend') value -= 0.02;
  return Math.max(0, Math.min(1, Number(value.toFixed(3))));
}

export function queryKnowledgeBase(
  query: KnowledgeQuery,
  docs: KnowledgeDocument[] = loadKnowledgeDocuments(),
): KnowledgeRetrievalResponse {
  const limit = query.limit ?? 20;
  const matching = docs.filter((doc) => matchesQuery(doc, query));
  const results: KnowledgeResult[] = matching
    .map((document) => ({
      document,
      score: score(document, query),
      matchedFilters: getMatchedFilters(document, query),
    }))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.document.title.localeCompare(b.document.title);
    })
    .slice(0, limit);

  return {
    ok: true,
    results,
    totalMatched: matching.length,
    method: 'deterministic',
    retrievedAt: new Date().toISOString(),
  };
}

export function buildKnowledgeContextPacket(
  query: KnowledgeQuery,
  docs: KnowledgeDocument[] = loadKnowledgeDocuments(),
): KnowledgeContextPacket {
  const retrieval = queryKnowledgeBase(query, docs);
  return {
    query,
    retrieval,
    documents: retrieval.results.map(({ document }) => ({
      id: document.id,
      title: document.title,
      category: document.category,
      documentType: document.documentType,
      truthStatus: document.truthStatus,
      implementationStatus: document.implementationStatus,
      evidenceBucket: document.evidenceBucket,
      sourceAuthority: document.sourceAuthority,
      summary: document.summary,
      keyPoints: document.keyPoints,
      doNotOverclaim: document.doNotOverclaim,
      openQuestions: document.openQuestions,
    })),
  };
}
