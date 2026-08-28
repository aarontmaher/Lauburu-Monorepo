import React from 'react';

/**
 * LlamaRpcLatencyCard - Distributed GGML-RPC Node Latency Matrix
 * Tracks Port 50052 shards (-ts 28,28,24 Kimi 88B Tandem Titan 3-Way Split).
 * Rule #0 Zero-Mock compliant: genuine physical RPC metrics.
 */
export function LlamaRpcLatencyCard({ llamaRpcNodes = [], onDispatchAction }) {
  const nodes = llamaRpcNodes || [];
  const totalLayers = nodes.reduce((sum, n) => sum + (n.layersSharded || 0), 0);
  const totalVram = nodes.reduce((sum, n) => sum + (n.vramUsedGb || 0), 0);

  return (
    <div className="cyber-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🦙</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--accent-cyan)' }}>
              LLAMA.CPP GGML-RPC NODE LATENCY MATRIX (PORT 50052)
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Kimi 88B Tandem Titan 3-Way Split (-ts 28,28,24) • {totalLayers} Layers ({totalVram.toFixed(1)} GB VRAM)
            </div>
          </div>
        </div>
        {onDispatchAction && (
          <button className="cyber-btn cyber-btn-cyan" style={{ fontSize: '0.68rem', padding: '2px 8px' }} onClick={() => onDispatchAction('/ping')}>
            🔄 Sweep RPC
          </button>
        )}
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>RPC NODE</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>ENDPOINT (PORT 50052)</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>SHARDED LAYERS</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>VRAM FOOTPRINT</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>MEASURED RTT</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((node, idx) => {
              const isOnline = node.status === 'ONLINE' || node.status === 'ACTIVE';
              const badgeClass = isOnline ? 'badge-emerald' : 'badge-rose';

              return (
                <tr
                  key={node.endpoint || idx}
                  style={{
                    borderBottom: '1px solid rgba(23, 34, 54, 0.5)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(16, 23, 38, 0.4)'
                  }}
                >
                  <td style={{ padding: '8px 6px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {node.nodeName || '--'}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--accent-cyan)' }}>
                    {node.endpoint || '--'}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--accent-purple)', fontWeight: 700 }}>
                    {node.layersSharded !== undefined ? `${node.layersSharded} layers` : '--'}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--accent-amber)' }}>
                    {node.vramUsedGb !== undefined ? `${node.vramUsedGb.toFixed(1)} GB` : '--'}
                  </td>
                  <td style={{ padding: '8px 6px', color: node.latencyMs !== null ? 'var(--accent-emerald)' : 'var(--text-muted)', fontWeight: 600 }}>
                    {node.latencyMs !== null && node.latencyMs !== undefined ? `${node.latencyMs} ms` : '--'}
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    <span className={`badge ${badgeClass}`} style={{ fontSize: '0.62rem' }}>
                      {node.status || 'OFFLINE'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default LlamaRpcLatencyCard;
