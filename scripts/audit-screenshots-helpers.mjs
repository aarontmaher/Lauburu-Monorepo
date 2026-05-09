/**
 * Pure helpers for audit-screenshots.mjs. Kept separate so they
 * can be imported by a test without spawning subprocesses.
 *
 * AUDIT_SCREENS is the canonical list of routes the audit
 * captures, in order. Add a screen by appending an entry — the
 * downstream manifest schema doesn't need to change.
 *
 * buildManifest produces the JSON the script writes to
 * artifacts/app-audit/<ts>/manifest.json. Schema is locked in
 * cloudflare-worker/test/test-audit-screenshots-manifest.ts so
 * downstream readers can rely on it.
 */

export const AUDIT_SCREENS = Object.freeze([
  { id: 'home',           label: 'Home',                     route: '(tabs)/index' },
  { id: 'health',         label: 'Health',                   route: '(tabs)/health' },
  { id: 'manage-sources', label: 'Health → Manage Sources',  route: '(tabs)/health · Manage Sources sheet' },
  { id: 'readiness',      label: 'Grappling Readiness',      route: '(tabs)/health · Readiness card' },
  { id: 'journal',        label: 'Journal / Feedback',       route: '(tabs)/feedback' },
  { id: 'train',          label: 'Train',                    route: '(tabs)/train' },
  { id: 'map',            label: 'Map',                      route: '(tabs)/map-3d' },
  { id: 'settings',       label: 'Settings',                 route: '(tabs)/settings' },
  { id: 'admin-dev',      label: 'Admin / Dev',              route: 'admin-dev (admin email required)' },
]);

const MANIFEST_SCHEMA_VERSION = 1;

function isString(v) {
  return typeof v === 'string' && v.length > 0;
}

function sanitizeBuild(build) {
  if (!build || typeof build !== 'object') return null;
  return {
    appVersion: typeof build.appVersion === 'string' ? build.appVersion : null,
    iosBuildNumber: typeof build.iosBuildNumber === 'string' ? build.iosBuildNumber : null,
    androidVersionCode: Number.isInteger(build.androidVersionCode) ? build.androidVersionCode : null,
    iosBundleIdentifier: typeof build.iosBundleIdentifier === 'string' ? build.iosBundleIdentifier : null,
    androidPackage: typeof build.androidPackage === 'string' ? build.androidPackage : null,
  };
}

function sanitizeRepo(repo) {
  if (!repo || typeof repo !== 'object') return { branch: 'unknown', shortHead: 'unknown' };
  return {
    branch: typeof repo.branch === 'string' && repo.branch ? repo.branch : 'unknown',
    shortHead: typeof repo.shortHead === 'string' && repo.shortHead ? repo.shortHead : 'unknown',
  };
}

function sanitizeDevice(device) {
  if (!device || typeof device !== 'object') return null;
  return {
    id: typeof device.id === 'string' ? device.id : null,
    name: typeof device.name === 'string' ? device.name : null,
  };
}

function sanitizeScreens(screens) {
  if (!Array.isArray(screens)) return [];
  return screens
    .map((s) => {
      if (!s || typeof s !== 'object') return null;
      if (!isString(s.id) || !isString(s.label) || !isString(s.route) || !isString(s.file) || !isString(s.capturedAt)) {
        return null;
      }
      return {
        id: s.id,
        label: s.label,
        route: s.route,
        file: s.file,
        capturedAt: s.capturedAt,
      };
    })
    .filter((s) => s !== null);
}

function sanitizeSkipped(skipped) {
  if (!Array.isArray(skipped)) return [];
  return skipped
    .map((s) => (s && typeof s === 'object' && isString(s.id) && isString(s.reason) ? { id: s.id, reason: s.reason } : null))
    .filter((s) => s !== null);
}

export function buildManifest(input) {
  const platform = input?.platform === 'ios' || input?.platform === 'android' ? input.platform : 'unknown';
  const capturedAt = isString(input?.capturedAt) ? input.capturedAt : new Date().toISOString();
  return {
    schemaVersion: MANIFEST_SCHEMA_VERSION,
    captureTier: 'v1.5_human_driven_auto_capture',
    platform,
    device: sanitizeDevice(input?.device),
    build: sanitizeBuild(input?.build),
    repo: sanitizeRepo(input?.repo),
    capturedAt,
    screens: sanitizeScreens(input?.screens),
    skipped: sanitizeSkipped(input?.skipped),
  };
}

/**
 * Filenames the iPhone Mirroring script will refuse to ingest
 * because they suggest a screenshot of secret-shaped content.
 * Aaron is responsible for cropping / blurring before saving;
 * this is a last-line guard against obvious mistakes.
 */
const FILENAME_SECRET_HINTS = [
  /token/i,
  /secret/i,
  /jwt/i,
  /\bsk[-_]/,
  /\bgh[pousr]_/i,
  /\bapikey/i,
  /\bbearer/i,
  /\bwhsec_/i,
  /\bAKIA/,
  /password/i,
];

export function isFilenameSuspicious(filename) {
  if (typeof filename !== 'string' || filename.length === 0) return false;
  return FILENAME_SECRET_HINTS.some((p) => p.test(filename));
}

const IPHONE_MIRRORING_SCHEMA_VERSION = 1;

function sanitizeMirroringScreens(screens) {
  if (!Array.isArray(screens)) return [];
  return screens
    .map((s) => {
      if (!s || typeof s !== 'object') return null;
      if (!isString(s.filename) || !isString(s.screen)) return null;
      const notes = isString(s.notes) ? s.notes : '';
      return { filename: s.filename, screen: s.screen, notes };
    })
    .filter((s) => s !== null);
}

/**
 * Build the manifest for an iPhone-Mirroring capture session.
 * Schema mirrors the prompt template precisely so downstream
 * Agent / Claude / Codex readers can rely on it.
 */
export function buildIphoneMirroringManifest(input) {
  const capturedAt = isString(input?.capturedAt) ? input.capturedAt : new Date().toISOString();
  return {
    schemaVersion: IPHONE_MIRRORING_SCHEMA_VERSION,
    captureMethod: 'iphone_mirroring',
    iosBuildNumber: isString(input?.iosBuildNumber) ? input.iosBuildNumber : null,
    appVersion: isString(input?.appVersion) ? input.appVersion : null,
    device: isString(input?.device) ? input.device : null,
    iosVersion: isString(input?.iosVersion) ? input.iosVersion : null,
    macosVersion: isString(input?.macosVersion) ? input.macosVersion : null,
    capturedAt,
    screens: sanitizeMirroringScreens(input?.screens),
    notes: isString(input?.notes) ? input.notes : '',
  };
}

/**
 * Slug a label into a filesystem-safe screen id used for the
 * manifest's `screen` field and the renamed file's middle slug
 * (e.g. "Admin/Dev top — MCP" → "admin-dev-top-mcp").
 */
export function labelToScreenSlug(label) {
  if (typeof label !== 'string') return 'screen';
  const slug = label
    .toLowerCase()
    .replace(/[/\\&]+/g, '-')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
  return slug.length > 0 ? slug : 'screen';
}

/** Two-digit zero-padded prefix for Finder/Agent ordering. */
export function indexPrefix(idx) {
  return String(idx + 1).padStart(2, '0');
}

/**
 * Build the manifest for a Maestro YAML-flow audit run. Mirrors the
 * iPhone-Mirroring shape but adds `flows` (the YAML files that ran)
 * and `failed` (per-flow failure list). Schema locked in
 * cloudflare-worker/test/test-audit-screenshots-manifest.ts.
 */
export function buildMaestroManifest(input) {
  const platform = input?.platform === 'ios' || input?.platform === 'android' ? input.platform : 'unknown';
  const capturedAt = isString(input?.capturedAt) ? input.capturedAt : new Date().toISOString();
  const auditGate = isString(input?.auditGate) ? input.auditGate : 'simulator_audit';
  return {
    schemaVersion: 1,
    captureMethod: 'maestro',
    captureTier: 'v3_maestro_full_auto',
    auditGate,
    verificationStatus: 'captured_only',
    installedDeviceGate: {
      canClearInstalledDeviceGate: false,
      reason: 'Maestro simulator/emulator screenshots are public-safe UI evidence only; installed-device gates require separate real-device Agent QA.',
    },
    platform,
    device: sanitizeDevice(input?.device),
    build: sanitizeBuild(input?.build),
    repo: sanitizeRepo(input?.repo),
    capturedAt,
    flows: Array.isArray(input?.flows) ? input.flows.filter((f) => isString(f)) : [],
    captured: Array.isArray(input?.captured)
      ? input.captured
          .map((c) => (c && typeof c === 'object' && isString(c.flow) && isString(c.file) && isString(c.capturedAt)
            ? { flow: c.flow, file: c.file, capturedAt: c.capturedAt } : null))
          .filter((c) => c !== null)
      : [],
    failed: Array.isArray(input?.failed)
      ? input.failed
          .map((f) => (f && typeof f === 'object' && isString(f.flow) && isString(f.reason)
            ? { flow: f.flow, reason: f.reason } : null))
          .filter((f) => f !== null)
      : [],
  };
}

export function buildMaestroAgentAuditManifest(input) {
  const manifest = input?.manifest && typeof input.manifest === 'object' ? input.manifest : {};
  const capturedAt = isString(manifest.capturedAt) ? manifest.capturedAt : new Date().toISOString();
  const bundlePath = isString(input?.bundlePath) ? input.bundlePath.replace(/\/+$/g, '') : '';
  const captured = Array.isArray(manifest.captured) ? manifest.captured : [];
  const screenshotRefs = captured
    .map((screen) => {
      if (!screen || typeof screen !== 'object' || !isString(screen.file)) return null;
      return bundlePath ? `${bundlePath}/${screen.file}` : screen.file;
    })
    .filter((ref) => ref !== null);
  const failed = Array.isArray(manifest.failed)
    ? manifest.failed
        .map((f) => (f && typeof f === 'object' && isString(f.flow) && isString(f.reason)
          ? { flow: f.flow, reason: f.reason }
          : null))
        .filter((f) => f !== null)
    : [];
  const manifestRef = bundlePath ? `${bundlePath}/manifest.json` : 'manifest.json';
  return {
    schemaVersion: 1,
    auditRunId: `agent-audit-maestro-captured-only-${safeIsoId(capturedAt)}`,
    source: 'maestro_v3',
    createdAt: capturedAt.replace(/\.\d{3}Z$/, 'Z'),
    updatedAt: capturedAt.replace(/\.\d{3}Z$/, 'Z'),
    status: failed.length > 0 ? 'partial' : 'captured_only',
    gate: isString(manifest.auditGate) ? manifest.auditGate : 'simulator_audit',
    platform: manifest.platform === 'ios' || manifest.platform === 'android' ? manifest.platform : 'unknown',
    captureTier: 'v3_maestro_full_auto',
    captureMethod: 'maestro',
    simulatorOrEmulatorOnly: true,
    installedDeviceGate: {
      canClearInstalledDeviceGate: false,
      reason: 'Maestro simulator/emulator audit cannot clear installed-device release gates or claim real-device verification.',
    },
    evidence: {
      manifestRef,
      screenshotRefs,
      capturedCount: screenshotRefs.length,
      failed,
      publicSafe: true,
      notes: 'Automated public-safe UI screenshot bundle. Agent may use this for UX audit context only; it is not installed-device proof.',
    },
  };
}

export function buildMaestroAgentHandoff(input) {
  const manifest = input?.manifest && typeof input.manifest === 'object' ? input.manifest : {};
  const agentManifest = input?.agentManifest && typeof input.agentManifest === 'object' ? input.agentManifest : {};
  const bundlePath = isString(input?.bundlePath) ? input.bundlePath : 'artifacts/app-audit/maestro/<platform>/<build>/<timestamp>';
  const captured = Array.isArray(manifest.captured) ? manifest.captured : [];
  const failed = Array.isArray(manifest.failed) ? manifest.failed : [];
  const screenLines = captured.length > 0
    ? captured
        .filter((screen) => screen && typeof screen === 'object' && isString(screen.file))
        .map((screen) => `- ${screen.flow}: ${bundlePath}/${screen.file}`)
        .join('\n')
    : '- none captured';
  const failedLines = failed.length > 0
    ? failed
        .filter((item) => item && typeof item === 'object' && isString(item.flow))
        .map((item) => `- ${item.flow}: ${isString(item.reason) ? item.reason : 'failed'}`)
        .join('\n')
    : '- none';
  return `# Agent Audit Handoff

Source: ${isString(agentManifest.source) ? agentManifest.source : 'maestro_v3'}
Status: ${isString(agentManifest.status) ? agentManifest.status : 'captured_only'}
Platform: ${manifest.platform === 'ios' || manifest.platform === 'android' ? manifest.platform : 'unknown'}
Bundle: ${bundlePath}
Manifest: ${bundlePath}/manifest.json
Agent manifest: ${bundlePath}/agent-audit-manifest.json

## Gate Rule

Maestro simulator/emulator evidence can find UI bugs and regressions, but cannot clear installed-device gates or support an installed-device verified claim. Real iPhone evidence still requires iPhone Mirroring, TestFlight install, and Apple Health device checks.

## Screenshots

${screenLines}

## Failed Flows

${failedLines}

## Agent Review Prompt

Review the public-safe screenshots and manifest for UI regressions, stale/error/provisional truth-label issues, unreadable copy, blocked navigation, and Admin/Dev freshness disagreement. Do not infer real-device Apple Health behavior from simulator evidence.
`;
}

export function parseMaestroArgs(argv) {
  const out = { flow: null, suite: null, platform: null, device: null, dryRun: false, keepTmp: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--flow' && next) { out.flow = next; i += 1; }
    else if (a === '--suite' && next) { if (next === 'ios' || next === 'default') out.suite = next; i += 1; }
    else if (a === '--platform' && next) { if (next === 'ios' || next === 'android') out.platform = next; i += 1; }
    else if (a === '--device' && next) { out.device = next; i += 1; }
    else if (a === '--dry-run') out.dryRun = true;
    else if (a === '--keep-tmp') out.keepTmp = true;
  }
  return out;
}

/**
 * Build the manifest for a scrcpy-driven Android audit. Mirrors the
 * iPhone-Mirroring shape but with android-specific build identity
 * and the Android-side OS version.
 */
export function buildScrcpyAndroidManifest(input) {
  const capturedAt = isString(input?.capturedAt) ? input.capturedAt : new Date().toISOString();
  const auditGate = isString(input?.auditGate) ? input.auditGate : null;
  const verificationStatus = [
    'not_started',
    'captured_only',
    'pass',
    'partial',
    'fail',
    'blocked',
  ].includes(input?.verificationStatus)
    ? input.verificationStatus
    : 'captured_only';
  return {
    schemaVersion: 1,
    captureMethod: 'scrcpy_android',
    auditGate,
    verificationStatus,
    androidVersionCode: Number.isInteger(input?.androidVersionCode) ? input.androidVersionCode : null,
    appVersion: isString(input?.appVersion) ? input.appVersion : null,
    device: isString(input?.device) ? input.device : null,
    androidVersion: isString(input?.androidVersion) ? input.androidVersion : null,
    macosVersion: isString(input?.macosVersion) ? input.macosVersion : null,
    capturedAt,
    screens: sanitizeMirroringScreens(input?.screens),
    notes: isString(input?.notes) ? input.notes : '',
  };
}

function safeIsoId(value) {
  return (isString(value) ? value : new Date().toISOString())
    .replace(/\.\d{3}Z$/, 'Z')
    .replace(/[^0-9A-Za-z]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export const SCRCPY_ANDROID_LABEL_PRESETS = Object.freeze({
  'v21-health-connect': [
    'home',
    'manage-sources',
    'permissions-dialog',
    'after-grant',
    'hc-apps-list',
    'hc-permission-detail',
    'after-sync',
    'lane-progress',
    'build-state-separation',
    'mcp-status',
  ],
});

export function validateV21HealthConnectCapture(manifest) {
  const expectedScreens = SCRCPY_ANDROID_LABEL_PRESETS['v21-health-connect'];
  const screens = Array.isArray(manifest?.screens) ? manifest.screens : [];
  const capturedScreens = screens
    .map((screen) => (screen && typeof screen === 'object' && isString(screen.screen) ? screen.screen : null))
    .filter((screen) => screen !== null);
  const missingScreens = expectedScreens.filter((screen) => !capturedScreens.includes(screen));
  const unexpectedScreens = capturedScreens.filter((screen) => !expectedScreens.includes(screen));
  const ordered = expectedScreens.length === capturedScreens.length
    && expectedScreens.every((screen, idx) => capturedScreens[idx] === screen);
  const verificationStatus = isString(manifest?.verificationStatus) ? manifest.verificationStatus : null;
  const androidVersionCode = Number.isInteger(manifest?.androidVersionCode) ? manifest.androidVersionCode : null;
  const captureMethod = isString(manifest?.captureMethod) ? manifest.captureMethod : null;
  const ok = captureMethod === 'scrcpy_android'
    && verificationStatus === 'captured_only'
    && androidVersionCode === 21
    && screens.length === expectedScreens.length
    && ordered
    && missingScreens.length === 0
    && unexpectedScreens.length === 0;
  return {
    ok,
    captureMethod,
    verificationStatus,
    androidVersionCode,
    expectedCount: expectedScreens.length,
    screenshotCount: screens.length,
    ordered,
    missingScreens,
    unexpectedScreens,
  };
}

/**
 * Captured-only scaffold for the Android v21 Health Connect
 * click-through audit. This is intentionally a partial QA record:
 * screenshots can prove the run was captured, but Agent still owns
 * the installed-device pass/fail verdict.
 */
export function buildV21HealthConnectAgentQaScaffold(input) {
  const manifest = input?.manifest && typeof input.manifest === 'object' ? input.manifest : {};
  const capturedAt = isString(manifest.capturedAt) ? manifest.capturedAt : new Date().toISOString();
  const bundlePath = isString(input?.bundlePath) ? input.bundlePath.replace(/\/+$/g, '') : '';
  const screenshotRefs = Array.isArray(manifest.screens)
    ? manifest.screens
        .map((screen) => {
          if (!screen || typeof screen !== 'object' || !isString(screen.filename)) return null;
          return bundlePath ? `${bundlePath}/${screen.filename}` : screen.filename;
        })
        .filter((ref) => ref !== null)
        .slice(0, 10)
    : [];
  const manifestRef = bundlePath ? `${bundlePath}/manifest.json` : 'manifest.json';
  const captureChecklist = validateV21HealthConnectCapture(manifest);
  return {
    schemaVersion: 1,
    qaRunId: `agent-qa-v21-health-connect-captured-only-${safeIsoId(capturedAt)}`,
    sourceAgent: 'codex-v21-scrcpy-scaffold',
    createdAt: capturedAt.replace(/\.\d{3}Z$/, 'Z'),
    updatedAt: capturedAt.replace(/\.\d{3}Z$/, 'Z'),
    status: 'partial',
    gate: 'release_gate',
    platform: 'android',
    deviceName: isString(manifest.device) ? manifest.device : null,
    installedBuild: {
      iosBuildNumber: null,
      androidVersionCode: Number.isInteger(manifest.androidVersionCode) ? manifest.androidVersionCode : 21,
      appVersion: isString(manifest.appVersion) ? manifest.appVersion : null,
      channel: null,
      track: 'play-internal-testing',
    },
    results: {
      healthManageSources: 'partial',
      androidHealthConnect: 'partial',
      iosAppleHealth: 'not_tested',
      grapplingReadiness: 'not_tested',
      adminControlCentre: 'partial',
      copyTruthfulness: 'partial',
      uiDensity: 'partial',
    },
    releaseGate: {
      newTestFlightAllowed: false,
      newAndroidBuildAllowed: false,
      reason: 'Captured-only screenshot bundle; Agent verdict is required before any installed-device gate claim.',
    },
    requiredFixes: [],
    evidence: {
      screenshotRefs,
      captureChecklist,
      notes: `Captured-only Android v21 Health Connect click-through bundle. Manifest: ${manifestRef}. This scaffold is not a pass verdict.`,
    },
    publicSummary: 'Captured-only Android v21 Health Connect screenshot bundle; installed-device pass/fail is not claimed.',
    privateDetails: null,
  };
}

/**
 * Build the index manifest for an Agent-ready bundle that
 * stitches together the latest capture from every audit tier
 * (simulator + iPhone Mirroring + scrcpy + Maestro) plus a
 * snapshot of the current MCP state. The intent is one folder
 * Aaron / Codex / Claude can hand to Agent without picking
 * across timestamp dirs.
 */
export function buildAgentBundleManifest(input) {
  const generatedAt = isString(input?.generatedAt) ? input.generatedAt : new Date().toISOString();
  const sources = Array.isArray(input?.sources) ? input.sources : [];
  return {
    schemaVersion: 1,
    captureMethod: 'agent_bundle',
    generatedAt,
    repo: sanitizeRepo(input?.repo),
    build: sanitizeBuild(input?.build),
    mcp: {
      generatedAt: isString(input?.mcp?.generatedAt) ? input.mcp.generatedAt : null,
      ageMs: typeof input?.mcp?.ageMs === 'number' && input.mcp.ageMs >= 0 ? input.mcp.ageMs : null,
      staleReason: isString(input?.mcp?.staleReason) ? input.mcp.staleReason : null,
      priority: isString(input?.mcp?.priority) ? input.mcp.priority.slice(0, 280) : null,
      nextAction: isString(input?.mcp?.nextAction) ? input.mcp.nextAction.slice(0, 280) : null,
    },
    sources: sources
      .map((s) => {
        if (!s || typeof s !== 'object') return null;
        if (!isString(s.tier) || !isString(s.path)) return null;
        return {
          tier: s.tier,
          path: s.path,
          manifest: isString(s.manifest) ? s.manifest : null,
          capturedAt: isString(s.capturedAt) ? s.capturedAt : null,
          screenCount: Number.isInteger(s.screenCount) && s.screenCount >= 0 ? s.screenCount : 0,
        };
      })
      .filter((s) => s !== null),
    notes: isString(input?.notes) ? input.notes : '',
  };
}

export function parseAgentBundleArgs(argv) {
  const out = { include: null, exclude: null, mcpUrl: null, dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--include' && next) { out.include = next; i += 1; }
    else if (a === '--exclude' && next) { out.exclude = next; i += 1; }
    else if (a === '--mcp-url' && next) { out.mcpUrl = next; i += 1; }
    else if (a === '--dry-run') out.dryRun = true;
  }
  return out;
}

export function parseScrcpyAndroidArgs(argv) {
  const out = {
    watchDir: null,
    windowMinutes: 10,
    androidVersionCode: null,
    appVersion: null,
    device: null,
    androidVersion: null,
    macosVersion: null,
    labels: null,
    labelPreset: null,
    auditGate: null,
    verificationStatus: null,
    notes: null,
    zip: false,
    nonInteractive: false,
    dryRun: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--watch-dir' && next) { out.watchDir = next; i += 1; }
    else if (a === '--window' && next) { const n = Number(next); if (Number.isFinite(n) && n > 0) out.windowMinutes = n; i += 1; }
    else if (a === '--android-version-code' && next) { const n = Number(next); if (Number.isInteger(n)) out.androidVersionCode = n; i += 1; }
    else if (a === '--app-version' && next) { out.appVersion = next; i += 1; }
    else if (a === '--device' && next) { out.device = next; i += 1; }
    else if (a === '--android-version' && next) { out.androidVersion = next; i += 1; }
    else if (a === '--macos-version' && next) { out.macosVersion = next; i += 1; }
    else if (a === '--labels' && next) { out.labels = next; i += 1; }
    else if (a === '--label-preset' && next) { out.labelPreset = next; i += 1; }
    else if (a === '--audit-gate' && next) { out.auditGate = next; i += 1; }
    else if (a === '--verification-status' && next) { out.verificationStatus = next; i += 1; }
    else if (a === '--notes' && next) { out.notes = next; i += 1; }
    else if (a === '--zip') out.zip = true;
    else if (a === '--non-interactive') out.nonInteractive = true;
    else if (a === '--dry-run') out.dryRun = true;
  }
  return out;
}

export function parseIphoneMirroringArgs(argv) {
  const out = {
    watchDir: null,
    windowMinutes: 10,
    iosBuild: null,
    appVersion: null,
    device: null,
    iosVersion: null,
    macosVersion: null,
    labels: null,
    notes: null,
    zip: false,
    nonInteractive: false,
    dryRun: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--watch-dir' && next) { out.watchDir = next; i += 1; }
    else if (a === '--window' && next) { const n = Number(next); if (Number.isFinite(n) && n > 0) out.windowMinutes = n; i += 1; }
    else if (a === '--ios-build' && next) { out.iosBuild = next; i += 1; }
    else if (a === '--app-version' && next) { out.appVersion = next; i += 1; }
    else if (a === '--device' && next) { out.device = next; i += 1; }
    else if (a === '--ios-version' && next) { out.iosVersion = next; i += 1; }
    else if (a === '--macos-version' && next) { out.macosVersion = next; i += 1; }
    else if (a === '--labels' && next) { out.labels = next; i += 1; }
    else if (a === '--notes' && next) { out.notes = next; i += 1; }
    else if (a === '--zip') { out.zip = true; }
    else if (a === '--non-interactive') { out.nonInteractive = true; }
    else if (a === '--dry-run') { out.dryRun = true; }
  }
  return out;
}

export function parseArgs(argv) {
  const out = { platform: null, skip: '', nonInteractive: false, device: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--platform' && i + 1 < argv.length) {
      const next = argv[i + 1];
      if (next === 'ios' || next === 'android') out.platform = next;
      i += 1;
    } else if (a === '--skip' && i + 1 < argv.length) {
      out.skip = argv[i + 1];
      i += 1;
    } else if (a === '--device' && i + 1 < argv.length) {
      out.device = argv[i + 1];
      i += 1;
    } else if (a === '--non-interactive') {
      out.nonInteractive = true;
    }
  }
  return out;
}
