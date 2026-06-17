import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const specPath = path.join(ROOT, 'docs', 'FS021_HEALTH_INPUTS_EXPANSION_SPEC.md');
const spec = fs.readFileSync(specPath, 'utf8');

for (const phrase of [
  'No medical advice',
  'No causation claims',
  'training/performance context only',
  'nutrition habit context only',
  'auth.uid() = user_id',
  'lactate_measurements',
  'nutrition_checklist_daily',
]) {
  assert.ok(spec.includes(phrase), `FS-021 spec missing required phrase: ${phrase}`);
}

const banned = /\b(this caused|you should|is safe|is dangerous|diagnoses|treats|cures)\b/i;
assert.equal(banned.test(spec), false, 'FS-021 spec contains unsafe/clinical/causal wording');

const privateData = /\b(test@example|bearer|jwt|sk-|ghp_|whsec_|sb_secret_|AKIA[0-9A-Z]{16})\b/i;
assert.equal(privateData.test(spec), false, 'FS-021 spec contains private-looking data or secret-shaped text');

console.log('FS-021 health inputs spec checks OK');
