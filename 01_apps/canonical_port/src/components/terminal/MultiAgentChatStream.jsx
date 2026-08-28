import React, { useState, useRef, useEffect } from 'react';

export const INITIAL_CHAT_MESSAGES = [
  {
    id: 'msg-1',
    speaker: 'Operator Aaron',
    speakerRole: 'Human Mesh Governor',
    badgeClass: 'badge-rose',
    timestamp: '12:40:12',
    content: 'Review the 10Gbps TB4 DMA interconnect kernel and verify zero-mock invariants for the 82.8 GB pooled VRAM sharding.',
    codeSnippet: null,
    tokens: 28,
    latencyMs: 0
  },
  {
    id: 'msg-2',
    speaker: 'Kimi 88B Tandem Titan',
    speakerRole: 'Strategic Orchestrator (Port 50052)',
    badgeClass: 'badge-cyan',
    timestamp: '12:40:14',
    content: 'Probing TB4 bridge at 169.254.187.138. Confirmed RTT of 0.277ms. Proposing memory-mapped ring buffer structure to guarantee zero allocations during 512Hz ECG biometrics ingestion.',
    codeSnippet: `// Ring buffer structure for lock-free 512Hz ECG streaming
type LockFreeRingBuffer struct {
    head     uint64
    tail     uint64
    capacity uint64
    buffer   []byte
}`,
    codeLang: 'go',
    tokens: 142,
    latencyMs: 14
  },
  {
    id: 'msg-3',
    speaker: 'Qwen 3.8 Max',
    speakerRole: 'Edge Reasoner & Vision Critic',
    badgeClass: 'badge-amber',
    timestamp: '12:40:16',
    content: 'Analyzed AST layout against Apple M4 Pro Metal performance shaders. The capacity must align to 64-byte cache lines to eliminate false sharing during dual-node RPC sharding.',
    codeSnippet: `// 64-byte cache-line aligned buffer segment
struct alignas(64) DMAChannelBuffer {
    std::atomic<uint64_t> write_pos;
    std::atomic<uint64_t> read_pos;
    uint8_t data[4096];
};`,
    codeLang: 'cpp',
    tokens: 118,
    latencyMs: 18
  },
  {
    id: 'msg-4',
    speaker: 'Gemini 3.1 Pro Cloud',
    speakerRole: 'Verification Oracle',
    badgeClass: 'badge-blue',
    timestamp: '12:40:18',
    content: 'Verification passed. Cosine accord index stands at 0.988 across the debate council. LLVM AddressSanitizer (ASan) confirms 0 memory leaks and 0 simulated arrays.',
    codeSnippet: null,
    tokens: 86,
    latencyMs: 124
  }
];

export function MultiAgentChatStream({
  messages = INITIAL_CHAT_MESSAGES,
  onSendMessage,
  onInsertCodeToBuffer,
  onInspectDiff,
  onExecuteCode,
  isStreaming = false,
  activeEngine = 'auto'
}) {
  const [inputText, setInputText] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'agents', 'operator', 'code'
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputText.trim()) return;
    const text = inputText.trim();
    setInputText('');
    if (onSendMessage) {
      onSendMessage(text);
    }
  };

  const handleCopyCode = (code, id) => {
    navigator.clipboard?.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredMessages = messages.filter(msg => {
    if (filterMode === 'agents') return !msg.speaker.includes('Operator');
    if (filterMode === 'operator') return msg.speaker.includes('Operator');
    if (filterMode === 'code') return !!msg.codeSnippet;
    return true;
  });

  return (
    <div className="cyber-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Chat Stream Header */}
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
          <span style={{ fontSize: '1rem' }}>💬</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            MULTI-AGENT SWARM CHAT STREAM
          </span>
          <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
            ENGINE: {activeEngine.toUpperCase()}
          </span>
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {[
            { id: 'all', label: 'All' },
            { id: 'agents', label: 'Agents' },
            { id: 'operator', label: 'Operator' },
            { id: 'code', label: 'Code' }
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setFilterMode(f.id)}
              className="cyber-btn"
              style={{
                padding: '2px 8px',
                fontSize: '0.68rem',
                background: filterMode === f.id ? 'var(--accent-cyan)' : 'transparent',
                color: filterMode === f.id ? '#000' : 'var(--text-secondary)',
                borderColor: filterMode === f.id ? 'var(--accent-cyan)' : 'var(--border-subtle)'
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages Feed */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        background: 'var(--bg-primary)'
      }}>
        {filteredMessages.map((msg) => {
          const isOperator = msg.speaker.includes('Operator');
          const isKimi = msg.speaker.includes('Kimi');
          const isQwen = msg.speaker.includes('Qwen');
          const isGemini = msg.speaker.includes('Gemini');
          const isLlama = msg.speaker.includes('Llama');

          const borderColor = isOperator
            ? 'rgba(244, 63, 94, 0.4)'
            : isKimi
            ? 'rgba(0, 255, 204, 0.4)'
            : isQwen
            ? 'rgba(245, 158, 11, 0.4)'
            : isGemini
            ? 'rgba(56, 189, 248, 0.4)'
            : isLlama
            ? 'rgba(192, 132, 252, 0.4)'
            : 'var(--border-subtle)';

          return (
            <div
              key={msg.id}
              style={{
                background: isOperator ? 'rgba(244, 63, 94, 0.05)' : 'var(--bg-secondary)',
                border: `1px solid ${borderColor}`,
                borderRadius: 'var(--radius-sm)',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              {/* Message Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    fontWeight: 700,
                    fontSize: '0.8rem',
                    fontFamily: 'var(--font-mono)',
                    color: isOperator ? 'var(--accent-rose)' : isKimi ? 'var(--accent-cyan)' : isQwen ? 'var(--accent-amber)' : isGemini ? 'var(--accent-blue)' : 'var(--accent-purple)'
                  }}>
                    {msg.speaker}
                  </span>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    [{msg.speakerRole}]
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                  {msg.tokens && (
                    <span className="badge badge-purple" style={{ fontSize: '0.62rem' }}>
                      {msg.tokens} tok
                    </span>
                  )}
                  {msg.latencyMs > 0 && (
                    <span className="badge badge-cyan" style={{ fontSize: '0.62rem' }}>
                      {msg.latencyMs}ms
                    </span>
                  )}
                  <span style={{ color: 'var(--text-dim)' }}>{msg.timestamp}</span>
                </div>
              </div>

              {/* Message Content */}
              <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                {msg.content}
              </div>

              {/* Code Snippet Box with Actions */}
              {msg.codeSnippet && (
                <div style={{
                  marginTop: '4px',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-strong)',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    padding: '4px 10px',
                    background: 'var(--bg-tertiary)',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.68rem',
                    fontFamily: 'var(--font-mono)'
                  }}>
                    <span style={{ color: 'var(--accent-cyan)' }}>
                      📄 {msg.codeLang ? msg.codeLang.toUpperCase() : 'CODE SNIPPET'}
                    </span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => handleCopyCode(msg.codeSnippet, msg.id)}
                        className="cyber-btn"
                        style={{ padding: '2px 6px', fontSize: '0.65rem' }}
                      >
                        {copiedId === msg.id ? '✓ Copied' : '📋 Copy'}
                      </button>
                      <button
                        onClick={() => onInsertCodeToBuffer && onInsertCodeToBuffer(msg.codeSnippet)}
                        className="cyber-btn cyber-btn-cyan"
                        style={{ padding: '2px 6px', fontSize: '0.65rem' }}
                        title="Insert into AST Live Code Buffer"
                      >
                        📝 Buffer
                      </button>
                      <button
                        onClick={() => onInspectDiff && onInspectDiff(msg.codeSnippet)}
                        className="cyber-btn"
                        style={{ padding: '2px 6px', fontSize: '0.65rem', borderColor: 'var(--accent-amber)', color: 'var(--accent-amber)' }}
                        title="Compare Diff with Current Buffer"
                      >
                        🔍 Diff
                      </button>
                      <button
                        onClick={() => onExecuteCode && onExecuteCode(msg.codeSnippet)}
                        className="cyber-btn"
                        style={{ padding: '2px 6px', fontSize: '0.65rem', borderColor: 'var(--accent-emerald)', color: 'var(--accent-emerald)' }}
                        title="Execute in ASan Sandbox"
                      >
                        ▶ Run
                      </button>
                    </div>
                  </div>
                  <pre style={{
                    margin: 0,
                    padding: '10px',
                    fontSize: '0.74rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--accent-emerald)',
                    overflowX: 'auto',
                    lineHeight: 1.4
                  }}>
                    {msg.codeSnippet}
                  </pre>
                </div>
              )}
            </div>
          );
        })}

        {isStreaming && (
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px dashed var(--accent-cyan)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <span style={{ fontSize: '1rem', animation: 'spin 1s linear infinite' }}>⚙️</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
              Swarm multi-beam reasoning in progress across 7 physical nodes...
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Footer */}
      <form
        onSubmit={handleSend}
        style={{
          padding: '10px 12px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'var(--bg-secondary)',
          display: 'flex',
          gap: '8px',
          alignItems: 'center'
        }}
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Prompt multi-agent swarm (or type /audit, /duel, /split, /engine)..."
          disabled={isStreaming}
          style={{
            flex: 1,
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 12px',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            outline: 'none'
          }}
        />
        <button
          type="submit"
          disabled={isStreaming || !inputText.trim()}
          className="cyber-btn cyber-btn-cyan"
          style={{ padding: '8px 16px', fontSize: '0.78rem' }}
        >
          <span>{isStreaming ? '⏳ Thinking' : '🚀 Send'}</span>
        </button>
      </form>
    </div>
  );
}

export default MultiAgentChatStream;
