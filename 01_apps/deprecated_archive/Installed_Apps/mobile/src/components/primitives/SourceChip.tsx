import { StatusPill } from './StatusPill';
import { mapTruthLabelToTone, type TruthLabel } from './_helpers';

/**
 * SourceChip — strict wrapper around StatusPill that ONLY accepts
 * the canonical six truth labels from
 * `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` § 3 plus the two
 * UI-only states ('missing', 'stale'). The label is rendered
 * verbatim so coders MUST pass the exact string.
 */
export interface SourceChipProps {
  state: TruthLabel;
}

export function SourceChip({ state }: SourceChipProps) {
  return <StatusPill label={state} tone={mapTruthLabelToTone(state)} dot={state === 'live'} />;
}
