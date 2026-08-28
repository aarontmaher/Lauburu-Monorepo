import React, { useState } from 'react';

export const SLASH_COMMANDS = [
  { cmd: '/audit', label: 'Truth Audit', desc: 'Swarm Truth Audit & 0-Simulated Array Check', color: 'badge-emerald' },
  { cmd: '/duel', label: 'FFA Duel', desc: 'Trigger 13-Model FFA tournament round', color: 'badge-amber' },
  { cmd: '/split', label: 'TB4 Shard', desc: 'Configure -ts 28,28,24 GPU Tensor Sharding', color: 'badge-purple' },
  { cmd: '/engine', label: 'Cycle Engine', desc: 'Hot-swap among 8 dynamic inference engines', color: 'badge-cyan' },
  { cmd: '/nodes', label: 'Fleet Matrix', desc: 'Probe 7 physical compute hardware nodes', color: 'badge-cyan' },
  { cmd: '/biometrics', label: '512Hz ECG', desc: 'Inspect Kamath 20% filter and Movesense BLE', color: 'badge-emerald' },
  { cmd: '/restart_daemons', label: 'Keepalive', desc: 'Restart Universal SSH & ADB keepalive daemons', color: 'badge-rose' },
  { cmd: '/key', label: 'Zero-Trust', desc: 'Rotate Tailscale WireGuard & Cloudflare keys', color: 'badge-purple' },
  { cmd: '/cron', label: 'LoRA Harvest', desc: 'Harvest 48 instruction pairs to /lora_datasets/', color: 'badge-cyan' },
  { cmd: '/storage', label: 'Tri-Vault', desc: 'Verify Obsidian, PySpark & Git tree health (<3ms)', color: 'badge-emerald' },
  { cmd: '/ping', label: 'Mesh Ping', desc: 'Sweep 7-Layer Mesh & 0.277ms TB4 DMA latency', color: 'badge-cyan' },
  { cmd: '/revive', label: 'WoL Revive', desc: 'Resurrect sleeping nodes via RFC 792 Magic Packet', color: 'badge-emerald' }
];

export function SlashCommandDock({ onDispatchAction, activeEngine, onCycleEngine }) {
  const [inputVal, setInputVal] = useState('');
  const [lastExecuted, setLastExecuted] = useState(null);
  const [suggestionsVisible, setSuggestionsVisible] = useState(false);

  const handleExecute = (command) => {
    const cmd = command.trim();
    if (!cmd) return;

    if (cmd === '/engine' && onCycleEngine) {
      onCycleEngine();
    }

    if (onDispatchAction) {
      onDispatchAction(cmd);
    }

    setLastExecuted({
      cmd,
      timestamp: new Date().toTimeString().split(' ')[0]
    });
    setInputVal('');
    setSuggestionsVisible(false);

    setTimeout(() => {
      setLastExecuted(null);
    }, 4000);
  };

  const filteredCommands = SLASH_COMMANDS.filter(c =>
    c.cmd.toLowerCase().includes(inputVal.toLowerCase()) ||
    c.label.toLowerCase().includes(inputVal.toLowerCase())
  );

  return (
    <div className="cyber-panel" style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {/* Quick Command Pills Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        overflowX: 'auto',
        paddingBottom: '2px'
      }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          SLASH DOCK:
        </span>
        {SLASH_COMMANDS.map((c) => (
          <button
            key={c.cmd}
            onClick={() => handleExecute(c.cmd)}
            className="cyber-btn"
            style={{
              padding: '2px 8px',
              fontSize: '0.68rem',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--font-mono)'
            }}
            title={c.desc}
          >
            <span style={{ color: 'var(--accent-cyan)' }}>{c.cmd}</span>
            <span style={{ color: 'var(--text-secondary)', marginLeft: '4px' }}>{c.label}</span>
          </button>
        ))}
      </div>

      {/* Interactive Input Line */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', position: 'relative' }}>
        <div style={{
          position: 'relative',
          flex: 1,
          display: 'flex',
          alignItems: 'center'
        }}>
          <span style={{
            position: 'absolute',
            left: '10px',
            color: 'var(--accent-cyan)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            pointerEvents: 'none'
          }}>
            &gt;
          </span>
          <input
            type="text"
            value={inputVal}
            onChange={(e) => {
              setInputVal(e.target.value);
              setSuggestionsVisible(e.target.value.startsWith('/'));
            }}
            onFocus={() => inputVal.startsWith('/') && setSuggestionsVisible(true)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleExecute(inputVal);
              }
            }}
            placeholder="Type / to dispatch mesh commands (/audit, /duel, /split, /engine, /nodes, /revive)..."
            style={{
              width: '100%',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px 6px 26px',
              color: 'var(--text-primary)',
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              outline: 'none'
            }}
          />

          {/* Autocomplete Dropdown */}
          {suggestionsVisible && inputVal.startsWith('/') && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              left: 0,
              right: 0,
              marginBottom: '6px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-sm)',
              boxShadow: 'var(--shadow-panel)',
              maxHeight: '180px',
              overflowY: 'auto',
              zIndex: 50
            }}>
              {filteredCommands.map((c) => (
                <div
                  key={c.cmd}
                  onClick={() => handleExecute(c.cmd)}
                  style={{
                    padding: '6px 12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    borderBottom: '1px solid var(--border-subtle)',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-card-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{c.cmd}</span>
                    <span style={{ color: 'var(--text-primary)' }}>{c.label}</span>
                  </div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>{c.desc}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={() => handleExecute(inputVal || '/audit')}
          className="cyber-btn cyber-btn-cyan"
          style={{ padding: '6px 12px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
        >
          <span>⚡ Execute</span>
        </button>

        {lastExecuted && (
          <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
            ✓ {lastExecuted.cmd} @ {lastExecuted.timestamp}
          </span>
        )}
      </div>
    </div>
  );
}

export default SlashCommandDock;
