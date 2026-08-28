import React, { useState } from 'react';

export function TriOrchestratorDebatePanel({
  debateState,
  onTriggerNextTurn,
  onResetDebate,
  onHarvestLoRA,
  onTriggerStagnation,
  onTriggerCodeOff
}) {
  const [customTopic, setCustomTopic] = useState('');
  const turns = debateState?.turns || [];
  const accord = debateState?.cosineAccord || 0.984;
  const isHighAccord = accord >= 0.98;
  const accordPercent = Math.min(100, Math.max(0, Math.round((accord - 0.90) / 0.10 * 100)));

  const handleStartTopic = (e) => {
    e.preventDefault();
    if (customTopic.trim()) {
      onResetDebate(customTopic.trim());
      setCustomTopic('');
    }
  };

  return (
    <div className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Debate Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1rem' }}>⚖️</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              TRI-ORCHESTRATOR LIVE DEBATE COUNCIL
            </span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            <span style={{ color: 'var(--text-muted)' }}>TOPIC: </span>
            <span style={{ color: 'var(--accent-cyan)', fontWeight: 500 }}>{debateState?.topic}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span className={`badge ${isHighAccord ? 'badge-emerald' : 'badge-amber'}`} style={{ fontSize: '0.68rem' }}>
            ACCORD: {accord}
          </span>
          <span className="badge badge-purple" style={{ fontSize: '0.68rem' }}>
            {debateState?.status || 'DELIBERATING'}
          </span>
          {debateState?.codeOffActive && (
            <span className="badge badge-rose" style={{ fontSize: '0.68rem' }}>● CODE-OFF</span>
          )}
        </div>
      </div>

      {/* Accord Progress Meter */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: 'var(--text-muted)' }}>COSINE ACCORD GAUGE (Threshold &gt;0.980)</span>
          <span style={{ color: isHighAccord ? 'var(--accent-emerald)' : 'var(--accent-amber)', fontWeight: 700 }}>
            {accord} / 1.000 ({accordPercent}%)
          </span>
        </div>
        <div className="telemetry-bar-bg" style={{ height: '6px' }}>
          <div
            className="telemetry-bar-fill"
            style={{
              width: `${accordPercent}%`,
              background: isHighAccord
                ? 'linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald))'
                : 'linear-gradient(90deg, var(--accent-amber), var(--accent-rose))'
            }}
          />
        </div>
      </div>

      {/* Action Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        <button
          className="cyber-btn cyber-btn-cyan"
          style={{ padding: '4px 10px', fontSize: '0.72rem' }}
          onClick={() => onTriggerNextTurn()}
          disabled={debateState?.isDebating}
        >
          {debateState?.isDebating ? '⏳ Deliberating...' : '▶ Next Turn'}
        </button>

        <button
          className="cyber-btn cyber-btn-amber"
          style={{ padding: '4px 8px', fontSize: '0.72rem' }}
          onClick={() => onTriggerCodeOff ? onTriggerCodeOff() : onTriggerStagnation && onTriggerStagnation()}
          title="Deadlock Resolution: Autonomous AST Code-Off Benchmark"
        >
          ⚔️ Code-Off
        </button>

        <button
          className="cyber-btn"
          style={{ padding: '4px 8px', fontSize: '0.72rem' }}
          onClick={onHarvestLoRA}
          title="Harvest validated debate turns to 24/7 LoRA JSONL dataset"
        >
          📥 Harvest LoRA
        </button>

        <button
          className="cyber-btn cyber-btn-rose"
          style={{ padding: '4px 8px', fontSize: '0.72rem' }}
          onClick={onTriggerStagnation}
          title="Human Operator Escalation Fallback"
        >
          ⚠️ Escalate
        </button>
      </div>

      {/* Topic Input Bar */}
      <form onSubmit={handleStartTopic} style={{ display: 'flex', gap: '6px' }}>
        <input
          type="text"
          placeholder="Inject new debate prompt or architectural dispute..."
          value={customTopic}
          onChange={(e) => setCustomTopic(e.target.value)}
          style={{
            flex: 1,
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            color: 'var(--text-primary)',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            outline: 'none'
          }}
        />
        <button type="submit" className="cyber-btn" style={{ padding: '6px 10px', fontSize: '0.72rem' }}>
          <span>🎯 Inject</span>
        </button>
      </form>

      {/* Deliberation Turns Feed */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        maxHeight: '260px',
        overflowY: 'auto',
        paddingRight: '4px'
      }}>
        {turns.map((turn, idx) => {
          const isKimi = turn.speaker.includes('Kimi');
          const isQwen = turn.speaker.includes('Qwen');
          const isGemini = turn.speaker.includes('Gemini');
          const isOperator = turn.speaker.includes('Operator');

          return (
            <div
              key={idx}
              style={{
                background: 'var(--bg-secondary)',
                border: isOperator
                  ? '1px solid var(--accent-rose)'
                  : isKimi
                  ? '1px solid rgba(0,255,204,0.3)'
                  : isQwen
                  ? '1px solid rgba(245,158,11,0.3)'
                  : isGemini
                  ? '1px solid rgba(56,189,248,0.3)'
                  : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{
                    fontWeight: 700,
                    fontSize: '0.78rem',
                    color: isOperator ? 'var(--accent-rose)' : isKimi ? 'var(--accent-cyan)' : isQwen ? 'var(--accent-amber)' : 'var(--accent-blue)'
                  }}>
                    {turn.speaker}
                  </span>
                  <span style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                    [{turn.speakerRole}]
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.65rem', fontFamily: 'var(--font-mono)' }}>
                  <span className="badge badge-emerald" style={{ fontSize: '0.58rem' }}>CONF {turn.confidence}</span>
                  <span style={{ color: 'var(--text-dim)' }}>{turn.timestamp}</span>
                </div>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                {turn.content}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TriOrchestratorDebatePanel;
