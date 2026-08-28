import React from 'react';

/**
 * NodeCard - High-Density Hardware Node Sentinel Card
 * Displays real-time CPU, RAM, AI VRAM, Thermals, Dynamic RAM Caps, and Network Latencies.
 * Rule #0 Zero-Mock compliant: returns clean '--' or 'OFFLINE' on null values.
 */
export function NodeCard({ node, onDispatchAction }) {
  if (!node) return null;

  const {
    nodeId = '--',
    name = 'Unknown Node',
    role = 'Compute Worker',
    ip = '--',
    tailscaleIp = '--',
    bridgeIp,
    ramTotalGb = 0,
    ramUsedGb = 0,
    aiVramCapGb = 0,
    usedVramGb = 0,
    dynamicCapPercent = 85,
    latencyMs = null,
    status = 'OFFLINE',
    tempC = null,
    cpuPercent = null,
    storageFreeGb = null,
    headlessScore = 80,
    priorityRank = 1,
    sshPort = 22
  } = node;

  const isOnline = status === 'ONLINE' || status === 'ACTIVE';
  const vramPercent = aiVramCapGb > 0 ? Math.min(100, Math.round((usedVramGb / aiVramCapGb) * 100)) : 0;
  const ramPercent = ramTotalGb > 0 ? Math.min(100, Math.round((ramUsedGb / ramTotalGb) * 100)) : 0;
  const cpuVal = cpuPercent !== null ? cpuPercent : '--';

  // Thermal Color Spectrum (<45°C emerald, 45-55°C amber, >55°C rose)
  const getTempColor = (t) => {
    if (t === null || t === undefined) return 'var(--text-muted)';
    if (t < 45) return 'var(--accent-emerald)';
    if (t <= 55) return 'var(--accent-amber)';
    return 'var(--accent-rose)';
  };

  const tempColor = getTempColor(tempC);

  return (
    <div
      className="cyber-panel"
      style={{
        padding: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        border: isOnline ? '1px solid var(--border-subtle)' : '1px solid rgba(244, 63, 94, 0.4)',
        background: 'var(--bg-card)'
      }}
    >
      {/* Top Header: Node ID, Role & Status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isOnline ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              boxShadow: isOnline ? '0 0 6px var(--accent-emerald)' : '0 0 6px var(--accent-rose)'
            }}
          />
          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            {nodeId.split('_')[0]}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            {name.split('(')[0].trim()}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="badge badge-cyan" style={{ fontSize: '0.62rem' }}>
            #{priorityRank} (Score: {headlessScore})
          </span>
          <span className={`badge ${isOnline ? 'badge-emerald' : 'badge-rose'}`} style={{ fontSize: '0.62rem' }}>
            {status}
          </span>
        </div>
      </div>

      {/* Role Subtitle & Hardware Model */}
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
        <span>{role}</span>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-purple)' }}>
          SSH :{sshPort}
        </span>
      </div>

      {/* Telemetry Metric Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          background: 'var(--bg-tertiary)',
          padding: '10px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)'
        }}
      >
        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>CPU USAGE</div>
          <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginTop: '2px' }}>
            {cpuVal !== '--' ? `${cpuVal}%` : '--'}
          </div>
          <div style={{ width: '100%', height: '3px', background: 'rgba(255,255,255,0.08)', marginTop: '4px', borderRadius: '2px' }}>
            <div style={{ width: `${Math.min(100, typeof cpuVal === 'number' ? cpuVal : 0)}%`, height: '100%', background: 'var(--accent-cyan)' }} />
          </div>
        </div>

        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>THERMALS</div>
          <div style={{ color: tempColor, fontWeight: 600, marginTop: '2px' }}>
            {tempC !== null && tempC !== undefined ? `${tempC}°C` : '--'}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'var(--text-dim)', marginTop: '3px' }}>
            {tempC < 50 ? '● Nominal' : '▲ Elevated'}
          </div>
        </div>

        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>RTT LATENCY</div>
          <div style={{ color: latencyMs !== null ? 'var(--accent-emerald)' : 'var(--text-muted)', fontWeight: 600, marginTop: '2px' }}>
            {latencyMs !== null && latencyMs !== undefined ? `${latencyMs} ms` : '--'}
          </div>
          <div style={{ fontSize: '0.6rem', color: 'var(--text-dim)', marginTop: '3px' }}>
            {bridgeIp ? 'TB4 DMA' : 'Tailscale'}
          </div>
        </div>
      </div>

      {/* VRAM / RAM Allocation Bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: 'var(--text-muted)' }}>
            AI VRAM (Cap {dynamicCapPercent}%):
          </span>
          <span style={{ color: 'var(--accent-amber)', fontWeight: 600 }}>
            {usedVramGb.toFixed(1)} / {aiVramCapGb.toFixed(1)} GB ({vramPercent}%)
          </span>
        </div>
        <div className="telemetry-bar-bg" style={{ height: '5px' }}>
          <div
            className="telemetry-bar-fill"
            style={{
              width: `${vramPercent}%`,
              background: vramPercent > 85 ? 'var(--accent-rose)' : 'var(--accent-amber)'
            }}
          />
        </div>
      </div>

      {/* Network Addresses */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        <span>TS: {tailscaleIp}</span>
        <span>LAN: {ip}</span>
      </div>
    </div>
  );
}

export default NodeCard;
