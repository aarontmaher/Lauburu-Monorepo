"use strict";
/**
 * WHOOP raw ingestion — converts MCP daily_summary responses
 * into typed WhoopDailyMetricsRaw records for Layer 1 storage.
 *
 * Pure function. No network calls. No interpretation.
 * Preserves data exactly as received; missing stays null.
 *
 * Internal-only: called by /v1/internal/ingest/whoop, never
 * by client-facing app routes.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ingestWhoopDay = ingestWhoopDay;
exports.ingestWhoopBatch = ingestWhoopBatch;
let _idCounter = 0;
function generateId(prefix, date) {
    return `${prefix}_${date}_${Date.now()}_${++_idCounter}`;
}
/**
 * Convert one WHOOP MCP day payload into a typed raw record.
 * Pure, deterministic (except for id generation timestamps).
 */
function ingestWhoopDay(payload, athleteId) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l;
    const now = new Date().toISOString();
    const workoutDetails = ((_a = payload.workout_details) !== null && _a !== void 0 ? _a : []).map((w) => {
        var _a, _b, _c;
        return ({
            id: w.id,
            sportId: w.sport_id,
            sportName: w.sport_name,
            strain: w.strain,
            avgHr: w.avg_hr,
            maxHr: w.max_hr,
            kilojoules: w.kilojoules,
            caloriesKcal: (_a = w.calories_kilocalories) !== null && _a !== void 0 ? _a : null,
            startIso: w.start,
            endIso: w.end,
            durationMin: w.duration_min,
            percentRecorded: (_b = w.percent_recorded) !== null && _b !== void 0 ? _b : null,
            hrZones: ((_c = w.hr_zones) !== null && _c !== void 0 ? _c : []).map((z) => ({
                zoneIndex: z.zone_index,
                durationMilli: z.duration_milli,
                percentOfWorkout: z.percent_of_workout,
            })),
        });
    });
    return {
        id: generateId('whoop_raw', payload.local_date),
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        athleteId,
        localDate: payload.local_date,
        timezone: (_b = payload.timezone) !== null && _b !== void 0 ? _b : 'UTC',
        recoveryScore: payload.recovery_score,
        hrvMs: payload.hrv_ms,
        rhrBpm: payload.rhr_bpm,
        spo2Pct: payload.spo2_pct,
        skinTempCelsius: payload.skin_temp_celsius,
        sleepPerformancePct: payload.sleep_performance_pct,
        sleepEfficiencyPct: payload.sleep_efficiency_pct,
        totalSleepHours: payload.total_sleep_hours,
        swsHours: payload.sws_hours,
        remHours: payload.rem_hours,
        lightSleepHours: (_c = payload.light_sleep_hours) !== null && _c !== void 0 ? _c : null,
        awakeHours: (_d = payload.awake_hours) !== null && _d !== void 0 ? _d : null,
        inBedHours: (_e = payload.in_bed_hours) !== null && _e !== void 0 ? _e : null,
        respiratoryRate: payload.respiratory_rate,
        sleepDebtHours: payload.sleep_debt_hours,
        sleepNeededBaselineHours: payload.sleep_needed_baseline_hours,
        sleepConsistencyPct: (_f = payload.sleep_consistency_pct) !== null && _f !== void 0 ? _f : null,
        dayStrain: payload.day_strain,
        dayKilojoules: payload.day_kilojoules,
        dayAvgHr: payload.day_avg_hr,
        dayMaxHr: payload.day_max_hr,
        workoutCount: (_g = payload.workout_count) !== null && _g !== void 0 ? _g : 0,
        workoutStrainTotal: payload.workout_strain_total,
        workoutMinutesTotal: payload.workout_minutes_total,
        workoutDetails,
        sourceUpdatedAt: (_h = payload.source_updated_at) !== null && _h !== void 0 ? _h : null,
        sourceRecordIds: {
            cycleId: (_j = payload.cycle_id) !== null && _j !== void 0 ? _j : null,
            sleepId: (_k = payload.sleep_id) !== null && _k !== void 0 ? _k : null,
            recoveryCycleId: (_l = payload.recovery_cycle_id) !== null && _l !== void 0 ? _l : null,
        },
    };
}
/**
 * Ingest a batch of WHOOP MCP day payloads.
 * Returns typed raw records sorted by date ascending.
 */
function ingestWhoopBatch(payloads, athleteId) {
    return payloads
        .map((p) => ingestWhoopDay(p, athleteId))
        .sort((a, b) => a.localDate.localeCompare(b.localDate));
}
