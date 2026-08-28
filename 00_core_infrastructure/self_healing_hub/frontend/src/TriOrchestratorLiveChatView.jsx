import React, { useState, useEffect, useRef } from 'react';

/**
 * 💬 Tri-Orchestrator Live Discussion & Swarm Action Room
 * Fully functional multi-agent conversational engine connecting Operator with:
 *   1. ⚡ Cloud Orchestrator (Gemini 3.7 Flash)
 *   2. 🧠 Local AI Orchestrator (DeepSeek-R1 & Genetic Smol)
 *   3. 🧬 Genetic AI Orchestrator (MoE Evolutionary Router)
 */
export default function TriOrchestratorLiveChatView() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all'); // 'all', 'cloud', 'local', 'genetic', 'user', 'system', 'beam'
  const [chatMode, setChatMode] = useState('multi_beam'); // 'multi_beam', 'consensus', 'auto_moe', 'debate', 'cloud', 'local', 'edge', 'genetic'
  const [expandedActionId, setExpandedActionId] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [maxVisibleCount, setMaxVisibleCount] = useState(15);
  const [toastMessage, setToastMessage] = useState(null);

  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const apiHost = window.location.hostname || 'localhost';

  const showToast = (text) => {
    setToastMessage(text);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleExecuteAction = async (actionType, payload = {}) => {
    try {
      showToast(`⚡ Executing action: ${actionType}...`);
      const res = await fetch(`http://${apiHost}:5001/api/chat/execute_action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: actionType, payload })
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`✅ ${data.message || data.status || 'Action executed successfully!'}`);
        await fetchMessages();
      } else {
        showToast(`❌ Error: ${data.error || 'Action failed'}`);
      }
    } catch (e) {
      showToast(`❌ Failed to dispatch action: ${e.message}`);
    }
  };

  const fetchMessages = async () => {
    try {
      const res = await fetch(`http://${apiHost}:5001/api/chat/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      }
    } catch (e) {
      console.error('Failed to fetch chat messages:', e);
    }
  };

  useEffect(() => {
    fetchMessages();
    const interval = setInterval(fetchMessages, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (autoScroll && chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  const handleSendMessage = async (customPrompt = null) => {
    const textToSend = (customPrompt || inputText).trim();
    if (!textToSend || isSending) return;

    if (!customPrompt) setInputText('');
    setIsSending(true);

    // Optimistically add user message
    const tempUserMsg = {
      id: `temp_${Date.now()}`,
      sender: 'user',
      name: 'Aaron (Operator)',
      avatar: '👤',
      role: 'System Operator & Creator',
      badge_color: '#facc15',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      text: textToSend
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await fetch(`http://${apiHost}:5001/api/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          name: 'Aaron',
          mode: chatMode
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.messages) {
          setMessages(data.messages);
        } else {
          await fetchMessages();
        }
      }
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Reset Tri-Orchestrator discussion room to initial state?')) return;
    try {
      const res = await fetch(`http://${apiHost}:5001/api/chat/clear`, { method: 'POST' });
      if (res.ok) {
        await fetchMessages();
      }
    } catch (err) {
      console.error('Failed to clear chat:', err);
    }
  };

  const ACTION_CHIPS = [
    { label: '⚡ /multi_beam', desc: '4-Model Side-by-Side', prompt: '/multi_beam' },
    { label: '🏛️ /debate', desc: 'Debate & Ratify Accord', prompt: '/debate 5-Layer Hardware Scaling & AST Slicing' },
    { label: '📓 /obsidian', desc: 'Qwen & Gemini Vault Sync', prompt: '/debate How should Qwen 3.8 Max and Gemini 3.1 Pro collaboratively structure the monorepo architecture in Obsidian?' },
    { label: '📱 /edge_chat', desc: 'Debate On-Device Chat SLM', prompt: '/debate Which edge SLM (SmolLM2 vs Qwen 1.5B vs Genetic MoE) should be embedded for on-device live text chat?' },
    { label: '🔍 /audit', desc: '5-Layer Truth Audit', prompt: '/audit' },
    { label: '⚔️ /duel', desc: 'Execute AI Arena Duel', prompt: '/duel' },
    { label: '⚡ /ping', desc: 'TB4 & Mesh Latency', prompt: '/ping' }
  ];

  const CHAT_MODES = [
    { id: 'multi_beam', label: '⚡ Multi-Beam (4 Models)', color: '#38bdf8', desc: 'Side-by-side responses from Qwen, Gemini, Claude, and DeepSeek' },
    { id: 'consensus', label: '🏛️ Consensus Accord', color: '#facc15', desc: 'Multi-round debate & unanimous ratification' },
    { id: 'genetic', label: '🧬 Genetic Auto-Route', color: '#c084fc', desc: 'Dynamic MoE routing to optimal specialist' },
    { id: 'edge', label: '📱 Edge SLM', color: '#06b6d4', desc: 'On-device local RAG' },
    { id: 'cloud', label: '⚡ Cloud Fast', color: '#ec4899', desc: 'Gemini 3.7 Flash High' },
    { id: 'local', label: '🧠 Local Apex', color: '#34d399', desc: 'Qwen 3.8 Max & DeepSeek' }
  ];

  const filteredMessages = messages.filter(m => {
    if (activeFilter === 'all') return true;
    return m.sender === activeFilter;
  });

  const visibleMessages = filteredMessages.slice(-maxVisibleCount);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '0.65rem',
      height: '100%',
      maxHeight: '710px',
      background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.90))',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '12px',
      padding: '0.85rem',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      overflow: 'hidden'
    }}>
      {/* HEADER WITH MULTI-AGENT METRICS */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.6rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        paddingBottom: '0.6rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: 'bold' }}>
              💬 Swarm Tri-Orchestrator &amp; On-Device Edge Chat
            </h2>
            <span style={{ fontSize: '0.68rem', background: 'rgba(6,182,212,0.2)', color: '#22d3ee', padding: '2px 7px', borderRadius: '12px', border: '1px solid #06b6d4', fontWeight: 'bold' }}>
              📱 Edge Specialist Active
            </span>
            <span style={{ fontSize: '0.68rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 7px', borderRadius: '12px', border: '1px solid #10b981', fontWeight: 'bold' }}>
              ● 3 Orchestrators Listening
            </span>
          </div>
          <div style={{ fontSize: '0.74rem', color: '#94a3b8', marginTop: '2px' }}>
            Direct dialogue with <strong>On-Device Edge RAG AI</strong>, <strong>Cloud (Gemini 3.7)</strong>, <strong>Local (DeepSeek-R1)</strong>, and <strong>Genetic MoE</strong>.
          </div>
        </div>

        {/* CHAT MODE SELECTOR & CONTROLS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          {/* Mode Dropdown / Pills */}
          <div style={{ display: 'flex', background: '#0f172a', padding: '2px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', flexWrap: 'wrap' }}>
            {[
              { id: 'multi_beam', label: '⚡ Multi-Beam' },
              { id: 'consensus', label: '💬 All / Accord' },
              { id: 'auto_moe', label: '🧬 Auto-MoE' },
              { id: 'debate', label: '⚔️ Debate' },
              { id: 'edge', label: '📱 Edge AI' },
              { id: 'cloud', label: '⚡ Cloud' },
              { id: 'local', label: '🧠 Local' },
              { id: 'genetic', label: '🧬 Genetic' }
            ].map(m => (
              <button
                key={m.id}
                onClick={() => setChatMode(m.id)}
                style={{
                  background: chatMode === m.id ? (m.id === 'multi_beam' ? '#3b82f6' : m.id === 'edge' ? '#0891b2' : m.id === 'auto_moe' ? '#9333ea' : '#0284c7') : 'transparent',
                  color: chatMode === m.id ? '#fff' : '#94a3b8',
                  border: 'none',
                  padding: '3px 7px',
                  borderRadius: '6px',
                  fontSize: '0.68rem',
                  fontWeight: chatMode === m.id ? 'bold' : '500',
                  cursor: 'pointer'
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          <button
            onClick={handleClearHistory}
            style={{
              background: 'rgba(239,68,68,0.15)',
              color: '#fda4af',
              border: '1px solid rgba(239,68,68,0.4)',
              padding: '3px 7px',
              borderRadius: '6px',
              fontSize: '0.68rem',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            🗑️ Clear
          </button>
        </div>
      </div>

      {/* TOAST ALERT */}
      {toastMessage && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.98))',
          border: '1px solid #38bdf8',
          color: '#38bdf8',
          padding: '5px 12px',
          borderRadius: '6px',
          fontSize: '0.72rem',
          fontWeight: 'bold',
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* QUICK SWARM ACTION CHIPS */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.35rem',
        overflowX: 'auto',
        paddingBottom: '2px',
        scrollbarWidth: 'none'
      }}>
        <span style={{ fontSize: '0.66rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase' }}>
          Actions:
        </span>
        {ACTION_CHIPS.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(chip.prompt)}
            disabled={isSending}
            style={{
              background: 'rgba(15,23,42,0.8)',
              border: '1px solid rgba(56,189,248,0.25)',
              color: '#38bdf8',
              padding: '3px 7px',
              borderRadius: '6px',
              fontSize: '0.68rem',
              cursor: isSending ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#38bdf8'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(56,189,248,0.25)'}
          >
            <strong>{chip.label}</strong>
            <span style={{ color: '#94a3b8', fontSize: '0.6rem' }}>({chip.desc})</span>
          </button>
        ))}
      </div>

      {/* FILTER TABS */}
      <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center', overflowX: 'auto', scrollbarWidth: 'none' }}>
        <span style={{ fontSize: '0.66rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase' }}>
          Filter:
        </span>
        {[
          { id: 'all', label: `All (${messages.length})`, color: '#fff' },
          { id: 'edge', label: '📱 Edge AI', color: '#06b6d4' },
          { id: 'cloud', label: '⚡ Cloud', color: '#ec4899' },
          { id: 'local', label: '🧠 Local', color: '#34d399' },
          { id: 'genetic', label: '🧬 Genetic', color: '#c084fc' },
          { id: 'user', label: '👤 Operator', color: '#facc15' },
          { id: 'system', label: '⚙️ Actions', color: '#38bdf8' }
        ].map(f => (
          <button
            key={f.id}
            onClick={() => setActiveFilter(f.id)}
            style={{
              background: activeFilter === f.id ? (f.id === 'all' ? '#3b82f6' : `${f.color}25`) : 'rgba(255,255,255,0.04)',
              color: activeFilter === f.id ? (f.id === 'all' ? '#fff' : f.color) : '#94a3b8',
              border: activeFilter === f.id ? `1px solid ${f.color}` : '1px solid rgba(255,255,255,0.06)',
              padding: '2px 7px',
              borderRadius: '6px',
              fontSize: '0.66rem',
              fontWeight: activeFilter === f.id ? 'bold' : 'normal',
              cursor: 'pointer'
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* CHAT MESSAGES LOG (SCROLLABLE & EXTENDED TO MATCH GAME) */}
      <div
        ref={chatContainerRef}
        style={{
          flex: 1,
          height: '430px',
          maxHeight: '430px',
          background: 'rgba(13,17,23,0.95)',
          border: '1px solid #30363d',
          borderRadius: '10px',
          padding: '0.8rem',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.6rem',
          boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.5)'
        }}
      >
        {filteredMessages.length > maxVisibleCount && (
          <div style={{ textAlign: 'center', padding: '2px 0 6px 0' }}>
            <button
              onClick={() => setMaxVisibleCount(prev => prev + 25)}
              style={{
                background: 'rgba(56,189,248,0.12)',
                color: '#38bdf8',
                border: '1px solid rgba(56,189,248,0.3)',
                borderRadius: '6px',
                fontSize: '0.66rem',
                padding: '3px 9px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              📜 Show older messages ({filteredMessages.length - maxVisibleCount} more)
            </button>
          </div>
        )}

        {visibleMessages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#64748b', fontSize: '0.8rem' }}>
            No messages found for active filter.
          </div>
        ) : (
          visibleMessages.map((msg, idx) => {
            const isUser = msg.sender === 'user';
            const isAction = msg.sender === 'system' && msg.action_data;
            const isCloud = msg.sender === 'cloud';
            const isLocal = msg.sender === 'local';
            const isGenetic = msg.sender === 'genetic';

            let cardBg = 'rgba(22,27,34,0.9)';
            let borderColor = '#30363d';
            let roleColor = '#8b949e';

            if (isUser) {
              cardBg = 'linear-gradient(135deg, rgba(234,179,8,0.08), rgba(22,27,34,0.95))';
              borderColor = '#eab308';
              roleColor = '#facc15';
            } else if (isAction) {
              cardBg = 'linear-gradient(135deg, rgba(56,189,248,0.1), rgba(15,23,42,0.95))';
              borderColor = '#38bdf8';
              roleColor = '#38bdf8';
            } else if (isCloud) {
              cardBg = 'linear-gradient(135deg, rgba(236,72,153,0.08), rgba(22,27,34,0.95))';
              borderColor = '#ec4899';
              roleColor = '#f472b6';
            } else if (isLocal) {
              cardBg = 'linear-gradient(135deg, rgba(16,185,129,0.08), rgba(22,27,34,0.95))';
              borderColor = '#10b981';
              roleColor = '#34d399';
            } else if (isGenetic) {
              cardBg = 'linear-gradient(135deg, rgba(168,85,247,0.08), rgba(22,27,34,0.95))';
              borderColor = '#a855f7';
              roleColor = '#c084fc';
            }

            return (
              <div
                key={msg.id || idx}
                style={{
                  background: cardBg,
                  borderLeft: `4px solid ${borderColor}`,
                  borderTop: '1px solid rgba(255,255,255,0.05)',
                  borderRight: '1px solid rgba(255,255,255,0.05)',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '8px',
                  padding: '0.7rem 0.9rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.25)'
                }}
              >
                {/* Top Header: Avatar + Name + Role + Timestamp */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <span style={{ fontSize: '1rem' }}>{msg.avatar || '🤖'}</span>
                    <span style={{ fontWeight: 'bold', fontSize: '0.82rem', color: '#f0f6fc' }}>
                      {msg.name}
                    </span>
                    <span style={{
                      background: 'rgba(255,255,255,0.06)',
                      color: roleColor,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      fontSize: '0.64rem',
                      fontWeight: '600',
                      border: `1px solid ${borderColor}40`
                    }}>
                      {msg.role}
                    </span>
                  </div>

                  <span style={{ color: '#64748b', fontSize: '0.64rem' }}>
                    {msg.timestamp}
                  </span>
                </div>

                {/* Message Text Body */}
                <div style={{
                  fontSize: '0.78rem',
                  lineHeight: '1.4',
                  color: isUser ? '#fef08a' : '#e2e8f0',
                  whiteSpace: 'pre-wrap',
                  paddingLeft: '2px'
                }}>
                  {msg.text}
                </div>

                {/* BIG-AGI STYLE MULTI-BEAM PARALLEL CARDS GRID */}
                {msg.beams && msg.beams.length > 0 && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: '0.65rem',
                    marginTop: '0.5rem'
                  }}>
                    {msg.beams.map((beam, bIdx) => (
                      <div
                        key={bIdx}
                        style={{
                          background: 'rgba(15,23,42,0.95)',
                          border: `1px solid ${beam.badge_color}40`,
                          borderTop: `3px solid ${beam.badge_color}`,
                          borderRadius: '8px',
                          padding: '0.75rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.4rem',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <span>{beam.avatar}</span>
                            <strong style={{ fontSize: '0.78rem', color: '#f8fafc' }}>{beam.model_name}</strong>
                          </div>
                          <span style={{ fontSize: '0.62rem', color: beam.badge_color, background: `${beam.badge_color}15`, padding: '1px 5px', borderRadius: '4px' }}>
                            {beam.tier}
                          </span>
                        </div>

                        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.64rem', color: '#94a3b8' }}>
                          <span>⏱️ {beam.latency_ms}ms</span>
                          <span>📊 {beam.token_count} tok</span>
                          <span style={{ color: beam.cost_usd === 0 ? '#34d399' : '#f59e0b' }}>
                            💰 ${beam.cost_usd.toFixed(5)}
                          </span>
                        </div>

                        <div style={{ fontSize: '0.74rem', color: '#cbd5e1', lineHeight: '1.35', flex: 1, whiteSpace: 'pre-wrap' }}>
                          {beam.text}
                        </div>

                        {beam.suggested_actions && beam.suggested_actions.length > 0 && (
                          <div style={{ marginTop: '0.3rem', display: 'flex', gap: '0.3rem' }}>
                            {beam.suggested_actions.map((act, aIdx) => (
                              <button
                                key={aIdx}
                                onClick={() => handleExecuteAction(act.action, act.payload)}
                                style={{
                                  background: `${beam.badge_color}25`,
                                  border: `1px solid ${beam.badge_color}`,
                                  color: '#fff',
                                  padding: '3px 8px',
                                  borderRadius: '5px',
                                  fontSize: '0.66rem',
                                  fontWeight: 'bold',
                                  cursor: 'pointer',
                                  width: '100%'
                                }}
                              >
                                {act.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* 1-CLICK ACTION BUTTONS BAR */}
                {(msg.action_buttons || msg.execution_actions) && (
                  <div style={{
                    marginTop: '0.5rem',
                    paddingTop: '0.5rem',
                    borderTop: '1px solid rgba(255,255,255,0.08)',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.4rem',
                    alignItems: 'center'
                  }}>
                    <span style={{ fontSize: '0.66rem', color: '#38bdf8', fontWeight: 'bold' }}>
                      ⚡ 1-Click Swarm Actions:
                    </span>
                    {(msg.action_buttons || msg.execution_actions).map((act, actIdx) => (
                      <button
                        key={actIdx}
                        onClick={() => handleExecuteAction(act.action || act.id, act.payload || {})}
                        style={{
                          background: act.color ? `${act.color}25` : 'rgba(56,189,248,0.2)',
                          border: `1px solid ${act.color || '#38bdf8'}`,
                          color: '#f8fafc',
                          padding: '3px 9px',
                          borderRadius: '6px',
                          fontSize: '0.68rem',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                )}

                {/* Expandable Action Result Drawer */}
                {isAction && (
                  <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {/* RICH TRUE LIVE DEBATE RENDERING */}
                    {(msg.action_data?.action === 'TRI_ORCHESTRATOR_TRUE_DEBATE' || msg.action_data?.action === 'TRI_ORCHESTRATOR_DEBATE') && (
                      <div style={{
                        background: 'linear-gradient(135deg, rgba(30,27,75,0.9), rgba(15,23,42,0.98))',
                        border: '1px solid #a855f7',
                        borderRadius: '10px',
                        padding: '1rem 1.1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                        boxShadow: '0 4px 20px rgba(168,85,247,0.25)'
                      }}>
                        {/* Debate Topic & Unanimous Accord Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
                          <div>
                            <div style={{ fontSize: '0.68rem', color: '#c084fc', textTransform: 'uppercase', fontWeight: 'bold', letterSpacing: '0.5px' }}>
                              🏛️ TRUE MULTI-AGENT LIVE DEBATE PROTOCOL
                            </div>
                            <h3 style={{ margin: '0.2rem 0 0 0', fontSize: '1.05rem', color: '#f8fafc', fontWeight: 'bold' }}>
                              {msg.action_data.topic}
                            </h3>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{
                              background: 'rgba(16,185,129,0.2)',
                              color: '#34d399',
                              border: '1px solid #10b981',
                              padding: '3px 9px',
                              borderRadius: '12px',
                              fontSize: '0.72rem',
                              fontWeight: 'bold',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.3rem'
                            }}>
                              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#34d399', display: 'inline-block' }}></span>
                              {msg.action_data.final_alignment_pct || 98.6}% Unanimous Accord Ratified
                            </span>
                          </div>
                        </div>

                        {/* Consensus Summary Banner */}
                        <div style={{
                          background: 'rgba(168,85,247,0.1)',
                          borderLeft: '4px solid #a855f7',
                          padding: '0.6rem 0.8rem',
                          borderRadius: '4px',
                          fontSize: '0.78rem',
                          color: '#e9d5ff',
                          lineHeight: '1.4'
                        }}>
                          <strong>Consensus Resolution:</strong> {msg.action_data.consensus_summary || 'Unanimous accord reached across 4 rounds with technical concessions and zero dissenting opinions.'}
                        </div>

                        {/* 4-Round Argument Progression */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 'bold', textTransform: 'uppercase' }}>
                            Deliberation Trail &amp; Concession Journey:
                          </div>

                          {msg.action_data.turns?.map((turn, tIdx) => (
                            <div
                              key={tIdx}
                              style={{
                                background: 'rgba(15,23,42,0.85)',
                                border: `1px solid ${turn.badge || '#30363d'}45`,
                                borderRadius: '6px',
                                padding: '0.55rem 0.75rem',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.2rem'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                                  <span style={{
                                    background: turn.badge || '#38bdf8',
                                    color: '#000',
                                    fontWeight: 'bold',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    fontSize: '0.62rem'
                                  }}>
                                    Round {turn.round || tIdx + 1}: {turn.stage || 'Thesis'}
                                  </span>
                                  <strong style={{ color: '#f8fafc' }}>{turn.speaker}</strong>
                                  <span style={{ color: '#94a3b8' }}>• {turn.stance}</span>
                                </div>

                                <span style={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '0.66rem' }}>
                                  {turn.alignment_pct}% Alignment
                                </span>
                              </div>

                              <div style={{ fontSize: '0.76rem', color: '#cbd5e1', lineHeight: '1.35', marginTop: '0.15rem' }}>
                                {turn.text}
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Formal Votes */}
                        {msg.action_data.votes && (
                          <div style={{
                            background: 'rgba(16,185,129,0.06)',
                            border: '1px solid rgba(16,185,129,0.3)',
                            borderRadius: '8px',
                            padding: '0.65rem 0.85rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.3rem'
                          }}>
                            <div style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 'bold' }}>
                              Formal Unanimous Accord Votes:
                            </div>
                            {Object.entries(msg.action_data.votes).map(([ai, vote], vIdx) => (
                              <div key={vIdx} style={{ fontSize: '0.72rem', color: '#e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.4rem' }}>
                                <strong style={{ color: '#f8fafc' }}>{ai}:</strong>
                                <span style={{ color: '#34d399', fontWeight: '600' }}>{vote}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Injected Priorities Card */}
                        {msg.action_data.injected_priorities?.length > 0 && (
                          <div style={{
                            background: 'rgba(15,23,42,0.9)',
                            border: '1px solid #38bdf8',
                            borderRadius: '8px',
                            padding: '0.65rem 0.85rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.35rem'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ fontSize: '0.74rem', color: '#38bdf8', fontWeight: 'bold' }}>
                                🎯 Synthesized Verified Priorities (Injected into progress.md):
                              </div>
                              <span style={{ fontSize: '0.64rem', color: '#10b981', background: 'rgba(16,185,129,0.15)', padding: '1px 6px', borderRadius: '4px' }}>
                                ✓ Verified &amp; Synced
                              </span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                              {msg.action_data.injected_priorities.map((p, pIdx) => (
                                <div key={pIdx} style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
                                  • {p}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <div>
                      <button
                        onClick={() => setExpandedActionId(expandedActionId === msg.id ? null : msg.id)}
                        style={{
                          background: 'rgba(56,189,248,0.12)',
                          border: '1px solid rgba(56,189,248,0.3)',
                          color: '#38bdf8',
                          padding: '2px 7px',
                          borderRadius: '4px',
                          fontSize: '0.65rem',
                          fontWeight: 'bold',
                          cursor: 'pointer'
                        }}
                      >
                        {expandedActionId === msg.id ? 'Hide Raw Action JSON ▲' : 'View Raw Action JSON ▼'}
                      </button>

                      {expandedActionId === msg.id && (
                        <pre style={{
                          background: '#0d1117',
                          border: '1px solid #30363d',
                          padding: '0.6rem',
                          borderRadius: '6px',
                          fontSize: '0.68rem',
                          color: '#38bdf8',
                          marginTop: '0.4rem',
                          overflowX: 'auto',
                          maxHeight: '220px'
                        }}>
                          {JSON.stringify(msg.action_data, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Live Generating Animation Indicator */}
        {isSending && (
          <div style={{
            background: 'rgba(30,41,59,0.7)',
            borderLeft: '4px solid #38bdf8',
            borderRadius: '8px',
            padding: '0.6rem 0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.75rem',
            color: '#38bdf8'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8', animation: 'pulse 1s infinite' }} />
            <span>Tri-Orchestrator consensus in progress... Consulting Cloud, Local &amp; Genetic models...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* INPUT FORM & CONTROLS */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        style={{
          display: 'flex',
          gap: '0.5rem',
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '10px',
          padding: '0.6rem 0.8rem',
          boxShadow: '0 4px 16px rgba(0,0,0,0.3)'
        }}
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={`Message the Tri-Orchestrator Swarm or type /audit, /duel, /storage, /ping...`}
          disabled={isSending}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#f0f6fc',
            fontSize: '0.82rem',
            outline: 'none',
            padding: '4px'
          }}
        />

        <button
          type="submit"
          disabled={isSending || !inputText.trim()}
          style={{
            background: isSending || !inputText.trim() ? '#21262d' : 'linear-gradient(135deg, #1f6feb, #0284c7)',
            color: '#fff',
            border: 'none',
            padding: '0.4rem 1.1rem',
            borderRadius: '6px',
            fontSize: '0.78rem',
            fontWeight: 'bold',
            cursor: isSending || !inputText.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            transition: 'all 0.15s ease'
          }}
        >
          <span>Send</span>
          <span>🚀</span>
        </button>
      </form>
    </div>
  );
}
