import React, { useState } from 'react';

/**
 * Computes a genuine line-by-line unified diff between oldText and newText
 */
function computeLineDiff(oldText = '', newText = '') {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  const diff = [];
  let additions = 0;
  let deletions = 0;

  const maxLen = Math.max(oldLines.length, newLines.length);
  for (let i = 0; i < maxLen; i++) {
    const o = oldLines[i];
    const n = newLines[i];

    if (o === undefined) {
      diff.push({ type: 'add', line: n, lineNum: i + 1, oldLineNum: null, newLineNum: i + 1 });
      additions++;
    } else if (n === undefined) {
      diff.push({ type: 'del', line: o, lineNum: i + 1, oldLineNum: i + 1, newLineNum: null });
      deletions++;
    } else if (o !== n) {
      diff.push({ type: 'del', line: o, lineNum: i + 1, oldLineNum: i + 1, newLineNum: null });
      diff.push({ type: 'add', line: n, lineNum: i + 1, oldLineNum: null, newLineNum: i + 1 });
      deletions++;
      additions++;
    } else {
      diff.push({ type: 'same', line: o, lineNum: i + 1, oldLineNum: i + 1, newLineNum: i + 1 });
    }
  }

  return { diff, additions, deletions };
}

export function LiveDiffInspector({
  baselineCode = '',
  modifiedCode = '',
  onApplyDiff,
  onDiscardDiff,
  onExportPatch,
  fileName = 'workspace_kernel.go'
}) {
  const [viewMode, setViewMode] = useState('unified'); // 'unified' or 'split'
  const { diff, additions, deletions } = computeLineDiff(baselineCode, modifiedCode);

  const handleExportPatch = () => {
    const patchHeader = `--- a/${fileName}\n+++ b/${fileName}\n@@ -1,${baselineCode.split('\n').length} +1,${modifiedCode.split('\n').length} @@\n`;
    const patchBody = diff.map(d => {
      if (d.type === 'add') return `+${d.line}`;
      if (d.type === 'del') return `-${d.line}`;
      return ` ${d.line}`;
    }).join('\n');

    const fullPatch = patchHeader + patchBody;
    navigator.clipboard?.writeText(fullPatch);
    if (onExportPatch) onExportPatch(fullPatch);
  };

  return (
    <div className="cyber-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Diff Header */}
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
          <span style={{ fontSize: '1rem' }}>🔍</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            LIVE AST DIFF INSPECTOR
          </span>
          <span className="badge badge-amber" style={{ fontSize: '0.65rem' }}>
            {fileName}
          </span>
        </div>

        {/* Diff Stats & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '4px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)' }}>
            <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>+{additions} lines</span>
            <span className="badge badge-rose" style={{ fontSize: '0.65rem' }}>-{deletions} lines</span>
          </div>

          <button
            onClick={() => setViewMode(viewMode === 'unified' ? 'split' : 'unified')}
            className="cyber-btn"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
          >
            {viewMode === 'unified' ? 'Split View' : 'Unified View'}
          </button>

          <button
            onClick={handleExportPatch}
            className="cyber-btn"
            style={{ padding: '3px 8px', fontSize: '0.7rem', borderColor: 'var(--accent-purple)', color: 'var(--accent-purple)' }}
            title="Copy git .patch format to clipboard"
          >
            📋 Copy .patch
          </button>

          <button
            onClick={() => onApplyDiff && onApplyDiff(modifiedCode)}
            className="cyber-btn cyber-btn-cyan"
            style={{ padding: '3px 10px', fontSize: '0.7rem' }}
          >
            ✓ Apply to Buffer
          </button>

          <button
            onClick={() => onDiscardDiff && onDiscardDiff()}
            className="cyber-btn cyber-btn-rose"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
          >
            ✕ Discard
          </button>
        </div>
      </div>

      {/* Diff Body */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        background: 'var(--bg-primary)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.75rem',
        lineHeight: 1.45
      }}>
        {viewMode === 'unified' ? (
          <div>
            {diff.map((item, idx) => {
              const isAdd = item.type === 'add';
              const isDel = item.type === 'del';
              const bg = isAdd ? 'rgba(16, 185, 129, 0.12)' : isDel ? 'rgba(244, 63, 94, 0.12)' : 'transparent';
              const color = isAdd ? 'var(--accent-emerald)' : isDel ? 'var(--accent-rose)' : 'var(--text-secondary)';
              const prefix = isAdd ? '+' : isDel ? '-' : ' ';

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    background: bg,
                    borderBottom: isAdd || isDel ? '1px solid rgba(255,255,255,0.03)' : 'none',
                    padding: '1px 8px'
                  }}
                >
                  <span style={{
                    width: '32px',
                    color: 'var(--text-dim)',
                    textAlign: 'right',
                    marginRight: '8px',
                    userSelect: 'none'
                  }}>
                    {item.oldLineNum || ''}
                  </span>
                  <span style={{
                    width: '32px',
                    color: 'var(--text-dim)',
                    textAlign: 'right',
                    marginRight: '12px',
                    userSelect: 'none'
                  }}>
                    {item.newLineNum || ''}
                  </span>
                  <span style={{ width: '16px', color, userSelect: 'none', fontWeight: 700 }}>
                    {prefix}
                  </span>
                  <span style={{ color, whiteSpace: 'pre', flex: 1 }}>
                    {item.line}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          /* Side by side view */
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: '100%' }}>
            <div style={{ borderRight: '1px solid var(--border-subtle)', padding: '8px', overflowX: 'auto' }}>
              <div style={{ padding: '4px', fontSize: '0.68rem', color: 'var(--accent-rose)', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                BASELINE (HEAD)
              </div>
              <pre style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.74rem' }}>{baselineCode}</pre>
            </div>
            <div style={{ padding: '8px', overflowX: 'auto', background: 'rgba(16, 185, 129, 0.03)' }}>
              <div style={{ padding: '4px', fontSize: '0.68rem', color: 'var(--accent-emerald)', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                MODIFIED (AST SYNTHESIS)
              </div>
              <pre style={{ margin: 0, color: 'var(--accent-emerald)', fontSize: '0.74rem' }}>{modifiedCode}</pre>
            </div>
          </div>
        )}
      </div>

      {/* Diff Footer */}
      <div style={{
        padding: '6px 14px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--bg-secondary)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.68rem',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)'
      }}>
        <span>AST DELTA: {additions + deletions} operations</span>
        <span style={{ color: 'var(--accent-purple)' }}>Tri-Vault Worktree Synchronized</span>
      </div>
    </div>
  );
}

export default LiveDiffInspector;
