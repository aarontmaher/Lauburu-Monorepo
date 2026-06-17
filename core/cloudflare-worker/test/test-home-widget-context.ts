/**
 * Home widget context contract.
 *
 * Locks the shared app-side data adapter that future iOS WidgetKit
 * and Android widget code should consume. The adapter is product
 * safe: no Admin/Dev or Developer MCP data, and no strong readiness
 * claims unless confidence + source freshness are sufficient.
 */

import assert from 'node:assert/strict';
import { buildHomeWidgetContext } from '../../apps/mobile/src/services/home-widget-context';
import type { AppAthleteState } from '../../apps/mobile/src/services/app-athlete-state';

function state(overrides: Partial<AppAthleteState> = {}): AppAthleteState {
  const base: AppAthleteState = {
    date: '2026-05-09',
    recovery_context: {
      band: 'mid',
      score_0_100: 71,
      contributing_sources: ['hrv_trend', 'sleep_hours'],
      note: 'Useful context, still app-owned.',
      uses_vendor_score: false,
    },
    load_context: {
      band: 'under',
      sessions_7d: 0,
      hard_sessions_3d: 0,
      consecutive_hard_days: 0,
      note: 'No recent sessions.',
    },
    sleep_adequacy: { band: 'mid', hours_last_night: 7, hours_7d_avg: 7, note: 'ok' },
    fueling_adequacy: { band: 'mid', calories_vs_target_pct: 85, protein_vs_target_pct: 90, gaps: [], note: 'ok' },
    hydration_adequacy: { band: 'mid', water_ml_today: 1800, note: 'ok' },
    acute_fatigue: { band: 'mid', note: 'ok' },
    chronic_load_trend: { direction: 'stable', note: 'ok' },
    readiness_confidence: { level: 'medium', value: 0.7, reasons_for_low: [] },
    data_quality: {
      missing: [],
      freshness_hours: { whoop: null, apple_health: 2, native_health: 2, nutrition: 4, training: 8 },
      history_depth: { hrv_days: 20, rhr_days: 20, sleep_days: 20, sessions_total: 3, baseline_window_days: 30 },
    },
    source_roles: {
      native_health: {
        source: 'apple_health',
        label: 'Apple Health',
        role: 'broad_baseline',
        days_with_data: 20,
        covers_today: true,
        history_depth_days: 20,
      },
      apple_health: { role: 'broad_baseline', days_with_data: 20, covers_today: true, history_depth_days: 20 },
      whoop_direct: { role: 'not_connected', has_today_cycle: false, latest_cycle_date: null },
      whoop_csv: { role: 'not_imported', imported_rows: null, window_days: null },
      polar: { role: 'not_connected', via_health_connect: false, days_with_records: null },
      samsung_health: { role: 'not_connected', days_with_records: null },
    },
    provisional: { seed_mode: true, score_kind: 'custom_readiness', calibration_source: null, primary_live_source: 'apple_health' },
  };
  return { ...base, ...overrides };
}

{
  const widget = buildHomeWidgetContext({ platform: 'ios', state: state() });
  assert.equal(widget.healthSource.label, 'Apple Health');
  assert.equal(widget.healthSource.status, 'connected');
  assert.equal(widget.readiness.truthLabel, 'provisional');
  assert.equal(widget.readiness.score, null, 'provisional readiness must not show a strong numeric score');
  assert.equal(widget.nextAction.id, 'train', 'underloaded week suggests opening timer');
  assert.deepEqual(widget.quickActions.map((a) => a.id), ['start_journal', 'open_timer', 'view_readiness']);
  assert.equal(widget.safety.productMcpSafe, true);
  assert.equal(widget.safety.includesDeveloperMcpData, false);
}

{
  const widget = buildHomeWidgetContext({
    platform: 'android',
    state: state({
      source_roles: {
        ...state().source_roles,
        native_health: {
          source: 'health_connect',
          label: 'Health Connect',
          role: 'not_connected',
          days_with_data: 0,
          covers_today: false,
          history_depth_days: null,
        },
      },
      data_quality: {
        ...state().data_quality,
        freshness_hours: { ...state().data_quality.freshness_hours, native_health: null },
      },
      provisional: { seed_mode: true, score_kind: 'custom_readiness', calibration_source: null, primary_live_source: 'none' },
    }),
  });
  assert.equal(widget.healthSource.label, 'Health Connect');
  assert.equal(widget.healthSource.status, 'missing');
  assert.equal(widget.readiness.label, 'Readiness needs data');
  assert.equal(widget.nextAction.id, 'connect_health');
}

{
  const widget = buildHomeWidgetContext({
    platform: 'ios',
    state: state({
      recovery_context: { ...state().recovery_context, band: 'high', score_0_100: 86 },
      readiness_confidence: { level: 'high', value: 0.92, reasons_for_low: [] },
    }),
  });
  assert.equal(widget.readiness.truthLabel, 'provisional');
  assert.equal(widget.readiness.score, null, 'seed-mode readiness stays non-numeric even when confidence is high');
  assert.equal(widget.safety.noStrongReadinessClaim, true);
}

{
  const widget = buildHomeWidgetContext({
    platform: 'ios',
    state: state({
      data_quality: {
        ...state().data_quality,
        freshness_hours: { ...state().data_quality.freshness_hours, native_health: 30 },
      },
    }),
  });
  assert.equal(widget.healthSource.status, 'stale');
  assert.equal(widget.readiness.truthLabel, 'stale');
  assert.equal(widget.readiness.score, null);
}

console.log('Home widget context contract test passed.');
