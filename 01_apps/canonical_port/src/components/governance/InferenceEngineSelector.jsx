import React from 'react';

export const INFERENCE_ENGINES = [
  {
    id: 'auto',
    name: 'Auto-Routing Mesh Governor',
    tag: 'DYNAMIC ROUTER',
    layer: 'L0-L6',
    port: 'Multi-Port',
    vram: 'Dynamic (0-82.8 GB)',
    context: '128K - 2M',
    latencyClass: 'SUB-MS TO 120MS',
    color: 'badge-emerald',
    desc: 'Local-first zero-cost routing with Cloudflare/Frontier fallback.'
  },
  {
    id: 'kimi_tandem',
    name: 'Kimi 88B Titan (Dual TB4 RPC)',
    tag: 'TB4 SHARDED',
    layer: 'L1 + L2 (Mac + MBP)',
    port: '50052',
    vram: '46.0 GB VRAM',
    context: '256K tokens',
    latencyClass: '0.277ms (TB4 DMA)',
    color: 'badge-cyan',
    desc: 'Dual-node 10Gbps Thunderbolt 4 sharded reasoner.'
  },
  {
    id: 'llama_rpc',
    name: 'llama.cpp Metal GPU Fleet',
    tag: 'LOCAL RPC',
    layer: 'L1, L2, L5',
    port: '8081-8084',
    vram: '28.5 GB VRAM',
    context: '64K tokens',
    latencyClass: '1.4ms (Metal DMA)',
    color: 'badge-cyan',
    desc: 'Apple Silicon Metal Performance Shaders cluster.'
  },
  {
    id: 'qwen_local',
    name: 'Qwen 3.8 Max (Edge Vision/GGUF)',
    tag: 'EDGE TPU',
    layer: 'L6 (Pixel 10 Pro XL)',
    port: '8082',
    vram: '12.5 GB AI Cap',
    context: '32K tokens',
    latencyClass: '1.8ms (NPU)',
    color: 'badge-amber',
    desc: 'Tensor G5 Edge TPU vision & biometrics critic.'
  },
  {
    id: 'exo',
    name: 'Exo P2P Decentralized Tensor Ring',
    tag: 'P2P RING',
    layer: 'L1-L5 Mesh',
    port: '52415',
    vram: '54.0 GB Pooled',
    context: '128K tokens',
    latencyClass: '4.2ms (Zero-Copy Ring)',
    color: 'badge-purple',
    desc: 'Dynamic topology peer-to-peer ring pipeline.'
  },
  {
    id: 'petals',
    name: 'Petals Swarm DHT Heterogeneous',
    tag: 'SWARM DHT',
    layer: 'L3 + L4 (Linux Nodes)',
    port: '31337',
    vram: '20.3 GB Pooled',
    context: '64K tokens',
    latencyClass: '12.5ms (DHT Block)',
    color: 'badge-purple',
    desc: 'Fault-tolerant distributed layer pipeline.'
  },
  {
    id: 'gemini',
    name: 'Gemini 3.1 Pro / 3.7 Flash Cloud',
    tag: 'CLOUD ORACLE',
    layer: 'Google Vertex AI',
    port: 'HTTPS',
    vram: 'Infinite Cloud',
    context: '1M - 2M tokens',
    latencyClass: '124ms (WAN)',
    color: 'badge-blue',
    desc: 'Verification oracle and multimodal code inspector.'
  },
  {
    id: 'cloudflare',
    name: 'Cloudflare Workers AI Gateway',
    tag: 'EDGE GATEWAY',
    layer: 'Cloudflare Workers',
    port: 'Edge REST',
    vram: 'Serverless Edge',
    context: '128K - 200K',
    latencyClass: '24.2ms (Edge)',
    color: 'badge-rose',
    desc: 'Frontier fallback: GPT-4o, Claude 3.5 Sonnet, DeepSeek R1.'
  }
];

export function InferenceEngineSelector({ activeEngine = 'auto', onSelectEngine }) {
  const current = INFERENCE_ENGINES.find(e => e.id === activeEngine) || INFERENCE_ENGINES[0];

  return (
    <div className="cyber-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1rem' }}>⚡</span>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            8-ENGINE INFERENCE SELECTOR
          </span>
        </div>
        <span className={`badge ${current.color}`} style={{ fontSize: '0.68rem' }}>
          {current.tag}
        </span>
      </div>

      {/* Engine Grid Selector */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '6px'
      }}>
        {INFERENCE_ENGINES.map((engine, idx) => {
          const isSelected = engine.id === activeEngine;
          return (
            <button
              key={engine.id}
              onClick={() => onSelectEngine && onSelectEngine(engine.id)}
              className="cyber-btn"
              style={{
                padding: '6px 8px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '2px',
                background: isSelected ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
                borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                boxShadow: isSelected ? 'var(--shadow-glow-cyan)' : 'none',
                textAlign: 'left'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)' }}>
                  [{idx + 1}] {engine.id}
                </span>
                {isSelected && <span style={{ color: 'var(--accent-emerald)', fontSize: '0.65rem' }}>●</span>}
              </div>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>
                {engine.layer}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Engine Detail Card */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius-sm)',
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-mono)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong style={{ color: 'var(--accent-cyan)' }}>{current.name}</strong>
          <span style={{ color: 'var(--text-muted)' }}>Port: {current.port}</span>
        </div>

        <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', lineHeight: 1.4 }}>
          {current.desc}
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '4px',
          paddingTop: '4px',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.68rem'
        }}>
          <div>VRAM: <span style={{ color: 'var(--accent-purple)' }}>{current.vram}</span></div>
          <div>CONTEXT: <span style={{ color: 'var(--accent-emerald)' }}>{current.context}</span></div>
          <div>LATENCY: <span style={{ color: 'var(--accent-amber)' }}>{current.latencyClass}</span></div>
          <div>LAYER: <span style={{ color: 'var(--text-primary)' }}>{current.layer}</span></div>
        </div>
      </div>
    </div>
  );
}

export default InferenceEngineSelector;
