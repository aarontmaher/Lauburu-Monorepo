import React from 'react';
import { AGIModelRosterCard } from './AGIModelRosterCard.jsx';
import { ClusterVRAMGauge } from './ClusterVRAMGauge.jsx';
import { TriOrchestratorDebatePanel } from './TriOrchestratorDebatePanel.jsx';
import { StagnationEscalationModal } from './StagnationEscalationModal.jsx';
import { SwarmActionDispatcherBar } from './SwarmActionDispatcherBar.jsx';
import { INITIAL_DYNAMIC_GOVERNANCE } from '../../services/mockFallbackData.js';

export function MasterAGIGovernanceView({
  models,
  clusterVram,
  debateState,
  onTriggerNextTurn,
  onResetDebate,
  onHarvestLoRA,
  onTriggerStagnation,
  isStagnationModalOpen,
  onCloseStagnationModal,
  onResolveStagnation,
  onDispatchAction
}) {
  const dynGov = INITIAL_DYNAMIC_GOVERNANCE;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* View Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>🧠 MASTER AGI HOUSING & SWARM GOVERNANCE</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Central orchestrator housing Kimi 88B Tandem Titan & Qwen 3.8 Max across 82.8 GB pooled VRAM with Infinite Consensus.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-emerald">AIR-GAP OPERATIONAL</span>
          <span className="badge badge-cyan">ZERO-MOCK CERTIFIED</span>
        </div>
      </div>

      {/* AGI Model Roster Grid */}
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '8px' }}>
          ACTIVE MASTER AGI ROSTER (R1 CONTRACT)
        </div>
        <div className="grid-cols-2">
          {(models || []).map((model) => (
            <AGIModelRosterCard key={model.id} model={model} />
          ))}
        </div>
      </div>

      {/* Pooled 82.8 GB VRAM Sharding Matrix */}
      <ClusterVRAMGauge clusterVram={clusterVram} />

      {/* Dynamic AGI Governance, RAM Tiers & 100B+ Rotation (F21/F26) */}
      <div className="cyber-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-purple)' }}>
            DYNAMIC AGI GOVERNANCE, RAM TIERS & 100B+ APEX ROTATION
          </span>
          <span className="badge badge-purple">FAILOVER: {dynGov.failoverLatencyMs} ms</span>
        </div>

        {/* Dynamic Metrics Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>MONOLITHIC RE-CONVERGENCE</span>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '2px' }}>
              ● {dynGov.reconvergenceStatus}
            </div>
          </div>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>AI CURRENCY / AGY TOKENS</span>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-amber)', marginTop: '2px' }}>
              {dynGov.aiCurrencyTracker.agyTokensIssued.toLocaleString()} AGY ({dynGov.aiCurrencyTracker.freedomOfChoiceModelsCount} Autonomous Models)
            </div>
          </div>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>24/7 LORA CYCLES AWARDED</span>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '2px' }}>
              {dynGov.aiCurrencyTracker.loraTrainingCyclesAwarded} Cycles ({dynGov.aiCurrencyTracker.smolagentRightsActive} Active Rights)
            </div>
          </div>
        </div>

        {/* 100B+ Apex Rotation Schedule */}
        <div style={{ marginTop: '6px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
            100B+ APEX ROTATION SCHEDULE:
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '8px' }}>
            {dynGov.apexRotationSchedule.map((cand, idx) => (
              <div key={idx} style={{ background: 'var(--bg-secondary)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{cand.candidate}</span>
                <span className={`badge ${cand.status.includes('ACTIVE') ? 'badge-emerald' : 'badge-amber'}`} style={{ fontSize: '0.65rem' }}>
                  {cand.status} ({cand.eloDelta})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tri-Orchestrator Debate Console */}
      <TriOrchestratorDebatePanel
        debateState={debateState}
        onTriggerNextTurn={onTriggerNextTurn}
        onResetDebate={onResetDebate}
        onHarvestLoRA={onHarvestLoRA}
        onTriggerStagnation={onTriggerStagnation}
      />

      {/* 1-Click Action Dispatcher */}
      <SwarmActionDispatcherBar onDispatchAction={onDispatchAction} />

      {/* Stagnation Escalation Modal */}
      <StagnationEscalationModal
        isOpen={isStagnationModalOpen}
        onClose={onCloseStagnationModal}
        onResolve={onResolveStagnation}
      />
    </div>
  );
}

export default MasterAGIGovernanceView;
