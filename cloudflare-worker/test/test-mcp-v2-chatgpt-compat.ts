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
const adminEnv = { ATHLETE_MEMORY_API_TOKEN: 'test-admin-token' } as any;
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

async function rpcWithToken(body: unknown): Promise<Response> {
  return handleMcpV2(new Request('https://example.test/mcp/v2', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      origin: 'https://chat.openai.com',
      authorization: 'Bearer test-admin-token',
    },
    body: JSON.stringify(body),
  }), adminEnv);
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

  const integrations = await rpc({
    jsonrpc: '2.0',
    id: 'integrations.get_overview.policy',
    method: 'tools/call',
    params: { name: 'integrations.get_overview', arguments: {} },
  });
  const integrationsBody = await integrations.json() as { result?: { content?: Array<{ text: string }>; isError?: boolean } };
  assert(integrationsBody.result?.isError === false, 'integrations.get_overview is public-safe');
  const integrationsPayload = JSON.parse(integrationsBody.result?.content?.[0]?.text ?? '{}') as {
    sources?: Record<string, { readinessRole?: string; userVisible?: boolean }>;
    note?: string;
  };
  assert(integrationsPayload.sources?.health_connect?.readinessRole === 'primary_android', 'Health Connect is Android primary');
  assert(integrationsPayload.sources?.apple_health?.readinessRole === 'primary_ios', 'Apple Health is iOS primary');
  assert(integrationsPayload.sources?.manual_journal?.readinessRole === 'context', 'Manual journal is context');
  assert(integrationsPayload.sources?.whoop_oauth?.readinessRole === 'not_core_readiness', 'WHOOP Direct is not core readiness');
  assert(integrationsPayload.sources?.polar_oauth?.readinessRole === 'not_core_readiness', 'Polar Direct is not core readiness');
  assert(integrationsPayload.sources?.whoop_oauth?.userVisible === false, 'WHOOP Direct hidden from public integration overview');
  assert(integrationsPayload.sources?.polar_oauth?.userVisible === false, 'Polar Direct hidden from public integration overview');

  const priorities = await rpc({
    jsonrpc: '2.0',
    id: 'project.list_priorities',
    method: 'tools/call',
    params: { name: 'project.list_priorities', arguments: {} },
  });
  assert(priorities.status === 200, `project.list_priorities returns HTTP 200 (got ${priorities.status})`);
  const prioritiesBody = await priorities.json() as { result?: { content?: Array<{ text: string }>; isError?: boolean } };
  assert(prioritiesBody.result?.isError === false, 'project.list_priorities is public-safe');
  const prioritiesPayload = JSON.parse(prioritiesBody.result?.content?.[0]?.text ?? '{}') as {
    items?: Array<{ rank?: number; title?: string }>;
  };
  assert(
    prioritiesPayload.items?.[0]?.rank === 0 &&
      prioritiesPayload.items[0].title === 'Native iPhone automation controls from TestFlight app, not Expo-only',
    'project.list_priorities surfaces native iPhone automation as rank 0',
  );

  const unauthWrite = await rpc({
    jsonrpc: '2.0',
    id: 'submit_priority_suggestion_unauth',
    method: 'tools/call',
    params: {
      name: 'project.submit_priority_suggestion',
      arguments: { title: 'Native iPhone automation controls from TestFlight app, not Expo-only' },
    },
  });
  const unauthBody = await unauthWrite.json() as { result?: { isError?: boolean; content?: Array<{ text: string }> } };
  assert(unauthBody.result?.isError === true, 'unauthenticated project.submit_priority_suggestion is blocked');
  assert(
    unauthBody.result?.content?.[0]?.text.includes('admin token required'),
    'unauthenticated write explains admin-token requirement',
  );

  const authedWrite = await rpcWithToken({
    jsonrpc: '2.0',
    id: 'submit_priority_suggestion_authed',
    method: 'tools/call',
    params: {
      name: 'project.submit_priority_suggestion',
      arguments: {
        title: 'Native iPhone automation controls from TestFlight app, not Expo-only',
        source: 'Aaron iPhone app request',
        area: 'mobile-native-automation',
      },
    },
  });
  const authedBody = await authedWrite.json() as { result?: { isError?: boolean; content?: Array<{ text: string }> } };
  assert(authedBody.result?.isError === false, 'authenticated project.submit_priority_suggestion is callable');
  const authedPayload = JSON.parse(authedBody.result?.content?.[0]?.text ?? '{}') as {
    ok?: boolean;
    rank?: number;
    publicWriteAllowed?: boolean;
  };
  assert(authedPayload.ok === true, 'authenticated priority suggestion returns ok true');
  assert(authedPayload.rank === 0, 'authenticated native iPhone priority maps to rank 0');
  assert(authedPayload.publicWriteAllowed === false, 'authenticated response still marks public writes disallowed');

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
