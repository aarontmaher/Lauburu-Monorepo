use std::ffi::CString;
use lauburu_core::bridge::c_api::*;

#[test]
fn test_c_ffi_lifecycle() {
    // 1. Initialize core FFI engine
    let init_res = lauburu_core_init();
    assert_eq!(init_res, 0);

    // 2. Ingest raw ECG sample via FFI
    let output = lauburu_process_ecg_sample(0.5);
    assert_eq!(output.is_qrs_peak, false, "Single raw sample must not trigger QRS peak");
    assert_eq!(output.heart_rate_bpm, 0.0, "Initial heart rate must be 0.0");

    // 3. Read biometric metrics (Zero-Mock Invariants)
    let readiness = lauburu_get_readiness_score();
    assert_eq!(readiness, 0.0, "Initial readiness score must be 0.0 (resting/disconnected)");

    let rmssd = lauburu_get_hrv_rmssd();
    assert_eq!(rmssd, 0.0, "Initial HRV RMSSD must be 0.0 ms");

    let alpha1 = lauburu_get_dfa_alpha1();
    assert!(alpha1 == 0.0 || (alpha1 >= 0.25 && alpha1 <= 1.75), "Alpha1 must be 0.0 uncalibrated or in physiological range [0.25, 1.75]");

    // 4. Test Shopify Tier validation via FFI C string
    let token_pro = CString::new("lauburu_pro_tier_subscriber_9912").unwrap();
    let tier_code = lauburu_verify_shopify_tier(token_pro.as_ptr());
    assert_eq!(tier_code, 1); // 1 = Pro Athlete

    let token_mesh = CString::new("lauburu_mesh_contributor_m4_mac_mini").unwrap();
    let mesh_tier_code = lauburu_verify_shopify_tier(token_mesh.as_ptr());
    assert_eq!(mesh_tier_code, 2); // 2 = Crowdsourced Compute Lifetime

    let token_free = CString::new("unknown_token").unwrap();
    let free_tier_code = lauburu_verify_shopify_tier(token_free.as_ptr());
    assert_eq!(free_tier_code, 0); // 0 = Free Community

    let null_tier_code = lauburu_verify_shopify_tier(std::ptr::null());
    assert_eq!(null_tier_code, 0); // Null safe fallback to Free

    // 5. Test JSON string allocation, validation, and deallocation
    let json_ptr = lauburu_get_telemetry_json();
    assert!(!json_ptr.is_null());
    let c_str = unsafe { std::ffi::CStr::from_ptr(json_ptr) };
    let json_str = c_str.to_str().unwrap();
    let parsed: serde_json::Value = serde_json::from_str(json_str).unwrap();
    assert_eq!(parsed["connected"], false);
    assert_eq!(parsed["readiness_score"], 0.0);
    assert_eq!(parsed["latest_ecg_sample"], 0.5);
    lauburu_free_string(json_ptr);
}
