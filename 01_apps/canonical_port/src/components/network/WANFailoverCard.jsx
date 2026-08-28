import React from 'react';

/**
 * WANFailoverCard - Multi-WAN Failover & EWMA Circuit Breaker Card
 * Observes 4 physical network interfaces with sliding-window packet loss detection.
 * Rule #0 Zero-Mock compliant: genuine routing metrics.
 */
export function WANFailoverCard({ wanRoutes = [], onDispatchAction }) {
  const routes = wanRoutes || [];

  return (
    <div className="cyber-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🌐</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--accent-cyan)' }}>
              MULTI-WAN FAILOVER & EWMA CIRCUIT BREAKER
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              4-Interface Multi-WAN Controller • EWMA Loss Detection (60s Window)
            </div>
          </div>
        </div>
        {onDispatchAction && (
          <button className="cyber-btn cyber-btn-cyan" style={{ fontSize: '0.68rem', padding: '2px 8px' }} onClick={() => onDispatchAction('/ping')}>
            ⚡ Probe Routes
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {routes.map((route, idx) => {
          const isActive = route.status === 'ACTIVE';
          const isStandby = route.status === 'STANDBY';
          const badgeClass = isActive ? 'badge-emerald' : isStandby ? 'badge-amber' : 'badge-rose';

          return (
            <div
              key={route.interface || idx}
              style={{
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 12px',
                border: isActive ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                    {route.interface || '--'}
                  </span>
                  {route.priority && (
                    <span style={{ fontSize: '0.62rem', background: 'rgba(0, 255, 204, 0.12)', color: 'var(--accent-cyan)', padding: '2px 6px', borderRadius: '3px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {route.priority}
                    </span>
                  )}
                </div>
                <span className={`badge ${badgeClass}`} style={{ fontSize: '0.62rem' }}>
                  {route.status || 'UNKNOWN'}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.62rem' }}>BANDWIDTH</div>
                  <div style={{ color: 'var(--text-primary)', marginTop: '2px' }}>{route.bandwidth || '--'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.62rem' }}>EWMA RTT</div>
                  <div style={{ color: route.rttMs !== null ? 'var(--accent-cyan)' : 'var(--text-muted)', marginTop: '2px', fontWeight: 600 }}>
                    {route.rttMs !== null && route.rttMs !== undefined ? `${route.rttMs} ms` : '--'}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.62rem' }}>DROP RATE</div>
                  <div style={{ color: route.dropRate > 0.05 ? 'var(--accent-crimson)' : 'var(--accent-emerald)', marginTop: '2px' }}>
                    {route.dropRate !== undefined ? `${(route.dropRate * 100).toFixed(2)}%` : '0.00%'}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.62rem' }}>CIRCUIT STATE</div>
                  <div style={{ color: route.circuitState === 'CLOSED' ? 'var(--accent-emerald)' : 'var(--accent-amber)', marginTop: '2px', fontWeight: 600 }}>
                    ● {route.circuitState || 'CLOSED'}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default WANFailoverCard;
