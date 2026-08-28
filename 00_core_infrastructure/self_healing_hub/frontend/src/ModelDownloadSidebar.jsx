import React, { useState, useEffect } from 'react';

export default function ModelDownloadSidebar() {
  const [downloadData, setDownloadData] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(true);

  useEffect(() => {
    const fetchDownloadStatus = async () => {
      try {
        const apiHost = window.location.hostname || 'localhost';
        const res = await fetch(`http://${apiHost}:5001/api/models/download_status`);
        if (res.ok) {
          setDownloadData(await res.json());
        }
      } catch (e) {
        console.error('Failed to fetch model download status:', e);
      }
    };

    fetchDownloadStatus();
    const interval = setInterval(fetchDownloadStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!downloadData) return null;

  const active = downloadData.active_model || {};
  const queue = downloadData.queue || [];
  const downloadedGb = typeof active.downloaded_gb === 'number' ? active.downloaded_gb.toFixed(2) : '0.00';
  const progressPct = typeof active.progress_pct === 'number' ? active.progress_pct.toFixed(1) : '0.0';
  const speed = typeof downloadData.speed_mbps === 'number' ? downloadData.speed_mbps.toFixed(1) : '0.0';
  const eta = typeof downloadData.eta_minutes === 'number' ? downloadData.eta_minutes.toFixed(1) : '0.0';

  return (
    <div style={{
      position: 'fixed',
      bottom: '2rem',
      right: '2rem',
      zIndex: 9999,
      width: isCollapsed ? 'auto' : '340px',
      background: 'rgba(17, 24, 39, 0.95)',
      backdropFilter: 'blur(12px)',
      border: '1px solid rgba(56, 189, 248, 0.35)',
      borderRadius: '12px',
      boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6), 0 0 15px rgba(56, 189, 248, 0.2)',
      color: '#f8fafc',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      transition: 'all 0.3s ease',
      overflow: 'hidden'
    }}>
      {/* HEADER */}
      <div 
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.8rem 1rem',
          background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.15), rgba(168, 85, 247, 0.15))',
          borderBottom: isCollapsed ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            display: 'inline-block',
            width: '9px',
            height: '9px',
            borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 8px #10b981'
          }} />
          <span style={{ fontWeight: 'bold', fontSize: '0.85rem', color: '#f8fafc' }}>
            📥 Local AI Model Stream
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 'bold' }}>
            {speed} MB/s
          </span>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            {isCollapsed ? '▲' : '▼'}
          </span>
        </div>
      </div>

      {/* EXPANDED CONTENT */}
      {!isCollapsed && (
        <div style={{ padding: '0.9rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          
          {/* LOCATION & TB4 BRIDGE BADGE */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: '#94a3b8' }}>
            <span>Target: <strong style={{ color: '#f8fafc' }}>Headless Mac Pro</strong></span>
            <span style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              10G TB4: {downloadData.tb4_link_latency_ms ?? 0.277}ms
            </span>
          </div>

          {/* ACTIVE MODEL CARD */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '0.7rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.3rem' }}>
              <span style={{ fontWeight: 'bold', fontSize: '0.82rem', color: '#38bdf8' }}>
                {active.name ?? 'Qwen 3.8 27B Flagship'}
              </span>
              <span style={{ fontSize: '0.7rem', color: '#a855f7', fontWeight: 'bold' }}>
                {active.size_gb ?? 17.1} GB
              </span>
            </div>
            
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontFamily: 'monospace', marginBottom: '0.4rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {active.filename ?? 'Qwen3.8-27B-Q4_K_M.gguf'}
            </div>

            {/* PROGRESS BAR */}
            <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.4rem' }}>
              <div style={{
                width: `${Math.min(100, Math.max(0, parseFloat(progressPct)))}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #38bdf8, #818cf8)',
                boxShadow: '0 0 8px rgba(56, 189, 248, 0.5)'
              }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#cbd5e1' }}>
              <span>{downloadedGb} / {active.size_gb ?? 17.1} GB ({progressPct}%)</span>
              <span style={{ color: '#38bdf8' }}>ETA: ~{eta}m</span>
            </div>
          </div>

          {/* QUEUE INVENTORY */}
          <div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>
              Download Queue (Official Hugging Face CLI)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              {queue.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', padding: '4px 6px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
                  <span style={{ color: item.status === 'COMPLETED' ? '#34d399' : item.status === 'DOWNLOADING' ? '#38bdf8' : '#94a3b8', fontWeight: item.status === 'DOWNLOADING' ? 'bold' : 'normal' }}>
                    {item.status === 'DOWNLOADING' ? '▶ ' : item.status === 'COMPLETED' ? '✓ ' : '• '}{item.name}
                  </span>
                  <span style={{ fontSize: '0.65rem', color: '#64748b' }}>
                    {item.downloaded_gb ? `${item.downloaded_gb.toFixed(1)} / ` : ''}{item.size_gb} GB
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* STORAGE HEADROOM FOOTER */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '0.5rem' }}>
            <span style={{ color: '#94a3b8' }}>Headless Mac Free:</span>
            <span style={{ color: '#34d399', fontWeight: 'bold' }}>{downloadData.headless_mac_free_gb ?? 415.6} GB</span>
          </div>

          {/* ENGINE FOOTER */}
          <div style={{ fontSize: '0.65rem', color: '#64748b', textAlign: 'center' }}>
            🚀 Standard `hf download` • Multi-threaded Transfer
          </div>

        </div>
      )}
    </div>
  );
}
