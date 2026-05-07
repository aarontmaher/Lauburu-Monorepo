/**
 * Polar store — scaffold for a future Polar integration.
 *
 * Status as of 2026-04-10: NO live ingestion. Polar data today reaches
 * the app only via Apple HealthKit / Android Health Connect when the
 * user has the Polar Flow app set to write there, which means it
 * arrives as generic HealthKit / Health Connect metrics with no
 * Polar-specific richness (no Nightly Recharge, no Recovery Pro,
 * no orthostatic test result, no training load breakdown).
 *
 * This store reserves the surface that a future direct Polar path
 * will target. Three candidate implementation paths for later, in
 * decreasing order of coverage and increasing order of effort:
 *
 *   (1) Polar AccessLink REST API — OAuth2 flow, daily + weekly
 *       summaries, Nightly Recharge + Recovery Pro when the user has
 *       the paid Polar Flow subscription. Biggest value, most work.
 *
 *   (2) Polar Flow web export / CSV import — the user exports from
 *       flow.polar.com, the app parses the CSV. Simpler, no OAuth,
 *       but manual and fragile when Polar changes the export format.
 *
 *   (3) Polar sensor BLE (H9/H10 chest strap, Verity Sense, etc.) —
 *       standard Bluetooth Heart Rate Service, reserved for future
 *       Train-session HR capture only. It does not feed readiness.
 *       Needs `react-native-ble-plx` + prebuild + dev client rebuild,
 *       same as FTMS.
 *
 * Nothing in the app calls this store today beyond the PolarCard
 * scaffold on the Health tab. When a real implementation lands, it
 * only needs to replace `fetchToday` with a real fetch and start
 * setting `day`, `status`, and `error`. The shape is already the
 * `PolarSnapshot` type from `@lauburu/shared`, which mirrors
 * `WhoopSnapshot` structurally. Any future Polar-backed readiness use
 * needs separate provenance, missingness, and product-gating work.
 */
import { create } from 'zustand';
import type { PolarSnapshot } from '@lauburu/shared';

type PolarStatus = 'idle' | 'loading' | 'ready' | 'error' | 'not_connected';

interface PolarState {
  status: PolarStatus;
  day: PolarSnapshot | null;
  fetchedAt: string | null;
  error: string | null;

  /**
   * Stub fetch — always resolves to `not_connected` today. Real
   * implementations will replace the body of this function, not
   * the surface.
   */
  fetchToday: () => Promise<void>;
}

export const usePolarStore = create<PolarState>((set) => ({
  status: 'not_connected',
  day: null,
  fetchedAt: null,
  error: null,

  fetchToday: async () => {
    // Reserved seam — no live integration yet. See file header for the
    // three candidate paths. When real ingestion lands this is the one
    // function to replace.
    set({
      status: 'not_connected',
      day: null,
      error: null,
      fetchedAt: new Date().toISOString(),
    });
  },
}));
