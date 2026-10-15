use lauburu_core::dsp::DfaCalculator;
use lauburu_core::biometrics::BiometricsEngine;

#[test]
fn test_dfa_alpha1_baseline() {
    let mut calc = DfaCalculator::new(60);
    assert_eq!(calc.get_alpha1(), 0.0);

    // Simulate 50 RR intervals with physiological random-walk drift (1/f pink noise approximation)
    for i in 0..50 {
        let drift = ((i as f32 * 0.3).sin() * 25.0) + ((i as f32 * 0.07).cos() * 15.0);
        let rr = (800.0 + drift).clamp(600.0, 1100.0);
        calc.add_rr_interval(rr);
    }

    let alpha1 = calc.get_alpha1();
    assert!(
        (0.25..=1.75).contains(&alpha1),
        "DFA Alpha1 {} should be in physiological range [0.25, 1.75]",
        alpha1
    );
}

#[test]
fn test_zone2_metabolic_classification() {
    let engine = BiometricsEngine::new(512.0);

    // Disconnected / zero-mock state
    assert_eq!(engine.classify_zone2(0.0, 0.0), "Resting / Disconnected");
    // Active metabolic zones
    assert_eq!(engine.classify_zone2(0.75, 135.0), "Zone 2: Optimal Aerobic (LT1)");
    assert_eq!(engine.classify_zone2(0.90, 110.0), "Zone 1: Active Recovery");
    assert_eq!(engine.classify_zone2(0.45, 175.0), "Zone 4/5: Anaerobic / Above LT2");
    assert_eq!(engine.classify_zone2(1.10, 48.0), "Resting / Deep Recovery");
}
