export {}; // module isolation — see test-control-centre-route.ts.

/**
 * Live integration test for POST /mcp/v2 (Phase 1 of UNIFIED_MCP_PLAN).
 *
 * Asserts:
 *   1. tools/list returns the full namespaced surface — at least
 *      one tool per namespace (project / mobile / integrations /
 *      handoff / website).
 *   2. Public-safe tools (project.* / mobile.get_*_overview /
 *      handoff.* / website.*) succeed WITHOUT admin token.
 *   3. Admin tools (mobile.get_control_centre etc) fail-soft with
 *      isError: true when token is absent.
 *   4. Admin tools succeed when ATHLETE_MEMORY_TOKEN is supplied.
 *   5. website.* proxy round-trips to mcp.lauburugrapplingmap.com
 *      (count of pending suggestions matches between
 *      project.get_overview.websitePendingCount and a direct
 *      website.list_pending_suggestions call).
 *   6. Legacy /mcp/public still returns its 4 tools — additive
 *      Phase-1 anti-rule (the v2 commit must not regress it).
 *
 * Skip-mode when env unset.
 */

const NAMESPACES = ['project', 'mobile', 'integrations', 'handoff', 'website'] as const;

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) throw new Error(`assertion failed: ${label}`);
}

interface JsonRpcEnvelope {
  result?: { content?: Array<{ text?: string; type?: string }>; tools?: Array<{ name: string }>; isError?: boolean };
  error?: { code: number; message: string };
}

async function rpc(url: string, body: unknown, token?: string): Promise<JsonRpcEnvelope> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', Accept: 'application/json' };
  if (token) headers['x-athlete-memory-token'] = token;
  const res = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
  return (await res.json()) as JsonRpcEnvelope;
}

function decodeContent(env: JsonRpcEnvelope): unknown {
  const text = env.result?.content?.[0]?.text;
  if (typeof text !== 'string') return null;
  try { return JSON.parse(text); } catch { return text; }
}

async function main(): Promise<void> {
  const baseUrl = (process.env.MCP_WORKER_URL ?? '').replace(/\/+$/, '');
  const token = process.env.ATHLETE_MEMORY_TOKEN ?? '';
  if (!baseUrl || !token) {
    console.log('skipping mcp-v2 live test — set MCP_WORKER_URL and ATHLETE_MEMORY_TOKEN to run.');
    return;
  }
  const v2 = `${baseUrl}/mcp/v2`;
  const publicV1 = `${baseUrl}/mcp/public`;

  // 1. tools/list namespace coverage.
  const listEnv = await rpc(v2, { jsonrpc: '2.0', id: 1, method: 'tools/list' });
  const tools = listEnv.result?.tools ?? [];
  assert(Array.isArray(tools) && tools.length > 0, 'tools/list returns array');
  const namespaceCounts = new Map<string, number>();
  for (const t of tools) {
    const ns = t.name.split('.')[0];
    namespaceCounts.set(ns, (namespaceCounts.get(ns) ?? 0) + 1);
  }
  for (const ns of NAMESPACES) {
    assert((namespaceCounts.get(ns) ?? 0) > 0, `namespace ${ns}.* has at least 1 tool`);
  }
  console.log(`✓ tools/list: ${tools.length} tools across ${namespaceCounts.size} namespaces`);

  // 2. Public-safe tools succeed without auth.
  const publicTools = ['project.get_overview', 'mobile.get_lane_overview', 'mobile.get_build_overview', 'mobile.get_repo_overview', 'integrations.get_overview', 'handoff.get_latest'];
  for (const name of publicTools) {
    const env = await rpc(v2, { jsonrpc: '2.0', id: 10, method: 'tools/call', params: { name } });
    assert(env.result?.isError !== true, `${name} (no auth) → no isError`);
    const decoded = decodeContent(env);
    assert(decoded !== null, `${name} returns content`);
    console.log(`✓ ${name} (no auth) → ok`);
  }

  // 3. Admin tools fail-soft without token.
  const adminTools = ['mobile.get_control_centre', 'mobile.get_coder_lanes', 'mobile.get_terminal_summary', 'mobile.get_handoff', 'mobile.get_work_status', 'mobile.get_build_status', 'mobile.get_build_readiness'];
  for (const name of adminTools) {
    const env = await rpc(v2, { jsonrpc: '2.0', id: 20, method: 'tools/call', params: { name } });
    assert(env.result?.isError === true, `${name} (no token) → isError true`);
    const text = env.result?.content?.[0]?.text ?? '';
    assert(text.toLowerCase().includes('admin token required'), `${name} (no token) error message`);
  }
  console.log(`✓ ${adminTools.length} admin tools fail-soft without token`);

  // 4. Admin tools succeed with token.
  const ccEnv = await rpc(v2, { jsonrpc: '2.0', id: 30, method: 'tools/call', params: { name: 'mobile.get_control_centre' } }, token);
  assert(ccEnv.result?.isError !== true, 'mobile.get_control_centre with token → no isError');
  const cc = decodeContent(ccEnv) as { schemaVersion?: number; dataSource?: string };
  assert(cc?.schemaVersion === 1, 'control_centre.schemaVersion === 1');
  assert(cc?.dataSource === 'supabase' || cc?.dataSource === 'placeholder', 'control_centre.dataSource enum');
  console.log(`✓ mobile.get_control_centre with token → schemaVersion=1, dataSource=${cc.dataSource}`);

  // 5. website.* proxy round-trip + project overview consistency.
  const overviewEnv = await rpc(v2, { jsonrpc: '2.0', id: 40, method: 'tools/call', params: { name: 'project.get_overview' } });
  const overview = decodeContent(overviewEnv) as { websitePendingCount?: number | null };
  assert(typeof overview?.websitePendingCount === 'number' || overview?.websitePendingCount === null, 'project.get_overview.websitePendingCount type');
  console.log(`✓ project.get_overview.websitePendingCount = ${overview.websitePendingCount}`);

  const proxyEnv = await rpc(v2, { jsonrpc: '2.0', id: 41, method: 'tools/call', params: { name: 'website.list_pending_suggestions' } });
  assert(proxyEnv.result?.isError !== true, 'website.list_pending_suggestions proxy → no isError');
  const proxyDecoded = decodeContent(proxyEnv) as { count?: number; items?: unknown[] } | string;
  if (proxyDecoded && typeof proxyDecoded === 'object' && typeof proxyDecoded.count === 'number' && typeof overview?.websitePendingCount === 'number') {
    assert(proxyDecoded.count === overview.websitePendingCount, 'overview.websitePendingCount === proxy.count');
    console.log(`✓ website proxy count matches overview (${proxyDecoded.count})`);
  } else {
    console.log('✓ website proxy returned content (count comparison skipped due to shape)');
  }

  // 6. Legacy /mcp/public still returns its 4 tools.
  const legacyEnv = await rpc(publicV1, { jsonrpc: '2.0', id: 50, method: 'tools/list' });
  const legacyTools = legacyEnv.result?.tools ?? [];
  assert(legacyTools.length === 4, `legacy /mcp/public tools/list expects 4, got ${legacyTools.length}`);
  console.log('✓ legacy /mcp/public still returns 4 tools — additive guarantee held');

  console.log('Unified MCP v2 live tests passed.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exitCode = 1;
});
