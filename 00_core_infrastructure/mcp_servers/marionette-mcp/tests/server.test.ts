import test from 'node:test';
import assert from 'node:assert';
import { MarionetteMcpServer } from '../src/server.js';
import { TOOL_DEFINITIONS } from '../src/tools/tool-definitions.js';

function getText(res: any): string {
  const item = res.content?.[0];
  return item && 'text' in item ? (item.text as string) : '';
}

test('MarionetteMcpServer: registers all 29 tools matching chrome-devtools-mcp', () => {
  const server = new MarionetteMcpServer();
  assert.strictEqual(TOOL_DEFINITIONS.length, 29, 'Must register exactly 29 tools');

  const toolNames = new Set(TOOL_DEFINITIONS.map((t) => t.name));
  const expectedTools = [
    'click',
    'close_page',
    'drag',
    'emulate',
    'evaluate_script',
    'fill',
    'fill_form',
    'get_console_message',
    'get_network_request',
    'handle_dialog',
    'hover',
    'lighthouse_audit',
    'list_console_messages',
    'list_network_requests',
    'list_pages',
    'navigate_page',
    'new_page',
    'performance_analyze_insight',
    'performance_start_trace',
    'performance_stop_trace',
    'press_key',
    'resize_page',
    'select_page',
    'take_heapsnapshot',
    'take_screenshot',
    'take_snapshot',
    'type_text',
    'upload_file',
    'wait_for',
  ];

  for (const expected of expectedTools) {
    assert.ok(toolNames.has(expected), `Tool ${expected} must be registered in tool definitions`);
  }
});

test('MarionetteMcpServer: tool execution across all categories', async () => {
  const server = new MarionetteMcpServer();
  const sm = server.getSessionManager();
  await sm.initialize();

  // 1. list_pages
  const listPagesRes = await sm.listPages();
  assert.ok(getText(listPagesRes).includes('pageId'));

  // 2. new_page
  const newPageRes = await sm.newPage({ url: 'http://localhost:3000' });
  assert.ok(getText(newPageRes).includes('Opened new page'));

  // 3. navigate_page
  const navRes = await sm.navigatePage({ pageId: 2, url: 'http://localhost:3000/app' });
  assert.ok(getText(navRes).includes('Navigated page 2'));

  // 4. select_page
  const selectRes = await sm.selectPage({ pageId: 2 });
  assert.ok(getText(selectRes).includes('Selected page 2'));

  // 5. resize_page
  const resizeRes = await sm.resizePage({ pageId: 2, width: 1440, height: 900 });
  assert.ok(getText(resizeRes).includes('Resized page 2'));

  // 6. take_snapshot
  const snapRes = await sm.takeSnapshot({ pageId: 2 });
  assert.ok(getText(snapRes).includes('RootWebArea'));

  // 7. take_screenshot
  const shotRes = await sm.takeScreenshot({ pageId: 2, format: 'png' });
  assert.strictEqual(shotRes.content[0].type, 'image');

  // 8. click
  const clickRes = await sm.click({ pageId: 2, uid: '2_0' });
  assert.ok(getText(clickRes).toLowerCase().includes('clicked element'));

  // 9. hover
  const hoverRes = await sm.hover({ pageId: 2, uid: '2_0' });
  assert.ok(getText(hoverRes).toLowerCase().includes('hovered over element'));

  // 10. fill
  const fillRes = await sm.fill({ pageId: 2, uid: '2_0', value: 'test' });
  assert.ok(getText(fillRes).toLowerCase().includes('filled element'));

  // 11. fill_form
  const fillFormRes = await sm.fillForm({ pageId: 2, elements: [{ uid: '2_0', value: 'val1' }] });
  assert.ok(getText(fillFormRes).toLowerCase().includes('filled'));

  // 12. drag
  const dragRes = await sm.drag({ pageId: 2, from_uid: '2_0', to_uid: '2_1' });
  assert.ok(getText(dragRes).toLowerCase().includes('dragged element'));

  // 13. press_key
  const pressRes = await sm.pressKey({ pageId: 2, key: 'Tab' });
  assert.ok(getText(pressRes).toLowerCase().includes('pressed key'));

  // 14. type_text
  const typeRes = await sm.typeText({ pageId: 2, text: 'Hello Marionette', submitKey: 'Enter' });
  assert.ok(getText(typeRes).toLowerCase().includes('typed text'));

  // 15. upload_file
  const uploadRes = await sm.uploadFile({ pageId: 2, uid: '2_0', filePaths: ['/tmp/file.txt'] });
  assert.ok(getText(uploadRes).toLowerCase().includes('uploaded files'));

  // 16. handle_dialog
  const dialogRes = await sm.handleDialog({ pageId: 2, action: 'accept' });
  assert.ok(getText(dialogRes).toLowerCase().includes('handled dialog'));

  // 17. evaluate_script
  const evalRes = await sm.evaluateScript({ pageId: 2, function: '() => 42 * 2' });
  assert.strictEqual(getText(evalRes).trim(), '84');

  // 18. list_console_messages
  const consoleRes = await sm.listConsoleMessages({ pageId: 2 });
  assert.ok(getText(consoleRes).length > 0);

  // 19. list_network_requests
  const netRes = await sm.listNetworkRequests({ pageId: 2 });
  assert.ok(getText(netRes).length > 0);

  // 20. emulate
  const emuRes = await sm.emulate({ pageId: 2, colorScheme: 'dark', viewport: '375x667x2,mobile' });
  assert.ok(getText(emuRes).toLowerCase().includes('emulation parameters'));

  // 21. performance_start_trace & 22. performance_stop_trace
  await sm.performanceStartTrace({ pageId: 2, autoStop: false, reload: false });
  const traceRes = await sm.performanceStopTrace({ pageId: 2 });
  assert.ok(getText(traceRes).toLowerCase().includes('performance trace stopped'));

  // 23. performance_analyze_insight
  const insightRes = await sm.performanceAnalyzeInsight({ pageId: 2, insightSetId: 'set1', insightName: 'DocumentLatency' });
  assert.ok(getText(insightRes).includes('TTFB'));

  // 24. lighthouse_audit
  const auditRes = await sm.lighthouseAudit({ pageId: 2, device: 'desktop' });
  assert.ok(getText(auditRes).includes('accessibility'));

  // 25. wait_for
  const waitRes = await sm.waitFor({ pageId: 2, text: ['Marionette', 'Page 2'] });
  assert.ok(getText(waitRes).toLowerCase().includes('found expected text'));

  // 26. close_page
  const closeRes = await sm.closePage({ pageId: 2 });
  assert.ok(getText(closeRes).toLowerCase().includes('closed page 2'));

  await server.close();
});
