/**
 * ChatGPT custom-MCP compatibility checks for /mcp/v2.
 *
 * Locks in the remote MCP behaviours ChatGPT expects:
 *   - CORS preflight succeeds
 *   - initialize can be returned as SSE-framed JSON-RPC
 *   - tools/list exposes the required public-safe v2 tools
 *   - required public-safe tools are callable with No Auth
 *   - /mcp/v2/health gives a cheap route-level probe
 */

import { handleMcpV2, handleMcpV2Health } from '../src/mcp-v2';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const REQUIRED_TOOLS = [
  'project.get_current_state',
  'project.get_operating_rules',
  'integrations.get_overview',
  'handoff.get_latest',
] as const;

const env = {} as any;
const originalFetch = globalThis.fetch;

globalThis.fetch = (async () => new Response('upstream unavailable in test', { status: 503 })) as typeof fetch;

async function rpc(body: unknown, accept = 'application/json'): Promise<Response> {
  return handleMcpV2(new Request('https://example.test/mcp/v2', {
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
  const preflight = await handleMcpV2(new Request('https://example.test/mcp/v2', {
    method: 'OPTIONS',
    headers: { origin: 'https://chat.openai.com' },
  }), env);
  assert(preflight.status === 204, `OPTIONS /mcp/v2 returns 204 (got ${preflight.status})`);
  assert(preflight.headers.get('access-control-allow-origin') === '*', 'OPTIONS includes CORS allow-origin');
  assert(
    preflight.headers.get('access-control-allow-methods')?.includes('POST'),
    'OPTIONS allows POST',
  );

  const init = await rpc({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2025-03-26',
      capabilities: {},
      clientInfo: { name: 'chatgpt-custom-mcp-test', version: '0.1.0' },
    },
  }, 'application/json, text/event-stream');
  const initText = await init.text();
  assert(init.status === 200, `initialize returns 200 (got ${init.status})`);
  assert(init.headers.get('content-type')?.includes('text/event-stream'), 'initialize can return SSE');
  assert(initText.includes('event: message'), 'initialize SSE includes event frame');
  assert(initText.includes('"name":"lauburu-mcp-unified"'), 'initialize returns unified server info');

  const listed = await rpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  assert(listed.status === 200, `tools/list returns 200 (got ${listed.status})`);
  assert(listed.headers.get('access-control-allow-origin') === '*', 'tools/list includes CORS');
  const listedJson = await listed.json() as { result: { tools: Array<{ name: string }> } };
  const names = listedJson.result.tools.map((t) => t.name);
  for (const name of REQUIRED_TOOLS) {
    assert(names.includes(name), `tools/list includes ${name}`);
  }

  for (const name of REQUIRED_TOOLS) {
    const called = await rpc({
      jsonrpc: '2.0',
      id: name,
      method: 'tools/call',
      params: { name, arguments: {} },
    });
    assert(called.status === 200, `${name} returns HTTP 200`);
    assert(called.headers.get('access-control-allow-origin') === '*', `${name} includes CORS`);
    const body = await called.json() as {
      result?: { content?: Array<{ type: string; text: string }>; isError?: boolean };
      error?: unknown;
    };
    assert(!body.error, `${name} has no JSON-RPC error`);
    assert(body.result?.isError === false, `${name} is not a tool error`);
    assert(body.result?.content?.[0]?.type === 'text', `${name} returns text content`);
  }

  const health = await handleMcpV2Health(new Request('https://example.test/mcp/v2/health', {
    method: 'GET',
    headers: { origin: 'https://chat.openai.com' },
  }), env);
  assert(health.status === 200, `GET /mcp/v2/health returns 200 (got ${health.status})`);
  assert(health.headers.get('access-control-allow-origin') === '*', 'health includes CORS');
  const healthJson = await health.json() as { ok: boolean; requiredTools: string[] };
  assert(healthJson.ok === true, 'health ok true');
  for (const name of REQUIRED_TOOLS) {
    assert(healthJson.requiredTools.includes(name), `health lists ${name}`);
  }

  globalThis.fetch = originalFetch;
  console.log('MCP v2 ChatGPT compatibility test passed.');
}

main().catch((err) => {
  globalThis.fetch = originalFetch;
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
