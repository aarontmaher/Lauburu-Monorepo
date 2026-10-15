//! C-Compatible FFI Export Layer for Flutter Rust Bridge & native interop.

use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::sync::atomic::{AtomicBool, Ordering};
use once_cell::sync::Lazy;
use parking_lot::Mutex;
use crate::biometrics::BiometricsEngine;
use crate::shopify::ShopifyMembershipState;

static GLOBAL_BIOMETRICS: Lazy<Mutex<BiometricsEngine>> = Lazy::new(|| Mutex::new(BiometricsEngine::new(512.0)));
static SERVER_RUNNING: AtomicBool = AtomicBool::new(false);

#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PanTompkinsOutput {
    pub is_qrs_peak: bool,
    pub filtered_val: f32,
    pub integrated_val: f32,
    pub heart_rate_bpm: f32,
    pub rr_interval_ms: f32,
    pub rmssd_ms: f32,
    pub sdnn_ms: f32,
    pub pnn50_percent: f32,
}

#[no_mangle]
pub extern "C" fn lauburu_core_init() -> i32 {
    let mut engine = GLOBAL_BIOMETRICS.lock();
    engine.detector.reset();
    0 // SUCCESS
}

#[no_mangle]
pub extern "C" fn lauburu_process_ecg_sample(raw_sample: f32) -> PanTompkinsOutput {
    let mut engine = GLOBAL_BIOMETRICS.lock();
    let res = engine.ingest_sample(raw_sample);
    PanTompkinsOutput {
        is_qrs_peak: res.is_qrs_peak,
        filtered_val: res.filtered_val,
        integrated_val: res.integrated_val,
        heart_rate_bpm: res.heart_rate_bpm,
        rr_interval_ms: res.rr_interval_ms,
        rmssd_ms: res.rmssd_ms,
        sdnn_ms: res.sdnn_ms,
        pnn50_percent: res.pnn50_percent,
    }
}

#[no_mangle]
pub extern "C" fn lauburu_get_readiness_score() -> f32 {
    let engine = GLOBAL_BIOMETRICS.lock();
    engine.latest_snapshot.readiness_score
}

#[no_mangle]
pub extern "C" fn lauburu_get_hrv_rmssd() -> f32 {
    let engine = GLOBAL_BIOMETRICS.lock();
    engine.latest_snapshot.hrv_rmssd_ms
}

#[no_mangle]
pub extern "C" fn lauburu_get_dfa_alpha1() -> f32 {
    let engine = GLOBAL_BIOMETRICS.lock();
    engine.latest_snapshot.dfa_alpha1
}

#[no_mangle]
pub extern "C" fn lauburu_verify_shopify_tier(token_ptr: *const c_char) -> i32 {
    if token_ptr.is_null() {
        return 0; // Free
    }
    let c_str = unsafe { CStr::from_ptr(token_ptr) };
    let token = c_str.to_str().unwrap_or("");
    let (_tier, code) = ShopifyMembershipState::verify_token(token);
    code
}

#[no_mangle]
pub extern "C" fn lauburu_get_telemetry_json() -> *mut c_char {
    let engine = GLOBAL_BIOMETRICS.lock();
    let json_str = serde_json::to_string(&engine.latest_snapshot).unwrap_or_else(|_| "{}".to_string());
    let c_string = CString::new(json_str).unwrap_or_default();
    c_string.into_raw()
}

#[no_mangle]
pub extern "C" fn lauburu_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

#[no_mangle]
pub extern "C" fn lauburu_is_server_running() -> bool {
    SERVER_RUNNING.load(Ordering::SeqCst)
}
