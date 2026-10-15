import React from 'react';

export function GrapplingKinematicsPane({ gmapData }) {
  const gmap = gmapData || {};
  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '12px' }}>
        3D GRAPPLING KINEMATICS
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Active Position:</span>
          <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{gmap.activePosition || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Total Nodes:</span>
          <span>{gmap.totalNodes || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Total Transitions:</span>
          <span>{gmap.totalTransitions || '--'}</span>
        </div>
      </div>
    </div>
  );
}
