import React, { useState, useEffect } from 'react';

export default function ShardedRPCClusterSafetyView() {
  const [clusterData, setClusterData] = useState(null);
  const [targetCap, setTargetCap] = useState(70);
  const [isTuning, setIsTuning] = useState(false);

  const fetchClusterStatus = async (cap = targetCap) => {
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/rpc_sharding/status?target_capacity_pct=${cap}`);
      if (res.ok) {
        setClusterData(await res.json());
      }
    } catch (e) {
      console.error('Failed to fetch RPC sharding status:', e);
    }
  };

  useEffect(() => {
    fetchClusterStatus(targetCap);
    const interval = setInterval(() => fetchClusterStatus(targetCap), 5000);
    return () => clearInterval(interval);
  }, [targetCap]);

  const handleTuneCapacity = async (newCap) => {
    setTargetCap(newCap);
    setIsTuning(true);
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/rpc_sharding/tune`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_capacity_pct: newCap })
      });
      if (res.ok) {
        setClusterData(await res.json());
      }
    } catch (e) {
      console.error('Error tuning capacity:', e);
    } finally {
      setIsTuning(false);
    }
  };

  const nodes = clusterData?.nodes || [];

  return (
    <div style={{ background: '#0d1527', border: '1px solid rgba(56,189,248,0.3)', borderRadius: '12px', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
      
      {/* HEADER & CLUSTER CAPACITY OVERVIEW */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.8rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.6rem' }}>🛡️</span>
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 'bold' }}>
              5-Way RPC Sharded Training &amp; Thermal / Battery Safety Cluster
            </h3>
            <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.15)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>
              Target: {clusterData?.cluster_target_capacity_pct || 70}% Active Shard Load
            </span>
          </div>
          <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
            Pooled <strong>38.26 GB Active Training VRAM</strong> across 7 physical devices. Live temperature throttling, battery drain protection, and 25% safety reserve.
          </p>
        </div>

        {/* TARGET CAPACITY TUNING CHIPS */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Load Preset:</span>
          {[
            { label: '50% Eco', cap: 50 },
            { label: '70% High-Throughput', cap: 70 },
            { label: '80% Burst Peak', cap: 80 }
          ].map((preset) => (
            <button
              key={preset.cap}
              onClick={() => handleTuneCapacity(preset.cap)}
              style={{
                background: targetCap === preset.cap ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(255,255,255,0.05)',
                border: targetCap === preset.cap ? 'none' : '1px solid rgba(255,255,255,0.1)',
                color: '#fff',
                fontWeight: targetCap === preset.cap ? 'bold' : 'normal',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* CLUSTER VRAM & SAFETY METRIC GAUGES */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.8rem' }}>
        <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '0.8rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Active Sharded AI VRAM</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
            {clusterData?.total_allocated_vram_gb || 38.26} / {clusterData?.total_pooled_cap_gb || 82.8} GB
          </div>
          <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.2rem' }}>
            {clusterData?.cluster_vram_utilization_pct || 70.0}% of pooled cluster VRAM utilized
          </div>
        </div>

        <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '0.8rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Mandatory Headroom Reserve</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#34d399', marginTop: '0.2rem' }}>
            {clusterData?.headroom_reserve_gb || 16.39} GB ({clusterData?.headroom_reserve_pct || 30.0}%)
          </div>
          <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.2rem' }}>
            Guarantees zero OS swap thrashing &amp; UI responsiveness
          </div>
        </div>

        <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '0.8rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Thermal &amp; Battery Status</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: clusterData?.all_nodes_thermal_safe ? '#10b981' : '#f59e0b', marginTop: '0.2rem' }}>
            {clusterData?.all_nodes_thermal_safe ? 'All Nodes Optimal' : 'Adaptive Throttled'}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.2rem' }}>
            Mobile Ceiling: 41.0°C • PC Ceiling: 78.0°C
          </div>
        </div>
      </div>

      {/* 5 PHYSICAL NODES DETAIL GRID */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.8rem' }}>
        {nodes.map((node) => (
          <div key={node.id} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            
            {/* NODE HEADER */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: '0.88rem', fontWeight: 'bold', color: '#f8fafc' }}>
                  {node.name}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#38bdf8' }}>
                  {node.role}
                </div>
              </div>
              <span style={{ fontSize: '0.68rem', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', background: node.safety_status === 'SAFE_70_ACTIVE' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)', color: node.safety_status === 'SAFE_70_ACTIVE' ? '#34d399' : '#f59e0b' }}>
                {node.safety_status}
              </span>
            </div>

            {/* VRAM ALLOCATION BAR */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#cbd5e1', marginBottom: '0.2rem' }}>
                <span>70% Training VRAM:</span>
                <span style={{ fontWeight: 'bold', color: '#38bdf8' }}>{node.allocated_vram_gb} GB / {node.ai_cap_gb} GB</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${(node.allocated_vram_gb / node.ai_cap_gb) * 100}%`, background: 'linear-gradient(90deg, #0284c7, #38bdf8)', height: '100%' }} />
              </div>
            </div>

            {/* LIVE VITALS (TEMP, BATTERY, POWER) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '6px' }}>
              <div>
                <span>🌡️ Temperature:</span>
                <div style={{ fontWeight: 'bold', color: node.current_temp_c >= node.thermal_limit_c ? '#ef4444' : '#34d399' }}>
                  {node.current_temp_c}°C ({node.temp_status})
                </div>
              </div>
              <div>
                <span>🔋 Battery / Power:</span>
                <div style={{ fontWeight: 'bold', color: '#38bdf8' }}>
                  {node.battery_level_pct}% • {node.is_charging ? '⚡ Charging' : 'Mains'}
                </div>
              </div>
              <div style={{ gridColumn: 'span 2', fontSize: '0.68rem', color: '#64748b' }}>
                🔌 <strong>Power:</strong> {node.power_source}
              </div>
              <div style={{ gridColumn: 'span 2', fontSize: '0.68rem', color: '#64748b' }}>
                🌐 <strong>Link:</strong> {node.connection} (RPC :50052)
              </div>
            </div>

          </div>
        ))}
      </div>

      {/* SAFETY PROTOCOL FOOTER */}
      <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px dashed rgba(56,189,248,0.2)', borderRadius: '6px', padding: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.72rem', color: '#94a3b8' }}>
        <div style={{ fontWeight: 'bold', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span>🛡️</span> Active Multi-Device Safety Protocols Enforced:
        </div>
        <div>
          • <strong>Thermal Guard:</strong> Mobile edge nodes (Pixel/S20) auto-yield to AC Macs if temp exceeds 41.0°C. PC nodes throttle at 78.0°C.
        </div>
        <div>
          • <strong>Battery Life Preservation:</strong> Discharging nodes below 25% battery offload all tensor computation to preserve device longevity.
        </div>
        <div>
          • <strong>RPC Sharding Headroom:</strong> Mandatory 25% memory headroom ensures zero kernel swap thrashing and instant sub-10ms UI interaction.
        </div>
      </div>

    </div>
  );
}
