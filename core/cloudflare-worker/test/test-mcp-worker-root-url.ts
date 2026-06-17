/**
 * Lock the `normaliseMcpWorkerRootUrl` contract introduced for
 * the 2026-05-09 iPhone Admin/Dev MCP-unavailable fix. The helper
 * MUST tolerate every form `EXPO_PUBLIC_MCP_BASE_URL` has shipped
 * in (worker root, `/api`, `/mcp/v2`, `/mcp/v2/admin`, with or
 * without a trailing slash) and always return the worker root
 * with no trailing slash, so callers can append the exact path
 * they need without producing 404s like `/mcp/v2/mcp/v2` or
 * `/mcp/v2/api/*`.
 */

import assert from 'node:assert/strict';
import { normaliseMcpWorkerRootUrl, mcpWorkerRootUrl } from '../../apps/mobile/src/services/ai-backend-config';

interface Case {
  label: string;
  input: string | null | undefined;
  expected: string | null;
}

const ROOT = 'https://lauburu-mcp-preview.lauburu-aaron.workers.dev';

const CASES: ReadonlyArray<Case> = [
  { label: 'undefined → null', input: undefined, expected: null },
  { label: 'null → null', input: null, expected: null },
  { label: 'empty string → null', input: '', expected: null },
  { label: 'worker root unchanged', input: ROOT, expected: ROOT },
  { label: 'worker root + trailing slash trimmed', input: `${ROOT}/`, expected: ROOT },
  { label: '/mcp/v2 suffix stripped', input: `${ROOT}/mcp/v2`, expected: ROOT },
  { label: '/mcp/v2/ trailing slash + suffix stripped', input: `${ROOT}/mcp/v2/`, expected: ROOT },
  { label: '/mcp/v2/admin stripped', input: `${ROOT}/mcp/v2/admin`, expected: ROOT },
  { label: '/mcp/v2/website stripped', input: `${ROOT}/mcp/v2/website`, expected: ROOT },
  { label: '/mcp/v2/health stripped', input: `${ROOT}/mcp/v2/health`, expected: ROOT },
  { label: '/api stripped', input: `${ROOT}/api`, expected: ROOT },
  { label: '/mcp/core stripped', input: `${ROOT}/mcp/core`, expected: ROOT },
  { label: '/mcp/public stripped', input: `${ROOT}/mcp/public`, expected: ROOT },
  { label: 'case-insensitive suffix match', input: `${ROOT}/MCP/V2`, expected: ROOT },
  // Regression: the bug we are fixing. EXPO_PUBLIC_MCP_BASE_URL
  // shipped to v19 was the full /mcp/v2 URL, and the v2 client
  // re-appended /mcp/v2 to produce /mcp/v2/mcp/v2. After the
  // normalisation, the resulting core endpoint must be the worker
  // root + /mcp/v2 — never /mcp/v2/mcp/v2.
  {
    label: 'idempotent under successive normalise calls',
    input: normaliseMcpWorkerRootUrl(`${ROOT}/mcp/v2`),
    expected: ROOT,
  },
];

function expectAll(): void {
  for (const c of CASES) {
    const actual = normaliseMcpWorkerRootUrl(c.input ?? null);
    assert.equal(actual, c.expected, `${c.label}: expected ${JSON.stringify(c.expected)} got ${JSON.stringify(actual)}`);
  }
}

function expectEnvLookup(): void {
  // mcpWorkerRootUrl reads process.env on every call. Round-trip
  // through both the bug-shape and the worker-root form to confirm
  // both produce the same normalised result.
  const original = process.env.EXPO_PUBLIC_MCP_BASE_URL;
  try {
    process.env.EXPO_PUBLIC_MCP_BASE_URL = `${ROOT}/mcp/v2`;
    assert.equal(mcpWorkerRootUrl(), ROOT, 'env=/mcp/v2 must normalise to worker root');
    process.env.EXPO_PUBLIC_MCP_BASE_URL = `${ROOT}/mcp/v2/admin`;
    assert.equal(mcpWorkerRootUrl(), ROOT, 'env=/mcp/v2/admin must normalise to worker root');
    process.env.EXPO_PUBLIC_MCP_BASE_URL = ROOT;
    assert.equal(mcpWorkerRootUrl(), ROOT, 'env=worker root must normalise unchanged');
    delete process.env.EXPO_PUBLIC_MCP_BASE_URL;
    assert.equal(mcpWorkerRootUrl(), null, 'env unset must return null');
  } finally {
    if (original === undefined) {
      delete process.env.EXPO_PUBLIC_MCP_BASE_URL;
    } else {
      process.env.EXPO_PUBLIC_MCP_BASE_URL = original;
    }
  }
}

function main(): void {
  expectAll();
  expectEnvLookup();
  console.log(`mcpWorkerRootUrl normalisation contract test passed (${CASES.length} static cases + 4 env-lookup cases).`);
}

main();
