import React, { useState, useEffect, useCallback } from 'react';
import { ShellLayout } from './components/layout/ShellLayout.jsx';
import { FrontDashboardChatEngine } from './components/dashboard/FrontDashboardChatEngine.jsx';
import { MembershipGateModal } from './components/commerce/MembershipGateModal.jsx';
import { NetworkMetricsView } from './components/network/NetworkMetricsView.jsx';
import { HardwareNodesView } from './components/hardware/HardwareNodesView.jsx';
import { BiometricsDspView } from './components/biometrics/BiometricsDspView.jsx';
import { BluetoothTerminalView } from './components/terminal/BluetoothTerminalView.jsx';
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
import { useMembership } from './hooks/useMembership.js';
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
  // Winning Default Primary View is Sovereign Chat Engine
  const [activeRoute, setActiveRoute] = useState('front-dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [actionNotification, setActionNotification] = useState(null);
  const [activeEngine, setActiveEngine] = useState('auto');
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // Shopify Membership & Token-Gated Feature State
  const {
    membership,
    tiers: membershipTiers,
    hasPermission,
    triggerGate,
    isGateModalOpen,
    setIsGateModalOpen,
    gateContext,
    setTierOverride,
    createCheckoutCart
  } = useMembership();

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

    // Poll biometrics data every 1s for live streaming
    const intervalId = setInterval(async () => {
      try {
        const bio = await canonicalApi.getBiometricsState();
        if (isMounted && bio) setBiometricsState(bio);
      } catch (err) {
        // ignore
      }
    }, 1000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
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
      if (key === '1' || key === 'd') setActiveRoute('front-dashboard');
      else if (key === 'c' || key === '2') {
        if (!hasPermission('full_ide_compiler')) {
          triggerGate('full_ide_compiler', 'Bluetooth Terminal & SPP Bridge', 'mesh_gym_master');
        } else {
          setActiveRoute('bluetooth-terminal');
        }
      }
      else if (key === 'n' || key === '3') setActiveRoute('network-metrics');
      else if (key === 'h' || key === '4') setActiveRoute('hardware-nodes');
      else if (key === 'b' || key === '5') {
        if (!hasPermission('movesense_512hz')) {
          triggerGate('movesense_512hz', 'Movesense Medical 512Hz ECG DSP', 'athlete_starter');
        } else {
          setActiveRoute('biometrics-dsp');
        }
      }
      else if (key === 'i' || key === '6') setActiveRoute('ai-inference');
      else if (key === 't' || key === '7') setActiveRoute('training-lora');
      else if (key === 'g' || key === '8') setActiveRoute('governance');
      else if (key === 'x' || key === '9') setActiveRoute('structural-graph');
      else if (key === 'o') setActiveRoute('optimization-storage');
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [hasPermission, triggerGate]);

  const handleOpenIdeFromChat = useCallback(() => {
    if (!hasPermission('full_ide_compiler')) {
      triggerGate('full_ide_compiler', 'Bluetooth Terminal & SPP Bridge', 'mesh_gym_master');
    } else {
      setActiveRoute('bluetooth-terminal');
    }
  }, [hasPermission, triggerGate]);

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
        nodesInvolved: ['Mac_Node', 'MacBook_Pro', 'Linux_Mini'],
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
      membership={membership}
      onOpenMembershipModal={() => setIsGateModalOpen(true)}
    >
      {/* Front Dashboard Default: Sovereign Chat Engine */}
      {activeRoute === 'front-dashboard' && (
        <FrontDashboardChatEngine
          models={models}
          membership={membership}
          onOpenIde={handleOpenIdeFromChat}
          onDispatchAction={handleDispatchAction}
          onOpenMembershipModal={() => setIsGateModalOpen(true)}
        />
      )}

      {/* Secondary Docked Tool: Bluetooth Terminal & Kai Morich SPP / BLE Interface */}
      {(activeRoute === 'bluetooth-terminal' || activeRoute === 'agi-terminal') && (
        <BluetoothTerminalView
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

      {/* Shopify Membership Token-Gated Unlock Modal */}
      <MembershipGateModal
        isOpen={isGateModalOpen}
        onClose={() => setIsGateModalOpen(false)}
        gateContext={gateContext}
        membership={membership}
        tiers={membershipTiers}
        onSelectTierOverride={setTierOverride}
        onCreateCheckoutCart={createCheckoutCart}
      />
    </ShellLayout>
  );
}

export default App;
