// config.rs — Cluster topology configuration for prima.cpp ring
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeSpec {
    pub rank: usize,
    pub name: String,
    pub host: String,         // IP or hostname
    pub port: u16,            // llama-server port (rank 0 only, workers = 0)
    pub ssh_user: Option<String>,
    pub ssh_port: u16,
    pub model_path: String,
    pub gpu_mem_gb: Option<f32>,
    pub is_master: bool,
    pub role: String,         // "mac_mini", "mbp", "linux", "pixel", "samsung"
    pub transport: String,    // "TB4", "LAN", "Tailscale"
    pub tailscale_ip: Option<String>,
}

impl NodeSpec {
    /// URL for health checks (only master has HTTP server)
    pub fn health_url(&self) -> Option<String> {
        if self.is_master || self.port > 0 {
            Some(format!("http://{}:{}/health", self.host, self.port))
        } else {
            None
        }
    }

    pub fn chat_url(&self) -> Option<String> {
        if self.is_master || self.port > 0 {
            Some(format!("http://{}:{}/v1/chat/completions", self.host, self.port))
        } else {
            None
        }
    }

    /// prima.cpp start command for this node
    pub fn prima_cmd(&self, world: usize, next_ip: &str, master_ip: &str) -> String {
        let bin = if self.is_master { "llama-server" } else { "llama-cli" };
        let mut cmd = format!(
            "{} -m {} --world {} --rank {} --master {} --next {} --prefetch",
            bin, self.model_path, world, self.rank, master_ip, next_ip
        );
        if self.is_master {
            cmd.push_str(&format!(" --host 0.0.0.0 --port {} -np 4 --cont-batching", self.port));
        }
        if let Some(gpu) = self.gpu_mem_gb {
            cmd.push_str(&format!(" -ngl {} --gpu-mem {}", (gpu * 4.0) as u32, gpu));
        }
        cmd
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterConfig {
    pub cluster_name: String,
    pub master_url: String,
    pub world_size: usize,
    pub model_name: String,
    pub nodes: Vec<NodeSpec>,
    /// Comparison framework endpoints
    pub frameworks: Vec<FrameworkConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrameworkConfig {
    pub name: String,
    pub url: String,
    pub transport: String,
    pub description: String,
}

/// Load cluster config — uses lauburu mesh topology
pub fn load_cluster_config() -> ClusterConfig {
    // Try loading from file first
    let config_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/prima_tui/cluster.json";
    if Path::new(config_path).exists() {
        if let Ok(content) = std::fs::read_to_string(config_path) {
            if let Ok(cfg) = serde_json::from_str::<ClusterConfig>(&content) {
                return cfg;
            }
        }
    }

    // Default Lauburu mesh topology (Full 7-Layer Physical Mesh)
    ClusterConfig {
        cluster_name: "Lauburu Mesh prima.cpp Ring".to_string(),
        master_url: "http://127.0.0.1:9000".to_string(),
        world_size: 7,
        model_name: "Qwen3.8-Max-Abliterated Q4_K_XL".to_string(),
        nodes: vec![
            NodeSpec {
                rank: 0,
                name: "L1: Mac Mini M4 Pro (Host)".to_string(),
                host: "127.0.0.1".to_string(),
                port: 9000,
                ssh_user: Some("aaron".to_string()),
                ssh_port: 22,
                model_path: "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf".to_string(),
                gpu_mem_gb: Some(18.0),
                is_master: true,
                role: "mac_mini".to_string(),
                transport: "TB4 DMA".to_string(),
                tailscale_ip: Some("100.119.199.76".to_string()),
            },
            NodeSpec {
                rank: 1,
                name: "L2: MacBook Pro Intel Vault".to_string(),
                host: "192.168.8.127".to_string(),
                port: 0,
                ssh_user: Some("aaronmaher".to_string()),
                ssh_port: 22,
                model_path: "/Users/aaronmaher/prima_models/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf".to_string(),
                gpu_mem_gb: Some(14.0),
                is_master: false,
                role: "mbp".to_string(),
                transport: "TB4 DMA".to_string(),
                tailscale_ip: Some("100.103.212.21".to_string()),
            },
            NodeSpec {
                rank: 2,
                name: "L3: Linux Head Node".to_string(),
                host: "192.168.8.224".to_string(),
                port: 0,
                ssh_user: Some("linux".to_string()),
                ssh_port: 22,
                model_path: "/home/linux/gguf_vault/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf".to_string(),
                gpu_mem_gb: None,
                is_master: false,
                role: "linux".to_string(),
                transport: "LAN 1Gbps".to_string(),
                tailscale_ip: Some("100.101.39.98".to_string()),
            },
            NodeSpec {
                rank: 3,
                name: "L4: Linux Tablet".to_string(),
                host: "100.81.92.125".to_string(),
                port: 0,
                ssh_user: Some("linux".to_string()),
                ssh_port: 22,
                model_path: "/home/linux/models/SmolLM2-135M-Instruct.Q4_K_M.gguf".to_string(),
                gpu_mem_gb: None,
                is_master: false,
                role: "tablet".to_string(),
                transport: "Tailscale WireGuard".to_string(),
                tailscale_ip: Some("100.81.92.125".to_string()),
            },
            NodeSpec {
                rank: 4,
                name: "L5: MacBook Air M4".to_string(),
                host: "192.168.8.222".to_string(),
                port: 0,
                ssh_user: Some("aaron".to_string()),
                ssh_port: 22,
                model_path: "/Users/aaron/models/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf".to_string(),
                gpu_mem_gb: Some(14.0),
                is_master: false,
                role: "macbook_air".to_string(),
                transport: "TB4 DMA".to_string(),
                tailscale_ip: Some("100.121.202.34".to_string()),
            },
            NodeSpec {
                rank: 5,
                name: "L6: Pixel 10 Pro XL".to_string(),
                host: "100.73.38.87".to_string(),
                port: 0,
                ssh_user: Some("u0_a234".to_string()),
                ssh_port: 8022,
                model_path: "/data/data/com.termux/files/home/prima_models/SmolLM2-135M-Instruct.Q4_K_M.gguf".to_string(),
                gpu_mem_gb: None,
                is_master: false,
                role: "pixel".to_string(),
                transport: "Wi-Fi 7".to_string(),
                tailscale_ip: Some("100.73.38.87".to_string()),
            },
            NodeSpec {
                rank: 6,
                name: "L7: Samsung S20+".to_string(),
                host: "100.84.40.95".to_string(),
                port: 0,
                ssh_user: Some("u0_a123".to_string()),
                ssh_port: 8022,
                model_path: "/data/data/com.termux/files/home/prima_models/SmolLM2-135M-Instruct.Q4_K_M.gguf".to_string(),
                gpu_mem_gb: None,
                is_master: false,
                role: "samsung".to_string(),
                transport: "Wi-Fi 6 / USB ADB".to_string(),
                tailscale_ip: Some("100.84.40.95".to_string()),
            },
        ],
        frameworks: vec![
            FrameworkConfig {
                name: "prima.cpp PRP".to_string(),
                url: "http://127.0.0.1:9000".to_string(),
                transport: "PRP Ring (7 nodes)".to_string(),
                description: "Pipelined-Ring Parallelism, Halda scheduler".to_string(),
            },
            FrameworkConfig {
                name: "llama.cpp TB4".to_string(),
                url: "http://127.0.0.1:8091".to_string(),
                transport: "TB4 DMA 0.52ms".to_string(),
                description: "2-node RPC shard via Thunderbolt 4".to_string(),
            },
            FrameworkConfig {
                name: "HF Accelerate".to_string(),
                url: "http://127.0.0.1:8094".to_string(),
                transport: "Tailscale 4-node".to_string(),
                description: "FSDP distributed training/inference".to_string(),
            },
            FrameworkConfig {
                name: "Exo P2P".to_string(),
                url: "http://127.0.0.1:8888".to_string(),
                transport: "Tailscale P2P".to_string(),
                description: "Decentralized peer-to-peer sharding".to_string(),
            },
            FrameworkConfig {
                name: "Petals DHT".to_string(),
                url: "http://192.168.8.224:8080".to_string(),
                transport: "DHT (Linux host)".to_string(),
                description: "Bittorrent-style distributed inference".to_string(),
            },
        ],
    }
}
