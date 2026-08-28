"""
Canonical Port Test Suite — conftest.py
Authoritative fixtures, interface contracts, and validation utilities for 4-Tier E2E Testing.
Derived strictly from ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md.
"""

import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import time
import tempfile
import asyncio
from typing import Dict, List, Any, Optional

@pytest.fixture(autouse=True)
def clean_blackboard_state_files():
    """Ensure blackboard state disk files and singleton caches are clean before each test."""
    for f in ["blackboard_state.json", "blackboard_state.yaml"]:
        if os.path.isfile(f):
            try:
                os.remove(f)
            except Exception:
                pass
    try:
        from tui.services.blackboard_store import blackboard_store
        with blackboard_store._lock:
            blackboard_store._last_snapshot = None
            blackboard_store._voice_cache = None
            blackboard_store._tb4_cache = None
            blackboard_store._ts_cache = None
            blackboard_store._bio_cache = None
            blackboard_store._ip_cache = None
    except Exception:
        pass
    yield
    for f in ["blackboard_state.json", "blackboard_state.yaml"]:
        if os.path.isfile(f):
            try:
                os.remove(f)
            except Exception:
                pass

@pytest.fixture
def canonical_routes() -> List[str]:
    """Authoritative list of 11 primary view routes per PROJECT.md interface contract."""
    return [
        "governance",
        "network-metrics",
        "optimization-hardware",
        "optimization-software",
        "optimization-internet",
        "optimization-storage",
        "training-lora",
        "training-games",
        "training-metrics",
        "training-traces",
        "leaderboard"
    ]

@pytest.fixture
def network_metrics_snapshot() -> Dict[str, Any]:
    """Authoritative Network Telemetry Snapshot fixture matching 8-node topology, probes, and Port 50052 RPC."""
    return {
        "timestamp": "08:00:00",
        "mac_mini_ip": "192.168.8.230",
        "wan_routes": [
            {"interface": "en0_wifi_wan", "status": "ACTIVE", "rtt_ms": 1.84, "drop_rate": 0.0, "circuit_state": "CLOSED", "bandwidth": "2.4 Gbps (Wi-Fi 7 MLO)", "priority": "P1"},
            {"interface": "en6_usb_tether", "status": "STANDBY", "rtt_ms": 24.5, "drop_rate": 0.0, "circuit_state": "CLOSED", "bandwidth": "120 Mbps (5G Hotspot)", "priority": "P3"},
            {"interface": "utun1_tailscale", "status": "ACTIVE", "rtt_ms": 4.12, "drop_rate": 0.0, "circuit_state": "CLOSED", "bandwidth": "1.0 Gbps (WireGuard Overlay)", "priority": "P2"}
        ],
        "tailscale_peers": [
            {"node_name": "Mac_Node", "ip": "100.119.199.76", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L1", "os": "macOS Darwin ARM64"},
            {"node_name": "MacBook_Pro", "ip": "100.103.212.21", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L2", "os": "macOS Darwin ARM64"},
            {"node_name": "Linux_Head_Node", "ip": "100.101.39.98", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L3", "os": "Debian Linux x86_64"},
            {"node_name": "Linux_Tablet", "ip": "100.81.92.125", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L4", "os": "Debian Linux ARM64"},
            {"node_name": "MacBook_Air", "ip": "100.93.158.96", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L5", "os": "macOS Darwin ARM64"},
            {"node_name": "Pixel_10_Pro_XL", "ip": "100.73.38.87", "status": "ONLINE", "relay": "Direct WireGuard", "layer": "L6", "os": "Android 15 (Tensor G5)"},
            {"node_name": "Samsung_S20", "ip": "100.84.40.95", "status": "IDLE", "relay": "Direct WireGuard", "layer": "L7", "os": "Android 13 (Exynos 990)"}
        ],
        "tb4_dma": {
            "ip": "169.254.187.138",
            "status": "CONNECTED",
            "rtt_ms": 0.277,
            "throughput_gbps": 38.4,
            "interface": "bridge0 / tb0",
            "zero_copy_active": True
        },
        "llama_rpc_nodes": [
            {"node_name": "Linux Head Node", "endpoint": "100.101.39.98:50052", "layers_sharded": 28, "vram_used_gb": 13.5, "status": "ONLINE", "latency_ms": 1.20},
            {"node_name": "MacBook Pro", "endpoint": "169.254.187.138:50052", "layers_sharded": 28, "vram_used_gb": 13.5, "status": "ONLINE", "latency_ms": 0.28},
            {"node_name": "Mac Mini Host", "endpoint": "127.0.0.1:50052", "layers_sharded": 24, "vram_used_gb": 12.0, "status": "ONLINE", "latency_ms": 0.05}
        ],
        "petals_dht": {
            "status": "ACTIVE",
            "port": 31337,
            "active_blocks": 80,
            "swarm_nodes": 3,
            "dht_connected": True
        },
        "exo_p2p": {
            "status": "ACTIVE",
            "port": 52415,
            "discovery_ring": True,
            "active_peers": 4,
            "topology": "Ring-P2P"
        },
        "internet_speed": {
            "download_mbps": 942.5,
            "upload_mbps": 118.2,
            "ping_ms": 4.8,
            "cycle_seconds": 300,
            "timestamp": "2026-08-27T08:00:00Z"
        }
    }

@pytest.fixture
def master_agi_models() -> List[Dict[str, Any]]:
    """Authoritative Master AGI model specifications per ORIGINAL_REQUEST §R1 and PROJECT.md."""
    return [
        {
            "id": "kimi_tandem_titan",
            "name": "Kimi 88B Tandem Titan",
            "architecture": "Kimi-VL Thinking 2506 + Kimi-Dev-72B-Instruct",
            "shardingStrategy": "-ts 28,28,24 on GGML RPC Port 50052",
            "contextWindow": 131072,
            "ports": [8085, 8081, 50052],
            "vramFootprintGb": 48.8,
            "throughputTokPerSec": 32.4,
            "eloRating": 3089.0,
            "status": "active",
            "isAbliterated": False,
            "codingProficiency": {"Python": 96, "Rust": 92, "C++": 94, "Dart": 88, "Kotlin": 90, "TypeScript": 95, "Swift": 91, "Bash": 94}
        },
        {
            "id": "qwen_38_max",
            "name": "Qwen 3.8 Max / Vision Master",
            "architecture": "Qwen2.5-VL-30B-Instruct + Qwen2.5-VL-7B Edge",
            "shardingStrategy": "Metal GPU Direct + Ray 3-Device Split",
            "contextWindow": 131072,
            "ports": [8084, 8082],
            "vramFootprintGb": 5.85,
            "throughputTokPerSec": 48.3,
            "eloRating": 2265.0,
            "status": "active",
            "isAbliterated": False,
            "codingProficiency": {"Python": 95, "Rust": 94, "C++": 96, "Dart": 90, "Kotlin": 92, "TypeScript": 97, "Swift": 89, "Bash": 95}
        },
        {
            "id": "gemini_flash_cloud",
            "name": "Gemini 3.7 Flash High (Cloud Frontier)",
            "architecture": "Multimodal Hybrid MoE Thinking CoT",
            "shardingStrategy": "Cloud Frontier API + Asynchronous Shadow Guard",
            "contextWindow": 1048576,
            "ports": [443],
            "vramFootprintGb": 0.0,
            "throughputTokPerSec": 115.0,
            "eloRating": 3210.0,
            "status": "active",
            "isAbliterated": False,
            "codingProficiency": {"Python": 98, "Rust": 95, "C++": 95, "Dart": 94, "Kotlin": 95, "TypeScript": 99, "Swift": 96, "Bash": 97}
        },
        {
            "id": "genetic_moe_core",
            "name": "Genetic MoE Evolutionary Core",
            "architecture": "5-Pillar Dynamic Telemetry Router",
            "shardingStrategy": "Nomad Courier v3.0 Governor",
            "contextWindow": 32768,
            "ports": [18802, 4000],
            "vramFootprintGb": 2.5,
            "throughputTokPerSec": 64.0,
            "eloRating": 3042.0,
            "status": "active",
            "isAbliterated": True,
            "codingProficiency": {"Python": 92, "Rust": 90, "C++": 89, "Dart": 86, "Kotlin": 88, "TypeScript": 93, "Swift": 87, "Bash": 96}
        },
        {
            "id": "llama_33_70b_abliterated",
            "name": "Llama 3.3 70B Instruct Abliterated",
            "architecture": "Uncensored Dense Transformer",
            "shardingStrategy": "Distributed RPC Mesh",
            "contextWindow": 65536,
            "ports": [8082],
            "vramFootprintGb": 42.0,
            "throughputTokPerSec": 42.0,
            "eloRating": 2190.0,
            "status": "standby",
            "isAbliterated": True,
            "codingProficiency": {"Python": 94, "Rust": 91, "C++": 92, "Dart": 87, "Kotlin": 89, "TypeScript": 94, "Swift": 88, "Bash": 93}
        }
    ]

@pytest.fixture
def cluster_vram_topology() -> Dict[str, Any]:
    """Authoritative 7-layer mesh hardware matrix, L5 #2 priority, headless scores, device ELO, and pooled VRAM definition."""
    return {
        "pooledVramGb": 82.8,
        "totalPhysicalRamGb": 108.0,
        "allocatedVramGb": 57.15,
        "freeHeadroomGb": 25.65,
        "interconnect": {
            "type": "Thunderbolt 4 DMA 40Gbps",
            "latencyMs": 0.277,
            "ip": "169.254.187.138"
        },
        "nodes": [
            {
                "nodeId": "mac_node_l1",
                "name": "Mac_Node (Host Mini M4)",
                "layer": "L1",
                "ip": "192.168.8.230",
                "tailscaleIp": "100.119.199.76",
                "ramTotalGb": 24.0,
                "aiVramCapGb": 21.6,
                "dynamicCapPercent": 90.0,
                "osReserveGb": 2.4,
                "latencyMs": 0.05,
                "priorityRank": 1,
                "headlessCapable": True,
                "headlessScore": 95,
                "deviceEloRating": 2450,
                "status": "ONLINE"
            },
            {
                "nodeId": "macbook_air_l5",
                "name": "MacBook_Air (M4 Worker)",
                "layer": "L5",
                "ip": "192.168.8.222",
                "tailscaleIp": "100.93.158.96",
                "ramTotalGb": 16.0,
                "aiVramCapGb": 14.4,
                "dynamicCapPercent": 90.0,
                "osReserveGb": 1.6,
                "latencyMs": 2.10,
                "priorityRank": 2,
                "headlessCapable": True,
                "headlessScore": 72,
                "deviceEloRating": 2180,
                "status": "ONLINE"
            },
            {
                "nodeId": "macbook_pro_l2",
                "name": "MacBook_Pro (TB4 Bridge Vault)",
                "layer": "L2",
                "ip": "192.168.8.127",
                "tailscaleIp": "100.103.212.21",
                "ramTotalGb": 16.0,
                "aiVramCapGb": 14.4,
                "dynamicCapPercent": 90.0,
                "osReserveGb": 1.6,
                "latencyMs": 0.277,
                "priorityRank": 3,
                "headlessCapable": True,
                "headlessScore": 70,
                "deviceEloRating": 2140,
                "status": "ONLINE"
            },
            {
                "nodeId": "linux_head_node_l3",
                "name": "Linux_Head_Node (Ryzen 7 5700U)",
                "layer": "L3",
                "ip": "192.168.8.224",
                "tailscaleIp": "100.101.39.98",
                "ramTotalGb": 16.0,
                "aiVramCapGb": 12.8,
                "dynamicCapPercent": 80.0,
                "osReserveGb": 3.2,
                "latencyMs": 1.20,
                "priorityRank": 4,
                "headlessCapable": True,
                "headlessScore": 92,
                "deviceEloRating": 2320,
                "status": "ONLINE"
            },
            {
                "nodeId": "linux_tablet_l4",
                "name": "Linux_Tablet (Debian Touch)",
                "layer": "L4",
                "ip": "192.168.8.173",
                "tailscaleIp": "100.81.92.125",
                "ramTotalGb": 8.0,
                "aiVramCapGb": 6.0,
                "dynamicCapPercent": 75.0,
                "osReserveGb": 2.0,
                "latencyMs": 4.50,
                "priorityRank": 5,
                "headlessCapable": True,
                "headlessScore": 75,
                "deviceEloRating": 1980,
                "status": "ONLINE"
            },
            {
                "nodeId": "pixel_10_pro_xl_l6",
                "name": "Pixel_10_Pro_XL (Tensor G5)",
                "layer": "L6",
                "ip": "192.168.8.160",
                "tailscaleIp": "100.73.38.87",
                "ramTotalGb": 16.0,
                "aiVramCapGb": 13.6,
                "dynamicCapPercent": 85.0,
                "osReserveGb": 2.4,
                "latencyMs": 6.80,
                "priorityRank": 6,
                "headlessCapable": True,
                "headlessScore": 88,
                "deviceEloRating": 2210,
                "status": "ONLINE"
            },
            {
                "nodeId": "samsung_s20_l7",
                "name": "Samsung_S20 (Exynos 990)",
                "layer": "L7",
                "ip": "192.168.8.158",
                "tailscaleIp": "100.84.40.95",
                "ramTotalGb": 12.0,
                "aiVramCapGb": 9.0,
                "dynamicCapPercent": 75.0,
                "osReserveGb": 3.0,
                "latencyMs": 8.40,
                "priorityRank": 7,
                "headlessCapable": True,
                "headlessScore": 80,
                "deviceEloRating": 1920,
                "status": "ONLINE"
            }
        ]
    }

@pytest.fixture
def headless_nodes_registry() -> Dict[str, Dict[str, Any]]:
    """Authoritative headless capability scores and flags for all 8 nodes."""
    return {
        "GW": {"name": "GL.iNet Router", "headless_capable": True, "headless_score": 100, "device_elo": 2500},
        "L1": {"name": "Mac_Node (Host Mini M4)", "headless_capable": True, "headless_score": 95, "device_elo": 2450},
        "L3": {"name": "Linux_Head_Node", "headless_capable": True, "headless_score": 92, "device_elo": 2320},
        "L6": {"name": "Pixel_10_Pro_XL", "headless_capable": True, "headless_score": 88, "device_elo": 2210},
        "L7": {"name": "Samsung_S20", "headless_capable": True, "headless_score": 80, "device_elo": 1920},
        "L4": {"name": "Linux_Tablet", "headless_capable": True, "headless_score": 75, "device_elo": 1980},
        "L5": {"name": "MacBook_Air", "headless_capable": True, "headless_score": 72, "device_elo": 2180},
        "L2": {"name": "MacBook_Pro", "headless_capable": True, "headless_score": 70, "device_elo": 2140},
    }

@pytest.fixture
def tri_orchestrator_debate_spec() -> Dict[str, Any]:
    """Authoritative Tri-Orchestrator debate protocol parameters with Infinite Consensus & Code-Off."""
    return {
        "consensusThreshold": 0.98,
        "infiniteConsensusProtocol": True,
        "codeOffTiebreaker": True,
        "humanFallback": True,
        "personas": [
            {"id": "cloud", "name": "Gemini 3.7 Flash High (Cloud)", "weight": 0.35},
            {"id": "local", "name": "Kimi 88B Tandem (Local Sovereign)", "weight": 0.40},
            {"id": "genetic", "name": "Genetic MoE Router (Swarm)", "weight": 0.25}
        ],
        "actionSlashCommands": [
            "/audit",
            "/duel",
            "/cron",
            "/storage",
            "/ping",
            "/revive"
        ]
    }

@pytest.fixture
def optimization_modules_spec() -> Dict[str, Any]:
    """Authoritative specifications for the 4 optimization modules per ORIGINAL_REQUEST §R2."""
    return {
        "hardware": {
            "id": "optimization-hardware",
            "name": "Hardware Analysis and Optimization App",
            "subsystems": ["LiveDeviceSentinelHUD", "ComputeHubWebView", "AdaptiveDeviceHardwareGovernor"],
            "telemetryEndpoints": ["/api/telemetry", "/api/devices", "/ws/telemetry"],
            "bleGattRateHz": 128,
            "governorModes": {"HUMAN_INTERACTIVE": 58, "AUTONOMOUS_SURGE": 94}
        },
        "software": {
            "id": "optimization-software",
            "name": "Software Analysis and Optimization App",
            "subsystems": ["MetaTrainingGameDashboardView", "CompilerSandbox", "PySparkASTAnalyser"],
            "telemetryEndpoints": ["/api/task/dispatch", "/api/task/history", "/api/sandbox/evaluate", "/api/pyspark/ast_index"],
            "compiler": "Apple Clang / GCC ASan UBSan",
            "monorepoFilesIndexed": 10251,
            "totalLOC": 3294334
        },
        "internet": {
            "id": "optimization-internet",
            "name": "Internet Analysis and Optimization App",
            "subsystems": ["FutureNetworkSimulationHub", "MultiWANShardingAccelerator", "MeshNetworkOptimizer"],
            "telemetryEndpoints": ["/api/simulation/future_network", "/api/genetic_moe/triage", "/api/mesh_all_to_all_matrix"],
            "transportersCount": 10,
            "primaryInterconnect": "TB4 40Gbps DMA 0.277ms"
        },
        "storage": {
            "id": "optimization-storage",
            "name": "Storage Analysis and Optimization App",
            "subsystems": ["StorageAnalysisHub", "StorageMeshOptimizer", "PySparkNASLakehouse"],
            "telemetryEndpoints": ["/api/storage/mesh", "/api/pyspark/sql", "/api/storage/deep_analysis"],
            "storageTiersCount": 5,
            "minFreeHeadroomGb": 10.0
        }
    }

@pytest.fixture
def training_multitab_spec() -> Dict[str, Any]:
    """Authoritative specifications for the 4 training sub-tabs per ORIGINAL_REQUEST §R3."""
    return {
        "tabs": [
            {"id": "lora_monitor", "name": "LoRA Training & Distillation Monitor"},
            {"id": "games_arena", "name": "Implemented Games & Benchmark Environments"},
            {"id": "structural_metrics", "name": "Structural & Dataset Metrics"},
            {"id": "execution_traces", "name": "Execution Traces & Action Logs"}
        ],
        "loraConfig": {
            "r": 8,
            "loraAlpha": 16,
            "targetModules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "targetModel": "Qwen/Qwen2.5-Coder-7B-Instruct / Kimi 88B Tandem",
            "datasetSink": "04_data_and_memory/lora_dataset.jsonl",
            "eloSink": "04_data_and_memory/lora_datasets/elo_discoveries.jsonl",
            "activeDatasetsCount": 23
        },
        "truthGate": {
            "maxPacketAgeSeconds": 20.0,
            "sensor": "Movesense 128Hz GATT",
            "strictZeroMock": True
        },
        "gamesArena": {
            "modelsCount": 13,
            "meshAlliances": ["BLE Mild", "LAN P2P Moderate", "Tailscale Secure", "TB4 Symbiotic"],
            "chaosSLMsCount": 8,
            "grapplingKinematicsNodes": 955
        }
    }

@pytest.fixture
def token_benchmark_spec() -> Dict[str, Any]:
    """Multi-prompt inference token/s benchmark matrix specifications."""
    return {
        "promptLengths": [128, 512, 2048],
        "models": ["kimi_tandem_titan", "qwen_38_max", "gemini_flash_cloud", "llama_33_70b_abliterated"],
        "expectedThroughputRanges": {
            128: (30.0, 150.0),
            512: (25.0, 130.0),
            2048: (15.0, 100.0)
        }
    }

@pytest.fixture
def speedtest_spec() -> Dict[str, Any]:
    """Internet speed test specifications."""
    return {
        "command": "/usr/bin/networkQuality -c -M 5",
        "cycleSeconds": 300,
        "fields": ["download_mbps", "upload_mbps", "ping_ms", "timestamp"]
    }

@pytest.fixture
def ssh_fleet_spec() -> List[Dict[str, Any]]:
    """SSH fleet daemon telemetry specifications across mesh nodes."""
    return [
        {"node": "L1_Mac_Node", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L2_MacBook_Pro", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L3_Linux_Head_Node", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L4_Linux_Tablet", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L5_MacBook_Air", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L6_Pixel_10_Pro_XL", "port": 8022, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "L7_Samsung_S20", "port": 8022, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"},
        {"node": "GW_GL_iNet", "port": 22, "key_type": "ssh-ed25519", "auth_status": "AUTHENTICATED"}
    ]

# ============================================================================
# NEW AUTHORITATIVE FIXTURES: SPEC MODULES (00-12) & MESH PIPELINE
# ============================================================================

@pytest.fixture
def spec_modules_catalog() -> Dict[str, Dict[str, Any]]:
    """Authoritative schema catalog for all 12 spec modules (spec-00 through spec-12)."""
    return {
        "spec_00_core_infra": {
            "module_id": "spec-00-core-infra",
            "display_name": "Core Infrastructure & Self-Healing Hub",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-00",
            "required_keys": ["seaweedfs_status", "docker_containers", "tailscale_subnet", "port_18802_api"],
            "telemetry_fields": ["disk_free_gb", "active_daemons", "rpc_socket_status"]
        },
        "spec_01_apps_ecosystem": {
            "module_id": "spec-01-apps-ecosystem",
            "display_name": "Applications & Multi-Hub Ecosystem",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-01",
            "required_keys": ["port_4000_hub", "movesense_hub", "zone_2_status", "shopify_ai", "grappling_3d"],
            "telemetry_fields": ["active_sessions", "ecg_stream_active", "hub_latency_ms"]
        },
        "spec_02_ai_inference": {
            "module_id": "spec-02-ai-inference",
            "display_name": "AI Inference Mesh & Model Vault",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-02",
            "required_keys": ["llama_rpc_shards", "petals_dht", "exo_p2p", "gguf_vault"],
            "telemetry_fields": ["pooled_vram_gb", "active_shards", "tokens_per_sec"]
        },
        "spec_03_biometrics_dsp": {
            "module_id": "spec-03-biometrics-dsp",
            "display_name": "Medical-Grade Biometrics & DSP",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-03",
            "required_keys": ["ecg_512hz", "pan_tompkins_qrs", "ptt_blood_pressure", "dfa_alpha1"],
            "telemetry_fields": ["heart_rate_bpm", "hrv_rmssd", "dfa_a1_score", "systolic_bp", "diastolic_bp"]
        },
        "spec_04_data_memory": {
            "module_id": "spec-04-data-memory",
            "display_name": "PySpark Lakehouse & LoRA Memory Sync",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-04",
            "required_keys": ["pyspark_ast_crawler", "lora_dataset_sink", "qdrant_vector_db", "gdrive_sync"],
            "telemetry_fields": ["ast_files_indexed", "total_loc", "lora_instruction_pairs", "vector_embeddings_count"]
        },
        "spec_05_agents_swarms": {
            "module_id": "spec-05-agents-swarms",
            "display_name": "Swarm Governance & Tri-Orchestrator AI Debate",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-05",
            "required_keys": ["tri_orchestrator_debate", "genetic_moe", "truth_audit_gate", "elo_leaderboard"],
            "telemetry_fields": ["debate_consensus_score", "active_agents", "audited_actions_count"]
        },
        "spec_06_scripts_tooling": {
            "module_id": "spec-06-scripts-tooling",
            "display_name": "Tooling, Universal SSH & WoL Resurrection",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-06",
            "required_keys": ["universal_ssh", "adb_keepalive", "wake_on_lan", "figma_mcp"],
            "telemetry_fields": ["ssh_authenticated_nodes", "adb_device_count", "wol_magic_packets_sent"]
        },
        "spec_07_docs_arch": {
            "module_id": "spec-07-docs-arch",
            "display_name": "Deep Architecture Index & Whitepapers",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-07",
            "required_keys": ["architecture_index", "whitepapers", "security_rfcs", "obsidian_graph"],
            "telemetry_fields": ["wikilinks_count", "notes_parsed", "graph_depth"]
        },
        "spec_08_commerce": {
            "module_id": "spec-08-commerce",
            "display_name": "Business & Monetization Engine",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-08",
            "required_keys": ["shopify_storefront_graphql", "membership_tiers", "subscription_billing", "cac_ltv_model"],
            "telemetry_fields": ["active_subscriptions", "mrr_usd", "gross_merchandise_value"]
        },
        "spec_09_app_store": {
            "module_id": "spec-09-app-store",
            "display_name": "App Store Production & Memory Leak Audits",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-09",
            "required_keys": ["play_store_readiness", "app_store_readiness", "apk_signing", "memory_leak_audit"],
            "telemetry_fields": ["crash_free_users_percent", "heap_allocation_mb", "signing_valid"]
        },
        "spec_10_spatial_kinematics": {
            "module_id": "spec-10-spatial-kinematics",
            "display_name": "3D Spatial Grappling Kinematics",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-10",
            "required_keys": ["opml_spatial_tree", "tatami_3d_world", "joint_torque_limits", "submission_counters"],
            "telemetry_fields": ["kinematics_nodes_count", "joint_angles", "angular_velocity_rad_s"]
        },
        "spec_11_12_security_lora": {
            "module_id": "spec-11-12-security-lora",
            "display_name": "Security Isolation & Continuous LoRA Evolution",
            "spec_version": "1.0.0",
            "endpoint_prefix": "/api/spec-11",
            "required_keys": ["red_blue_team", "hmac_sha256_auth", "continuous_lora_tracker", "peft_merging"],
            "telemetry_fields": ["security_violations_count", "current_lora_loss", "checkpoint_epoch"]
        }
    }

@pytest.fixture
def sample_mesh_node_payloads() -> Dict[str, Dict[str, Any]]:
    """Authoritative sample payloads for all 7 mesh layers + Gateway node."""
    return {
        "Mac_Node": {
            "node_id": "Mac_Node",
            "layer": "L1",
            "ip": "192.168.8.230",
            "tailscale_ip": "100.119.199.76",
            "cpu_percent": 14.5,
            "ram_used_gb": 12.8,
            "ram_total_gb": 24.0,
            "ai_vram_cap_gb": 21.6,
            "vram_used_gb": 11.2,
            "rtt_ms": 0.05,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "macOS Darwin ARM64",
            "timestamp": time.time()
        },
        "Linux_Head_Node": {
            "node_id": "Linux_Head_Node",
            "layer": "L3",
            "ip": "192.168.8.224",
            "tailscale_ip": "100.101.39.98",
            "cpu_percent": 28.2,
            "ram_used_gb": 9.4,
            "ram_total_gb": 16.0,
            "ai_vram_cap_gb": 12.8,
            "vram_used_gb": 8.5,
            "rtt_ms": 1.20,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "Debian Linux x86_64",
            "timestamp": time.time()
        },
        "MacBook_Pro": {
            "node_id": "MacBook_Pro",
            "layer": "L2",
            "ip": "192.168.8.127",
            "tailscale_ip": "100.103.212.21",
            "tb4_ip": "169.254.187.138",
            "cpu_percent": 18.0,
            "ram_used_gb": 10.2,
            "ram_total_gb": 16.0,
            "ai_vram_cap_gb": 14.4,
            "vram_used_gb": 9.0,
            "rtt_ms": 0.277,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "macOS Darwin ARM64",
            "timestamp": time.time()
        },
        "MacBook_Air": {
            "node_id": "MacBook_Air",
            "layer": "L5",
            "ip": "192.168.8.222",
            "tailscale_ip": "100.93.158.96",
            "cpu_percent": 12.0,
            "ram_used_gb": 8.0,
            "ram_total_gb": 16.0,
            "ai_vram_cap_gb": 14.4,
            "vram_used_gb": 6.5,
            "rtt_ms": 2.10,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "macOS Darwin ARM64",
            "timestamp": time.time()
        },
        "Linux_Tablet": {
            "node_id": "Linux_Tablet",
            "layer": "L4",
            "ip": "192.168.8.173",
            "tailscale_ip": "100.81.92.125",
            "cpu_percent": 35.0,
            "ram_used_gb": 4.5,
            "ram_total_gb": 8.0,
            "ai_vram_cap_gb": 6.0,
            "vram_used_gb": 3.2,
            "rtt_ms": 4.50,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "Debian Linux ARM64",
            "timestamp": time.time()
        },
        "Pixel_10_Pro_XL": {
            "node_id": "Pixel_10_Pro_XL",
            "layer": "L6",
            "ip": "192.168.8.160",
            "tailscale_ip": "100.73.38.87",
            "cpu_percent": 22.0,
            "ram_used_gb": 8.2,
            "ram_total_gb": 16.0,
            "ai_vram_cap_gb": 13.6,
            "vram_used_gb": 5.0,
            "rtt_ms": 6.80,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "Android 15 (Tensor G5)",
            "timestamp": time.time()
        },
        "Samsung_S20": {
            "node_id": "Samsung_S20",
            "layer": "L7",
            "ip": "192.168.8.158",
            "tailscale_ip": "100.84.40.95",
            "cpu_percent": 10.0,
            "ram_used_gb": 6.0,
            "ram_total_gb": 12.0,
            "ai_vram_cap_gb": 9.0,
            "vram_used_gb": 4.0,
            "rtt_ms": 8.40,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "Android 13 (Exynos 990)",
            "timestamp": time.time()
        },
        "GL_iNet_Router": {
            "node_id": "GL_iNet_Router",
            "layer": "GW",
            "ip": "192.168.8.1",
            "tailscale_ip": "100.122.185.123",
            "cpu_percent": 15.0,
            "ram_used_gb": 0.35,
            "ram_total_gb": 0.512,
            "ai_vram_cap_gb": 0.0,
            "vram_used_gb": 0.0,
            "rtt_ms": 1.10,
            "drop_rate": 0.0,
            "status": "ONLINE",
            "os": "OpenWrt / GL.iNet MLO",
            "timestamp": time.time()
        }
    }

@pytest.fixture
def mock_obsidian_vault_dir(tmp_path) -> str:
    """Creates an isolated temporary Obsidian Vault structure with Index.md and sample notes."""
    vault_dir = tmp_path / "obsidian_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Index.md
    index_file = vault_dir / "Index.md"
    index_file.write_text(
        "---\n"
        "title: \"Lauburu AI Monorepo - Master Knowledge Graph\"\n"
        "tags: [lauburu, root, master_index, swarm]\n"
        "---\n"
        "# 🧠 Master Knowledge Vault\n"
        "- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]\n"
        "- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]\n"
        "- [[Mac_Node]]\n"
        "- [[Linux_Head_Node]]\n"
        "- [[MacBook_Pro]]\n"
    )
    
    # Create nodes directory
    nodes_dir = vault_dir / "nodes"
    nodes_dir.mkdir(exist_ok=True)
    (nodes_dir / "Mac_Node.md").write_text("# [[Mac_Node]]\nLayer 1 Primary Host")
    (nodes_dir / "Linux_Head_Node.md").write_text("# [[Linux_Head_Node]]\nLayer 3 Compute Hub")
    (nodes_dir / "MacBook_Pro.md").write_text("# [[MacBook_Pro]]\nLayer 2 TB4 DMA Vault")
    
    return str(vault_dir)

@pytest.fixture
def smolagent_tool_definitions() -> List[Dict[str, Any]]:
    """Authoritative tool definitions available to the Smolagents autonomous ecosystem."""
    return [
        {
            "name": "probe_mesh_interface",
            "description": "Probe a physical or virtual network interface for latency and drop rate",
            "parameters": {
                "interface_name": {"type": "string", "required": True},
                "target_ip": {"type": "string", "required": True}
            }
        },
        {
            "name": "sync_obsidian_telemetry",
            "description": "Format and write telemetry snapshot to Obsidian Vault Markdown notes",
            "parameters": {
                "node_id": {"type": "string", "required": True},
                "telemetry_dict": {"type": "object", "required": True}
            }
        },
        {
            "name": "harvest_lora_dataset",
            "description": "Harvest validated diffs and audit logs to JSONL training buffer",
            "parameters": {
                "source_log": {"type": "string", "required": True},
                "sink_path": {"type": "string", "required": True}
            }
        },
        {
            "name": "heal_stale_git_lock",
            "description": "Idempotently check for and remove stale .git/index.lock if present",
            "parameters": {
                "repo_path": {"type": "string", "required": True}
            }
        }
    ]

@pytest.fixture
def smolagent_provider_configs() -> Dict[str, Dict[str, Any]]:
    """Authoritative provider configs for Smolagents routing (Local llama.cpp/exo and free-tier cloud)."""
    return {
        "local_llamacpp": {
            "provider_type": "local",
            "endpoint": "http://127.0.0.1:8081/v1",
            "model": "Kimi-88B-Tandem",
            "priority": 1,
            "max_tokens": 4096,
            "is_free": True
        },
        "local_exo": {
            "provider_type": "local",
            "endpoint": "http://127.0.0.1:52415/v1",
            "model": "Qwen2.5-Coder-7B",
            "priority": 2,
            "max_tokens": 4096,
            "is_free": True
        },
        "cloudflare_ai_free": {
            "provider_type": "cloud",
            "endpoint": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3-8b-instruct",
            "model": "@cf/meta/llama-3-8b-instruct",
            "priority": 3,
            "daily_quota": 10000,
            "is_free": True
        },
        "gemini_flash_free": {
            "provider_type": "cloud",
            "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash",
            "model": "gemini-2.5-flash",
            "priority": 4,
            "daily_quota": 300,  # User Ultra Plan 300 req/24/7 allowance
            "is_free": True
        }
    }
