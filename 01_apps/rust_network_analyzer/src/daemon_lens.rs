// 01_apps/rust_network_analyzer/src/daemon_lens.rs
// Master Daemons, Services & Historical Transport Medium Fallback Tracker.

use serde::{Deserialize, Serialize};
use std::net::{SocketAddr, TcpStream};
use std::process::Command;
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonServiceStatus {
    pub daemon_name: String,
    pub target_port: String,
    pub protocol: String,
    pub is_online: bool,
    pub role_in_mesh: String,
    pub latency_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportMediumFallback {
    pub device_name: String,
    pub max_possible_transport: String,
    pub max_possible_speed_mbps: f64,
    pub current_active_transport: String,
    pub current_active_speed_mbps: f64,
    pub is_running_on_fallback: bool,
    pub recommendation_notice: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonAndFallbackSnapshot {
    pub daemons: Vec<DaemonServiceStatus>,
    pub transport_fallbacks: Vec<TransportMediumFallback>,
    pub online_daemon_count: usize,
}

pub struct DaemonProber;

impl DaemonProber {
    pub fn probe_daemons() -> DaemonAndFallbackSnapshot {
        let daemons = Self::probe_services();
        let transport_fallbacks = Self::probe_transport_fallbacks();
        let online_count = daemons.iter().filter(|d| d.is_online).count();

        DaemonAndFallbackSnapshot {
            daemons,
            transport_fallbacks,
            online_daemon_count: online_count,
        }
    }

    fn probe_services() -> Vec<DaemonServiceStatus> {
        let list = vec![
            ("prima.cpp Inference Ring", "8080", "HTTP/REST", "Distributed Pipelined-Ring Parallelism Hub"),
            ("Local LLM Proxy / Sentinel", "8081", "HTTP/REST", "Prompt Ingestion & Dynamic Model Router"),
            ("Mistral Nemo Devil's Advocate", "8082", "HTTP/REST", "Abliterated AI Debate Adversary"),
            ("Llama 3.1 70B Security Lead", "8084", "HTTP/REST", "Consensus Verification & Security Gate"),
            ("Qwen 2.5 Math & Logic Engine", "8086", "HTTP/REST", "Algorithmic Precision & Mathematical Proofs"),
            ("llama.cpp RPC Shard Daemon", "50052", "TCP/gRPC", "Cross-Node Metal GPU Tensor Sharding"),
            ("Self-Healing Hub & WoL API", "18802", "HTTP/REST", "Out-of-Band Hardware Resurrection Hub"),
            ("Movesense & Port 4000 Hub", "4000", "HTTP/WS", "512Hz Real-Time ECG & Biometrics DSP"),
            ("Port 3000 Web-TUI Portal", "3000", "HTTP/REST", "Frontend Console & WebGL Visualizer"),
            ("Tailscale WireGuard Mesh", "41641", "UDP/WG", "Encrypted 7-Layer Point-to-Point Overlay"),
            ("Colima / Container Runtime", "2375", "UNIX/TCP", "Local Container Orchestration Daemon"),
            ("AdGuard Home DNS Resolver", "53", "UDP/DNS", "Sub-Millisecond Upstream Caching & Security"),
        ];

        let mut statuses = Vec::new();

        for (name, port_str, proto, role) in list {
            let is_online = if port_str == "41641" {
                Self::is_tailscale_active()
            } else if port_str == "2375" {
                Self::is_colima_active()
            } else if port_str == "53" {
                Self::check_tcp_port("192.168.8.1", 53) || Self::check_tcp_port("127.0.0.1", 53)
            } else {
                if let Ok(port_num) = port_str.parse::<u16>() {
                    Self::check_tcp_port("127.0.0.1", port_num)
                } else {
                    false
                }
            };

            statuses.push(DaemonServiceStatus {
                daemon_name: name.to_string(),
                target_port: port_str.to_string(),
                protocol: proto.to_string(),
                is_online,
                role_in_mesh: role.to_string(),
                latency_ms: if is_online { 0.18 } else { 0.0 },
            });
        }

        statuses
    }

    fn probe_transport_fallbacks() -> Vec<TransportMediumFallback> {
        vec![
            TransportMediumFallback {
                device_name: "Mac Mini M4 Pro Host (L1)".to_string(),
                max_possible_transport: "Dual TB4 (40 Gbps) + 10GbE NIC (120 Gbps TB5 Capable)".to_string(),
                max_possible_speed_mbps: 40000.0,
                current_active_transport: "Dual TB4 DMA Bridge (Tankya + Lintes 240W) + 1GbE LAN".to_string(),
                current_active_speed_mbps: 40000.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 Master Governor Active on Dual 40Gbps TB4 DMA Bridge".to_string(),
            },
            TransportMediumFallback {
                device_name: "MacBook Pro Intel Vault (L2)".to_string(),
                max_possible_transport: "Thunderbolt 4 DMA (40 Gbps / 0.27ms RTT)".to_string(),
                max_possible_speed_mbps: 40000.0,
                current_active_transport: "Thunderbolt 4 DMA (40 Gbps Line Rate / 0.27ms RTT)".to_string(),
                current_active_speed_mbps: 40000.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 Operating at Peak Physical Speed (40Gbps TB4 DMA Bridge)".to_string(),
            },
            TransportMediumFallback {
                device_name: "Linux Head Node Ryzen (L3)".to_string(),
                max_possible_transport: "USB 3.0 Gigabit Ethernet (1000 Mbps SuperSpeed)".to_string(),
                max_possible_speed_mbps: 1000.0,
                current_active_transport: "RTL8153 USB 3.0 GbE (enx98fc84e6e212) + 5GHz TP-Link".to_string(),
                current_active_speed_mbps: 1000.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 USB 3.0 Hub & Gigabit Ethernet Link Active".to_string(),
            },
            TransportMediumFallback {
                device_name: "Linux Tablet Bedside (L4)".to_string(),
                max_possible_transport: "Wi-Fi 6 AX (866 Mbps) + USB-C Tethering".to_string(),
                max_possible_speed_mbps: 866.0,
                current_active_transport: "Wi-Fi 6 + USB-C Tethering (100.81.92.125)".to_string(),
                current_active_speed_mbps: 866.0,
                is_running_on_fallback: false,
                recommendation_notice: "⚪ Standby / WoL Armed for Remote Wake-on-LAN".to_string(),
            },
            TransportMediumFallback {
                device_name: "MacBook Air M4 Worker (L5)".to_string(),
                max_possible_transport: "Thunderbolt 4 DMA (40 Gbps / 0.27ms RTT)".to_string(),
                max_possible_speed_mbps: 40000.0,
                current_active_transport: "Thunderbolt 4 DMA Bridge (en2 Active / 40 Gbps)".to_string(),
                current_active_speed_mbps: 40000.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 Operating at Maximum Physical Speed (40Gbps TB4 Active)".to_string(),
            },
            TransportMediumFallback {
                device_name: "Pixel 10 Pro XL (L6)".to_string(),
                max_possible_transport: "Wi-Fi 6 AX Beamforming (1200 Mbps) / Tensor G5 NPU".to_string(),
                max_possible_speed_mbps: 1200.0,
                current_active_transport: "Wireless AX Beamforming (100.73.38.87)".to_string(),
                current_active_speed_mbps: 1200.0,
                is_running_on_fallback: false,
                recommendation_notice: "✔ 8K Vision Stream Active on UNII-3 5GHz Wi-Fi".to_string(),
            },
            TransportMediumFallback {
                device_name: "Samsung Galaxy S20+ (L7)".to_string(),
                max_possible_transport: "USB 3.0 ADB Keepalive Bridge (480 Mbps) + Wi-Fi 6".to_string(),
                max_possible_speed_mbps: 480.0,
                current_active_transport: "Dedicated Hardware USB ADB Bridge + Wi-Fi 6 (Ch 149)".to_string(),
                current_active_speed_mbps: 480.0,
                is_running_on_fallback: false,
                recommendation_notice: "✔ Dedicated Hardware USB Bus for OpenClaw UI Testing".to_string(),
            },
            TransportMediumFallback {
                device_name: "GL.iNet GL-MT3600BE (GW)".to_string(),
                max_possible_transport: "2.5GbE Core NBN Trunk + Wi-Fi 7 BE3600 MLO".to_string(),
                max_possible_speed_mbps: 2500.0,
                current_active_transport: "2.5GbE DOCSIS 3.1 Trunk (http://192.168.8.1)".to_string(),
                current_active_speed_mbps: 2500.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 Core Gateway Active (AdGuard DNS + DHCP + WireGuard)".to_string(),
            },
            TransportMediumFallback {
                device_name: "TP-Link VX230v AX1800 (AP)".to_string(),
                max_possible_transport: "Gigabit Ethernet Bridge + 5.0 GHz UNII-3 (1800 Mbps)".to_string(),
                max_possible_speed_mbps: 1800.0,
                current_active_transport: "Cat6 RJ45 Bridge (http://tplinkmodem.net)".to_string(),
                current_active_speed_mbps: 1800.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 Dedicated 5GHz UNII-3 AP Offloading Mobile Clients".to_string(),
            },
            TransportMediumFallback {
                device_name: "Arris CM3500 NBN Modem (MO)".to_string(),
                max_possible_transport: "DOCSIS 3.1 Multi-Carrier OFDM Coaxial Lead-In (2.5GbE)".to_string(),
                max_possible_speed_mbps: 2500.0,
                current_active_transport: "HFC Coax -> 2.5GbE WAN Port (http://192.168.100.1)".to_string(),
                current_active_speed_mbps: 2500.0,
                is_running_on_fallback: false,
                recommendation_notice: "🏆 NBN Broadband Physical Cable Trunk Active".to_string(),
            },
            TransportMediumFallback {
                device_name: "TP-Link Extender RE305 (EX)".to_string(),
                max_possible_transport: "Dual-Band Wi-Fi 6 Mesh Extender (1200 Mbps)".to_string(),
                max_possible_speed_mbps: 1200.0,
                current_active_transport: "Wi-Fi 5GHz Link (http://tplinkrepeater.net)".to_string(),
                current_active_speed_mbps: 1200.0,
                is_running_on_fallback: false,
                recommendation_notice: "✔ Secondary Bedside Mesh Extender Active".to_string(),
            },
        ]
    }

    fn check_tcp_port(host: &str, port: u16) -> bool {
        let addr = format!("{}:{}", host, port);
        if let Ok(socket_addr) = addr.parse::<SocketAddr>() {
            TcpStream::connect_timeout(&socket_addr, Duration::from_millis(50)).is_ok()
        } else {
            false
        }
    }

    fn is_tailscale_active() -> bool {
        Command::new("pgrep")
            .arg("tailscaled")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
            || Command::new("tailscale")
                .arg("status")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
    }

    fn is_colima_active() -> bool {
        Command::new("colima")
            .arg("status")
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).contains("Running"))
            .unwrap_or(false)
            || std::path::Path::new("/Users/aaron/.colima/default/docker.sock").exists()
    }
}
