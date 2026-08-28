import React from 'react';

export function ImplementedGamesArenaTab({ gamesState, onDispatchAction }) {
  const state = gamesState || {};
  const models = state.models || [];
  const events = state.recentEvents || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Tournament Header */}
      <div className="cyber-panel cyber-panel-glow-amber" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--accent-amber)' }}>
            🎮 {state.activeTournament}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Round {state.currentRound} of {state.totalRounds} | Current Leader: {state.leaderModel}
          </div>
        </div>
        <button className="cyber-btn cyber-btn-cyan" onClick={() => onDispatchAction('/duel')}>
          <span>⚔️ Trigger Arena Round</span>
        </button>
      </div>

      {/* Model Combatants Roster Table */}
      <div className="cyber-panel" style={{ padding: '16px' }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '12px' }}>
          COMBATANT ARENA STANDINGS & ALLIANCES
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '8px' }}>MODEL COMBATANT</th>
              <th style={{ padding: '8px' }}>SCORE</th>
              <th style={{ padding: '8px' }}>KILLS</th>
              <th style={{ padding: '8px' }}>HP</th>
              <th style={{ padding: '8px' }}>ALLIANCE</th>
              <th style={{ padding: '8px' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '8px', color: 'var(--text-primary)', fontWeight: 600 }}>{m.name}</td>
                <td style={{ padding: '8px', color: 'var(--accent-cyan)' }}>{m.score} pts</td>
                <td style={{ padding: '8px', color: 'var(--accent-rose)' }}>{m.kills}</td>
                <td style={{ padding: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '50px' }} className="telemetry-bar-bg">
                      <div className="telemetry-bar-fill" style={{ width: `${m.hp}%`, background: m.hp > 50 ? 'var(--accent-emerald)' : m.hp > 0 ? 'var(--accent-amber)' : 'var(--accent-rose)' }} />
                    </div>
                    <span>{m.hp}%</span>
                  </div>
                </td>
                <td style={{ padding: '8px', color: 'var(--accent-purple)' }}>{m.alliance}</td>
                <td style={{ padding: '8px' }}>
                  <span className={`badge ${m.status === 'ALIVE' ? 'badge-emerald' : 'badge-rose'}`}>
                    ● {m.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Live Combat Event Stream */}
      <div className="cyber-panel" style={{ padding: '16px' }}>
        <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '10px' }}>
          LIVE ARENA ACTION & BACKSTABBING FEED
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {events.map((ev, idx) => (
            <div key={idx} style={{
              background: 'var(--bg-secondary)',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span style={{ color: 'var(--text-primary)' }}>{ev.event}</span>
              <span className="mono-val" style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{ev.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
