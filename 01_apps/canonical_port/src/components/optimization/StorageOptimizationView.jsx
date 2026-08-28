import React from 'react';
import { OptimizationHubShell } from './OptimizationHubShell.jsx';

export function StorageOptimizationView({ onSelectModule, onDispatchAction }) {
  const vaults = [
    { name: 'Obsidian Knowledge Vault', path: '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault', size: '245 MB', status: 'HEALTHY', role: 'Human & Semantic Core (41 MCP Tools)' },
    { name: 'PySpark & Big Data Lake', path: '/Users/aaron/DFS_UNIFIED/lora_datasets', size: '14.8 GB', status: 'HEALTHY', role: 'High-Throughput 24/7 LoRA Datasets' },
    { name: 'GitHub Monorepo Worktree', path: '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo', size: '2.4 GB', status: 'HEALTHY', role: 'Canonical Git Source & Tests' }
  ];

  return (
    <OptimizationHubShell
      activeModule="optimization-storage"
      onSelectModule={onSelectModule}
      moduleTitle="💾 STORAGE ANALYSIS & TRI-VAULT SYNCHRONIZER"
      moduleDescription="Mount point for StorageAnalysisHub, 3-layer Tri-Vault storage architecture, and DFS NAS sync"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Mount Point Status */}
        <div className="cyber-panel cyber-panel-glow-cyan" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.2rem' }}>🏛️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-cyan)' }}>
                MOUNTED SUBSYSTEM: StorageAnalysisHub & Tri-Vault DFS Governor
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Contract: StorageAnalysisOptimizationApp | Rule #6 Storage Health Invariant Certified
              </div>
            </div>
          </div>
          <button className="cyber-btn cyber-btn-cyan" onClick={() => onDispatchAction('/storage')}>
            <span>📁 Sync All Vaults</span>
          </button>
        </div>

        {/* Tri-Vault Breakdown Grid */}
        <div className="grid-cols-3">
          {vaults.map((vault, i) => (
            <div key={i} className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{vault.name}</span>
                <span className="badge badge-emerald">● {vault.status}</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{vault.role}</div>
              <div style={{
                background: 'var(--bg-secondary)',
                padding: '6px 8px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.68rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--accent-cyan)',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {vault.path}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
                <span style={{ color: 'var(--text-muted)' }}>SIZE:</span>
                <span style={{ color: 'var(--accent-purple)' }}>{vault.size}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Free Headroom Bar */}
        <div className="cyber-panel" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>HOST NVMe HEADROOM (RULE 6.1 INVARIANT)</span>
            <span className="mono-val" style={{ color: 'var(--accent-emerald)', fontSize: '0.82rem' }}>≥ 10.0 GB Required | 148.2 GB Free</span>
          </div>
          <div className="telemetry-bar-bg" style={{ height: '10px' }}>
            <div className="telemetry-bar-fill" style={{ width: '84%', background: 'var(--accent-emerald)' }} />
          </div>
        </div>
      </div>
    </OptimizationHubShell>
  );
}
