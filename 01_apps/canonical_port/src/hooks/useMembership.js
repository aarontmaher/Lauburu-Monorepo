import { useState, useEffect, useCallback } from 'react';

export function useMembership() {
  const [membershipState, setMembershipState] = useState({
    customer_id: 'cust_aaron_sovereign_01',
    email: 'aaron@lauburu.ai',
    name: 'Aaron Maher',
    tier_id: 'mesh_gym_master',
    tier_name: '👑 Sovereign Mesh Gym Master',
    tier_badge: 'GYM MASTER',
    price_aud_monthly: 99.0,
    net_credits_aud: 1.37,
    net_monthly_due_aud: 97.63,
    features_unlocked: [],
    allowed_modules: [
      'chat_basic', 'public_telemetry', 'movesense_512hz', 'zone2_cardio',
      'grappling_3d', 'ptt_blood_pressure', 'dfa_alpha1', 'obsidian_rag',
      'full_ide_compiler', 'lora_distillation', 'mesh_sharding_82gb', 'cloud_burst'
    ],
    is_sovereign_override: false,
    storefront_domain: 'lauburu-grappling.myshopify.com'
  });

  const [tiers, setTiers] = useState([]);
  const [isGateModalOpen, setIsGateModalOpen] = useState(false);
  const [gateContext, setGateContext] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/commerce/membership/status');
      if (res.ok) {
        const data = await res.json();
        setMembershipState(data);
      }
    } catch (e) {
      console.warn('[useMembership] Using fallback membership state');
    }
  }, []);

  const fetchTiers = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/commerce/membership/tiers');
      if (res.ok) {
        const data = await res.json();
        if (data.tiers) setTiers(data.tiers);
      }
    } catch (e) {
      console.warn('[useMembership] Using fallback tiers');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchTiers();
  }, [fetchStatus, fetchTiers]);

  const hasPermission = useCallback((featureKey) => {
    if (!membershipState || !membershipState.allowed_modules) return true;
    return membershipState.allowed_modules.includes(featureKey);
  }, [membershipState]);

  const triggerGate = useCallback((featureKey, featureName, requiredTier = 'athlete_starter') => {
    setGateContext({ featureKey, featureName, requiredTier });
    setIsGateModalOpen(true);
  }, []);

  const setTierOverride = useCallback(async (newTierId) => {
    try {
      const res = await fetch('/api/v1/commerce/membership/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier_id: newTierId })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status) {
          setMembershipState(data.status);
          return data.status;
        }
      }
    } catch (e) {
      console.error('[useMembership] Error setting tier override:', e);
    }
    return null;
  }, []);

  const createCheckoutCart = useCallback(async (targetTierId) => {
    try {
      const res = await fetch('/api/v1/commerce/membership/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier_id: targetTierId })
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error('[useMembership] Error creating checkout cart:', e);
    }
    return {
      checkout_url: `https://lauburu-grappling.myshopify.com/cart/c/cart_${Date.now()}_${targetTierId}`
    };
  }, []);

  return {
    membership: membershipState,
    tiers,
    hasPermission,
    triggerGate,
    isGateModalOpen,
    setIsGateModalOpen,
    gateContext,
    setTierOverride,
    createCheckoutCart,
    refreshStatus: fetchStatus
  };
}
