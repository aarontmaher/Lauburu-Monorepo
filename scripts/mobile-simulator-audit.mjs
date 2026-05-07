#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const TMP_ROOT = path.join(ROOT, 'tmp', 'qa-screenshots');
const strict = process.argv.includes('--strict');
const noScreenshot = process.argv.includes('--no-screenshot');
const APP_START_COMMAND = 'cd apps/mobile && npx expo start --dev-client';
const IOS_SIMULATOR_OPEN_COMMAND = 'open -a Simulator';
const IOS_APP_RUN_COMMAND = 'cd apps/mobile && npx expo run:ios';
const ROUTE_SMOKE_COMMAND = 'node scripts/mobile-route-smoke.mjs --strict';

function stamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '-',
    pad(now.getHours()),
    pad(now.getMinutes()),
  ].join('');
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    ...options,
  });
  return {
    ok: result.status === 0,
    status: result.status,
    stdout: (result.stdout ?? '').trim(),
    stderr: (result.stderr ?? '').trim(),
  };
}

function shortHead() {
  try {
    return execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function branchName() {
  try {
    return execFileSync('git', ['branch', '--show-current'], { cwd: ROOT, encoding: 'utf8' }).trim() || 'main';
  } catch {
    return 'main';
  }
}

function readAppConfig() {
  try {
    const app = JSON.parse(fs.readFileSync(path.join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8')).expo ?? {};
    return {
      appVersion: app.version ?? null,
      iosBuildNumber: app.ios?.buildNumber == null ? null : String(app.ios.buildNumber),
      androidVersionCode: Number.isInteger(app.android?.versionCode) ? app.android.versionCode : null,
      iosBundleIdentifier: app.ios?.bundleIdentifier ?? null,
      androidPackage: app.android?.package ?? null,
    };
  } catch {
    return {
      appVersion: null,
      iosBuildNumber: null,
      androidVersionCode: null,
      iosBundleIdentifier: null,
      androidPackage: null,
    };
  }
}

function compact(text, cap = 700) {
  const clean = String(text ?? '').replace(/\s+/g, ' ').trim();
  return clean.length > cap ? `${clean.slice(0, cap - 1).trim()}…` : clean;
}

function routeSmoke() {
  const result = run('node', ['scripts/mobile-route-smoke.mjs', '--strict']);
  let parsed = null;
  try {
    parsed = JSON.parse(result.stdout);
  } catch {
    parsed = null;
  }
  return { ...result, parsed };
}

async function metroStatus() {
  try {
    const response = await fetch('http://localhost:8081/status');
    const text = await response.text();
    return {
      ok: response.ok && /packager-status:running/i.test(text),
      status: response.status,
      detail: compact(text, 120),
      command: APP_START_COMMAND,
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      detail: compact(error instanceof Error ? error.message : String(error), 160),
      command: APP_START_COMMAND,
    };
  }
}

function captureIosScreenshot(outDir) {
  const expectedPath = path.join(outDir, 'ios-simulator-home.png');
  if (noScreenshot) {
    return {
      ok: false,
      skipped: true,
      path: path.relative(ROOT, expectedPath),
      command: `xcrun simctl io booted screenshot ${path.relative(ROOT, expectedPath)}`,
      detail: '--no-screenshot was passed.',
    };
  }
  const xcrun = run('xcrun', ['simctl', 'list', 'devices', 'booted']);
  if (!xcrun.ok || !/\(Booted\)/.test(xcrun.stdout)) {
    return {
      ok: false,
      skipped: false,
      path: path.relative(ROOT, expectedPath),
      command: `xcrun simctl io booted screenshot ${path.relative(ROOT, expectedPath)}`,
      detail: 'No booted iOS Simulator found. Boot one, open the app, then rerun npm run qa:simulator.',
    };
  }
  const screenshotPath = expectedPath;
  const shot = run('xcrun', ['simctl', 'io', 'booted', 'screenshot', screenshotPath]);
  return {
    ok: shot.ok && fs.existsSync(screenshotPath),
    skipped: false,
    path: path.relative(ROOT, screenshotPath),
    command: `xcrun simctl io booted screenshot ${path.relative(ROOT, screenshotPath)}`,
    detail: shot.ok ? 'Captured booted iOS Simulator screenshot.' : compact(`${shot.stderr} ${shot.stdout}`, 240),
  };
}

function androidPlan() {
  return [
    'Start emulator from Android Studio Device Manager or run: emulator -list-avds && emulator -avd <name>.',
    'Start Metro: cd apps/mobile && npx expo start --dev-client.',
    'Install/run the app: cd apps/mobile && npx expo run:android.',
    'Navigate Health -> Manage health sources; verify Health Connect copy and missingness.',
    'Capture screenshot: adb exec-out screencap -p > tmp/qa-screenshots/<run>/android-health.png.',
    'Record partial QA with npm run bridge:agent-qa -- tmp/qa-screenshots/<run>/agent-qa-simulator.json.',
  ];
}

const runId = stamp();
const outDir = path.join(TMP_ROOT, runId);
fs.mkdirSync(outDir, { recursive: true });

const app = readAppConfig();
const metro = await metroStatus();
const smoke = routeSmoke();
const iosScreenshot = captureIosScreenshot(outDir);
const screenshotRefs = iosScreenshot.ok && iosScreenshot.path ? [iosScreenshot.path] : [];
const smokeChecks = smoke.parsed?.checks ?? [];
const failedChecks = Array.isArray(smokeChecks) ? smokeChecks.filter((check) => !check.ok) : [];
const routeChecklist = Array.isArray(smoke.parsed?.checklist)
  ? smoke.parsed.checklist
  : [
      'Home renders without redirect loop.',
      'Create account opens account creation mode.',
      'Sign in opens sign-in mode.',
      'Back navigation returns to Home or previous tab.',
      'Health -> Manage health sources is reachable.',
      'Grappling Readiness is reachable and provisional.',
    ];
const requiredFixes =
  failedChecks.length > 0
    ? failedChecks.map((check) => `${check.id}: ${check.detail}`)
    : ['Simulator QA remains partial and does not clear installed-device gates.'];

const qaJson = {
  schemaVersion: 1,
  qaRunId: `qa-simulator-${runId}`,
  sourceAgent: 'agent',
  status: smoke.ok ? 'partial' : 'blocked',
  gate: 'general',
  platform: 'ios',
  deviceName: 'iOS Simulator',
  installedBuild: {
    iosBuildNumber: app.iosBuildNumber,
    androidVersionCode: null,
    appVersion: app.appVersion,
    channel: 'simulator',
    track: 'local',
  },
  repo: {
    branch: branchName(),
    shortHead: shortHead(),
  },
  results: {
    healthManageSources: smoke.ok ? 'partial' : 'not_tested',
    androidHealthConnect: 'not_tested',
    iosAppleHealth: 'not_tested',
    grapplingReadiness: smoke.ok ? 'partial' : 'not_tested',
    adminControlCentre: 'not_tested',
    copyTruthfulness: smoke.ok ? 'partial' : 'not_tested',
    uiDensity: screenshotRefs.length > 0 ? 'partial' : 'not_tested',
  },
  releaseGate: {
    newTestFlightAllowed: false,
    newAndroidBuildAllowed: false,
    reason: 'Simulator QA is partial and does not clear installed-device gates.',
  },
  requiredFixes,
  evidence: {
    screenshotRefs,
    notes: compact(
      [
        `Metro: ${metro.ok ? 'running' : `not confirmed (${metro.detail}); start with ${metro.command}`}.`,
        `Route smoke: ${smoke.ok ? 'strict pass' : 'failed or blocked'}.`,
        iosScreenshot.detail,
      ].join(' '),
      900,
    ),
  },
  publicSummary: smoke.ok
    ? 'Simulator route smoke/evidence captured; installed-device QA still required before build gates clear.'
    : 'Simulator audit harness ran but route smoke or local simulator evidence is blocked.',
  privateDetails: null,
};

const qaJsonPath = path.join(outDir, 'agent-qa-simulator.json');
const handoffPath = path.join(outDir, 'agent-handoff-prompt.md');
const androidPlanPath = path.join(outDir, 'android-emulator-plan.md');
const commandsPath = path.join(outDir, 'commands.md');
const routeChecklistPath = path.join(outDir, 'route-smoke-checklist.md');
const screenshotPlanPath = path.join(outDir, 'screenshot-capture-paths.md');

fs.writeFileSync(qaJsonPath, `${JSON.stringify(qaJson, null, 2)}\n`);
fs.writeFileSync(androidPlanPath, `${androidPlan().map((step, index) => `${index + 1}. ${step}`).join('\n')}\n`);
fs.writeFileSync(
  commandsPath,
  [
    '# Simulator QA Commands',
    '',
    'Start Metro/dev server:',
    '',
    `    ${APP_START_COMMAND}`,
    '',
    'Open iOS Simulator:',
    '',
    `    ${IOS_SIMULATOR_OPEN_COMMAND}`,
    '',
    'Install/open the app in iOS Simulator:',
    '',
    `    ${IOS_APP_RUN_COMMAND}`,
    '',
    'Run static route smoke:',
    '',
    `    ${ROUTE_SMOKE_COMMAND}`,
    '',
    'Run full evidence harness:',
    '',
    '    npm run qa:simulator',
    '',
    'Record the QA result into MCP/shared state:',
    '',
    `    npm run bridge:agent-qa -- ${path.relative(ROOT, qaJsonPath)}`,
    '    npm run bridge:snapshot',
    '',
  ].join('\n'),
);
fs.writeFileSync(routeChecklistPath, `${routeChecklist.map((item, index) => `${index + 1}. ${item}`).join('\n')}\n`);
fs.writeFileSync(
  screenshotPlanPath,
  [
    '# Screenshot Capture Paths',
    '',
    `Evidence folder: ${path.relative(ROOT, outDir)}`,
    '',
    'iOS Simulator home/current screen:',
    '',
    `    ${iosScreenshot.command}`,
    '',
    `Expected path: ${iosScreenshot.path}`,
    '',
    'Suggested extra screenshots after navigating manually:',
    '',
    `- ${path.relative(ROOT, path.join(outDir, 'ios-health-manage-sources.png'))}`,
    `- ${path.relative(ROOT, path.join(outDir, 'ios-grappling-readiness.png'))}`,
    `- ${path.relative(ROOT, path.join(outDir, 'ios-admin-control-centre.png'))}`,
    '',
    'Android Emulator:',
    '',
    `    adb exec-out screencap -p > ${path.relative(ROOT, path.join(outDir, 'android-health-manage-sources.png'))}`,
    '',
  ].join('\n'),
);
fs.writeFileSync(
  handoffPath,
  [
    '# Agent Simulator QA Handoff',
    '',
    `Repo: ${branchName()} @ ${shortHead()}`,
    `Evidence folder: ${path.relative(ROOT, outDir)}`,
    `QA JSON: ${path.relative(ROOT, qaJsonPath)}`,
    `Commands: ${path.relative(ROOT, commandsPath)}`,
    `Route checklist: ${path.relative(ROOT, routeChecklistPath)}`,
    `Screenshot paths: ${path.relative(ROOT, screenshotPlanPath)}`,
    '',
    'Exact commands Aaron can run locally:',
    '',
    `- Start app/dev server: ${APP_START_COMMAND}`,
    `- Open iOS Simulator: ${IOS_SIMULATOR_OPEN_COMMAND}`,
    `- Install/open iOS simulator app: ${IOS_APP_RUN_COMMAND}`,
    `- Route smoke: ${ROUTE_SMOKE_COMMAND}`,
    '',
    'Audit these screens from the local iOS Simulator evidence and any screenshots Aaron adds:',
    '',
    ...routeChecklist.map((item) => `- ${item}`),
    '- Admin/Control Centre only if Aaron is signed in as admin',
    '',
    'Screenshot list:',
    '',
    ...(screenshotRefs.length > 0 ? screenshotRefs : [iosScreenshot.path]).map((ref) => `- ${ref}`),
    `- ${path.relative(ROOT, path.join(outDir, 'ios-health-manage-sources.png'))}`,
    `- ${path.relative(ROOT, path.join(outDir, 'ios-grappling-readiness.png'))}`,
    `- ${path.relative(ROOT, path.join(outDir, 'ios-admin-control-centre.png'))}`,
    '',
    'Return AGENT_QA_RESULT_JSON using the schema in the QA JSON file.',
    'Keep status partial for simulator-only QA. Do not clear TestFlight or Android internal build gates.',
    'Do not include private health/journal data, secrets, tokens, raw logs, or screenshots with sensitive data.',
    '',
    'To ingest after review:',
    '',
    `npm run bridge:agent-qa -- ${path.relative(ROOT, qaJsonPath)}`,
    'npm run bridge:snapshot',
    '',
  ].join('\n'),
);

const summary = {
  ok: smoke.ok,
  strict,
  runId,
  evidenceDir: path.relative(ROOT, outDir),
  metro,
  routeSmoke: {
    ok: smoke.ok,
    failedChecks: failedChecks.map((check) => check.id),
    checklist: routeChecklist,
  },
  iosScreenshot,
  qaJson: path.relative(ROOT, qaJsonPath),
  commands: path.relative(ROOT, commandsPath),
  routeChecklist: path.relative(ROOT, routeChecklistPath),
  screenshotPlan: path.relative(ROOT, screenshotPlanPath),
  handoffPrompt: path.relative(ROOT, handoffPath),
  androidPlan: path.relative(ROOT, androidPlanPath),
  ingestCommand: `npm run bridge:agent-qa -- ${path.relative(ROOT, qaJsonPath)}`,
};

console.log(JSON.stringify(summary, null, 2));
if (strict && !smoke.ok) process.exit(1);
