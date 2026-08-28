import React from 'react';

export function AGIModelRosterCard({ model }) {
  const isKimi = model.id === 'kimi_tandem_titan';
  const isQwen = model.id === 'qwen_38_max';

  return (
    <div
      className={`cyber-panel ${isKimi ? 'cyber-panel-glow-cyan' : isQwen ? 'cyber-panel-glow-amber' : ''}`}
      style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Top Banner */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 700, fontSize: '1.05rem', color: isKimi ? 'var(--accent-cyan)' : isQwen ? 'var(--accent-amber)' : 'var(--text-primary)' }}>
              {model.name}
            </span>
            <span className={`badge ${model.status === 'active' ? 'badge-emerald' : 'badge-amber'}`}>
              ● {model.status}
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {model.role}
          </div>
        </div>

        <div className="badge badge-purple mono-val" style={{ fontSize: '0.75rem' }}>
          ELO {model.eloRating}
        </div>
      </div>

      {/* Architecture & Sharding */}
      <div style={{
        background: 'var(--bg-secondary)',
        padding: '8px 12px',
        borderRadius: 'var(--radius-sm)',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-mono)',
        border: '1px solid var(--border-subtle)'
      }}>
        <div style={{ color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--text-muted)' }}>ARCH: </span>{model.architecture}
        </div>
        <div style={{ color: 'var(--accent-blue)', marginTop: '3px' }}>
          <span style={{ color: 'var(--text-muted)' }}>SHARD: </span>{model.shardingStrategy}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px',
        background: 'var(--bg-tertiary)',
        padding: '10px',
        borderRadius: 'var(--radius-sm)'
      }}>
        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>VRAM FOOTPRINT</div>
          <div className="mono-val" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
            {model.vramFootprintGb} GB
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>THROUGHPUT</div>
          <div className="mono-val" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-emerald)' }}>
            {model.throughputTokPerSec} tok/s
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>CONTEXT LIMIT</div>
          <div className="mono-val" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-purple)' }}>
            {(model.contextWindow / 1024).toFixed(0)}k
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>REST PORTS</div>
          <div className="mono-val" style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent-amber)' }}>
            {model.ports.join(', ')}
          </div>
        </div>
      </div>
    </div>
  );
}
