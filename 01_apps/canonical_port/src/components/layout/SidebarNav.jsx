import React from 'react';

export function SidebarNav({
  activeRoute,
  setActiveRoute,
  isSidebarCollapsed,
  toggleSidebar
}) {
  const navSections = [
    {
      title: '0. BARE-METAL NETWORKING (PRIMARY)',
      items: [
        { id: 'network-metrics', label: 'Bare-Metal Networking', icon: '📡', badge: 'PRIMARY', hotkey: 'n' }
      ]
    },
    {
      title: '1. HARDWARE & NODES',
      items: [
        { id: 'hardware-nodes', label: 'Hardware & Nodes', icon: '⚡', badge: '7 NODES', hotkey: 'h' },
        { id: 'optimization-hardware', label: 'Hardware Sentinel HUD', icon: '🖥️', badge: 'PORT 18802' }
      ]
    },
    {
      title: '2. MEDICAL BIOMETRICS & DSP',
      items: [
        { id: 'biometrics-dsp', label: 'Medical Biometrics & DSP', icon: '🫀', badge: '512Hz ECG', hotkey: 'b' }
      ]
    },
    {
      title: '3. LOCAL AI INFERENCE & SYNTHESIS',
      items: [
        { id: 'agi-terminal', label: 'AGI Coding Terminal', icon: '💻', badge: 'SCREEN 1', hotkey: 'c' },
        { id: 'ai-inference', label: 'Local AI Inference Mesh', icon: '🤖', badge: 'RPC :50052', hotkey: 'i' }
      ]
    },
    {
      title: '4. LOCAL AI TRAINING & GAMES',
      items: [
        { id: 'training-lora', label: 'LoRA Distillation Monitor', icon: '🔥', badge: '24/7 SFT', hotkey: 't' },
        { id: 'training-games', label: 'Implemented Games Arena', icon: '🎮', badge: '13-FFA' },
        { id: 'training-metrics', label: 'Structural AST Metrics', icon: '📊', badge: '3.29M LOC' },
        { id: 'training-traces', label: 'Execution Action Traces', icon: '📜', badge: 'LEDGER' }
      ]
    },
    {
      title: '5. MASTER AGI GOVERNANCE',
      items: [
        { id: 'governance', label: 'Master AGI Governance', icon: '🧠', badge: '>0.98 ACCORD', hotkey: 'g' },
        { id: 'leaderboard', label: 'Swarm ELO Leaderboard', icon: '🏆', badge: 'TOP 10' },
        { id: 'structural-graph', label: '3D Structural Graph', icon: '🌐', badge: 'OBSIDIAN', hotkey: 'x' }
      ]
    },
    {
      title: '6. TOOLING & COMMERCE',
      items: [
        { id: 'tooling-commerce', label: 'Tooling & Commerce Hub', icon: '🧰', badge: '12 MCP' }
      ]
    },
    {
      title: 'OPTIMIZATION SHELLS',
      items: [
        { id: 'optimization-software', label: 'Software & ASan', icon: '🛠️', badge: 'COMPILER' },
        { id: 'optimization-internet', label: 'Internet & Multi-WAN', icon: '🌐', badge: '10-ROUTE' },
        { id: 'optimization-storage', label: 'Storage & Tri-Vault', icon: '💾', badge: 'DFS SYNC', hotkey: 'o' }
      ]
    }
  ];

  return (
    <aside style={{
      width: isSidebarCollapsed ? '64px' : '260px',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      transition: 'width 0.2s ease',
      zIndex: 20
    }}>
      {/* Sidebar Header */}
      <div style={{
        height: '60px',
        padding: isSidebarCollapsed ? '0' : '0 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: isSidebarCollapsed ? 'center' : 'space-between',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        {!isSidebarCollapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.2rem' }}>💠</span>
            <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-cyan)' }}>
              LAUBURU MESH
            </span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="cyber-btn"
          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
          title={isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isSidebarCollapsed ? '▶' : '◀'}
        </button>
      </div>

      {/* Navigation List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 8px' }}>
        {navSections.map((section, idx) => (
          <div key={idx} style={{ marginBottom: '16px' }}>
            {!isSidebarCollapsed && (
              <div style={{
                fontSize: '0.66rem',
                fontWeight: 700,
                color: 'var(--text-muted)',
                letterSpacing: '0.08em',
                padding: '4px 8px 6px',
                fontFamily: 'var(--font-mono)'
              }}>
                {section.title}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {section.items.map((item) => {
                const isActive = activeRoute === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveRoute(item.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: isSidebarCollapsed ? 'center' : 'space-between',
                      padding: isSidebarCollapsed ? '10px 0' : '7px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: isActive ? 'rgba(0, 255, 204, 0.12)' : 'transparent',
                      border: isActive ? '1px solid rgba(0, 255, 204, 0.3)' : '1px solid transparent',
                      color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontFamily: 'inherit',
                      transition: 'all 0.15s ease'
                    }}
                    title={item.hotkey ? `${item.label} (Press [${item.hotkey}])` : item.label}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.95rem' }}>{item.icon}</span>
                      {!isSidebarCollapsed && (
                        <span style={{ fontSize: '0.8rem', fontWeight: isActive ? 600 : 400 }}>
                          {item.label}
                        </span>
                      )}
                    </div>
                    {!isSidebarCollapsed && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {item.hotkey && (
                          <span style={{
                            fontSize: '0.62rem',
                            fontFamily: 'var(--font-mono)',
                            color: isActive ? 'var(--accent-cyan)' : 'var(--text-dim)',
                            background: 'rgba(255,255,255,0.04)',
                            padding: '1px 4px',
                            borderRadius: '2px',
                            border: '1px solid rgba(255,255,255,0.08)'
                          }}>
                            [{item.hotkey}]
                          </span>
                        )}
                        {item.badge && (
                          <span className={`badge ${isActive ? 'badge-cyan' : 'badge-amber'}`} style={{ fontSize: '0.6rem' }}>
                            {item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Sidebar Footer */}
      {!isSidebarCollapsed && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-tertiary)',
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)'
        }}>
          <div>NODE: Mac_Node (L1 Host)</div>
          <div style={{ color: 'var(--accent-emerald)', marginTop: '2px' }}>● 7 / 7 NODES ONLINE</div>
        </div>
      )}
    </aside>
  );
}

export default SidebarNav;
