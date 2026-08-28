import React, { useState, useEffect } from 'react';

export default function GlobalMeshShardingProfiler() {
  const [data, setData] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [activeTab, setActiveTab] = useState('configs'); // 'configs', 'tasks', 'nvidia_linear', 'models', 'transports'
  const [isLoading, setIsLoading] = useState(true);
  const apiHost = window.location.hostname || 'localhost';

  useEffect(() => {
    const fetchProfilerData = async () => {
      try {
        const res = await fetch(`http://${apiHost}:5001/api/network/global_sharding_profiler`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
          if (json.all_configurations?.length > 0 && !selectedConfig) {
            setSelectedConfig(json.all_configurations[0]);
          }
        }
      } catch (err) {
        console.error("Failed to load global sharding profiler data:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfilerData();
    const interval = setInterval(fetchProfilerData, 10000);
    return () => clearInterval(interval);
  }, [apiHost]);

  if (isLoading && !data) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div style={{ fontSize: '2rem' }}>⚡</div>
        <p>Loading Enhanced Global Sharding Profiler &amp; Dual AI Benchmarks...</p>
      </div>
    );
  }

  const configurations = data?.all_configurations || [];
  const models = data?.models_portfolio || {};
  const tasks = data?.task_optimizations || [];
  const nvidia = data?.nvidia_linear_transfer || {};

  const filteredConfigs = configurations.filter(cfg => {
    if (selectedFilter === 'home_2_device') return cfg.nodes.length === 2;
    if (selectedFilter === 'cross_platform') return cfg.nodes.some(n => n.includes('Mac')) && cfg.nodes.some(n => n.includes('Linux'));
    if (selectedFilter === 'mobile') return cfg.nodes.some(n => n.includes('Pixel') || n.includes('Samsung') || n.includes('Tablet'));
    if (selectedFilter === 'full_mesh') return cfg.nodes.length >= 4;
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', color: '#f8fafc' }}>
      
      {/* 1. TOP STATS DOCK */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.95))',
        border: '1px solid rgba(56,189,248,0.3)',
        borderRadius: '12px',
        padding: '1.2rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        boxShadow: '0 8px 32px rgba(56,189,248,0.12)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem' }}>
          <div style={{
            fontSize: '2rem',
            background: 'rgba(56,189,248,0.15)',
            padding: '10px 16px',
            borderRadius: '12px',
            border: '1px solid #38bdf8',
            color: '#38bdf8',
            fontWeight: '900'
          }}>
            🌐
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: '900', color: '#38bdf8' }}>
              Global 11-Config Profiler (Dual Benchmarked • High-ROI Ranked)
            </h2>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'flex', gap: '1rem', marginTop: '0.3rem', flexWrap: 'wrap' }}>
              <span>🖥️ Pooled Mesh Nodes: <strong style={{ color: '#10b981' }}>7 Devices</strong></span>
              <span>• Total Usable VRAM: <strong style={{ color: '#facc15' }}>82.8 GB</strong></span>
              <span>• 100B+ MoE Headroom: <strong style={{ color: '#c084fc' }}>+18.8 GB to +30.8 GB</strong></span>
              <span>• NVIDIA Linear Speedup: <strong style={{ color: '#fb923c' }}>25.1x TTFT</strong></span>
            </div>
          </div>
        </div>

        {/* SUB-TABS */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveTab('configs')}
            style={{
              background: activeTab === 'configs' ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(56,189,248,0.4)',
              padding: '7px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            ⚡ 11 Dual-Benchmarked Configs
          </button>
          <button
            onClick={() => setActiveTab('tasks')}
            style={{
              background: activeTab === 'tasks' ? 'linear-gradient(135deg, #059669, #10b981)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(16,185,129,0.4)',
              padding: '7px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            🎯 Task-Specific Optimizations
          </button>
          <button
            onClick={() => setActiveTab('nvidia_linear')}
            style={{
              background: activeTab === 'nvidia_linear' ? 'linear-gradient(135deg, #76b900, #a3e635)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(163,230,53,0.4)',
              padding: '7px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            🚀 NVIDIA Linear Math (25x Speedup)
          </button>
          <button
            onClick={() => setActiveTab('models')}
            style={{
              background: activeTab === 'models' ? 'linear-gradient(135deg, #9333ea, #c084fc)' : 'rgba(255,255,255,0.05)',
              color: '#fff',
              border: '1px solid rgba(192,132,252,0.4)',
              padding: '7px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.8rem'
            }}
          >
            🧠 100B+ MoE Large Models
          </button>
        </div>
      </div>

      {/* 2. TAB: 11 DUAL-BENCHMARKED CONFIGURATIONS */}
      {activeTab === 'configs' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* FILTER BUTTONS */}
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', marginRight: '0.4rem' }}>Filter Setups:</span>
            {[
              { id: 'all', label: 'All Setups (11)' },
              { id: 'home_2_device', label: '🏠 2-Device Home Pairs' },
              { id: 'cross_platform', label: '💻 Cross-Platform (Mac + Linux)' },
              { id: 'mobile', label: '📱 Mobile Creators (Pixel & S20)' },
              { id: 'full_mesh', label: '👑 Heavy Multi-Node Array' }
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setSelectedFilter(f.id)}
                style={{
                  background: selectedFilter === f.id ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.04)',
                  color: selectedFilter === f.id ? '#38bdf8' : '#94a3b8',
                  border: `1px solid ${selectedFilter === f.id ? '#38bdf8' : 'rgba(255,255,255,0.08)'}`,
                  padding: '5px 12px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  fontSize: '0.76rem',
                  fontWeight: selectedFilter === f.id ? 'bold' : '500'
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* CONFIG CARDS GRID */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1rem' }}>
            {filteredConfigs.map(cfg => {
              const isSelected = selectedConfig?.id === cfg.id;
              return (
                <div
                  key={cfg.id}
                  onClick={() => setSelectedConfig(cfg)}
                  style={{
                    background: isSelected ? '#1e293b' : '#0f172a',
                    border: `1px solid ${isSelected ? '#38bdf8' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '10px',
                    padding: '1.1rem',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.6rem',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? '0 0 20px rgba(56,189,248,0.2)' : 'none'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <div>
                      <span style={{ fontSize: '0.68rem', color: '#facc15', fontWeight: 'bold' }}>{cfg.high_roi_rank}</span>
                      <h3 style={{ margin: '2px 0 0 0', fontSize: '0.95rem', color: isSelected ? '#38bdf8' : '#f8fafc', fontWeight: 'bold' }}>
                        {cfg.name}
                      </h3>
                    </div>
                    <span style={{
                      fontSize: '0.7rem',
                      background: 'rgba(16,185,129,0.15)',
                      color: '#34d399',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontWeight: 'bold',
                      whiteSpace: 'nowrap'
                    }}>
                      {cfg.pooled_vram_gb} GB VRAM
                    </span>
                  </div>

                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    📍 <strong>Nodes:</strong> {cfg.nodes.join(' + ')}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    ⚡ <strong>Transport:</strong> <span style={{ color: '#fbbf24' }}>{cfg.transport}</span>
                  </div>

                  {/* DUAL BENCHMARK SCORES */}
                  <div style={{ background: '#090d16', padding: '0.6rem', borderRadius: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                      <span style={{ color: '#38bdf8' }}>📊 <strong>Standard AI Benchmark:</strong></span>
                      <strong style={{ color: '#fff' }}>{cfg.standard_ai_score}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                      <span style={{ color: '#10b981' }}>🧬 <strong>Self-Improving Project AI:</strong></span>
                      <strong style={{ color: '#34d399' }}>{cfg.project_ai_score}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '4px', marginTop: '2px' }}>
                      <span style={{ color: '#facc15' }}>💎 <strong>Composite ROI Score:</strong></span>
                      <strong style={{ color: '#facc15' }}>{cfg.composite_roi_index} / 100</strong>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', background: '#090d16', padding: '0.5rem', borderRadius: '6px' }}>
                    <div>
                      <div style={{ fontSize: '0.65rem', color: '#64748b' }}>THROUGHPUT</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 'bold', color: '#10b981' }}>{cfg.tok_per_sec} tok/s</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.65rem', color: '#64748b' }}>TTFT LATENCY</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 'bold', color: '#38bdf8' }}>{cfg.ttft_ms} ms</div>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.7rem', color: '#a7f3d0', background: 'rgba(16,185,129,0.08)', padding: '4px 8px', borderRadius: '4px' }}>
                    {cfg.home_user_fit}
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}

      {/* 3. TAB: TASK-SPECIFIC OPTIMIZATIONS */}
      {activeTab === 'tasks' && (
        <div style={{
          background: '#0f172a',
          border: '1px solid rgba(16,185,129,0.3)',
          borderRadius: '12px',
          padding: '1.2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <div>
            <h3 style={{ margin: 0, color: '#34d399', fontSize: '1.15rem' }}>
              🎯 Task-Specific High-ROI Hardware Optimization Matrix
            </h3>
            <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
              Dynamically pins each active monorepo workload to its mathematically optimal hardware path, framework, and transport socket.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '0.9rem' }}>
            {tasks.map((t, idx) => (
              <div
                key={idx}
                style={{
                  background: '#090d16',
                  border: '1px solid rgba(16,185,129,0.2)',
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.88rem', color: '#facc15' }}>{t.task_name}</strong>
                  <span style={{ fontSize: '0.68rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 8px', borderRadius: '8px', fontWeight: 'bold' }}>
                    {t.roi_speedup}
                  </span>
                </div>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  🏆 <strong>Winning Nodes:</strong> {t.winning_nodes.join(' + ')}
                </div>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  ⚡ <strong>Transport:</strong> <span style={{ color: '#38bdf8' }}>{t.transport}</span>
                </div>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  🚀 <strong>Speed:</strong> <strong style={{ color: '#10b981' }}>{t.tok_per_sec} tok/s</strong> ({t.latency_ms} ms RTT)
                </div>
                <div style={{ fontSize: '0.72rem', color: '#e2e8f0', background: 'rgba(255,255,255,0.03)', padding: '6px 8px', borderRadius: '4px', lineHeight: '1.4' }}>
                  💡 <em>{t.rationale}</em>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. TAB: NVIDIA LINEAR MATH RESEARCH */}
      {activeTab === 'nvidia_linear' && (
        <div style={{
          background: '#0f172a',
          border: '1px solid rgba(163,230,53,0.3)',
          borderRadius: '12px',
          padding: '1.2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🚀</span>
              <h3 style={{ margin: 0, color: '#a3e635', fontSize: '1.15rem' }}>
                NVIDIA Research: Cross-Model KV Cache Transfer via Linear Math (arXiv:2608.03893)
              </h3>
            </div>
            <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
              Published August 2026: Replaces costly multi-model handoff re-prefills with closed-form ordinary least squares linear algebra.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.8rem' }}>
            <div style={{ background: '#090d16', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(163,230,53,0.2)' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>SPEEDUP MULTIPLIER</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '900', color: '#a3e635', marginTop: '4px' }}>{nvidia.speedup_multiplier}</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>278 ms vs 6,980 ms baseline</div>
            </div>
            <div style={{ background: '#090d16', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>ACCURACY RETENTION</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '900', color: '#38bdf8', marginTop: '4px' }}>{nvidia.accuracy_retention}</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>Closed-form OLS transformation</div>
            </div>
            <div style={{ background: '#090d16', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(250,204,21,0.2)' }}>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>MATHEMATICAL CORE</div>
              <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#facc15', marginTop: '6px' }}>W_proj · KV_source + b</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>Zero backprop • Gradient-Free</div>
            </div>
          </div>

          <div style={{ background: '#090d16', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <h4 style={{ margin: '0 0 0.4rem 0', color: '#f8fafc', fontSize: '0.88rem' }}>How This Supercharges the Lauburu Monorepo:</h4>
            <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8', lineHeight: '1.5' }}>
              {nvidia.monorepo_implementation}
            </p>
          </div>
        </div>
      )}

      {/* 5. TAB: 100B+ MoE LARGE MODELS */}
      {activeTab === 'models' && (
        <div style={{
          background: '#0f172a',
          border: '1px solid rgba(192,132,252,0.3)',
          borderRadius: '12px',
          padding: '1.2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          <div>
            <h3 style={{ margin: 0, color: '#c084fc', fontSize: '1.15rem' }}>
              🧠 100B+ MoE Large Models Catalog (Fitting in 82.8 GB Mesh Pool)
            </h3>
            <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
              High-efficiency Mixture-of-Experts architectures providing 100B–236B parameter intelligence with 10B–39B active compute footprint.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '0.9rem' }}>
            {Object.entries(models).map(([key, m]) => (
              <div
                key={key}
                style={{
                  background: '#090d16',
                  border: '1px solid rgba(192,132,252,0.2)',
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.9rem', color: '#f8fafc' }}>{m.name}</strong>
                  <span style={{ fontSize: '0.7rem', background: 'rgba(192,132,252,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '10px', fontWeight: 'bold' }}>
                    {m.vram_req_gb} GB VRAM
                  </span>
                </div>

                <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  Total: <strong>{m.params_b}B</strong> • Active per token: <strong style={{ color: '#10b981' }}>{m.active_params_b}B</strong>
                </div>

                <div style={{ fontSize: '0.74rem', color: '#facc15' }}>
                  🛡️ <strong>Mesh Headroom:</strong> +{m.mesh_headroom_gb} GB Free Buffer
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', background: 'rgba(255,255,255,0.03)', padding: '4px 8px', borderRadius: '4px' }}>
                  <span>Standard AI: <strong>{m.benchmark_scores?.standard_ai}</strong></span>
                  <span>Project AI: <strong style={{ color: '#34d399' }}>{m.benchmark_scores?.project_ai}</strong></span>
                </div>

                <div style={{ fontSize: '0.72rem', color: '#a7f3d0' }}>
                  {m.roi_rating}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
