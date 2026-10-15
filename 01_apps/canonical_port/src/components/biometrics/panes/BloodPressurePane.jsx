import React from 'react';

export function BloodPressurePane({ pttData }) {
  const ptt = pttData || {};
  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '12px' }}>
        PTT BLOOD PRESSURE
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SYSTOLIC / DIASTOLIC</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {ptt.systolicMmhg ? `${ptt.systolicMmhg}/${ptt.diastolicMmhg}` : '--/--'}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Status:</span>
          <span style={{ color: ptt.status === 'NOMINAL' ? 'var(--accent-emerald)' : 'var(--text-primary)' }}>{ptt.status || '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>Pulse Transit Time:</span>
          <span style={{ color: 'var(--text-primary)' }}>{ptt.pulseTransitTimeMs ? `${ptt.pulseTransitTimeMs} ms` : '--'}</span>
        </div>
      </div>
    </div>
  );
}
