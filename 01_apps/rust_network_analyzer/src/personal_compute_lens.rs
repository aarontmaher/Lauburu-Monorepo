// 01_apps/rust_network_analyzer/src/personal_compute_lens.rs
// "Paying by Computing" Decentralized Micro-Contribution Ledger & Tenant-Isolated Personal Swarm.

use std::process::Command;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct PersonalComputeSnapshot {
    pub device_name: String,
    pub os_and_arch: String,
    pub compute_accelerator: String,
    pub local_ip: String,
    pub cpu_cores: usize,
    pub cpu_usage_pct: f32,
    pub local_ram_gb: f32,
    pub used_ram_gb: f32,
    pub power_source: String,
    pub battery_pct: Option<u8>,
    
    // "Paying by Computing" Financial & Micro-Billing Engine
    pub compute_sharing_active: bool,
    pub subscription_tier: String,
    pub monthly_fee_waived_usd: f32,
    pub tokens_served_today: u64,
    pub flop_hours_contributed: f64,
    pub compute_credits_balance: f32,
    pub throttle_status: String,

    // My Paired Personal Swarm (Tenant Isolated)
    pub personal_devices: Vec<PersonalDevice>,
}

#[derive(Debug, Clone)]
pub struct PersonalDevice {
    pub name: String,
    pub role: String,
    pub ip: String,
    pub status: String,
    pub rtt_ms: f32,
    pub compute_cap: String,
}

pub struct PersonalComputeProber;

impl PersonalComputeProber {
    pub fn probe() -> PersonalComputeSnapshot {
        let hostname = Self::get_hostname();
        let (os_arch, accelerator) = Self::get_system_info();
        let (total_ram, used_ram) = Self::get_memory();
        let (power_src, battery) = Self::get_power();
        let local_ip = Self::get_local_ip();

        let personal_devices = vec![
            PersonalDevice {
                name: format!("💻 {}", hostname),
                role: "Primary Personal Workstation".to_string(),
                ip: local_ip.clone(),
                status: "🟢 Local Active".to_string(),
                rtt_ms: 0.04,
                compute_cap: format!("{:.0} GB RAM ({})", total_ram, accelerator),
            },
            PersonalDevice {
                name: "📱 Google Pixel 10 Pro XL".to_string(),
                role: "Personal Mobile Companion".to_string(),
                ip: "100.73.38.87".to_string(),
                status: "🟢 Connected (Tailscale WireGuard)".to_string(),
                rtt_ms: 171.0,
                compute_cap: "16.0 GB RAM (Google Tensor G5 Edge TPU)".to_string(),
            },
        ];

        PersonalComputeSnapshot {
            device_name: hostname,
            os_and_arch: os_arch,
            compute_accelerator: accelerator,
            local_ip,
            cpu_cores: num_cpus(),
            cpu_usage_pct: 18.5,
            local_ram_gb: total_ram,
            used_ram_gb: used_ram,
            power_source: power_src,
            battery_pct: battery,
            compute_sharing_active: true,
            subscription_tier: "⭐ Pro Suite ($29/mo Value)".to_string(),
            monthly_fee_waived_usd: 29.00,
            tokens_served_today: 48_210,
            flop_hours_contributed: 14.82,
            compute_credits_balance: 14.82,
            throttle_status: "Adaptive (Auto-scales down during interactive typing)".to_string(),
            personal_devices,
        }
    }

    fn get_hostname() -> String {
        if let Ok(out) = Command::new("hostname").output() {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !s.is_empty() {
                return s;
            }
        }
        "My-Personal-Device".to_string()
    }

    fn get_system_info() -> (String, String) {
        #[cfg(target_os = "macos")]
        {
            let os_arch = "macOS Sequoia (Darwin 24 / Apple Silicon)".to_string();
            let accelerator = "Apple Metal Performance Shaders (MPS / ANE)".to_string();
            (os_arch, accelerator)
        }
        #[cfg(target_os = "linux")]
        {
            let os_arch = "Linux 6.x (x86_64 / aarch64)".to_string();
            let accelerator = "Vulkan / CPU AVX2 Vector Kernels".to_string();
            (os_arch, accelerator)
        }
        #[cfg(not(any(target_os = "macos", target_os = "linux")))]
        {
            ("Generic OS".to_string(), "Standard CPU".to_string())
        }
    }

    fn get_memory() -> (f32, f32) {
        #[cfg(target_os = "macos")]
        {
            (24.0, 16.2)
        }
        #[cfg(target_os = "linux")]
        {
            (16.0, 6.8)
        }
        #[cfg(not(any(target_os = "macos", target_os = "linux")))]
        {
            (16.0, 8.0)
        }
    }

    fn get_power() -> (String, Option<u8>) {
        #[cfg(target_os = "macos")]
        {
            ("AC Power (Mains Connected)".to_string(), None)
        }
        #[cfg(target_os = "linux")]
        {
            ("AC Power Adapter".to_string(), Some(100))
        }
        #[cfg(not(any(target_os = "macos", target_os = "linux")))]
        {
            ("AC Mains".to_string(), None)
        }
    }

    fn get_local_ip() -> String {
        if let Ok(out) = Command::new("sh").arg("-c").arg("ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || route get 1.1.1.1 2>/dev/null | grep interface | awk '{print $2}'").output() {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !s.is_empty() {
                return s;
            }
        }
        "127.0.0.1".to_string()
    }
}

fn num_cpus() -> usize {
    #[cfg(target_os = "macos")]
    {
        if let Ok(out) = Command::new("sysctl").arg("-n").arg("hw.ncpu").output() {
            if let Ok(n) = String::from_utf8_lossy(&out.stdout).trim().parse::<usize>() {
                return n;
            }
        }
    }
    8
}
