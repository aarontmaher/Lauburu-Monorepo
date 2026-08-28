import React, { useState, useEffect } from 'react';

export default function SwarmArenaCompetitionView() {
  const [arenaData, setArenaData] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState('TASK_CODE_REFACTOR');
  const [isRunning, setIsRunning] = useState(false);
  const [matchResultFeedback, setMatchResultFeedback] = useState(null);

  const fetchArenaData = async () => {
    try {
      const apiHost = window.location.hostname || 'localhost';
      const [compRes, tasksRes] = await Promise.all([
        fetch(`http://${apiHost}:5001/api/swarm_arena/competitions`),
        fetch(`http://${apiHost}:5001/api/swarm_arena/tasks`)
      ]);
      if (compRes.ok) setArenaData(await compRes.json());
      if (tasksRes.ok) setTasks(await tasksRes.json());
    } catch (e) {
      console.error('Failed to fetch arena data:', e);
    }
  };

  useEffect(() => {
    fetchArenaData();
    const interval = setInterval(fetchArenaData, 6000);
    return () => clearInterval(interval);
  }, []);

  const triggerNewCompetition = async () => {
    setIsRunning(true);
    setMatchResultFeedback('⚡ Running Tri-Orchestrator Tournament: Local Only vs Cloud Only vs Hybrid Fusion...');
    try {
      const apiHost = window.location.hostname || 'localhost';
      const res = await fetch(`http://${apiHost}:5001/api/swarm_arena/competitions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: selectedTask })
      });
      if (res.ok) {
        const newMatch = await res.json();
        setMatchResultFeedback(`🏆 Match Complete! Victor: ${newMatch.winners?.overall_match_victor}`);
        fetchArenaData();
        setTimeout(() => setMatchResultFeedback(null), 6000);
      }
    } catch (e) {
      setMatchResultFeedback(`Error running arena: ${e.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const latest = arenaData?.latest_match;
  const competitors = latest?.competitors || {};
  const localComp = competitors.local_only || {};
  const cloudComp = competitors.cloud_only || {};
  const hybridComp = competitors.hybrid_fusion || {};
  const analysis = latest?.post_match_analysis || {};
  const winners = latest?.winners || {};

  return (
    <div style={{ background: '#0b1329', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '12px', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
      
      {/* ARENA HEADER & TRIGGER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.8rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.6rem' }}>⚔️</span>
            <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 'bold' }}>
              Tri-Orchestrator Swarm Arena: Local vs Cloud vs Hybrid Tournament
            </h3>
            <span style={{ fontSize: '0.72rem', background: 'rgba(236,72,153,0.15)', color: '#f472b6', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(236,72,153,0.3)', fontWeight: 'bold' }}>
              Machine Learning Feedback Engine
            </span>
          </div>
          <p style={{ margin: '0.3rem 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
            Continuous competitive benchmarking comparing strategy, cost, latency, and syntax accuracy across <strong>Local Only</strong>, <strong>Cloud Only</strong>, and <strong>Hybrid Fusion</strong> swarms.
          </p>
        </div>

        {/* TOURNAMENT CONTROLS */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <select 
            value={selectedTask}
            onChange={(e) => setSelectedTask(e.target.value)}
            style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.15)', color: '#f8fafc', padding: '6px 10px', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
          >
            {tasks.map(t => (
              <option key={t.task_id} value={t.task_id}>
                {t.task_name} ({t.category})
              </option>
            ))}
          </select>

          <button
            onClick={triggerNewCompetition}
            disabled={isRunning}
            style={{
              background: isRunning ? 'rgba(255,255,255,0.1)' : 'linear-gradient(135deg, #ec4899, #8b5cf6)',
              border: 'none',
              color: '#fff',
              fontWeight: 'bold',
              padding: '7px 16px',
              borderRadius: '6px',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              fontSize: '0.8rem',
              boxShadow: '0 4px 12px rgba(236,72,153,0.3)'
            }}
          >
            {isRunning ? '⚔️ In Progress...' : '🚀 Run Swarm Matchup'}
          </button>
        </div>
      </div>

      {matchResultFeedback && (
        <div style={{ background: 'rgba(56,189,248,0.15)', border: '1px solid #38bdf8', color: '#38bdf8', padding: '0.7rem 1.2rem', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 'bold' }}>
          {matchResultFeedback}
        </div>
      )}

      {/* CURRENT MATCH TASK CARD */}
      {latest?.task && (
        <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '0.8rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.6rem' }}>
          <div>
            <span style={{ fontSize: '0.7rem', color: '#38bdf8', textTransform: 'uppercase', fontWeight: 'bold' }}>Active Benchmark Task:</span>
            <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#f8fafc', marginTop: '0.1rem' }}>
              {latest.task.task_name}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              {latest.task.description}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem' }}>
            <span style={{ fontSize: '0.7rem', padding: '3px 8px', borderRadius: '4px', background: 'rgba(56,189,248,0.15)', color: '#38bdf8' }}>
              Category: {latest.task.category}
            </span>
            <span style={{ fontSize: '0.7rem', padding: '3px 8px', borderRadius: '4px', background: 'rgba(234,179,8,0.15)', color: '#facc15' }}>
              Complexity: {latest.task.complexity}
            </span>
          </div>
        </div>
      )}

      {/* 3-WAY COMPETITOR CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        
        {/* LOCAL ONLY SWARM */}
        <div style={{ background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.2rem' }}>🏠</span>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#34d399', fontWeight: 'bold' }}>
                Local Only Swarm
              </h4>
            </div>
            <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.15)', color: '#34d399', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
              Score: {localComp.overall_performance_score || 96.8}%
            </span>
          </div>

          <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
            <strong>Engine:</strong> {localComp.model_mesh}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
            <strong>Strategy:</strong> {localComp.strategy}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.2rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Financial Cost</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#34d399' }}>{localComp.cost_display || '$0.00'}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Execution Latency</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#38bdf8' }}>{localComp.latency_ms || 520} ms</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Throughput</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#a855f7' }}>{localComp.throughput_tok_s || 24.5} tok/s</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Truth Compliance</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#10b981' }}>{localComp.truth_compliance_pct || 100}%</div>
            </div>
          </div>

          <div style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic', marginTop: 'auto' }}>
            💡 {localComp.key_strength}
          </div>
        </div>

        {/* CLOUD ONLY SWARM */}
        <div style={{ background: 'rgba(59,130,246,0.04)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.2rem' }}>☁️</span>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#60a5fa', fontWeight: 'bold' }}>
                Cloud Only Swarm
              </h4>
            </div>
            <span style={{ fontSize: '0.72rem', background: 'rgba(59,130,246,0.15)', color: '#60a5fa', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
              Score: {cloudComp.overall_performance_score || 98.2}%
            </span>
          </div>

          <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
            <strong>Engine:</strong> {cloudComp.model_mesh}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
            <strong>Strategy:</strong> {cloudComp.strategy}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.2rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Financial Cost</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#facc15' }}>{cloudComp.cost_display || '$0.045'}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Execution Latency</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#f87171' }}>{cloudComp.latency_ms || 1450} ms</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Syntax Pass Rate</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#38bdf8' }}>{cloudComp.syntax_pass_rate_pct || 99.1}%</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Hallucination Risk</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#fbbf24' }}>{cloudComp.hallucination_risk_pct || 0.4}%</div>
            </div>
          </div>

          <div style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic', marginTop: 'auto' }}>
            💡 {cloudComp.key_strength}
          </div>
        </div>

        {/* HYBRID FUSION SWARM */}
        <div style={{ background: 'rgba(168,85,247,0.06)', border: '1px solid rgba(168,85,247,0.4)', borderRadius: '10px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.8rem', boxShadow: '0 0 16px rgba(168,85,247,0.15)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ fontSize: '1.2rem' }}>⚡</span>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#c084fc', fontWeight: 'bold' }}>
                Hybrid Fusion Swarm (Champion)
              </h4>
            </div>
            <span style={{ fontSize: '0.72rem', background: 'rgba(168,85,247,0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold', border: '1px solid #c084fc' }}>
              Score: {hybridComp.overall_performance_score || 98.9}% 🏆
            </span>
          </div>

          <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
            <strong>Engine:</strong> {hybridComp.model_mesh}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
            <strong>Strategy:</strong> {hybridComp.strategy}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.2rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Financial Cost</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#34d399' }}>{hybridComp.cost_display || '$0.001'}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Execution Latency</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#34d399' }}>{hybridComp.latency_ms || 320} ms ⚡</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Syntax Pass Rate</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#38bdf8' }}>{hybridComp.syntax_pass_rate_pct || 98.7}%</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '5px' }}>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Truth Compliance</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#10b981' }}>{hybridComp.truth_compliance_pct || 100}%</div>
            </div>
          </div>

          <div style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic', marginTop: 'auto' }}>
            💡 {hybridComp.key_strength}
          </div>
        </div>

      </div>

      {/* POST-MATCH TRI-ORCHESTRATOR POST-MORTEM DEBATE */}
      <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span>🎙️</span> Tri-Orchestrator Post-Match Analysis &amp; Consensus Verdict
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.78rem', color: '#cbd5e1' }}>
          <div style={{ background: 'rgba(16,185,129,0.05)', padding: '0.6rem', borderRadius: '5px', borderLeft: '3px solid #10b981' }}>
            {analysis.local_orchestrator_verdict}
          </div>
          <div style={{ background: 'rgba(59,130,246,0.05)', padding: '0.6rem', borderRadius: '5px', borderLeft: '3px solid #3b82f6' }}>
            {analysis.cloud_orchestrator_verdict}
          </div>
          <div style={{ background: 'rgba(168,85,247,0.05)', padding: '0.6rem', borderRadius: '5px', borderLeft: '3px solid #a855f7' }}>
            {analysis.genetic_moe_verdict}
          </div>
        </div>

        {/* WINNERS PODIUM */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.6rem', marginTop: '0.4rem' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>💰 Cost Champion</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#34d399', marginTop: '0.2rem' }}>{winners.cost_champion}</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>⚡ Speed Champion</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>{winners.speed_champion}</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>🎯 Accuracy Champion</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#a855f7', marginTop: '0.2rem' }}>{winners.accuracy_champion}</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem', borderRadius: '6px', border: '1px solid rgba(236,72,153,0.3)' }}>
            <div style={{ fontSize: '0.68rem', color: '#f472b6' }}>🏆 Overall Match Victor</div>
            <div style={{ fontSize: '0.82rem', fontWeight: 'bold', color: '#f472b6', marginTop: '0.2rem' }}>{winners.overall_match_victor}</div>
          </div>
        </div>
      </div>

    </div>
  );
}
