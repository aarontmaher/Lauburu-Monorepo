/**
 * Test Suite: Track Alpha - NOC, Hardware Matrix & Biometrics DSP
 * Version: 3.0.0-CANONICAL
 * Verifies Features 1, 2, 3, 4 across Tiers 1-4
 */

import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';
import {
  INITIAL_NETWORK_METRICS,
  INITIAL_CLUSTER_VRAM,
  INITIAL_BIOMETRICS_STATE
} from '../../src/services/mockFallbackData.js';

export const suite = createTestSuite('Track Alpha: NOC Dashboard & Hardware Matrix');

// ============================================================================
// FEATURE 1: Global Header & 7-Node Pill Matrix
// ============================================================================

suite.test('[F1][T1] Global HeaderStatusBar renders branding, master AGI badges, and TB4 latency', async () => {
  const mod = await loadComponent('src/components/layout/HeaderStatusBar.jsx');
  const html = render(mod.HeaderStatusBar, {
    activeRoute: 'network-metrics',
    clusterVram: INITIAL_CLUSTER_VRAM,
    isConnected: true,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'CANONICAL PORT');
  assertTextContains(html, 'v3.0-CANONICAL');
  assertTextContains(html, 'KIMI 88B TITAN');
  assertTextContains(html, 'QWEN 3.8 MAX');
  assertTextContains(html, '0.277 ms');
  assertTextContains(html, '482 Mbps');
  assertTextContains(html, 'POOLED VRAM:');
  assertTextContains(html, '61.4 / 82.8 GB');
  assertTextContains(html, '/audit');
  assertTextContains(html, '/storage');
  assertTextContains(html, '/ping');
});

suite.test('[F1][T2] HeaderStatusBar disconnected state displays rose indicator badge', async () => {
  const mod = await loadComponent('src/components/layout/HeaderStatusBar.jsx');
  const html = render(mod.HeaderStatusBar, {
    activeRoute: 'network-metrics',
    clusterVram: { allocatedVramGb: 0, pooledVramGb: 82.8 },
    isConnected: false,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'CANONICAL PORT');
  assertContains(html, 'var(--accent-rose)');
});

suite.test('[F1][T3] SidebarNav renders 7-node footer and primary routing sections', async () => {
  const mod = await loadComponent('src/components/layout/SidebarNav.jsx');
  const html = render(mod.SidebarNav, {
    activeRoute: 'network-metrics',
    setActiveRoute: () => {},
    isSidebarCollapsed: false,
    toggleSidebar: () => {}
  });

  assertTextContains(html, 'LAUBURU MESH');
  assertTextContains(html, '0. BARE-METAL NETWORKING (PRIMARY)');
  assertTextContains(html, '1. HARDWARE & NODES');
  assertTextContains(html, '2. MEDICAL BIOMETRICS & DSP');
  assertTextContains(html, '3. LOCAL AI INFERENCE & SYNTHESIS');
  assertTextContains(html, '4. LOCAL AI TRAINING & GAMES');
  assertTextContains(html, '5. MASTER AGI GOVERNANCE');
  assertTextContains(html, '6. TOOLING & COMMERCE');
  assertTextContains(html, '7 / 7 NODES ONLINE');
  assertTextContains(html, 'Mac_Node (L1 Host)');
});

suite.test('[F1][T4] ShellLayout renders action notification banner when command is dispatched', async () => {
  const mod = await loadComponent('src/components/layout/ShellLayout.jsx');
  const html = render(mod.ShellLayout, {
    activeRoute: 'network-metrics',
    setActiveRoute: () => {},
    isSidebarCollapsed: false,
    toggleSidebar: () => {},
    clusterVram: INITIAL_CLUSTER_VRAM,
    isConnected: true,
    actionNotification: {
      summary: 'Swarm Truth Audit passed with 0.998 score.',
      timestamp: '12:00:00'
    },
    children: null
  });

  assertTextContains(html, '[ACTION DISPATCHED]');
  assertTextContains(html, 'Swarm Truth Audit passed with 0.998 score.');
  assertTextContains(html, '12:00:00');
});

// ============================================================================
// FEATURE 2: Layer 0 Network & TB4 DMA Dashboard
// ============================================================================

suite.test('[F2][T1] NetworkMetricsView renders full WAN failover matrix and TB4 DMA card', async () => {
  const mod = await loadComponent('src/components/network/NetworkMetricsView.jsx');
  const html = render(mod.NetworkMetricsView, {
    networkMetrics: INITIAL_NETWORK_METRICS,
    clusterVram: INITIAL_CLUSTER_VRAM,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'LAYER 0: FULL BARE-METAL NETWORKING & 7-NODE MESH TELEMETRY');
  assertTextContains(html, '7 / 7 NODES');
  assertTextContains(html, '482 Mbps');
  assertTextContains(html, '48 Mbps');
  assertTextContains(html, '0.277 ms');
  assertTextContains(html, '-ts 28,28,24');
  assertTextContains(html, 'p01_tb4_dma');
  assertTextContains(html, 'en0_wifi_wan');
  assertTextContains(html, 'utun1_tailscale');
  assertTextContains(html, 'en6_usb_tether');
});

suite.test('[F2][T2] NetworkMetricsView verifies all 8 SSH Fleet node endpoints (L1-GW)', async () => {
  const mod = await loadComponent('src/components/network/NetworkMetricsView.jsx');
  const html = render(mod.NetworkMetricsView, {
    networkMetrics: INITIAL_NETWORK_METRICS,
    clusterVram: INITIAL_CLUSTER_VRAM,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'SSH DAEMON FLEET TELEMETRY (PORT 22 / 8022)');
  assertTextContains(html, 'F18 CERTIFIED');
  assertTextContains(html, '127.0.0.1');
  assertTextContains(html, '192.168.8.127');
  assertTextContains(html, '192.168.8.224');
  assertTextContains(html, '192.168.8.173');
  assertTextContains(html, '192.168.8.222');
  assertTextContains(html, '192.168.8.160');
  assertTextContains(html, '192.168.8.158');
  assertTextContains(html, '192.168.8.1');
  assertTextContains(html, '8022');
  assertTextContains(html, 'OPEN');
});

suite.test('[F2][T3] TB4DmaBridgeCard renders 10Gbps PCIe DMA metrics and zero-copy state', async () => {
  const mod = await loadComponent('src/components/network/TB4DmaBridgeCard.jsx');
  const html = render(mod.TB4DmaBridgeCard, {
    tb4Dma: INITIAL_NETWORK_METRICS.tb4Dma
  });

  assertTextContains(html, '10GBPS THUNDERBOLT 4 PCIE DMA BRIDGE');
  assertTextContains(html, '169.254.187.138');
  assertTextContains(html, '0.277 ms');
  assertTextContains(html, '38.4 Gbps');
  assertTextContains(html, 'CONNECTED');
});

suite.test('[F2][T4] TailscaleMeshCard renders WireGuard overlay peers across 7 layers', async () => {
  const mod = await loadComponent('src/components/network/TailscaleMeshCard.jsx');
  const html = render(mod.TailscaleMeshCard, {
    tailscalePeers: INITIAL_NETWORK_METRICS.tailscalePeers
  });

  assertTextContains(html, 'TAILSCALE WIREGUARD MESH OVERLAY');
  assertTextContains(html, '100.119.199.76');
  assertTextContains(html, '100.103.212.21');
  assertTextContains(html, '100.101.39.98');
  assertTextContains(html, '100.81.92.125');
  assertTextContains(html, '100.93.158.96');
  assertTextContains(html, '100.73.38.87');
  assertTextContains(html, '100.84.40.95');
  assertTextContains(html, 'Direct WireGuard');
});

suite.test('[F2][T5] LlamaRpcLatencyCard renders 3-way distributed tensor sharding', async () => {
  const mod = await loadComponent('src/components/network/LlamaRpcLatencyCard.jsx');
  const html = render(mod.LlamaRpcLatencyCard, {
    llamaRpcNodes: INITIAL_NETWORK_METRICS.llamaRpcNodes,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'LLAMA.CPP GGML-RPC NODE LATENCY MATRIX (PORT 50052)');
  assertTextContains(html, '100.101.39.98:50052');
  assertTextContains(html, '169.254.187.138:50052');
  assertTextContains(html, '127.0.0.1:50052');
  assertTextContains(html, '28 layers');
  assertTextContains(html, '24 layers');
  assertTextContains(html, '13.5 GB');
  assertTextContains(html, '12.0 GB');
});

// ============================================================================
// FEATURE 3: Layer 1 Hardware Compute Matrix
// ============================================================================

suite.test('[F3][T1] HardwareNodesView renders 108GB RAM / 82.8GB VRAM cluster overview', async () => {
  const mod = await loadComponent('src/components/hardware/HardwareNodesView.jsx');
  const html = render(mod.HardwareNodesView, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'LAYER 1: COMPUTE HARDWARE & 7-NODE MESH MATRIX');
  assertTextContains(html, '108.0 GB System RAM');
  assertTextContains(html, '82.8 GB Pooled VRAM');
  assertTextContains(html, 'Dynamic RAM Ceilings');
});

suite.test('[F3][T2] HardwareNodesView verifies all 7 physical node specifications and headless scores', async () => {
  const mod = await loadComponent('src/components/hardware/HardwareNodesView.jsx');
  const html = render(mod.HardwareNodesView, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'Mac_Node');
  assertTextContains(html, 'MacBook_Air');
  assertTextContains(html, 'MacBook_Pro');
  assertTextContains(html, 'Linux_Head_Node');
  assertTextContains(html, 'Pixel_10_Pro_XL');
  assertTextContains(html, 'Samsung_S20');
  assertTextContains(html, 'Linux_Tablet');
  assertTextContains(html, 'GL.iNet Gateway');
  assertTextContains(html, '#1 (Score: 95)');
  assertTextContains(html, '#8 (Score: 100)');
});

suite.test('[F3][T3] HardwareOptimizationView renders Sentinel HUD and dynamic limits', async () => {
  const mod = await loadComponent('src/components/optimization/HardwareOptimizationView.jsx');
  const html = render(mod.HardwareOptimizationView, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    onSelectModule: () => {},
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'HARDWARE ANALYSIS & DEVICE SENTINEL');
  assertTextContains(html, 'LiveDeviceSentinelHUD (Port 18802)');
  assertTextContains(html, 'MOVESENSE BLE 512Hz ECG & DSP SENTINEL');
});

// ============================================================================
// FEATURE 4: Layer 2 Biometrics DSP HUD
// ============================================================================

suite.test('[F4][T1] BiometricsDspView renders 512Hz ECG, Kamath 20% filter, and Zone 2 status', async () => {
  const mod = await loadComponent('src/components/biometrics/BiometricsDspView.jsx');
  const html = render(mod.BiometricsDspView, {
    biometricsState: INITIAL_BIOMETRICS_STATE,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '2. MEDICAL-GRADE BIOMETRICS & KINEMATICS DSP');
  assertTextContains(html, '138.4 BPM');
  assertTextContains(html, 'ZONE_2_OPTIMAL');
  assertTextContains(html, '42.8 ms');
  assertTextContains(html, '0.75');
  assertTextContains(html, '118/76 mmHg');
  assertTextContains(html, 'Movesense-Medical-230950000');
  assertTextContains(html, '512 Hz');
  assertTextContains(html, '28.5 dB');
  assertTextContains(html, 'Kamath 20% Filter: ACTIVE (Rejection: 1.42%)');
});

suite.test('[F4][T2] BiometricsDspView renders 3D Spatial Grappling Kinematics with 31 OPML nodes', async () => {
  const mod = await loadComponent('src/components/biometrics/BiometricsDspView.jsx');
  const html = render(mod.BiometricsDspView, {
    biometricsState: INITIAL_BIOMETRICS_STATE,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '3D SPATIAL GRAPPLING KINEMATICS (31 OPML NODES)');
  assertTextContains(html, 'Side Control');
  assertTextContains(html, '31 Nodes | 57 Transitions');
  assertTextContains(html, '8.0 x 8.0 x 2.5 m');
  assertTextContains(html, 'Straight Armbar, Kimura, RNC');
});

// ============================================================================
// PROTOTYPE: Track Alpha Flagship Bento-Box NOC Dashboard
// ============================================================================

suite.test('[Alpha][P1] TrackAlphaNocDashboard renders bento-box (30/45/25), 7-node pill matrix, and RAM/VRAM gauge', async () => {
  const mod = await loadComponent('src/prototypes/TrackAlphaNocDashboard.jsx');
  const html = render(mod.TrackAlphaNocDashboard, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    networkMetrics: INITIAL_NETWORK_METRICS,
    biometricsState: INITIAL_BIOMETRICS_STATE,
    isConnected: true,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'TRACK ALPHA: NOC & HARDWARE SENTINEL');
  assertTextContains(html, 'HIGH-DENSITY BENTO (30/45/25)');
  assertTextContains(html, 'RULE #0 ZERO-MOCK CERTIFIED');
  assertTextContains(html, 'POOLED VRAM:');
  assertTextContains(html, '61.4 / 82.8 GB');
  assertTextContains(html, '108GB RAM');
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
  assertTextContains(html, 'MOVESENSE 512Hz ECG WAVEFORM');
  assertTextContains(html, 'DAEMON & DOCKER HUD');
  assertTextContains(html, 'Self-Healing Hub (Port 18802)');
});

suite.test('[Alpha][P2] TrackAlphaNocDashboard renders clean Rule #0 fallbacks on offline states', async () => {
  const mod = await loadComponent('src/prototypes/TrackAlphaNocDashboard.jsx');
  const html = render(mod.TrackAlphaNocDashboard, {
    clusterVram: {
      pooledVramGb: 82.8,
      totalRamGb: 108.0,
      allocatedVramGb: 0,
      nodes: [
        { nodeId: 'L1_Mac_Node', name: 'Mac_Node', role: 'Host', ip: '--', tailscaleIp: '--', status: 'OFFLINE', cpuPercent: null, tempC: null, latencyMs: null, ramTotalGb: 24, aiVramCapGb: 21.6, usedVramGb: 0 }
      ]
    },
    networkMetrics: {
      wanRoutes: [],
      tb4Dma: { status: 'OFFLINE', rttMs: null },
      llamaRpcNodes: [],
      tailscalePeers: [],
      sshFleet: []
    },
    biometricsState: {
      heartRateBpm: null,
      rmssdMs: null,
      dfaAlpha1: undefined,
      pttBloodPressure: { systolicMmhg: null }
    },
    isConnected: false,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'TRACK ALPHA: NOC & HARDWARE SENTINEL');
  assertTextContains(html, 'OFFLINE');
  assertTextContains(html, '--');
});

suite.test('[Alpha][P3] NodeCard, PooledMemoryGauge, and ThermalGovernorCard render correctly', async () => {
  const nodeCardMod = await loadComponent('src/components/hardware/NodeCard.jsx');
  const memGaugeMod = await loadComponent('src/components/hardware/PooledMemoryGauge.jsx');
  const thermMod = await loadComponent('src/components/hardware/ThermalGovernorCard.jsx');

  const nodeHtml = render(nodeCardMod.NodeCard, {
    node: INITIAL_CLUSTER_VRAM.nodes[0],
    onDispatchAction: () => {}
  });
  assertTextContains(nodeHtml, 'L1');
  assertTextContains(nodeHtml, 'Mac_Node');
  assertTextContains(nodeHtml, 'CPU USAGE');
  assertTextContains(nodeHtml, 'THERMALS');

  const memHtml = render(memGaugeMod.PooledMemoryGauge, {
    clusterVram: INITIAL_CLUSTER_VRAM,
    onDispatchAction: () => {}
  });
  assertTextContains(memHtml, 'POOLED VRAM & DYNAMIC RAM GOVERNOR');
  assertTextContains(memHtml, '108.0 GB Pooled Physical RAM');
  assertTextContains(memHtml, '82.8 GB Pooled AI VRAM');

  const thermHtml = render(thermMod.ThermalGovernorCard, {
    nodes: INITIAL_CLUSTER_VRAM.nodes
  });
  assertTextContains(thermHtml, 'CLUSTER THERMAL SENTINEL & FAN GOVERNOR');
  assertTextContains(thermHtml, 'AVG CLUSTER TEMP');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_track_alpha.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}

