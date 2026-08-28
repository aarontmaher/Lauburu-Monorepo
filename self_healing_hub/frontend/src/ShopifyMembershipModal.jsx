import React, { useState } from 'react';

export default function ShopifyMembershipModal({ isOpen, onClose, currentProfile, onMembershipUpdated }) {
  const [activeTab, setActiveTab] = useState('tiers'); // 'tiers', 'login', 'crowdsource'
  const [email, setEmail] = useState('');
  const [tokenInput, setTokenInput] = useState('');
  const [selectedTier, setSelectedTier] = useState('PAID_PRO');
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  if (!isOpen) return null;

  const apiHost = window.location.hostname || 'localhost';

  const handleValidateMembership = async (tier = selectedTier, token = tokenInput) => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await fetch(`http://${apiHost}:5001/api/shopify/validate_membership`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customerAccessToken: token || (tier === 'PAID_PRO' ? 'tok_pro_member' : tier === 'CROWDSOURCED' ? 'tok_crowdsource_member' : 'tok_free_member'),
          selectedTier: tier,
          email: email || undefined
        })
      });
      if (res.ok) {
        const data = await res.json();
        setFeedback({ success: true, message: `✅ Membership Updated: ${data.profile?.tier || tier} Tier Active!` });
        if (onMembershipUpdated) onMembershipUpdated(data.profile);
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        setFeedback({ success: false, message: '❌ Validation failed. Please check credentials.' });
      }
    } catch (err) {
      setFeedback({ success: false, message: `Validation Error: ${err.message}` });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 99999,
      padding: '1rem'
    }}>
      <div style={{
        background: '#0f172a',
        border: '1px solid #38bdf8',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '820px',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '1.5rem',
        boxShadow: '0 10px 40px rgba(56,189,248,0.3)',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.8rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <img src="/assets/lauburu_symbol.png" width="32" height="32" style={{ borderRadius: '6px' }} alt="Lauburu" />
            <div>
              <h2 style={{ margin: 0, color: '#f8fafc', fontSize: '1.25rem', fontWeight: 'bold' }}>
                🛍️ Shopify Membership &amp; Subscription Access
              </h2>
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.75rem' }}>
                Choose your membership tier or sign in with your Shopify Customer Account
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer', padding: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div style={{
            background: feedback.success ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
            border: `1px solid ${feedback.success ? '#10b981' : '#ef4444'}`,
            color: feedback.success ? '#34d399' : '#f87171',
            padding: '0.6rem 1rem',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: '600'
          }}>
            {feedback.message}
          </div>
        )}

        {/* Sub-Tabs */}
        <div style={{ display: 'flex', gap: '0.4rem', background: '#1e293b', padding: '0.3rem', borderRadius: '8px' }}>
          {[
            { id: 'tiers', label: '⭐ Membership Tiers (3 Options)' },
            { id: 'login', label: '🔑 Shopify Customer Login / Token' },
            { id: 'crowdsource', label: '⚡ Crowdsourced Compute Staking' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                background: activeTab === tab.id ? '#38bdf8' : 'transparent',
                color: activeTab === tab.id ? '#000' : '#cbd5e1',
                border: 'none',
                padding: '8px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: 'bold',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* TAB 1: 3 MEMBERSHIP TIERS */}
        {activeTab === 'tiers' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1rem' }}>
            
            {/* TIER 1: FREE */}
            <div style={{
              background: '#1e293b',
              border: selectedTier === 'FREE' ? '2px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
              borderRadius: '12px',
              padding: '1.2rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '1rem'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ background: 'rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: '0.68rem', padding: '2px 8px', borderRadius: '12px', fontWeight: 'bold' }}>BASIC</span>
                  <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff' }}>$0</span>
                </div>
                <h3 style={{ color: '#fff', fontSize: '1.05rem', margin: '0.6rem 0 0.3rem 0' }}>Free Tier</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.72rem', margin: 0 }}>Instant daily readiness check &amp; phone camera PPG testing.</p>

                <ul style={{ listStyle: 'none', padding: 0, margin: '1rem 0 0 0', fontSize: '0.74rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <li>✓ Daily Autonomic Readiness Score</li>
                  <li>✓ Phone Camera Optical PPG (5-Min Checks)</li>
                  <li>✓ Basic Workout &amp; Round History</li>
                  <li style={{ color: '#64748b' }}>✗ Medical-grade 128Hz Movesense ECG</li>
                  <li style={{ color: '#64748b' }}>✗ Real-time DFA-α1 &amp; Kinematics</li>
                </ul>
              </div>

              <button
                onClick={() => {
                  setSelectedTier('FREE');
                  handleValidateMembership('FREE', 'tok_free_member');
                }}
                disabled={isLoading}
                style={{
                  background: currentProfile?.tier === 'FREE' ? '#334155' : 'rgba(255,255,255,0.1)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,0.2)',
                  padding: '10px',
                  borderRadius: '8px',
                  fontWeight: 'bold',
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                {currentProfile?.tier === 'FREE' ? 'Current Tier' : 'Select Free Tier'}
              </button>
            </div>

            {/* TIER 2: PAID / PRO */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(56,189,248,0.1), #1e293b)',
              border: selectedTier === 'PAID_PRO' ? '2px solid #38bdf8' : '1px solid rgba(56,189,248,0.4)',
              borderRadius: '12px',
              padding: '1.2rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '1rem',
              position: 'relative'
            }}>
              <div style={{ position: 'absolute', top: '-10px', right: '14px', background: '#38bdf8', color: '#000', fontSize: '0.62rem', fontWeight: '900', padding: '2px 8px', borderRadius: '10px' }}>
                POPULAR
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ background: 'rgba(56,189,248,0.2)', color: '#38bdf8', fontSize: '0.68rem', padding: '2px 8px', borderRadius: '12px', fontWeight: 'bold' }}>PRO ATHLETE</span>
                  <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#38bdf8' }}>$19<span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>/mo</span></span>
                </div>
                <h3 style={{ color: '#fff', fontSize: '1.05rem', margin: '0.6rem 0 0.3rem 0' }}>Paid Pro Tier</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.72rem', margin: 0 }}>Full medical-grade Movesense ECG &amp; 3D AI coaching.</p>

                <ul style={{ listStyle: 'none', padding: 0, margin: '1rem 0 0 0', fontSize: '0.74rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <li>✓ <strong>All Free Tier Features</strong></li>
                  <li>✓ Medical-grade 128Hz Movesense ECG &amp; IMU</li>
                  <li>✓ Real-Time DFA-α1 Dynamic Fatigue Staging</li>
                  <li>✓ Polysomnographic Overnight Sleep DSP</li>
                  <li>✓ Vision-Inertial 3D Grappling Kinematics</li>
                  <li>✓ 24/7 LoRA Live Coaching Synthesis</li>
                </ul>
              </div>

              <button
                onClick={() => {
                  setSelectedTier('PAID_PRO');
                  handleValidateMembership('PAID_PRO', 'tok_pro_member');
                }}
                disabled={isLoading}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                  color: '#000',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '8px',
                  fontWeight: 'bold',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(56,189,248,0.4)'
                }}
              >
                {currentProfile?.tier === 'PAID_PRO' ? '✓ Active Pro Member' : 'Subscribe via Shopify ($19)'}
              </button>
            </div>

            {/* TIER 3: CROWDSOURCED COMPUTING */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(168,85,247,0.1), #1e293b)',
              border: selectedTier === 'CROWDSOURCED' ? '2px solid #a855f7' : '1px solid rgba(168,85,247,0.3)',
              borderRadius: '12px',
              padding: '1.2rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '1rem'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ background: 'rgba(168,85,247,0.2)', color: '#c084fc', fontSize: '0.68rem', padding: '2px 8px', borderRadius: '12px', fontWeight: 'bold' }}>ZERO-DOLLAR</span>
                  <span style={{ fontSize: '1.05rem', fontWeight: '900', color: '#c084fc' }}>Share Compute</span>
                </div>
                <h3 style={{ color: '#fff', fontSize: '1.05rem', margin: '0.6rem 0 0.3rem 0' }}>Crowdsourced</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.72rem', margin: 0 }}>Stake unused RAM/NPU to earn 100% Pro Tier for free.</p>

                <ul style={{ listStyle: 'none', padding: 0, margin: '1rem 0 0 0', fontSize: '0.74rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <li>✓ <strong>100% FREE Pro Tier Access</strong></li>
                  <li>✓ Contributes idle device RAM/NPU to mesh</li>
                  <li>✓ Earns continuous LCT staking tokens</li>
                  <li>✓ Full Movesense 128Hz ECG &amp; 3D Tatami Arena</li>
                  <li>✓ $0 Recurring Spend Forever</li>
                </ul>
              </div>

              <button
                onClick={() => {
                  setSelectedTier('CROWDSOURCED');
                  handleValidateMembership('CROWDSOURCED', 'tok_crowdsource_member');
                }}
                disabled={isLoading}
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
                  color: '#fff',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '8px',
                  fontWeight: 'bold',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(168,85,247,0.4)'
                }}
              >
                {currentProfile?.tier === 'CONTRIBUTOR_PRO' ? '✓ Compute Staking Active' : 'Join as Compute Contributor'}
              </button>
            </div>

          </div>
        )}

        {/* TAB 2: SHOPIFY CUSTOMER LOGIN / ACCESS TOKEN */}
        {activeTab === 'login' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <h3 style={{ margin: 0, color: '#38bdf8', fontSize: '1rem' }}>Shopify Storefront Customer Account Login</h3>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.75rem' }}>
              Enter your customer email or paste your Shopify Storefront Customer Access Token to unlock your active store subscription.
            </p>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Customer Email:</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="athlete@lauburu.ai"
                style={{ width: '100%', background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.82rem' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.3rem' }}>Shopify Customer Access Token (Optional):</label>
              <input
                type="text"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="shpat_xxxx or tok_pro_member"
                style={{ width: '100%', background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.82rem' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.4rem' }}>
              <button
                onClick={() => handleValidateMembership('PAID_PRO', tokenInput || 'tok_pro_member')}
                disabled={isLoading}
                style={{ flex: 1, background: '#38bdf8', color: '#000', border: 'none', padding: '10px', borderRadius: '8px', fontWeight: 'bold', fontSize: '0.85rem', cursor: 'pointer' }}
              >
                {isLoading ? 'Verifying with Shopify...' : 'Verify Customer Token'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: CROWDSOURCED STAKING INSTRUCTIONS */}
        {activeTab === 'crowdsource' && (
          <div style={{ background: '#1e293b', borderRadius: '12px', padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <h3 style={{ margin: 0, color: '#a855f7', fontSize: '1rem' }}>⚡ Contribute Local Compute &amp; Unlock Free Lifetime Pro</h3>
            <p style={{ margin: 0, color: '#cbd5e1', fontSize: '0.75rem', lineHeight: '1.4' }}>
              By sharing a portion of your local device RAM/NPU (e.g. running `ggml-rpc-server` on Android Termux or Mac Host), you participate in the 82.8 GB distributed mesh. The cluster grants you full unrestricted access to all Paid Pro analytics with $0 subscription cost.
            </p>

            <div style={{ background: '#0f172a', padding: '0.8rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.72rem', color: '#94a3b8' }}>
              <strong>Active Mesh Contributor Nodes:</strong> Pixel 10 Pro XL (11.4 GB Cap), Samsung S20+ (8.0 GB Cap), MacBook Pro (12.0 GB Cap).
            </div>

            <button
              onClick={() => handleValidateMembership('CROWDSOURCED', 'tok_crowdsource_member')}
              disabled={isLoading}
              style={{ background: 'linear-gradient(135deg, #7c3aed, #a855f7)', color: '#fff', border: 'none', padding: '10px', borderRadius: '8px', fontWeight: 'bold', fontSize: '0.85rem', cursor: 'pointer' }}
            >
              Activate Compute Contributor Pass
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
