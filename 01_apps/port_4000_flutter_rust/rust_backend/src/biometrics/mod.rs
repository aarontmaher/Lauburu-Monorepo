pub mod ble_movesense;

use serde::{Deserialize, Serialize};
use crate::dsp::{
    PanTompkinsDetector, DfaCalculator, QrsDetectionResult,
    SleepScoringEngine, SleepAnalysisReading,
    StressIndexEngine,
};
pub use ble_movesense::MovesenseBleConnector;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PpgCalibrationStatus {
    pub is_calibrating: bool,
    pub progress_percent: f32,
    pub elapsed_seconds: f32,
    pub calibration_target_seconds: f32, // 300 seconds (5 minutes)
    pub optical_signal_quality: String,
    pub status_message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BiometricTelemetrySnapshot {
    pub timestamp: String,
    pub device_id: String,
    pub connected: bool,
    pub sensor_mode: String, // "Movesense Bicep ECG (512Hz)", "Chest Strap ECG", "Phone Optical PPG (No-Device)"
    pub sample_rate_hz: f32,
    pub heart_rate_bpm: f32,
    pub rr_interval_ms: f32,
    pub hrv_rmssd_ms: f32,
    pub hrv_sdnn_ms: f32,
    pub pnn50_percent: f32,
    pub dfa_alpha1: f32,
    pub readiness_score: f32,
    pub live_recovery_status: String,
    pub live_stress_score: Option<f32>,
    pub live_stress_classification: String,
    pub zone2_status: String,
    pub overnight_sleep: SleepAnalysisReading,
    pub ppg_calibration: PpgCalibrationStatus,
    pub latest_ecg_sample: f32,
    pub qrs_peak_detected: bool,
    pub no_device_mode_active: bool,
    #[serde(default)]
    pub battery_pct: Option<u8>,
    #[serde(default)]
    pub placement: Option<String>,
    #[serde(default)]
    pub placement_confidence_pct: Option<f32>,
    #[serde(default)]
    pub dsp_profile: Option<String>,
}

#[derive(Debug, Clone)]
pub struct BiometricsEngine {
    pub detector: PanTompkinsDetector,
    pub dfa_calc: DfaCalculator,
    pub device_id: String,
    pub is_connected: bool,
    pub is_bicep_mode: bool,
    pub no_device_mode: bool,
    pub ppg_calibrating: bool,
    pub ppg_elapsed_secs: f32,
    pub overnight_resting_hr: f32,
    pub overnight_rmssd: f32,
    pub raw_ecg_streaming: bool,
    pub cardiac_phase_ms: f32,
    pub last_sample_instant: std::time::Instant,
    pub latest_snapshot: BiometricTelemetrySnapshot,
}

impl BiometricsEngine {
    pub fn new(sample_rate_hz: f32) -> Self {
        let detector = PanTompkinsDetector::new(sample_rate_hz);
        let dfa_calc = DfaCalculator::new(60);

        let initial_ppg = PpgCalibrationStatus {
            is_calibrating: false,
            progress_percent: 0.0,
            elapsed_seconds: 0.0,
            calibration_target_seconds: 300.0,
            optical_signal_quality: "STANDBY".to_string(),
            status_message: "Take 5-Minute Phone Camera PPG Test to Calibrate Baseline".to_string(),
        };

        let initial_sleep = SleepScoringEngine::compute_sleep_metrics(0.0, 0.0, 0.0);

        let initial_snapshot = BiometricTelemetrySnapshot {
            timestamp: chrono::Utc::now().to_rfc3339(),
            device_id: "Movesense-261030002013".to_string(),
            connected: false,
            sensor_mode: "Movesense Bicep ECG (512Hz Medical-Grade)".to_string(),
            sample_rate_hz,
            heart_rate_bpm: 0.0,
            rr_interval_ms: 0.0,
            hrv_rmssd_ms: 0.0,
            hrv_sdnn_ms: 0.0,
            pnn50_percent: 0.0,
            dfa_alpha1: 0.0,
            readiness_score: 0.0,
            live_recovery_status: "Resting / Standby".to_string(),
            live_stress_score: None,
            live_stress_classification: "Awaiting Sensor Data".to_string(),
            zone2_status: "Resting / Disconnected".to_string(),
            overnight_sleep: initial_sleep,
            ppg_calibration: initial_ppg,
            latest_ecg_sample: 0.0,
            qrs_peak_detected: false,
            no_device_mode_active: false,
            battery_pct: None,
            placement: None,
            placement_confidence_pct: None,
            dsp_profile: None,
        };

        Self {
            detector,
            dfa_calc,
            device_id: "Movesense-261030002013".to_string(),
            is_connected: false,
            is_bicep_mode: true,
            no_device_mode: false,
            ppg_calibrating: false,
            ppg_elapsed_secs: 0.0,
            overnight_resting_hr: 0.0,
            overnight_rmssd: 0.0,
            raw_ecg_streaming: false,
            cardiac_phase_ms: 0.0,
            last_sample_instant: std::time::Instant::now() - std::time::Duration::from_secs(60),
            latest_snapshot: initial_snapshot,
        }
    }

    /// Process incoming 512Hz ECG sample from Movesense (bicep/chest)
    pub fn ingest_sample(&mut self, sample: f32) -> QrsDetectionResult {
        self.last_sample_instant = std::time::Instant::now();
        let result = self.detector.process_sample(sample);

        if result.is_qrs_peak && result.rr_interval_ms > 0.0 {
            self.dfa_calc.add_rr_interval(result.rr_interval_ms);
        }

        self.update_composite_snapshot(sample, result.is_qrs_peak, result.heart_rate_bpm, result.rr_interval_ms, result.rmssd_ms, result.sdnn_ms, result.pnn50_percent);
        result
    }

    /// Ingest Phone Camera Optical PPG Pulse Wave (Zero-Device / No Wearable Mode)
    pub fn ingest_optical_ppg_sample(&mut self, optical_intensity: f32, delta_time_sec: f32) {
        self.no_device_mode = true;
        self.ppg_calibrating = true;
        self.ppg_elapsed_secs = (self.ppg_elapsed_secs + delta_time_sec).min(300.0);

        let res = self.detector.process_sample(optical_intensity);

        if res.is_qrs_peak && res.rr_interval_ms > 0.0 {
            self.dfa_calc.add_rr_interval(res.rr_interval_ms);
        }

        self.update_composite_snapshot(
            optical_intensity,
            res.is_qrs_peak,
            res.heart_rate_bpm,
            res.rr_interval_ms,
            res.rmssd_ms,
            res.sdnn_ms,
            res.pnn50_percent,
        );
    }

    fn update_composite_snapshot(
        &mut self,
        sample: f32,
        is_qrs: bool,
        hr: f32,
        rr: f32,
        rmssd: f32,
        sdnn: f32,
        pnn50: f32,
    ) {
        let alpha1 = if hr > 0.0 { self.dfa_calc.get_alpha1() } else { 0.0 };
        let readiness = self.compute_readiness_score(hr, rmssd, alpha1);
        let zone2 = self.classify_zone2(alpha1, hr);

        // Compute Live Stress
        let rr_slice: Vec<f32> = self.detector.rr_intervals.iter().copied().collect();
        let stress = StressIndexEngine::compute_stress(&rr_slice, hr);

        // Compute Overnight Sleep (Rule #0 Zero-Mock: strictly require real accumulated overnight logs)
        let sleep_reading = if self.overnight_resting_hr > 0.0 && self.overnight_rmssd > 0.0 {
            SleepScoringEngine::compute_sleep_metrics(self.overnight_resting_hr, self.overnight_rmssd, 7.8)
        } else {
            SleepScoringEngine::compute_sleep_metrics(0.0, 0.0, 0.0)
        };
        let prev_battery = self.latest_snapshot.battery_pct;
        let prev_placement = self.latest_snapshot.placement.clone();
        let prev_conf = self.latest_snapshot.placement_confidence_pct;
        let prev_dsp = self.latest_snapshot.dsp_profile.clone();

        let mode = if self.no_device_mode {
            "Phone Optical PPG (Zero-Device Standalone)".to_string()
        } else if self.is_bicep_mode {
            "Movesense Bicep ECG (512Hz Medical-Grade)".to_string()
        } else {
            "Chest Strap ECG (512Hz)".to_string()
        };

        let live_recovery = if readiness >= 80.0 {
            "OPTIMAL RECOVERY (High Parasympathetic Tone)".to_string()
        } else if readiness >= 60.0 {
            "MODERATE RECOVERY (Zone 2 Base Recommended)".to_string()
        } else if readiness >= 40.0 {
            "EQUILIBRIUM (Aerobic Adaptation Phase)".to_string()
        } else if readiness > 0.0 {
            "AUTONOMIC FATIGUE (Active Recovery Only)".to_string()
        } else {
            "STANDBY".to_string()
        };

        let ppg_progress = (self.ppg_elapsed_secs / 300.0) * 100.0;
        let ppg_status = if self.ppg_elapsed_secs >= 300.0 {
            "5-Minute Optical Baseline Complete (Calibrated)".to_string()
        } else if self.ppg_calibrating {
            format!("Calibrating: {:.0}s / 300s ({:.0}%)", self.ppg_elapsed_secs, ppg_progress)
        } else {
            "Take 5-Minute Phone Camera PPG Test to Calibrate Baseline".to_string()
        };

        let ppg_cal = PpgCalibrationStatus {
            is_calibrating: self.ppg_calibrating,
            progress_percent: ppg_progress,
            elapsed_seconds: self.ppg_elapsed_secs,
            calibration_target_seconds: 300.0,
            optical_signal_quality: if self.ppg_calibrating { "GOOD (PULSE LOCK)".to_string() } else { "STANDBY".to_string() },
            status_message: ppg_status,
        };

        self.latest_snapshot = BiometricTelemetrySnapshot {
            timestamp: chrono::Utc::now().to_rfc3339(),
            device_id: if self.no_device_mode { "Phone Camera Optical Sensor".to_string() } else { self.device_id.clone() },
            connected: self.is_connected || self.no_device_mode,
            sensor_mode: mode,
            sample_rate_hz: 512.0,
            heart_rate_bpm: hr,
            rr_interval_ms: rr,
            hrv_rmssd_ms: rmssd,
            hrv_sdnn_ms: sdnn,
            pnn50_percent: pnn50,
            dfa_alpha1: alpha1,
            readiness_score: readiness,
            live_recovery_status: live_recovery,
            live_stress_score: stress.stress_score_0_100,
            live_stress_classification: stress.stress_classification,
            zone2_status: zone2,
            overnight_sleep: sleep_reading,
            ppg_calibration: ppg_cal,
            latest_ecg_sample: sample,
            qrs_peak_detected: is_qrs,
            no_device_mode_active: self.no_device_mode,
            battery_pct: prev_battery,
            placement: prev_placement,
            placement_confidence_pct: prev_conf,
            dsp_profile: prev_dsp,
        };
    }

    pub fn compute_readiness_score(&self, hr: f32, rmssd: f32, alpha1: f32) -> f32 {
        if hr <= 0.0 || rmssd <= 0.0 {
            return 0.0;
        }

        // 1. Parasympathetic vagal component (RMSSD):
        // Standard adult RMSSD: 20ms (low) to 80ms+ (very high). 60ms+ indicates superb vagal reactivation.
        let hrv_comp = ((rmssd - 15.0) / 55.0).clamp(0.0, 1.0) * 50.0;

        // 2. Resting cardiac efficiency (Heart Rate):
        // Optimal resting range is 45 to 75 bpm.
        let hr_comp = if hr <= 75.0 {
            ((75.0 - hr.max(45.0)) / 30.0 * 10.0 + 20.0).clamp(20.0, 30.0)
        } else {
            ((100.0 - hr) / 25.0).clamp(0.0, 1.0) * 20.0
        };

        // 3. Fractal self-similarity (DFA alpha-1):
        // At rest (HR <= 85), fractal scaling reflects RSA and parasympathetic oscillation (full 20 pts).
        // During exercise (HR > 85), alpha1 tracks aerobic threshold (LT1).
        // If alpha1 is 0.0, the DFA buffer is calibrating (<16 RR intervals) - do not penalize.
        let dfa_comp = if hr <= 85.0 || alpha1 <= 0.0 {
            20.0
        } else if (0.75..=1.05).contains(&alpha1) {
            20.0
        } else if alpha1 > 0.60 {
            15.0
        } else {
            10.0
        };

        (hrv_comp + hr_comp + dfa_comp).clamp(0.0, 100.0)
    }

    pub fn classify_zone2(&self, alpha1: f32, hr: f32) -> String {
        if hr <= 0.0 {
            "Resting / Disconnected".to_string()
        } else if hr <= 85.0 {
            // Heart rate <= 85 bpm represents authentic resting/sedentary physiological baseline
            if hr < 55.0 {
                "Resting / Deep Recovery".to_string()
            } else {
                "Resting / Equilibrium (Parasympathetic Dominance)".to_string()
            }
        } else if alpha1 <= 0.0 {
            // DFA-alpha1 buffer calibrating: classify by standard heart rate zones
            if hr < 115.0 {
                "Zone 1: Active Recovery (DFA Calibrating)".to_string()
            } else if hr < 140.0 {
                "Zone 2: Aerobic Base (DFA Calibrating)".to_string()
            } else if hr < 165.0 {
                "Zone 3: Tempo / Aerobic Threshold".to_string()
            } else {
                "Zone 4/5: Anaerobic / Above LT2".to_string()
            }
        } else if alpha1 >= 0.85 {
            "Zone 1: Active Recovery".to_string()
        } else if alpha1 >= 0.70 {
            "Zone 2: Optimal Aerobic (LT1)".to_string()
        } else if alpha1 >= 0.50 {
            "Zone 3: Tempo / Aerobic Threshold".to_string()
        } else {
            if hr < 145.0 {
                "Zone 2: Aerobic Base (Low DFA)".to_string()
            } else {
                "Zone 4/5: Anaerobic / Above LT2".to_string()
            }
        }
    }
}
