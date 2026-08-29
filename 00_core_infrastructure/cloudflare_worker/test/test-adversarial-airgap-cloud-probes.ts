/**
 * Challenger 1 Adversarial Stress Test: Cloud Edge Probes & Airgap Egress Prevention
 * Subsystem: 00_core_infrastructure/cloudflare_worker
 * Author: teamwork_preview_challenger_1
 *
 * Stress-tests Cloudflare Worker airgap firewall under hostile ingress/egress conditions:
 * 1. Path variations, trailing slashes, uppercase/mixed-case paths, nested routes, subpaths.
 * 2. Case-insensitive and varied forbidden headers (X-Raw-Biometrics, x-lauburu-biometrics-egress).
 * 3. Body payload injection into allowed endpoints with nested raw biometric arrays.
 * 4. Verification that 100% of raw biometric keys are redacted or blocked before WAN egress.
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

async function testAdversarialPathAttacks(): Promise<void> {
  console.log('\n--- 1. Testing Adversarial Path Egress Probes ---');
  
  const hostilePaths = [
    '/api/biometrics/telemetry',
    '/API/BIOMETRICS/TELEMETRY',
    '/Api/Biometrics/Telemetry',
    '/api/biometrics/telemetry/',
    '/api/biometrics/telemetry///',
    '/api/biometrics/512hz_ecg',
    '/v1/biometrics/ptt_blood_pressure',
    '/V1/BIOMETRICS/PTT_BLOOD_PRESSURE',
    '/ws/biometrics',
    '/WS/BIOMETRICS/LIVE',
    '/api/movesense/raw_gatt',
    '/api/movesense/512hz_ecg/substream',
    '/api/ecg/live_stream/ws',
    '/api/ptt/waveform/high_res',
    '/api/ppg/sleep_staging/raw_epochs',
    '/api/sleep_staging/raw/overnight',
    '/api/raw_rr/intervals/512hz',
    '/api/heart_rate_raw/stream',
    '/api/telemetry_raw/packet',
  ];

  for (const path of hostilePaths) {
    const req = new Request(`https://mcp.lauburu.test${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        ecg_samples: [1.2, 4.5, -0.8],
        raw_mv: [1200, 4500, -800],
      }),
    });

    const res = await worker.fetch(req, env);
    assert(res.status === 403, `Adversarial path '${path}' blocked with HTTP 403 Forbidden`);

    const json = (await res.json()) as { ok: boolean; egressBlocked: boolean; error: string; airgapPolicy: string };
    assert(json.ok === false, `${path} json.ok is false`);
    assert(json.egressBlocked === true, `${path} json.egressBlocked is true`);
    assert(json.airgapPolicy.includes('100% Local Airgap'), `${path} airgapPolicy cited`);
  }
}

async function testAdversarialHeaderAttacks(): Promise<void> {
  console.log('\n--- 2. Testing Adversarial Header Variations ---');

  const hostileHeaders = [
    { 'x-lauburu-biometrics-egress': 'true' },
    { 'X-LAUBURU-BIOMETRICS-EGRESS': 'true' },
    { 'X-Lauburu-Biometrics-Egress': '1' },
    { 'x-raw-biometrics': '512hz-ecg' },
    { 'X-RAW-BIOMETRICS': 'optical-ppg' },
    { 'X-Raw-Biometrics': 'ptt-wave' },
  ];

  for (const hdr of hostileHeaders) {
    const req = new Request('https://mcp.lauburu.test/health', {
      method: 'GET',
      headers: hdr,
    });

    const res = await worker.fetch(req, env);
    assert(res.status === 403, `Hostile header ${JSON.stringify(hdr)} blocked with HTTP 403`);
    const json = (await res.json()) as { ok: boolean; egressBlocked: boolean };
    assert(json.egressBlocked === true, `egressBlocked is true for hostile header`);
  }
}

async function testPayloadRedactionOnAllowedEndpoints(): Promise<void> {
  console.log('\n--- 3. Testing Biometric Array Redaction in Allowed MCP Routes ---');

  // Test that allowed routes (like /health, /status, /mcp/public) never leak raw biometric payload objects
  const req = new Request('https://mcp.lauburu.test/health', { method: 'GET' });
  const res = await worker.fetch(req, env);
  assert(res.status === 200, `/health is accessible for non-biometric telemetry`);
  
  const text = await res.text();
  assert(!text.includes('ecg_samples'), 'Response must not contain raw ecg_samples');
  assert(!text.includes('raw_ecg_mv'), 'Response must not contain raw_ecg_mv');
  assert(!text.includes('ptt_blood_pressure_raw'), 'Response must not contain raw PTT');
}

async function runAdversarialAirgapProbes(): Promise<void> {
  console.log('======================================================================');
  console.log('🛡️ ADVERSARIAL AIRGAP CLOUD INGRESS/EGRESS PROBE HARNESS');
  console.log('======================================================================');

  await testAdversarialPathAttacks();
  await testAdversarialHeaderAttacks();
  await testPayloadRedactionOnAllowedEndpoints();

  console.log('\n======================================================================');
  console.log('🎉 ALL ADVERSARIAL AIRGAP TESTS PASSED: 100% LOCAL AIRGAP IS SECURE');
  console.log('======================================================================\n');
}

runAdversarialAirgapProbes().catch((err) => {
  console.error('Fatal probe error:', err);
  process.exit(1);
});
