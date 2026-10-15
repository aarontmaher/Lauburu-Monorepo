import React from 'react';

export function TinyMlGaugePane({ bio }) {
  const tinyml = bio.tinymlTrend || {};
  const dfa = bio.dfaAlpha1;
  
  // Calculate stroke dasharray for DFA-alpha1 (0.0 to 2.0)
  const dfaValue = dfa !== null && dfa !== undefined ? Math.min(Math.max(dfa, 0), 2.0) : 0;
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (dfaValue / 2.0) * circumference;

  let gaugeColor = 'var(--accent-emerald)';
  if (dfaValue < 0.5) gaugeColor = 'var(--accent-red)';
  else if (dfaValue < 0.75) gaugeColor = 'var(--accent-amber)';

  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-purple)', marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
        <span>TINYML DFA-α1 READINESS</span>
        {tinyml.zero_rejection_certified && <span className="badge badge-purple" style={{fontSize: '0.6rem'}}>ZERO REJECT CERT</span>}
      </div>
      
      <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
        {/* Circular Gauge */}
        <div style={{ position: 'relative', width: '100px', height: '100px' }}>
          <svg width="100" height="100" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle cx="50" cy="50" r="40" fill="none" stroke="var(--bg-layer-2)" strokeWidth="8" />
            {/* Foreground circle */}
            <circle 
              cx="50" cy="50" r="40" 
              fill="none" 
              stroke={gaugeColor} 
              strokeWidth="8" 
              strokeDasharray={circumference}
              strokeDashoffset={dfa !== null && dfa !== undefined ? strokeDashoffset : circumference}
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
              style={{ transition: 'stroke-dashoffset 0.5s ease-in-out, stroke 0.5s ease-in-out' }}
            />
          </svg>
          <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: '1.2rem', fontWeight: 800, color: gaugeColor }}>
              {dfa !== null && dfa !== undefined ? dfa.toFixed(2) : '--'}
            </span>
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>DFA-α1</span>
          </div>
        </div>
        
        {/* TinyML Metrics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Ectopic Density:</span>
            <span style={{ color: 'var(--text-primary)' }}>{tinyml.ectopic_density_per_min !== undefined ? tinyml.ectopic_density_per_min.toFixed(2) : '--'} /min</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Cardiac Drift:</span>
            <span style={{ color: 'var(--text-primary)' }}>{tinyml.cardiac_drift_pct !== undefined ? tinyml.cardiac_drift_pct.toFixed(1) : '--'}%</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Alpha1 Slope:</span>
            <span style={{ color: 'var(--text-primary)' }}>{tinyml.alpha1_slope_per_min !== undefined ? tinyml.alpha1_slope_per_min.toFixed(3) : '--'} /min</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>Training Zone:</span>
            <span style={{ color: 'var(--accent-amber)', fontSize: '0.75rem' }}>{tinyml.training_zone || '--'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
