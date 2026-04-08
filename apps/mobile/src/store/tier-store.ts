/**
 * Subscription tier store and feature gating.
 *
 * Current implementation: local tier assignment only.
 * Future: Stripe/App Store subscription status determines tier.
 *
 * Default tier: 'free' — all zero-cost features work immediately.
 * During development/testing: can be overridden to any tier.
 */
import { create } from 'zustand';
import { tierHasCapability, getTierCapabilities } from '@lauburu/shared';
import type { Tier, Capability } from '@lauburu/shared';

interface TierState {
  /** Current subscription tier */
  tier: Tier;

  /** Override for development/testing (null = use real tier) */
  devOverride: Tier | null;

  /** Get the effective tier (respects dev override) */
  effectiveTier: () => Tier;

  /** Check if a capability is enabled */
  can: (cap: Capability) => boolean;

  /** Get all enabled capabilities */
  capabilities: () => Capability[];

  /** Set tier (from billing webhook or manual) */
  setTier: (tier: Tier) => void;

  /** Set dev override (for testing) */
  setDevOverride: (tier: Tier | null) => void;
}

export const useTierStore = create<TierState>((set, get) => ({
  tier: 'free',
  devOverride: null,

  effectiveTier: () => {
    const { devOverride, tier } = get();
    return devOverride ?? tier;
  },

  can: (cap) => {
    return tierHasCapability(get().effectiveTier(), cap);
  },

  capabilities: () => {
    return getTierCapabilities(get().effectiveTier());
  },

  setTier: (tier) => set({ tier }),

  setDevOverride: (tier) => set({ devOverride: tier }),
}));
