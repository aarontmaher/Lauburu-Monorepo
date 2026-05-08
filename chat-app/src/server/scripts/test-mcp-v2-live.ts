export {}; // module isolation — see test-control-centre-route.ts.

/**
 * Live integration test for the /mcp/v2 surface family.
 *
 * The /mcp/v2 path was trimmed to a ChatGPT-friendly 8-tool core.
 * Admin reads + non-core public extras moved to /mcp/v2/admin;
 * website-project proxy tools moved to /mcp/v2/website. This test
 * asserts each surface exposes the right subset and that admin
 * gating still works.
 *
 *   /mcp/v2          — 8 tools across {project, mobile, integrations, handoff}
 *   /mcp/v2/admin    — admin reads (project.get_overview, project.list_priorities,
 *                      mobile.get_<full>, qa.*, release.get_gate, write tools)
 *   /mcp/v2/website  — 25 website.* proxy tools (forwarded)
 *   /mcp/public      — legacy 4-tool surface (must stay green — additive guarantee)
 *
 * Skip-mode when MCP_WORKER_URL or ATHLETE_MEMORY_TOKEN unset.
 */

const CORE_NAMESPACES = ['project', 'mobile', 'integrations', 'handoff'] as const;

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
  const v2Core = `${baseUrl}/mcp/v2`;
  const v2Admin = `${baseUrl}/mcp/v2/admin`;
  const v2Website = `${baseUrl}/mcp/v2/website`;
  const publicV1 = `${baseUrl}/mcp/public`;

  // ── 1. /mcp/v2 core surface ──────────────────────────────────────
  const listEnv = await rpc(v2Core, { jsonrpc: '2.0', id: 1, method: 'tools/list' });
  const coreTools = listEnv.result?.tools ?? [];
  assert(Array.isArray(coreTools) && coreTools.length > 0, 'core tools/list returns array');
  assert(coreTools.length <= 25, `core tools/list stays under ChatGPT cap (got ${coreTools.length})`);
  const coreNamespaceCounts = new Map<string, number>();
  for (const t of coreTools) {
    const ns = t.name.split('.')[0];
    coreNamespaceCounts.set(ns, (coreNamespaceCounts.get(ns) ?? 0) + 1);
  }
  for (const ns of CORE_NAMESPACES) {
    assert((coreNamespaceCounts.get(ns) ?? 0) > 0, `core namespace ${ns}.* has at least 1 tool`);
  }
  assert((coreNamespaceCounts.get('website') ?? 0) === 0, 'core surface excludes website.* tools');
  console.log(`✓ /mcp/v2 (core): ${coreTools.length} tools across ${coreNamespaceCounts.size} namespaces`);

  // ── 2. Public-safe core tools succeed without auth ───────────────
  const corePublicTools = [
    'project.get_current_state',
    'project.get_operating_rules',
    'project.get_work_status',
    'mobile.get_lane_overview',
    'mobile.get_build_overview',
    'integrations.get_overview',
    'handoff.get_latest',
  ];
  for (const name of corePublicTools) {
    const env = await rpc(v2Core, { jsonrpc: '2.0', id: 10, method: 'tools/call', params: { name } });
    assert(env.result?.isError !== true, `core ${name} (no auth) → no isError`);
    const decoded = decodeContent(env);
    assert(decoded !== null, `core ${name} returns content`);
  }
  console.log(`✓ ${corePublicTools.length} core public tools callable without auth`);

  // ── 3. Core admin write tool fails soft without token ────────────
  const coreUnauth = await rpc(v2Core, {
    jsonrpc: '2.0',
    id: 11,
    method: 'tools/call',
    params: { name: 'project.update_work_status', arguments: { agent: 'codex', status: 'working', task: 'live-test' } },
  });
  assert(coreUnauth.result?.isError === true, 'core project.update_work_status (no token) → isError');
  console.log('✓ core project.update_work_status admin gating works');

  // ── 4. /mcp/v2/admin surface ─────────────────────────────────────
  const adminListEnv = await rpc(v2Admin, { jsonrpc: '2.0', id: 20, method: 'tools/list' });
  const adminTools = adminListEnv.result?.tools ?? [];
  assert(adminTools.length > 0, 'admin tools/list non-empty');
  assert(adminTools.length <= 25, `admin tools/list stays under ChatGPT cap (got ${adminTools.length})`);
  const adminNames = new Set(adminTools.map((t) => t.name));
  for (const expected of ['project.get_overview', 'project.list_priorities', 'mobile.get_repo_overview', 'qa.get_latest_result', 'release.get_gate', 'mobile.get_control_centre', 'project.submit_priority_suggestion']) {
    assert(adminNames.has(expected), `admin tools/list includes ${expected}`);
  }
  for (const excluded of corePublicTools) {
    assert(!adminNames.has(excluded), `admin tools/list excludes core-only tool ${excluded}`);
  }
  console.log(`✓ /mcp/v2/admin: ${adminTools.length} tools, includes the moved-out admin + extras set`);

  // ── 5. Admin write tool fails soft without token; succeeds with ──
  const adminUnauth = await rpc(v2Admin, {
    jsonrpc: '2.0',
    id: 21,
    method: 'tools/call',
    params: { name: 'mobile.get_control_centre' },
  });
  assert(adminUnauth.result?.isError === true, 'admin mobile.get_control_centre (no token) → isError');

  const ccEnv = await rpc(v2Admin, { jsonrpc: '2.0', id: 22, method: 'tools/call', params: { name: 'mobile.get_control_centre' } }, token);
  assert(ccEnv.result?.isError !== true, 'admin mobile.get_control_centre with token → no isError');
  const cc = decodeContent(ccEnv) as { schemaVersion?: number; dataSource?: string };
  assert(cc?.schemaVersion === 1, 'control_centre.schemaVersion === 1');
  assert(cc?.dataSource === 'supabase' || cc?.dataSource === 'placeholder', 'control_centre.dataSource enum');
  console.log(`✓ admin mobile.get_control_centre with token → schemaVersion=1, dataSource=${cc.dataSource}`);

  // ── 6. /mcp/v2/website surface ───────────────────────────────────
  const websiteListEnv = await rpc(v2Website, { jsonrpc: '2.0', id: 30, method: 'tools/list' });
  const websiteTools = websiteListEnv.result?.tools ?? [];
  assert(websiteTools.length > 0, 'website tools/list non-empty');
  for (const t of websiteTools) {
    assert(t.name.startsWith('website.'), `website tool ${t.name} carries website. prefix`);
  }
  console.log(`✓ /mcp/v2/website: ${websiteTools.length} proxy tools`);

  // overview consistency check via admin surface (where project.get_overview lives now).
  const overviewEnv = await rpc(v2Admin, { jsonrpc: '2.0', id: 31, method: 'tools/call', params: { name: 'project.get_overview' } });
  const overview = decodeContent(overviewEnv) as { websitePendingCount?: number | null };
  assert(typeof overview?.websitePendingCount === 'number' || overview?.websitePendingCount === null, 'admin project.get_overview.websitePendingCount type');
  console.log(`✓ admin project.get_overview.websitePendingCount = ${overview.websitePendingCount}`);

  const proxyEnv = await rpc(v2Website, { jsonrpc: '2.0', id: 32, method: 'tools/call', params: { name: 'website.list_pending_suggestions' } });
  assert(proxyEnv.result?.isError !== true, 'website.list_pending_suggestions proxy → no isError');
  const proxyDecoded = decodeContent(proxyEnv) as { count?: number; items?: unknown[] } | string;
  if (proxyDecoded && typeof proxyDecoded === 'object' && typeof proxyDecoded.count === 'number' && typeof overview?.websitePendingCount === 'number') {
    assert(proxyDecoded.count === overview.websitePendingCount, 'admin overview.websitePendingCount === website proxy.count');
    console.log(`✓ website proxy count matches admin overview (${proxyDecoded.count})`);
  } else {
    console.log('✓ website proxy returned content (count comparison skipped due to shape)');
  }

  // ── 7. Cross-surface guard ───────────────────────────────────────
  const wrongSurface = await rpc(v2Core, { jsonrpc: '2.0', id: 40, method: 'tools/call', params: { name: 'mobile.get_control_centre' } }, token);
  assert(wrongSurface.error?.code === -32602, 'admin tool on core surface returns -32602');
  console.log('✓ cross-surface guard: admin tools rejected on core path');

  // ── 8. Legacy /mcp/public still returns 4 tools ──────────────────
  const legacyEnv = await rpc(publicV1, { jsonrpc: '2.0', id: 50, method: 'tools/list' });
  const legacyTools = legacyEnv.result?.tools ?? [];
  assert(legacyTools.length === 4, `legacy /mcp/public tools/list expects 4, got ${legacyTools.length}`);
  console.log('✓ legacy /mcp/public still returns 4 tools — additive guarantee held');

  console.log('Unified MCP v2 surface-split live tests passed.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exitCode = 1;
});
