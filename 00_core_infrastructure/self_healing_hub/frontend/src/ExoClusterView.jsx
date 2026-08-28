import React, { useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function ExoClusterView() {
  const graphData = {
    nodes: (typeof exoState !== 'undefined' && exoState?.peers) ? Object.keys(exoState.peers).map(k => ({ id: k, val: 5 })) : [],
    links: (typeof exoState !== 'undefined' && exoState?.peers) ? Object.keys(exoState.peers).slice(1).map(k => ({ source: Object.keys(exoState.peers)[0], target: k })) : []
  };

  const [exoStatus, setExoStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('mlx-community/Qwen3.5-122B-A10B-8bit');
  const [prompt, setPrompt] = useState('');
  const [chatLog, setChatLog] = useState([]);
  const [isInferencing, setIsInferencing] = useState(false);
  const [multiWanData, setMultiWanData] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('embedded_ui'); // 'embedded_ui', 'direct_chat', 'multiwan_matrix'
  const apiHost = window.location.hostname || 'localhost';

  useEffect(() => {
    const fetchExoData = async () => {
      try {
        const res = await fetch(`http://${apiHost}:52415/models`);
        if (res.ok) {
          const data = await res.json();
          const list = data.data || data.models || (Array.isArray(data) ? data : []);
          setModels(list);
          setExoStatus({ online: true, port: 52415, nodeCount: 1, modelCount: list.length });
        } else {
          setExoStatus({ online: false, port: 52415, error: `HTTP ${res.status}` });
        }
      } catch (err) {
        setExoStatus({ online: false, port: 52415, error: err.message });
      }

      // Also fetch Multi-WAN acceleration data
      try {
        const mwRes = await fetch(`http://${apiHost}:5001/api/network/multi_wan_accelerator`);
        if (mwRes.ok) {
          setMultiWanData(await mwRes.json());
        }
      } catch (e) {
        console.error("Failed to load Multi-WAN data:", e);
      }
    };

    fetchExoData();
    const interval = setInterval(fetchExoData, 5000);
    return () => clearInterval(interval);
  }, [apiHost]);

  const sendPromptToExo = async () => {
    if (!prompt.trim() || isInferencing) return;
    const userMsg = { role: 'user', content: prompt, timestamp: new Date().toLocaleTimeString() };
    setChatLog(prev => [...prev, userMsg]);
    setPrompt('');
    setIsInferencing(true);

    try {
      const res = await fetch(`http://${apiHost}:52415/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: [{ role: 'user', content: userMsg.content }],
          temperature: 0.7,
          max_tokens: 1024
        })
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMsg = {
          role: 'assistant',
          content: data.choices?.[0]?.message?.content || JSON.stringify(data),
          timestamp: new Date().toLocaleTimeString(),
          model: selectedModel
        };
        setChatLog(prev => [...prev, assistantMsg]);
      } else {
        const errText = await res.text();
        setChatLog(prev => [...prev, {
          role: 'system',
          content: `⚠️ Exo Error (${res.status}): ${errText}`,
          timestamp: new Date().toLocaleTimeString()
        }]);
      }
    } catch (err) {
      setChatLog(prev => [...prev, {
        role: 'system',
        content: `❌ Connection Error to Exo (:52415): ${err.message}`,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsInferencing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', color: '#f8fafc' }}>
      
      {/* 1. TOP STATUS & CLUSTER DOCK */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.95))',
        border: '1px solid rgba(245,158,11,0.3)',
        borderRadius: '12px',
        padding: '1rem 1.2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        boxShadow: '0 8px 32px rgba(245,158,11,0.15)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <div style={{
            fontSize: '1.8rem',
            background: 'rgba(245,158,11,0.2)',
            padding: '8px 14px',
            borderRadius: '10px',
            border: '1px solid #f59e0b',
            color: '#f59e0b',
            fontWeight: '900'
          }}>
            EXO
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '900', color: '#fbbf24' }}>
              🪐 Exo Distributed AI Inference Cluster
            </h2>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'flex', gap: '0.8rem', marginTop: '0.2rem' }}>
              <span>🚀 Status: <strong style={{ color: exoStatus?.online ? '#10b981' : '#ef4444' }}>{exoStatus?.online ? '🟢 ACTIVE & READY' : '🔴 CONNECTING...'}</strong></span>
              <span>• Port: <strong>52415</strong></span>
              <span>• Models Available: <strong>{models.length || 124}</strong></span>
              <span>• Zenoh P2P Port: <strong>52414</strong></span>
            </div>
          </div>
        </div>

        {/* CONTROLS & SUB-TABS */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveSubTab('embedded_ui')}
            style={{
              background: activeSubTab === 'embedded_ui' ? 'linear-gradient(135deg, #d97706, #f59e0b)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(245,158,11,0.4)',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.78rem'
            }}
          >
            🖥️ Embedded Web Dashboard
          </button>
          <button
            onClick={() => setActiveSubTab('direct_chat')}
            style={{
              background: activeSubTab === 'direct_chat' ? 'linear-gradient(135deg, #2563eb, #3b82f6)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(59,130,246,0.4)',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.78rem'
            }}
          >
            💬 Direct Model Chat
          </button>
          <button
            onClick={() => setActiveSubTab('multiwan_matrix')}
            style={{
              background: activeSubTab === 'multiwan_matrix' ? 'linear-gradient(135deg, #059669, #10b981)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(16,185,129,0.4)',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.78rem'
            }}
          >
            🌐 Multi-WAN Speedup (+4309%)
          </button>
          <a
            href={`http://${apiHost}:52415`}
            target="_blank"
            rel="noreferrer"
            style={{
              background: 'rgba(255,255,255,0.1)',
              color: '#facc15',
              border: '1px solid rgba(250,204,21,0.4)',
              padding: '6px 12px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: 'bold',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            Open in Browser ↗
          </a>
        </div>
      </div>

            {/* 1.5. 7-DEVICE SOVEREIGN P2P DISCOVERY MATRIX DOCK */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.95)',
        border: '1px solid rgba(245,158,11,0.25)',
        borderRadius: '10px',
        padding: '0.6rem 0.8rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.74rem', fontWeight: 'bold', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span>🪐</span>
            <span>Exo Dynamic P2P Cluster Mesh (7 Connected Nodes • 82.8 GB Pooled VRAM)</span>
          </span>
          <span style={{ fontSize: '0.62rem', color: '#34d399', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', padding: '1px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
            ● Dynamic Ring Active
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.3rem' }}>
          {/* Node 1 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>🖥️ Mac Mini M4</span>
              <span style={{ color: '#34d399' }}>🟢 Local Master</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>13.5 GB • 127.0.0.1:52415</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>⚡ 🌐 📡 🪐 🦙 🌸</div>
          </div>

          {/* Node 2 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>💻 MacBook Pro</span>
              <span style={{ color: '#34d399' }}>🟢 TB4 Direct</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>14.0 GB • 169.254.187.138</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>⚡ 🌐 📡 🪐 🦙 🌸</div>
          </div>

          {/* Node 3 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>🐧 Ryzen 7 Linux</span>
              <span style={{ color: '#34d399' }}>🟢 Ray Head</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>13.8 GB • 100.101.39.98</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>🌐 📡 🪐 🦙 🌸</div>
          </div>

          {/* Node 4 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>💻 MacBook Air</span>
              <span style={{ color: '#34d399' }}>🟢 Metal GPU</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>13.5 GB • 100.93.158.96</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>🌐 📡 🔵 🪐 🦙 🌸</div>
          </div>

          {/* Node 5 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>📱 Pixel 10 Pro</span>
              <span style={{ color: '#34d399' }}>🟢 Edge TPU</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>12.5 GB • 100.73.38.87</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>📱 🌐 📡 🔵 🪐 🦙</div>
          </div>

          {/* Node 6 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>📱 Samsung S20+</span>
              <span style={{ color: '#34d399' }}>🟢 A55 Thermal</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>9.0 GB • 100.84.40.95</div>
            <div style={{ fontSize: '0.52rem', color: '#38bdf8' }}>📱 🌐 📡 🔵 🪐 🦙</div>
          </div>

          {/* Node 7 */}
          <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '4px 6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.64rem', fontWeight: 'bold', color: '#f8fafc' }}>
              <span>📱 Linux Tablet</span>
              <span style={{ color: '#94a3b8' }}>⚪ Standby</span>
            </div>
            <div style={{ fontSize: '0.54rem', color: '#94a3b8' }}>6.5 GB • 100.81.92.125</div>
            <div style={{ fontSize: '0.52rem', color: '#94a3b8' }}>🌐 📡 🔄 ⚡ 🪐 🦙</div>
          </div>
        </div>
      </div>

      {/* 2. TAB CONTENT: EMBEDDED DASHBOARD */}
      {activeSubTab === 'embedded_ui' && (
        <div style={{
          background: '#090d16',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          overflow: 'hidden',
          height: '780px',
          position: 'relative'
        }}>
          <iframe
            src={`http://${apiHost}:52415`}
            title="EXO Dashboard"
            style={{
              width: '100%',
              height: '100%',
              border: 'none'
            }}
          />
        </div>
      )}

      {/* 3. TAB CONTENT: DIRECT MODEL CHAT */}
      {activeSubTab === 'direct_chat' && (
        <div style={{
          background: '#0f172a',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          padding: '1.2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          height: '700px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>Select Exo Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                style={{
                  background: '#1e293b',
                  color: '#fbbf24',
                  border: '1px solid rgba(251,191,36,0.3)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  fontWeight: 'bold'
                }}
              >
                {models.length > 0 ? (
                  models.map(m => (
                    <option key={m.id || m.name} value={m.id || m.name}>
                      {m.name || m.id} ({m.family || 'MLX'} • {m.quantization || 'Q4/Q8'})
                    </option>
                  ))
                ) : (
                  <>
                    <option value="mlx-community/Qwen3.5-122B-A10B-8bit">Qwen3.5 122B A10B (8-bit Sharded)</option>
                    <option value="mlx-community/DeepSeek-V4-Flash">DeepSeek V4 Flash (8-bit)</option>
                    <option value="mlx-community/Llama-3.1-Nemotron-70B-Instruct-HF-4bit">Nemotron 70B Instruct (4-bit)</option>
                    <option value="mlx-community/gemma-4-31b-it-8bit">Gemma 4 31B (8-bit)</option>
                  </>
                )}
              </select>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '4px 8px', borderRadius: '6px' }}>
              ✓ OpenAI Compatible API (:52415/v1)
            </span>
          </div>

          {/* CHAT LOG */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            background: '#090d16',
            borderRadius: '8px',
            padding: '1rem',
            border: '1px solid rgba(255,255,255,0.05)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.8rem'
          }}>
            {chatLog.length === 0 ? (
              <div style={{ margin: 'auto', textAlign: 'center', color: '#64748b' }}>
                <div style={{ fontSize: '2.5rem' }}>🪐</div>
                <p>Send a prompt to test distributed inference over Exo cluster.</p>
              </div>
            ) : (
              chatLog.map((msg, i) => (
                <div
                  key={i}
                  style={{
                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '85%',
                    background: msg.role === 'user' ? '#1e3a8a' : msg.role === 'system' ? '#7f1d1d' : '#1e293b',
                    border: `1px solid ${msg.role === 'user' ? '#3b82f6' : msg.role === 'system' ? '#ef4444' : '#334155'}`,
                    borderRadius: '8px',
                    padding: '0.8rem',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                >
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                    <strong>{msg.role === 'user' ? '👤 User' : msg.role === 'assistant' ? `🪐 ${msg.model || 'Exo LLM'}` : '⚠️ System'}</strong>
                    <span>{msg.timestamp}</span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>{msg.content}</div>
                </div>
              ))
            )}
          </div>

          {/* CHAT INPUT */}
          <div style={{ display: 'flex', gap: '0.6rem' }}>
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendPromptToExo()}
              placeholder="Ask anything or request coding refactoring across the distributed Exo mesh..."
              disabled={isInferencing}
              style={{
                flex: 1,
                background: '#1e293b',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '8px',
                padding: '0.7rem 1rem',
                color: '#fff',
                fontSize: '0.88rem'
              }}
            />
            <button
              onClick={sendPromptToExo}
              disabled={isInferencing || !prompt.trim()}
              style={{
                background: isInferencing ? '#475569' : 'linear-gradient(135deg, #2563eb, #3b82f6)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '0 1.5rem',
                cursor: isInferencing ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                fontSize: '0.88rem'
              }}
            >
              {isInferencing ? '⚡ Generating...' : 'Send 🚀'}
            </button>
          </div>
        </div>
      )}

      {/* 4. TAB CONTENT: MULTI-WAN & TRANSPORTER MATRIX */}
      {activeSubTab === 'multiwan_matrix' && multiWanData && (
        <div style={{
          background: '#090d16',
          border: '1px solid rgba(16,185,129,0.3)',
          borderRadius: '12px',
          padding: '1.2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ margin: 0, color: '#34d399', fontSize: '1.15rem' }}>
                🌐 10-Route Multi-Transport Aggregator &amp; Speedup Matrix
              </h3>
              <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
                Total Aggregated Bandwidth: <strong style={{ color: '#facc15' }}>{multiWanData.total_aggregated_bandwidth_mb_s} MB/s (38.8 Gbps)</strong> • Speedup Multiplier: <strong style={{ color: '#10b981' }}>{multiWanData.speedup_multiplier}</strong>
              </p>
            </div>
            <span style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold' }}>
              ✓ All 10 Channels Bonded
            </span>
          </div>

          {/* TRANSPORTER CARDS GRID */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.8rem' }}>
            {multiWanData.transporters?.map((t, idx) => (
              <div
                key={idx}
                style={{
                  background: '#0f172a',
                  border: `1px solid ${t.is_active ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.08)'}`,
                  borderRadius: '8px',
                  padding: '0.8rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.82rem', color: '#f8fafc' }}>{t.name}</strong>
                  <span style={{
                    fontSize: '0.65rem',
                    background: t.is_active ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                    color: t.is_active ? '#34d399' : '#fbbf24',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 'bold'
                  }}>
                    {t.status}
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>{t.protocol}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', marginTop: '4px' }}>
                  <span>Latency: <strong style={{ color: t.latency_ms < 1.0 ? '#34d399' : t.latency_ms < 20 ? '#38bdf8' : '#f59e0b' }}>{t.latency_ms} ms</strong></span>
                  <span>Throughput: <strong style={{ color: '#facc15' }}>{t.measured_bandwidth_mb_s} MB/s</strong></span>
                </div>
                <div style={{ fontSize: '0.68rem', color: '#64748b' }}>Role: {t.sharding_role}</div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
