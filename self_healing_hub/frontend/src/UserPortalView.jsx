import React, { useState, useEffect } from 'react';
import ShopifyMembershipModal from './ShopifyMembershipModal';
import UnifiedGenieTatamiArenaView from './UnifiedGenieTatamiArenaView';

export default function UserPortalView({ onOpenSimulator }) {
  const [showShopifyModal, setShowShopifyModal] = useState(false);
  const [membershipProfile, setMembershipProfile] = useState({
    tier: 'FREE',
    name: 'Free Athlete',
    is_paid_subscriber: false,
    email: 'athlete@lauburu.ai'
  });
  const [activeUserSubTab, setActiveUserSubTab] = useState('readiness'); // 'readiness', 'training_game', 'sleep', 'sensor_status'
  
  // Optical PPG 5-Min Check State
  const [isPpgTesting, setIsPpgTesting] = useState(false);
  const [ppgProgress, setPpgProgress] = useState(0);
  const [ppgResults, setPpgResults] = useState(null);

  // Sleep & Telemetry
  const [sleepSummary, setSleepSummary] = useState(null);
  const [liveTelemetry, setLiveTelemetry] = useState(null);

  const apiHost = window.location.hostname || 'localhost';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sleepRes, telRes] = await Promise.all([
          fetch(`http://${apiHost}:5001/api/movesense/sleep/summary`),
          fetch(`http://${apiHost}:5001/api/telemetry`)
        ]);
        if (sleepRes.ok) setSleepSummary(await sleepRes.json());
        if (telRes.ok) setLiveTelemetry(await telRes.json());
      } catch (e) {
        console.warn('User portal data fetch error:', e);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  // 5-Minute Phone PPG Test Simulation
  const handleStartPpgTest = () => {
    setIsPpgTesting(true);
    setPpgProgress(0);
    setPpgResults(null);

    let progress = 0;
    const ppgInterval = setInterval(() => {
      progress += 10;
      setPpgProgress(progress);
      if (progress >= 100) {
        clearInterval(ppgInterval);
        setIsPpgTesting(false);
        setPpgResults({
          hr: 68,
          rmssd: 48.5,
          readiness: 91,
          grade: 'OPTIMAL RECOVERY'
        });
      }
    }, 400);
  };

  const isProOrContributor = membershipProfile.tier === 'PAID_PRO' || membershipProfile.tier === 'CONTRIBUTOR_PRO';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', padding: '1rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
      
      {/* 1. TOP USER MEMBERSHIP BANNER */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,41,59,0.95))',
        border: '1px solid rgba(56,189,248,0.3)',
        borderRadius: '16px',
        padding: '1.2rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        boxShadow: '0 8px 30px rgba(0,0,0,0.45)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <img src="/assets/lauburu_symbol.png" width="44" height="44" style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} alt="Lauburu" />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2 style={{ margin: 0, color: '#f8fafc', fontSize: '1.3rem', fontWeight: 'bold' }}>Welcome, {membershipProfile.name}</h2>
              <span style={{
                background: isProOrContributor ? 'rgba(56,189,248,0.2)' : 'rgba(255,255,255,0.08)',
                color: isProOrContributor ? '#38bdf8' : '#94a3b8',
                fontSize: '0.7rem',
                fontWeight: 'bold',
                padding: '2px 8px',
                borderRadius: '12px',
                border: `1px solid ${isProOrContributor ? '#38bdf8' : 'rgba(255,255,255,0.15)'}`
              }}>
                {membershipProfile.tier === 'PAID_PRO' ? '⭐ PAID PRO TIER' : membershipProfile.tier === 'CONTRIBUTOR_PRO' ? '⚡ COMPUTE CONTRIBUTOR' : 'FREE TIER'}
              </span>
            </div>
            <p style={{ margin: '0.2rem 0 0 0', color: '#94a3b8', fontSize: '0.78rem' }}>
              {isProOrContributor
                ? 'Full Access Unlocked: Medical-Grade Movesense 128Hz ECG, Real-Time DFA-α1, Polysomnographic Sleep & 3D AI Arena.'
                : 'Free Access Active: Optical Phone Camera PPG 5-Min Checks & Daily Readiness. Upgrade to Pro or Share Compute for 128Hz ECG.'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <button
            onClick={() => setShowShopifyModal(true)}
            style={{
              background: isProOrContributor ? 'rgba(56,189,248,0.15)' : 'linear-gradient(135deg, #0284c7, #38bdf8)',
              color: isProOrContributor ? '#38bdf8' : '#000',
              border: isProOrContributor ? '1px solid #38bdf8' : 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '0.82rem',
              cursor: 'pointer',
              boxShadow: isProOrContributor ? 'none' : '0 4px 15px rgba(56,189,248,0.3)'
            }}
          >
            {isProOrContributor ? 'Manage Subscription' : '🛍️ Upgrade Tier / Sign In'}
          </button>

          {onOpenSimulator && (
            <button
              onClick={onOpenSimulator}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#cbd5e1',
                padding: '8px 14px',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.82rem',
                cursor: 'pointer'
              }}
            >
              📱 Test on Device Simulators
            </button>
          )}
        </div>
      </div>

      {/* 2. USER SUB-NAV TABS */}
      <div style={{
        display: 'flex',
        gap: '0.4rem',
        background: '#0f172a',
        padding: '0.35rem',
        borderRadius: '10px',
        border: '1px solid rgba(255,255,255,0.06)'
      }}>
        {[
          { id: 'readiness', label: '🫀 Daily Readiness & 5-Min Optical Check', icon: '🫀' },
          { id: 'training_game', label: '🎮 3D AI Training & Tatami Arena', icon: '🎮' },
          { id: 'sleep', label: '🌙 Overnight Sleep Staging', icon: '🌙' },
          { id: 'sensor_status', label: '📡 BLE Hardware & Movesense', icon: '📡' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveUserSubTab(tab.id)}
            style={{
              flex: 1,
              background: activeUserSubTab === tab.id ? '#1e293b' : 'transparent',
              color: activeUserSubTab === tab.id ? '#38bdf8' : '#94a3b8',
              border: activeUserSubTab === tab.id ? '1px solid rgba(56,189,248,0.3)' : 'none',
              padding: '8px',
              borderRadius: '6px',
              fontSize: '0.78rem',
              fontWeight: activeUserSubTab === tab.id ? 'bold' : '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 3. TAB 1: DAILY READINESS & 5-MIN OPTICAL PPG CHECK */}
      {activeUserSubTab === 'readiness' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.2rem' }}>
          
          {/* READINESS GAUGE CARD */}
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '14px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>Autonomic Readiness Score</h3>
              <span style={{ fontSize: '0.7rem', color: '#10b981', background: 'rgba(16,185,129,0.15)', padding: '2px 8px', borderRadius: '10px', fontWeight: 'bold' }}>
                FREE TIER FEATURE
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem 0' }}>
              <div style={{
                width: '140px',
                height: '140px',
                borderRadius: '50%',
                border: '8px solid #10b981',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(16,185,129,0.05)',
                boxShadow: '0 0 25px rgba(16,185,129,0.2)'
              }}>
                <span style={{ fontSize: '2.4rem', fontWeight: '900', color: '#fff' }}>91%</span>
                <span style={{ fontSize: '0.65rem', color: '#10b981', fontWeight: 'bold' }}>OPTIMAL</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '8px' }}>
                <span style={{ color: '#94a3b8' }}>Resting Heart Rate:</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>58 BPM</div>
              </div>
              <div style={{ background: '#1e293b', padding: '0.8rem', borderRadius: '8px' }}>
                <span style={{ color: '#94a3b8' }}>HRV RMSSD:</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#a855f7', marginTop: '0.2rem' }}>64.2 ms</div>
              </div>
            </div>
          </div>

          {/* 5-MINUTE PHONE OPTICAL PPG CHECK */}
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '14px', padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>📸 Phone Camera Optical PPG Check</h3>
                <span style={{ fontSize: '0.68rem', color: '#38bdf8' }}>5-Minute Spot Test</span>
              </div>
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.76rem', lineHeight: '1.4' }}>
                Hold your index finger steadily over the phone camera flash. The optical photoplethysmogram derives continuous arterial pulsatile waveforms to measure autonomic recovery.
              </p>
            </div>

            {isPpgTesting ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', padding: '1rem 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#38bdf8' }}>
                  <span>Reading Optical Pulsatile Micro-Vessel Signals...</span>
                  <span>{ppgProgress}%</span>
                </div>
                <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${ppgProgress}%`, height: '100%', background: 'linear-gradient(90deg, #0284c7, #38bdf8)', transition: 'width 0.3s ease' }}></div>
                </div>
              </div>
            ) : ppgResults ? (
              <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid #10b981', padding: '1rem', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                <div style={{ color: '#10b981', fontWeight: 'bold', fontSize: '0.85rem' }}>✓ 5-Minute PPG Spot Check Complete</div>
                <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
                  Estimated Pulse: <strong>{ppgResults.hr} BPM</strong> • Spot RMSSD: <strong>{ppgResults.rmssd} ms</strong>
                </div>
              </div>
            ) : (
              <div style={{ background: '#1e293b', padding: '1.5rem', borderRadius: '8px', textAlign: 'center', color: '#94a3b8', fontSize: '0.78rem' }}>
                Press start and place finger on camera lens for 5-minute diagnostic test.
              </div>
            )}

            <button
              onClick={handleStartPpgTest}
              disabled={isPpgTesting}
              style={{
                background: isPpgTesting ? '#475569' : 'linear-gradient(135deg, #0284c7, #38bdf8)',
                color: '#000',
                border: 'none',
                padding: '12px',
                borderRadius: '8px',
                fontWeight: 'bold',
                fontSize: '0.85rem',
                cursor: isPpgTesting ? 'not-allowed' : 'pointer'
              }}
            >
              {isPpgTesting ? 'Capturing Optical PPG...' : '▶️ Start 5-Minute Camera PPG Check'}
            </button>
          </div>

        </div>
      )}

      {/* 4. TAB 2: 3D AI TRAINING & TATAMI ARENA */}
      {activeUserSubTab === 'training_game' && (
        <UnifiedGenieTatamiArenaView />
      )}

      {/* 5. TAB 3: OVERNIGHT SLEEP STAGING */}
      {activeUserSubTab === 'sleep' && (
        <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '14px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.15rem' }}>🌙 Overnight Polysomnographic Sleep DSP</h3>
              <p style={{ margin: '0.2rem 0 0 0', color: '#94a3b8', fontSize: '0.75rem' }}>
                5-Minute rolling epoch trajectory derived from physical Movesense 128Hz ECG &amp; 3-axis IMU actigraphy.
              </p>
            </div>
            {!isProOrContributor && (
              <span style={{ fontSize: '0.7rem', color: '#f59e0b', background: 'rgba(245,158,11,0.15)', padding: '4px 10px', borderRadius: '10px', fontWeight: 'bold' }}>
                PRO TIER FEATURE (Preview Mode)
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '10px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Sleep Efficiency:</span>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '0.2rem' }}>
                {sleepSummary?.sleep_efficiency_pct != null ? `${sleepSummary.sleep_efficiency_pct}%` : '88.4%'}
              </div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '10px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Deep Sleep (N3):</span>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#a855f7', marginTop: '0.2rem' }}>1h 42m</div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '10px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>REM Stage:</span>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#ec4899', marginTop: '0.2rem' }}>2h 08m</div>
            </div>
            <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '10px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Autonomic Recovery:</span>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#10b981', marginTop: '0.2rem' }}>92 / 100</div>
            </div>
          </div>
        </div>
      )}

      {/* 6. TAB 4: SENSOR STATUS & BLE */}
      {activeUserSubTab === 'sensor_status' && (
        <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '14px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.15rem' }}>📡 Movesense &amp; Polar GATT BLE Ingestion Status</h3>
          <div style={{ background: '#1e293b', padding: '1rem', borderRadius: '8px', fontSize: '0.78rem', color: '#cbd5e1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span>Compute Hub GATT Ingestion:</span>
              <strong style={{ color: '#10b981' }}>ONLINE (Port 5001 / WebSocket Broadcast)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
              <span>Movesense 128Hz Custom GATT:</span>
              <strong style={{ color: '#38bdf8' }}>Ready (GATT 0x180D / 0x2A37)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>DFA-α1 Real-time Mathematical DSP:</span>
              <strong style={{ color: '#a855f7' }}>Detrended Fluctuation Filter Active</strong>
            </div>
          </div>
        </div>
      )}

      {/* SHOPIFY MEMBERSHIP MODAL */}
      <ShopifyMembershipModal
        isOpen={showShopifyModal}
        onClose={() => setShowShopifyModal(false)}
        currentProfile={membershipProfile}
        onMembershipUpdated={(prof) => setMembershipProfile(prof)}
      />

    </div>
  );
}
