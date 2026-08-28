import React, { useState, useEffect } from 'react';

export default function ROIImprovementsView({ roiStore, setRoiStore }) {
  const [subsystemFilter, setSubsystemFilter] = useState('all'); // 'all', 'localhost_3000', 'localhost_4000', '3d_spatial_map'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'to_do', 'active_pipeline', 'unsure'
  const [showGraduatedArchive, setShowGraduatedArchive] = useState(false);
  const [isDebating, setIsDebating] = useState(false);

  const apiHost = typeof window !== 'undefined' ? (window.location.hostname || 'localhost') : 'localhost';

  const updateRoiStatus = async (itemId, targetStatus) => {
    try {
      const res = await fetch(`http://${apiHost}:5001/api/roi_improvements/update_status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: itemId, status_list: targetStatus })
      });
      if (res.ok) {
        const data = await res.json();
        if (setRoiStore) setRoiStore(data);
      }
    } catch (e) {
      console.error('Failed to update ROI status:', e);
    }
  };

  const triggerDebateCycle = async () => {
    setIsDebating(true);
    try {
      const res = await fetch(`http://${apiHost}:5001/api/roi_improvements/trigger_debate_cycle`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        if (setRoiStore) setRoiStore(data);
      }
    } catch (e) {
      console.error('Failed to trigger debate cycle:', e);
    } finally {
      setTimeout(() => setIsDebating(false), 800);
    }
  };

  const fullList = (roiStore?.full_catalog || roiStore?.top_5_roi_improvements || []);
  
  const filteredItems = fullList.filter(item => {
    const matchesSubsystem = subsystemFilter === 'all' || item.category === subsystemFilter;
    const matchesStatus = statusFilter === 'all' || item.status_list === statusFilter;
    return matchesSubsystem && matchesStatus && item.status_list !== 'applied';
  });

  const graduatedItems = fullList.filter(item => item.status_list === 'applied')
    .concat(roiStore?.graduated_and_verified || []);
  const uniqueGraduated = Array.from(new Map(graduatedItems.map(item => [item.id, item])).values());

  const getSubsystemBadge = (cat) => {
    if (cat === '3d_spatial_map') return { label: '🥋 3D Spatial Map (Port 3000/5001)', bg: 'rgba(16,185,129,0.15)', color: '#34d399', border: '#10b981' };
    if (cat === 'localhost_4000') return { label: '📱 localhost:4000 App Store & DSP', bg: 'rgba(56,189,248,0.15)', color: '#38bdf8', border: '#38bdf8' };
    return { label: '🌐 localhost:3000 Swarm Mesh Hub', bg: 'rgba(168,85,247,0.15)', color: '#c084fc', border: '#a855f7' };
  };

  const getStatusBadge = (status) => {
    if (status === 'active_pipeline') return { label: '⚡ Active Pipeline', bg: 'rgba(56,189,248,0.2)', color: '#7dd3fc' };
    if (status === 'unsure') return { label: '❓ In Review', bg: 'rgba(168,85,247,0.2)', color: '#d8b4fe' };
    return { label: '📋 Actionable To-Do', bg: 'rgba(234,179,8,0.2)', color: '#fde047' };
  };

  return (
    <section className="card leaderboard-card" style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '1.2rem' }}>
      
      {/* HEADER & TRI-ORCHESTRATOR DEBATE SYNC */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #30363d', paddingBottom: '1rem', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.8rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.2rem' }}>🧠</span>
            <h2 style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 'bold', margin: 0 }}>
              Tri-Orchestrator AI Debate ROI Accumulator
            </h2>
            <span style={{ fontSize: '0.65rem', background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', padding: '2px 7px', borderRadius: '10px', fontWeight: 'bold' }}>
              Cycle #{roiStore?.debate_cycle || 1} Active
            </span>
          </div>
          <p style={{ color: '#8b949e', fontSize: '0.8rem', margin: '0.3rem 0 0 0' }}>
            High-yield monorepo optimizations synthesized via continuous debate across <strong>localhost:3000</strong> (Mesh Hub), <strong>localhost:4000</strong> (App Store &amp; Movesense DSP), and the <strong>3D Spatial Map</strong>.
          </p>
        </div>

        {/* QUICK PORT NAVIGATOR & RUN DEBATE TRIGGER */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: '0.68rem', background: 'rgba(168,85,247,0.15)', border: '1px solid #a855f7', color: '#c084fc', padding: '3px 8px', borderRadius: '6px', textDecoration: 'none', fontWeight: 'bold' }}
          >
            🌐 :3000 Hub ↗
          </a>
          <a
            href="http://localhost:4000"
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: '0.68rem', background: 'rgba(56,189,248,0.15)', border: '1px solid #38bdf8', color: '#38bdf8', padding: '3px 8px', borderRadius: '6px', textDecoration: 'none', fontWeight: 'bold' }}
          >
            📱 :4000 App ↗
          </a>
          <button
            onClick={triggerDebateCycle}
            disabled={isDebating}
            style={{
              background: isDebating ? 'rgba(16,185,129,0.3)' : 'linear-gradient(135deg, #10b981, #059669)',
              border: '1px solid #34d399',
              color: '#fff',
              padding: '4px 10px',
              borderRadius: '6px',
              cursor: isDebating ? 'not-allowed' : 'pointer',
              fontSize: '0.72rem',
              fontWeight: 'bold'
            }}
          >
            {isDebating ? '⚡ Synthesizing Debate...' : '⚡ Run Live AI Debate'}
          </button>
        </div>
      </div>

      {/* FILTER BUTTONS: SUBSYSTEM & STATUS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.6rem', background: '#161b22', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid #30363d' }}>
        
        {/* Subsystem Filters */}
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.7rem', color: '#8b949e', fontWeight: 'bold' }}>Subsystem:</span>
          {[
            { id: 'all', label: `All (${fullList.filter(i => i.status_list !== 'applied').length})` },
            { id: '3d_spatial_map', label: '🥋 3D Spatial Map' },
            { id: 'localhost_3000', label: '🌐 localhost:3000' },
            { id: 'localhost_4000', label: '📱 localhost:4000' }
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setSubsystemFilter(f.id)}
              style={{
                background: subsystemFilter === f.id ? '#21262d' : 'transparent',
                border: subsystemFilter === f.id ? '1px solid #58a6ff' : '1px solid transparent',
                color: subsystemFilter === f.id ? '#58a6ff' : '#8b949e',
                padding: '2px 7px',
                borderRadius: '4px',
                fontSize: '0.68rem',
                cursor: 'pointer',
                fontWeight: subsystemFilter === f.id ? 'bold' : 'normal'
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Graduated Toggle */}
        <button
          onClick={() => setShowGraduatedArchive(!showGraduatedArchive)}
          style={{
            background: showGraduatedArchive ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.05)',
            border: showGraduatedArchive ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.15)',
            color: showGraduatedArchive ? '#34d399' : '#8b949e',
            padding: '3px 8px',
            borderRadius: '4px',
            fontSize: '0.68rem',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          {showGraduatedArchive ? 'Hide Graduated Archive' : `📦 Graduated Archive (${uniqueGraduated.length})`}
        </button>
      </div>

      {/* ACTIVE ACCUMULATED ROI MOVES LIST */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {filteredItems.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: '#34d399', background: 'rgba(16,185,129,0.05)', borderRadius: '8px', border: '1px dashed #10b981' }}>
            🎉 <strong>All Filtered AI Debate Priorities Implemented &amp; Graduated!</strong>
            <div style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '0.3rem' }}>
              Click "⚡ Run Live AI Debate" above to synthesize the next round of monorepo moves.
            </div>
          </div>
        ) : (
          filteredItems.map((item, idx) => {
            const subBadge = getSubsystemBadge(item.category);
            const statusBadge = getStatusBadge(item.status_list);

            return (
              <div
                key={item.id}
                style={{
                  background: '#161b22',
                  borderRadius: '6px',
                  border: '1px solid #30363d',
                  padding: '0.85rem 1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  transition: 'border 0.2s'
                }}
              >
                {/* Top Row: Badges & Title */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.4rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ background: '#21262d', color: '#58a6ff', width: '22px', height: '22px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 'bold' }}>
                      #{idx + 1}
                    </span>
                    <h3 style={{ color: '#fff', fontSize: '0.92rem', fontWeight: 'bold', margin: 0 }}>
                      {item.title}
                    </h3>
                    <span style={{ fontSize: '0.62rem', background: subBadge.bg, border: `1px solid ${subBadge.border}`, color: subBadge.color, padding: '1px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
                      {subBadge.label}
                    </span>
                  </div>

                  <span style={{ fontSize: '0.62rem', background: statusBadge.bg, color: statusBadge.color, padding: '2px 7px', borderRadius: '10px', fontWeight: 'bold' }}>
                    {statusBadge.label}
                  </span>
                </div>

                {/* Description */}
                <p style={{ color: '#8b949e', fontSize: '0.75rem', margin: 0 }}>
                  {item.desc}
                </p>

                {/* Debate Consensus Quote Box */}
                {item.debate_quote && (
                  <div style={{ background: '#0d1117', borderLeft: '3px solid #38bdf8', padding: '0.35rem 0.6rem', borderRadius: '0 4px 4px 0', fontSize: '0.7rem', color: '#7dd3fc', fontStyle: 'italic' }}>
                    💬 <strong>AI Debate:</strong> "{item.debate_quote}"
                  </div>
                )}

                {/* Bottom Row: Metrics & Triage Controls */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                  <div style={{ display: 'flex', gap: '0.8rem', fontSize: '0.7rem', color: '#8b949e' }}>
                    <span>Estimated Yield: <strong style={{ color: '#f59e0b', fontSize: '0.76rem' }}>{item.roi_multiplier} ROI</strong></span>
                    <span>Confidence: <strong style={{ color: '#34d399' }}>{item.confidence}</strong></span>
                    <span>Cost: <strong style={{ color: '#fff' }}>{item.cost}</strong></span>
                  </div>

                  {/* Triage Action Buttons */}
                  <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                    <button
                      onClick={() => updateRoiStatus(item.id, 'active_pipeline')}
                      style={{ background: item.status_list === 'active_pipeline' ? 'rgba(56,189,248,0.25)' : 'rgba(255,255,255,0.05)', border: '1px solid rgba(56,189,248,0.4)', color: '#38bdf8', padding: '2px 6px', borderRadius: '3px', fontSize: '0.62rem', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      ⚡ Active
                    </button>
                    <button
                      onClick={() => updateRoiStatus(item.id, 'unsure')}
                      style={{ background: item.status_list === 'unsure' ? 'rgba(168,85,247,0.25)' : 'rgba(255,255,255,0.05)', border: '1px solid rgba(168,85,247,0.4)', color: '#c084fc', padding: '2px 6px', borderRadius: '3px', fontSize: '0.62rem', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      ❓ Review
                    </button>
                    <button
                      onClick={() => updateRoiStatus(item.id, 'applied')}
                      style={{ background: 'linear-gradient(135deg, #10b981, #059669)', border: '1px solid #34d399', color: '#fff', padding: '2px 8px', borderRadius: '3px', fontSize: '0.62rem', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      ✅ Apply &amp; Graduate
                    </button>
                  </div>
                </div>

              </div>
            );
          })
        )}
      </div>

      {/* GRADUATED & VERIFIED ARCHIVE DRAWER */}
      {showGraduatedArchive && (
        <div style={{ marginTop: '1.2rem', background: '#161b22', padding: '0.9rem', borderRadius: '6px', border: '1px solid #30363d' }}>
          <h4 style={{ color: '#34d399', fontSize: '0.8rem', fontWeight: 'bold', margin: '0 0 0.5rem 0' }}>
            📦 Graduated &amp; Verified Monorepo Achievements
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {uniqueGraduated.map(item => (
              <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0d1117', padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.2)', fontSize: '0.7rem' }}>
                <span style={{ color: '#e2e8f0', fontWeight: 'bold' }}>✅ {item.title}</span>
                <button
                  onClick={() => updateRoiStatus(item.id, 'to_do')}
                  style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: '#94a3b8', padding: '1px 5px', borderRadius: '3px', fontSize: '0.6rem', cursor: 'pointer' }}
                >
                  Reopen
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

    </section>
  );
}
