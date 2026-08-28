import React from 'react';
import { OptimizationHubShell } from './OptimizationHubShell.jsx';

export function HardwareOptimizationView({
  clusterVram,
  onSelectModule,
  onDispatchAction
}) {
  const nodes = clusterVram?.nodes || [];

  return (
    <OptimizationHubShell
      activeModule="optimization-hardware"
      onSelectModule={onSelectModule}
      moduleTitle="⚡ HARDWARE ANALYSIS & DEVICE SENTINEL"
      moduleDescription="Mount point for LiveDeviceSentinelHUD, 7-node dynamic RAM governance, and 128Hz biometrics DSP"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Mount Point Status Banner */}
        <div className="cyber-panel cyber-panel-glow-cyan" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>🔌</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-cyan)' }}>
                MOUNTED SUBSYSTEM: LiveDeviceSentinelHUD (Port 18802)
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Contract: HardwareAnalysisOptimizationApp | 7 Physical Layers Connected
              </div>
            </div>
          </div>
          <button className="cyber-btn cyber-btn-cyan" onClick={() => onDispatchAction('/ping')}>
            <span>📡 Sweep All Nodes</span>
          </button>
        </div>

        {/* 7 Node Hardware Cards Grid */}
        <div className="grid-cols-3">
          {nodes.map((node) => (
            <div key={node.nodeId} className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                    {node.nodeId}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {node.name}
                  </div>
                </div>
                <span className="badge badge-emerald">ONLINE</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>VRAM USAGE:</span>
                  <span className="mono-val" style={{ color: 'var(--accent-cyan)' }}>{node.usedVramGb} / {node.aiVramCapGb} GB</span>
                </div>
                <div className="telemetry-bar-bg">
                  <div
                    className="telemetry-bar-fill"
                    style={{
                      width: `${Math.round((node.usedVramGb / node.aiVramCapGb) * 100)}%`,
                      background: 'var(--accent-cyan)'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>TEMP / CPU:</span>
                  <span>{node.tempC}°C / {node.cpuPercent}%</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>NET LATENCY:</span>
                  <span style={{ color: 'var(--accent-blue)' }}>{node.latencyMs} ms</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Biometrics DSP Sentinel Placeholder */}
        <div className="cyber-panel" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
              MOVESENSE BLE 512Hz ECG & DSP SENTINEL
            </div>
            <span className="badge badge-cyan">PAN-TOMPKINS ACTIVE</span>
          </div>
          <div style={{
            background: 'var(--bg-secondary)',
            height: '80px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.78rem'
          }}>
            [Live 512Hz Bandpass ECG Stream & R-Peak Fiducial Detector — Continuous Telemetry Active]
          </div>
        </div>
      </div>
    </OptimizationHubShell>
  );
}
