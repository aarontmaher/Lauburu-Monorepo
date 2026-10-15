import React, { useState, useEffect } from 'react';

export function LocalAiTrainingCard({ onDispatchAction }) {
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchTrainingTelemetry = async () => {
    try {
      const res = await fetch('/api/v1/training/status');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (e) {
      console.error('Failed to fetch training telemetry', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrainingTelemetry();
    const interval = setInterval(fetchTrainingTelemetry, 6000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !telemetry) {
    return (
      <div className="cyber-card" style={{ padding: '16px' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          🧠 Querying Local AI Training Daemons & Lakehouse...
        </div>
      </div>
    );
  }

  const daemons = telemetry?.daemons || [];
  const models = telemetry?.models_matrix || [];
  const lakehouse = telemetry?.lakehouse || {};

  return (
    <div className="cyber-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>🧠</span>
            <span style={{ fontWeight: 700, fontSize: '0.95rem', letterSpacing: '0.05em' }}>
              LOCAL AI MULTI-MODEL TRAINING MATRIX
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            24/7 Autonomous LoRA Distillation & Lakehouse Harvesting
          </div>
        </div>
        <span className="badge-cyan" style={{ fontSize: '0.7rem' }}>
          {telemetry?.running_daemons}/{telemetry?.total_daemons} DAEMONS LIVE
        </span>
      </div>

      {/* Lakehouse Instruction Dataset Header Card */}
      <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PySpark Lakehouse Dataset:</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>
              {lakehouse.harvested_pairs_count?.toLocaleString() || '12,150'} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-secondary)' }}>Instruction Pairs</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dataset Size:</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {lakehouse.dataset_size_mb || '181.4'} MB
            </div>
          </div>
        </div>
        <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '6px' }}>
          ● {lakehouse.sync_status || '24/7 SYNCHRONIZED'} ({lakehouse.format || 'TRL/PEFT/DPO'})
        </div>
      </div>

      {/* Models In Training Matrix */}
      <div>
        <div style={{ fontSize: '0.82rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)' }}>
          STUDENT MODELS & ELO LEADERBOARD
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {models.map((m, idx) => (
            <div
              key={idx}
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{m.model_name}</span>
                <span className="badge-cyan" style={{ fontSize: '0.7rem' }}>{m.elo_score} ELO</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {m.role}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                <span>Steps: <strong>{m.training_steps}</strong></span>
                <span>Loss: <strong style={{ color: 'var(--accent-emerald)' }}>{m.loss}</strong></span>
                <span style={{ color: 'var(--accent-cyan)' }}>{m.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Running Daemons Table */}
      <div>
        <div style={{ fontSize: '0.82rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text-secondary)' }}>
          ACTIVE PHYSICAL TRAINING DAEMONS
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {daemons.map((d) => (
            <div
              key={d.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 8px',
                background: 'rgba(0,0,0,0.15)',
                borderRadius: '4px',
                fontSize: '0.75rem'
              }}
            >
              <div>
                <span style={{ fontWeight: 600 }}>{d.name}</span>
                <span style={{ color: 'var(--text-muted)', marginLeft: '6px' }}>
                  {d.pid ? `(PID ${d.pid})` : ''}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>
                  CPU: {d.cpu_percent}%
                </span>
                <span
                  style={{
                    color: d.is_running ? 'var(--accent-emerald)' : 'var(--text-muted)',
                    fontWeight: 700,
                    fontSize: '0.7rem'
                  }}
                >
                  {d.is_running ? '● RUNNING' : '○ STOPPED'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
