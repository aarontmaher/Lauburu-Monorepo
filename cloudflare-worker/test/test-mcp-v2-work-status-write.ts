/**
 * MCP v2 work-status writeback contract.
 *
 * Locks in the admin-gated project.update_work_status tool without
 * touching live Supabase. The test mocks PostgREST and verifies:
 *   - unauthenticated calls fail soft
 *   - authenticated calls upsert connector_work_status + coder lane
 *   - implementation-complete-awaiting-agent-confirmation maps to
 *     the canonical lane enum `needs_review`
 *   - token-shaped text is redacted before storage
 */

import { handleMcpV2 } from '../src/mcp-v2';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const env = {
  ATHLETE_MEMORY_API_TOKEN: 'test-admin-token',
  SUPABASE_URL: 'https://example.supabase.co',
  SUPABASE_SERVICE_ROLE_KEY: 'sb_secret_test_123',
} as any;

const writes: Array<{ url: string; body: unknown }> = [];
const originalFetch = globalThis.fetch;

globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  if (url.startsWith('https://example.supabase.co/rest/v1/')) {
    writes.push({ url, body: init?.body ? JSON.parse(String(init.body)) : null });
    return new Response('', { status: 201 });
  }
  return new Response('not mocked', { status: 500 });
}) as typeof fetch;

async function callTool(headers: Record<string, string> = {}): Promise<any> {
  const req = new Request('https://example.test/mcp/v2', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json', ...headers },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/call',
      params: {
        name: 'project.update_work_status',
        arguments: {
          agent: 'codex',
          status: 'implementation-complete-awaiting-agent-confirmation',
          task: 'HealthNutrition simplified Health tab daily flow',
          summary: 'Health tab daily flow simplified; secret sk-testtoken1234567890 should not persist.',
          branch: 'main',
          commit: 'c8e9f48',
        },
      },
    }),
  });
  const res = await handleMcpV2(req, env);
  assert(res.status === 200, `HTTP 200 from MCP tool call, got ${res.status}`);
  return res.json();
}

async function main(): Promise<void> {
  const unauth = await callTool();
  const unauthText = unauth.result.content[0].text as string;
  assert(unauth.result.isError === true, 'unauthenticated write fails soft');
  assert(unauthText.includes('admin token required'), 'unauthenticated write explains admin token');
  assert(writes.length === 0, 'unauthenticated write does not call Supabase');

  const authed = await callTool({ 'x-athlete-memory-token': 'test-admin-token' });
  const inner = JSON.parse(authed.result.content[0].text);
  assert(inner.ok === true, 'authenticated write returns ok');
  assert(inner.status === 'needs_review', 'implementation-complete maps to needs_review');
  assert(inner.commit === 'c8e9f48', 'commit echoed');
  assert(writes.length === 2, 'authenticated write upserts work status and coder lane');

  const workWrite = writes.find((w) => w.url.includes('connector_work_status'));
  const laneWrite = writes.find((w) => w.url.includes('connector_coder_lanes'));
  assert(workWrite, 'connector_work_status upsert called');
  assert(laneWrite, 'connector_coder_lanes upsert called');
  const lanePayload = (laneWrite!.body as any[])[0].payload;
  assert(lanePayload.status === 'needs_review', 'stored lane status is canonical');
  assert(lanePayload.statusDetail === 'implementation-complete-awaiting-agent-confirmation', 'stored lane keeps detailed status');
  assert(!JSON.stringify(writes).includes('sk-testtoken1234567890'), 'token-shaped text redacted before storage');

  globalThis.fetch = originalFetch;
  console.log('MCP v2 work-status writeback test passed.');
}

main().catch((err) => {
  globalThis.fetch = originalFetch;
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
