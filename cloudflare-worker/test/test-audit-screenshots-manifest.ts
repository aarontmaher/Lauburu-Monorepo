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
  buildMaestroManifest,
  buildScrcpyAndroidManifest,
  buildV21HealthConnectAgentQaScaffold,
  validateV21HealthConnectCapture,
  buildAgentBundleManifest,
  indexPrefix,
  isFilenameSuspicious,
  labelToScreenSlug,
  parseArgs,
  parseIphoneMirroringArgs,
  parseMaestroArgs,
  parseScrcpyAndroidArgs,
  parseAgentBundleArgs,
  SCRCPY_ANDROID_LABEL_PRESETS,
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

// ── Maestro manifest ────────────────────────────────────────────────

const maestro = buildMaestroManifest({
  platform: 'android',
  device: { id: 'emulator-5554', name: 'Pixel 8a' },
  build: { appVersion: '0.1.0', androidVersionCode: 20, iosBuildNumber: '20', iosBundleIdentifier: null, androidPackage: 'com.lauburu.grapplingmap' },
  repo: { branch: 'main', shortHead: '8ba25ae' },
  capturedAt: '2026-05-09T12:00:00.000Z',
  flows: ['00-launch', '01-home', '02-health'],
  captured: [
    { flow: '00-launch', file: '00-launch-1.png', capturedAt: '2026-05-09T12:00:01.000Z' },
    { flow: '01-home', file: '01-home-1.png', capturedAt: '2026-05-09T12:00:02.000Z' },
  ],
  failed: [{ flow: '02-health', reason: 'maestro-exit-1' }],
});
assert(maestro.schemaVersion === 1, 'maestro: schemaVersion === 1');
assert(maestro.captureMethod === 'maestro', 'maestro: captureMethod marker');
assert(maestro.captureTier === 'v3_maestro_full_auto', 'maestro: captureTier v3 marker');
assert(maestro.flows.length === 3 && maestro.flows[0] === '00-launch', 'maestro: flows preserved');
assert(maestro.captured.length === 2 && maestro.captured[0].flow === '00-launch', 'maestro: captured shape');
assert(maestro.failed.length === 1 && maestro.failed[0].reason === 'maestro-exit-1', 'maestro: failed shape');

const maestroJunk = buildMaestroManifest({
  platform: 'web' as any,
  flows: ['ok', 12345 as any, '', 'also-ok'],
  captured: [
    { flow: 'ok' } as any,                                                     // missing fields
    { flow: 'ok', file: 'ok-1.png', capturedAt: '2026-05-09T12:00:00.000Z' },
  ],
  failed: [{ flow: 'oops' } as any, { flow: 'oops', reason: 'x' }],
});
assert(maestroJunk.platform === 'unknown', 'maestro junk: platform falls back to unknown');
assert(maestroJunk.flows.length === 2, 'maestro junk: empty/non-string flows dropped');
assert(maestroJunk.captured.length === 1, 'maestro junk: malformed captured dropped');
assert(maestroJunk.failed.length === 1, 'maestro junk: malformed failed dropped');

const maestroArgs1 = parseMaestroArgs([]);
assert(maestroArgs1.flow === null && maestroArgs1.platform === null && maestroArgs1.dryRun === false && maestroArgs1.keepTmp === false, 'parseMaestroArgs default empty');

const maestroArgs2 = parseMaestroArgs(['--flow', '02-health', '--platform', 'ios', '--device', 'sim-1', '--dry-run', '--keep-tmp']);
assert(maestroArgs2.flow === '02-health', 'parseMaestroArgs --flow');
assert(maestroArgs2.platform === 'ios', 'parseMaestroArgs --platform ios');
assert(maestroArgs2.device === 'sim-1', 'parseMaestroArgs --device');
assert(maestroArgs2.dryRun === true, 'parseMaestroArgs --dry-run');
assert(maestroArgs2.keepTmp === true, 'parseMaestroArgs --keep-tmp');

assert(parseMaestroArgs(['--platform', 'web']).platform === null, 'parseMaestroArgs rejects unknown platform');

// ── scrcpy Android manifest ─────────────────────────────────────────

const scrcpy = buildScrcpyAndroidManifest({
  auditGate: 'release_gate',
  verificationStatus: 'captured_only',
  androidVersionCode: 20,
  appVersion: '0.1.0',
  device: 'Pixel 8a',
  androidVersion: '15',
  macosVersion: '15.2',
  capturedAt: '2026-05-09T12:00:00.000Z',
  screens: [
    { filename: '01-home.png', screen: 'home', notes: '' },
    { filename: '02-health.png', screen: 'health', notes: 'manage sources sheet open' },
  ],
  notes: 'v20 retest',
});
assert(scrcpy.schemaVersion === 1, 'scrcpy: schemaVersion === 1');
assert(scrcpy.captureMethod === 'scrcpy_android', 'scrcpy: captureMethod marker');
assert(scrcpy.auditGate === 'release_gate', 'scrcpy: auditGate preserved');
assert(scrcpy.verificationStatus === 'captured_only', 'scrcpy: verificationStatus preserved');
assert(scrcpy.androidVersionCode === 20, 'scrcpy: androidVersionCode preserved');
assert(scrcpy.device === 'Pixel 8a', 'scrcpy: device preserved');
assert(scrcpy.androidVersion === '15', 'scrcpy: androidVersion preserved');
assert(scrcpy.screens.length === 2, 'scrcpy: 2 screens');
assert(scrcpy.notes === 'v20 retest', 'scrcpy: notes preserved');

const scrcpyJunk = buildScrcpyAndroidManifest({
  androidVersionCode: 'not-a-number' as any,
  device: { not: 'string' } as any,
  screens: [
    { filename: '01.png' } as any,
    { filename: '02.png', screen: 'home' } as any,
  ],
});
assert(scrcpyJunk.androidVersionCode === null, 'scrcpy junk: non-int androidVersionCode → null');
assert(scrcpyJunk.device === null, 'scrcpy junk: object device → null');
assert(scrcpyJunk.screens.length === 1, 'scrcpy junk: malformed screens dropped');

const s1 = parseScrcpyAndroidArgs([]);
assert(s1.windowMinutes === 10, 'parseScrcpyAndroidArgs default windowMinutes 10');
assert(s1.androidVersionCode === null, 'parseScrcpyAndroidArgs default androidVersionCode null');

const s2 = parseScrcpyAndroidArgs([
  '--watch-dir', '/tmp/x',
  '--window', '30',
  '--label-preset', 'v21-health-connect',
  '--audit-gate', 'release_gate',
  '--verification-status', 'captured_only',
  '--android-version-code', '20',
  '--app-version', '0.1.0',
  '--device', 'Pixel 8a',
  '--android-version', '15',
  '--macos-version', '15.2',
  '--labels', 'a,b',
  '--notes', 'cycle 1',
  '--zip',
  '--non-interactive',
  '--dry-run',
]);
assert(s2.watchDir === '/tmp/x', 'parseScrcpyAndroidArgs --watch-dir');
assert(s2.windowMinutes === 30, 'parseScrcpyAndroidArgs --window');
assert(s2.labelPreset === 'v21-health-connect', 'parseScrcpyAndroidArgs --label-preset');
assert(s2.auditGate === 'release_gate', 'parseScrcpyAndroidArgs --audit-gate');
assert(s2.verificationStatus === 'captured_only', 'parseScrcpyAndroidArgs --verification-status');
assert(s2.androidVersionCode === 20, 'parseScrcpyAndroidArgs --android-version-code');
assert(s2.appVersion === '0.1.0', 'parseScrcpyAndroidArgs --app-version');
assert(s2.device === 'Pixel 8a', 'parseScrcpyAndroidArgs --device');
assert(s2.zip === true, 'parseScrcpyAndroidArgs --zip');
assert(s2.nonInteractive === true, 'parseScrcpyAndroidArgs --non-interactive');
assert(s2.dryRun === true, 'parseScrcpyAndroidArgs --dry-run');

assert(parseScrcpyAndroidArgs(['--android-version-code', 'oops']).androidVersionCode === null, 'parseScrcpyAndroidArgs rejects non-int');

assert(Array.isArray(SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect']), 'scrcpy preset: v21 health connect exists');
assert(SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect'].length === 10, 'scrcpy preset: v21 health connect has 10 labels');
assert(SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect'][2] === 'permissions-dialog', 'scrcpy preset: step 03 locks v20 failure point');
assert(SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect'][8] === 'build-state-separation', 'scrcpy preset: build-state evidence included');

const v21Manifest = buildScrcpyAndroidManifest({
  auditGate: 'release_gate',
  verificationStatus: 'captured_only',
  androidVersionCode: 21,
  appVersion: '0.1.0',
  device: 'Pixel 8a',
  androidVersion: '15',
  capturedAt: '2026-05-09T12:00:00.000Z',
  screens: SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect'].map((screen: string, idx: number) => ({
    filename: `${indexPrefix(idx)}-${screen}.png`,
    screen,
    notes: '',
  })),
});

const v21Checklist = validateV21HealthConnectCapture(v21Manifest);
assert(v21Checklist.ok === true, 'v21 checklist: complete captured-only v21 bundle is ok');
assert(v21Checklist.expectedCount === 10 && v21Checklist.screenshotCount === 10, 'v21 checklist: counts match preset');
assert(v21Checklist.ordered === true, 'v21 checklist: preset order preserved');
assert(v21Checklist.missingScreens.length === 0 && v21Checklist.unexpectedScreens.length === 0, 'v21 checklist: no missing or unexpected screens');

const v21IncompleteChecklist = validateV21HealthConnectCapture(buildScrcpyAndroidManifest({
  auditGate: 'release_gate',
  verificationStatus: 'pass',
  androidVersionCode: 20,
  screens: [
    { filename: '01-home.png', screen: 'home', notes: '' },
    { filename: '02-mystery.png', screen: 'mystery', notes: '' },
  ],
}));
assert(v21IncompleteChecklist.ok === false, 'v21 checklist: incomplete/non-captured-only bundle is not ok');
assert(v21IncompleteChecklist.verificationStatus === 'pass', 'v21 checklist: exposes unsafe verificationStatus mismatch');
assert(v21IncompleteChecklist.androidVersionCode === 20, 'v21 checklist: exposes versionCode mismatch');
assert(v21IncompleteChecklist.missingScreens.includes('permissions-dialog'), 'v21 checklist: reports missing expected screen');
assert(v21IncompleteChecklist.unexpectedScreens.includes('mystery'), 'v21 checklist: reports unexpected screen');

const v21Scaffold = buildV21HealthConnectAgentQaScaffold({
  manifest: v21Manifest,
  bundlePath: 'artifacts/app-audit/android-scrcpy/2026-05-09T12-00-00-000Z',
});
assert(v21Scaffold.status === 'partial', 'v21 scaffold: captured-only status is partial');
assert(v21Scaffold.gate === 'release_gate' && v21Scaffold.platform === 'android', 'v21 scaffold: release gate android');
assert(v21Scaffold.installedBuild.androidVersionCode === 21, 'v21 scaffold: android versionCode 21');
assert(v21Scaffold.releaseGate.newAndroidBuildAllowed === false, 'v21 scaffold: android release remains blocked');
assert(v21Scaffold.releaseGate.newTestFlightAllowed === false, 'v21 scaffold: iOS release remains blocked');
assert(v21Scaffold.results.androidHealthConnect === 'partial', 'v21 scaffold: HC result partial until Agent verdict');
assert(v21Scaffold.evidence.screenshotRefs.length === 10, 'v21 scaffold: carries 10 screenshot refs');
assert(v21Scaffold.evidence.screenshotRefs[2].endsWith('/03-permissions-dialog.png'), 'v21 scaffold: step 03 screenshot ref preserved');
assert(v21Scaffold.evidence.captureChecklist.ok === true, 'v21 scaffold: embeds capture checklist');
assert(v21Scaffold.evidence.notes.includes('not a pass verdict'), 'v21 scaffold: notes reject pass claim');

// ── Agent-bundle manifest ───────────────────────────────────────────

const bundle = buildAgentBundleManifest({
  generatedAt: '2026-05-09T12:00:00.000Z',
  repo: { branch: 'main', shortHead: '14bbf62' },
  build: { appVersion: '0.1.0', androidVersionCode: 20, iosBuildNumber: '20', iosBundleIdentifier: 'com.lauburu.grapplingmap', androidPackage: 'com.lauburu.grapplingmap' },
  mcp: {
    generatedAt: '2026-05-09T11:59:30.000Z',
    ageMs: 30_000,
    staleReason: 'fresh',
    priority: 'Health connectivity Phase 1 mobile truth labels',
    nextAction: 'Agent audit Health Manage Sources on Android and iPhone.',
  },
  sources: [
    { tier: 'simulator', path: 'artifacts/agent-bundles/foo/simulator', manifest: 'manifest.json', capturedAt: '2026-05-09T11:55:00.000Z', screenCount: 9 },
    { tier: 'maestro', path: 'artifacts/agent-bundles/foo/maestro', manifest: 'manifest.json', capturedAt: '2026-05-09T11:58:00.000Z', screenCount: 12 },
  ],
  notes: 'overnight bundle',
});
assert(bundle.schemaVersion === 1, 'agent-bundle: schemaVersion === 1');
assert(bundle.captureMethod === 'agent_bundle', 'agent-bundle: captureMethod marker');
assert(bundle.repo.shortHead === '14bbf62', 'agent-bundle: repo.shortHead preserved');
assert(bundle.mcp.staleReason === 'fresh', 'agent-bundle: mcp.staleReason preserved');
assert(bundle.mcp.ageMs === 30_000, 'agent-bundle: mcp.ageMs preserved');
assert(bundle.sources.length === 2, 'agent-bundle: 2 sources');
assert(bundle.sources[0].tier === 'simulator', 'agent-bundle: source order preserved');
assert(bundle.sources[1].screenCount === 12, 'agent-bundle: screenCount preserved');
assert(bundle.notes === 'overnight bundle', 'agent-bundle: notes preserved');

const bundleJunk = buildAgentBundleManifest({
  mcp: { ageMs: 'oops' as any, priority: 12345 as any },
  sources: [
    { tier: 'foo' } as any,                                                        // missing path
    { path: 'no-tier' } as any,                                                    // missing tier
    { tier: 'maestro', path: 'ok', screenCount: 'bad' as any },                    // bad screenCount → 0
  ],
});
assert(bundleJunk.mcp.ageMs === null, 'agent-bundle junk: bad ageMs → null');
assert(bundleJunk.mcp.priority === null, 'agent-bundle junk: numeric priority → null');
assert(bundleJunk.sources.length === 1, 'agent-bundle junk: malformed sources dropped');
assert(bundleJunk.sources[0].screenCount === 0, 'agent-bundle junk: bad screenCount → 0');

const ag1 = parseAgentBundleArgs([]);
assert(ag1.include === null && ag1.exclude === null && ag1.mcpUrl === null && ag1.dryRun === false, 'parseAgentBundleArgs default empty');

const ag2 = parseAgentBundleArgs(['--include', 'simulator,maestro', '--exclude', 'scrcpy', '--mcp-url', 'https://x', '--dry-run']);
assert(ag2.include === 'simulator,maestro', 'parseAgentBundleArgs --include');
assert(ag2.exclude === 'scrcpy', 'parseAgentBundleArgs --exclude');
assert(ag2.mcpUrl === 'https://x', 'parseAgentBundleArgs --mcp-url');
assert(ag2.dryRun === true, 'parseAgentBundleArgs --dry-run');

console.log('audit-screenshots manifest contract test passed.');
