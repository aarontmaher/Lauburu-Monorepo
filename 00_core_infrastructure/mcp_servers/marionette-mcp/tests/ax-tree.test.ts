import test from 'node:test';
import assert from 'node:assert';
import { parseHtmlToAxTree, formatAxTree } from '../src/dom/ax-tree-builder.js';
import { AXNode } from '../src/types.js';

test('AX Tree Builder: parses HTML elements into structured AX nodes with UIDs', () => {
  const html = `
    <html>
      <head><title>Test App</title></head>
      <body>
        <header><h1>Application Dashboard</h1></header>
        <main>
          <a href="/profile">My Profile</a>
          <input type="text" id="username" placeholder="Enter username" />
          <button id="btn-login">Sign In</button>
        </main>
      </body>
    </html>
  `;

  const snapshot = parseHtmlToAxTree(html, 1, 'Test App');

  assert.ok(snapshot.formattedTree.includes('RootWebArea "Test App"'), 'Snapshot must contain RootWebArea');
  assert.ok(snapshot.formattedTree.includes('heading "Application Dashboard"'), 'Snapshot must contain heading');
  assert.ok(snapshot.formattedTree.includes('[uid="1_0"]'), 'Snapshot must contain first UID marker');
  assert.ok(snapshot.formattedTree.includes('[uid="1_1"]'), 'Snapshot must contain second UID marker');
  assert.ok(snapshot.elements.length >= 3, 'Must extract at least 3 interactive elements');

  const btn = snapshot.elements.find((e) => e.tagName === 'button');
  assert.ok(btn, 'Must locate button element in extracted list');
  assert.strictEqual(btn?.selector, '#btn-login', 'Button selector should be resolved correctly');
});

test('AX Tree Builder: formats hierarchical AXNode correctly', () => {
  const rootNode: AXNode = {
    role: 'RootWebArea',
    name: 'Main Page',
    focused: true,
    children: [
      {
        role: 'banner',
        children: [
          { role: 'heading', name: 'Header Title', level: 1 },
        ],
      },
      {
        role: 'main',
        children: [
          { role: 'textbox', name: 'Search', value: 'query', uid: '1_0' },
          { role: 'button', name: 'Submit', uid: '1_1' },
        ],
      },
    ],
  };

  const output = formatAxTree(rootNode);
  assert.ok(output.includes('RootWebArea "Main Page" [focused]'));
  assert.ok(output.includes('  banner'));
  assert.ok(output.includes('    heading "Header Title" [level=1]'));
  assert.ok(output.includes('    textbox "Search" (value: "query") [uid="1_0"]'));
  assert.ok(output.includes('    button "Submit" [uid="1_1"]'));
});
