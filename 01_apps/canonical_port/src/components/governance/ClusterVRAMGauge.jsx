import React from 'react';

export function ClusterVRAMGauge({ clusterVram }) {
  const nodes = clusterVram?.nodes || [];
  const totalPooled = clusterVram?.pooledVramGb || 82.8;
  const totalAllocated = clusterVram?.allocatedVramGb || 61.4;
  const headroom = clusterVram?.freeHeadroomGb || 21.4;
  const percentPooledUsed = Math.round((totalAllocated / totalPooled) * 100);

  return (
    <div className="cyber-panel" style={{ padding: '18px' }}>
      {/* Gauge Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1rem', fontWeight: 700 }}>POOLED 82.8 GB VRAM SHARDING MATRIX</span>
            <span className="badge badge-cyan">7 NODES POOLED</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Physical dynamic RAM governance & 10Gbps Thunderbolt 4 DMA memory routing
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div className="mono-val" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {totalAllocated} <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/ {totalPooled} GB</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)' }}>
            HEADROOM: {headroom} GB ({100 - percentPooledUsed}%)
          </div>
        </div>
      </div>

      {/* Global Pooled VRAM Bar */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px', fontFamily: 'var(--font-mono)' }}>
          <span>GLOBAL CLUSTER ALLOCATION</span>
          <span>{percentPooledUsed}% POOLED</span>
        </div>
        <div className="telemetry-bar-bg" style={{ height: '12px' }}>
          <div
            className="telemetry-bar-fill"
            style={{
              width: `${percentPooledUsed}%`,
              background: 'linear-gradient(90deg, #00ffcc 0%, #38bdf8 60%, #c084fc 100%)'
            }}
          />
        </div>
      </div>

      {/* 7 Physical Nodes Telemetry Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '6px 8px' }}>NODE LAYER</th>
              <th style={{ padding: '6px 8px' }}>HARDWARE / ROLE</th>
              <th style={{ padding: '6px 8px' }}>IP / LINK</th>
              <th style={{ padding: '6px 8px' }}>TOTAL RAM</th>
              <th style={{ padding: '6px 8px' }}>AI VRAM CAP</th>
              <th style={{ padding: '6px 8px' }}>USED VRAM</th>
              <th style={{ padding: '6px 8px' }}>LIMIT</th>
              <th style={{ padding: '6px 8px' }}>LATENCY</th>
              <th style={{ padding: '6px 8px' }}>TEMP / CPU</th>
              <th style={{ padding: '6px 8px' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((node) => {
              const nodeUsagePercent = Math.round((node.usedVramGb / node.aiVramCapGb) * 100);
              const isOverLimit = nodeUsagePercent > node.dynamicCapPercent;
              const isTb4 = node.nodeId === 'L2_MacBook_Pro';

              return (
                <tr key={node.nodeId} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '8px', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                    {node.nodeId}
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-primary)' }}>
                    <div>{node.name}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{node.role}</div>
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                    <div>{node.ip}</div>
                    {node.bridgeIp ? (
                      <div style={{ color: 'var(--accent-cyan)', fontSize: '0.68rem' }}>{node.bridgeIp}</div>
                    ) : (
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{node.tailscaleIp}</div>
                    )}
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-primary)' }}>
                    {node.ramTotalGb} GB
                  </td>
                  <td style={{ padding: '8px', color: 'var(--accent-blue)', fontWeight: 600 }}>
                    {node.aiVramCapGb} GB
                  </td>
                  <td style={{ padding: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <div style={{ width: '50px' }} className="telemetry-bar-bg">
                        <div
                          className="telemetry-bar-fill"
                          style={{
                            width: `${nodeUsagePercent}%`,
                            background: isOverLimit ? 'var(--accent-rose)' : 'var(--accent-cyan)'
                          }}
                        />
                      </div>
                      <span style={{ color: isOverLimit ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
                        {node.usedVramGb} GB
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '8px', color: 'var(--accent-amber)' }}>
                    ≤{node.dynamicCapPercent}%
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span className={`badge ${isTb4 ? 'badge-cyan' : 'badge-emerald'}`} style={{ fontSize: '0.68rem' }}>
                      {node.latencyMs} ms
                    </span>
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                    {node.tempC}°C / {node.cpuPercent}%
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                      ● {node.status}
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
