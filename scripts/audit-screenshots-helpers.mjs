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
  return {
    schemaVersion: 1,
    captureMethod: 'maestro',
    captureTier: 'v3_maestro_full_auto',
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

export function parseMaestroArgs(argv) {
  const out = { flow: null, platform: null, device: null, dryRun: false, keepTmp: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = argv[i + 1];
    if (a === '--flow' && next) { out.flow = next; i += 1; }
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
  return {
    schemaVersion: 1,
    captureMethod: 'scrcpy_android',
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
