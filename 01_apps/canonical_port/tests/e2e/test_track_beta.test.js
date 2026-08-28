/**
 * Test Suite: Track Beta - Master AGI Coding Terminal, 8-Engine Inference & Tri-Orchestrator Debate
 * Version: 3.0.0-CANONICAL
 * Verifies Features 5, 6, 7, 8 across Tiers 1-4
 */

import { loadComponent, render, assertContains, assertTextContains, assertNotContains, createTestSuite } from './test_helpers.js';
import {
  INITIAL_AGI_MODELS,
  INITIAL_ABLITERATED_MODELS,
  INITIAL_NETWORK_METRICS,
  INITIAL_CLUSTER_VRAM,
  INITIAL_DEBATE_STATE,
  INITIAL_DYNAMIC_GOVERNANCE,
  INITIAL_CODING_PROFICIENCY_MATRIX
} from '../../src/services/mockFallbackData.js';
import { canonicalApi } from '../../src/services/api.js';

export const suite = createTestSuite('Track Beta: Chat/IDE Shell, 8-Engine Selector & Swarm Governance');

// ============================================================================
// FEATURE 5: Master AGI Coding Cockpit
// ============================================================================

suite.test('[F5][T1] AgiCodingTerminalView renders Screen 1 terminal, code editor buffer, and reasoner dropdown', async () => {
  const mod = await loadComponent('src/components/terminal/AgiCodingTerminalView.jsx');
  const html = render(mod.AgiCodingTerminalView, {
    models: INITIAL_AGI_MODELS,
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'Screen 1: Master AGI Coding & Synthesis Terminal');
  assertTextContains(html, 'Port 50052 RPC');
  assertTextContains(html, 'MODEL:');
  assertTextContains(html, 'Kimi 88B Titan (Dual-Node TB4 RPC)');
  assertTextContains(html, 'Qwen 3.8 Max (Edge Reasoner / Vision)');
  assertTextContains(html, 'VerifyZeroMockInvariants');
  assertTextContains(html, '0.277');
});

suite.test('[F5][T2] AstCodeBufferEditor renders multi-language presets (Go, Rust, Python, TS) and code metrics', async () => {
  const mod = await loadComponent('src/components/terminal/AstCodeBufferEditor.jsx');
  const html = render(mod.AstCodeBufferEditor, {
    codeBuffer: `package main\n\nfunc main() {\n    println("Zero-Mock Invariant Verified")\n}`,
    onChangeCodeBuffer: () => {},
    onExecuteCode: () => {},
    onCompareDiff: () => {},
    isExecuting: false,
    activeEngine: 'kimi_tandem'
  });

  assertTextContains(html, 'AST CODE BUFFER EDITOR');
  assertTextContains(html, 'LIVE BUFFER');
  assertTextContains(html, 'TB4 DMA Ring Buffer (Go)');
  assertTextContains(html, 'Kamath 20% ECG DSP (Rust)');
  assertTextContains(html, 'PySpark Monorepo AST (Python)');
  assertTextContains(html, 'Infinite Consensus Accord (TypeScript)');
  assertTextContains(html, 'ZERO-MOCK CERTIFIED');
  assertTextContains(html, 'LLVM ASAN READY');
});

suite.test('[F5][T3] LiveDiffInspector renders side-by-side AST comparison and delta stats', async () => {
  const mod = await loadComponent('src/components/terminal/LiveDiffInspector.jsx');
  const html = render(mod.LiveDiffInspector, {
    baselineCode: `func Probe() bool { return true }`,
    modifiedCode: `func Probe() bool { return rtt < 0.3 }`,
    onClose: () => {}
  });

  assertTextContains(html, 'LIVE AST DIFF INSPECTOR');
  assertTextContains(html, 'Split View');
  assertTextContains(html, 'Apply to Buffer');
  assertTextContains(html, 'Discard');
  assertTextContains(html, 'Tri-Vault Worktree Synchronized');
});

suite.test('[F5][T4] MultiAgentChatStream renders multi-turn dialogue with speaker badges and confidences', async () => {
  const mod = await loadComponent('src/components/terminal/MultiAgentChatStream.jsx');
  const html = render(mod.MultiAgentChatStream, {
    messages: [
      {
        id: 'msg-1',
        speaker: 'Kimi 88B Titan',
        speakerRole: 'Master Strategic Reasoner',
        content: 'Optimizing memory allocations across TB4 DMA bridge.',
        timestamp: '12:00:01',
        tokens: 28,
        latencyMs: 14
      },
      {
        id: 'msg-2',
        speaker: 'Qwen 3.8 Max',
        speakerRole: 'Edge Vision Critic',
        content: 'Zero memory leaks confirmed in Clang sandbox.',
        timestamp: '12:00:15',
        tokens: 34,
        latencyMs: 18
      }
    ],
    onSendMessage: () => {}
  });

  assertTextContains(html, 'MULTI-AGENT SWARM CHAT STREAM');
  assertTextContains(html, 'Kimi 88B Titan');
  assertTextContains(html, 'Master Strategic Reasoner');
  assertTextContains(html, 'Qwen 3.8 Max');
  assertTextContains(html, '28 tok');
  assertTextContains(html, '34 tok');
});

// ============================================================================
// FEATURE 6: 8-Engine Dynamic Inference Selector
// ============================================================================

suite.test('[F6][T1] InferenceEngineSelector renders all 8 canonical engines with layer and port badges', async () => {
  const mod = await loadComponent('src/components/governance/InferenceEngineSelector.jsx');
  const html = render(mod.InferenceEngineSelector, {
    activeEngine: 'auto',
    onSelectEngine: () => {}
  });

  assertTextContains(html, '8-ENGINE INFERENCE SELECTOR');
  assertTextContains(html, 'auto');
  assertTextContains(html, 'kimi_tandem');
  assertTextContains(html, 'llama_rpc');
  assertTextContains(html, 'qwen_local');
  assertTextContains(html, 'exo');
  assertTextContains(html, 'petals');
  assertTextContains(html, 'gemini');
  assertTextContains(html, 'cloudflare');
  assertTextContains(html, 'Auto-Routing Mesh Governor');
  assertTextContains(html, 'DYNAMIC ROUTER');
});

suite.test('[F6][T2] InferenceEngineSelector renders active engine specification details for Kimi TB4', async () => {
  const mod = await loadComponent('src/components/governance/InferenceEngineSelector.jsx');
  const html = render(mod.InferenceEngineSelector, {
    activeEngine: 'kimi_tandem',
    onSelectEngine: () => {}
  });

  assertTextContains(html, 'Kimi 88B Titan (Dual TB4 RPC)');
  assertTextContains(html, 'Port: 50052');
  assertTextContains(html, '46.0 GB VRAM');
  assertTextContains(html, '256K tokens');
  assertTextContains(html, '0.277ms (TB4 DMA)');
  assertTextContains(html, 'TB4 SHARDED');
});

suite.test('[F6][T3] AiInferenceView renders multi-prompt token/s benchmarks and abliterated registry', async () => {
  const mod = await loadComponent('src/components/inference/AiInferenceView.jsx');
  const html = render(mod.AiInferenceView, {
    models: INITIAL_AGI_MODELS,
    networkMetrics: INITIAL_NETWORK_METRICS,
    onDispatchAction: () => {}
  });

  assertTextContains(html, '3. LOCAL AI INFERENCE & DISTRIBUTED MESH SHARDING');
  assertTextContains(html, 'MULTI-PROMPT GENERATION BENCHMARKS (128 / 512 / 2048 TOKENS)');
  assertTextContains(html, 'F19 CERTIFIED');
  assertTextContains(html, 'Kimi 88B Tandem Titan');
  assertTextContains(html, 'Qwen 3.8 Max / 2.5-VL Edge');
  assertTextContains(html, 'ABLITERATED & UNCENSORED MODEL REGISTRY (ZERO-FILTER RED TEAMING)');
  assertTextContains(html, 'F20 ABLITERATED');
  assertTextContains(html, 'Llama-3.3-70B-Instruct-Abliterated');
  assertTextContains(html, 'Qwen-2.5-72B-Instruct-Abliterated');
  assertTextContains(html, 'BYPASSED (Rule #0)');
  assertTextContains(html, 'CLOUDFLARE WORKERS AI FRONTIER FALLBACK LAYER (F28)');
});

// ============================================================================
// FEATURE 7: Tri-Orchestrator AI Debate Panel
// ============================================================================

suite.test('[F7][T1] TriOrchestratorDebatePanel renders cosine accord gauge > 0.98 and debate turns', async () => {
  const mod = await loadComponent('src/components/governance/TriOrchestratorDebatePanel.jsx');
  const html = render(mod.TriOrchestratorDebatePanel, {
    debateState: INITIAL_DEBATE_STATE,
    onTriggerNextTurn: () => {},
    onResetDebate: () => {},
    onHarvestLoRA: () => {},
    onTriggerStagnation: () => {}
  });

  assertTextContains(html, 'TRI-ORCHESTRATOR LIVE DEBATE COUNCIL');
  assertTextContains(html, 'ACCORD: 0.984');
  assertTextContains(html, 'COSINE ACCORD GAUGE (Threshold >0.980)');
  assertTextContains(html, 'TOPIC:');
  assertTextContains(html, 'Kimi 88B Tandem Titan');
  assertTextContains(html, 'Strategic Orchestrator');
  assertTextContains(html, 'Qwen 3.8 Max');
  assertTextContains(html, 'Edge Reasoner & Vision Critic');
  assertTextContains(html, 'Gemini 3.1 Pro Cloud');
  assertTextContains(html, 'Verification Oracle');
  assertTextContains(html, 'Next Turn');
  assertTextContains(html, 'Code-Off');
  assertTextContains(html, 'Harvest LoRA');
  assertTextContains(html, 'Escalate');
});

suite.test('[F7][T2] MasterAGIGovernanceView renders dynamic governance reconvergence and AI currency', async () => {
  const mod = await loadComponent('src/components/governance/MasterAGIGovernanceView.jsx');
  const html = render(mod.MasterAGIGovernanceView, {
    models: INITIAL_AGI_MODELS,
    clusterVram: INITIAL_CLUSTER_VRAM,
    debateState: INITIAL_DEBATE_STATE,
    onTriggerNextTurn: () => {},
    onResetDebate: () => {},
    onHarvestLoRA: () => {},
    onTriggerStagnation: () => {},
    isStagnationModalOpen: false,
    onCloseStagnationModal: () => {},
    onResolveStagnation: () => {},
    onDispatchAction: () => {}
  });

  assertTextContains(html, 'MASTER AGI HOUSING & SWARM GOVERNANCE');
  assertTextContains(html, 'TRI-ORCHESTRATOR LIVE DEBATE COUNCIL');
  assertTextContains(html, 'ACCORD: 0.984');
  assertTextContains(html, 'DYNAMIC AGI GOVERNANCE, RAM TIERS & 100B+ APEX ROTATION');
  assertTextContains(html, '184,500 AGY');
});

suite.test('[F7][T3] StagnationEscalationModal renders escalation fallback and code-off benchmark options', async () => {
  const mod = await loadComponent('src/components/governance/StagnationEscalationModal.jsx');
  const html = render(mod.StagnationEscalationModal, {
    isOpen: true,
    onClose: () => {},
    onResolve: () => {},
    topic: 'Optimizing 7-Node Distributed LoRA Distillation'
  });

  assertTextContains(html, 'SWARM STAGNATION & DEADLOCK FAILSAFE');
  assertTextContains(html, 'Ratify Kimi 88B Titan Decision (Preferred Strategic Vector)');
  assertTextContains(html, 'Ratify Qwen 3.8 Max Decision (Low-Latency Edge Vector)');
  assertTextContains(html, 'Escalate to Gemini 3.1 Pro Cloud Oracle (Absolute Arbiter)');
});

// ============================================================================
// FEATURE 8: Slash Command Dispatcher Dock
// ============================================================================

suite.test('[F8][T1] SlashCommandDock renders all 10 quick command pills and interactive prompt line', async () => {
  const mod = await loadComponent('src/components/terminal/SlashCommandDock.jsx');
  const html = render(mod.SlashCommandDock, {
    onDispatchAction: () => {},
    activeEngine: 'auto',
    onCycleEngine: () => {}
  });

  assertTextContains(html, 'SLASH DOCK:');
  assertTextContains(html, '/audit Truth Audit');
  assertTextContains(html, '/duel FFA Duel');
  assertTextContains(html, '/split TB4 Shard');
  assertTextContains(html, '/engine Cycle Engine');
  assertTextContains(html, '/nodes Fleet Matrix');
  assertTextContains(html, '/biometrics 512Hz ECG');
  assertTextContains(html, '/restart_daemons Keepalive');
  assertTextContains(html, '/key Zero-Trust');
  assertTextContains(html, '/cron LoRA Harvest');
  assertTextContains(html, '/storage Tri-Vault');
  assertTextContains(html, 'Execute');
});

suite.test('[F8][T2] canonicalApi.dispatchSwarmAction returns authentic results for /audit, /cron, /storage', async () => {
  const auditRes = await canonicalApi.dispatchSwarmAction('/audit');
  assertContains(auditRes.summary, 'Swarm Truth Audit passed');
  assertTextContains(auditRes.summary, '0 simulated arrays detected');

  const cronRes = await canonicalApi.dispatchSwarmAction('/cron');
  assertContains(cronRes.summary, 'Harvested 48 new verified instruction pairs');

  const storageRes = await canonicalApi.dispatchSwarmAction('/storage');
  assertContains(storageRes.summary, 'Tri-Vault synchronization certified healthy');

  const pingRes = await canonicalApi.dispatchSwarmAction('/ping');
  assertContains(pingRes.summary, 'TB4 DMA Bridge RTT: 0.277 ms');
});

// Auto-run when executed directly via Node.js
if (process.argv[1] && process.argv[1].endsWith('test_track_beta.test.js')) {
  suite.run().then(res => {
    process.exit(res.failed === 0 ? 0 : 1);
  });
}
