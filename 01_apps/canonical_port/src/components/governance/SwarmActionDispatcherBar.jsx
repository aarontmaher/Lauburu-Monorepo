import React from 'react';

export function SwarmActionDispatcherBar({ onDispatchAction }) {
  const actions = [
    {
      cmd: '/audit',
      label: 'Swarm Truth Audit',
      desc: 'Verify 0-mock assertions across 10,240 AST nodes',
      variant: 'cyan'
    },
    {
      cmd: '/duel',
      label: 'AI Arena FFA',
      desc: 'Trigger round in 13-Model FFA tournament',
      variant: 'amber'
    },
    {
      cmd: '/cron',
      label: 'LoRA Harvest',
      desc: 'Sync consensus pairs to /lora_datasets',
      variant: 'emerald'
    },
    {
      cmd: '/storage',
      label: 'Tri-Vault Sync',
      desc: 'Certify Obsidian, PySpark & Git tree',
      variant: 'blue'
    },
    {
      cmd: '/ping',
      label: 'Mesh RTT Sweep',
      desc: 'Measure 10Gbps TB4 & Tailscale latency',
      variant: 'purple'
    },
    {
      cmd: '/revive',
      label: 'Wake-on-LAN',
      desc: 'Resurrect sleeping nodes via magic packet',
      variant: 'rose'
    }
  ];

  return (
    <div className="cyber-panel" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>1-CLICK SWARM ACTION DISPATCHER</span>
          <span className="badge badge-cyan">PORT 18802 SENTINEL</span>
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          Idempotent execution across 7 mesh layers
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '10px'
      }}>
        {actions.map((act) => (
          <button
            key={act.cmd}
            className={`cyber-btn ${act.variant === 'cyan' ? 'cyber-btn-cyan' : act.variant === 'rose' ? 'cyber-btn-rose' : ''}`}
            onClick={() => onDispatchAction(act.cmd)}
            style={{
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: '4px',
              textAlign: 'left'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
              <span className="mono-val" style={{ fontWeight: 700, fontSize: '0.85rem' }}>{act.cmd}</span>
              <span style={{ fontSize: '0.75rem' }}>➔</span>
            </div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>{act.label}</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{act.desc}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
