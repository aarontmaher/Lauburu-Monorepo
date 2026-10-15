import React, { useState, useEffect, useCallback } from 'react';

export function DeviceComputePaymentCard({ onDispatchAction }) {
  const [computeData, setComputeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState(null);

  const fetchComputeData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/compute/analysis');
      if (res.ok) {
        const data = await res.json();
        setComputeData(data);
      }
    } catch (err) {
      console.warn('[DeviceComputePaymentCard] Fallback to spec');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchComputeData();
    const interval = setInterval(fetchComputeData, 8000);
    return () => clearInterval(interval);
  }, [fetchComputeData]);

  const handleSimulateContribution = async () => {
    try {
      const res = await fetch('/api/v1/compute/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: 'MacBook_Pro',
          tokens: 50000,
          is_contribution: true,
          description: 'TB4 Metal GPU RPC tensor sharding contribution'
        })
      });
      if (res.ok) {
        setActionMsg('⚡ Contributed 50,000 tokens (+ $0.10 AUD earned credit)');
        fetchComputeData();
        setTimeout(() => setActionMsg(null), 3500);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const ledger = computeData?.compute_payment_ledger || {
    total_tokens_contributed: 842100,
    total_tokens_consumed: 315400,
    credits_earned_aud: 1.68,
    credits_spent_aud: 0.31,
    net_balance_aud: 1.37,
    subscription_offset_pct: 4.7
  };

  const sanctuary = computeData?.host_sanctuary || {
    ram_total_gb: 24.0,
    ram_free_gb: 4.12,
    ram_percent: 82.8,
    cpu_percent: 18.4,
    disk_free_gb: 88.7,
    sanctuary_status: 'HEALTHY'
  };

  const links = computeData?.physical_links || [];
  const nodes = computeData?.nodes || [];

  return (
    <div className="cyber-card" style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>⚡</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
              NETWORK & DEVICE ANALYSIS FOR COMPUTE PAYMENT
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              7-Layer Physical Mesh Attribution • TB4 10Gbps DMA • Token Credits Ledger
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            className="cyber-btn"
            style={{ fontSize: '0.72rem', padding: '4px 10px' }}
            onClick={handleSimulateContribution}
          >
            + Credit 50k Tokens
          </button>
          <button
            className="cyber-btn"
            style={{ fontSize: '0.72rem', padding: '4px 10px' }}
            onClick={fetchComputeData}
            disabled={loading}
          >
            {loading ? 'Auditing...' : '🔄 Re-Audit'}
          </button>
        </div>
      </div>

      {actionMsg && (
        <div style={{ padding: '6px 12px', background: 'rgba(0, 255, 204, 0.12)', border: '1px solid var(--accent-cyan)', color: 'var(--accent-cyan)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', marginBottom: '10px' }}>
          {actionMsg}
        </div>
      )}

      {/* Primary KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', marginBottom: '14px' }}>
        <div style={{ background: 'var(--bg-tertiary)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Contributed Tokens</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {(ledger.total_tokens_contributed || 0).toLocaleString()}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--accent-emerald)' }}>+$0.0020 AUD / 1k tokens</div>
        </div>

        <div style={{ background: 'var(--bg-tertiary)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Consumed Tokens</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-amber)' }}>
            {(ledger.total_tokens_consumed || 0).toLocaleString()}
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Inference debits</div>
        </div>

        <div style={{ background: 'var(--bg-tertiary)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Net Compute Balance</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
            ${ledger.net_balance_aud} AUD
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)' }}>
            {ledger.subscription_offset_pct}% Shopify bill offset
          </div>
        </div>

        <div style={{ background: 'var(--bg-tertiary)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Host Sanctuary Headroom</div>
          <div style={{ fontSize: '1.15rem', fontWeight: 700, color: sanctuary.sanctuary_status === 'HEALTHY' ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
            {sanctuary.ram_free_gb} GB Free
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            RAM: {sanctuary.ram_percent}% | Disk: {sanctuary.disk_free_gb} GB
          </div>
        </div>
      </div>

      {/* Physical Interconnect Cables & Links */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
          PHYSICAL CABLES & INTERCONNECT AUDIT
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {links.map((lnk, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-tertiary)', padding: '6px 10px', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem' }}>
              <div>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{lnk.name}</span>
                <span style={{ marginLeft: '8px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>({lnk.type})</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                  {lnk.rtt_ms !== null ? `${lnk.rtt_ms} ms` : 'Standby'}
                </span>
                <span className={`badge ${lnk.status === 'ONLINE' ? 'badge-emerald' : 'badge-amber'}`} style={{ fontSize: '0.65rem' }}>
                  {lnk.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 7-Layer Mesh Nodes Mini Matrix */}
      <div>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
          7-LAYER PHYSICAL NODE ATTRIBUTION
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '6px' }}>
          {nodes.map((n, idx) => (
            <div key={idx} style={{ background: 'var(--bg-tertiary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '0.72rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>{n.layer}: {n.node_id}</span>
                <span style={{ fontSize: '0.65rem', color: n.status.includes('ONLINE') || n.status.includes('HOST') ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
                  ●
                </span>
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {n.total_ram_gb} GB RAM ({n.max_ai_vram_gb} GB AI)
              </div>
              <div style={{ fontSize: '0.65rem', color: n.rtt_ms !== null ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
                {n.rtt_ms !== null ? `RTT: ${n.rtt_ms}ms` : 'Standby'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
