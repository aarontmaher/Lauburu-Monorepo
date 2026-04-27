import type { KnowledgeDocument } from './types';
import { seedKnowledgeDocuments } from './docs';

function dedupeSorted(values: string[]): string[] {
  return Array.from(
    new Set(values.map((value) => value.trim()).filter(Boolean)),
  ).sort((a, b) => a.localeCompare(b));
}

function assertIsoDate(value: string, field: string, docId: string): void {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new Error(`Knowledge doc ${docId} has invalid ${field}: ${value}`);
  }
}

function validateDoc(doc: KnowledgeDocument): KnowledgeDocument {
  if (!doc.id) throw new Error('Knowledge doc missing id');
  if (!doc.canonicalSlug) {
    throw new Error(`Knowledge doc ${doc.id} missing canonicalSlug`);
  }
  if (!doc.title) throw new Error(`Knowledge doc ${doc.id} missing title`);
  if (!doc.summary) throw new Error(`Knowledge doc ${doc.id} missing summary`);
  if (!doc.detailedBody) {
    throw new Error(`Knowledge doc ${doc.id} missing detailedBody`);
  }
  if (doc.version < 1) {
    throw new Error(`Knowledge doc ${doc.id} version must be >= 1`);
  }
  assertIsoDate(doc.createdAt, 'createdAt', doc.id);
  assertIsoDate(doc.updatedAt, 'updatedAt', doc.id);
  assertIsoDate(doc.lastReviewed, 'lastReviewed', doc.id);

  return {
    ...doc,
    subcategories: dedupeSorted(doc.subcategories),
    keyPoints: dedupeSorted(doc.keyPoints),
    applicableSurfaces: Array.from(new Set(doc.applicableSurfaces)),
    relatedFeatures: dedupeSorted(doc.relatedFeatures),
    relatedEntities: dedupeSorted(doc.relatedEntities),
    retrievalTags: dedupeSorted(doc.retrievalTags),
    openQuestions: dedupeSorted(doc.openQuestions),
    doNotOverclaim: dedupeSorted(doc.doNotOverclaim),
    supersedes: dedupeSorted(doc.supersedes),
  };
}

export function loadKnowledgeDocuments(): KnowledgeDocument[] {
  const ids = new Set<string>();
  const slugs = new Set<string>();
  return seedKnowledgeDocuments.map((doc) => {
    const next = validateDoc(doc);
    if (ids.has(next.id)) throw new Error(`Duplicate knowledge doc id: ${next.id}`);
    if (slugs.has(next.canonicalSlug)) {
      throw new Error(`Duplicate knowledge doc canonicalSlug: ${next.canonicalSlug}`);
    }
    ids.add(next.id);
    slugs.add(next.canonicalSlug);
    return next;
  });
}

export function getKnowledgeDocumentBySlug(
  canonicalSlug: string,
  docs: KnowledgeDocument[] = loadKnowledgeDocuments(),
): KnowledgeDocument | null {
  return docs.find((doc) => doc.canonicalSlug === canonicalSlug) ?? null;
}
