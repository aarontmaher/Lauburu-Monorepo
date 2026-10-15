//! Detrended Fluctuation Analysis (DFA) - Alpha 1 Real-Time Calculator
//! Used for aerobic threshold (LT1/LT2) Zone 2 endurance coaching from R-R interval time series.

use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub struct DfaCalculator {
    rr_window: VecDeque<f32>,
    window_size: usize,
    current_alpha1: f32,
}

impl DfaCalculator {
    pub fn new(window_size: usize) -> Self {
        let ws = if window_size < 30 { 60 } else { window_size };
        Self {
            rr_window: VecDeque::with_capacity(ws + 10),
            window_size: ws,
            current_alpha1: 0.0,
        }
    }

    /// Ingest a new R-R interval in milliseconds and compute alpha1 if sufficient data
    pub fn add_rr_interval(&mut self, rr_ms: f32) -> f32 {
        if !(300.0..=2000.0).contains(&rr_ms) {
            return self.current_alpha1;
        }

        self.rr_window.push_back(rr_ms);
        if self.rr_window.len() > self.window_size {
            self.rr_window.pop_front();
        }

        if self.rr_window.len() >= 30 {
            self.current_alpha1 = self.calculate_alpha1();
        }

        self.current_alpha1
    }

    pub fn get_alpha1(&self) -> f32 {
        self.current_alpha1
    }

    /// Calculate short-term scaling exponent (alpha 1, scale range 4..16)
    fn calculate_alpha1(&self) -> f32 {
        let n = self.rr_window.len();
        if n < 16 {
            return 0.0;
        }

        let mean: f32 = self.rr_window.iter().sum::<f32>() / (n as f32);
        
        // Cumulative sum of integrated series
        let mut y = Vec::with_capacity(n);
        let mut cumsum = 0.0;
        for &val in &self.rr_window {
            cumsum += val - mean;
            y.push(cumsum);
        }

        // Window scales for alpha 1 (short-range correlations: 4 to 16 beats)
        let scales = [4, 6, 8, 12, 16];
        let mut log_scales = Vec::new();
        let mut log_fluctuations = Vec::new();

        for &scale in &scales {
            if scale >= n {
                continue;
            }
            let segments = n / scale;
            if segments == 0 {
                continue;
            }

            let mut sum_sq_err = 0.0;
            let mut total_points = 0;

            for s in 0..segments {
                let start_idx = s * scale;
                let end_idx = start_idx + scale;
                let seg = &y[start_idx..end_idx];

                // Linear trend regression: y = a*x + b
                let (slope, intercept) = Self::linear_fit(seg);
                for (x_i, &val) in seg.iter().enumerate() {
                    let trend = slope * (x_i as f32) + intercept;
                    let diff = val - trend;
                    sum_sq_err += diff * diff;
                    total_points += 1;
                }
            }

            if total_points > 0 {
                let fluctuation = (sum_sq_err / (total_points as f32)).sqrt();
                if fluctuation > 1e-5 {
                    log_scales.push((scale as f32).ln());
                    log_fluctuations.push(fluctuation.ln());
                }
            }
        }

        if log_scales.len() >= 2 {
            let (alpha, _) = Self::linear_fit_xy(&log_scales, &log_fluctuations);
            // Physiological bounding
            alpha.clamp(0.25, 1.75)
        } else {
            0.0
        }
    }

    fn linear_fit(y: &[f32]) -> (f32, f32) {
        let n = y.len() as f32;
        let sum_x = (0..y.len()).map(|i| i as f32).sum::<f32>();
        let sum_y = y.iter().sum::<f32>();
        let sum_xx = (0..y.len()).map(|i| (i as f32).powi(2)).sum::<f32>();
        let sum_xy = y.iter().enumerate().map(|(i, &v)| (i as f32) * v).sum::<f32>();

        let denom = n * sum_xx - sum_x * sum_x;
        if denom.abs() < 1e-6 {
            return (0.0, sum_y / n);
        }

        let slope = (n * sum_xy - sum_x * sum_y) / denom;
        let intercept = (sum_y - slope * sum_x) / n;
        (slope, intercept)
    }

    fn linear_fit_xy(x: &[f32], y: &[f32]) -> (f32, f32) {
        let n = x.len() as f32;
        let sum_x = x.iter().sum::<f32>();
        let sum_y = y.iter().sum::<f32>();
        let sum_xx = x.iter().map(|v| v * v).sum::<f32>();
        let sum_xy = x.iter().zip(y.iter()).map(|(&a, &b)| a * b).sum::<f32>();

        let denom = n * sum_xx - sum_x * sum_x;
        if denom.abs() < 1e-6 {
            return (0.0, sum_y / n);
        }

        let slope = (n * sum_xy - sum_x * sum_y) / denom;
        let intercept = (sum_y - slope * sum_x) / n;
        (slope, intercept)
    }
}
