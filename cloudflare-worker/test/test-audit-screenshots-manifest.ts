/**
 * Manifest contract for `npm run audit:screenshots`.
 *
 * Locks the shape produced by scripts/audit-screenshots-helpers.mjs
 * `buildManifest`, which downstream readers (Agent / Claude /
 * Codex audit reviewers) rely on to consume the bundle.
 *
 * Run: cd cloudflare-worker && npx tsx test/test-audit-screenshots-manifest.ts
 */

// @ts-expect-error - .mjs JS module imported into TS test
import { AUDIT_SCREENS, buildManifest, parseArgs } from '../../scripts/audit-screenshots-helpers.mjs';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

// ── AUDIT_SCREENS catalogue ─────────────────────────────────────────

const expectedIds = ['home', 'health', 'manage-sources', 'readiness', 'journal', 'train', 'map', 'settings', 'admin-dev'];
const screenIds = (AUDIT_SCREENS as Array<{ id: string }>).map((s) => s.id);
assert(JSON.stringify(screenIds) === JSON.stringify(expectedIds), `AUDIT_SCREENS has the canonical 9 ids in order (got ${JSON.stringify(screenIds)})`);
for (const screen of AUDIT_SCREENS as Array<{ id: string; label: string; route: string }>) {
  assert(typeof screen.id === 'string' && screen.id.length > 0, `${screen.id} has non-empty id`);
  assert(typeof screen.label === 'string' && screen.label.length > 0, `${screen.id} has non-empty label`);
  assert(typeof screen.route === 'string' && screen.route.length > 0, `${screen.id} has non-empty route hint`);
}

// ── buildManifest happy path ────────────────────────────────────────

const happy = buildManifest({
  platform: 'ios',
  device: { id: 'ABC-123', name: 'iPhone 15 Pro' },
  build: {
    appVersion: '0.1.0',
    iosBuildNumber: '20',
    androidVersionCode: 20,
    iosBundleIdentifier: 'com.lauburu.grapplingmap',
    androidPackage: 'com.lauburu.grapplingmap',
  },
  repo: { branch: 'main', shortHead: '0991468' },
  capturedAt: '2026-05-09T12:00:00.000Z',
  screens: [
    { id: 'home', label: 'Home', route: '(tabs)/index', file: 'home.png', capturedAt: '2026-05-09T12:00:01.000Z' },
    { id: 'health', label: 'Health', route: '(tabs)/health', file: 'health.png', capturedAt: '2026-05-09T12:00:02.000Z' },
  ],
  skipped: [{ id: 'admin-dev', reason: 'user-skipped' }],
});

assert(happy.schemaVersion === 1, 'happy: schemaVersion === 1');
assert(happy.captureTier === 'v1.5_human_driven_auto_capture', 'happy: captureTier carries v1.5 marker');
assert(happy.platform === 'ios', 'happy: platform preserved');
assert(happy.device?.id === 'ABC-123', 'happy: device id preserved');
assert(happy.build?.iosBuildNumber === '20', 'happy: build.iosBuildNumber preserved');
assert(happy.build?.androidVersionCode === 20, 'happy: build.androidVersionCode preserved');
assert(happy.repo?.branch === 'main', 'happy: repo.branch preserved');
assert(happy.repo?.shortHead === '0991468', 'happy: repo.shortHead preserved');
assert(happy.capturedAt === '2026-05-09T12:00:00.000Z', 'happy: capturedAt preserved');
assert(Array.isArray(happy.screens) && happy.screens.length === 2, 'happy: 2 screens captured');
assert(happy.screens[0].id === 'home', 'happy: first screen id home');
assert(Array.isArray(happy.skipped) && happy.skipped.length === 1, 'happy: 1 skipped entry');
assert(happy.skipped[0].id === 'admin-dev' && happy.skipped[0].reason === 'user-skipped', 'happy: skipped entry shape');

// ── platform sanitisation ───────────────────────────────────────────

const unknownPlatform = buildManifest({ platform: 'web' as any });
assert(unknownPlatform.platform === 'unknown', 'unknown platform falls back to "unknown"');

const androidOnly = buildManifest({ platform: 'android', device: { id: 'emulator-5554', name: 'emulator-5554' } });
assert(androidOnly.platform === 'android', 'android platform preserved');
assert(androidOnly.device?.id === 'emulator-5554', 'android device id preserved');

// ── junk inputs are sanitised, not crash ───────────────────────────

const junk = buildManifest({
  platform: 'ios',
  device: 'not-an-object' as any,
  build: 'not-an-object' as any,
  repo: null as any,
  capturedAt: 12345 as any,
  screens: 'not-an-array' as any,
  skipped: { not: 'array' } as any,
});
assert(junk.device === null, 'junk device coerces to null');
assert(junk.build === null, 'junk build coerces to null');
assert(junk.repo.branch === 'unknown' && junk.repo.shortHead === 'unknown', 'junk repo coerces to unknown');
assert(typeof junk.capturedAt === 'string' && junk.capturedAt.length > 0, 'junk capturedAt falls back to a string');
assert(Array.isArray(junk.screens) && junk.screens.length === 0, 'junk screens coerces to []');
assert(Array.isArray(junk.skipped) && junk.skipped.length === 0, 'junk skipped coerces to []');

// ── partial screen entries dropped, not crash ──────────────────────

const partial = buildManifest({
  platform: 'ios',
  screens: [
    { id: 'home', label: 'Home', route: '(tabs)/index', file: 'home.png', capturedAt: '2026-05-09T12:00:00.000Z' },
    { id: 'broken' } as any, // missing fields
    { id: 'health', label: 'Health', route: '(tabs)/health', file: 'health.png', capturedAt: '2026-05-09T12:00:01.000Z' },
  ],
});
assert(partial.screens.length === 2, 'partial: bad entry dropped, good entries kept');
assert(partial.screens.map((s: any) => s.id).join(',') === 'home,health', 'partial: order preserved');

// ── parseArgs ──────────────────────────────────────────────────────

const a1 = parseArgs([]);
assert(a1.platform === null && a1.skip === '' && a1.nonInteractive === false && a1.device === null, 'parseArgs default empty');

const a2 = parseArgs(['--platform', 'ios', '--skip', 'map,admin-dev', '--non-interactive']);
assert(a2.platform === 'ios', 'parseArgs --platform ios');
assert(a2.skip === 'map,admin-dev', 'parseArgs --skip preserved');
assert(a2.nonInteractive === true, 'parseArgs --non-interactive true');

const a3 = parseArgs(['--platform', 'web']);
assert(a3.platform === null, 'parseArgs rejects unknown platform');

const a4 = parseArgs(['--device', 'emulator-5554']);
assert(a4.device === 'emulator-5554', 'parseArgs --device preserved');

console.log('audit-screenshots manifest contract test passed.');
