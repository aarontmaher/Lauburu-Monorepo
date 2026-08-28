import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(__dirname, '../..');
const IOS_FLOW_DIR = path.join(ROOT, 'apps/mobile/audit-flows/ios');
const RUNNER = fs.readFileSync(path.join(ROOT, 'scripts/audit-maestro.mjs'), 'utf8');
const HELP = fs.readFileSync(path.join(ROOT, 'audit-system/run-audit.sh'), 'utf8');
const DOC = fs.readFileSync(path.join(ROOT, 'docs/IOS_AUTOMATED_AUDIT.md'), 'utf8');

const expectedFlows = [
  '00-ios-launch-refresh.yml',
  '01-ios-home-readiness.yml',
  '02-ios-health-apple-health.yml',
  '03-ios-readiness-states.yml',
  '04-ios-journal.yml',
  '05-ios-admin-dev-queues.yml',
  '06-ios-control-queue.yml',
];

const actualFlows = fs.readdirSync(IOS_FLOW_DIR).filter((name) => name.endsWith('.yml')).sort();
assert.deepEqual(actualFlows, expectedFlows, 'iOS Maestro suite flow list');

const joinedFlows = actualFlows
  .map((name) => fs.readFileSync(path.join(IOS_FLOW_DIR, name), 'utf8'))
  .join('\n');

for (const token of [
  'launchApp',
  'Home',
  'Readiness',
  'Apple Health',
  'Journal',
  'Admin / Dev',
  'Overnight Prompt Queue',
  'Refresh',
  'stale',
  'Error',
  'Seed / provisional',
]) {
  assert.ok(joinedFlows.includes(token), `iOS flows include ${token}`);
}

assert.ok(RUNNER.includes('--suite <default|ios>'), 'runner documents --suite ios');
assert.ok(RUNNER.includes("args.suite === 'ios'"), 'runner selects the iOS suite directory');
assert.ok(RUNNER.includes('agent-handoff.md'), 'runner writes Agent handoff artifact');
assert.ok(HELP.includes('--platform ios --suite ios'), 'entrypoint help shows iOS suite command');
assert.ok(DOC.includes('XCUITest Plan'), 'iOS audit doc includes XCUITest plan');
assert.ok(DOC.includes('cannot clear installed-device gates'), 'iOS audit doc preserves installed-device gate rule');
