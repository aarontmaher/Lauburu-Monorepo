#![allow(dead_code)]
use serde::{Deserialize, Serialize};

pub const DEFAULT_PORT: u16 = 18804;
pub const DEFAULT_SOCKS5_PORT: u16 = 1080;
pub const TUN_STREAM_ID: u8 = 1;
pub const SOCKS5_STREAM_ID: u8 = 2;
pub const TELEMETRY_STREAM_ID: u8 = 3;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinkTelemetry {
    pub link_id: usize,
    pub local_addr: String,
    pub remote_addr: String,
    pub rtt_ms: f64,
    pub send_kbps: f64,
    pub recv_kbps: f64,
    pub is_working: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineTelemetryReport {
    pub session_id: String,
    pub active_links_count: usize,
    pub total_send_kbps: f64,
    pub total_recv_kbps: f64,
    pub links: Vec<LinkTelemetry>,
}
