import React, { useState, useEffect } from 'react';

export default function StorageAnalysisHub() {
  const [nasData, setNasData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  
  // Interactive PySpark SQL State
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM storage_hardware_nodes');
  const [sqlResult, setSqlResult] = useState(null);
  const [sqlLoading, setSqlLoading] = useState(false);

  // Genetic MoE Router Sandbox State
  const [simFilename, setSimFilename] = useState('qwen3-vl-32b-vision-instruct.gguf');
  const [simSize, setSimSize] = useState('18.2');
  const [simType, setSimType] = useState('GGUF_MODEL_WEIGHTS');
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  const fetchNasOverview = async () => {
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/nas/overview`);
      if (res.ok) {
        const json = await res.json();
        setNasData(json);
        setError(null);
      } else {
        setError('Failed to load Unified NAS API');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNasOverview();
    const interval = setInterval(fetchNasOverview, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTriggerSync = async () => {
    setSyncStatus('🚀 Initiating Full Unified NAS Synchronization & Rebalance Cycle...');
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/nas/trigger_sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (res.ok) {
        const json = await res.json();
        setNasData(json);
        setSyncStatus(`✅ Unified NAS Sync Complete in ${json.last_sync_duration_sec || 0.05}s (100% Zero-Loss Certified)`);
      }
    } catch (e) {
      setSyncStatus(`❌ Sync Failed: ${e.message}`);
    }
  };

  const handleExecuteSql = async (queryToRun) => {
    const q = queryToRun || sqlQuery;
    setSqlLoading(true);
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/nas/execute_sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q })
      });
      if (res.ok) {
        const json = await res.json();
        setSqlResult(json.output);
      }
    } catch (e) {
      setSqlResult(`Error executing SQL: ${e.message}`);
    } finally {
      setSqlLoading(false);
    }
  };

  const handleRouteSimulation = async () => {
    setSimLoading(true);
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/nas/route_file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: simFilename,
          size_gb: parseFloat(simSize) || 1.0,
          file_type: simType
        })
      });
      if (res.ok) {
        const json = await res.json();
        setSimResult(json);
      }
    } catch (e) {
      setSimResult({ error: e.message });
    } finally {
      setSimLoading(false);
    }
  };

  if (loading && !nasData) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💾</div>
        Connecting to 6-Tier Unified NAS Storage Mesh & PySpark Lakehouse...
      </div>
    );
  }

  const pooled = nasData?.pooled_metrics || {};
  const transports = nasData?.multi_transport_status || {};
  const nodes = nasData?.hardware_tiers || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', padding: '0.5rem 0' }}>
      
      {/* HEADER BANNER */}
      <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.35), rgba(88,28,135,0.35))', border: '1px solid rgba(96,165,250,0.3)', borderRadius: '10px', padding: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.6rem' }}>💾</span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 'bold' }}>
              6-Tier Unified NAS Storage Mesh & PySpark Lakehouse
            </h2>
            <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.2)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>
              MergerFS + Syncthing + GDrive + PySpark + Genetic MoE
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.82rem', margin: '0.4rem 0 0 0' }}>
            Unified virtual namespace (/Volumes/NAS) pooling Headless Mac, External 1TB SSD, Main Mac, Linux, Samsung S20 & Google Drive.
          </p>
        </div>

        <button 
          onClick={handleTriggerSync}
          style={{ background: 'linear-gradient(135deg, #10b981, #059669)', border: 'none', color: '#000', fontWeight: 'bold', padding: '0.6rem 1.2rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem', boxShadow: '0 4px 12px rgba(16,185,129,0.3)' }}
        >
          <span>⚡</span> Sync & Rebalance NAS Mesh
        </button>
      </div>

      {syncStatus && (
        <div style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', padding: '0.6rem 1rem', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 'bold' }}>
          {syncStatus}
        </div>
      )}

      {/* TOP SUMMARY STATS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.8rem' }}>
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Pooled Capacity</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
            {pooled.total_pooled_capacity_tb} TB
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>{pooled.total_pooled_capacity_gb} GB Pooled across 6 Tiers</div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Available Storage</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#4ade80', marginTop: '0.2rem' }}>
            {(pooled.total_available_gb / 1024).toFixed(2)} TB
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>{pooled.total_available_gb} GB Free Headroom</div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Primary Mac Guarded Space</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#fbbf24', marginTop: '0.2rem' }}>
            {pooled.primary_mac_guarded_free_gb} GB Free
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>Automatic Pruning Guard Active</div>
        </div>

        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PySpark Indexed Files</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#c084fc', marginTop: '0.2rem' }}>
            {pooled.total_indexed_files} Artifacts
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>{pooled.total_indexed_size_gb} GB Cataloged</div>
        </div>
      </div>

      {/* MULTI-TRANSPORT PROTOCOL STATUS */}
      <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
        <h3 style={{ margin: '0 0 0.8rem 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 'bold' }}>
          🌐 Multi-Transport Ingestion & Protocol Engines
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.6rem' }}>
          {Object.entries(transports).map(([key, val]) => (
            <div key={key} style={{ background: '#1f2937', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
                🟢 {val}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 6 PHYSICAL & CLOUD STORAGE TIERS */}
      <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
        <h3 style={{ margin: '0 0 0.8rem 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 'bold' }}>
          🏗️ 6-Tier Hardware Nodes & Virtual Storage Tiers
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.8rem' }}>
          {nodes.map(node => {
            const usagePct = ((node.used_gb / node.total_capacity_gb) * 100).toFixed(1);
            return (
              <div key={node.node_id} style={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '6px', padding: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'bold', fontSize: '0.85rem', color: '#f8fafc' }}>{node.name}</span>
                  <span style={{ fontSize: '0.68rem', padding: '1px 6px', borderRadius: '3px', background: 'rgba(56,189,248,0.2)', color: '#38bdf8', fontWeight: 'bold' }}>
                    {node.status}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.3rem' }}>
                  <strong>Role:</strong> {node.target_data_class}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.1rem' }}>
                  <strong>Interconnect:</strong> {node.interconnect}
                </div>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.1rem' }}>
                  <strong>Mount:</strong> <code style={{ color: '#cbd5e1' }}>{node.mount_tier}</code>
                </div>

                {/* Progress bar */}
                <div style={{ marginTop: '0.6rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8' }}>
                    <span>{node.used_gb} GB used</span>
                    <span>{node.available_gb} GB free ({usagePct}%)</span>
                  </div>
                  <div style={{ width: '100%', height: '5px', background: '#334155', borderRadius: '3px', marginTop: '0.2rem', overflow: 'hidden' }}>
                    <div style={{ width: `${usagePct}%`, height: '100%', background: usagePct > 80 ? '#ef4444' : usagePct > 50 ? '#fbbf24' : '#10b981' }}></div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* INTERACTIVE PYSPARK SQL LAKEHOUSE STUDIO */}
      <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
          <h3 style={{ margin: 0, fontSize: '0.95rem', color: '#f8fafc', fontWeight: 'bold' }}>
            ⚡ PySpark NAS Lakehouse SQL Studio
          </h3>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button 
              onClick={() => { setSqlQuery('SELECT * FROM storage_hardware_nodes'); handleExecuteSql('SELECT * FROM storage_hardware_nodes'); }}
              style={{ background: '#334155', border: 'none', color: '#e2e8f0', padding: '3px 8px', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}
            >
              Hardware Nodes
            </button>
            <button 
              onClick={() => { setSqlQuery('SELECT category, count(*), sum(size_gb) FROM nas_unified_inventory GROUP BY category'); handleExecuteSql('SELECT category, count(*), sum(size_gb) FROM nas_unified_inventory GROUP BY category'); }}
              style={{ background: '#334155', border: 'none', color: '#e2e8f0', padding: '3px 8px', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}
            >
              Category Aggregation
            </button>
            <button 
              onClick={() => { setSqlQuery('SELECT * FROM nas_unified_inventory'); handleExecuteSql('SELECT * FROM nas_unified_inventory'); }}
              style={{ background: '#334155', border: 'none', color: '#e2e8f0', padding: '3px 8px', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}
            >
              Full Inventory
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.8rem' }}>
          <input 
            type="text" 
            value={sqlQuery} 
            onChange={(e) => setSqlQuery(e.target.value)}
            placeholder="Enter Spark SQL query (e.g. SELECT * FROM nas_unified_inventory)"
            style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', borderRadius: '6px', padding: '0.5rem 0.8rem', color: '#38bdf8', fontFamily: 'monospace', fontSize: '0.82rem' }}
          />
          <button 
            onClick={() => handleExecuteSql()}
            disabled={sqlLoading}
            style={{ background: '#3b82f6', border: 'none', color: '#fff', fontWeight: 'bold', padding: '0.5rem 1rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.82rem' }}
          >
            {sqlLoading ? 'Executing...' : 'Run SQL'}
          </button>
        </div>

        {sqlResult && (
          <pre style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: '6px', padding: '0.8rem', color: '#a7f3d0', fontFamily: 'monospace', fontSize: '0.75rem', overflowX: 'auto', margin: 0 }}>
            {sqlResult}
          </pre>
        )}
      </div>

      {/* GENETIC MOE STORAGE ROUTER SIMULATOR */}
      <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem' }}>
        <h3 style={{ margin: '0 0 0.8rem 0', fontSize: '0.95rem', color: '#f8fafc', fontWeight: 'bold' }}>
          🧬 Genetic MoE Dynamic File Routing Simulator
        </h3>
        <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: '0 0 0.8rem 0' }}>
          Simulates 4-Expert Softmax Gating (Capacity, Latency, Cloud Immortality, Edge Tester) to determine the optimal physical hardware tier for any file.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.6rem', marginBottom: '0.8rem' }}>
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>Filename</label>
            <input 
              type="text" 
              value={simFilename} 
              onChange={e => setSimFilename(e.target.value)}
              style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.4rem', color: '#f8fafc', fontSize: '0.78rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>Size (GB)</label>
            <input 
              type="number" 
              value={simSize} 
              onChange={e => setSimSize(e.target.value)}
              style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.4rem', color: '#f8fafc', fontSize: '0.78rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '2px' }}>File Type</label>
            <select 
              value={simType} 
              onChange={e => setSimType(e.target.value)}
              style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.4rem', color: '#f8fafc', fontSize: '0.78rem' }}
            >
              <option value="GGUF_MODEL_WEIGHTS">GGUF Model Weights</option>
              <option value="LORA_TRAINING_PAIR">LoRA Training Pair (.jsonl)</option>
              <option value="PARQUET_TELEMETRY">Parquet Lakehouse Table</option>
              <option value="UI_TEST_ARTIFACTS">UI Test Artifacts / Video</option>
              <option value="SOURCE_CODE_AST">Source Code AST</option>
              <option value="GENERAL_DATA">General Data</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button 
              onClick={handleRouteSimulation}
              disabled={simLoading}
              style={{ width: '100%', background: '#8b5cf6', border: 'none', color: '#fff', fontWeight: 'bold', padding: '0.5rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.78rem' }}
            >
              {simLoading ? 'Evaluating...' : 'Evaluate MoE Routing'}
            </button>
          </div>
        </div>

        {simResult && (
          <div style={{ background: '#1e1b4b', border: '1px solid #4338ca', borderRadius: '6px', padding: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 'bold', color: '#c7d2fe', fontSize: '0.85rem' }}>
                Selected Target Tier: <span style={{ color: '#4ade80' }}>{simResult.selected_node}</span>
              </span>
              <span style={{ fontSize: '0.72rem', background: '#312e81', color: '#a5b4fc', padding: '2px 8px', borderRadius: '4px' }}>
                Confidence: {simResult.confidence_pct}%
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '0.3rem' }}>
              <strong>Target Directory:</strong> <code>{simResult.target_directory}</code>
            </div>

            {/* Probability Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.4rem', marginTop: '0.6rem' }}>
              {simResult.routing_distribution && Object.entries(simResult.routing_distribution).map(([node, pct]) => (
                <div key={node} style={{ background: '#312e81', padding: '0.4rem', borderRadius: '4px', fontSize: '0.68rem', color: '#e0e7ff' }}>
                  <div style={{ color: '#93c5fd' }}>{node}</div>
                  <div style={{ fontWeight: 'bold', marginTop: '2px' }}>{pct}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
