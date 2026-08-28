import React from 'react';

export function ExecutionTracesTab({ traces, onDispatchAction }) {
  const traceList = traces || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
            📜 SWARM EXECUTION TRACES & ACTION LEDGER
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Immutable audit log of all /audit, /cron, /ping, /storage and /duel commands
          </div>
        </div>
        <button className="cyber-btn" onClick={() => onDispatchAction('/audit')}>
          <span>⚡ New Audit Trace</span>
        </button>
      </div>

      {/* Traces List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {traceList.map((trc) => (
          <div
            key={trc.id}
            className="cyber-panel"
            style={{
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="mono-val" style={{ fontWeight: 700, color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>
                  {trc.action}
                </span>
                <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                  ● {trc.status}
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {trc.timestamp} | {trc.durationMs}ms
              </div>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)' }}>
              {trc.details}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
              <span>INITIATOR: {trc.initiator}</span>
              <span>NODES: {trc.nodesInvolved?.join(', ')}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
