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

// /mcp/v2 (post-trim) advertises EXACTLY these 9 tools — well under
// ChatGPT's ~30-tool picker cap. Admin reads + non-core public
// extras live at /mcp/v2/admin and are exercised separately
// against that surface below. project.ping is the zero-dependency
// diagnostic for clients that fail on richer tools.
const CORE_TOOLS = [
  'project.ping',
  'project.get_current_state',
  'project.get_operating_rules',
  'project.get_work_status',
  'project.update_work_status',
  'handoff.get_latest',
  'integrations.get_overview',
  'mobile.get_lane_overview',
  'mobile.get_build_overview',
] as const;

const CORE_PUBLIC_TOOLS = [
  'project.ping',
  'project.get_current_state',
  'project.get_operating_rules',
  'project.get_work_status',
  'handoff.get_latest',
  'integrations.get_overview',
  'mobile.get_lane_overview',
  'mobile.get_build_overview',
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
  }), env, 'core');
}

async function rpcAdmin(body: unknown): Promise<Response> {
  return handleMcpV2(new Request('https://example.test/mcp/v2/admin', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      origin: 'https://chat.openai.com',
    },
    body: JSON.stringify(body),
  }), env, 'admin');
}

async function rpcAdminWithToken(body: unknown): Promise<Response> {
  return handleMcpV2(new Request('https://example.test/mcp/v2/admin', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      origin: 'https://chat.openai.com',
      authorization: 'Bearer test-admin-token',
    },
    body: JSON.stringify(body),
  }), adminEnv, 'admin');
}

async function rpcCoreWithToken(body: unknown): Promise<Response> {
  return handleMcpV2(new Request('https://example.test/mcp/v2', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      origin: 'https://chat.openai.com',
      authorization: 'Bearer test-admin-token',
    },
    body: JSON.stringify(body),
  }), adminEnv, 'core');
}

async function main(): Promise<void> {
  // ── /mcp/v2 (core) ─────────────────────────────────────────────────
  const preflight = await handleMcpV2(new Request('https://example.test/mcp/v2', {
    method: 'OPTIONS',
    headers: { origin: 'https://chat.openai.com' },
  }), env, 'core');
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
  assert(initText.includes('"surface":"core"'), 'initialize tags surface core');

  const listed = await rpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
  assert(listed.status === 200, `tools/list returns 200 (got ${listed.status})`);
  assert(listed.headers.get('access-control-allow-origin') === '*', 'tools/list includes CORS');
  const listedJson = await listed.json() as { result: { tools: Array<{ name: string }> } };
  const names = listedJson.result.tools.map((t) => t.name);
  assert(
    names.length === CORE_TOOLS.length,
    `tools/list returns exactly ${CORE_TOOLS.length} core tools (got ${names.length}: ${JSON.stringify(names)})`,
  );
  for (const name of CORE_TOOLS) {
    assert(names.includes(name), `tools/list includes core tool ${name}`);
  }
  for (const expelled of ['qa.get_latest_result', 'qa.list_results', 'release.get_gate', 'project.get_overview', 'project.list_priorities', 'mobile.get_repo_overview', 'mobile.get_control_centre']) {
    assert(!names.includes(expelled), `core tools/list does NOT include moved-to-admin tool ${expelled}`);
  }

  for (const name of CORE_PUBLIC_TOOLS) {
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

  // project.ping shape — Agent / ChatGPT diagnostic must remain
  // dependency-free so it answers when richer tools cannot.
  const ping = await rpc({
    jsonrpc: '2.0',
    id: 'project.ping.shape',
    method: 'tools/call',
    params: { name: 'project.ping', arguments: {} },
  });
  const pingBody = await ping.json() as { result?: { content?: Array<{ text: string }>; isError?: boolean } };
  assert(pingBody.result?.isError === false, 'project.ping is not a tool error');
  const pingPayload = JSON.parse(pingBody.result?.content?.[0]?.text ?? '{}') as {
    ok?: boolean;
    publicSafe?: boolean;
    transport?: string;
    protocolVersion?: string;
    auth?: string;
    surface?: string;
    timestamp?: string;
  };
  assert(pingPayload.ok === true, 'project.ping reports ok true');
  assert(pingPayload.publicSafe === true, 'project.ping reports publicSafe true');
  assert(pingPayload.transport === 'streamable-http', 'project.ping advertises streamable-http transport');
  assert(pingPayload.protocolVersion === '2025-03-26', 'project.ping carries protocolVersion 2025-03-26');
  assert(pingPayload.auth === 'no_auth', 'project.ping advertises no_auth');
  assert(pingPayload.surface === 'core', 'project.ping reports surface core');
  assert(typeof pingPayload.timestamp === 'string' && pingPayload.timestamp.length > 0, 'project.ping returns ISO timestamp');

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

  // project.update_work_status lives on /mcp/v2 (core) per Aaron's spec
  // and is admin-token-gated. Calling without a token returns the soft
  // gate error; calling with a valid token returns isError === false.
  const unauthWrite = await rpc({
    jsonrpc: '2.0',
    id: 'core_update_work_status_unauth',
    method: 'tools/call',
    params: {
      name: 'project.update_work_status',
      arguments: { agent: 'codex', status: 'working', task: 'core-surface-test' },
    },
  });
  const unauthBody = await unauthWrite.json() as { result?: { isError?: boolean; content?: Array<{ text: string }> } };
  assert(unauthBody.result?.isError === true, 'unauthenticated project.update_work_status on core is blocked');
  assert(
    unauthBody.result?.content?.[0]?.text.includes('admin token required'),
    'core unauthenticated write explains admin-token requirement',
  );

  // ── /mcp/v2/admin ──────────────────────────────────────────────────
  const adminListed = await rpcAdmin({ jsonrpc: '2.0', id: 'admin-list', method: 'tools/list' });
  assert(adminListed.status === 200, 'admin tools/list returns 200');
  const adminListedJson = await adminListed.json() as { result: { tools: Array<{ name: string }> } };
  const adminNames = adminListedJson.result.tools.map((t) => t.name);
  for (const name of ['qa.get_latest_result', 'qa.list_results', 'release.get_gate', 'project.get_overview', 'project.list_priorities', 'mobile.get_repo_overview', 'mobile.get_control_centre', 'project.submit_priority_suggestion']) {
    assert(adminNames.includes(name), `admin tools/list includes ${name}`);
  }
  for (const exclude of CORE_PUBLIC_TOOLS) {
    assert(!adminNames.includes(exclude), `admin tools/list excludes core-only tool ${exclude}`);
  }

  const priorities = await rpcAdmin({
    jsonrpc: '2.0',
    id: 'project.list_priorities',
    method: 'tools/call',
    params: { name: 'project.list_priorities', arguments: {} },
  });
  assert(priorities.status === 200, `admin project.list_priorities returns HTTP 200 (got ${priorities.status})`);
  const prioritiesBody = await priorities.json() as { result?: { content?: Array<{ text: string }>; isError?: boolean } };
  assert(prioritiesBody.result?.isError === false, 'admin project.list_priorities is public-safe');
  const prioritiesPayload = JSON.parse(prioritiesBody.result?.content?.[0]?.text ?? '{}') as {
    items?: Array<{ rank?: number; title?: string }>;
  };
  assert(
    prioritiesPayload.items?.[0]?.rank === 0 &&
      prioritiesPayload.items[0].title === 'Native iPhone automation controls from TestFlight app, not Expo-only',
    'admin project.list_priorities surfaces native iPhone automation as rank 0',
  );

  const unauthAdminWrite = await rpcAdmin({
    jsonrpc: '2.0',
    id: 'admin_submit_priority_suggestion_unauth',
    method: 'tools/call',
    params: {
      name: 'project.submit_priority_suggestion',
      arguments: { title: 'Native iPhone automation controls from TestFlight app, not Expo-only' },
    },
  });
  const unauthAdminBody = await unauthAdminWrite.json() as { result?: { isError?: boolean; content?: Array<{ text: string }> } };
  assert(unauthAdminBody.result?.isError === true, 'admin unauthenticated submit is blocked');
  assert(
    unauthAdminBody.result?.content?.[0]?.text.includes('admin token required'),
    'admin unauthenticated submit explains admin-token requirement',
  );

  const releaseGate = await rpcAdmin({
    jsonrpc: '2.0',
    id: 'release.get_gate',
    method: 'tools/call',
    params: { name: 'release.get_gate', arguments: {} },
  });
  const releaseGateBody = await releaseGate.json() as { result?: { content?: Array<{ text: string }>; isError?: boolean } };
  assert(releaseGateBody.result?.isError === false, 'admin release.get_gate is public-safe');
  const releaseGatePayload = JSON.parse(releaseGateBody.result?.content?.[0]?.text ?? '{}') as {
    buildAllowed?: { ios?: boolean; android?: boolean };
    reason?: string;
    publicSafe?: boolean;
  };
  assert(releaseGatePayload.publicSafe === true, 'release.get_gate marks publicSafe');
  assert(releaseGatePayload.buildAllowed?.ios === false, 'release.get_gate blocks iOS without installed-device QA');
  assert(releaseGatePayload.buildAllowed?.android === false, 'release.get_gate blocks Android without installed-device QA');
  assert(/repo.only|No Agent QA|Supabase bridge/i.test(releaseGatePayload.reason ?? ''), 'release.get_gate explains blocked gate');

  const authedAdminWrite = await rpcAdminWithToken({
    jsonrpc: '2.0',
    id: 'admin_submit_priority_suggestion_authed',
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
  const authedAdminBody = await authedAdminWrite.json() as { result?: { isError?: boolean; content?: Array<{ text: string }> } };
  assert(authedAdminBody.result?.isError === false, 'admin authenticated project.submit_priority_suggestion is callable');
  const authedPayload = JSON.parse(authedAdminBody.result?.content?.[0]?.text ?? '{}') as {
    ok?: boolean;
    rank?: number;
    publicWriteAllowed?: boolean;
  };
  assert(authedPayload.ok === true, 'authenticated priority suggestion returns ok true');
  assert(authedPayload.rank === 0, 'authenticated native iPhone priority maps to rank 0');
  assert(authedPayload.publicWriteAllowed === false, 'authenticated response still marks public writes disallowed');

  // Cross-surface guard: admin tools must NOT be callable on the core
  // path even with a valid token. They moved out of /mcp/v2.
  const crossSurface = await rpcCoreWithToken({
    jsonrpc: '2.0',
    id: 'release_get_gate_on_core',
    method: 'tools/call',
    params: { name: 'release.get_gate', arguments: {} },
  });
  const crossBody = await crossSurface.json() as { error?: { code?: number; message?: string } };
  assert(crossBody.error?.code === -32602, 'release.get_gate is rejected on core surface (-32602)');
  assert(/Unknown tool for core surface/i.test(crossBody.error?.message ?? ''), 'cross-surface error names the surface');

  // ── /mcp/v2/health ─────────────────────────────────────────────────
  const health = await handleMcpV2Health(new Request('https://example.test/mcp/v2/health', {
    method: 'GET',
    headers: { origin: 'https://chat.openai.com' },
  }), env);
  assert(health.status === 200, `GET /mcp/v2/health returns 200 (got ${health.status})`);
  assert(health.headers.get('access-control-allow-origin') === '*', 'health includes CORS');
  const healthJson = await health.json() as { ok: boolean; requiredTools: string[] };
  assert(healthJson.ok === true, 'health ok true');
  // health endpoint advertises the canonical core + admin required tools.
  for (const name of ['project.get_current_state', 'project.get_operating_rules', 'integrations.get_overview', 'handoff.get_latest']) {
    assert(healthJson.requiredTools.includes(name), `health lists ${name}`);
  }

  globalThis.fetch = originalFetch;
  console.log(`MCP v2 ChatGPT compatibility test passed (core=${CORE_TOOLS.length} tools).`);
}

main().catch((err) => {
  globalThis.fetch = originalFetch;
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
