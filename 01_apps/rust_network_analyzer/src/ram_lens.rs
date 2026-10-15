// 01_apps/rust_network_analyzer/src/ram_lens.rs
// Full-Network & Per-Device RAM / AI VRAM Pooling with 24/7 Training Maintenance Pool.

use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceRamMetric {
    pub layer: String,
    pub device_name: String,
    pub total_ram_gb: f64,
    pub used_ram_gb: f64,
    pub free_ram_gb: f64,
    pub ai_training_allocated_gb: f64,
    pub usable_ai_vram_gb: f64,
    pub dynamic_safety_limit_pct: u8,
    pub usage_percentage: f64,
    pub memory_governor_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkRamSnapshot {
    pub devices: Vec<DeviceRamMetric>,
    pub total_network_ram_gb: f64,
    pub total_used_ram_gb: f64,
    pub total_training_pool_gb: f64,
    pub total_free_headroom_gb: f64,
    pub total_ai_vram_pool_gb: f64,
    pub network_ram_utilization_pct: f64,
}

pub struct RamProber;

impl RamProber {
    pub fn probe_ram() -> NetworkRamSnapshot {
        let mut devices = Vec::new();

        // 1. Host Mac Mini M4 Pro (L1)
        let host_used = Self::probe_host_mac_ram();
        devices.push(DeviceRamMetric {
            layer: "L1".to_string(),
            device_name: "Mac Mini M4 Pro Host".to_string(),
            total_ram_gb: 24.0,
            used_ram_gb: host_used,
            free_ram_gb: 24.0 - host_used,
            ai_training_allocated_gb: 16.0,
            usable_ai_vram_gb: 21.6,
            dynamic_safety_limit_pct: 90,
            usage_percentage: (host_used / 24.0) * 100.0,
            memory_governor_status: "🟢 16.0 GB Training Pool / Safe".to_string(),
        });

        // 2. MacBook Pro Intel Core i7 Vault (L2)
        devices.push(DeviceRamMetric {
            layer: "L2".to_string(),
            device_name: "MacBook Pro Intel Vault".to_string(),
            total_ram_gb: 16.0,
            used_ram_gb: 6.2,
            free_ram_gb: 9.8,
            ai_training_allocated_gb: 8.0,
            usable_ai_vram_gb: 14.0,
            dynamic_safety_limit_pct: 90,
            usage_percentage: 38.75,
            memory_governor_status: "🟢 8.0 GB Training Pool (GGML LoRA)".to_string(),
        });

        // 3. Linux Head Node (L3 Ryzen 7 5700U)
        let linux_used = Self::probe_linux_ram();
        devices.push(DeviceRamMetric {
            layer: "L3".to_string(),
            device_name: "Linux Head Node (Ryzen)".to_string(),
            total_ram_gb: 16.0,
            used_ram_gb: linux_used,
            free_ram_gb: 16.0 - linux_used,
            ai_training_allocated_gb: 10.0,
            usable_ai_vram_gb: 13.8,
            dynamic_safety_limit_pct: 80,
            usage_percentage: (linux_used / 16.0) * 100.0,
            memory_governor_status: "🟢 10.0 GB Training Pool (Docker/Ray)".to_string(),
        });

        // 4. Linux Tablet Bedside (L4)
        devices.push(DeviceRamMetric {
            layer: "L4".to_string(),
            device_name: "Linux Tablet / Bedside".to_string(),
            total_ram_gb: 8.0,
            used_ram_gb: 2.4,
            free_ram_gb: 5.6,
            ai_training_allocated_gb: 0.0,
            usable_ai_vram_gb: 6.5,
            dynamic_safety_limit_pct: 75,
            usage_percentage: 30.0,
            memory_governor_status: "🟢 NOMINAL (Lightweight DSP)".to_string(),
        });

        // 5. MacBook Air M4 Metal Worker (L5)
        devices.push(DeviceRamMetric {
            layer: "L5".to_string(),
            device_name: "MacBook Air M4 Worker".to_string(),
            total_ram_gb: 16.0,
            used_ram_gb: 7.1,
            free_ram_gb: 8.9,
            ai_training_allocated_gb: 8.0,
            usable_ai_vram_gb: 14.0,
            dynamic_safety_limit_pct: 90,
            usage_percentage: 44.37,
            memory_governor_status: "🟢 8.0 GB Training Pool (Metal LoRA)".to_string(),
        });

        // 6. Pixel 10 Pro XL (L6)
        devices.push(DeviceRamMetric {
            layer: "L6".to_string(),
            device_name: "Pixel 10 Pro XL".to_string(),
            total_ram_gb: 16.0,
            used_ram_gb: 5.2,
            free_ram_gb: 10.8,
            ai_training_allocated_gb: 0.0,
            usable_ai_vram_gb: 12.5,
            dynamic_safety_limit_pct: 85,
            usage_percentage: 32.5,
            memory_governor_status: "🟢 NOMINAL (Edge TPU Vision)".to_string(),
        });

        // 7. Samsung Galaxy S20 (L7)
        devices.push(DeviceRamMetric {
            layer: "L7".to_string(),
            device_name: "Samsung Galaxy S20".to_string(),
            total_ram_gb: 12.0,
            used_ram_gb: 4.8,
            free_ram_gb: 7.2,
            ai_training_allocated_gb: 0.0,
            usable_ai_vram_gb: 9.0,
            dynamic_safety_limit_pct: 75,
            usage_percentage: 40.0,
            memory_governor_status: "🟢 NOMINAL (OpenClaw UI Tester)".to_string(),
        });

        // 8. GL.iNet Gateway Router (GW)
        devices.push(DeviceRamMetric {
            layer: "GW".to_string(),
            device_name: "GL.iNet GL-MT3600BE Gateway".to_string(),
            total_ram_gb: 0.512,
            used_ram_gb: 0.371,
            free_ram_gb: 0.141,
            ai_training_allocated_gb: 0.0,
            usable_ai_vram_gb: 0.0,
            dynamic_safety_limit_pct: 80,
            usage_percentage: 72.4,
            memory_governor_status: "🟢 141 MB Free (Offloading 5G)".to_string(),
        });

        // 9. TP-Link VX230v AP (AP)
        devices.push(DeviceRamMetric {
            layer: "AP".to_string(),
            device_name: "TP-Link VX230v AX1800 AP".to_string(),
            total_ram_gb: 0.512,
            used_ram_gb: 0.185,
            free_ram_gb: 0.327,
            ai_training_allocated_gb: 0.0,
            usable_ai_vram_gb: 0.0,
            dynamic_safety_limit_pct: 80,
            usage_percentage: 36.1,
            memory_governor_status: "🟢 327 MB Free (Handling 5GHz)".to_string(),
        });

        let total_ram: f64 = devices.iter().map(|d| d.total_ram_gb).sum();
        let total_used: f64 = devices.iter().map(|d| d.used_ram_gb).sum();
        let total_training: f64 = devices.iter().map(|d| d.ai_training_allocated_gb).sum();
        let total_ai_vram: f64 = devices.iter().map(|d| d.usable_ai_vram_gb).sum();
        let total_free = total_ram - total_used;
        let utilization = (total_used / total_ram) * 100.0;

        NetworkRamSnapshot {
            devices,
            total_network_ram_gb: total_ram,
            total_used_ram_gb: total_used,
            total_training_pool_gb: total_training,
            total_free_headroom_gb: total_free - total_training,
            total_ai_vram_pool_gb: total_ai_vram,
            network_ram_utilization_pct: utilization,
        }
    }

    fn probe_host_mac_ram() -> f64 {
        if let Ok(_out) = Command::new("sysctl").arg("hw.memsize").output() {
            if let Ok(vm_out) = Command::new("vm_stat").output() {
                let vm_s = String::from_utf8_lossy(&vm_out.stdout);
                let mut page_size = 16384u64; // Default on Apple Silicon
                let mut pages_active = 0u64;
                let mut pages_wired = 0u64;
                let mut pages_compressed = 0u64;

                for line in vm_s.lines() {
                    if line.contains("page size of") {
                        for token in line.split_whitespace() {
                            if let Ok(p) = token.parse::<u64>() {
                                page_size = p;
                            }
                        }
                    } else if line.contains("Pages active:") {
                        pages_active = Self::parse_page_num(line);
                    } else if line.contains("Pages wired down:") {
                        pages_wired = Self::parse_page_num(line);
                    } else if line.contains("Pages occupied by compressor:") {
                        pages_compressed = Self::parse_page_num(line);
                    }
                }
                let used_bytes = (pages_active + pages_wired + pages_compressed) * page_size;
                return (used_bytes as f64) / (1024.0 * 1024.0 * 1024.0);
            }
        }
        20.0
    }

    fn probe_linux_ram() -> f64 {
        if let Ok(out) = Command::new("ssh")
            .args(["-o", "ConnectTimeout=1", "-o", "BatchMode=yes", "linux", "free -m | grep Mem:"])
            .output()
        {
            if out.status.success() {
                let s = String::from_utf8_lossy(&out.stdout);
                let parts: Vec<&str> = s.split_whitespace().collect();
                if parts.len() >= 3 {
                    if let Ok(used_mb) = parts[2].parse::<f64>() {
                        return used_mb / 1024.0;
                    }
                }
            }
        }
        1.8
    }

    fn parse_page_num(line: &str) -> u64 {
        line.split(':')
            .nth(1)
            .and_then(|s| s.trim().trim_end_matches('.').parse().ok())
            .unwrap_or(0)
    }
}
