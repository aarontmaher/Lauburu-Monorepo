import React from 'react';
import { OptimizationHubShell } from './OptimizationHubShell.jsx';

export function SoftwareOptimizationView({ onSelectModule, onDispatchAction }) {
  const compilerPasses = [
    { name: 'Clang AddressSanitizer (ASan)', status: 'PASSING', duration: '12ms', details: 'Zero heap-use-after-free or buffer overflows' },
    { name: 'MemorySanitizer (MSan)', status: 'PASSING', duration: '18ms', details: 'No uninitialized memory reads in tensor shims' },
    { name: 'UndefinedBehaviorSanitizer (UBSan)', status: 'PASSING', duration: '9ms', details: 'Signed integer overflows clean' },
    { name: 'PySpark Monorepo AST Crawler', status: 'PASSING', duration: '142ms', details: '3,100 files indexed; 0 syntax violations' }
  ];

  return (
    <OptimizationHubShell
      activeModule="optimization-software"
      onSelectModule={onSelectModule}
      moduleTitle="🛠️ SOFTWARE ANALYSIS & CLANG ASAN SANDBOX"
      moduleDescription="Mount point for MetaTrainingGame AST Dispatcher, compiler verification, and CoT reasoning optimizer"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Mount Point Status */}
        <div className="cyber-panel cyber-panel-glow-amber" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>⚙️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-amber)' }}>
                MOUNTED SUBSYSTEM: MetaTrainingGame AST & Compiler Sandbox
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Contract: SoftwareAnalysisOptimizationApp | ASan / UBSan Sandboxed Execution
              </div>
            </div>
          </div>
          <button className="cyber-btn" onClick={() => onDispatchAction('/audit')}>
            <span>⚡ Run ASan Test Suite</span>
          </button>
        </div>

        {/* Compiler Passes Table */}
        <div className="cyber-panel" style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '12px' }}>
            ACTIVE COMPILER & SANITIZER VERIFICATION PASSES
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {compilerPasses.map((pass, idx) => (
              <div key={idx} style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-primary)' }}>{pass.name}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{pass.details}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{pass.duration}</span>
                  <span className="badge badge-emerald">● {pass.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </OptimizationHubShell>
  );
}
