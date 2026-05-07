/**
 * Operating-rules contract test.
 *
 * Asserts:
 *   1. The Worker constant exposes exactly 13 rules with stable
 *      ids 1..13 in order.
 *   2. Every rule has a non-empty title and body.
 *   3. The corresponding Markdown anchors live in
 *      docs/OPERATING_RULES.md (numbered list "1." through
 *      "13.").
 *   4. Every rule title is reachable from the doc text — the
 *      first non-trivial word of each title appears in the
 *      doc, so a future rename in only one of the two
 *      surfaces fails this test.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-operating-rules.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { OPERATING_RULES, OPERATING_RULES_DOC_PATH } from '../src/operating-rules';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const REPO_ROOT = path.resolve(__dirname, '../../');
const docPath = path.join(REPO_ROOT, OPERATING_RULES_DOC_PATH);

// 1. Count + id contract.
const EXPECTED_RULE_COUNT = 13;
assert(OPERATING_RULES.length === EXPECTED_RULE_COUNT, `OPERATING_RULES.length === ${EXPECTED_RULE_COUNT} (got ${OPERATING_RULES.length})`);
for (let i = 0; i < OPERATING_RULES.length; i++) {
  const r = OPERATING_RULES[i];
  assert(r.id === i + 1, `rule[${i}].id === ${i + 1} (got ${r.id})`);
  assert(typeof r.title === 'string' && r.title.length > 0, `rule[${i}].title non-empty`);
  assert(typeof r.body === 'string' && r.body.length > 0, `rule[${i}].body non-empty`);
}
console.log(`✓ OPERATING_RULES contract: ${EXPECTED_RULE_COUNT} rules, ids 1..${EXPECTED_RULE_COUNT}, all titles + bodies non-empty`);

// 2. Doc reachability.
assert(fs.existsSync(docPath), `${OPERATING_RULES_DOC_PATH} exists`);
const doc = fs.readFileSync(docPath, 'utf8');
for (let i = 1; i <= EXPECTED_RULE_COUNT; i++) {
  const re = new RegExp(`(^|\\n)${i}\\.\\s+\\*\\*`);
  assert(re.test(doc), `${OPERATING_RULES_DOC_PATH} contains numbered anchor "${i}. **"`);
}
console.log(`✓ ${OPERATING_RULES_DOC_PATH} has all ${EXPECTED_RULE_COUNT} numbered rule anchors`);

// 3. Cross-text reachability (loose match — first significant word
//    of each rule title appears somewhere in the doc).
const STOPWORDS = new Set(['the', 'a', 'an', 'on', 'in', 'is', 'and', 'or', 'to', 'of']);
for (const r of OPERATING_RULES) {
  const firstWord = (r.title.match(/[A-Za-z][A-Za-z-]+/g) ?? [])
    .find((w) => !STOPWORDS.has(w.toLowerCase()));
  assert(typeof firstWord === 'string', `rule ${r.id} title has at least one significant word`);
  assert(doc.toLowerCase().includes(firstWord!.toLowerCase()),
    `${OPERATING_RULES_DOC_PATH} mentions rule ${r.id} keyword "${firstWord}"`);
}
console.log(`✓ doc text references every rule's significant first word`);

console.log('Operating-rules contract test passed.');
