import type { AddressInfo } from 'net';
import { app } from '../app';

const TOKEN = 'test-token';
process.env.ATHLETE_MEMORY_API_TOKEN = TOKEN;

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function getJson(baseUrl: string, path: string): Promise<any> {
  const res = await fetch(`${baseUrl}${path}`, {
    headers: {
      Accept: 'application/json',
      'x-athlete-memory-token': TOKEN,
    },
  });
  assert(res.status === 200, `${path} expected HTTP 200, got ${res.status}`);
  return res.json();
}

async function main() {
  const server = app.listen(0);
  try {
    const address = server.address() as AddressInfo;
    const baseUrl = `http://127.0.0.1:${address.port}`;

    const workStatus = await getJson(baseUrl, '/api/work_status');
    assert(workStatus.schemaVersion === 1, 'work_status schemaVersion mismatch');
    assert(typeof workStatus.generatedAt === 'string', 'work_status generatedAt missing');
    assert(typeof workStatus.currentPriority === 'string', 'work_status currentPriority missing');
    assert(workStatus.liveStatus && typeof workStatus.liveStatus === 'object', 'work_status liveStatus missing');
    assert(typeof workStatus.liveStatus.androidVersionCode === 'number', 'work_status androidVersionCode missing');
    assert(workStatus.repoStatus && typeof workStatus.repoStatus === 'object', 'work_status repoStatus missing');
    assert(typeof workStatus.nextAction === 'string', 'work_status nextAction missing');

    const coderLanes = await getJson(baseUrl, '/api/coder_lanes');
    assert(coderLanes.schemaVersion === 1, 'coder_lanes schemaVersion mismatch');
    assert(Array.isArray(coderLanes.lanes), 'coder_lanes lanes missing');
    assert(coderLanes.lanes.some((lane: any) => lane.laneId === 'claude'), 'coder_lanes claude row missing');
    assert(coderLanes.lanes.some((lane: any) => lane.laneId === 'codex'), 'coder_lanes codex row missing');
    for (const lane of coderLanes.lanes) {
      assert(typeof lane.status === 'string', 'coder_lanes lane status missing');
      assert('dirtyFiles' in lane && Array.isArray(lane.dirtyFiles), 'coder_lanes dirtyFiles missing');
    }

    const buildStatus = await getJson(baseUrl, '/api/build_status');
    assert(buildStatus.schemaVersion === 1, 'build_status schemaVersion mismatch');
    assert(typeof buildStatus.generatedAt === 'string', 'build_status generatedAt missing');
    assert(typeof buildStatus.android.versionCode === 'number', 'build_status android.versionCode missing');
    assert(typeof buildStatus.android.playTrack === 'string', 'build_status android.playTrack missing');
    assert(typeof buildStatus.ios.buildNumber === 'string', 'build_status ios.buildNumber missing');
    assert(typeof buildStatus.ios.testflightGroup === 'string', 'build_status ios.testflightGroup missing');

    const handoff = await getJson(baseUrl, '/api/handoff');
    assert(handoff.schemaVersion === 1, 'handoff schemaVersion mismatch');
    assert(typeof handoff.latestClaudePrompt === 'string', 'handoff latestClaudePrompt missing');
    assert(typeof handoff.latestCodexPrompt === 'string', 'handoff latestCodexPrompt missing');
    assert(Array.isArray(handoff.manualSteps), 'handoff manualSteps missing');
    assert(Array.isArray(handoff.doNotTouch), 'handoff doNotTouch missing');
    assert(typeof handoff.safeToBuild === 'boolean', 'handoff safeToBuild missing');
    assert(typeof handoff.safeToBuildReason === 'string', 'handoff safeToBuildReason missing');

    const terminalSummary = await getJson(baseUrl, '/api/terminal_summary');
    assert(terminalSummary.schemaVersion === 1, 'terminal_summary schemaVersion mismatch');
    assert(typeof terminalSummary.generatedAt === 'string', 'terminal_summary generatedAt missing');
    assert(Array.isArray(terminalSummary.entries), 'terminal_summary entries missing');
    assert(terminalSummary.entries.length <= 50, 'terminal_summary entry cap exceeded');
    for (const entry of terminalSummary.entries) {
      assert(typeof entry.laneId === 'string', 'terminal_summary entry laneId missing');
      assert(typeof entry.at === 'string', 'terminal_summary entry at missing');
      assert(typeof entry.summary === 'string' && entry.summary.length <= 1200, 'terminal_summary entry summary cap');
      assert(typeof entry.verification === 'string' && entry.verification.length <= 240, 'terminal_summary entry verification cap');
      assert(typeof entry.nextAction === 'string' && entry.nextAction.length <= 240, 'terminal_summary entry nextAction cap');
      assert(entry.exitCode === null || typeof entry.exitCode === 'number', 'terminal_summary entry exitCode shape');
    }

    // Auth gating: every connector route must reject the wrong / missing token.
    for (const path of ['/api/work_status', '/api/coder_lanes', '/api/build_status', '/api/handoff', '/api/terminal_summary']) {
      const noToken = await fetch(`${baseUrl}${path}`, { headers: { Accept: 'application/json' } });
      assert(noToken.status === 403, `${path} unauth expected 403, got ${noToken.status}`);
      const wrongToken = await fetch(`${baseUrl}${path}`, {
        headers: { Accept: 'application/json', 'x-athlete-memory-token': 'not-the-real-token' },
      });
      assert(wrongToken.status === 403, `${path} wrong-token expected 403, got ${wrongToken.status}`);
    }

    console.log('MCP route schema tests passed.');
  } finally {
    await new Promise<void>((resolve, reject) => {
      server.close((err: Error | undefined) => (err ? reject(err) : resolve()));
    });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
