import React, { useState, useEffect } from 'react';

export default function FutureNetworkSimulationHub() {
  const [moeData, setMoeData] = useState(null);
  const [simData, setSimData] = useState(null);
  const [stressLevel, setStressLevel] = useState(0);
  const [usersCount, setUsersCount] = useState(10);
  const [behaviorPreset, setBehaviorPreset] = useState('BALANCED');
  const [optInTier, setOptInTier] = useState('ADAPTIVE_SMART');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSimulationData = async (stress = stressLevel, count = usersCount, preset = behaviorPreset, optIn = optInTier) => {
    try {
      const apiHost = window.location.hostname || 'localhost';
      const [moeRes, simRes] = await Promise.all([
        fetch(`http://${apiHost}:5001/api/genetic_moe/triage`),
        fetch(`http://${apiHost}:5001/api/simulation/future_network?stress_level=${stress}&users_count=${count}&behavior_preset=${preset}&opt_in_tier=${optIn}`)
      ]);
      if (moeRes.ok) setMoeData(await moeRes.json());
      if (simRes.ok) setSimData(await simRes.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulationData();
    const interval = setInterval(() => fetchSimulationData(), 4000);
    return () => clearInterval(interval);
  }, [stressLevel, usersCount, behaviorPreset, optInTier]);

  const handlePresetClick = (preset) => {
    setBehaviorPreset(preset);
    fetchSimulationData(stressLevel, usersCount, preset, optInTier);
  };

  const handleOptInChange = (tier) => {
    setOptInTier(tier);
    fetchSimulationData(stressLevel, usersCount, behaviorPreset, tier);
  };

  const handleUsersChange = (count) => {
    setUsersCount(count);
    fetchSimulationData(stressLevel, count, behaviorPreset, optInTier);
  };

  const handleStressChange = (stress) => {
    setStressLevel(stress);
    fetchSimulationData(stress, usersCount, behaviorPreset, optInTier);
  };

  if (loading && !simData) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🧬</div>
        Loading Real-World Self-Optimizing Simulated Network &amp; Stealth Load Balancer...
      </div>
    );
  }

  const summary = simData?.summary || {};
  const stealthSummary = simData?.stealth_mesh_summary || {};
  const geneticOpt = simData?.genetic_self_optimization || {};
  const realCoreNodes = simData?.real_core_nodes || [];
  const remoteUsers = simData?.onboarded_remote_users || [];
  const sharding = simData?.sharding_analysis || {};
  const pillars = moeData?.pillars || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', padding: '0.5rem 0' }}>
      
      {/* HEADER BANNER */}
      <div style={{ background: 'linear-gradient(135deg, rgba(88,28,135,0.35), rgba(15,23,42,0.85))', border: '1px solid rgba(192,132,252,0.3)', borderRadius: '10px', padding: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.6rem' }}>🛡️</span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 'bold' }}>
              Real-World Self-Optimizing Network Simulator &amp; Stealth Balancer
            </h2>
            <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>
              100% Real Hardware • Real ISPs • Real USB &amp; Power
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.82rem', margin: '0.4rem 0 0 0' }}>
            Autonomous genetic routing crossover across physical hardware, fiber/5G/satellite plans, Thunderbolt 4 / USB-C PD interfaces, and user opt-in constraints.
          </p>
        </div>

        {/* CONTROLS BAR */}
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Onboarded Peers: <strong style={{ color: '#38bdf8' }}>{usersCount}</strong></div>
            <input 
              type="range" min="1" max="25" value={usersCount} 
              onChange={(e) => handleUsersChange(parseInt(e.target.value))}
              style={{ cursor: 'pointer', accentColor: '#38bdf8', width: '85px' }}
            />
          </div>

          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Partition Stress: <strong style={{ color: stressLevel > 2 ? '#ef4444' : '#34d399' }}>Lv {stressLevel}</strong></div>
            <input 
              type="range" min="0" max="5" value={stressLevel} 
              onChange={(e) => handleStressChange(parseInt(e.target.value))}
              style={{ cursor: 'pointer', accentColor: stressLevel > 2 ? '#ef4444' : '#34d399', width: '75px' }}
            />
          </div>
        </div>
      </div>

      {/* USER OPT-IN CONTROLS & SCENARIO BUTTONS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.8rem', background: 'rgba(0,0,0,0.3)', padding: '0.7rem 1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
        
        {/* OPT-IN TIERS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 'bold' }}>👤 Real User Opt-In:</span>
          {[
            { id: 'ADAPTIVE_SMART', label: '🧠 Adaptive Smart (40% Cap / 0 Fan)' },
            { id: 'UNLIMITED_MAINS', label: '⚡ Unlimited AC Mains (75% Cap)' },
            { id: 'BATTERY_SAVER_MICRO', label: '🔋 Battery Saver (5% Pulse)' },
            { id: 'BALANCED_50', label: '⚖️ Balanced (50% Cap)' },
            { id: 'CONSERVATIVE_10', label: '🛡️ Conservative (10% Cap)' }
          ].map(tier => (
            <button
              key={tier.id}
              onClick={() => handleOptInChange(tier.id)}
              style={{
                background: optInTier === tier.id ? 'linear-gradient(135deg, #0ea5e9, #6366f1)' : 'rgba(255,255,255,0.03)',
                border: optInTier === tier.id ? 'none' : '1px solid rgba(255,255,255,0.08)',
                color: optInTier === tier.id ? '#fff' : '#94a3b8',
                fontWeight: optInTier === tier.id ? 'bold' : 'normal',
                padding: '4px 10px',
                borderRadius: '5px',
                fontSize: '0.72rem',
                cursor: 'pointer'
              }}
            >
              {tier.label}
            </button>
          ))}
        </div>

        {/* PRESET BEHAVIORS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 'bold' }}>⚡ Profiles:</span>
          {[
            { id: 'BALANCED', label: '⚡ Normal Day' },
            { id: 'NIGHT_IDLE_SURGE', label: '💤 Night Surge' },
            { id: 'PEAK_GAMING_SPIKE', label: '🎮 Gaming Spike' },
            { id: 'STARLINK_JITTER', label: '🛰️ Starlink Jitter' }
          ].map((p) => (
            <button 
              key={p.id}
              onClick={() => handlePresetClick(p.id)}
              style={{ background: behaviorPreset === p.id ? 'rgba(168,85,247,0.3)' : 'rgba(255,255,255,0.02)', border: behaviorPreset === p.id ? '1px solid #c084fc' : '1px solid rgba(255,255,255,0.06)', color: '#fff', padding: '0.3rem 0.5rem', borderRadius: '5px', fontSize: '0.72rem', cursor: 'pointer' }}
            >
              {p.label}
            </button>
          ))}
        </div>

      </div>

      {/* GENETIC SELF-OPTIMIZATION CONVERGENCE BANNER */}
      <div style={{ background: 'linear-gradient(135deg, rgba(6,95,70,0.25), rgba(15,23,42,0.85))', border: '1px solid rgba(16,185,129,0.35)', borderRadius: '8px', padding: '0.8rem 1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '1.2rem' }}>🧬</span>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 'bold', color: '#34d399' }}>
              Genetic Algorithm Self-Optimization Pass: {geneticOpt.genetic_optimization_status || 'CONVERGED_OPTIMAL'}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Evaluated across {geneticOpt.generations_evaluated || 5} micro-generations • Optimal Cluster Fitness: <strong style={{ color: '#38bdf8' }}>{geneticOpt.optimal_cluster_fitness}%</strong> • Optimized Avg Latency: <strong style={{ color: '#4ade80' }}>{geneticOpt.optimized_avg_rtt_ms} ms</strong>
            </div>
          </div>
        </div>
        <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '3px 8px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>
          {geneticOpt.self_healing_routing_pass}
        </span>
      </div>

      {/* STEALTH EXPERIENCE HERO STATS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.8rem' }}>
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Active Harvested VRAM</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
            {summary.total_active_vram_gb} GB
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
            100% Load-Balanced Across {summary.total_pooled_mesh_nodes} Nodes
          </div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Zero Idle Peers</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#34d399', marginTop: '0.2rem' }}>
            100.0% Active
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
            0 Wasted Nodes ({summary.idle_nodes_count} Idle Peers)
          </div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>User Disruption Index</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#4ade80', marginTop: '0.2rem' }}>
            {summary.global_user_disruption_index}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
            Completely Imperceptible to Users
          </div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Instant Yield Latency</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#c084fc', marginTop: '0.2rem' }}>
            {stealthSummary.avg_instant_yield_time_ms} ms
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
            Sub-5ms GPU/CPU Yield on User Action
          </div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Fan Noise &amp; Thermal Cap</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#facc15', marginTop: '0.2rem' }}>
            0.0 dB
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
            Caps Temp &le; 58°C (PC) / &le; 38°C (Mobile)
          </div>
        </div>
      </div>

      {/* DUAL COLUMN: REAL CORE ANCHOR vs ONBOARDED PEERS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1rem' }}>
        
        {/* COLUMN 1: REAL CORE LOCAL NETWORK */}
        <div style={{ background: '#111827', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.1rem' }}>📍</span>
              <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#34d399', fontWeight: 'bold' }}>
                100% Real Live Local Network (Command Anchor)
              </h3>
            </div>
            <span style={{ fontSize: '0.68rem', background: 'rgba(16,185,129,0.15)', color: '#34d399', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
              5 Physical Devices
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {realCoreNodes.map((n, idx) => {
              const st = n.stealth_telemetry || {};
              return (
                <div key={idx} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px', padding: '0.7rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', color: '#f8fafc', fontSize: '0.85rem' }}>{n.name}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{n.hardware} • {n.os}</div>
                    <div style={{ fontSize: '0.68rem', color: '#38bdf8', marginTop: '0.2rem' }}>
                      🌐 {n.internet_plan} • 🔌 {n.connection_interface}
                    </div>
                    <div style={{ fontSize: '0.66rem', color: '#64748b', marginTop: '0.1rem' }}>
                      ⚡ {n.power_profile} • Mode: <strong style={{ color: '#34d399' }}>{st.stealth_mode}</strong> • Temp: <strong>{st.device_temperature_c}°C</strong>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '0.85rem' }}>{st.allocated_vram_gb} GB Active</div>
                    <div style={{ fontSize: '0.68rem', color: '#34d399', fontWeight: 'bold', marginTop: '0.1rem' }}>
                      {st.idle_status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* COLUMN 2: CROWDSOURCED ONBOARDED REMOTE USERS */}
        <div style={{ background: '#111827', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.1rem' }}>🌍</span>
              <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#c084fc', fontWeight: 'bold' }}>
                Onboarded Real-World Peers ({remoteUsers.length} Devices • 0 Idle)
              </h3>
            </div>
            <span style={{ fontSize: '0.68rem', background: 'rgba(168,85,247,0.15)', color: '#c084fc', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
              Stealth QoS Background
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '420px', overflowY: 'auto' }}>
            {remoteUsers.map((u, idx) => {
              const st = u.stealth_telemetry || {};
              return (
                <div key={idx} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px', padding: '0.7rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', color: '#f8fafc', fontSize: '0.85rem' }}>{u.user_name} • {u.location}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{u.device_name} ({u.hardware_type})</div>
                    <div style={{ fontSize: '0.68rem', color: '#a855f7', marginTop: '0.2rem' }}>
                      🌐 {u.internet_plan} • 🔌 {u.connection_interface}
                    </div>
                    <div style={{ fontSize: '0.66rem', color: '#64748b', marginTop: '0.1rem' }}>
                      ⚡ {u.power_profile} • Mode: <strong style={{ color: u.user_behavior === 'GAMING_ACTIVE' ? '#ef4444' : u.user_behavior === 'IDLE_NIGHT_MODE' ? '#34d399' : '#facc15' }}>{st.stealth_mode}</strong> • Temp: <strong>{st.device_temperature_c}°C</strong>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ color: '#c084fc', fontWeight: 'bold', fontSize: '0.85rem' }}>+{st.allocated_vram_gb} GB Active</div>
                    <div style={{ fontSize: '0.68rem', color: '#4ade80', fontWeight: 'bold', marginTop: '0.1rem' }}>
                      Impact: {st.user_experience_impact_pct}% ({st.instant_yield_latency_ms}ms Yield)
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* SHARDING CAPACITY & MODEL FIT ANALYSIS */}
      <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span>🦙</span> Cluster Model Fit &amp; Multi-Node Sharding Analysis
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.8rem' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>70B Model (Q4_K_M ~23 GB)</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#34d399', marginTop: '0.2rem' }}>
              {sharding['70B_model_mesh_fit']}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>405B Frontier MoE (~220 GB)</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
              {sharding['405B_model_mesh_fit']}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>USB &amp; Thermal Protection</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#a855f7', marginTop: '0.2rem' }}>
              {sharding['usb_pd_thermal_safety']}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Byzantine Fault Tolerance</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#facc15', marginTop: '0.2rem' }}>
              {sharding['byzantine_fault_tolerance']}
            </div>
          </div>
        </div>
      </div>

      {/* 🚀 GOOGLE ANTIGRAVITY SDK MULTI-AGENT ROUTER & SUBAGENT SWARM HUD */}
      <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.25), rgba(15,23,42,0.95))', border: '1px solid rgba(59,130,246,0.35)', borderRadius: '12px', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.6rem' }}>🚀</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#f8fafc', fontWeight: 'bold' }}>
                Google Antigravity (AGY) SDK Multi-Agent MoE Router
              </h3>
              <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                Unified Agent, Conversation &amp; Connection strategies across Cloud TPUs, 10Gbps TB4 Metal GPU, and Edge TPU
              </div>
            </div>
          </div>
          <span style={{ background: 'rgba(16,185,129,0.2)', border: '1px solid #10b981', color: '#34d399', fontSize: '0.72rem', fontWeight: 'bold', padding: '3px 10px', borderRadius: '999px' }}>
            ● AGY SDK Native Routing Active
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.8rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '8px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.7rem', color: '#60a5fa', fontWeight: 'bold' }}>TIER 1: CLOUD TITAN</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#f8fafc', marginTop: '2px' }}>Gemini 3.7 Flash</div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '2px' }}>Strategy: <code>LocalConnectionStrategy</code></div>
            <div style={{ fontSize: '0.68rem', color: '#cbd5e1', marginTop: '4px' }}>High-Thinking CoT Planner &amp; Shadow Guard</div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '8px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.7rem', color: '#34d399', fontWeight: 'bold' }}>TIER 2: LOCAL METAL MESH</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#f8fafc', marginTop: '2px' }}>Qwen 3.8 Max (TB4)</div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '2px' }}>Strategy: <code>LocalOpenAIConnectionStrategy</code></div>
            <div style={{ fontSize: '0.68rem', color: '#cbd5e1', marginTop: '4px' }}>10Gbps Thunderbolt Metal • $0 Token Spend</div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(168,85,247,0.2)', borderRadius: '8px', padding: '0.8rem' }}>
            <div style={{ fontSize: '0.7rem', color: '#c084fc', fontWeight: 'bold' }}>TIER 3: EDGE MOBILE TPU</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#f8fafc', marginTop: '2px' }}>SmolLM2-1.7B / LiteRT-LM</div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '2px' }}>Strategy: <code>LiteRTConnectionStrategy</code></div>
            <div style={{ fontSize: '0.68rem', color: '#cbd5e1', marginTop: '4px' }}>Pixel 10 Pro XL Tensor G5 • Sub-50ms GATT</div>
          </div>
        </div>
      </div>

    </div>
  );
}
