#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const OUT_DIR = path.join(ROOT, 'data', 'agent-status', 'lanes');
const OUT_FILE = path.join(OUT_DIR, 'agent_qa_result.json');

const STATUSES = new Set(['pass', 'fail', 'blocked', 'repo_only', 'partial']);
const GATES = new Set(['health_connectivity', 'grappling_readiness', 'native_control_centre', 'release_gate', 'general']);
const PLATFORMS = new Set(['android', 'ios', 'both', 'repo']);
const RESULT_STATUSES = new Set(['pass', 'fail', 'blocked', 'repo_only', 'partial', 'not_tested']);

const SECRET_PATTERNS = [
  /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,
  /sk-[A-Za-z0-9_-]{20,}/g,
  /gh[pousr]_[A-Za-z0-9]{30,}/g,
  /whsec_[A-Za-z0-9]{20,}/g,
  /AKIA[0-9A-Z]{16}/g,
  /sb_secret_[A-Za-z0-9_-]{20,}/g,
];

function redact(value) {
  if (typeof value !== 'string') return value;
  return SECRET_PATTERNS.reduce((text, pattern) => text.replace(pattern, '<redacted>'), value);
}

function cleanString(value, cap, fallback = '') {
  const text = redact(String(value ?? fallback)).replace(/\s+/g, ' ').trim();
  return text.length > cap ? `${text.slice(0, Math.max(0, cap - 1)).trim()}…` : text;
}

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
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

function ensureEnum(value, allowed, fallback, field) {
  const text = String(value ?? fallback);
  if (allowed.has(text)) return text;
  throw new Error(`${field} must be one of: ${Array.from(allowed).join(', ')}`);
}

function resultStatus(value) {
  const text = String(value ?? 'not_tested');
  return RESULT_STATUSES.has(text) ? text : 'not_tested';
}

function bool(value) {
  return value === true || value === 'true';
}

function currentBuildTargets() {
  try {
    const app = JSON.parse(fs.readFileSync(path.join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8')).expo ?? {};
    return {
      iosBuildNumber: app.ios?.buildNumber == null ? null : String(app.ios.buildNumber),
      androidVersionCode: Number.isInteger(app.android?.versionCode) ? app.android.versionCode : null,
    };
  } catch {
    return { iosBuildNumber: null, androidVersionCode: null };
  }
}

function normalize(input) {
  const now = isoNow();
  const status = ensureEnum(input.status, STATUSES, 'repo_only', 'status');
  const gate = ensureEnum(input.gate, GATES, 'general', 'gate');
  const platform = ensureEnum(input.platform, PLATFORMS, 'repo', 'platform');
  const installedBuild = input.installedBuild && typeof input.installedBuild === 'object' ? input.installedBuild : {};
  const repo = input.repo && typeof input.repo === 'object' ? input.repo : {};
  const results = input.results && typeof input.results === 'object' ? input.results : {};
  const releaseGate = input.releaseGate && typeof input.releaseGate === 'object' ? input.releaseGate : {};
  const evidence = input.evidence && typeof input.evidence === 'object' ? input.evidence : {};
  const fixes = Array.isArray(input.requiredFixes) ? input.requiredFixes : [];
  const screenshots = Array.isArray(evidence.screenshotRefs) ? evidence.screenshotRefs : [];
  const publicSummary = cleanString(
    input.publicSummary ?? `${status} QA for ${gate} on ${platform}.`,
    280,
  );

  return {
    schemaVersion: 1,
    qaRunId: cleanString(input.qaRunId ?? `agent-qa-${now}`, 80),
    sourceAgent: cleanString(input.sourceAgent ?? 'agent', 80),
    createdAt: cleanString(input.createdAt ?? now, 24),
    updatedAt: cleanString(input.updatedAt ?? now, 24),
    status,
    gate,
    platform,
    deviceName: input.deviceName == null ? null : cleanString(input.deviceName, 120),
    installedBuild: {
      iosBuildNumber: installedBuild.iosBuildNumber == null ? null : cleanString(installedBuild.iosBuildNumber, 20),
      androidVersionCode: Number.isInteger(installedBuild.androidVersionCode) ? installedBuild.androidVersionCode : null,
      appVersion: installedBuild.appVersion == null ? null : cleanString(installedBuild.appVersion, 40),
      channel: installedBuild.channel == null ? null : cleanString(installedBuild.channel, 80),
      track: installedBuild.track == null ? null : cleanString(installedBuild.track, 80),
    },
    repo: {
      branch: cleanString(repo.branch ?? branchName(), 80, 'main'),
      shortHead: /^[0-9a-f]{7,12}$/.test(String(repo.shortHead ?? '')) ? String(repo.shortHead) : shortHead(),
    },
    results: {
      healthManageSources: resultStatus(results.healthManageSources),
      androidHealthConnect: resultStatus(results.androidHealthConnect),
      iosAppleHealth: resultStatus(results.iosAppleHealth),
      grapplingReadiness: resultStatus(results.grapplingReadiness),
      adminControlCentre: resultStatus(results.adminControlCentre),
      copyTruthfulness: resultStatus(results.copyTruthfulness),
      uiDensity: resultStatus(results.uiDensity),
    },
    releaseGate: {
      newTestFlightAllowed: bool(releaseGate.newTestFlightAllowed),
      newAndroidBuildAllowed: bool(releaseGate.newAndroidBuildAllowed),
      reason: cleanString(releaseGate.reason ?? 'No installed-device QA gate has been cleared.', 280),
    },
    requiredFixes: fixes.map((fix) => cleanString(fix, 200)).filter(Boolean).slice(0, 20),
    evidence: {
      screenshotRefs: screenshots.map((ref) => cleanString(ref, 160)).filter(Boolean).slice(0, 10),
      notes: cleanString(evidence.notes ?? '', 1000),
    },
    publicSummary,
    privateDetails: input.privateDetails == null ? null : cleanString(input.privateDetails, 2000),
  };
}

async function promptForInput() {
  const rl = readline.createInterface({ input, output });
  try {
    const status = await rl.question('status (pass/fail/blocked/repo_only/partial): ');
    const gate = await rl.question('gate (health_connectivity/grappling_readiness/native_control_centre/release_gate/general): ');
    const platform = await rl.question('platform (android/ios/both/repo): ');
    const publicSummary = await rl.question('public summary (<=280 chars): ');
    const reason = await rl.question('release gate reason: ');
    return { status, gate, platform, publicSummary, releaseGate: { reason } };
  } finally {
    rl.close();
  }
}

const inputPath = process.argv[2];
if (inputPath === '--help' || inputPath === '-h') {
  console.log('Usage: npm run bridge:agent-qa -- [path/to/agent-qa-result.json]');
  console.log('Without a JSON path, prompts interactively for the minimal fields.');
  process.exit(0);
}
const raw = inputPath
  ? JSON.parse(fs.readFileSync(path.resolve(process.cwd(), inputPath), 'utf8'))
  : await promptForInput();
const payload = normalize(raw);
const targets = currentBuildTargets();

if (payload.status !== 'pass') {
  payload.releaseGate.newTestFlightAllowed = false;
  payload.releaseGate.newAndroidBuildAllowed = false;
}

if (payload.status === 'repo_only') {
  if (!/repo.only|installed/i.test(payload.releaseGate.reason)) {
    payload.releaseGate.reason = cleanString(`Repo-only QA does not clear installed-device gates. ${payload.releaseGate.reason}`, 280);
  }
}
if (payload.status === 'partial') {
  payload.releaseGate.reason = cleanString(`Partial QA does not clear installed-device gates. ${payload.releaseGate.reason}`, 280);
}
if (payload.status === 'blocked' || payload.status === 'fail') {
  payload.releaseGate.reason = cleanString(`${payload.status} QA does not clear installed-device gates. ${payload.releaseGate.reason}`, 280);
}
if (payload.platform === 'repo') {
  payload.releaseGate.newTestFlightAllowed = false;
  payload.releaseGate.newAndroidBuildAllowed = false;
}
if (payload.releaseGate.newTestFlightAllowed) {
  const matchesIos = payload.platform === 'ios' || payload.platform === 'both';
  if (!matchesIos || !targets.iosBuildNumber || payload.installedBuild.iosBuildNumber !== targets.iosBuildNumber) {
    payload.releaseGate.newTestFlightAllowed = false;
    payload.releaseGate.reason = cleanString(`iOS QA must be a pass on current build ${targets.iosBuildNumber ?? 'unknown'}. ${payload.releaseGate.reason}`, 280);
  }
}
if (payload.releaseGate.newAndroidBuildAllowed) {
  const matchesAndroid = payload.platform === 'android' || payload.platform === 'both';
  if (!matchesAndroid || !targets.androidVersionCode || payload.installedBuild.androidVersionCode !== targets.androidVersionCode) {
    payload.releaseGate.newAndroidBuildAllowed = false;
    payload.releaseGate.reason = cleanString(`Android QA must be a pass on current versionCode ${targets.androidVersionCode ?? 'unknown'}. ${payload.releaseGate.reason}`, 280);
  }
}

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(OUT_FILE, `${JSON.stringify(payload, null, 2)}\n`);
console.log(`wrote ${path.relative(ROOT, OUT_FILE)} status=${payload.status} gate=${payload.gate} platform=${payload.platform}`);
