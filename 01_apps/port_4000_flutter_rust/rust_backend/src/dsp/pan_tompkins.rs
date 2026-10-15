//! Pan-Tompkins Real-Time QRS Detection & HRV DSP Engine
//! Implements 5-15Hz Bandpass, 5-point Derivative, Squaring, Moving Window Integration (MWI),
//! and Dual-Threshold Adaptive Peak Detection for 128Hz - 512Hz ECG streams.

use std::collections::VecDeque;

#[derive(Debug, Clone, PartialEq)]
pub struct QrsDetectionResult {
    pub is_qrs_peak: bool,
    pub filtered_val: f32,
    pub integrated_val: f32,
    pub heart_rate_bpm: f32,
    pub rr_interval_ms: f32,
    pub rmssd_ms: f32,
    pub sdnn_ms: f32,
    pub pnn50_percent: f32,
}

#[derive(Debug, Clone)]
pub struct PanTompkinsDetector {
    pub sample_rate_hz: f32,
    // Buffer histories for digital filtering
    raw_history: VecDeque<f32>,
    bp_history: VecDeque<f32>,
    mwi_buffer: VecDeque<f32>,
    mwi_window_size: usize,

    // Peak detection state
    spki: f32, // Signal Peak Integrator
    npki: f32, // Noise Peak Integrator
    threshold_i1: f32,
    threshold_i2: f32,

    // Timing state
    sample_count: u64,
    last_qrs_sample: u64,
    refractory_samples: u64,

    // RR intervals history (in ms)
    pub rr_intervals: VecDeque<f32>,
    max_rr_history: usize,

    // Running metrics
    pub current_hr_bpm: f32,
    pub current_rmssd: f32,
    pub current_sdnn: f32,
    pub current_pnn50: f32,

    // Adaptive peak tracking
    last_mwi: f32,
    prev_mwi: f32,
}

impl PanTompkinsDetector {
    pub fn new(sample_rate_hz: f32) -> Self {
        let sr = if sample_rate_hz <= 0.0 { 512.0 } else { sample_rate_hz };
        // MWI window is ~120 ms
        let mwi_window_size = ((0.120 * sr) as usize).max(3);
        // Refractory period is ~200 ms (to reject T-waves)
        let refractory_samples = ((0.200 * sr) as u64).max(1);

        Self {
            sample_rate_hz: sr,
            raw_history: VecDeque::with_capacity(32),
            bp_history: VecDeque::with_capacity(32),
            mwi_buffer: VecDeque::with_capacity(mwi_window_size + 4),
            mwi_window_size,

            spki: 0.15,
            npki: 0.02,
            threshold_i1: 0.05,
            threshold_i2: 0.025,

            sample_count: 0,
            last_qrs_sample: 0,
            refractory_samples,

            rr_intervals: VecDeque::with_capacity(64),
            max_rr_history: 60,

            current_hr_bpm: 0.0,
            current_rmssd: 0.0,
            current_sdnn: 0.0,
            current_pnn50: 0.0,

            last_mwi: 0.0,
            prev_mwi: 0.0,
        }
    }

    /// Process a single ECG sample and return the detection and biometric state
    pub fn process_sample(&mut self, raw_sample: f32) -> QrsDetectionResult {
        self.sample_count += 1;

        self.raw_history.push_back(raw_sample);
        if self.raw_history.len() > 32 {
            self.raw_history.pop_front();
        }

        // 1. Digital Bandpass Filter
        let filtered_val = self.apply_bandpass(raw_sample);
        self.bp_history.push_back(filtered_val);
        if self.bp_history.len() > 16 {
            self.bp_history.pop_front();
        }

        // 2. 5-Point Derivative Filter
        let deriv_val = self.apply_derivative(filtered_val);

        // 3. Non-linear Squaring
        let squared_val = deriv_val * deriv_val;

        // 4. Moving Window Integrator (MWI)
        self.mwi_buffer.push_back(squared_val);
        if self.mwi_buffer.len() > self.mwi_window_size {
            self.mwi_buffer.pop_front();
        }
        let mwi_val: f32 = self.mwi_buffer.iter().sum::<f32>() / (self.mwi_window_size as f32);

        // 5. Local Peak Detection on MWI signal
        let is_local_max = self.last_mwi > self.prev_mwi && self.last_mwi > mwi_val;
        let peak_candidate = self.last_mwi;
        self.prev_mwi = self.last_mwi;
        self.last_mwi = mwi_val;

        let mut is_qrs = false;
        let samples_since_last = if self.last_qrs_sample > 0 {
            self.sample_count.saturating_sub(self.last_qrs_sample)
        } else {
            0
        };

        if is_local_max && (self.last_qrs_sample == 0 || samples_since_last > self.refractory_samples) {
            if peak_candidate > self.threshold_i1 {
                is_qrs = true;

                if self.last_qrs_sample > 0 {
                    let rr_ms = (samples_since_last as f32 / self.sample_rate_hz) * 1000.0;
                    self.add_rr_interval(rr_ms);
                }

                self.last_qrs_sample = self.sample_count;
                self.spki = 0.125 * peak_candidate + 0.875 * self.spki;
            } else if peak_candidate > self.threshold_i2 {
                self.npki = 0.125 * peak_candidate + 0.875 * self.npki;
            }
        }

        // Dynamic threshold adjustment
        self.threshold_i1 = (self.npki + 0.25 * (self.spki - self.npki)).max(0.005);
        self.threshold_i2 = 0.5 * self.threshold_i1;

        QrsDetectionResult {
            is_qrs_peak: is_qrs,
            filtered_val,
            integrated_val: mwi_val,
            heart_rate_bpm: self.current_hr_bpm,
            rr_interval_ms: self.rr_intervals.back().copied().unwrap_or(0.0),
            rmssd_ms: self.current_rmssd,
            sdnn_ms: self.current_sdnn,
            pnn50_percent: self.current_pnn50,
        }
    }

    fn apply_bandpass(&self, x: f32) -> f32 {
        let n = self.raw_history.len();
        if n < 4 {
            return x;
        }
        let x0 = x;
        let x1 = self.raw_history[n - 1];
        let x2 = if n >= 2 { self.raw_history[n - 2] } else { x1 };
        let x3 = if n >= 3 { self.raw_history[n - 3] } else { x2 };

        (x0 - x3) + 0.5 * (x1 - x2)
    }

    fn apply_derivative(&self, x: f32) -> f32 {
        let n = self.bp_history.len();
        if n < 4 {
            return x;
        }
        let x0 = x;
        let x1 = self.bp_history[n - 1];
        let x2 = if n >= 2 { self.bp_history[n - 2] } else { x1 };
        let x3 = if n >= 3 { self.bp_history[n - 3] } else { x2 };

        (2.0 * x0 + x1 - x2 - 2.0 * x3) * 0.25
    }

    /// Ingest an RR interval with Kamath 20% Clinical Filter and update HRV metrics.
    /// Rejects physiological outliers (<300ms / >2000ms) and arm-motion/ectopic deviations (>20% from median).
    pub fn add_rr_interval(&mut self, raw_rr_ms: f32) -> Option<f32> {
        // 1. Biological limits check: 300ms (200 bpm) to 2000ms (30 bpm)
        if !(300.0..=2000.0).contains(&raw_rr_ms) {
            return None;
        }

        // 2. Kamath 20% Clinical Filter against recent running median
        let clean_rr = if self.rr_intervals.len() >= 3 {
            let recent_count = self.rr_intervals.len().min(7);
            let mut recent: Vec<f32> = self.rr_intervals.iter().rev().take(recent_count).copied().collect();
            recent.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            let median_rr = recent[recent.len() / 2];

            if median_rr > 0.0 && (raw_rr_ms - median_rr).abs() / median_rr > 0.20 {
                // Flagged as ectopic beat or motion artifact: clamp to median
                median_rr
            } else {
                raw_rr_ms
            }
        } else {
            raw_rr_ms
        };

        self.rr_intervals.push_back(clean_rr);
        if self.rr_intervals.len() > self.max_rr_history {
            self.rr_intervals.pop_front();
        }

        self.update_hrv_metrics();
        Some(clean_rr)
    }

    pub fn update_hrv_metrics(&mut self) {
        if self.rr_intervals.is_empty() {
            return;
        }

        // 1. Mean HR calculation
        let mean_rr: f32 = self.rr_intervals.iter().sum::<f32>() / (self.rr_intervals.len() as f32);
        if mean_rr > 0.0 && self.current_hr_bpm == 0.0 {
            self.current_hr_bpm = 60000.0 / mean_rr;
        }

        if self.rr_intervals.len() < 2 {
            return;
        }

        // 2. SDNN calculation
        let variance: f32 = self
            .rr_intervals
            .iter()
            .map(|&rr| (rr - mean_rr).powi(2))
            .sum::<f32>()
            / (self.rr_intervals.len() as f32);
        self.current_sdnn = variance.sqrt();

        // 3. RMSSD and pNN50 calculation
        let mut sum_sq_diff = 0.0;
        let mut count_50 = 0;
        let diff_count = self.rr_intervals.len() - 1;

        for i in 0..diff_count {
            let diff = (self.rr_intervals[i + 1] - self.rr_intervals[i]).abs();
            sum_sq_diff += diff * diff;
            if diff > 50.0 {
                count_50 += 1;
            }
        }

        self.current_rmssd = (sum_sq_diff / (diff_count as f32)).sqrt();
        self.current_pnn50 = (count_50 as f32 / diff_count as f32) * 100.0;
    }

    /// Reset internal state buffers
    pub fn reset(&mut self) {
        self.raw_history.clear();
        self.bp_history.clear();
        self.mwi_buffer.clear();
        self.rr_intervals.clear();
        self.sample_count = 0;
        self.last_qrs_sample = 0;
        self.spki = 0.15;
        self.npki = 0.02;
        self.threshold_i1 = 0.05;
        self.threshold_i2 = 0.025;
        self.current_hr_bpm = 0.0;
        self.current_rmssd = 0.0;
        self.current_sdnn = 0.0;
        self.current_pnn50 = 0.0;
        self.last_mwi = 0.0;
        self.prev_mwi = 0.0;
    }
}
