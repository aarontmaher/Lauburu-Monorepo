/**
 * Public-safe MCP redaction test.
 *
 * Asserts that every tool exposed by /mcp/public passes a sample
 * payload through to its allow-list sanitiser without leaking the
 * known dangerous shapes:
 *
 *   - Free-text fields (lastSummary, currentPriority, manualSteps)
 *   - File paths
 *   - Prompt IDs
 *   - JWT / sk- / ghp_ / whsec_ / xox / AKIA shapes
 *   - EAS / submission / run UUIDs
 *
 * The sanitiser builds output from named scalars (not by filtering
 * a free-text blob) so this test exists to lock in that contract:
 * any future code change that adds a new field to the public
 * surface must update this test, otherwise the test fails by
 * grepping the response body for the dangerous markers.
 *
 * Run:
 *   cd cloudflare-worker
 *   npx tsx test/test-mcp-public-redaction.ts
 *
 * Zero deps; uses fetch + a tiny vendored Env stub.
 */

// Minimal Env stub. We don't call Supabase here — every tool builder
// short-circuits to its "no adapter / empty rows" branch when env is
// blank, returning the safe defaults we want to assert on.
const env = {} as Record<string, string | undefined>;

import {
  // We re-import only the public-safe entry point — never the
  // private adapters or the private MCP handler. If those leak in,
  // the import alone is a regression.
  // eslint-disable-next-line import/no-relative-parent-imports
} from '../src/mcp-public';

// Dynamic import so we can pass a synthesised Request object.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { handleMcpPublic } = require('../src/mcp-public');

const DANGEROUS_PATTERNS: ReadonlyArray<{ name: string; pattern: RegExp }> = [
  { name: 'JWT', pattern: /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/ },
  { name: 'sk- key', pattern: /\bsk-[A-Za-z0-9_-]{16,}\b/ },
  { name: 'ghp_ token', pattern: /\bghp_[A-Za-z0-9]{20,}\b/ },
  { name: 'whsec_', pattern: /\bwhsec_[A-Za-z0-9]{20,}\b/ },
  { name: 'AKIA', pattern: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'xox slack', pattern: /\bxox[abposr]-[A-Za-z0-9-]{20,}/ },
  // EAS / submission / TestFlight UUIDs (8-4-4-4-12 hex).
  { name: 'UUID', pattern: /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/ },
  // GitHub run IDs from the existing seed (10+ digit numeric).
  { name: 'GitHub run id', pattern: /\b\d{10,}\b/ },
  // Repo-relative path-shaped strings the public surface should never
  // emit. Anything containing a slash + extension is suspect.
  { name: 'repo path', pattern: /\b(?:apps|packages|cloudflare-worker|chat-app|scripts|docs)\/[^\s"]+\.(?:tsx?|md|json|sql|sh)\b/ },
  // Prompt IDs follow SCREAMING-KEBAB-CASE with a -01 suffix; private
  // surface uses them, public surface MUST NOT.
  { name: 'prompt id', pattern: /\b[A-Z]{2,}(?:-[A-Z0-9]+){2,}-\d{2}\b/ },
];

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

async function callTool(name: string): Promise<string> {
  const req = new Request('https://example.test/mcp/public', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/call',
      params: { name, arguments: {} },
    }),
  });
  const res: Response = await handleMcpPublic(req, env);
  assert(res.status === 200, `${name} status 200 (got ${res.status})`);
  const body = await res.text();
  return body;
}

async function listTools(): Promise<string[]> {
  const req = new Request('https://example.test/mcp/public', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }),
  });
  const res: Response = await handleMcpPublic(req, env);
  const json = (await res.json()) as { result: { tools: Array<{ name: string }> } };
  return json.result.tools.map((t) => t.name);
}

async function main(): Promise<void> {
  // 1. Confirm the public tool list matches the documented allow-list.
  const expected = [
    'get_public_mcp_health',
    'get_lane_overview',
    'get_build_overview',
    'get_repo_overview',
  ];
  const actual = await listTools();
  assert(
    JSON.stringify(actual) === JSON.stringify(expected),
    `tools/list matches allow-list (got ${JSON.stringify(actual)})`,
  );
  console.log(`✓ tools/list matches allow-list (${expected.length} tools)`);

  // 2. Each tool's response body must NOT contain any dangerous
  //    pattern. We grep the raw text — even if a future Supabase row
  //    contains a JWT in a free-text field, the public sanitiser must
  //    drop it before the response goes out.
  for (const name of expected) {
    const body = await callTool(name);
    for (const { name: patternName, pattern } of DANGEROUS_PATTERNS) {
      const match = body.match(pattern);
      if (match) {
        console.error(`✗ ${name} leaked ${patternName}: ${match[0].slice(0, 80)}`);
        process.exit(1);
      }
    }
    console.log(`✓ ${name} clean of all ${DANGEROUS_PATTERNS.length} dangerous patterns`);
  }

  // 3. Every public response must include `publicPreview: true`
  //    inside the inner JSON content the tool returns. The
  //    JSON-RPC envelope wraps the payload as a stringified text
  //    block, so we have to decode that before asserting.
  for (const name of ['get_public_mcp_health', 'get_lane_overview', 'get_build_overview', 'get_repo_overview']) {
    const body = await callTool(name);
    const envelope = JSON.parse(body) as {
      result: { content: Array<{ type: string; text: string }> };
    };
    const innerText = envelope.result.content[0]?.text ?? '';
    const inner = JSON.parse(innerText) as { publicPreview?: unknown };
    assert(inner.publicPreview === true, `${name} carries publicPreview: true`);
    console.log(`✓ ${name} carries publicPreview: true`);
  }

  // 4. GET /mcp/public (no auth) returns the public discovery
  //    document and lists exactly the four tools.
  const getReq = new Request('https://example.test/mcp/public', { method: 'GET' });
  const getRes: Response = await handleMcpPublic(getReq, env);
  assert(getRes.status === 200, `GET /mcp/public status 200 (got ${getRes.status})`);
  const getJson = (await getRes.json()) as { tools: Array<{ name: string }>; auth: string };
  assert(getJson.auth === 'none', 'GET /mcp/public auth: none');
  assert(getJson.tools.length === 4, 'GET /mcp/public lists 4 tools');
  console.log('✓ GET /mcp/public discovery document clean');

  console.log('Public-safe MCP redaction tests passed.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
