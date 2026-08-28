import React, { useState, useEffect } from 'react';

export default function GrapplingVisionBiometricsView() {
  const [hardwareStatus, setHardwareStatus] = useState(null);
  const [fusionData, setFusionData] = useState(null);
  const [isLiveActive, setIsLiveActive] = useState(true);
  const [activeTab, setActiveTab] = useState('radar'); // 'radar', 'hardware', 'shopify'
  const [shopifyEmail, setShopifyEmail] = useState('');
  const [membershipStatus, setMembershipStatus] = useState(null);
  const [isCheckingMembership, setIsCheckingMembership] = useState(false);

  const apiHost = window.location.hostname || 'localhost';

  useEffect(() => {
    let interval = null;
    const fetchTelemetry = async () => {
      try {
        const [hwRes, fusionRes] = await Promise.all([
          fetch(`http://${apiHost}:5001/api/hardware/npu_vram_status`),
          fetch(`http://${apiHost}:5001/api/grappling/fusion_stream`)
        ]);
        if (hwRes.ok) setHardwareStatus(await hwRes.json());
        if (fusionRes.ok) setFusionData(await fusionRes.json());
      } catch (err) {
        console.error('Error fetching NPU/Vision telemetry:', err);
      }
    };

    fetchTelemetry();
    if (isLiveActive) {
      interval = setInterval(fetchTelemetry, 2500);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [isLiveActive, apiHost]);

  const handleVerifyShopify = async (e) => {
    e.preventDefault();
    setIsCheckingMembership(true);
    try {
      const res = await fetch(`http://${apiHost}:5001/api/shopify/validate_membership`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customerAccessToken: 'sample_token_or_email' })
      });
      const data = await res.json();
      setMembershipStatus(data);
    } catch (err) {
      setMembershipStatus({ is_active_subscriber: false, error: err.message });
    } finally {
      setIsCheckingMembership(false);
    }
  };

  const armbarRisk = fusionData?.safety_radar?.armbar_hyperextension_risk || 'SAFE';
  const kimuraRisk = fusionData?.safety_radar?.kimura_rotational_risk || 'SAFE';
  const isOccluded = fusionData?.occlusion_state?.includes('OCCLUDED');

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '1.2rem',
      padding: '1.2rem',
      background: '#090d16',
      minHeight: '85vh',
      color: '#f8fafc',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* HEADER WITH NPU POWER STATUS */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(15,23,42,0.95))',
        border: '1px solid rgba(16,185,129,0.35)',
        borderRadius: '12px',
        padding: '1rem 1.4rem',
        boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
        flexWrap: 'wrap',
        gap: '0.8rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <div style={{ fontSize: '2rem' }}>🥋</div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>Vision-Inertial Grappling Analytics</span>
              <span style={{ fontSize: '0.72rem', background: '#10b981', color: '#000', padding: '2px 8px', borderRadius: '6px', fontWeight: 'bold' }}>
                ⚡ NPU-FIRST (1.2W)
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
              Google MediaPipe 3D Pose + Movesense 128Hz IMU/ECG Extended Kalman Filter
            </div>
          </div>
        </div>

        {/* Live Power & Hierarchy Indicators */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{
            background: 'rgba(15,23,42,0.8)',
            border: '1px solid rgba(255,255,255,0.1)',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            textAlign: 'right'
          }}>
            <div style={{ color: '#94a3b8' }}>Active Execution Priority</div>
            <div style={{ color: '#38bdf8', fontWeight: 'bold' }}>1. NPU ➔ 2. VRAM ➔ 3. CPU</div>
          </div>
          <button
            onClick={() => setIsLiveActive(!isLiveActive)}
            style={{
              background: isLiveActive ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)',
              border: `1px solid ${isLiveActive ? '#ef4444' : '#10b981'}`,
              color: isLiveActive ? '#fca5a5' : '#86efac',
              padding: '8px 14px',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '0.78rem',
              cursor: 'pointer'
            }}
          >
            {isLiveActive ? '● Live Stream Active' : '▶️ Resume Stream'}
          </button>
        </div>
      </div>

      {/* TOP NAVIGATION TABS */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
        {[
          { id: 'radar', label: '🥋 Live Joint Radar & Kinematics', icon: '📐' },
          { id: 'hardware', label: '🧠 NPU Silicon & VRAM Mesh (60 TOPS)', icon: '⚡' },
          { id: 'shopify', label: '🛍️ Shopify Subscriptions & Proof of Compute', icon: '💎' }
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              background: activeTab === t.id ? 'rgba(56,189,248,0.15)' : 'transparent',
              border: activeTab === t.id ? '1px solid #38bdf8' : '1px solid transparent',
              color: activeTab === t.id ? '#38bdf8' : '#94a3b8',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              fontWeight: activeTab === t.id ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem'
            }}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* TAB 1: LIVE JOINT RADAR & SENSOR FUSION */}
      {activeTab === 'radar' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {/* Card 1: 3D Joint Safety Angles */}
          <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#38bdf8', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>📐</span>
              <span>Optical-Inertial Joint Angles</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span>Elbow Extension (Armbar Risk)</span>
                  <span style={{ color: armbarRisk.includes('CRITICAL') ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>
                    {fusionData?.joint_angles?.elbow_extension_deg || 0}° ({armbarRisk})
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: '#1f2937', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, ((fusionData?.joint_angles?.elbow_extension_deg || 0) / 180) * 100)}%`,
                    height: '100%',
                    background: armbarRisk.includes('CRITICAL') ? '#ef4444' : (armbarRisk.includes('ELEVATED') ? '#f59e0b' : '#10b981'),
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span>Shoulder Torsion (Kimura / Americana)</span>
                  <span style={{ color: kimuraRisk.includes('CRITICAL') ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>
                    {fusionData?.joint_angles?.shoulder_rotation_deg || 0}° ({kimuraRisk})
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: '#1f2937', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, ((fusionData?.joint_angles?.shoulder_rotation_deg || 0) / 90) * 100)}%`,
                    height: '100%',
                    background: kimuraRisk.includes('CRITICAL') ? '#ef4444' : '#10b981',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span>Knee Flexion (Guard Retention Frame)</span>
                  <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>
                    {fusionData?.joint_angles?.knee_flexion_deg || 0}°
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: '#1f2937', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, ((fusionData?.joint_angles?.knee_flexion_deg || 0) / 180) * 100)}%`,
                    height: '100%',
                    background: '#38bdf8',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
            </div>

            {/* Occlusion Alert */}
            <div style={{
              marginTop: '1rem',
              padding: '8px 10px',
              borderRadius: '6px',
              background: isOccluded ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.12)',
              border: `1px solid ${isOccluded ? '#f59e0b' : '#10b981'}`,
              fontSize: '0.74rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}>
              <span>{isOccluded ? '⚠️' : '👁️'}</span>
              <span>
                {isOccluded
                  ? 'Optical Occlusion Detected: EKF Dead-Reckoning Active via Movesense IMU'
                  : 'Optical Line of Sight Clear: 33 3D Keypoints Tracking at 60 FPS'}
              </span>
            </div>
          </div>

          {/* Card 2: Movesense Physical Biometrics */}
          <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#f43f5e', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>💓</span>
              <span>Movesense 128Hz Physical Telemetry</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Live Heart Rate</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#f43f5e' }}>
                  {fusionData?.movesense_biometrics?.heart_rate_bpm || '--'} <span style={{ fontSize: '0.8rem' }}>BPM</span>
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Peak Scramble G-Force</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#38bdf8' }}>
                  {fusionData?.movesense_biometrics?.linear_g_force || '--'} <span style={{ fontSize: '0.8rem' }}>g</span>
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>DFA-α1 (Fatigue State)</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#10b981' }}>
                  {fusionData?.movesense_biometrics?.dfa_alpha1 || '--'}
                </div>
                <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{fusionData?.movesense_biometrics?.fatigue_state}</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.35)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Tactical Position</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#c084fc', marginTop: '4px' }}>
                  {fusionData?.tactical_position || 'Standing Neutral'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: NPU SILICON & VRAM MESH */}
      {activeTab === 'hardware' && (
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1.2rem' }}>
          <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#10b981', marginBottom: '0.8rem' }}>
            ⚡ 60 TOPS NPU-First Compute Architecture
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div style={{ fontSize: '0.75rem', color: '#86efac', fontWeight: 'bold' }}>Priority 1: Dedicated NPU (1.2W)</div>
              <div style={{ fontSize: '0.88rem', color: '#f8fafc', marginTop: '4px' }}>
                {hardwareStatus?.hardware_profile?.host_node?.npu_name}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                Framework: {hardwareStatus?.hardware_profile?.host_node?.npu_framework} (38 TOPS ANE + 22 TOPS Pixel TPU)
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)' }}>
              <div style={{ fontSize: '0.75rem', color: '#7dd3fc', fontWeight: 'bold' }}>Priority 2: Unified AI VRAM Pool</div>
              <div style={{ fontSize: '0.88rem', color: '#f8fafc', marginTop: '4px' }}>
                {hardwareStatus?.hardware_profile?.total_mesh_vram_gb} GB Pooled VRAM (10Gbps TB4 Bridge)
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                Active when on AC Wall Power for 70B parameter model sharding.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SHOPIFY SUBSCRIPTIONS & PROOF OF COMPUTE */}
      {activeTab === 'shopify' && (
        <div style={{ background: '#111827', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '1.2rem' }}>
          <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#38bdf8', marginBottom: '0.8rem' }}>
            🛍️ Shopify Storefront Subscriptions (lauburugrappling.myshopify.com)
          </div>
          <form onSubmit={handleVerifyShopify} style={{ display: 'flex', gap: '0.6rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <input
              type="email"
              placeholder="Enter Shopify Customer Email"
              value={shopifyEmail}
              onChange={(e) => setShopifyEmail(e.target.value)}
              style={{
                background: '#1f2937',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: '6px',
                flex: '1',
                minWidth: '240px'
              }}
            />
            <button
              type="submit"
              disabled={isCheckingMembership}
              style={{
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                border: 'none',
                color: '#000',
                fontWeight: 'bold',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              {isCheckingMembership ? 'Verifying...' : 'Validate Membership'}
            </button>
          </form>

          {membershipStatus && (
            <div style={{
              background: membershipStatus.is_active_subscriber ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
              border: `1px solid ${membershipStatus.is_active_subscriber ? '#10b981' : '#ef4444'}`,
              padding: '12px',
              borderRadius: '8px',
              fontSize: '0.8rem'
            }}>
              <div style={{ fontWeight: 'bold', color: membershipStatus.is_active_subscriber ? '#86efac' : '#fca5a5' }}>
                {membershipStatus.is_active_subscriber ? '✅ Pro Athlete Subscription ACTIVE (Shopify Verified)' : '⚠️ Free Tier / No Active Subscription Found'}
              </div>
              <div style={{ color: '#94a3b8', marginTop: '4px' }}>
                Unlocked Features: {(membershipStatus.unlocked_features || []).join(', ')}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
