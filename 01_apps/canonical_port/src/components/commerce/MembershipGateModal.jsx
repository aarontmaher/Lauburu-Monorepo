import React, { useState } from 'react';

export function MembershipGateModal({
  isOpen,
  onClose,
  gateContext,
  membership,
  tiers,
  onSelectTierOverride,
  onCreateCheckoutCart
}) {
  const [selectedTier, setSelectedTier] = useState('athlete_pro');
  const [loading, setLoading] = useState(false);
  const [checkoutUrl, setCheckoutUrl] = useState(null);

  if (!isOpen) return null;

  const currentTier = membership?.tier_id || 'free';
  const featureName = gateContext?.featureName || 'Advanced Mesh Feature';

  const handleCheckout = async (tierId) => {
    setLoading(true);
    const cart = await onCreateCheckoutCart(tierId);
    setLoading(false);
    if (cart?.checkout_url) {
      setCheckoutUrl(cart.checkout_url);
      window.open(cart.checkout_url, '_blank');
    }
  };

  const handleOverride = async (tierId) => {
    await onSelectTierOverride(tierId);
    onClose();
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '16px'
    }}>
      <div className="cyber-card" style={{
        maxWidth: '720px',
        width: '100%',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--accent-cyan)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 0 30px rgba(0, 255, 204, 0.15)',
        padding: '24px',
        maxHeight: '90vh',
        overflowY: 'auto'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.4rem' }}>🔒</span>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                MEMBERSHIP TIER REQUIRED
              </h3>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--accent-amber)', marginTop: '4px' }}>
              Access to "{featureName}" is token-gated by Shopify Storefront Membership.
            </div>
          </div>
          <button onClick={onClose} className="cyber-btn" style={{ padding: '4px 10px', fontSize: '0.8rem' }}>
            ✕
          </button>
        </div>

        {/* Current Status Banner */}
        <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Current Active Subscription:</span>
            <span style={{ marginLeft: '8px', fontWeight: 700, color: 'var(--accent-cyan)', fontSize: '0.88rem' }}>
              {membership?.tier_name} (${membership?.price_aud_monthly} AUD/mo)
            </span>
          </div>
          <div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Net Compute Credits:</span>
            <span style={{ marginLeft: '8px', fontWeight: 700, color: 'var(--accent-emerald)', fontSize: '0.88rem' }}>
              ${membership?.net_credits_aud} AUD
            </span>
          </div>
        </div>

        {/* Tiers Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          {tiers.map((t) => {
            const isCurrent = t.tier_id === currentTier;
            return (
              <div
                key={t.tier_id}
                onClick={() => setSelectedTier(t.tier_id)}
                style={{
                  background: isCurrent ? 'rgba(0, 255, 204, 0.08)' : 'var(--bg-tertiary)',
                  border: isCurrent ? '2px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{t.name}</span>
                    <span className={`badge ${isCurrent ? 'badge-cyan' : 'badge-emerald'}`} style={{ fontSize: '0.65rem' }}>
                      {isCurrent ? 'ACTIVE' : t.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-cyan)', marginBottom: '8px' }}>
                    ${t.price_aud_monthly} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>AUD/mo</span>
                  </div>
                  <ul style={{ paddingLeft: '16px', margin: '0 0 10px 0', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {t.features.map((feat, fIdx) => (
                      <li key={fIdx} style={{ marginBottom: '3px' }}>{feat}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {!isCurrent && (
                    <button
                      className="cyber-btn"
                      style={{ fontSize: '0.75rem', width: '100%', padding: '6px' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCheckout(t.tier_id);
                      }}
                      disabled={loading}
                    >
                      🛒 Checkout via Shopify
                    </button>
                  )}
                  {/* Sovereign Testing Override */}
                  <button
                    className="cyber-btn"
                    style={{ fontSize: '0.68rem', width: '100%', padding: '4px', background: 'transparent', color: 'var(--text-muted)' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleOverride(t.tier_id);
                    }}
                  >
                    👑 Sovereign Override to Tier
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer info */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
          <div>
            Powered by Headless Shopify Storefront GraphQL & Compute Credit Offsets.
          </div>
          <button className="cyber-btn" onClick={onClose} style={{ padding: '6px 14px', fontSize: '0.78rem' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
