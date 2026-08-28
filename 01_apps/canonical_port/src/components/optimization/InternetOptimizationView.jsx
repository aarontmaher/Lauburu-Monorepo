import React from 'react';
import { OptimizationHubShell } from './OptimizationHubShell.jsx';

export function InternetOptimizationView({ onSelectModule, onDispatchAction }) {
  const routes = [
    { route: 'TB4 DMA Bridge (169.254.187.138)', bandwidth: '10.0 Gbps', rtt: '0.277 ms', priority: 'P0 - Tensor Sharding', status: 'ACTIVE' },
    { route: 'GL.iNet Wi-Fi 7 MLO (192.168.8.1)', bandwidth: '2.4 Gbps', rtt: '1.12 ms', priority: 'P1 - LAN Ingress', status: 'ACTIVE' },
    { route: 'Tailscale WireGuard Mesh (100.x)', bandwidth: '500 Mbps', rtt: '8.40 ms', priority: 'P2 - Remote Swarm', status: 'ACTIVE' },
    { route: '5G Cellular Emergency Hotspot', bandwidth: '120 Mbps', rtt: '24.5 ms', priority: 'P3 - Fallback Link', status: 'STANDBY' }
  ];

  return (
    <OptimizationHubShell
      activeModule="optimization-internet"
      onSelectModule={onSelectModule}
      moduleTitle="🌐 INTERNET ANALYSIS & 10-ROUTE ACCELERATOR"
      moduleDescription="Mount point for FutureNetworkSimulationHub, multi-WAN channel bonding, and chaos router injection"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Mount Point Status */}
        <div className="cyber-panel cyber-panel-glow-cyan" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>📡</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-cyan)' }}>
                MOUNTED SUBSYSTEM: FutureNetworkSimulationHub & Multi-WAN Router
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Contract: InternetAnalysisOptimizationApp | 4 Transport Layers Multiplexed
              </div>
            </div>
          </div>
          <button className="cyber-btn cyber-btn-cyan" onClick={() => onDispatchAction('/ping')}>
            <span>📡 Test All 10 Routes</span>
          </button>
        </div>

        {/* Multipath Route Table */}
        <div className="cyber-panel" style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '12px' }}>
            MULTIPATH WAN & LOCAL DMA TRANSPORT TOPOLOGY
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '8px' }}>TRANSPORT INTERFACE</th>
                <th style={{ padding: '8px' }}>BANDWIDTH</th>
                <th style={{ padding: '8px' }}>RTT LATENCY</th>
                <th style={{ padding: '8px' }}>PRIORITY</th>
                <th style={{ padding: '8px' }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '8px', color: 'var(--accent-cyan)', fontWeight: 600 }}>{r.route}</td>
                  <td style={{ padding: '8px', color: 'var(--text-primary)' }}>{r.bandwidth}</td>
                  <td style={{ padding: '8px', color: 'var(--accent-emerald)' }}>{r.rtt}</td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>{r.priority}</td>
                  <td style={{ padding: '8px' }}>
                    <span className={`badge ${r.status === 'ACTIVE' ? 'badge-emerald' : 'badge-amber'}`}>
                      ● {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </OptimizationHubShell>
  );
}
