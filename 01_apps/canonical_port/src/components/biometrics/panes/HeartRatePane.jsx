import React from 'react';

export function HeartRatePane({ bio }) {
  const hr = bio.heartRateBpm;
  const rmssd = bio.rmssdMs;
  const dfa = bio.dfaAlpha1;
  const zone = bio.zone2Status;

  return (
    <div className="cyber-card">
      <div style={{ fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '12px' }}>
        HEART RATE & HRV
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>BPM</div>
          <div style={{ fontSize: hr ? '1.6rem' : '1.0rem', fontWeight: 700, color: hr ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
            {zone === 'WAITING_FOR_SENSOR' || !hr ? 'WAITING_FOR_SENSOR' : hr}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)' }}>Zone: {zone || '--'}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>RMSSD (ms)</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {rmssd ? rmssd : '--'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>DFA-alpha1</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-amber)' }}>
            {dfa !== undefined && dfa !== null ? dfa : '--'}
          </div>
        </div>
        {bio.rrIntervalsMs && bio.rrIntervalsMs.length > 0 && (
          <div>
             <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Recent RR Intervals</div>
             <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {bio.rrIntervalsMs.slice(-5).join(', ')}
             </div>
          </div>
        )}
      </div>
    </div>
  );
}
