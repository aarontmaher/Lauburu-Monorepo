#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const strict = process.argv.includes('--strict');

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8');
}

function exists(rel) {
  return fs.existsSync(path.join(ROOT, rel));
}

function check(id, ok, detail, route = null) {
  return { id, ok: Boolean(ok), route, detail };
}

const home = read('apps/mobile/app/(tabs)/index.tsx');
const settings = read('apps/mobile/app/(tabs)/settings.tsx');
const health = read('apps/mobile/app/(tabs)/health.tsx');
const layout = read('apps/mobile/app/(tabs)/_layout.tsx');

const checks = [
  check(
    'home-route-exists',
    exists('apps/mobile/app/(tabs)/index.tsx'),
    'Home tab route file exists.',
    '/(tabs)/index',
  ),
  check(
    'create-account-route-target',
    /router\.push\(\{\s*pathname:\s*['"]\/settings['"][\s\S]*auth:\s*['"]sign_up['"]/.test(home),
    'Create account should route to /settings with auth=sign_up, not a missing grouped path.',
    '/settings?auth=sign_up',
  ),
  check(
    'sign-in-route-target',
    /router\.push\(\{\s*pathname:\s*['"]\/settings['"][\s\S]*auth:\s*['"]sign_in['"]/.test(home),
    'Sign in should route to /settings with auth=sign_in, not a missing grouped path.',
    '/settings?auth=sign_in',
  ),
  check(
    'settings-route-exists',
    exists('apps/mobile/app/(tabs)/settings.tsx'),
    'Settings tab route file exists and owns auth form.',
    '/settings',
  ),
  check(
    'settings-auth-param-consumed',
    /useLocalSearchParams/.test(settings) && /sign_up|sign_in/.test(settings),
    'Settings should consume auth route params so Create account opens signup mode and Sign in opens login mode.',
    '/settings?auth=sign_up|sign_in',
  ),
  check(
    'back-navigation-tab-context',
    /name="settings"/.test(layout) || /settings/.test(layout),
    'Settings is registered in the tab layout, so back/tab navigation can return to Home.',
    '/settings -> back/home',
  ),
  check(
    'health-route-exists',
    exists('apps/mobile/app/(tabs)/health.tsx'),
    'Health tab route file exists.',
    '/health',
  ),
  check(
    'manage-sources-reachable',
    /Manage health sources/.test(health) || /HealthActionsPanel/.test(health),
    'Health screen exposes Manage health sources path.',
    '/health -> Manage health sources',
  ),
  check(
    'grappling-readiness-reachable',
    /InsightsCard|Grappling Readiness|readiness/i.test(health) && /Provisional|Seed|readiness/i.test(health),
    'Health screen exposes provisional Grappling Readiness surface.',
    '/health -> readiness',
  ),
];

const failed = checks.filter((item) => !item.ok);
const checklist = [
  'Home renders without redirect loop.',
  'Tap Create account: stays inside app and opens account creation mode.',
  'Back from account creation returns to Home or previous tab.',
  'Tap Sign in: stays inside app and opens sign-in mode.',
  'Back from sign-in returns to Home or previous tab.',
  'Open Health tab and tap Manage health sources.',
  'Confirm Apple Health is iOS-only and Health Connect is Android-only in the sheet.',
  'Confirm Grappling Readiness is visible only as provisional/seed context.',
];

const result = {
  ok: failed.length === 0,
  strict,
  generatedAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  checks,
  checklist,
  qaBridgeTemplate: 'scripts/templates/agent-qa-simulator-route-smoke.json',
};

console.log(JSON.stringify(result, null, 2));
if (strict && failed.length > 0) process.exit(1);
