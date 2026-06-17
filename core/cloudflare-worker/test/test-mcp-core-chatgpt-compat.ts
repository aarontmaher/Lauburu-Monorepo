/**
 * ChatGPT custom-MCP compatibility checks for /mcp/core.
 *
 * /mcp/core is the trimmed 6-tool surface added so ChatGPT can attach
 * to GrapplingMap MCP without timing out on the larger /mcp/v2.
 * This test locks in:
 *   - OPTIONS preflight returns 204 with permissive CORS
 *   - GET returns the descriptor with exactly the 6 tools
 *   - initialize handshake (Accept: application/json, text/event-stream)
 *     returns SSE-framed JSON-RPC
 *   - tools/list returns exactly the 6 public-safe tools, in order
 *   - tools/call works with No Auth on every tool
 *   - unknown tools return a structured -32602
 */

import { handleMcpCore } from '../src/mcp-core';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const EXPECTED_TOOLS = [
  'project.get_current_state',
  'project.get_operating_rules',
  'handoff.get_latest',
  'integrations.get_overview',
  'mobile.get_lane_overview',
  'mobile.get_build_overview',
] as const;

const env = {} as any;
const originalFetch = globalThis.fetch;

// Stub upstream fetches the builders make. /mcp/core's six tools all
// degrade gracefully when Supabase / website upstreams are unreachable
// (placeholder payloads), so a 503 stub is enough.
globalThis.fetch = (async () => new Response('upstream unavailable in test', { status: 503 })) as typeof fetch;

async function rpc(body: unknown, accept = 'application/json'): Promise<Response> {
  return handleMcpCore(new Request('https://example.test/mcp/core', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept,
      origin: 'https://chat.openai.com',
    },
    body: JSON.stringify(body),
  }), env);
}

async function main(): Promise<void> {
  // OPTIONS preflight from chat.openai.com.
  const preflight = await handleMcpCore(new Request('https://example.test/mcp/core', {
    method: 'OPTIONS',
    headers: { origin: 'https://chat.openai.com' },
  }), env);
  assert(preflight.status === 204, `OPTIONS /mcp/core returns 204 (got ${preflight.status})`);
  assert(preflight.headers.get('access-control-allow-origin') === '*', 'OPTIONS allow-origin *');
  assert(
    preflight.headers.get('access-control-allow-methods')?.includes('POST'),
    'OPTIONS allow-methods includes POST',
  );

  // GET descriptor — ChatGPT may probe the endpoint with GET first.
  const get = await handleMcpCore(new Request('https://example.test/mcp/core', { method: 'GET' }), env);
  assert(get.status === 200, `GET /mcp/core returns 200 (got ${get.status})`);
  const getBody = await get.json() as any;
  assert(getBody.transport === 'streamable-http', 'GET descriptor advertises streamable-http');
  assert(Array.isArray(getBody.tools), 'GET descriptor lists tools');
  assert(getBody.tools.length === EXPECTED_TOOLS.length, `GET descriptor lists exactly ${EXPECTED_TOOLS.length} tools (got ${getBody.tools.length})`);

  // initialize handshake — Accept includes text/event-stream like ChatGPT.
  const init = await rpc({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2025-03-26',
      capabilities: {},
      clientInfo: { name: 'chatgpt', version: 'test' },
    },
  }, 'application/json, text/event-stream');
  assert(init.status === 200, `initialize returns 200 (got ${init.status})`);
  assert(init.headers.get('content-type')?.startsWith('text/event-stream'), 'initialize negotiates SSE when Accept includes text/event-stream');
  const initText = await init.text();
  assert(initText.startsWith('event: message\n'), 'initialize SSE frame starts with event: message');
  const initPayload = JSON.parse(initText.replace(/^event: message\ndata: /, '').replace(/\n\n$/, ''));
  assert(initPayload.result?.protocolVersion === '2025-03-26', 'initialize result.protocolVersion 2025-03-26');
  assert(initPayload.result?.serverInfo?.name === 'lauburu-mcp-core', 'initialize serverInfo name = lauburu-mcp-core');

  // tools/list — exact set, exact order.
  const listRes = await rpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  assert(listRes.status === 200, 'tools/list returns 200');
  const listBody = await listRes.json() as any;
  const names = (listBody.result?.tools ?? []).map((t: any) => t.name);
  assert(
    JSON.stringify(names) === JSON.stringify(EXPECTED_TOOLS),
    `tools/list returns exactly ${EXPECTED_TOOLS.length} tools in order (got ${names.length}: ${JSON.stringify(names)})`,
  );

  // tools/call every public tool — all must work with No Auth.
  for (const name of EXPECTED_TOOLS) {
    const res = await rpc({ jsonrpc: '2.0', id: name, method: 'tools/call', params: { name, arguments: {} } });
    assert(res.status === 200, `tools/call ${name} returns 200`);
    const body = await res.json() as any;
    assert(!body.error, `tools/call ${name} has no JSON-RPC error`);
    assert(body.result?.content?.[0]?.type === 'text', `tools/call ${name} returns text content`);
    assert(body.result?.isError === false, `tools/call ${name} isError === false`);
  }

  // tools/call unknown tool returns -32602.
  const bad = await rpc({ jsonrpc: '2.0', id: 99, method: 'tools/call', params: { name: 'nope.does_not_exist', arguments: {} } });
  const badBody = await bad.json() as any;
  assert(badBody.error?.code === -32602, 'unknown tool name returns -32602');

  // Method not found returns -32601.
  const mn = await rpc({ jsonrpc: '2.0', id: 100, method: 'nope/unknown' });
  const mnBody = await mn.json() as any;
  assert(mnBody.error?.code === -32601, 'unknown method returns -32601');

  globalThis.fetch = originalFetch;
  console.log(`MCP /mcp/core ChatGPT compatibility test passed (${EXPECTED_TOOLS.length} tools).`);
}

main().catch((err) => {
  console.error('test-mcp-core-chatgpt-compat threw', err);
  process.exit(1);
});
