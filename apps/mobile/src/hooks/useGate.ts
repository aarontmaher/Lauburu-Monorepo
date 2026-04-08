/**
 * Feature gating hook and helpers.
 *
 * Usage:
 *   const { allowed, tierRequired } = useGate('backend_persistence');
 *   if (!allowed) return <UpgradePrompt capability="backend_persistence" />;
 */
import { useTierStore } from '../store/tier-store';
import { minimumTierFor, TIER_INFO, CAPABILITY_INFO } from '@lauburu/shared';
import type { Capability } from '@lauburu/shared';

export function useGate(capability: Capability) {
  const can = useTierStore((s) => s.can);
  const effectiveTier = useTierStore((s) => s.effectiveTier);

  const allowed = can(capability);
  const tierRequired = minimumTierFor(capability);
  const tierInfo = TIER_INFO[tierRequired];
  const capInfo = CAPABILITY_INFO[capability];

  return {
    allowed,
    tierRequired,
    tierLabel: tierInfo.label,
    tierColor: tierInfo.color,
    capLabel: capInfo.label,
    capDescription: capInfo.description,
    currentTier: effectiveTier(),
  };
}
