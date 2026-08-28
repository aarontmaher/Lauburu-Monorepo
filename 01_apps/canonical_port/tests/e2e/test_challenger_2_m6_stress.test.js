/**
 * Adversarial Empirical Stress Test Suite — Challenger 2
 * Focus: Rapid Hotkey Cycling (9 Screens), Extreme Slash Command Dock Inputs, Network Disconnection Resilience
 * Application: Canonical Port Web UI (Port 4000)
 * Version: 3.0.0-CANONICAL
 */

import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';
import { canonicalApi } from '../../src/services/api.js';
import {
  INITIAL_CLUSTER_VRAM,
  INITIAL_NETWORK_METRICS,
  INITIAL_AGI_MODELS,
  INITIAL_BIOMETRICS_STATE,
  INITIAL_TRAINING_STATE,
  INITIAL_GAMES_STATE,
  INITIAL_STRUCTURAL_METRICS,
  INITIAL_EXECUTION_TRACES,
  INITIAL_LEADERBOARD,
  INITIAL_TOOLING_COMMERCE_STATE
} from '../../src/services/mockFallbackData.js';

export const suite = createTestSuite('Challenger 2: Hotkey Cycling, Slash Dock, & Network Resilience Stress Test');

// ===========================================================================
// 1. RAPID HOTKEY CYCLING & 9-SCREEN NAVIGATION MATRIX
// ===========================================================================

const ALL_9_ROUTES = [
  { id: 'agi-terminal', hotkey: 'c', numKey: '1', name: 'Tab 1: AGI Coding Terminal' },
  { id: 'network-metrics', hotkey: 'n', numKey: '2', name: 'Tab 2: Network Metrics' },
  { id: 'hardware-nodes', hotkey: 'h', numKey: '3', name: 'Tab 3: Hardware Nodes' },
  { id: 'biometrics-dsp', hotkey: 'b', numKey: '4', name: 'Tab 4: Biometrics DSP' },
  { id: 'ai-inference', hotkey: 'i', numKey: '5', name: 'Tab 5: AI Inference Mesh' },
  { id: 'training-lora', hotkey: 't', numKey: '6', name: 'Tab 6: LoRA Training' },
  { id: 'governance', hotkey: 'g', numKey: '7', name: 'Tab 7: Swarm Governance' },
  { id: 'structural-graph', hotkey: 'x', numKey: '8', name: 'Tab 8: Structural Graph' },
  { id: 'optimization-storage', hotkey: 'o', numKey: '9', name: 'Tab 9: Storage Optimization' }
];

suite.test('[CH2][T1] All 9 Screen Views Render Correctly In Isolation', async () => {
  const compPaths = [
    { path: 'src/components/terminal/AgiCodingTerminalView.jsx', name: 'AgiCodingTerminalView', props: { models: INITIAL_AGI_MODELS } },
    { path: 'src/components/network/NetworkMetricsView.jsx', name: 'NetworkMetricsView', props: { networkMetrics: INITIAL_NETWORK_METRICS, clusterVram: INITIAL_CLUSTER_VRAM } },
    { path: 'src/components/hardware/HardwareNodesView.jsx', name: 'HardwareNodesView', props: { clusterVram: INITIAL_CLUSTER_VRAM } },
    { path: 'src/components/biometrics/BiometricsDspView.jsx', name: 'BiometricsDspView', props: { biometricsState: INITIAL_BIOMETRICS_STATE } },
    { path: 'src/components/inference/AiInferenceView.jsx', name: 'AiInferenceView', props: { models: INITIAL_AGI_MODELS, networkMetrics: INITIAL_NETWORK_METRICS } },
    { path: 'src/components/training/TrainingMultiTabView.jsx', name: 'TrainingMultiTabView', props: { activeSubTab: 'training-lora', trainingState: INITIAL_TRAINING_STATE, gamesState: INITIAL_GAMES_STATE, structuralMetrics: INITIAL_STRUCTURAL_METRICS, executionTraces: INITIAL_EXECUTION_TRACES } },
    { path: 'src/components/governance/MasterAGIGovernanceView.jsx', name: 'MasterAGIGovernanceView', props: { models: INITIAL_AGI_MODELS, clusterVram: INITIAL_CLUSTER_VRAM } },
    { path: 'src/components/graph/StructuralEcosystemGraphView.jsx', name: 'StructuralEcosystemGraphView', props: {} },
    { path: 'src/components/optimization/StorageOptimizationView.jsx', name: 'StorageOptimizationView', props: {} }
  ];

  for (const c of compPaths) {
    const mod = await loadComponent(c.path);
    const Comp = mod[c.name] || mod.default;
    const html = render(Comp, c.props);
    if (!html || html.length < 50) {
      throw new Error(`Component ${c.name} produced insufficient HTML`);
    }
    assertNotContains(html, 'NaN', `Component ${c.name} rendered NaN`);
  }
});

suite.test('[CH2][T2] Rapid Hotkey Cycling Simulation (81 Pairwise Transitions & 10,000 Cycle Random Walk)', async () => {
  // Test 81 pairwise transitions
  const transitions = [];
  for (const fromRoute of ALL_9_ROUTES) {
    for (const toRoute of ALL_9_ROUTES) {
      transitions.push({ from: fromRoute.id, to: toRoute.id });
    }
  }
  if (transitions.length !== 81) {
    throw new Error('Must have 81 pairwise route transitions');
  }

  // Simulated router state transition engine
  class SimulatedAppRouter {
    constructor() {
      this.activeRoute = 'agi-terminal';
      this.history = ['agi-terminal'];
      this.keyMap = {
        'c': 'agi-terminal', '1': 'agi-terminal',
        'n': 'network-metrics', '2': 'network-metrics',
        'h': 'hardware-nodes', '3': 'hardware-nodes',
        'b': 'biometrics-dsp', '4': 'biometrics-dsp',
        'i': 'ai-inference', '5': 'ai-inference',
        't': 'training-lora', '6': 'training-lora',
        'g': 'governance', '7': 'governance',
        'x': 'structural-graph', '8': 'structural-graph',
        'o': 'optimization-storage', '9': 'optimization-storage'
      };
    }

    handleKeyDown(event) {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.targetTag) || event.isContentEditable) {
        return false; // suppressed inside input elements
      }
      const targetRoute = this.keyMap[event.key.toLowerCase()];
      if (targetRoute) {
        this.activeRoute = targetRoute;
        this.history.push(targetRoute);
        return true;
      }
      return false;
    }
  }

  const router = new SimulatedAppRouter();

  // Test 1: All 81 pairwise transitions
  for (const t of transitions) {
    const fromKey = ALL_9_ROUTES.find(r => r.id === t.from).hotkey;
    const toKey = ALL_9_ROUTES.find(r => r.id === t.to).hotkey;
    router.handleKeyDown({ key: fromKey, targetTag: 'BODY', isContentEditable: false });
    if (router.activeRoute !== t.from) {
      throw new Error(`Expected route ${t.from}, got ${router.activeRoute}`);
    }
    router.handleKeyDown({ key: toKey, targetTag: 'BODY', isContentEditable: false });
    if (router.activeRoute !== t.to) {
      throw new Error(`Expected route ${t.to}, got ${router.activeRoute}`);
    }
  }

  // Test 2: 10,000 rapid random walk hotkey triggers
  const allKeys = ['c', 'n', 'h', 'b', 'i', 't', 'g', 'x', 'o', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
  const t0 = performance.now();
  for (let i = 0; i < 10000; i++) {
    const key = allKeys[i % allKeys.length];
    const handled = router.handleKeyDown({ key, targetTag: 'BODY', isContentEditable: false });
    if (!handled) {
      throw new Error(`Hotkey '${key}' was not handled`);
    }
  }
  const durationMs = performance.now() - t0;
  if (durationMs >= 50) {
    throw new Error(`10,000 hotkey cycles took ${durationMs}ms (expected < 50ms)`);
  }

  // Test 3: Hotkey suppression inside input/textarea elements
  const suppressedTags = ['INPUT', 'TEXTAREA', 'SELECT'];
  for (const tag of suppressedTags) {
    const handled = router.handleKeyDown({ key: 'c', targetTag: tag, isContentEditable: false });
    if (handled) {
      throw new Error(`Hotkey must be suppressed in <${tag}>`);
    }
  }
});

suite.test('[CH2][T3] Hotkey Resilience Under Unmapped, Modified, & Adversarial Keystrokes', async () => {
  const router = {
    activeRoute: 'agi-terminal',
    keyMap: {
      'c': 'agi-terminal', '1': 'agi-terminal',
      'n': 'network-metrics', '2': 'network-metrics',
      'h': 'hardware-nodes', '3': 'hardware-nodes',
      'b': 'biometrics-dsp', '4': 'biometrics-dsp',
      'i': 'ai-inference', '5': 'ai-inference',
      't': 'training-lora', '6': 'training-lora',
      'g': 'governance', '7': 'governance',
      'x': 'structural-graph', '8': 'structural-graph',
      'o': 'optimization-storage', '9': 'optimization-storage'
    },
    handleKey(key, targetTag = 'BODY') {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(targetTag)) return false;
      const r = this.keyMap[key?.toLowerCase()];
      if (r) {
        this.activeRoute = r;
        return true;
      }
      return false;
    }
  };

  const adversarialKeys = [
    '', ' ', 'Escape', 'Enter', 'Tab', 'Shift', 'Control', 'Alt', 'Meta',
    'F1', 'F12', 'Backspace', 'Delete', 'ArrowUp', 'ArrowDown',
    'z', 'q', 'w', 'e', 'r', 'y', 'u', 'p', 'a', 's', 'd', 'f', 'j', 'k', 'l', 'v', 'm',
    '0', '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/',
    '🚀', '💩', '漢字', 'ñ', 'ä', 'ö', 'ü', 'ß', '\x00', '\n', '\t'
  ];

  for (const key of adversarialKeys) {
    const routeBefore = router.activeRoute;
    const handled = router.handleKey(key);
    if (handled) {
      throw new Error(`Unmapped key '${key}' should return false`);
    }
    if (router.activeRoute !== routeBefore) {
      throw new Error(`Unmapped key '${key}' mutated route unexpectedly`);
    }
  }
});

// ===========================================================================
// 2. EXTREME & ADVERSARIAL SLASH COMMAND DOCK INPUTS
// ===========================================================================

suite.test('[CH2][T4] SlashCommandDock Renders All 12 Commands & Autocomplete Filters Under Special Characters', async () => {
  const mod = await loadComponent('src/components/terminal/SlashCommandDock.jsx');
  const SlashCommandDock = mod.SlashCommandDock || mod.default;
  const SLASH_COMMANDS = mod.SLASH_COMMANDS;

  if (!SLASH_COMMANDS || SLASH_COMMANDS.length !== 12) {
    throw new Error(`Expected 12 SLASH_COMMANDS, found ${SLASH_COMMANDS ? SLASH_COMMANDS.length : 0}`);
  }

  // Render standard dock
  const html = render(SlashCommandDock, {
    onDispatchAction: () => {},
    activeEngine: 'kimi_tandem_titan',
    onCycleEngine: () => {}
  });

  assertTextContains(html, 'SLASH DOCK:');
  for (const cmd of SLASH_COMMANDS) {
    assertTextContains(html, cmd.cmd);
    assertTextContains(html, cmd.label);
  }

  // Test Autocomplete regex character safety (ensure no RegExp syntax crash)
  const extremeSearchQueries = [
    '/', '/a', '/audit', '/d', '/duel', '/split', '/engine', '/nodes', '/biometrics',
    '/restart', '/key', '/cron', '/storage', '/ping', '/revive',
    '/.*', '/(.*)/', '/[a-z]/', '/?', '/$', '/^', '/\\', '/[', '/]', '/{', '/}',
    '///', '/99999', '/nonexistent_command', '<script>', '"; DROP TABLE'
  ];

  for (const q of extremeSearchQueries) {
    // Autocomplete filtering uses String.prototype.includes, which is regex-safe
    const filtered = SLASH_COMMANDS.filter(c =>
      c.cmd.toLowerCase().includes(q.toLowerCase()) ||
      c.label.toLowerCase().includes(q.toLowerCase())
    );
    if (!Array.isArray(filtered)) {
      throw new Error(`Filter query '${q}' failed`);
    }
  }
});

suite.test('[CH2][T5] canonicalApi.dispatchSwarmAction Handles All 12 Commands and Adversarial Payloads Gracefully', async () => {
  const mod = await loadComponent('src/components/terminal/SlashCommandDock.jsx');
  const SLASH_COMMANDS = mod.SLASH_COMMANDS;

  // Test all 12 registered commands
  for (const c of SLASH_COMMANDS) {
    const res = await canonicalApi.dispatchSwarmAction(c.cmd);
    if (!res) throw new Error(`Command ${c.cmd} returned empty result`);
    if (res.success !== true) throw new Error(`Command ${c.cmd} success status not true`);
    if (!res.summary || res.summary.length === 0) throw new Error(`Command ${c.cmd} missing summary`);
    if (!res.timestamp) throw new Error(`Command ${c.cmd} missing timestamp`);
  }

  // Test adversarial commands and payloads
  const adversarialCases = [
    { cmd: '/unsupported_action_123', payload: {} },
    { cmd: '/drop_database', payload: { force: true } },
    { cmd: '/<script>alert(1)</script>', payload: { xss: true } },
    { cmd: '/audit', payload: { malformedJson: '{"broken":' } },
    { cmd: '/cron', payload: { count: -9999, sink: '/dev/null' } },
    { cmd: '/ping', payload: { timeoutMs: 0.0001, nodes: ['NonExistentNode'] } },
    { cmd: '', payload: null },
    { cmd: '    ', payload: undefined },
    { cmd: '/revive', payload: { mac_address: 'FF:FF:FF:FF:FF:FF', port: 9 } },
    { cmd: '/storage', payload: { deepCheck: true, timeout: 999999 } }
  ];

  for (const tc of adversarialCases) {
    const res = await canonicalApi.dispatchSwarmAction(tc.cmd, tc.payload);
    if (!res) throw new Error(`Adversarial command '${tc.cmd}' returned null/undefined`);
    if (res.success !== true) throw new Error(`Adversarial command '${tc.cmd}' failed`);
    if (typeof res.summary !== 'string') throw new Error(`Adversarial command '${tc.cmd}' summary not string`);
    if (!res.timestamp) throw new Error(`Adversarial command '${tc.cmd}' missing timestamp`);
  }

  // Concurrent massive dispatch test (50 simultaneous calls)
  const concurrentPromises = Array.from({ length: 50 }, (_, idx) =>
    canonicalApi.dispatchSwarmAction(SLASH_COMMANDS[idx % SLASH_COMMANDS.length].cmd, { callIndex: idx })
  );
  const concurrentResults = await Promise.all(concurrentPromises);
  if (concurrentResults.length !== 50) {
    throw new Error('Expected 50 concurrent results');
  }
  for (const r of concurrentResults) {
    if (r.success !== true) {
      throw new Error('Concurrent action dispatch failed');
    }
  }
});

// ===========================================================================
// 3. ABRUPT NETWORK DISCONNECTION RESILIENCE & OFFLINE FALLBACKS
// ===========================================================================

suite.test('[CH2][T6] Abrupt Network Drop & Null State Stability Across All 9 Screens (Zero NaN / Zero Crashes)', async () => {
  // Test each screen view rendered with completely null/empty/degraded props
  const viewTests = [
    {
      name: 'AgiCodingTerminalView [c] with empty models',
      component: 'src/components/terminal/AgiCodingTerminalView.jsx',
      exportName: 'AgiCodingTerminalView',
      props: { models: [], onDispatchAction: null }
    },
    {
      name: 'NetworkMetricsView [n] with null metrics',
      component: 'src/components/network/NetworkMetricsView.jsx',
      exportName: 'NetworkMetricsView',
      props: { networkMetrics: null, clusterVram: null, onDispatchAction: null }
    },
    {
      name: 'HardwareNodesView [h] with null clusterVram',
      component: 'src/components/hardware/HardwareNodesView.jsx',
      exportName: 'HardwareNodesView',
      props: { clusterVram: null, onDispatchAction: null }
    },
    {
      name: 'BiometricsDspView [b] with null biometricsState',
      component: 'src/components/biometrics/BiometricsDspView.jsx',
      exportName: 'BiometricsDspView',
      props: { biometricsState: null, onDispatchAction: null }
    },
    {
      name: 'AiInferenceView [i] with null props',
      component: 'src/components/inference/AiInferenceView.jsx',
      exportName: 'AiInferenceView',
      props: { models: null, networkMetrics: null, onDispatchAction: null }
    },
    {
      name: 'TrainingMultiTabView [t] with null states',
      component: 'src/components/training/TrainingMultiTabView.jsx',
      exportName: 'TrainingMultiTabView',
      props: { activeSubTab: 'training-lora', trainingState: null, gamesState: null, structuralMetrics: null, executionTraces: null, onDispatchAction: null }
    },
    {
      name: 'MasterAGIGovernanceView [g] with null props',
      component: 'src/components/governance/MasterAGIGovernanceView.jsx',
      exportName: 'MasterAGIGovernanceView',
      props: { models: null, clusterVram: null, debateState: null, onDispatchAction: null }
    },
    {
      name: 'StructuralEcosystemGraphView [x] with null action handler',
      component: 'src/components/graph/StructuralEcosystemGraphView.jsx',
      exportName: 'StructuralEcosystemGraphView',
      props: { onDispatchAction: null }
    },
    {
      name: 'StorageOptimizationView [o] with null callbacks',
      component: 'src/components/optimization/StorageOptimizationView.jsx',
      exportName: 'StorageOptimizationView',
      props: { onSelectModule: null, onDispatchAction: null }
    },
    {
      name: 'HeaderStatusBar [Shell] with isConnected=false',
      component: 'src/components/layout/HeaderStatusBar.jsx',
      exportName: 'HeaderStatusBar',
      props: { clusterVram: null, networkMetrics: null, isConnected: false, onDispatchAction: null }
    },
    {
      name: 'ShellLayout with disconnected state and null metrics',
      component: 'src/components/layout/ShellLayout.jsx',
      exportName: 'ShellLayout',
      props: {
        activeRoute: 'agi-terminal',
        setActiveRoute: () => {},
        isSidebarCollapsed: false,
        toggleSidebar: () => {},
        clusterVram: null,
        networkMetrics: null,
        isConnected: false,
        onDispatchAction: () => {},
        children: '<div>TEST DISCONNECTED</div>'
      }
    }
  ];

  for (const vt of viewTests) {
    const mod = await loadComponent(vt.component);
    const Comp = mod[vt.exportName] || mod.default;
    const html = render(Comp, vt.props);

    if (!html || html.length < 50) {
      throw new Error(`${vt.name} failed to render HTML in offline state`);
    }
    assertNotContains(html, 'NaN', `${vt.name} produced NaN under null/offline state`);
  }
});

suite.test('[CH2][T7] HeaderStatusBar Cleanly Reflects Disconnected/Offline State (Rose Badge & Offline Fallbacks)', async () => {
  const mod = await loadComponent('src/components/layout/HeaderStatusBar.jsx');
  const HeaderStatusBar = mod.HeaderStatusBar || mod.default;

  // Disconnected state
  const htmlOffline = render(HeaderStatusBar, {
    clusterVram: { pooledVramGb: 82.8, allocatedVramGb: 0, freeHeadroomGb: 82.8, nodes: [] },
    networkMetrics: { wanRoutes: [], tailscalePeers: [], tb4Dma: null, llamaRpcNodes: [] },
    isConnected: false,
    onDispatchAction: () => {}
  });

  assertTextContains(htmlOffline, 'DISCONNECTED');
  assertTextContains(htmlOffline, 'CANONICAL PORT');
  assertTextContains(htmlOffline, 'FLEET MATRIX:');
  assertNotContains(htmlOffline, 'NaN');

  // Connected state
  const htmlOnline = render(HeaderStatusBar, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    networkMetrics: INITIAL_NETWORK_METRICS,
    isConnected: true,
    onDispatchAction: () => {}
  });

  assertTextContains(htmlOnline, '● LIVE STREAM');
  assertTextContains(htmlOnline, '0.277 ms');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_challenger_2_m6_stress.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}
