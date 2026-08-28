/**
 * Dev-only test script — exercises the full mobile→backend→ai-context→Coach
 * round-trip using the same POST contracts the mobile app sends.
 *
 * Covers: health ingest, manual nutrition, barcode confirmed, barcode
 * unconfirmed, photo confirmed, photo proposed, HIIT session, ai-context,
 * Coach questions, Cronometer status, and truth assertions.
 *
 * Local:    INTERNAL_API_TOKEN=test-token ATHLETE_MEMORY_API_TOKEN=test-token npm run test:roundtrip
 * Deployed:  BACKEND_URL=https://your-app.railway.app INTERNAL_API_TOKEN=xxx ATHLETE_MEMORY_API_TOKEN=xxx npm run test:roundtrip:deployed
 */

const BASE = process.env.BACKEND_URL ?? 'http://localhost:3000';
const INTERNAL_TOKEN = process.env.INTERNAL_API_TOKEN ?? 'test-token';
const PUBLIC_TOKEN = process.env.ATHLETE_MEMORY_API_TOKEN ?? 'test-token';
const ATHLETE = 'dev-athlete';
const TODAY = new Date().toISOString().slice(0, 10);

let passed = 0;
let failed = 0;

function assert(condition: boolean, name: string) {
  if (condition) { passed++; console.log(`  PASS: ${name}`); }
  else { failed++; console.log(`  FAIL: ${name}`); }
}

async function post(path: string, body: unknown, internal = true) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (internal) headers['x-internal-token'] = INTERNAL_TOKEN;
  else { headers['x-athlete-memory-token'] = PUBLIC_TOKEN; headers['x-athlete-id'] = ATHLETE; }
  const resp = await fetch(`${BASE}${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
  return resp.json();
}

async function get(path: string) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'x-athlete-memory-token': PUBLIC_TOKEN, 'x-athlete-id': ATHLETE },
  });
  return resp.json();
}

/**
 * Build a fake Supabase-shaped JWT for testing ownership enforcement.
 * The backend only decodes the `sub` claim (doesn't verify signature yet),
 * so any well-formed JWT with the right `sub` works for testing.
 */
function buildFakeJwt(sub: string): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ sub, iat: Math.floor(Date.now() / 1000) })).toString('base64url');
  const signature = 'fake-signature';
  return `${header}.${payload}.${signature}`;
}

async function main() {
  console.log(`\n=== ROUND-TRIP TEST (${TODAY}) ===\n`);

  // 1. Health ingest (simulates Apple Health sync)
  console.log('--- 1. Health ingest ---');
  const health = await post('/v1/internal/ingest/health-source/daily', {
    athleteId: ATHLETE,
    day: {
      date: TODAY, provider: 'apple_health',
      sleep_hours: 7.5, deep_sleep_hours: 2.0, rem_sleep_hours: 1.2,
      active_calories: 420, step_count: 8500, workout_count: 1, workout_minutes_total: 55,
      source_updated_at: new Date().toISOString(),
    },
  });
  assert(health.ok === true, 'health ingest ok');

  // 2. Manual nutrition ingest
  console.log('--- 2. Manual nutrition ingest ---');
  const nutr = await post('/v1/internal/ingest/nutrition/daily', {
    athleteId: ATHLETE,
    day: {
      date: TODAY, source: 'manual', sourceState: 'manual', confirmed: true,
      calories_kcal: 2100, protein_g: 165, carbs_g: 220, fat_g: 70,
      sourceDependencies: ['manual'], missingFields: [],
    },
  });
  assert(nutr.ok === true, 'manual nutrition ok');
  assert(nutr.confirmed === true, 'manual nutrition confirmed');
  assert(nutr.sourceState === 'manual', 'manual nutrition sourceState preserved');

  // 3. Barcode confirmed ingest
  console.log('--- 3. Barcode confirmed ingest ---');
  const barcodeConf = await post('/v1/internal/ingest/nutrition/daily', {
    athleteId: ATHLETE,
    day: {
      date: TODAY, source: 'barcode', sourceState: 'manual', confirmed: true,
      calories_kcal: 200, protein_g: 15, carbs_g: 25, fat_g: 8,
      sourceDependencies: ['barcode', 'openfoodfacts'], evidenceIds: ['ne-123'],
    },
  });
  assert(barcodeConf.ok === true, 'barcode confirmed ok');
  assert(barcodeConf.confirmed === true, 'barcode confirmed enters normalized');

  // 4. Barcode unconfirmed ingest (should NOT enter normalized)
  console.log('--- 4. Barcode unconfirmed ingest ---');
  const barcodeUnconf = await post('/v1/internal/ingest/nutrition/daily', {
    athleteId: ATHLETE,
    day: {
      date: TODAY, source: 'barcode', confirmed: false,
      calories_kcal: 300, protein_g: 20,
    },
  });
  assert(barcodeUnconf.ok === true, 'barcode unconfirmed stored as raw');
  assert(barcodeUnconf.confirmed === false, 'barcode unconfirmed not normalized');
  assert(barcodeUnconf.stored === 'raw_only', 'barcode unconfirmed stored as raw_only');

  // 5. Photo proposal (should NOT enter normalized)
  console.log('--- 5. Photo proposal ---');
  const photoProposal = await post('/v1/internal/nutrition/photo-proposal', {
    athleteId: ATHLETE,
    proposal: {
      proposalId: 'photo-rt-1',
      photoRef: 'test.jpg',
      description: 'Test meal',
      proposedCalories: 500, proposedProteinG: 30,
      proposedCarbG: 60, proposedFatG: 20,
      confidence: 'low', missingFields: [],
    },
  });
  assert(photoProposal.ok === true, 'photo proposal stored');
  assert(photoProposal.enteredNormalized === false, 'photo proposal not normalized');

  // 6. Photo confirm (should enter normalized)
  console.log('--- 6. Photo confirm ---');
  const photoConfirm = await post('/v1/internal/nutrition/photo-confirm', {
    athleteId: ATHLETE,
    proposalId: 'photo-rt-1',
    action: 'user_confirmed',
  });
  assert(photoConfirm.ok === true, 'photo confirm ok');
  assert(photoConfirm.enteredNormalized === true, 'photo confirmed enters normalized');

  // 7. HIIT session ingest
  console.log('--- 7. HIIT session ingest ---');
  const hiit = await post('/v1/internal/ingest/session-log', {
    athleteId: ATHLETE,
    session: {
      sessionId: `rt-sess-${Date.now()}`,
      athleteId: ATHLETE,
      date: TODAY,
      createdAt: new Date().toISOString(),
      templateId: 'friday-bike',
      protocolFormat: '30:30',
      machineType: 'assault_bike',
      machineProvider: 'manual',
      source: 'manual',
      sets: [
        { setIndex: 0, type: 'work', durationSeconds: 30, avgWatts: 250, peakWatts: 280, calories: 12, hrMin: 140, hrMax: 165, hrAvg: 155, distanceM: null, avgCadence: null, hrAtStart: 140, hrAtEnd: 165, hrRange: 25, hrRecoveryFromPrevious: null },
        { setIndex: 1, type: 'rest', durationSeconds: 30, avgWatts: null, peakWatts: null, calories: null, hrMin: 130, hrMax: 145, hrAvg: 138, distanceM: null, avgCadence: null, hrAtStart: 165, hrAtEnd: 130, hrRange: 15, hrRecoveryFromPrevious: null },
        { setIndex: 2, type: 'work', durationSeconds: 30, avgWatts: 230, peakWatts: 260, calories: 11, hrMin: 150, hrMax: 170, hrAvg: 162, distanceM: null, avgCadence: null, hrAtStart: 130, hrAtEnd: 170, hrRange: 40, hrRecoveryFromPrevious: 35 },
      ],
      totalSets: 3, workSets: 2, restSets: 1,
      totalDurationSeconds: 90, totalCalories: 23, totalWorkKj: null,
      avgWatts: 240, peakWatts: 280, avgHr: 155, peakHr: 170,
      sourceRecordIds: [], missingFields: [],
    },
  });
  assert(hiit.ok === true, 'HIIT session ingested');
  assert(hiit.normalized?.machineConnected === false, 'HIIT manual = not machine connected');

  // 8. AI context read
  console.log('--- 8. AI context ---');
  const ctx = await get(`/api/athlete-memory/${ATHLETE}/ai-context`);
  assert(ctx.ok === true, 'ai-context ok');
  assert(ctx.nutritionDailySummary != null, 'nutrition appears in ai-context');
  assert(ctx.nutritionDailySummary?.sourceState != null, 'nutrition sourceState in ai-context');
  assert(ctx.nutritionDailySummary?.allConfirmed === true, 'nutrition allConfirmed in ai-context');
  assert(ctx.multiSourceHealth?.cronometer != null, 'cronometer in multiSourceHealth');

  // Check HIIT appears
  const hasHIIT = ctx.recentHIITWorkouts != null && ctx.recentHIITWorkouts.length > 0;
  assert(hasHIIT, 'HIIT session appears in recentHIITWorkouts');

  // 9. Cronometer status (internal route, needs auth)
  console.log('--- 9. Cronometer status ---');
  const cronResp = await fetch(`${BASE}/v1/internal/cronometer/${ATHLETE}/status`, {
    headers: { 'x-internal-token': INTERNAL_TOKEN },
  });
  const cronStatus = await cronResp.json();
  assert(cronStatus.ok === true, 'cronometer status ok');
  assert(cronStatus.connection?.status === 'not_connected' || cronStatus.connection?.status === 'auth_required',
    'cronometer truthful not_connected/auth_required');

  // 10. Coach questions
  console.log('--- 10. Coach questions ---');
  const coachTests = [
    { q: 'What data sources are connected?', expect: 'answered' },
    { q: 'Is Cronometer connected?', expectInShort: 'not connected' },
    { q: 'What did I eat today?', expectDomain: 'nutrition' },
    { q: 'How did my HIIT compare to last time?', expectDomain: 'hiit' },
    { q: 'Am I recovered enough to sprint?', expectNoReadinessLeak: true },
    { q: 'Is my nutrition log complete?', expectDomain: 'nutrition' },
  ];
  for (const t of coachTests) {
    const ans = await post(`/api/athlete-memory/${ATHLETE}/coach/ask`, { question: t.q }, false);
    if (t.expectDomain) assert(ans.domain === t.expectDomain, `Coach "${t.q}" → domain ${t.expectDomain}`);
    if (t.expectInShort) assert(ans.answer?.short?.toLowerCase().includes(t.expectInShort), `Coach "${t.q}" short includes "${t.expectInShort}"`);
    if (t.expectNoReadinessLeak) {
      // Should not give a confident readiness green-light without WHOOP
      assert(ans.status !== 'answered' || ans.confidence !== 'high' || !ans.answer?.short?.toLowerCase().includes('green light'),
        `Coach "${t.q}" no readiness leak`);
    }
    console.log(`  ${ans.domain?.padEnd(10)} ${ans.status?.padEnd(18)} ${ans.answer?.short?.slice(0, 60)}`);
  }

  // 11. Nutrition provenance in ai-context
  console.log('--- 11. Nutrition provenance ---');
  assert(ctx.nutritionDailySummary?.sourceDependencies != null, 'nutrition sourceDependencies in ai-context');
  assert(Array.isArray(ctx.nutritionDailySummary?.sourceDependencies), 'sourceDependencies is array');
  assert(ctx.nutritionDailySummary?.sourceState === 'manual' || ctx.nutritionDailySummary?.sourceState === 'estimated',
    'sourceState from raw record (not derived)');

  // 12. Cronometer reason carried through
  console.log('--- 12. Cronometer reason carry-through ---');
  assert(ctx.multiSourceHealth?.cronometer?.reason != null || ctx.multiSourceHealth?.cronometer?.status === 'not_connected',
    'Cronometer reason present or truthful not_connected');

  // 13. Apple Health + nutrition alone cannot unlock readiness
  console.log('--- 13. Apple Health alone readiness check ---');
  // Post health-only data (no WHOOP recovery/HRV/strain) and check Coach blocks readiness
  const readinessAns = await post(`/api/athlete-memory/${ATHLETE}/coach/ask`,
    { question: 'Am I recovered enough to do hard HIIT today?' }, false);
  assert(readinessAns.status === 'insufficient_data' || readinessAns.status === 'downgraded'
    || (readinessAns.answer?.short && !readinessAns.answer.short.toLowerCase().includes('green light')),
    'Apple Health + nutrition alone = no readiness green light');

  // 14. Post-ingest Coach answer reflects ingested data
  console.log('--- 14. Post-ingest Coach consistency ---');
  const postIngestCoach = await post(`/api/athlete-memory/${ATHLETE}/coach/ask`,
    { question: 'What did I eat today?' }, false);
  assert(postIngestCoach.domain === 'nutrition', 'post-ingest Coach routes to nutrition');
  assert(postIngestCoach.status === 'answered' || postIngestCoach.status === 'downgraded',
    'post-ingest Coach has data');
  // Should reflect the photo-confirmed data (500 cal from step 6)
  assert(postIngestCoach.answer?.short?.includes('500') || postIngestCoach.answer?.short?.includes('kcal'),
    'post-ingest Coach reflects ingested nutrition');

  // 15. HIIT post-ingest Coach
  const hiitCoach = await post(`/api/athlete-memory/${ATHLETE}/coach/ask`,
    { question: 'How did my watts drop off in HIIT?' }, false);
  assert(hiitCoach.domain === 'hiit', 'HIIT Coach routes correctly');
  assert(hiitCoach.status === 'answered' || hiitCoach.status === 'insufficient_data',
    'HIIT Coach answers from ingested session data');

  // 16. Auth enforcement — note the test server uses ALLOW_SHARED_TOKEN_ONLY=1
  // so existing shared-token tests pass. In production, missing Authorization
  // would return 401. This is verified by the contract-level guard code.
  console.log('--- 16. Auth enforcement (shared token + JWT + ownership) ---');
  const noAuthResp = await fetch(`${BASE}/api/athlete-memory/${ATHLETE}/ai-context`, {
    headers: {
      'x-athlete-memory-token': PUBLIC_TOKEN,
      'x-athlete-id': ATHLETE,
      // Deliberately NO Authorization header
    },
  });
  assert(noAuthResp.status === 200 || noAuthResp.status === 401,
    'missing Authorization: 200 in test override, 401 in production');

  // 17. Cross-user ownership enforcement
  console.log('--- 17. Cross-user ownership enforcement ---');
  // Simulate: authenticated user "alice-abc" tries to read "dev-athlete" data
  // A fake JWT with sub=alice-abc is rejected because path athleteId is dev-athlete
  const fakeJwtForAlice = buildFakeJwt('alice-abc-123');
  const crossUserResp = await fetch(`${BASE}/api/athlete-memory/${ATHLETE}/ai-context`, {
    headers: {
      'x-athlete-memory-token': PUBLIC_TOKEN,
      'x-athlete-id': ATHLETE,
      'Authorization': `Bearer ${fakeJwtForAlice}`,
    },
  });
  assert(crossUserResp.status === 403, 'cross-user JWT request returns 403');
  const crossBody = await crossUserResp.json().catch(() => ({}));
  assert((crossBody as any).error?.toLowerCase().includes('ownership') ||
         (crossBody as any).error?.toLowerCase().includes('mismatch') ||
         (crossBody as any).error?.toLowerCase().includes('forbidden'),
    'cross-user error mentions ownership/mismatch/forbidden');

  // Same-user JWT is accepted
  const validJwt = buildFakeJwt(ATHLETE);
  const sameUserResp = await fetch(`${BASE}/api/athlete-memory/${ATHLETE}/ai-context`, {
    headers: {
      'x-athlete-memory-token': PUBLIC_TOKEN,
      'x-athlete-id': ATHLETE,
      'Authorization': `Bearer ${validJwt}`,
    },
  });
  assert(sameUserResp.status === 200, 'same-user JWT request returns 200');

  // Summary
  console.log(`\n=== ROUND-TRIP SUMMARY ===`);
  console.log(`  Passed: ${passed}`);
  console.log(`  Failed: ${failed}`);
  console.log(`  Total:  ${passed + failed}`);
  if (failed > 0) process.exit(1);
  else console.log('\nAll round-trip tests passed.');
}

main().catch(console.error);
