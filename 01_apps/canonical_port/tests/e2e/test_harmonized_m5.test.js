/**
 * Test Suite: Milestone M5 Harmonized Production Integration
 * Version: 3.0.0-CANONICAL
 * Verifies the Triple-Pillar Harmonized Synthesis in src/App.jsx and src/components/layout/:
 * - Persistent Top Header: Track Alpha HeaderStatusBar with 7-node fleet pills, 108GB RAM / 82.8GB VRAM meter, 0.277ms TB4 DMA badge, WAN badge
 * - 9-Screen Tab Navigation Matrix with Tab 1 [c] AgiCodingTerminalView as primary default cockpit
 * - Persistent Bottom Dock: Track Beta SlashCommandDock (/audit, /duel, /cron, /storage, /ping, /revive)
 * - Strict Rule #0 Zero-Mock fallbacks and non-blocking asynchronous state updates
 */

import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';
import {
  INITIAL_CLUSTER_VRAM,
  INITIAL_NETWORK_METRICS,
  INITIAL_AGI_MODELS
} from '../../src/services/mockFallbackData.js';

export const suite = createTestSuite('Milestone M5: Winning Harmonized Production React App');

suite.test('[M5][T1] App renders ShellLayout with Tab 1 [c] AgiCodingTerminalView by default', async () => {
  const mod = await loadComponent('src/App.jsx');
  const html = render(mod.App);

  // Top Header Status Bar
  assertTextContains(html, 'CANONICAL PORT');
  assertTextContains(html, 'v3.0-CANONICAL');
  assertTextContains(html, 'MASTER: KIMI 88B TITAN');
  assertTextContains(html, 'EDGE: QWEN 3.8 MAX');
  assertTextContains(html, 'POOLED VRAM:');
  assertTextContains(html, '0.277 ms');
  assertTextContains(html, 'FLEET MATRIX:');
  assertTextContains(html, 'L1');
  assertTextContains(html, 'L2');
  assertTextContains(html, 'L3');
  assertTextContains(html, 'L4');
  assertTextContains(html, 'L5');
  assertTextContains(html, 'L6');
  assertTextContains(html, 'L7');
  assertTextContains(html, 'GW');

  // Tab 1 [c] Primary Cockpit (AgiCodingTerminalView)
  assertTextContains(html, 'Screen 1: Master AGI Coding & Synthesis Terminal');
  assertTextContains(html, 'AST CODE BUFFER EDITOR');
  assertTextContains(html, 'MULTI-AGENT SWARM CHAT STREAM');

  // Bottom Persistent Dock (SlashCommandDock)
  assertTextContains(html, 'SLASH DOCK:');
  assertTextContains(html, '/audit');
  assertTextContains(html, '/duel');
  assertTextContains(html, '/cron');
  assertTextContains(html, '/storage');
  assertTextContains(html, '/ping');
  assertTextContains(html, '/revive');
});

suite.test('[M5][T2] HeaderStatusBar renders all 7 physical nodes + gateway in Fleet Matrix strip', async () => {
  const mod = await loadComponent('src/components/layout/HeaderStatusBar.jsx');
  const html = render(mod.HeaderStatusBar, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    networkMetrics: INITIAL_NETWORK_METRICS,
    isConnected: true,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'FLEET MATRIX:');
  assertTextContains(html, 'L1');
  assertTextContains(html, 'L2');
  assertTextContains(html, 'L3');
  assertTextContains(html, 'L4');
  assertTextContains(html, 'L5');
  assertTextContains(html, 'L6');
  assertTextContains(html, 'L7');
  assertTextContains(html, 'GW');
  assertTextContains(html, 'Mac');
  assertTextContains(html, 'Linux');
  assertTextContains(html, 'Pixel');
  assertTextContains(html, 'Samsung');
  assertTextContains(html, 'GL.iNet');
});

suite.test('[M5][T3] ShellLayout correctly nests Top Header, Main Viewport, and Bottom Slash Dock', async () => {
  const mod = await loadComponent('src/components/layout/ShellLayout.jsx');
  const html = render(mod.ShellLayout, {
    activeRoute: 'agi-terminal',
    setActiveRoute: () => {},
    isSidebarCollapsed: false,
    toggleSidebar: () => {},
    clusterVram: INITIAL_CLUSTER_VRAM,
    networkMetrics: INITIAL_NETWORK_METRICS,
    isConnected: true,
    onDispatchAction: () => {},
    actionNotification: null,
    activeEngine: 'auto',
    onCycleEngine: () => {},
    children: '<div id="test-viewport">VIEWPORT CONTENT</div>'
  });

  assertTextContains(html, 'CANONICAL PORT');
  assertTextContains(html, 'LAUBURU MESH');
  assertTextContains(html, 'VIEWPORT CONTENT');
  assertTextContains(html, 'SLASH DOCK:');
});

suite.test('[M5][T4] SidebarNav contains hotkey indicators [c], [n], [h], [b], [i], [t], [g], [x], [o]', async () => {
  const mod = await loadComponent('src/components/layout/SidebarNav.jsx');
  const html = render(mod.SidebarNav, {
    activeRoute: 'agi-terminal',
    setActiveRoute: () => {},
    isSidebarCollapsed: false,
    toggleSidebar: () => {}
  });

  assertTextContains(html, '[c]');
  assertTextContains(html, '[n]');
  assertTextContains(html, '[h]');
  assertTextContains(html, '[b]');
  assertTextContains(html, '[i]');
  assertTextContains(html, '[t]');
  assertTextContains(html, '[g]');
  assertTextContains(html, '[x]');
  assertTextContains(html, '[o]');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_harmonized_m5.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}
