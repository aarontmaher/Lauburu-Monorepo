use lauburu_core::dsp::PanTompkinsDetector;

#[test]
fn test_pan_tompkins_initialization() {
    let mut detector = PanTompkinsDetector::new(512.0);
    let res = detector.process_sample(0.0);
    assert_eq!(res.is_qrs_peak, false);
    assert_eq!(res.heart_rate_bpm, 0.0);
    assert_eq!(res.filtered_val, 0.0);
    assert_eq!(res.integrated_val, 0.0);
    assert_eq!(res.rr_interval_ms, 0.0);
    assert_eq!(res.rmssd_ms, 0.0);
    assert_eq!(res.sdnn_ms, 0.0);
    assert_eq!(res.pnn50_percent, 0.0);
}

#[test]
fn test_pan_tompkins_qrs_detection_synthetic() {
    let mut detector = PanTompkinsDetector::new(200.0);
    let sample_rate = 200.0;
    let duration_secs = 6.0;
    let total_samples = (sample_rate * duration_secs) as usize;

    let mut peak_count = 0;

    for i in 0..total_samples {
        let cycle_idx = i % 200;
        let sample = if cycle_idx == 10 {
            -0.2
        } else if (11..=13).contains(&cycle_idx) {
            2.0
        } else if cycle_idx == 14 {
            -0.4
        } else if (30..=45).contains(&cycle_idx) {
            0.15
        } else {
            0.0
        };

        let result = detector.process_sample(sample);
        if result.is_qrs_peak {
            peak_count += 1;
        }
    }

    assert!(
        (3..=7).contains(&peak_count),
        "Expected between 3 and 7 peaks, detected: {}",
        peak_count
    );
}

#[test]
fn test_hrv_calculation_validity() {
    let mut detector = PanTompkinsDetector::new(200.0);
    let mut detected_peaks = 0;

    for beat in 0..15 {
        for cycle_idx in 0..200 {
            let sample = if cycle_idx == 10 {
                -0.2
            } else if (11..=13).contains(&cycle_idx) {
                2.0
            } else if cycle_idx == 14 {
                -0.4
            } else if (30..=45).contains(&cycle_idx) {
                0.15
            } else {
                0.0
            };
            let res = detector.process_sample(sample);
            if res.is_qrs_peak {
                detected_peaks += 1;
                println!("Beat {} detected peak, HR: {}, RR: {}", beat, res.heart_rate_bpm, res.rr_interval_ms);
            }
        }
    }

    println!("Total detected peaks: {}, stored RR count: {}", detected_peaks, detector.rr_intervals.len());
    println!("Current HR: {}", detector.current_hr_bpm);

    assert!(detected_peaks >= 5, "Should detect at least 5 peaks, got: {}", detected_peaks);
    assert!(
        detector.current_hr_bpm >= 50.0 && detector.current_hr_bpm <= 75.0,
        "Heart rate {} should be close to 60 BPM",
        detector.current_hr_bpm
    );
}

#[test]
fn test_kamath_20_clinical_filter_prevents_rmssd_explosion() {
    let mut detector = PanTompkinsDetector::new(512.0);

    // Baseline resting beats (~78 bpm, natural variation 760-780 ms)
    let baseline_rrs = [770.0, 775.0, 768.0, 780.0, 772.0, 778.0, 771.0];
    for &rr in &baseline_rrs {
        detector.add_rr_interval(rr);
    }

    assert!(detector.current_rmssd < 20.0, "Resting RMSSD on steady beats should be <20ms, got: {}", detector.current_rmssd);
    assert!(detector.current_sdnn > 0.0, "SDNN must be non-zero");

    // Ingest a missed beat / ectopic interval of 1846.68 ms (the exact bug observed on Movesense)
    let clean = detector.add_rr_interval(1846.68);
    assert!(clean.is_some(), "Interval should be accepted as clamped");

    // Without Kamath filter, 1846ms causes RMSSD to explode to >500ms.
    // With Kamath filter, the outlier is clamped to the running median (~772ms), preserving physiological RMSSD!
    println!("Filtered RMSSD: {} ms (must be < 50 ms, was previously 591.9 ms)", detector.current_rmssd);
    assert!(
        detector.current_rmssd < 50.0,
        "Kamath 20% filter must prevent RMSSD explosion! Got: {}",
        detector.current_rmssd
    );
    assert!(detector.current_sdnn > 0.0, "SDNN must be populated");
}

