/**
 * Test Suite: Zero-Mock & Offline Fallback Conformance (Rule #0)
 * Version: 3.0.0-CANONICAL
 * Verifies that all components cleanly render authentic specification values or fallback states
 * when offline or receiving null telemetry without throwing errors or generating simulated/fake arrays.
 */

import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';

export const suite = createTestSuite('Zero-Mock & Offline Fallback Conformance (Rule #0)');

// ============================================================================
// ZERO-MOCK CONFORMANCE & OFFLINE DEGRADATION TESTS
// ============================================================================

suite.test('[ZM][T1] HeaderStatusBar renders rose indicator badge when disconnected without crash', async () => {
  const mod = await loadComponent('src/components/layout/HeaderStatusBar.jsx');
  const html = render(mod.HeaderStatusBar, {
    isConnected: false,
    clusterVram: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'CANONICAL PORT');
  assertTextContains(html, 'v3.0-CANONICAL');
  assertTextContains(html, 'MASTER: KIMI 88B TITAN');
  assertTextContains(html, 'EDGE: QWEN 3.8 MAX');
  assertContains(html, 'var(--accent-rose)');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

suite.test('[ZM][T2] TB4DmaBridgeCard renders clean fallback state when metrics are empty or null', async () => {
  const mod = await loadComponent('src/components/network/TB4DmaBridgeCard.jsx');
  const html = render(mod.TB4DmaBridgeCard, {
    metrics: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '10GBPS THUNDERBOLT 4 PCIE DMA BRIDGE');
  assertTextContains(html, '0.277ms RTT');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

suite.test('[ZM][T3] BiometricsDspView handles null state gracefully with authentic specification baseline', async () => {
  const mod = await loadComponent('src/components/biometrics/BiometricsDspView.jsx');
  const html = render(mod.BiometricsDspView, {
    biometricsState: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '2. MEDICAL-GRADE BIOMETRICS & KINEMATICS DSP');
  assertTextContains(html, '512Hz ECG / ZONE 2 DFA-alpha1');
  assertTextContains(html, '31 OPML Grappling Nodes');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

suite.test('[ZM][T4] LoraLossCurveCard handles null training state using authentic specification defaults', async () => {
  const mod = await loadComponent('src/components/training/LoraLossCurveCard.jsx');
  const html = render(mod.LoraLossCurveCard, {
    trainingState: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '24/7 CONTINUOUS LoRA DISTILLATION MONITOR');
  assertTextContains(html, 'CURRENT LOSS');
  assertTextContains(html, '0.142');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

suite.test('[ZM][T5] PySparkAstCard handles null structural metrics without throwing exceptions', async () => {
  const mod = await loadComponent('src/components/training/PySparkAstCard.jsx');
  const html = render(mod.PySparkAstCard, {
    structuralMetrics: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'PySpark AST CODE METRICS CARD');
  assertTextContains(html, '3.29M LOC • 10,240 Files Across 32 Active Projects');
  assertTextContains(html, '✓ 0-MOCK CERTIFIED');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

suite.test('[ZM][T6] HardwareNodesView renders cleanly with empty or partial hardware node array', async () => {
  const mod = await loadComponent('src/components/hardware/HardwareNodesView.jsx');
  const html = render(mod.HardwareNodesView, {
    nodes: [],
    clusterVram: null,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'LAYER 1: COMPUTE HARDWARE & 7-NODE MESH MATRIX');
  assertTextContains(html, '108.0 GB System RAM • 82.8 GB Pooled VRAM');
  assertNotContains(html, 'undefined');
  assertNotContains(html, 'NaN');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_zero_mock.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}
