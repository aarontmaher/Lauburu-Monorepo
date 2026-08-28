import React from 'react';
import { LoRADistillationMonitorTab } from './LoRADistillationMonitorTab.jsx';
import { ImplementedGamesArenaTab } from './ImplementedGamesArenaTab.jsx';
import { StructuralMetricsTab } from './StructuralMetricsTab.jsx';
import { ExecutionTracesTab } from './ExecutionTracesTab.jsx';

export function TrainingMultiTabView({
  activeSubTab,
  onSelectSubTab,
  trainingState,
  gamesState,
  structuralMetrics,
  executionTraces,
  onDispatchAction
}) {
  const tabs = [
    { id: 'training-lora', label: '1. LoRA Distillation Monitor', icon: '🔥' },
    { id: 'training-games', label: '2. Implemented Games Arena', icon: '🎮' },
    { id: 'training-metrics', label: '3. Structural AST Metrics', icon: '📊' },
    { id: 'training-traces', label: '4. Execution Action Traces', icon: '📜' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Sub-Nav */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>🔥 LOCAL AI TRAINING & MULTI-TAB HUB</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            24/7 LoRA distillation monitoring, FFA tournament arena, 3.29M LOC structural metrics & execution traces
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', gap: '4px' }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => onSelectSubTab(t.id)}
              className="cyber-btn"
              style={{
                background: activeSubTab === t.id ? 'rgba(0, 255, 204, 0.15)' : 'transparent',
                borderColor: activeSubTab === t.id ? 'var(--accent-cyan)' : 'transparent',
                color: activeSubTab === t.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                fontSize: '0.78rem'
              }}
            >
              <span>{t.icon} {t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content View */}
      {activeSubTab === 'training-lora' && (
        <LoRADistillationMonitorTab trainingState={trainingState} onDispatchAction={onDispatchAction} />
      )}
      {activeSubTab === 'training-games' && (
        <ImplementedGamesArenaTab gamesState={gamesState} onDispatchAction={onDispatchAction} />
      )}
      {activeSubTab === 'training-metrics' && (
        <StructuralMetricsTab metrics={structuralMetrics} />
      )}
      {activeSubTab === 'training-traces' && (
        <ExecutionTracesTab traces={executionTraces} onDispatchAction={onDispatchAction} />
      )}
    </div>
  );
}
