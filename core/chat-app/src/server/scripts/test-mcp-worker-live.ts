/**
 * Live integration test for the Cloudflare MCP Worker.
 *
 * Verifies:
 *   1. All five connector routes reject unauthenticated requests
 *      with HTTP 403.
 *   2. With a valid admin token, every route returns HTTP 200 with
 *      a JSON body whose `dataSource` matches the connector
 *      schema's allowed shapes.
 *   3. The /api/terminal_summary payload validates against
 *      TerminalSummary in chat-app/src/server/types/connector.ts.
 *
 * Configuration via env (skipped politely when missing):
 *   MCP_WORKER_URL          - e.g. https://lauburu-mcp-preview.lauburu-aaron.workers.dev
 *   ATHLETE_MEMORY_TOKEN    - same token bundled in mobile + Worker
 *
 * Run:
 *   cd chat-app
 *   MCP_WORKER_URL=… ATHLETE_MEMORY_TOKEN=… \
 *     npx tsx src/server/scripts/test-mcp-worker-live.ts
 *
 * Exits non-zero on any assertion failure. No mocks; real HTTP only.
 */

import {
  CONNECTOR_SCHEMA_VERSION,
  type LaneId,
  type TerminalSummary,
  type TerminalSummaryEntry,
} from '../types/connector';

const ROUTES = [
  '/api/work_status',
  '/api/coder_lanes',
  '/api/build_status',
  '/api/handoff',
  '/api/terminal_summary',
] as const;

const LANE_IDS: ReadonlySet<LaneId> = new Set([
  'claude', 'codex', 'claude_chat', 'chatgpt', 'cowork',
] as const);

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) throw new Error(`assertion failed: ${label}`);
}

function isIsoZ(s: unknown): s is string {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(s);
}

interface DataSourcePlaceholder {
  source: 'placeholder';
  reason?: string;
  message?: string;
  schemaRequired?: { table: string; envelope: readonly string[]; migration: string };
}
interface DataSourceSupabase {
  source: 'supabase';
  table: string;
}
type DataSourceField = DataSourcePlaceholder | DataSourceSupabase;

function validateDataSource(field: unknown, route: string): asserts field is DataSourceField {
  assert(field !== null && typeof field === 'object', `${route} dataSource is object`);
  const ds = field as { source?: unknown };
  assert(ds.source === 'placeholder' || ds.source === 'supabase', `${route} dataSource.source enum`);
  if (ds.source === 'supabase') {
    const t = (field as DataSourceSupabase).table;
    assert(typeof t === 'string' && t.startsWith('connector_'), `${route} dataSource.table connector_*`);
  } else {
    const sr = (field as DataSourcePlaceholder).schemaRequired;
    assert(sr !== undefined, `${route} placeholder must include schemaRequired`);
    assert(typeof sr.table === 'string' && sr.table.startsWith('connector_'), `${route} schemaRequired.table connector_*`);
    assert(typeof sr.migration === 'string' && sr.migration.includes('supabase/migrations/'), `${route} schemaRequired.migration path`);
  }
}

function validateTerminalEntry(entry: TerminalSummaryEntry, prefix: string): void {
  assert(LANE_IDS.has(entry.laneId), `${prefix} laneId enum`);
  assert(isIsoZ(entry.at), `${prefix} at`);
  assert(typeof entry.summary === 'string' && entry.summary.length <= 1200, `${prefix} summary cap`);
  assert(typeof entry.verification === 'string' && entry.verification.length <= 240, `${prefix} verification cap`);
  assert(typeof entry.nextAction === 'string' && entry.nextAction.length <= 240, `${prefix} nextAction cap`);
  assert(entry.exitCode === null || typeof entry.exitCode === 'number', `${prefix} exitCode`);
}

function validateTerminalSummary(payload: TerminalSummary): void {
  assert(payload.schemaVersion === CONNECTOR_SCHEMA_VERSION, 'terminal_summary schemaVersion');
  assert(isIsoZ(payload.generatedAt), 'terminal_summary generatedAt');
  assert(Array.isArray(payload.entries), 'terminal_summary entries array');
  assert(payload.entries.length <= 50, 'terminal_summary entry cap');
  payload.entries.forEach((e, i) => validateTerminalEntry(e, `terminal_summary.entries[${i}]`));
}

async function main(): Promise<void> {
  const baseUrl = (process.env.MCP_WORKER_URL ?? '').replace(/\/+$/, '');
  const token = process.env.ATHLETE_MEMORY_TOKEN ?? '';

  if (!baseUrl || !token) {
    console.log('skipping live worker tests — set MCP_WORKER_URL and ATHLETE_MEMORY_TOKEN to run.');
    return;
  }

  console.log(`Live worker: ${baseUrl}`);

  for (const route of ROUTES) {
    const res = await fetch(`${baseUrl}${route}`);
    assert(res.status === 403, `unauth ${route} → expected 403, got ${res.status}`);
    console.log(`✓ ${route} unauth → 403`);
  }

  for (const route of ROUTES) {
    const res = await fetch(`${baseUrl}${route}`, {
      headers: { 'x-athlete-memory-token': token },
    });
    assert(res.status === 200, `auth ${route} → expected 200, got ${res.status}`);
    const body = (await res.json()) as { dataSource?: unknown };
    validateDataSource(body.dataSource, route);
    console.log(`✓ ${route} auth → 200 (dataSource.source=${(body.dataSource as DataSourceField).source})`);
  }

  const tsRes = await fetch(`${baseUrl}/api/terminal_summary`, {
    headers: { 'x-athlete-memory-token': token },
  });
  const tsBody = (await tsRes.json()) as TerminalSummary;
  validateTerminalSummary(tsBody);
  console.log(`✓ /api/terminal_summary schema valid (entries=${tsBody.entries.length})`);

  console.log('Live MCP Worker tests passed.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exitCode = 1;
});
