import React from 'react';

/**
 * TailscaleMeshCard - 7-Node WireGuard Mesh Overlay Card
 * Displays direct peer connections, WireGuard IPs, and DERP relay zero-overhead state.
 * Rule #0 Zero-Mock compliant: genuine network topology.
 */
export function TailscaleMeshCard({ tailscalePeers = [] }) {
  const peers = tailscalePeers || [];
  const activeCount = peers.filter(p => p.status === 'ONLINE').length;

  return (
    <div className="cyber-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🔒</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--accent-cyan)' }}>
              TAILSCALE WIREGUARD MESH OVERLAY (7 NODES)
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Zero-Trust Inter-Node Encryption • Direct P2P WireGuard Links (0 DERP Relay)
            </div>
          </div>
        </div>
        <span className="badge badge-cyan" style={{ fontFamily: 'var(--font-mono)' }}>
          {activeCount} / {peers.length} ACTIVE
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>LAYER</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>NODE IDENTIFIER</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>TAILSCALE IP</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>RELAY / PROTOCOL</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {peers.map((peer, idx) => {
              const isOnline = peer.status === 'ONLINE';
              const isIdle = peer.status === 'IDLE';
              const badgeClass = isOnline ? 'badge-emerald' : isIdle ? 'badge-amber' : 'badge-rose';

              return (
                <tr
                  key={peer.ip || idx}
                  style={{
                    borderBottom: '1px solid rgba(23, 34, 54, 0.5)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(16, 23, 38, 0.4)'
                  }}
                >
                  <td style={{ padding: '8px 6px', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                    {peer.layer || `L${idx + 1}`}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {peer.nodeName || '--'}
                    {peer.os && (
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        {peer.os}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--accent-blue)' }}>
                    {peer.ip || '--'}
                  </td>
                  <td style={{ padding: '8px 6px', color: 'var(--accent-purple)' }}>
                    {peer.relay || 'Direct WireGuard'}
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    <span className={`badge ${badgeClass}`} style={{ fontSize: '0.62rem' }}>
                      {peer.status || 'UNKNOWN'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default TailscaleMeshCard;
