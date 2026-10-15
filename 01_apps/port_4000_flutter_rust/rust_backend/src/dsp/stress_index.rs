//! Baevsky Stress Index & Autonomic Sympathovagal Balance Engine.
//! Computes live stress (0-100) and recovery status from R-R interval distributions.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StressIndexReading {
    pub stress_score_0_100: Option<f32>,
    pub baevsky_si: Option<f32>,
    pub parasympathetic_tone_pct: Option<f32>,
    pub sympathetic_activity_pct: Option<f32>,
    pub stress_classification: String,
    pub recovery_state: String,
}

pub struct StressIndexEngine;

impl StressIndexEngine {
    /// Calculate Baevsky Stress Index: SI = AMo / (2 * Mo * MxDMn)
    pub fn compute_stress(rr_intervals: &[f32], hr_bpm: f32) -> StressIndexReading {
        if rr_intervals.len() < 10 || hr_bpm <= 0.0 {
            return StressIndexReading {
                stress_score_0_100: None,
                baevsky_si: None,
                parasympathetic_tone_pct: None,
                sympathetic_activity_pct: None,
                stress_classification: "AWAITING RR INTERVALS".to_string(),
                recovery_state: "STANDBY".to_string(),
            };
        }

        let min_rr = rr_intervals.iter().cloned().fold(f32::INFINITY, f32::min);
        let max_rr = rr_intervals.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let range_mxdmn = (max_rr - min_rr) / 1000.0; // In seconds

        let mean_rr: f32 = rr_intervals.iter().sum::<f32>() / (rr_intervals.len() as f32);
        let mo_sec = mean_rr / 1000.0; // Mode approximation in seconds

        let bin_width = 50.0; // 50 ms bin width
        let mut mode_count = 0;
        for &rr in rr_intervals {
            if (rr - mean_rr).abs() <= bin_width {
                mode_count += 1;
            }
        }
        let amo_pct = (mode_count as f32 / rr_intervals.len() as f32) * 100.0;

        let si = if range_mxdmn > 0.02 && mo_sec > 0.3 {
            (amo_pct / (2.0 * mo_sec * range_mxdmn)).clamp(10.0, 1500.0)
        } else {
            100.0
        };

        // Normalized Stress Score (0-100)
        let norm_stress = ((si - 30.0) / 450.0).clamp(0.0, 1.0) * 100.0;
        let p_tone = (100.0 - norm_stress).clamp(5.0, 95.0);
        let s_tone = (100.0 - p_tone).clamp(5.0, 95.0);

        let (classification, recovery) = if si < 50.0 {
            ("LOW STRESS / HIGH VAGAL TONE", "SUPERCOMPENSATED / FULLY RECOVERED")
        } else if si < 150.0 {
            ("MODERATE / EQUILIBRIUM", "OPTIMAL RESTORATION")
        } else if si < 300.0 {
            ("ELEVATED SYMPATHETIC DRIVE", "FATIGUED / ADAPTATION PHASE")
        } else {
            ("HIGH PHYSIOLOGICAL STRAIN", "EXHAUSTION / OVERTRAINING RISK")
        };

        StressIndexReading {
            stress_score_0_100: Some(norm_stress),
            baevsky_si: Some(si),
            parasympathetic_tone_pct: Some(p_tone),
            sympathetic_activity_pct: Some(s_tone),
            stress_classification: classification.to_string(),
            recovery_state: recovery.to_string(),
        }
    }
}
