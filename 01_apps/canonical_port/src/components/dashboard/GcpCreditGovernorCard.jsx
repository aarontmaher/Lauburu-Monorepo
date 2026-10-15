import React, { useState, useEffect } from 'react';

export function GcpCreditGovernorCard({ onDispatchAction }) {
  const [status, setStatus] = useState(null);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBatch, setSelectedBatch] = useState('BATCH_01_EDGE_SLMS');
  const [projectedSpend, setProjectedSpend] = useState(8.50);
  const [burstPreview, setBurstPreview] = useState(null);
  const [exportStatus, setExportStatus] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  const fetchCloudStatus = async () => {
    try {
      const [stRes, btRes] = await Promise.all([
        fetch('/api/v1/cloud/gcp/status'),
        fetch('/api/v1/cloud/gcp/batches')
      ]);
      if (stRes.ok) {
        const stData = await stRes.json();
        setStatus(stData);
      }
      if (btRes.ok) {
        const btData = await btRes.json();
        setBatches(btData.batches || []);
      }
    } catch (e) {
      console.error('Failed to load GCP status', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCloudStatus();
    const interval = setInterval(fetchCloudStatus, 8000);
    return () => clearInterval(interval);
  }, []);

  const handlePreviewBurst = async () => {
    try {
      const res = await fetch('/api/v1/cloud/gcp/burst/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_id: selectedBatch,
          projected_spend_aud: projectedSpend
        })
      });
      if (res.ok) {
        const data = await res.json();
        setBurstPreview(data);
      }
    } catch (e) {
      console.error('Failed to preview burst', e);
    }
  };

  const handleExportLakehouseDataset = async () => {
    setIsExporting(true);
    try {
      const res = await fetch('/api/v1/cloud/gcp/dataset/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (res.ok) {
        const data = await res.json();
        setExportStatus(data);
      }
    } catch (e) {
      console.error('Failed to export dataset', e);
    } finally {
      setIsExporting(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="cyber-card" style={{ padding: '16px' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          ☁️ Querying Google Cloud Credit Governor...
        </div>
      </div>
    );
  }

  const total = status?.total_grant_aud || 1400.0;
  const committed = status?.total_committed_aud || 350.0;
  const remaining = status?.remaining_reserve_aud || 1050.0;
  const progressPct = Math.min(100, Math.round((committed / total) * 100));

  return (
    <div className="cyber-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>☁️</span>
            <span style={{ fontWeight: 700, fontSize: '0.95rem', letterSpacing: '0.05em' }}>
              GOOGLE CLOUD $1,400 ESCALATION
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Billing: <code>{status?.billing_account_id}</code> | Project: <code>{status?.project_id}</code>
          </div>
        </div>
        <span className="badge-cyan" style={{ fontSize: '0.7rem' }}>
          {status?.status || 'ACTIVE'}
        </span>
      </div>

      {/* Credit Pool Progress Bar */}
      <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
          <span><strong>Committed:</strong> ${committed.toFixed(2)} AUD ({progressPct}%)</span>
          <span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>
            Remaining Reserve: ${remaining.toFixed(2)} AUD
          </span>
        </div>
        <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${progressPct}%`,
              background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald))',
              transition: 'width 0.4s ease'
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
          <span>$0 Free Baseline</span>
          <span>$1,400 Total Grant</span>
        </div>
      </div>

      {/* Circuit Breaker & Safety Invariant */}
      <div style={{
        background: 'rgba(16, 185, 129, 0.08)',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        borderRadius: '6px',
        padding: '10px 12px',
        fontSize: '0.78rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-emerald)', fontWeight: 700 }}>
          <span>🛡️ HARDWARE CIRCUIT BREAKER ARMED</span>
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          Ephemeral Spot L4 VMs enforce: <code>{status?.circuit_breaker}</code>.
          Zero out-of-pocket risk against Aaron's account.
        </div>
      </div>

      {/* Staged Batches */}
      <div>
        <div style={{ fontSize: '0.82rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)' }}>
          STAGED DISTILLATION BATCHES (4 TRANCHES)
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {batches.map((b) => (
            <div
              key={b.batch_id}
              style={{
                background: selectedBatch === b.batch_id ? 'rgba(6, 182, 212, 0.08)' : 'var(--bg-secondary)',
                border: `1px solid ${selectedBatch === b.batch_id ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                borderRadius: '6px',
                padding: '10px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onClick={() => setSelectedBatch(b.batch_id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{b.name}</span>
                <span className="badge-cyan" style={{ fontSize: '0.7rem' }}>${b.budget_aud.toFixed(2)} AUD</span>
              </div>
              <div style={{ display: 'flex', gap: '12px', fontSize: '0.73rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                <span>⚡ {b.spot_gpu_hours}</span>
                <span>📈 Expected: <strong>{b.expected_elo_gain}</strong></span>
                <span style={{ color: 'var(--accent-emerald)' }}>● {b.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Micro-Burst Simulator */}
      <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: '8px' }}>
          🚀 SPOT GPU MICRO-BURST PREVIEW
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Spend ($ AUD):</label>
          <input
            type="number"
            min="1.0"
            max="175.0"
            step="1.0"
            value={projectedSpend}
            onChange={(e) => setProjectedSpend(parseFloat(e.target.value) || 0)}
            className="cyber-input"
            style={{ width: '80px', padding: '4px 8px', fontSize: '0.8rem' }}
          />
          <button
            className="cyber-btn"
            style={{ fontSize: '0.75rem', padding: '5px 10px', background: 'var(--accent-cyan)', color: 'var(--bg-primary)' }}
            onClick={handlePreviewBurst}
          >
            Calculate GPU-Hours
          </button>
        </div>

        {burstPreview && (
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '4px' }}>
            <div>Instance: <strong>{burstPreview.instance_type}</strong></div>
            <div>Estimated Run: <strong>{burstPreview.estimated_gpu_hours} Spot L4 GPU-Hours</strong> (${burstPreview.projected_spend_aud} AUD)</div>
            <div>Safety: <code>{burstPreview.circuit_breaker_command}</code></div>
          </div>
        )}
      </div>

      {/* Lakehouse Dataset Exporter */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
        <button
          className="cyber-btn"
          style={{ fontSize: '0.75rem', padding: '6px 12px' }}
          onClick={handleExportLakehouseDataset}
          disabled={isExporting}
        >
          {isExporting ? '⏳ Exporting...' : '📦 Export Lakehouse Dataset for Vertex AI'}
        </button>
        {exportStatus && (
          <span style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)' }}>
            ✓ {exportStatus.pairs_exported} pairs exported
          </span>
        )}
      </div>
    </div>
  );
}
