import { JOURNAL_CANONICAL_TERMS, JOURNAL_ITEM_CATEGORIES } from '../src/data/journal-canonical-terms';

const allowedCategories = new Set<string>(JOURNAL_ITEM_CATEGORIES);
const sensitiveConfirmationCategories = new Set(['medication', 'peptide', 'inhaler', 'sleep_aid']);
const forbiddenPersonal = /\b(aaron|test@example|example@example|john doe|jane doe|patient name|user id)\b/i;
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
  for (const { name, pattern } of secretPatterns) {
    assert(!pattern.test(text), `${label} contains ${name}`);
  }
}

const canonicals = new Set<string>();

assert(JOURNAL_CANONICAL_TERMS.length >= 140, `expected ~150 canonical terms, got ${JOURNAL_CANONICAL_TERMS.length}`);

for (const [index, entry] of JOURNAL_CANONICAL_TERMS.entries()) {
  const prefix = `entry[${index}] ${entry.canonical}`;
  assert(entry.canonical.trim().length > 0, `${prefix} canonical non-empty`);
  assert(!canonicals.has(entry.canonical.toLowerCase()), `${prefix} canonical duplicate`);
  canonicals.add(entry.canonical.toLowerCase());
  assert(allowedCategories.has(entry.category), `${prefix} category is FS-018 enum`);
  assert(Array.isArray(entry.aliases), `${prefix} aliases array`);
  assert(entry.aliases.length > 0 || entry.needsConfirmation === false, `${prefix} alias or low-risk exact-match`);
  assertClean(entry.canonical, `${prefix} canonical`);
  for (const alias of entry.aliases) {
    assert(alias.length > 0, `${prefix} alias non-empty`);
    assert(alias === alias.trim(), `${prefix} alias trimmed: ${alias}`);
    assert(alias === alias.toLowerCase(), `${prefix} alias lowercase: ${alias}`);
    assertClean(alias, `${prefix} alias`);
  }
  if (entry.needsConfirmation === true) {
    assert(sensitiveConfirmationCategories.has(entry.category), `${prefix} sensitive confirmation category`);
  }
}

console.log(`Journal canonical terms contract passed (${JOURNAL_CANONICAL_TERMS.length} terms).`);
