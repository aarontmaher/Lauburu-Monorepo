/**
 * Pure mapper from the legacy `SourceSheetRow` status strings to
 * the canonical eight `TruthLabel` values consumed by `SourceChip`.
 *
 * Anti-rule: this module MUST NOT invent new phrasings. The chip
 * only renders one of the eight TruthLabel strings; richer per-row
 * detail belongs in the meta line beneath the chip (already
 * rendered separately in `SourceSheetRow`).
 *
 * Mapping rationale (preserves semantics per
 * `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` § 3):
 *
 * - Apple Health / Health Connect:
 *   - 'Connected' → 'live' (active OS handoff, fresh data).
 *   - 'Connected — no data' → 'seed/provisional' (handoff exists
 *     but no records to confirm — chip must not over-claim).
 *   - 'Sync failed — retry' → 'stale' (last successful read is
 *     by definition out of date).
 *   - 'Permission needed' → 'setup required'.
 *   - 'Sync needed' → 'setup required'.
 *
 * - WHOOP Direct:
 *   - 'Connected' → 'live'.
 *   - 'Awaiting cycle' → 'live' (WHOOP scores overnight; this is
 *     normal connected behaviour, not provisional data).
 *   - 'Partial' → 'seed/provisional' (some domains missing).
 *   - 'Reconnect required' → 'setup required' (auth expired).
 *   - 'Setup required' → 'setup required'.
 *   - 'Not connected' → 'missing'.
 *   - 'Stale' → 'stale'.
 *   - 'Unknown' → 'missing'.
 */

import type { TruthLabel } from './_helpers';

export const SOURCE_SHEET_STATUS_TO_TRUTH_LABEL: Record<string, TruthLabel> = {
  // Apple Health / Health Connect
  'Connected': 'live',
  'Connected — no data': 'seed/provisional',
  'Sync failed — retry': 'stale',
  'Permission needed': 'setup required',
  'Sync needed': 'setup required',
  // WHOOP Direct
  'Awaiting cycle': 'live',
  'Partial': 'seed/provisional',
  'Reconnect required': 'setup required',
  'Setup required': 'setup required',
  'Not connected': 'missing',
  'Stale': 'stale',
  'Unknown': 'missing',
};

/**
 * Map a legacy SourceSheetRow status string to a canonical
 * TruthLabel. Unknown strings fall back to `'missing'` rather
 * than `'live'` so the chip never over-claims connectivity.
 */
export function mapSourceSheetStatusToTruthLabel(status: string): TruthLabel {
  return SOURCE_SHEET_STATUS_TO_TRUTH_LABEL[status] ?? 'missing';
}
