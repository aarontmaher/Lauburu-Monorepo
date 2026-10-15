import React from 'react';

export function KamathFilterPane({ filterData }) {
  const kf = filterData || {};
  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-amber)', marginBottom: '12px' }}>
        KAMATH FILTER DIAGNOSTICS
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Status:</span>
          <span style={{ color: kf.isActive ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
            {kf.isActive ? 'ACTIVE' : 'DISABLED'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Name:</span>
          <span style={{ color: 'var(--text-primary)' }}>{kf.filterName || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Threshold:</span>
          <span style={{ color: 'var(--text-primary)' }}>{kf.thresholdPct !== undefined ? kf.thresholdPct + '%' : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Window Size:</span>
          <span style={{ color: 'var(--text-primary)' }}>{kf.windowSize || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Rejection Rate:</span>
          <span style={{ color: 'var(--accent-amber)' }}>{kf.rejectionRatePct !== undefined ? kf.rejectionRatePct + '%' : '--'}</span>
        </div>
      </div>
    </div>
  );
}
