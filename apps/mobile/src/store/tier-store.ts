/**
 * Subscription tier store and feature gating.
 *
 * Current implementation: local tier assignment only.
 * Future: Stripe/App Store subscription status determines tier.
 *
 * Default tier: 'free' — all zero-cost features work immediately.
 * During development/testing: can be overridden to any tier.
 *
 * Persistence: backed by `secureStorage` so a dev override set on
 * one launch survives app kill (otherwise iterating on gated UI
 * means re-setting the override every cold start). Real tier is
 * also persisted so gated UI stays stable until the next billing
 * webhook refresh — prevents a flash of free-tier content on cold
 * start for paying users.
 */
import { create } from 'zustand';
import { tierHasCapability, getTierCapabilities } from '@lauburu/shared';
import type { Tier, Capability } from '@lauburu/shared';
import { readStoredJson, writeStoredJson, removeStoredJson } from './secure-storage';

const STORAGE_KEY = 'tier_state_v1';

const VALID_TIERS: readonly Tier[] = ['free', 'low_cost', 'pro', 'ai_premium'];

function isTier(value: unknown): value is Tier {
  return typeof value === 'string' && (VALID_TIERS as readonly string[]).includes(value);
}

interface PersistedTierBlob {
  tier: Tier;
  devOverride: Tier | null;
}

async function persistSafely(blob: PersistedTierBlob): Promise<void> {
  if (blob.tier === 'free' && blob.devOverride == null) {
    await removeStoredJson(STORAGE_KEY);
    return;
  }
  await writeStoredJson(STORAGE_KEY, blob);
}

function sanitizeBlob(value: unknown): PersistedTierBlob | null {
  if (!value || typeof value !== 'object') return null;
  const parsed = value as Partial<PersistedTierBlob>;
  const tier: Tier = isTier(parsed.tier) ? parsed.tier : 'free';
  const devOverride: Tier | null = isTier(parsed.devOverride)
    ? parsed.devOverride
    : null;
  return { tier, devOverride };
}

interface TierState {
  /** Current subscription tier */
  tier: Tier;

  /** Override for development/testing (null = use real tier) */
  devOverride: Tier | null;

  /** Whether persisted tier state has been loaded */
  hydrated: boolean;

  /** Hydrate tier + dev override from secureStorage */
  hydrate: () => Promise<void>;

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
  hydrated: false,

  hydrate: async () => {
    const parsed = await readStoredJson<unknown>(STORAGE_KEY);
    const next = sanitizeBlob(parsed);
    if (!next) {
      set({ hydrated: true });
      return;
    }
    set({
      tier: next.tier,
      devOverride: next.devOverride,
      hydrated: true,
    });
  },

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

  setTier: (tier) => {
    set((s) => {
      void persistSafely({ tier, devOverride: s.devOverride });
      return { tier };
    });
  },

  setDevOverride: (devOverride) => {
    set((s) => {
      void persistSafely({ tier: s.tier, devOverride });
      return { devOverride };
    });
  },
}));
