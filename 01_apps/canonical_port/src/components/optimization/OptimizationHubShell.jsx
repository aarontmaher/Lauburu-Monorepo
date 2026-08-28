import React from 'react';

export function OptimizationHubShell({
  activeModule,
  onSelectModule,
  moduleTitle,
  moduleDescription,
  children
}) {
  const modules = [
    { id: 'optimization-hardware', label: '1. Hardware Optimization', icon: '⚡' },
    { id: 'optimization-software', label: '2. Software & ASan', icon: '🛠️' },
    { id: 'optimization-internet', label: '3. Internet & Multi-WAN', icon: '🌐' },
    { id: 'optimization-storage', label: '4. Storage & Tri-Vault', icon: '💾' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Sub-Nav */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>{moduleTitle}</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {moduleDescription}
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', gap: '4px' }}>
          {modules.map((m) => (
            <button
              key={m.id}
              onClick={() => onSelectModule(m.id)}
              className="cyber-btn"
              style={{
                background: activeModule === m.id ? 'rgba(0, 255, 204, 0.15)' : 'transparent',
                borderColor: activeModule === m.id ? 'var(--accent-cyan)' : 'transparent',
                color: activeModule === m.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                fontSize: '0.78rem'
              }}
            >
              <span>{m.icon} {m.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Module Mount Point Container */}
      <div style={{ position: 'relative' }}>
        {children}
      </div>
    </div>
  );
}
