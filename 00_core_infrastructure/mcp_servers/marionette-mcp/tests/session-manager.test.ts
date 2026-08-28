import test from 'node:test';
import assert from 'node:assert';
import { SessionManager } from '../src/driver/session-manager.js';

function getText(res: any): string {
  const item = res.content?.[0];
  return item && 'text' in item ? (item.text as string) : '';
}

test('SessionManager: multi-tab page lifecycle and navigation', async () => {
  const manager = new SessionManager();
  await manager.initialize();

  // List initial pages
  const list1 = await manager.listPages();
  const pages1 = JSON.parse(getText(list1));
  assert.strictEqual(pages1.length, 1, 'Initial session should have 1 page');
  assert.strictEqual(pages1[0].pageId, 1);

  // Open new page
  const newRes = await manager.newPage({ url: 'http://localhost:3000/dashboard' });
  assert.ok(getText(newRes).includes('Opened new page 2'));

  // List pages again
  const list2 = await manager.listPages();
  const pages2 = JSON.parse(getText(list2));
  assert.strictEqual(pages2.length, 2, 'Should have 2 pages');

  // Select first page
  const selectRes = await manager.selectPage({ pageId: 1 });
  assert.ok(getText(selectRes).includes('Selected page 1'));

  // Navigate page 1
  const navRes = await manager.navigatePage({ pageId: 1, url: 'http://localhost:3000/login' });
  assert.ok(getText(navRes).includes('Navigated page 1 to http://localhost:3000/login'));

  // Resize page 1
  const resizeRes = await manager.resizePage({ pageId: 1, width: 1920, height: 1080 });
  assert.ok(getText(resizeRes).includes('Resized page 1 to 1920x1080'));

  // Close page 2
  const closeRes = await manager.closePage({ pageId: 2 });
  assert.ok(getText(closeRes).includes('Closed page 2'));

  // Cannot close last remaining page
  const closeLastRes = await manager.closePage({ pageId: 1 });
  assert.strictEqual(closeLastRes.isError, true, 'Cannot close last page');

  await manager.close();
});

test('SessionManager: DOM snapshot, screenshot, and interaction', async () => {
  const manager = new SessionManager();
  await manager.initialize();

  // Take snapshot
  const snapshotRes = await manager.takeSnapshot({ pageId: 1 });
  const snapshotText = getText(snapshotRes);
  assert.ok(snapshotText.includes('RootWebArea'), 'Snapshot must contain RootWebArea');

  // Take screenshot
  const screenshotRes = await manager.takeScreenshot({ pageId: 1 });
  assert.strictEqual(screenshotRes.content[0].type, 'image');
  const imgContent = screenshotRes.content[0] as { type: 'image'; data: string; mimeType: string };
  assert.strictEqual(imgContent.mimeType, 'image/png');
  assert.ok(imgContent.data.length > 50, 'Screenshot data must be non-empty base64 string');

  // Verify interaction handlers
  const fillRes = await manager.fill({ pageId: 1, uid: '1_0', value: 'admin@test.com' });
  assert.ok(getText(fillRes).includes('Filled element [uid="1_0"]'));

  const clickRes = await manager.click({ pageId: 1, uid: '1_1' });
  assert.ok(getText(clickRes).includes('Successfully clicked element [uid="1_1"]'));

  const keyRes = await manager.pressKey({ pageId: 1, key: 'Enter' });
  assert.ok(getText(keyRes).includes('Pressed key "Enter"'));

  await manager.close();
});
