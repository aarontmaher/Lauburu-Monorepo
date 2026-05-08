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
