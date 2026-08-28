import { JOURNAL_RESEARCH_SNIPPETS } from '../src/data/journal-research-snippets';

const forbiddenPersonal = /\b(aaron|test@example|example@example|john doe|jane doe|patient name|user id)\b/i;
const bannedPhrases = /\b(you should|this will help|is safe|is dangerous|cures|treats|prescribed)\b/i;
const secretPatterns: ReadonlyArray<{ name: string; pattern: RegExp }> = [
  { name: 'JWT', pattern: /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/ },
  { name: 'sb_secret_', pattern: /\bsb_secret_[A-Za-z0-9_-]{20,}\b/ },
  { name: 'GitHub token', pattern: /\bgh[pousr]_[A-Za-z0-9]{20,}\b/ },
  { name: 'AKIA', pattern: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'sk-', pattern: /\bsk-[A-Za-z0-9_-]{16,}\b/ },
  { name: 'whsec_', pattern: /\bwhsec_[A-Za-z0-9]{20,}\b/ },
];

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

function assertClean(text: string, label: string): void {
  assert(!forbiddenPersonal.test(text), `${label} contains user-private placeholder`);
  assert(!bannedPhrases.test(text), `${label} contains banned phrase`);
  for (const { name, pattern } of secretPatterns) {
    assert(!pattern.test(text), `${label} contains ${name}`);
  }
}

assert(JOURNAL_RESEARCH_SNIPPETS.length >= 30, `expected at least 30 snippets, got ${JOURNAL_RESEARCH_SNIPPETS.length}`);

for (const [index, entry] of JOURNAL_RESEARCH_SNIPPETS.entries()) {
  const prefix = `snippet[${index}] ${entry.canonical}`;
  assert(entry.canonical.trim().length > 0, `${prefix} canonical non-empty`);
  assert(entry.summary.trim().length > 0 && entry.summary.length <= 300, `${prefix} summary length`);
  assert(entry.commonClaims.length > 0 && entry.commonClaims.length <= 5, `${prefix} commonClaims length`);
  assert(entry.sourceLinks.length > 0, `${prefix} sourceLinks non-empty`);
  assert(entry.disclaimer.trim().length >= 30 && entry.disclaimer.length <= 200, `${prefix} disclaimer length`);
  assertClean(entry.canonical, `${prefix} canonical`);
  assertClean(entry.summary, `${prefix} summary`);
  assertClean(entry.disclaimer, `${prefix} disclaimer`);
  for (const claim of entry.commonClaims) {
    assert(claim.trim().length > 0, `${prefix} claim non-empty`);
    assertClean(claim, `${prefix} claim`);
  }
  for (const link of entry.sourceLinks) {
    assert(link.startsWith('https://'), `${prefix} source link https`);
    assert(link.length < 200, `${prefix} source link under 200 chars`);
    assertClean(link, `${prefix} source link`);
  }
}

console.log(`Journal research snippets contract passed (${JOURNAL_RESEARCH_SNIPPETS.length} snippets).`);
