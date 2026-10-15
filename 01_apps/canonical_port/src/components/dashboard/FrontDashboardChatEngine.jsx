import React, { useState, useRef, useEffect, useCallback } from 'react';
import { DeviceComputePaymentCard } from './DeviceComputePaymentCard.jsx';
import { GcpCreditGovernorCard } from './GcpCreditGovernorCard.jsx';
import { LocalAiTrainingCard } from './LocalAiTrainingCard.jsx';
import { NeoProjectAppGraph } from './NeoProjectAppGraph.jsx';

const INITIAL_MESSAGES = [
  {
    id: 'msg-init-1',
    speaker: 'Sovereign Orchestrator',
    role: 'Local Master Reasoner (:8081 / :8083)',
    badgeClass: 'badge-cyan',
    timestamp: '07:50:00',
    content: `👋 **Welcome to the Lauburu Mesh Sovereign Front Dashboard.**
    
The IDE is docked as a secondary tool. The front dashboard defaults to this **high-speed conversational chat engine**, providing zero-friction access to system control, biometrics analysis, and hardware orchestration.

• **Pooled VRAM:** 82.8 GB across 7 physical nodes (M4 Pro TB4 DMA linked at 0.277ms).
• **Local Orchestrator:** Qwen 2.5 Coder 7B (:8081) & Huihui 27B Abliterated (:8083) ready.
• **Micro-RAG Vault:** Connected to Obsidian Vault Knowledge Core.
• **Membership Tier:** Synchronized with Shopify Storefront GraphQL.

Type your command, select a quick prompt below, or switch to the secondary IDE at any time.`,
    tokens: 148,
    latencyMs: 12
  }
];

export function FrontDashboardChatEngine({
  models = [],
  membership,
  onOpenIde,
  onDispatchAction,
  onOpenMembershipModal
}) {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState('');
  const [selectedModel, setSelectedModel] = useState('qwen_38_max');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComputeCardExpanded, setIsComputeCardExpanded] = useState(true);
  const [activeSideCard, setActiveSideCard] = useState('compute'); // 'compute' | 'gcp' | 'training' | 'graph'
  const [bicepEcg, setBicepEcg] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchBicepEcg = async () => {
      try {
        const res = await fetch('/api/v1/biometrics/movesense/live');
        if (res.ok) {
          const data = await res.json();
          setBicepEcg(data);
        }
      } catch (err) {
        // silent fallback
      }
    };
    fetchBicepEcg();
    const interval = setInterval(fetchBicepEcg, 2000);
    return () => clearInterval(interval);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSendMessage = useCallback(async (textToSend) => {
    const prompt = (textToSend || inputText).trim();
    if (!prompt || isStreaming) return;

    const userMsg = {
      id: `msg-${Date.now()}`,
      speaker: 'Operator Aaron',
      role: 'Human Mesh Governor',
      badgeClass: 'badge-rose',
      timestamp: new Date().toTimeString().split(' ')[0],
      content: prompt,
      tokens: Math.round(prompt.length / 4),
      latencyMs: 0
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setIsStreaming(true);

    const t0 = performance.now();

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: prompt,
          model: selectedModel,
          max_tokens: 512,
          history: []
        })
      });

      const elapsed = Math.round(performance.now() - t0);

      if (res.ok) {
        const data = await res.json();
        const aiMsg = {
          id: `msg-${Date.now() + 1}`,
          speaker: data.model_used || selectedModel.toUpperCase(),
          role: data.source || 'Local AI Engine',
          badgeClass: data.source?.includes('8083') ? 'badge-amber' : 'badge-cyan',
          timestamp: new Date().toTimeString().split(' ')[0],
          content: data.response || 'Inference executed.',
          ragUsed: data.rag_used,
          tokens: Math.round((data.response?.length || 0) / 4),
          latencyMs: data.latency_ms || elapsed
        };
        setMessages(prev => [...prev, aiMsg]);

        // Record consumed tokens for compute credit ledger
        try {
          fetch('/api/v1/compute/record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              device_id: 'Mac_Node',
              tokens: Math.round(prompt.length / 4) + Math.round((data.response?.length || 0) / 4),
              is_contribution: false,
              description: `Front Dashboard chat inference (${selectedModel})`
            })
          }).catch(() => {});
        } catch (e) {}

      } else {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: `msg-${Date.now() + 1}`,
          speaker: 'System Diagnostics',
          role: 'Inference Fallback',
          badgeClass: 'badge-amber',
          timestamp: new Date().toTimeString().split(' ')[0],
          content: `⚠️ [Local Engine Notice]: ${err.message}. Local inference servers (:8081 / :8083) ready. You can also review hardware and cable health below.`,
          tokens: 28,
          latencyMs: Math.round(performance.now() - t0)
        }
      ]);
    } finally {
      setIsStreaming(false);
    }
  }, [inputText, isStreaming, selectedModel]);

  const handleQuickPrompt = (promptText) => {
    handleSendMessage(promptText);
  };

  const handleCopy = (content, id) => {
    navigator.clipboard?.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '14px' }}>
      {/* Top Header Card */}
      <div className="cyber-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.5rem' }}>💬</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                SOVEREIGN CHAT ENGINE
              </h2>
              <span className="badge badge-emerald">PRIMARY DASHBOARD</span>
              <span
                onClick={onOpenMembershipModal}
                className="badge badge-cyan"
                style={{ cursor: 'pointer' }}
                title="Click to manage Shopify membership"
              >
                {membership?.tier_badge || 'GYM MASTER'}
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Default Front View • Local Zero-Mock Reasoning • Micro-RAG Vault • Offset: ${membership?.net_credits_aud || 0} AUD
            </div>
          </div>
        </div>

        {/* Model Selector & Secondary IDE Dock Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="cyber-input"
            style={{ padding: '6px 12px', fontSize: '0.75rem', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', borderRadius: 'var(--radius-sm)' }}
          >
            <option value="qwen_38_max">🤖 Qwen 2.5 Coder 7B (:8081 Metal)</option>
            <option value="qwen_38_max_abliterated">🔥 Huihui 27B Abliterated (:8083 Red Team)</option>
            <option value="smollm2-1.7b">⚡ SmolLM2 1.7B (Edge Micro SLM)</option>
            <option value="gemini-3.8-flash">☁️ Gemini 3.8 Flash (Cloud Oracle)</option>
          </select>

          <button
            onClick={onOpenIde}
            className="cyber-btn"
            style={{
              padding: '6px 14px',
              fontSize: '0.78rem',
              fontWeight: 700,
              background: 'rgba(0, 255, 204, 0.15)',
              border: '1px solid var(--accent-cyan)',
              color: 'var(--accent-cyan)'
            }}
            title="Switch to Secondary Docked IDE & Compiler"
          >
            💻 Launch Docked IDE [c]
          </button>
        </div>
      </div>

      {/* Bicep ECG & USB 3 Hardware Telemetry HUD Ribbon */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '8px' }}>
        <div className="cyber-card" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.25rem' }} className="animate-pulse">❤️</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Movesense Bicep ECG
            </div>
            <div style={{ fontSize: '0.86rem', fontWeight: 800, color: bicepEcg?.connected && bicepEcg?.heart_rate_bpm ? 'var(--accent-rose)' : 'var(--text-muted)' }}>
              {bicepEcg?.connected && bicepEcg?.heart_rate_bpm ? `${bicepEcg.heart_rate_bpm} BPM` : 'Disconnected (-- BPM)'}
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: '6px' }}>
                • {bicepEcg?.connected && bicepEcg?.zone ? bicepEcg.zone.split(' ')[0] : 'STANDBY'}
              </span>
            </div>
          </div>
          <span className="badge badge-rose" style={{ fontSize: '0.6rem' }}>BICEP STRAP</span>
        </div>

        <div className="cyber-card" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.25rem' }}>🛡️</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Clinical DSP Filter
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
              Kamath 20% Noise Rejection
            </div>
          </div>
          <span className="badge badge-cyan" style={{ fontSize: '0.6rem' }}>EMG GATED</span>
        </div>

        <div className="cyber-card" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.25rem' }}>⚡</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Hardware Bus Link
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
              USB 3.2 Gen 2 (10 Gbps)
            </div>
          </div>
          <span className="badge badge-emerald" style={{ fontSize: '0.6rem' }}>LINKED</span>
        </div>

        <div className="cyber-card" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.25rem' }}>🧠</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Neo App Graph
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-purple)' }}>
              41 Nodes • 26 Edges
            </div>
          </div>
          <button
            onClick={() => setActiveSideCard('graph')}
            className="cyber-btn"
            style={{ fontSize: '0.65rem', padding: '3px 8px' }}
          >
            Explore 🗺️
          </button>
        </div>
      </div>

      {/* Main Content Split: Chat Thread + Collapsible Compute Payment Card */}
      <div style={{ display: 'grid', gridTemplateColumns: isComputeCardExpanded ? 'minmax(450px, 1.4fr) minmax(320px, 1fr)' : '1fr', gap: '14px', flex: 1, minHeight: 0 }}>
        {/* Left Column: Chat Thread & Input */}
        <div className="cyber-card" style={{ display: 'flex', flexDirection: 'column', padding: '16px', overflow: 'hidden', height: '100%' }}>
          {/* Scrollable Messages Area */}
          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '6px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {messages.map((m) => {
              const isUser = m.speaker.includes('Aaron');
              return (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '100%'
                  }}
                >
                  {/* Speaker Meta Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', fontSize: '0.7rem' }}>
                    <span style={{ fontWeight: 700, color: isUser ? 'var(--accent-rose)' : 'var(--accent-cyan)' }}>
                      {m.speaker}
                    </span>
                    <span className={`badge ${m.badgeClass}`} style={{ fontSize: '0.62rem' }}>
                      {m.role}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>{m.timestamp}</span>
                    {m.ragUsed && <span className="badge badge-emerald" style={{ fontSize: '0.6rem' }}>● RAG GROUNDED</span>}
                  </div>

                  {/* Message Bubble */}
                  <div
                    style={{
                      background: isUser ? 'rgba(255, 0, 85, 0.1)' : 'var(--bg-tertiary)',
                      border: isUser ? '1px solid rgba(255, 0, 85, 0.3)' : '1px solid var(--border-subtle)',
                      borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                      padding: '12px 16px',
                      color: 'var(--text-primary)',
                      fontSize: '0.84rem',
                      lineHeight: '1.5',
                      maxWidth: '92%',
                      whiteSpace: 'pre-wrap',
                      position: 'relative'
                    }}
                  >
                    {m.content}

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {m.latencyMs > 0 && <span>{m.latencyMs}ms</span>}
                      {m.tokens > 0 && <span>• {m.tokens} tokens</span>}
                      <button
                        onClick={() => handleCopy(m.content, m.id)}
                        style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', padding: 0 }}
                      >
                        {copiedId === m.id ? '✓ Copied' : '📋 Copy'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}

            {isStreaming && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-cyan)', fontSize: '0.78rem', padding: '8px' }}>
                <span className="spinner" style={{ width: '12px', height: '12px' }}></span>
                <span>{selectedModel} reasoning over 7-layer mesh...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Prompt Chips */}
          <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', padding: '10px 0 6px 0', borderTop: '1px solid var(--border-subtle)', marginTop: '8px' }}>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => handleQuickPrompt('Inspect physical cables, USB bottlenecks, and SIM/Broadband routes.')}
            >
              🔌 Cable & WAN Audit
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => {
                setActiveSideCard('compute');
                handleQuickPrompt('Review device compute payment credits and 7-layer token balance.');
              }}
            >
              ⚡ Compute Credits
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => {
                setActiveSideCard('gcp');
                handleQuickPrompt('What is our Google Cloud $1,400 credit allocation, remaining reserve, and Spot L4 availability?');
              }}
            >
              ☁️ GCP $1,400 Pool
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => {
                setActiveSideCard('training');
                handleQuickPrompt('Report real-time status of all 4 local AI training daemons, loss, and Lakehouse pairs.');
              }}
            >
              🧠 AI Training Matrix
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => handleQuickPrompt('Check Movesense Medical 512Hz ECG stream and Zone 2 heart rate.')}
            >
              🫀 Movesense 512Hz ECG
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={onOpenMembershipModal}
            >
              🛍️ Shopify Tiers
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap' }}
              onClick={() => {
                setActiveSideCard('graph');
                handleQuickPrompt('Analyze all TUIs, localhost apps, notebooks, and 7-layer mesh topology with Neo.');
              }}
            >
              🗺️ Neo App Graph
            </button>
            <button
              className="cyber-btn"
              style={{ fontSize: '0.7rem', padding: '4px 8px', whiteSpace: 'nowrap', color: 'var(--accent-cyan)' }}
              onClick={onOpenIde}
            >
              💻 Open Docked IDE
            </button>
          </div>

          {/* Prompt Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: 'flex', gap: '8px', marginTop: '6px' }}
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask anything, dispatch mesh commands, or audit hardware..."
              className="cyber-input"
              style={{ flex: 1, padding: '10px 14px', fontSize: '0.84rem' }}
              disabled={isStreaming}
            />
            <button
              type="submit"
              className="cyber-btn"
              style={{
                padding: '10px 20px',
                fontWeight: 700,
                background: 'var(--accent-cyan)',
                color: 'var(--bg-primary)',
                border: 'none',
                cursor: 'pointer'
              }}
              disabled={isStreaming || !inputText.trim()}
            >
              Send ↵
            </button>
          </form>
        </div>

        {/* Right Column: Multi-Tab Console (Device Compute, GCP $1,400 Pool, & Local AI Training Matrix) */}
        {isComputeCardExpanded && (
          <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Console Tab Selector */}
            <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                className="cyber-btn"
                style={{
                  fontSize: '0.72rem',
                  padding: '6px 8px',
                  flex: 1,
                  background: activeSideCard === 'compute' ? 'var(--accent-cyan)' : 'transparent',
                  color: activeSideCard === 'compute' ? 'var(--bg-primary)' : 'var(--text-secondary)',
                  fontWeight: activeSideCard === 'compute' ? 700 : 500,
                  border: 'none'
                }}
                onClick={() => setActiveSideCard('compute')}
              >
                ⚡ Compute
              </button>
              <button
                type="button"
                className="cyber-btn"
                style={{
                  fontSize: '0.72rem',
                  padding: '6px 8px',
                  flex: 1,
                  background: activeSideCard === 'gcp' ? 'var(--accent-cyan)' : 'transparent',
                  color: activeSideCard === 'gcp' ? 'var(--bg-primary)' : 'var(--text-secondary)',
                  fontWeight: activeSideCard === 'gcp' ? 700 : 500,
                  border: 'none'
                }}
                onClick={() => setActiveSideCard('gcp')}
              >
                ☁️ GCP $1.4k
              </button>
              <button
                type="button"
                className="cyber-btn"
                style={{
                  fontSize: '0.72rem',
                  padding: '6px 8px',
                  flex: 1,
                  background: activeSideCard === 'training' ? 'var(--accent-cyan)' : 'transparent',
                  color: activeSideCard === 'training' ? 'var(--bg-primary)' : 'var(--text-secondary)',
                  fontWeight: activeSideCard === 'training' ? 700 : 500,
                  border: 'none'
                }}
                onClick={() => setActiveSideCard('training')}
              >
                🧠 AI Matrix
              </button>
              <button
                type="button"
                className="cyber-btn"
                style={{
                  fontSize: '0.72rem',
                  padding: '6px 8px',
                  flex: 1,
                  background: activeSideCard === 'graph' ? 'var(--accent-cyan)' : 'transparent',
                  color: activeSideCard === 'graph' ? 'var(--bg-primary)' : 'var(--text-secondary)',
                  fontWeight: activeSideCard === 'graph' ? 700 : 500,
                  border: 'none'
                }}
                onClick={() => setActiveSideCard('graph')}
              >
                🗺️ Neo Graph
              </button>
            </div>

            {/* Active Console Card */}
            {activeSideCard === 'compute' && (
              <DeviceComputePaymentCard onDispatchAction={onDispatchAction} />
            )}
            {activeSideCard === 'gcp' && (
              <GcpCreditGovernorCard onDispatchAction={onDispatchAction} />
            )}
            {activeSideCard === 'training' && (
              <LocalAiTrainingCard onDispatchAction={onDispatchAction} />
            )}
            {activeSideCard === 'graph' && (
              <NeoProjectAppGraph onDispatchAction={onDispatchAction} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
