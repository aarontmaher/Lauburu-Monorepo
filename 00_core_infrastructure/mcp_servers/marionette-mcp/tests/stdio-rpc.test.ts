import test from 'node:test';
import assert from 'node:assert';
import { spawn } from 'node:child_process';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const serverScript = path.resolve(__dirname, '../src/index.js');

test('Stdio JSON-RPC: initialize, tools/list, and tools/call over stdio pipe', async () => {
  const child = spawn('node', [serverScript], {
    stdio: ['pipe', 'pipe', 'inherit'],
  });

  let responseBuffer = '';

  const sendRequest = (req: any): Promise<any> => {
    return new Promise((resolve, reject) => {
      const onData = (data: Buffer) => {
        responseBuffer += data.toString('utf8');
        const lines = responseBuffer.split('\n');
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line) {
            try {
              const parsed = JSON.parse(line);
              if (parsed.id === req.id) {
                child.stdout.off('data', onData);
                resolve(parsed);
                return;
              }
            } catch {
              // ignore non-json log lines
            }
          }
        }
      };

      child.stdout.on('data', onData);
      child.stdin.write(JSON.stringify(req) + '\n');
    });
  };

  try {
    // 1. Initialize Handshake
    const initReq = {
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'test-client', version: '1.0.0' },
      },
    };
    const initRes = await sendRequest(initReq);
    assert.strictEqual(initRes.jsonrpc, '2.0');
    assert.strictEqual(initRes.id, 1);
    assert.strictEqual(initRes.result.serverInfo.name, 'marionette-mcp');

    // 2. tools/list
    const listReq = {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {},
    };
    const listRes = await sendRequest(listReq);
    assert.strictEqual(listRes.id, 2);
    assert.strictEqual(listRes.result.tools.length, 29, 'Must list exactly 29 tools via MCP stdio protocol');

    // 3. tools/call take_screenshot
    const callReq = {
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'take_screenshot',
        arguments: { pageId: 1, format: 'png' },
      },
    };
    const callRes = await sendRequest(callReq);
    assert.strictEqual(callRes.id, 3);
    assert.ok(callRes.result.content.length > 0);
    assert.strictEqual(callRes.result.content[0].type, 'image');

    // 4. tools/call take_snapshot
    const snapReq = {
      jsonrpc: '2.0',
      id: 4,
      method: 'tools/call',
      params: {
        name: 'take_snapshot',
        arguments: { pageId: 1 },
      },
    };
    const snapRes = await sendRequest(snapReq);
    assert.strictEqual(snapRes.id, 4);
    assert.ok(snapRes.result.content[0].text.includes('RootWebArea'));

  } finally {
    child.kill('SIGTERM');
  }
});
