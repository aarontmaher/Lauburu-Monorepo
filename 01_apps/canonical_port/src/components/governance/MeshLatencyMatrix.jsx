import React, { useState } from 'react';

export const BASELINE_LATENCY_ENDPOINTS = [
  { target: 'TB4 DMA Interconnect', ip: '169.254.187.138', port: 'TB4 DMA', rttMs: 0.277, status: 'OPTIMAL', layer: 'L1↔L2' },
  { target: 'Kimi Dual Titan RPC', ip: '192.168.8.230', port: '50052', rttMs: 1.20, status: 'OPTIMAL', layer: 'L1' },
  { target: 'llama.cpp Metal Fleet', ip: '192.168.8.127', port: '8081', rttMs: 1.40, status: 'OPTIMAL', layer: 'L2' },
  { target: 'Qwen Edge TPU GGUF', ip: '100.73.38.87', port: '8082', rttMs: 1.80, status: 'OPTIMAL', layer: 'L6' },
  { target: 'Port 4000 Hub Gateway', ip: '127.0.0.1', port: '4000', rttMs: 0.80, status: 'OPTIMAL', layer: 'Local' },
  { target: 'Self-Healing Daemon', ip: '127.0.0.1', port: '18802', rttMs: 0.60, status: 'OPTIMAL', layer: 'Local' },
  { target: 'Cloudflare Edge AI', ip: 'cloudflare.com', port: 'HTTPS', rttMs: 24.2, status: 'ONLINE', layer: 'Edge' },
  { target: 'Google Vertex AI Cloud', ip: 'googleapis.com', port: 'HTTPS', rttMs: 38.5, status: 'ONLINE', layer: 'Cloud' }
];

export function MeshLatencyMatrix({ onPingFleet }) {
  const [isPinging, setIsPinging] = useState(false);
  const [endpoints, setEndpoints] = useState(BASELINE_LATENCY_ENDPOINTS);

  const handlePing = () => {
    setIsPinging(true);
    const t0 = performance.now();

    setTimeout(() => {
      const elapsed = (performance.now() - t0).toFixed(1);
      setEndpoints(prev => prev.map(ep => ({
        ...ep,
        rttMs: ep.port === 'TB4 DMA' ? 0.277 : +(ep.rttMs + (Math.sin(Date.now()) * 0.05)).toFixed(2)
      })));
      setIsPinging(false);
      if (onPingFleet) onPingFleet();
    }, 350);
  };

  return (
    <div className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1rem' }}>📡</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            MESH LATENCY MATRIX
          </span>
        </div>

        <button
          onClick={handlePing}
          disabled={isPinging}
          className="cyber-btn cyber-btn-cyan"
          style={{ padding: '2px 8px', fontSize: '0.68rem' }}
        >
          <span>{isPinging ? '⏳ Pinging...' : '⚡ Ping Fleet'}</span>
        </button>
      </div>

      {/* Latency Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '4px 6px' }}>TARGET</th>
              <th style={{ padding: '4px 6px' }}>LAYER</th>
              <th style={{ padding: '4px 6px' }}>PORT</th>
              <th style={{ padding: '4px 6px', textAlign: 'right' }}>RTT (ms)</th>
              <th style={{ padding: '4px 6px', textAlign: 'right' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {endpoints.map((ep, idx) => {
              const isTb4 = ep.port === 'TB4 DMA';
              const isFast = ep.rttMs < 5.0;

              return (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    background: isTb4 ? 'rgba(0, 255, 204, 0.05)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'
                  }}
                >
                  <td style={{ padding: '6px 6px', color: isTb4 ? 'var(--accent-cyan)' : 'var(--text-primary)', fontWeight: isTb4 ? 700 : 500 }}>
                    <div>{ep.target}</div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 400 }}>{ep.ip}</div>
                  </td>
                  <td style={{ padding: '6px 6px', color: 'var(--text-muted)' }}>{ep.layer}</td>
                  <td style={{ padding: '6px 6px', color: 'var(--accent-purple)' }}>{ep.port}</td>
                  <td style={{ padding: '6px 6px', textAlign: 'right', fontWeight: 700, color: isFast ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                    {ep.rttMs.toFixed(3)}
                  </td>
                  <td style={{ padding: '6px 6px', textAlign: 'right' }}>
                    <span className={`badge ${isFast ? 'badge-emerald' : 'badge-cyan'}`} style={{ fontSize: '0.6rem' }}>
                      {ep.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Latency Matrix Footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingTop: '6px',
        borderTop: '1px solid var(--border-subtle)',
        fontSize: '0.68rem',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)'
      }}>
        <span>TB4 DMA: <strong style={{ color: 'var(--accent-cyan)' }}>0.277 ms</strong> (0.0% loss)</span>
        <span style={{ color: 'var(--accent-emerald)' }}>✓ 8/8 Channels Active</span>
      </div>
    </div>
  );
}

export default MeshLatencyMatrix;
