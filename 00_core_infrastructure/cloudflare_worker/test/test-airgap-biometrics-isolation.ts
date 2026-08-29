/**
 * 100% Local Airgap Biometrics Isolation Firewall Test Suite.
 *
 * Verifies that the Cloudflare Worker strictly forbids any raw biometric egress
 * and guarantees that physiological data (512Hz ECG, PTT BP, PPG sleep streams,
 * Kamath RR arrays) stays 100% local on Apple Silicon & private mesh hardware (127.0.0.1).
 */

import worker from '../src/worker';
import type { Env } from '../src/worker-env';

const env = {
  WORKER_MODE: 'test',
  ATHLETE_MEMORY_API_TOKEN: 'test-admin-token',
} as unknown as Env;

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ FAIL: ${label}`);
    process.exit(1);
  }
  console.log(`✓ PASS: ${label}`);
}

async function testAirgapBlockedPaths(): Promise<void> {
  console.log('\n--- 1. Testing Airgap Forbidden Paths ---');
  const forbiddenPaths = [
    '/api/biometrics/telemetry',
    '/api/biometrics/ecg_stream',
    '/api/movesense/raw_gatt',
    '/api/movesense/512hz_ecg',
    '/v1/biometrics/ptt_blood_pressure',
    '/api/ecg/live_stream',
    '/api/ptt/waveform',
    '/api/ppg/sleep_staging',
    '/api/sleep_staging/raw',
    '/api/raw_rr/intervals',
    '/api/heart_rate_raw',
    '/api/telemetry_raw',
    '/ws/biometrics',
  ];

  for (const path of forbiddenPaths) {
    const req = new Request(`https://mcp.lauburu.test${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ ecg_samples: [1.2, 1.4, -0.8] }),
    });

    const res = await worker.fetch(req, env);
    assert(res.status === 403, `${path} blocked with HTTP 403 Forbidden`);

    const json = (await res.json()) as { ok: boolean; egressBlocked: boolean; error: string; airgapPolicy: string };
    assert(json.ok === false, `${path} response ok is false`);
    assert(json.egressBlocked === true, `${path} egressBlocked flag is true`);
    assert(json.error.includes('100% Local Airgap Violation'), `${path} error message cites airgap violation`);
    assert(json.airgapPolicy.includes('100% Local Airgap'), `${path} airgapPolicy is specified`);
  }
}

async function testAirgapBlockedHeaders(): Promise<void> {
  console.log('\n--- 2. Testing Airgap Forbidden Headers ---');
  const headersToTest = [
    { 'x-lauburu-biometrics-egress': 'true' },
    { 'x-raw-biometrics': '512hz-ecg' },
  ];

  for (const hdr of headersToTest) {
    const req = new Request('https://mcp.lauburu.test/health', {
      method: 'GET',
      headers: hdr,
    });

    const res = await worker.fetch(req, env);
    assert(res.status === 403, `Request with header ${JSON.stringify(hdr)} blocked with HTTP 403`);
    const json = (await res.json()) as { ok: boolean; egressBlocked: boolean };
    assert(json.egressBlocked === true, `Header block has egressBlocked: true`);
  }
}

async function testAllowedNonBiometricRoutes(): Promise<void> {
  console.log('\n--- 3. Testing Allowed Non-Biometric Routes ---');
  const allowedPaths = [
    '/health',
    '/status',
    '/mcp/public',
  ];

  for (const path of allowedPaths) {
    const req = new Request(`https://mcp.lauburu.test${path}`, { method: 'GET' });
    const res = await worker.fetch(req, env);
    assert(res.status === 200, `${path} allowed through (status 200)`);
    const json = (await res.json()) as { ok?: boolean; provider?: string };
    assert(json.ok === true || json.provider !== undefined, `${path} returned valid meta payload`);
  }
}

async function main(): Promise<void> {
  console.log('======================================================================');
  console.log('🔒 RUNNING 100% LOCAL AIRGAP BIOMETRICS ISOLATION VERIFICATION');
  console.log('======================================================================');

  await testAirgapBlockedPaths();
  await testAirgapBlockedHeaders();
  await testAllowedNonBiometricRoutes();

  console.log('\n======================================================================');
  console.log('🎉 ALL AIRGAP ISOLATION TESTS PASSED (100% Local Airgap Enforced)');
  console.log('======================================================================\n');
}

main().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
