import React from 'react';

export function StagnationEscalationModal({ isOpen, onClose, onResolve }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(7, 11, 18, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: '20px'
    }}>
      <div
        className="cyber-panel cyber-panel-glow-rose"
        style={{
          width: '100%',
          maxWidth: '560px',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}
      >
        {/* Modal Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.4rem' }}>🚨</span>
          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-rose)' }}>
              SWARM STAGNATION & DEADLOCK FAILSAFE
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Tri-Orchestrator accord dropped below 0.85 threshold or encountered recursive loop
            </div>
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)',
          padding: '12px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
          border: '1px solid var(--border-subtle)'
        }}>
          Debate consensus deadlock detected between Kimi 88B Titan (Port 8085) and Qwen 3.8 Max (Port 8084).
          Human operator tie-breaker or forced quorum is required before gradient descent can resume.
        </div>

        {/* Action Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button
            className="cyber-btn cyber-btn-cyan"
            style={{ justifyContent: 'center', padding: '10px' }}
            onClick={() => onResolve('RATIFY_KIMI_TITAN')}
          >
            👑 Ratify Kimi 88B Titan Decision (Preferred Strategic Vector)
          </button>

          <button
            className="cyber-btn"
            style={{ justifyContent: 'center', padding: '10px', borderColor: 'var(--accent-amber)', color: 'var(--accent-amber)' }}
            onClick={() => onResolve('RATIFY_QWEN_MAX')}
          >
            ⚡ Ratify Qwen 3.8 Max Decision (Low-Latency Edge Vector)
          </button>

          <button
            className="cyber-btn cyber-btn-rose"
            style={{ justifyContent: 'center', padding: '10px' }}
            onClick={() => onResolve('FORCE_CLOUD_QUORUM')}
          >
            ☁️ Escalate to Gemini 3.1 Pro Cloud Oracle (Absolute Arbiter)
          </button>
        </div>

        {/* Footer Cancel */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
          <button
            className="cyber-btn"
            onClick={onClose}
            style={{ fontSize: '0.75rem' }}
          >
            Dismiss / Manual Inspect
          </button>
        </div>
      </div>
    </div>
  );
}
