import React, { useState, useEffect, useCallback } from 'react';
import { ShellLayout } from './components/layout/ShellLayout.jsx';
import { NetworkMetricsView } from './components/network/NetworkMetricsView.jsx';
import { HardwareNodesView } from './components/hardware/HardwareNodesView.jsx';
import { BiometricsDspView } from './components/biometrics/BiometricsDspView.jsx';
import { AgiCodingTerminalView } from './components/terminal/AgiCodingTerminalView.jsx';
import { AiInferenceView } from './components/inference/AiInferenceView.jsx';
import { TrainingMultiTabView } from './components/training/TrainingMultiTabView.jsx';
import { MasterAGIGovernanceView } from './components/governance/MasterAGIGovernanceView.jsx';
import { CanonicalLeaderboardView } from './components/leaderboard/CanonicalLeaderboardView.jsx';
import { StructuralEcosystemGraphView } from './components/graph/StructuralEcosystemGraphView.jsx';
import { ToolingCommerceView } from './components/tooling/ToolingCommerceView.jsx';
import { HardwareOptimizationView } from './components/optimization/HardwareOptimizationView.jsx';
import { SoftwareOptimizationView } from './components/optimization/SoftwareOptimizationView.jsx';
import { InternetOptimizationView } from './components/optimization/InternetOptimizationView.jsx';
import { StorageOptimizationView } from './components/optimization/StorageOptimizationView.jsx';
import { useLiveTelemetry } from './hooks/useLiveTelemetry.js';
import { useSwarmDebate } from './hooks/useSwarmDebate.js';
import { useNetworkMetrics } from './hooks/useNetworkMetrics.js';
import { canonicalApi } from './services/api.js';
import { INFERENCE_ENGINES } from './components/governance/InferenceEngineSelector.jsx';

/**
 * App - Winning Harmonized Production Shell (Milestone M5)
 * Unifies the Triple-Pillar Harmonized Architecture:
 * - Top Global Header: Track Alpha HeaderStatusBar (7-node pills L1-L7+GW, 108GB RAM / 82.8GB VRAM meter, 0.277ms TB4 DMA badge, WAN route)
 * - 9-Screen Tab Navigation Matrix:
 *   * Tab 1 [c]: Track Beta AgiCodingTerminalView (Chat + AST Buffer Editor + Live Diff + ASan Execution Console + Voice HUD)
 *   * Tab 2 [n]: Track Alpha NetworkMetricsView (WAN Failover, TB4 DMA card, SSH fleet table)
 *   * Tab 3 [h]: Track Alpha HardwareNodesView (7 compute nodes, thermals, dynamic RAM caps)
 *   * Tab 4 [b]: Track Alpha BiometricsDspView (512Hz Canvas ECG, Kamath 20% filter, 3D Kinematics)
 *   * Tab 5 [i]: Track Beta AiInferenceView (Distributed RPC sharding, 8-engine selector, abliterated models)
 *   * Tab 6 [t]: Track Gamma TrainingMultiTabView / LoRADistillationMonitorTab (24/7 LoRA loss curve steps 0-4800, PySpark AST)
 *   * Tab 7 [g]: Track Beta MasterAGIGovernanceView / TriOrchestratorDebatePanel (Accord gauge >0.98, topic injection)
 *   * Tab 8 [x]: Track Gamma StructuralEcosystemGraphView (14-node Sugiyama SVG topology with Tarjan SCC cycle badges)
 *   * Tab 9 [o]: Track Gamma StorageOptimizationView (Tri-Vault storage sync)
 * - Bottom Dock: Track Beta SlashCommandDock (/audit, /duel, /cron, /storage, /ping, /revive)
 *
 * Strict Rule #0 Zero-Mock fallbacks and non-blocking asynchronous telemetry streaming.
 */
export function App() {
  // Winning Default Primary Tab is Tab 1 [c] AGI Coding Terminal per canonical debate verdict
  const [activeRoute, setActiveRoute] = useState('agi-terminal');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [actionNotification, setActionNotification] = useState(null);
  const [activeEngine, setActiveEngine] = useState('auto');
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // Live Data States
  const [models, setModels] = useState([]);
  const [biometricsState, setBiometricsState] = useState(null);
  const [toolingState, setToolingState] = useState(null);
  const [trainingState, setTrainingState] = useState(null);
  const [gamesState, setGamesState] = useState(null);
  const [structuralMetrics, setStructuralMetrics] = useState(null);
  const [executionTraces, setExecutionTraces] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);

  // Non-blocking Asynchronous Hooks
  const { clusterVram, isConnected } = useLiveTelemetry(2500);
  const { networkMetrics } = useNetworkMetrics(2500);
  const {
    debateState,
    isStagnationModalOpen,
    triggerNextTurn,
    triggerCodeOff,
    resetDebate,
    harvestConsensusToLoRA,
    triggerStagnation,
    resolveStagnation,
    setIsStagnationModalOpen
  } = useSwarmDebate();

  // Load Initial API Data
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [m, bio, tl, tr, g, s, e, l] = await Promise.all([
          canonicalApi.getAGIModels(),
          canonicalApi.getBiometricsState(),
          canonicalApi.getToolingCommerceState(),
          canonicalApi.getTrainingState(),
          canonicalApi.getGamesState(),
          canonicalApi.getStructuralMetrics(),
          canonicalApi.getExecutionTraces(),
          canonicalApi.getLeaderboard()
        ]);
        if (isMounted) {
          if (m) setModels(m);
          if (bio) setBiometricsState(bio);
          if (tl) setToolingState(tl);
          if (tr) setTrainingState(tr);
          if (g) setGamesState(g);
          if (s) setStructuralMetrics(s);
          if (e) setExecutionTraces(e);
          if (l) setLeaderboard(l);
        }
      } catch (err) {
        console.warn('[App] Non-blocking fallback to zero-mock baseline:', err);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Hotkey navigation matrix (c, n, h, b, i, t, g, x, o)
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      // Don't intercept when user is typing in code editor, chat, prompt dock or inputs
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target?.tagName) || e.target?.isContentEditable) {
        return;
      }

      const key = e.key.toLowerCase();
      if (key === 'c' || key === '1') setActiveRoute('agi-terminal');
      else if (key === 'n' || key === '2') setActiveRoute('network-metrics');
      else if (key === 'h' || key === '3') setActiveRoute('hardware-nodes');
      else if (key === 'b' || key === '4') setActiveRoute('biometrics-dsp');
      else if (key === 'i' || key === '5') setActiveRoute('ai-inference');
      else if (key === 't' || key === '6') setActiveRoute('training-lora');
      else if (key === 'g' || key === '7') setActiveRoute('governance');
      else if (key === 'x' || key === '8') setActiveRoute('structural-graph');
      else if (key === 'o' || key === '9') setActiveRoute('optimization-storage');
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Hot-swap inference engine
  const handleCycleEngine = useCallback(() => {
    if (!INFERENCE_ENGINES || INFERENCE_ENGINES.length === 0) return;
    const currentIndex = INFERENCE_ENGINES.findIndex(eng => eng.id === activeEngine);
    const nextEngine = INFERENCE_ENGINES[(currentIndex + 1) % INFERENCE_ENGINES.length];
    setActiveEngine(nextEngine.id);
    handleDispatchAction(`/engine ${nextEngine.id}`);
  }, [activeEngine]);

  // Action Dispatcher Handler
  const handleDispatchAction = async (actionCommand) => {
    const t0 = performance.now();
    const result = await canonicalApi.dispatchSwarmAction(actionCommand);
    const measuredDuration = Math.max(4, Math.round(performance.now() - t0));
    setActionNotification(result);

    if (actionCommand.startsWith('/audit') || actionCommand.startsWith('/cron') || actionCommand.startsWith('/duel') || actionCommand.startsWith('/storage') || actionCommand.startsWith('/ping') || actionCommand.startsWith('/revive')) {
      const newTrace = {
        id: `trc-${Date.now().toString().slice(-4)}`,
        timestamp: new Date().toTimeString().split(' ')[0],
        action: `${actionCommand} - Swarm Command Execution`,
        initiator: 'Operator Aaron (UI Trigger)',
        status: 'COMPLETED_SUCCESS',
        durationMs: measuredDuration,
        nodesInvolved: ['Mac_Node', 'MacBook_Pro', 'Linux_Head_Node'],
        details: result.summary
      };
      setExecutionTraces(prev => [newTrace, ...prev]);
    }

    setTimeout(() => {
      setActionNotification(null);
    }, 4000);
  };

  const handleHarvestLoRA = () => {
    harvestConsensusToLoRA();
    handleDispatchAction('/cron');
  };

  return (
    <ShellLayout
      activeRoute={activeRoute}
      setActiveRoute={setActiveRoute}
      isSidebarCollapsed={isSidebarCollapsed}
      toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      clusterVram={clusterVram}
      networkMetrics={networkMetrics}
      isConnected={isConnected}
      onDispatchAction={handleDispatchAction}
      actionNotification={actionNotification}
      activeEngine={activeEngine}
      onCycleEngine={handleCycleEngine}
      selectedNodeId={selectedNodeId}
      onSelectNode={setSelectedNodeId}
    >
      {/* Tab 1 [c]: Master AGI Coding & Synthesis Terminal (Track Beta Core Cockpit) */}
      {activeRoute === 'agi-terminal' && (
        <AgiCodingTerminalView
          models={models}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 2 [n]: Bare-Metal Network Metrics & Multi-WAN Failover (Track Alpha) */}
      {activeRoute === 'network-metrics' && (
        <NetworkMetricsView
          networkMetrics={networkMetrics}
          clusterVram={clusterVram}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 3 [h]: 7-Layer Hardware Compute Nodes & Thermals (Track Alpha) */}
      {activeRoute === 'hardware-nodes' && (
        <HardwareNodesView
          clusterVram={clusterVram}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 4 [b]: Medical 512Hz Movesense ECG DSP & Kinematics (Track Alpha) */}
      {activeRoute === 'biometrics-dsp' && (
        <BiometricsDspView
          biometricsState={biometricsState}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 5 [i]: Local AI Inference Mesh & Distributed RPC Sharding (Track Beta) */}
      {activeRoute === 'ai-inference' && (
        <AiInferenceView
          models={models}
          networkMetrics={networkMetrics}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 6 [t]: Local AI Training & Multi-Tab Hub (Track Gamma) */}
      {(activeRoute === 'training-lora' ||
        activeRoute === 'training-games' ||
        activeRoute === 'training-metrics' ||
        activeRoute === 'training-traces') && (
        <TrainingMultiTabView
          activeSubTab={activeRoute}
          onSelectSubTab={setActiveRoute}
          trainingState={trainingState}
          gamesState={gamesState}
          structuralMetrics={structuralMetrics}
          executionTraces={executionTraces}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 7 [g]: Swarm Governance & Tri-Orchestrator Debate Panel (Track Beta) */}
      {activeRoute === 'governance' && (
        <MasterAGIGovernanceView
          models={models}
          clusterVram={clusterVram}
          debateState={debateState}
          onTriggerNextTurn={triggerNextTurn}
          onResetDebate={resetDebate}
          onHarvestLoRA={handleHarvestLoRA}
          onTriggerStagnation={triggerStagnation}
          isStagnationModalOpen={isStagnationModalOpen}
          onCloseStagnationModal={() => setIsStagnationModalOpen(false)}
          onResolveStagnation={resolveStagnation}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 8 [x]: 3D Structural Ecosystem Graph & Obsidian Knowledge Vault (Track Gamma) */}
      {activeRoute === 'structural-graph' && (
        <StructuralEcosystemGraphView
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Tab 9 [o]: Storage Optimization & Rule #6 Tri-Vault Health (Track Gamma) */}
      {activeRoute === 'optimization-storage' && (
        <StorageOptimizationView
          onSelectModule={setActiveRoute}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {/* Supporting Views & Sub-Shells */}
      {activeRoute === 'optimization-hardware' && (
        <HardwareOptimizationView
          clusterVram={clusterVram}
          onSelectModule={setActiveRoute}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {activeRoute === 'optimization-software' && (
        <SoftwareOptimizationView
          onSelectModule={setActiveRoute}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {activeRoute === 'optimization-internet' && (
        <InternetOptimizationView
          onSelectModule={setActiveRoute}
          onDispatchAction={handleDispatchAction}
        />
      )}

      {activeRoute === 'leaderboard' && (
        <CanonicalLeaderboardView leaderboard={leaderboard} />
      )}

      {activeRoute === 'tooling-commerce' && (
        <ToolingCommerceView
          toolingState={toolingState}
          onDispatchAction={handleDispatchAction}
        />
      )}
    </ShellLayout>
  );
}

export default App;
