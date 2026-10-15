//! Lauburu Port 4000 Core Library Engine.
//! High-performance Rust backend providing Biometrics DSP, Pan-Tompkins QRS, Movesense BLE,
//! 3D Spatial Grappling Kinematics, Shopify Membership validation, Axum/Tokio HTTP/WebSocket server,
//! and Flutter Rust Bridge C-FFI exports.

pub mod dsp;
pub mod biometrics;
pub mod spatial;
pub mod shopify;
pub mod bridge;
pub mod server;
pub mod ide_engine;
pub mod npu_analysis;

pub use dsp::{PanTompkinsDetector, DfaCalculator, QrsDetectionResult};
pub use biometrics::{BiometricsEngine, BiometricTelemetrySnapshot};
pub use spatial::{SpatialKinematicsEngine, SpatialGrapplingState, Landmark3D, JointAngleTorque};
pub use shopify::{ShopifyMembershipState, MembershipTier};
pub use bridge::*;
pub use server::{run_server, create_router, AppState};
pub use ide_engine::*;
pub use npu_analysis::*;
