import React, { useState } from 'react';
import { INITIAL_CODING_PROFICIENCY_MATRIX } from '../../services/mockFallbackData.js';

export function CanonicalLeaderboardView({ leaderboard }) {
  const items = leaderboard || [];
  const [selectedRamTier, setSelectedRamTier] = useState('ALL');

  const filteredItems = items.filter(item => {
    if (selectedRamTier === 'ALL') return true;
    return item.ramTier === selectedRamTier;
  });

  const languages = ['Python', 'Rust', 'C++', 'Dart', 'Kotlin', 'TypeScript', 'Swift', 'Bash'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>🏆 SWARM ELO LEADERBOARD & CODING PROFICIENCY MATRIX</span>
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Continuous competitive ELO ratings, RAM-tier segmentation (16GB - 108GB Apex), and multi-language AST benchmarks.
          </p>
        </div>

        {/* RAM-Tier Filter Buttons */}
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {['ALL', '16GB Tier', '32GB Tier', '64GB Tier', '108GB Apex Mesh', 'Cloud Frontier'].map((tier) => (
            <button
              key={tier}
              onClick={() => setSelectedRamTier(tier)}
              className="cyber-btn"
              style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                background: selectedRamTier === tier ? 'var(--accent-cyan)' : 'transparent',
                color: selectedRamTier === tier ? '#000' : 'var(--text-secondary)',
                fontWeight: selectedRamTier === tier ? 700 : 400
              }}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {/* Leaderboard Table with RAM Tiers */}
      <div className="cyber-panel" style={{ padding: '18px' }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '12px', fontSize: '0.9rem' }}>
          1. CANONICAL AGI ELO RANKINGS & RAM-TIER SEGMENTATION
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '10px' }}>RANK</th>
              <th style={{ padding: '10px' }}>MODEL NAME</th>
              <th style={{ padding: '10px' }}>RAM TIER</th>
              <th style={{ padding: '10px' }}>TYPE / ARCHITECTURE</th>
              <th style={{ padding: '10px' }}>ELO RATING</th>
              <th style={{ padding: '10px' }}>WIN RATE</th>
              <th style={{ padding: '10px' }}>THROUGHPUT</th>
              <th style={{ padding: '10px' }}>AUTONOMY</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => (
              <tr key={item.rank} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '10px' }}>
                  <span className={`badge ${item.rank === 1 ? 'badge-amber' : item.rank === 2 ? 'badge-cyan' : item.rank === 3 ? 'badge-purple' : 'badge-emerald'}`}>
                    #{item.rank}
                  </span>
                </td>
                <td style={{ padding: '10px', color: 'var(--text-primary)', fontWeight: 600 }}>{item.name}</td>
                <td style={{ padding: '10px' }}>
                  <span className="badge badge-purple">{item.ramTier || '108GB Apex'}</span>
                </td>
                <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{item.type}</td>
                <td style={{ padding: '10px', color: 'var(--accent-purple)', fontWeight: 700 }}>{item.elo}</td>
                <td style={{ padding: '10px', color: 'var(--accent-emerald)' }}>{item.winRate}</td>
                <td style={{ padding: '10px', color: 'var(--accent-cyan)' }}>{item.tokensPerSec} tok/s</td>
                <td style={{ padding: '10px' }}>
                  <span className={`badge ${item.freedomOfChoiceUnlocked ? 'badge-emerald' : 'badge-amber'}`}>
                    {item.freedomOfChoiceUnlocked ? '● UNLOCKED' : '○ RESTRICTED'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Coding Language Proficiency Matrix Table (F21) */}
      <div className="cyber-panel" style={{ padding: '18px' }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '12px', fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>2. PER-MODEL CODING LANGUAGE PROFICIENCY MATRIX (0-100 BENCHMARK SCORES)</span>
          <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>F21 PROFICIENCY</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '10px' }}>MODEL NAME</th>
                {languages.map((lang) => (
                  <th key={lang} style={{ padding: '10px', textAlign: 'center' }}>{lang}</th>
                ))}
                <th style={{ padding: '10px', textAlign: 'center', color: 'var(--accent-cyan)' }}>COMPOSITE</th>
              </tr>
            </thead>
            <tbody>
              {items.map((m) => {
                const scores = m.codingProficiency || { Python: 90, Rust: 85, 'C++': 85, Dart: 80, Kotlin: 80, TypeScript: 88, Swift: 85, Bash: 90 };
                const values = languages.map(l => scores[l] || 85);
                const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);

                return (
                  <tr key={`prof-${m.name}`} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', color: 'var(--text-primary)', fontWeight: 600 }}>{m.name}</td>
                    {languages.map((lang) => {
                      const score = scores[lang] || 85;
                      const scoreColor = score >= 95 ? 'var(--accent-emerald)' : score >= 90 ? 'var(--accent-cyan)' : 'var(--accent-amber)';
                      return (
                        <td key={lang} style={{ padding: '10px', textAlign: 'center', color: scoreColor, fontWeight: 600 }}>
                          {score}
                        </td>
                      );
                    })}
                    <td style={{ padding: '10px', textAlign: 'center', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                      {avg}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default CanonicalLeaderboardView;

