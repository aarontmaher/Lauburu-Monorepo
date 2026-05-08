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
import {
  AUDIT_SCREENS,
  buildManifest,
  buildIphoneMirroringManifest,
  indexPrefix,
  isFilenameSuspicious,
  labelToScreenSlug,
  parseArgs,
  parseIphoneMirroringArgs,
} from '../../scripts/audit-screenshots-helpers.mjs';

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

// ── iPhone Mirroring manifest ───────────────────────────────────────

const mirror = buildIphoneMirroringManifest({
  iosBuildNumber: '20',
  appVersion: '0.1.0',
  device: 'iPhone 15 Pro',
  iosVersion: '18.2',
  macosVersion: '15.2',
  capturedAt: '2026-05-09T12:00:00.000Z',
  screens: [
    { filename: '01-admin-dev-top.png', screen: 'admin-dev-top', notes: '' },
    { filename: '02-admin-dev-mcp.png', screen: 'admin-dev-mcp', notes: 'fresh writeback visible' },
  ],
  notes: 'v20 health-connect retest cycle 1',
});
assert(mirror.schemaVersion === 1, 'mirror: schemaVersion === 1');
assert(mirror.captureMethod === 'iphone_mirroring', 'mirror: captureMethod marker');
assert(mirror.iosBuildNumber === '20', 'mirror: iosBuildNumber preserved');
assert(mirror.device === 'iPhone 15 Pro', 'mirror: device preserved');
assert(mirror.iosVersion === '18.2', 'mirror: iosVersion preserved');
assert(mirror.macosVersion === '15.2', 'mirror: macosVersion preserved');
assert(mirror.capturedAt === '2026-05-09T12:00:00.000Z', 'mirror: capturedAt preserved');
assert(Array.isArray(mirror.screens) && mirror.screens.length === 2, 'mirror: 2 screens');
assert(mirror.screens[0].filename === '01-admin-dev-top.png' && mirror.screens[0].screen === 'admin-dev-top', 'mirror: first screen shape');
assert(mirror.screens[1].notes === 'fresh writeback visible', 'mirror: second screen notes preserved');
assert(mirror.notes === 'v20 health-connect retest cycle 1', 'mirror: top-level notes preserved');

const mirrorJunk = buildIphoneMirroringManifest({
  iosBuildNumber: 12345 as any,
  device: { not: 'string' } as any,
  screens: [
    { filename: '01.png' } as any,                             // missing screen
    { screen: 'no-filename' } as any,                          // missing filename
    { filename: '03.png', screen: 'health' } as any,           // good (notes default '')
    { filename: '04.png', screen: 'home', notes: 99 } as any,  // notes coerced to ''
  ],
  notes: 12345 as any,
});
assert(mirrorJunk.iosBuildNumber === null, 'mirror junk: numeric iosBuildNumber → null');
assert(mirrorJunk.device === null, 'mirror junk: object device → null');
assert(mirrorJunk.notes === '', 'mirror junk: numeric notes → ""');
assert(mirrorJunk.screens.length === 2, 'mirror junk: keeps 2 valid screens');
assert(mirrorJunk.screens[0].filename === '03.png' && mirrorJunk.screens[0].notes === '', 'mirror junk: missing notes coerces to ""');
assert(mirrorJunk.screens[1].notes === '', 'mirror junk: numeric notes coerces to ""');

const mirrorEmpty = buildIphoneMirroringManifest({});
assert(mirrorEmpty.captureMethod === 'iphone_mirroring', 'mirror empty: captureMethod still iphone_mirroring');
assert(mirrorEmpty.screens.length === 0, 'mirror empty: screens [] default');
assert(typeof mirrorEmpty.capturedAt === 'string' && mirrorEmpty.capturedAt.length > 0, 'mirror empty: capturedAt fallback string');

// ── isFilenameSuspicious ────────────────────────────────────────────

assert(isFilenameSuspicious('Screenshot 2026-05-09 token.png'), 'token-shaped filename refused');
assert(isFilenameSuspicious('Screenshot ghp_abcdefghij.png'), 'ghp_ filename refused');
assert(isFilenameSuspicious('AKIAIOSFODNN7EXAMPLE.png'), 'AKIA filename refused');
assert(isFilenameSuspicious('apikey-screen.png'), 'apikey filename refused');
assert(isFilenameSuspicious('jwt-leaked.png'), 'jwt filename refused');
assert(!isFilenameSuspicious('Screenshot 2026-05-09 admin-dev-top.png'), 'admin-dev filename allowed');
assert(!isFilenameSuspicious('01-health-sources.png'), 'health-sources filename allowed');
assert(!isFilenameSuspicious(''), 'empty filename does not throw');

// ── labelToScreenSlug ───────────────────────────────────────────────

assert(labelToScreenSlug('Admin/Dev top') === 'admin-dev-top', 'slash slugifies');
assert(labelToScreenSlug('Admin Dev — MCP') === 'admin-dev-mcp', 'em-dash slugifies');
assert(labelToScreenSlug('   ') === 'screen', 'whitespace falls back to "screen"');
assert(labelToScreenSlug(undefined as any) === 'screen', 'undefined falls back to "screen"');

const longLabel = 'a'.repeat(200);
assert(labelToScreenSlug(longLabel).length <= 60, 'slug capped at 60 chars');

// ── indexPrefix ─────────────────────────────────────────────────────

assert(indexPrefix(0) === '01', 'indexPrefix 0 → "01"');
assert(indexPrefix(8) === '09', 'indexPrefix 8 → "09"');
assert(indexPrefix(9) === '10', 'indexPrefix 9 → "10"');

// ── parseIphoneMirroringArgs ────────────────────────────────────────

const m1 = parseIphoneMirroringArgs([]);
assert(m1.windowMinutes === 10, 'parseIphoneMirroringArgs default windowMinutes 10');
assert(m1.zip === false && m1.nonInteractive === false && m1.dryRun === false, 'parseIphoneMirroringArgs default booleans false');

const m2 = parseIphoneMirroringArgs([
  '--watch-dir', '/tmp/x',
  '--window', '60',
  '--ios-build', '20',
  '--app-version', '0.1.0',
  '--device', 'iPhone 15 Pro',
  '--ios-version', '18.2',
  '--macos-version', '15.2',
  '--labels', 'a,b,c',
  '--notes', 'cycle 1',
  '--zip',
  '--non-interactive',
  '--dry-run',
]);
assert(m2.watchDir === '/tmp/x', 'parseIphoneMirroringArgs --watch-dir');
assert(m2.windowMinutes === 60, 'parseIphoneMirroringArgs --window 60');
assert(m2.iosBuild === '20', 'parseIphoneMirroringArgs --ios-build');
assert(m2.appVersion === '0.1.0', 'parseIphoneMirroringArgs --app-version');
assert(m2.device === 'iPhone 15 Pro', 'parseIphoneMirroringArgs --device');
assert(m2.iosVersion === '18.2', 'parseIphoneMirroringArgs --ios-version');
assert(m2.macosVersion === '15.2', 'parseIphoneMirroringArgs --macos-version');
assert(m2.labels === 'a,b,c', 'parseIphoneMirroringArgs --labels');
assert(m2.notes === 'cycle 1', 'parseIphoneMirroringArgs --notes');
assert(m2.zip === true, 'parseIphoneMirroringArgs --zip');
assert(m2.nonInteractive === true, 'parseIphoneMirroringArgs --non-interactive');
assert(m2.dryRun === true, 'parseIphoneMirroringArgs --dry-run');

const m3 = parseIphoneMirroringArgs(['--window', 'not-a-number']);
assert(m3.windowMinutes === 10, 'parseIphoneMirroringArgs invalid --window keeps default');

console.log('audit-screenshots manifest contract test passed.');
