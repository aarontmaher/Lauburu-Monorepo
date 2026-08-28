/**
 * Test Suite: Track Gamma - Structural Ecosystem Graph, 24/7 LoRA Distillation & Tri-Vault Storage
 * Version: 3.0.0-CANONICAL
 * Verifies Features 9, 10, 11, 12 across Tiers 1-4
 */

import assert from 'node:assert/strict';
import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';
import {
  INITIAL_MONOREPO_GRAPH_NODES,
  INITIAL_MONOREPO_GRAPH_LINKS,
  INITIAL_TRAINING_STATE,
  INITIAL_GAMES_STATE,
  INITIAL_STRUCTURAL_METRICS,
  INITIAL_EXECUTION_TRACES
} from '../../src/services/mockFallbackData.js';
import { runTarjanScc, computeSugiyamaLayout, generateCurvedLinkPath } from '../../src/components/graph/TarjanSccAnalyzer.js';

export const suite = createTestSuite('Track Gamma: Data Lake, Obsidian Graph & Continuous LoRA');

// ============================================================================
// FEATURE 9: 14-Node Structural Ecosystem Graph (F27 "The Obsidian View")
// ============================================================================

suite.test('[F9][T1] StructuralEcosystemGraphView renders 14 federated nodes and filter controls', async () => {
  const mod = await loadComponent('src/components/graph/StructuralEcosystemGraphView.jsx');
  const html = render(mod.StructuralEcosystemGraphView, {
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'The Obsidian View: 3D Structural Ecosystem Graph (F27)');
  assertTextContains(html, '14 FEDERATED NODES');
  assertTextContains(html, '17 DIRECTED EDGES');
  assertTextContains(html, 'Swarm Audit');
  assertTextContains(html, 'SUGIYAMA DIRECTED TOPOLOGY GRAPH');
});

suite.test('[F9][T2] SugiyamaTopologyCanvas renders directed graph with cycle detection and legend', async () => {
  const mod = await loadComponent('src/components/graph/SugiyamaTopologyCanvas.jsx');
  const html = render(mod.SugiyamaTopologyCanvas, {
    nodes: INITIAL_MONOREPO_GRAPH_NODES,
    links: INITIAL_MONOREPO_GRAPH_LINKS,
    selectedNode: INITIAL_MONOREPO_GRAPH_NODES[0],
    onSelectNode: () => {},
    zoomLevel: 1.0,
    onZoomChange: () => {},
    filterCategory: 'all',
    monetizationFilter: 'all',
    searchTerm: '',
    onResetView: () => {}
  });

  assertTextContains(html, 'SUGIYAMA DIRECTED TOPOLOGY GRAPH');
  assertTextContains(html, '14 NODES');
  assertTextContains(html, '17 DIRECTED EDGES');
  assertTextContains(html, 'TOPOLOGY LEGEND');
  assertTextContains(html, 'Commercial / Revenue-Generating Pipeline');
  assertTextContains(html, 'Tarjan SCC Cycle (AI Feedback Loop)');
  assertTextContains(html, 'RANK 0: ROOT CORE');
  assertTextContains(html, 'RANK 5: L7 OBSIDIAN KNOWLEDGE GRAPH');
});

suite.test('[F9][T3] TarjanSccAnalyzer correctly executes graph algorithms on monorepo topology', async () => {
  const sccResult = runTarjanScc(INITIAL_MONOREPO_GRAPH_NODES, INITIAL_MONOREPO_GRAPH_LINKS);
  assert(sccResult.sccList.length > 0, 'Must compute SCC decomposition');
  assert(sccResult.nodeDegreeMap.size === INITIAL_MONOREPO_GRAPH_NODES.length, 'Must compute in/out degrees for all nodes');

  const rootDegrees = sccResult.nodeDegreeMap.get('monorepo_root');
  assert(rootDegrees.outDegree >= 7, 'Root monorepo node must have >= 7 outgoing edges');

  const layout = computeSugiyamaLayout(INITIAL_MONOREPO_GRAPH_NODES, INITIAL_MONOREPO_GRAPH_LINKS);
  assert(layout.size === INITIAL_MONOREPO_GRAPH_NODES.length, 'Layout must position all 14 nodes');
  assert(layout.get('monorepo_root').y < layout.get('07_docs_arch').y, 'Root must be ranked higher than Docs');

  const path = generateCurvedLinkPath(100, 100, 300, 300, false);
  assert(path.startsWith('M 100 100 C'), 'Must generate smooth cubic Bézier SVG path');
});

// ============================================================================
// FEATURE 10: 24/7 Continuous LoRA Monitor
// ============================================================================

suite.test('[F10][T1] LoRADistillationMonitorTab renders real-time SVG loss curve and throughput metrics', async () => {
  const mod = await loadComponent('src/components/training/LoRADistillationMonitorTab.jsx');
  const html = render(mod.LoRADistillationMonitorTab, {
    trainingState: INITIAL_TRAINING_STATE,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '24/7 CONTINUOUS LoRA DISTILLATION MONITOR');
  assertTextContains(html, 'Real-time SFT / DPO Convergence Curve (Step 0 – 4800)');
  assertTextContains(html, 'CONVERGING');
  assertTextContains(html, '0.142');
  assertTextContains(html, '142.5 pairs/m');
  assertTextContains(html, '84,320');
  assertTextContains(html, 'lauburu-lora-moe-step-4800.safetensors');
  assertTextContains(html, 'LIVE HARVESTED INSTRUCTION PAIR STREAM');
  assertTextContains(html, 'TRUTH CERTIFIED');
});

suite.test('[F10][T2] LoraLossCurveCard renders isolated loss trajectory card', async () => {
  const mod = await loadComponent('src/components/training/LoraLossCurveCard.jsx');
  const html = render(mod.LoraLossCurveCard, {
    trainingState: INITIAL_TRAINING_STATE
  });

  assertTextContains(html, '24/7 CONTINUOUS LoRA DISTILLATION MONITOR');
  assertTextContains(html, 'Real-time SFT / DPO Convergence Curve (Step 0 – 4800)');
  assertTextContains(html, 'CONVERGING');
  assertContains(html, '<polyline');
});

// ============================================================================
// FEATURE 11: PySpark AST Metrics & FFA Arena
// ============================================================================

suite.test('[F11][T1] StructuralMetricsTab renders 3.29M LOC, 10,240 files and polyglot distribution', async () => {
  const mod = await loadComponent('src/components/training/StructuralMetricsTab.jsx');
  const html = render(mod.StructuralMetricsTab, {
    metrics: INITIAL_STRUCTURAL_METRICS,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'PySpark AST CODE METRICS CARD');
  assertTextContains(html, '3.29M LOC • 10,240 Files Across 32 Active Projects');
  assertTextContains(html, '✓ 0-MOCK CERTIFIED');
  assertTextContains(html, 'POLYGLOT CODEBASE DISTRIBUTION (3.29M LOC INDEX)');
  assertTextContains(html, 'Python');
  assertTextContains(html, '4,340 files (42.4%)');
  assertTextContains(html, 'TypeScript/JSX');
  assertTextContains(html, '2,930 files (28.6%)');
  assertTextContains(html, 'Rust / C++');
  assertTextContains(html, 'Dart / Kotlin');
});

suite.test('[F11][T2] ImplementedGamesArenaTab renders 13-Model FFA tournament standings and combat feed', async () => {
  const mod = await loadComponent('src/components/training/ImplementedGamesArenaTab.jsx');
  const html = render(mod.ImplementedGamesArenaTab, {
    gamesState: INITIAL_GAMES_STATE,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '13-Model Free-For-All Chaos Championship');
  assertTextContains(html, 'Round 14 of 50');
  assertTextContains(html, 'Current Leader: Kimi 88B Tandem Titan');
  assertTextContains(html, 'COMBATANT ARENA STANDINGS & ALLIANCES');
  assertTextContains(html, 'Kimi 88B Tandem Titan');
  assertTextContains(html, '1420 pts');
  assertTextContains(html, 'Titan Concordat');
  assertTextContains(html, 'Qwen 3.8 Max');
  assertTextContains(html, '1380 pts');
  assertTextContains(html, 'LIVE ARENA ACTION & BACKSTABBING FEED');
  assertTextContains(html, 'Trigger Arena Round');
});

suite.test('[F11][T3] TrainingMultiTabView switches across subtabs cleanly', async () => {
  const mod = await loadComponent('src/components/training/TrainingMultiTabView.jsx');
  const html = render(mod.TrainingMultiTabView, {
    activeSubTab: 'training-lora',
    onSelectSubTab: () => {},
    trainingState: INITIAL_TRAINING_STATE,
    gamesState: INITIAL_GAMES_STATE,
    structuralMetrics: INITIAL_STRUCTURAL_METRICS,
    executionTraces: INITIAL_EXECUTION_TRACES,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'LOCAL AI TRAINING & MULTI-TAB HUB');
  assertTextContains(html, '1. LoRA Distillation Monitor');
  assertTextContains(html, '2. Implemented Games Arena');
  assertTextContains(html, '3. Structural AST Metrics');
  assertTextContains(html, '4. Execution Action Traces');
});

// ============================================================================
// FEATURE 12: Tri-Vault Storage Optimization View
// ============================================================================

suite.test('[F12][T1] StorageOptimizationView renders Rule #6 Tri-Vault storage invariant health and NVMe headroom', async () => {
  const mod = await loadComponent('src/components/optimization/StorageOptimizationView.jsx');
  const html = render(mod.StorageOptimizationView, {
    onSelectModule: () => {},
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'STORAGE ANALYSIS & TRI-VAULT SYNCHRONIZER');
  assertTextContains(html, 'MOUNTED SUBSYSTEM: StorageAnalysisHub & Tri-Vault DFS Governor');
  assertTextContains(html, 'Obsidian Knowledge Vault');
  assertTextContains(html, 'PySpark & Big Data Lake');
  assertTextContains(html, 'GitHub Monorepo Worktree');
  assertTextContains(html, 'HEALTHY');
  assertTextContains(html, 'HOST NVMe HEADROOM (RULE 6.1 INVARIANT)');
  assertTextContains(html, '≥ 10.0 GB Required | 148.2 GB Free');
  assertTextContains(html, 'Sync All Vaults');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_track_gamma.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}
