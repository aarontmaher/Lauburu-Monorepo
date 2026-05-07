import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const migrationPath = path.join(ROOT, 'supabase', 'migrations', '0006_journal_imports_macros_terms.sql');
const sql = fs.readFileSync(migrationPath, 'utf8');

const tables = [
  'journal_term_normalizations',
  'nutrition_daily_log',
  'journal_imports',
] as const;

for (const table of tables) {
  assert.match(sql, new RegExp(`create table if not exists public\\.${table}\\s*\\(`, 'i'), `${table} table missing`);
  assert.match(sql, new RegExp(`user_id uuid not null references auth\\.users\\(id\\)`, 'i'), `${table} missing user_id`);
  assert.match(sql, new RegExp(`alter table public\\.${table} enable row level security`, 'i'), `${table} RLS missing`);
  assert.match(sql, new RegExp(`create policy ${table}_self on public\\.${table}`, 'i'), `${table} self policy missing`);
  assert.match(sql, /using \(auth\.uid\(\) = user_id\)/i, `${table} policy missing auth.uid using check`);
  assert.match(sql, /with check \(auth\.uid\(\) = user_id\)/i, `${table} policy missing auth.uid write check`);
}

assert.match(
  sql,
  /unique \(user_id, raw_text\)/i,
  'journal_term_normalizations must dedupe per user and raw text',
);
assert.match(
  sql,
  /create index if not exists idx_journal_term_normalizations_user_raw_text\s+on public\.journal_term_normalizations\(user_id, raw_text\)/i,
  'journal_term_normalizations user/raw_text index missing',
);
assert.match(
  sql,
  /unique \(user_id, date, source\)/i,
  'nutrition_daily_log must dedupe per user/date/source',
);
assert.match(
  sql,
  /create index if not exists idx_nutrition_daily_log_user_date\s+on public\.nutrition_daily_log\(user_id, date\)/i,
  'nutrition_daily_log user/date index missing',
);

const forbiddenPublicWrite = /\bpublic\s+(insert|update|delete)\b|\bgrant\s+(insert|update|delete)\s+on\b/i;
assert.equal(forbiddenPublicWrite.test(sql), false, 'migration must not grant public writes');

console.log('journal import migration RLS/privacy checks OK');
