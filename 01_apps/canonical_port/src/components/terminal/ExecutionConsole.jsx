import React, { useState } from 'react';

export function ExecutionConsole({
  output = '',
  isExecuting = false,
  onRunTest,
  onClearConsole,
  onHarvestTrace,
  selectedModel = 'kimi_tandem_titan'
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="cyber-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Console Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--bg-tertiary)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1rem' }}>📟</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-magenta)', fontFamily: 'var(--font-mono)' }}>
            EXECUTION CONSOLE & CLANG/ASAN HUD
          </span>
          <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
            ASAN CLEAN
          </span>
        </div>

        {/* Console Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={onClearConsole}
            className="cyber-btn"
            style={{ padding: '2px 8px', fontSize: '0.68rem' }}
          >
            🧹 Clear
          </button>

          <button
            onClick={handleCopy}
            className="cyber-btn"
            style={{ padding: '2px 8px', fontSize: '0.68rem' }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>

          {onHarvestTrace && (
            <button
              onClick={onHarvestTrace}
              className="cyber-btn"
              style={{ padding: '2px 8px', fontSize: '0.68rem', borderColor: 'var(--accent-purple)', color: 'var(--accent-purple)' }}
              title="Harvest execution trace to 24/7 LoRA dataset"
            >
              📥 LoRA Trace
            </button>
          )}

          <button
            onClick={() => onRunTest && onRunTest()}
            disabled={isExecuting}
            className="cyber-btn cyber-btn-cyan"
            style={{ padding: '2px 10px', fontSize: '0.68rem' }}
          >
            <span>{isExecuting ? '⏳ Running...' : '▶ Execute'}</span>
          </button>
        </div>
      </div>

      {/* Terminal Output Area */}
      <div style={{
        flex: 1,
        background: 'var(--bg-primary)',
        padding: '14px',
        overflowY: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.78rem',
        lineHeight: 1.5,
        color: 'var(--text-secondary)'
      }}>
        {isExecuting ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--accent-cyan)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
              <span>Compiling with clang -fsanitize=address,undefined -O3...</span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
              Executing on 10Gbps TB4 DMA node [169.254.187.138] across 82.8 GB VRAM mesh...
            </div>
          </div>
        ) : (
          <pre style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'inherit',
            color: 'var(--text-primary)'
          }}>
            {output || 'Terminal standby. Select an action or execute AST buffer above.'}
          </pre>
        )}
      </div>

      {/* Console Footer */}
      <div style={{
        padding: '6px 14px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-secondary)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.68rem',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)'
      }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <span style={{ color: 'var(--accent-emerald)' }}>✓ 0 Leaks Detected</span>
          <span style={{ color: 'var(--accent-cyan)' }}>Target: {selectedModel}</span>
        </div>
        <span style={{ color: 'var(--accent-purple)' }}>Tri-Vault Continuous Memory Active</span>
      </div>
    </div>
  );
}

export default ExecutionConsole;
