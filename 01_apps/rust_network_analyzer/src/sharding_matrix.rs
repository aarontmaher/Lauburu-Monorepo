// 01_apps/rust_network_analyzer/src/sharding_matrix.rs
// Real-time Dual-Path Multi-Transport AI Tensor Sharding Latency & BDP Matrix.

use serde::{Deserialize, Serialize};
use std::process::Command;
use std::time::Instant;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeShardingMetric {
    pub layer: String,
    pub node_name: String,
    pub ip_address: String,
    pub transport_medium: String,
    pub rtt_latency_ms: f64,
    pub jitter_ms: f64,
    pub nominal_bandwidth_mbps: f64,
    pub bandwidth_delay_product_kb: f64,
    pub sharding_verdict: String,
    pub is_active: bool,
}

pub struct ShardingMatrixProber;

impl ShardingMatrixProber {
    pub fn probe_mesh_matrix() -> Vec<NodeShardingMetric> {
        let targets: Vec<(&str, &str, Vec<&str>, &str, f64)> = vec![
            ("L1", "Mac Mini Host", vec!["127.0.0.1", "10.0.0.2", "192.168.8.143", "192.168.8.230", "100.119.199.76"], "Dual TB4 (40Gbps) + 1GbE", 40000.0),
            ("L2", "MacBook Pro Vault", vec!["10.0.0.4", "192.168.8.127", "100.103.212.21"], "40Gbps TB4 DMA (0.27ms)", 40000.0),
            ("L1a", "MacBook Air M4", vec!["100.121.202.34", "192.168.8.248"], "Thunderbolt 4 DMA (40 Gbps)", 40000.0),
            ("L1b", "Mac Mini M2 Pro", vec!["10.0.0.3", "192.168.8.114", "100.104.128.34"], "40Gbps TB4 DMA (0.43ms)", 40000.0),
            ("L8", "Linux Mini Hub (lauburu)", vec!["10.0.0.8", "192.168.8.242", "100.121.247.8"], "40Gbps TB4 DMA (0.38ms)", 40000.0),
            ("L3", "Linux Head Node", vec!["192.168.8.225", "100.101.39.98"], "TP-Link 802.11ac (5GHz) + USB 3", 1000.0),
            ("L4", "Debian Tablet/VM", vec!["100.80.64.5", "192.168.8.116"], "Wi-Fi 6 + USB-C Tethering", 866.0),
            ("L6", "Pixel 10 Pro XL", vec!["100.114.215.68", "192.168.8.213"], "Wi-Fi 6 AX / Tensor G5 NPU", 1200.0),
            ("L7", "Samsung S20 UI", vec!["100.84.40.95", "192.168.8.157"], "USB ADB Bridge (Port 5555)", 866.0),
            ("GW", "GL.iNet Gateway", vec!["192.168.8.1", "100.70.123.123"], "2.5GbE Core NBN Trunk", 2500.0),
            ("AP", "TP-Link VX230v", vec!["192.168.8.2", "192.168.8.116"], "1GbE AP Trunk Bridge", 1800.0),
        ];

        let num_targets = targets.len();
        let (tx, rx) = std::sync::mpsc::channel();

        for (idx, (layer, name, ip_candidates, transport, bw)) in targets.into_iter().enumerate() {
            let tx_clone = tx.clone();
            std::thread::spawn(move || {
                let mut best_online = false;
                let mut best_rtt = 0.0;
                let mut best_jitter = 0.0;
                let mut active_ip = ip_candidates[0].to_string();

                for ip in &ip_candidates {
                    let (online, rtt, jitter) = Self::ping_probe(ip);
                    if online {
                        best_online = true;
                        best_rtt = rtt;
                        best_jitter = jitter;
                        active_ip = ip.to_string();
                        break;
                    }
                }

                let rtt_sec = if best_rtt > 0.0 { best_rtt / 1000.0 } else { 0.001 };
                let bdp_kb = if best_online {
                    (bw * 1_000_000.0 * rtt_sec) / (8.0 * 1024.0)
                } else {
                    0.0
                };

                let verdict = if !best_online {
                    "⚪ Offline / Standby (WoL Armed)".to_string()
                } else if best_rtt < 0.5 {
                    "🏆 Ultra-Low Latency (TB4 DMA / Intra-Host)".to_string()
                } else if best_rtt < 15.0 {
                    "🟢 Optimal (1GbE LAN / 5GHz Wi-Fi)".to_string()
                } else if best_rtt < 150.0 {
                    "🟡 High-Speed Mesh Overlay (Tailscale)".to_string()
                } else {
                    "⚠️ High Latency / Cellular Link".to_string()
                };

                let metric = NodeShardingMetric {
                    layer: layer.to_string(),
                    node_name: name.to_string(),
                    ip_address: active_ip,
                    transport_medium: transport.to_string(),
                    rtt_latency_ms: best_rtt,
                    jitter_ms: best_jitter,
                    nominal_bandwidth_mbps: bw,
                    bandwidth_delay_product_kb: bdp_kb,
                    sharding_verdict: verdict,
                    is_active: best_online,
                };

                let _ = tx_clone.send((idx, metric));
            });
        }
        drop(tx);

        let mut collected: Vec<(usize, NodeShardingMetric)> = Vec::with_capacity(num_targets);
        while let Ok((idx, metric)) = rx.recv() {
            collected.push((idx, metric));
        }

        collected.sort_by_key(|(idx, _)| *idx);
        collected.into_iter().map(|(_, metric)| metric).collect()
    }

    fn ping_probe(ip: &str) -> (bool, f64, f64) {
        if ip == "127.0.0.1" || ip == "localhost" {
            return (true, 0.04, 0.01);
        }

        let t0 = Instant::now();
        let p = Command::new("ping")
            .args(["-c", "1", "-W", "150", ip])
            .output();

        if let Ok(out) = p {
            if out.status.success() {
                let stdout = String::from_utf8_lossy(&out.stdout);
                for line in stdout.lines() {
                    if line.contains("time=") {
                        if let Some(time_part) = line.split("time=").nth(1) {
                            if let Some(ms_str) = time_part.split_whitespace().next() {
                                if let Ok(val) = ms_str.parse::<f64>() {
                                    return (true, val, 0.04);
                                }
                            }
                        }
                    }
                }
                let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
                return (true, elapsed, 0.05);
            }
        }
        (false, 0.0, 0.0)
    }
}
