"""
Lauburu Cable & Mesh Analyzer - Configuration
Defines mesh nodes, probe timeouts, listening port (4007), and paths.
"""
from pathlib import Path
import os
import sys
from typing import Dict, Any, List, Optional

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    APP_DIR = Path(sys._MEIPASS)
    FRONTEND_DIR = APP_DIR / "frontend"
else:
    APP_DIR = Path(__file__).resolve().parent.parent
    FRONTEND_DIR = APP_DIR / "frontend"

PORT = 4007
HOST = "0.0.0.0"

# Executables & Ports
WHATCABLE_BIN = os.environ.get("WHATCABLE_BIN", "/Users/aaron/.local/bin/whatcable")
PYTHON_314_BIN = "/Users/aaron/.local/opt/python@3.14/bin/python3.14"
NEO_LAUNCHER_BIN = "/Users/aaron/.local/bin/neo-mcp-launcher"
ADB_BIN = "/usr/local/bin/adb" if os.path.exists("/usr/local/bin/adb") else "adb"

# Bluetooth Serial Terminal & Local AI
BT_TERMINAL_HOST = "127.0.0.1"
BT_TERMINAL_PORT = 4005
LOCAL_AI_HOST = "127.0.0.1"
LOCAL_AI_PORT = 8082
LOCAL_AI_MODEL = "hermes-3-llama-3.1-8b"
LOCAL_AI_REDTEAM_PORT = 8083
LOCAL_AI_REDTEAM_MODEL = "qwen2.5-7b-instruct-abliterated"

# Mesh Nodes Definition
MESH_NODES = {
    "l1_mac_mini": {
        "id": "l1_mac_mini",
        "name": "Mac Mini M4 Pro (Host L1)",
        "role": "Primary Host & Memory Governor",
        "local_ip": "192.168.8.155",
        "tailscale_ip": "100.119.199.76",
        "os": "macOS (Darwin)",
        "arch": "Apple M4 Pro (12-Core CPU / 16-Core GPU)",
        "ram_total_gb": 24.0,
        "npu_name": "Apple Neural Engine (ANE)",
        "npu_cores": 16,
        "npu_tops": 38.0,
        "is_local": True
    },
    "l2_macbook_pro": {
        "id": "l2_macbook_pro",
        "name": "Intel MacBook Pro (L2)",
        "role": "Metal GPU RPC & Storage Vault",
        "local_ip": "10.127.110.221",
        "tailscale_ip": "100.103.212.21",
        "tb4_ip": "fe80::1ca1:d3cc:d4b9:695b%bridge0",
        "alt_tb4_ip": "192.168.2.3",
        "ssh_host": "macbook-pro",
        "os": "macOS (Darwin)",
        "arch": "Intel Core i7 / T2 Metal",
        "ram_total_gb": 16.0,
        "npu_name": "Apple Metal GPU / 285GB Vault",
        "npu_cores": 16,
        "npu_tops": 38.0,
        "is_local": False
    },
    "l3_linux_head": {
        "id": "l3_linux_head",
        "name": "Linux Laptop Node (L3)",
        "role": "Compute Hub & 1M Router AI Worker",
        "local_ip": "192.168.8.225",
        "tailscale_ip": "100.101.39.98",
        "ssh_host": "linux",
        "os": "Ubuntu Linux 24.04",
        "arch": "Dell Inspiron 15 3525 (AMD Ryzen 7 5700U 8C/16T, Lucienne)",
        "ram_total_gb": 16.0,
        "npu_name": "AMD Ryzen 7 SIMD AVX2",
        "npu_cores": 8,
        "npu_tops": 10.0,
        "is_local": False
    },
    "l8_linux_mini": {
        "id": "l8_linux_mini",
        "name": "Linux Mini Compute Vault (L8)",
        "role": "Gateway Ingress & Genetic Drafter Trainer",
        "local_ip": "192.168.8.238",
        "tailscale_ip": "100.121.247.8",
        "tb4_ip": "192.168.2.8",
        "ssh_host": "linuxmini-tb",
        "os": "Ubuntu Linux 24.04",
        "arch": "Apple Mac Mini 2018 (Intel Core i7-8700B 6C/12T @ 3.20GHz)",
        "ram_total_gb": 32.0,
        "npu_name": "Intel Core i7 AVX2 / 27B Huihui Server",
        "npu_cores": 6,
        "npu_tops": 14.0,
        "is_local": False
    },
    "l4_linux_tablet": {
        "id": "l4_linux_tablet",
        "name": "Linux Tablet (L4)",
        "role": "Mobile Linux Compute & Touch DSP",
        "local_ip": "192.168.8.190",
        "tailscale_ip": "100.118.79.63",
        "ssh_host": "tablet",
        "os": "Debian Linux 13 (Trixie)",
        "arch": "ARM64 / Touch DSP Subsystem",
        "ram_total_gb": 8.0,
        "npu_name": "Mobile Touch DSP & Petals Worker",
        "npu_cores": 4,
        "npu_tops": 6.5,
        "is_local": False
    },
    "l5_macbook_air": {
        "id": "l5_macbook_air",
        "name": "MacBook Air M4 (L5)",
        "role": "Secondary High-Speed Metal Worker",
        "local_ip": "192.168.8.122",
        "tailscale_ip": "100.121.202.34",
        "tb4_ip": "192.168.2.11",
        "ssh_host": "macbook-air-tb",
        "os": "macOS (Darwin)",
        "arch": "Apple M4 (8-Core CPU / 10-Core GPU)",
        "ram_total_gb": 16.0,
        "npu_name": "Apple Neural Engine (ANE)",
        "npu_cores": 16,
        "npu_tops": 38.0,
        "is_local": False
    },
    "l6_pixel_10": {
        "id": "l6_pixel_10",
        "name": "Pixel 10 Pro XL (L6)",
        "role": "Edge Vision & TPU Compute",
        "local_ip": "100.73.38.87",
        "tailscale_ip": "100.73.38.87",
        "adb_target": "100.73.38.87:5555",
        "os": "Android 16 / VanillaIceCream",
        "arch": "Google Tensor G5 (Edge TPU SoC)",
        "ram_total_gb": 16.0,
        "npu_name": "Google Tensor G5 Edge TPU",
        "npu_cores": 4,
        "npu_tops": 45.0,
        "is_local": False
    },
    "l7_samsung_s20": {
        "id": "l7_samsung_s20",
        "name": "Samsung Galaxy S20+ (L7)",
        "role": "Dedicated Automated UI Tester",
        "local_ip": "192.168.8.131",
        "tailscale_ip": "100.84.40.95",
        "adb_target": "100.84.40.95:5555",
        "os": "Android 13 / OneUI",
        "arch": "Samsung Exynos 990",
        "ram_total_gb": 12.0,
        "npu_name": "Samsung Exynos Dual-Core NPU",
        "npu_cores": 2,
        "npu_tops": 10.0,
        "is_local": False
    },
    "l9_iphone_16": {
        "id": "l9_iphone_16",
        "name": "iPhone 16 Pro (L9)",
        "role": "Primary iOS Testing Node & Screen Lens Commerce Target",
        "local_ip": "192.168.8.102",
        "tailscale_ip": "100.122.52.89",
        "lockdown_port": 62078,
        "udid": "00008140-00015D5E3EFA801C",
        "coredevice_id": "AE1D33CE-4249-5E2C-B866-FE3BD627D575",
        "os": "iOS 26.6.2 (Darwin)",
        "arch": "Apple A18 Pro (6-Core CPU / 6-Core GPU)",
        "ram_total_gb": 8.0,
        "npu_name": "Apple 16-Core Neural Engine (35 TOPS)",
        "npu_cores": 16,
        "npu_tops": 35.0,
        "is_local": False
    },
    "gw_router": {
        "id": "gw_router",
        "name": "GL.iNet Gateway Router (GW)",
        "role": "Core Gateway & Hardware USB Bridge",
        "local_ip": "192.168.8.1",
        "tailscale_ip": "100.103.212.34",
        "ssh_host": "root@192.168.8.1",
        "os": "OpenWrt Linux",
        "arch": "MediaTek MT7981B",
        "ram_total_gb": 0.5,
        "npu_name": "Hardware NAT / Packet Engine",
        "npu_cores": 2,
        "npu_tops": 1.0,
        "is_local": False
    }
}

def get_dynamic_mesh_nodes(force: bool = False):
    """Overlay dynamic IP discovery on top of static mesh node metadata and include auto-discovered peers."""
    try:
        from .probes.dynamic_ip_finder import find_dynamic_mesh_ips
    except (ImportError, ValueError):
        from probes.dynamic_ip_finder import find_dynamic_mesh_ips
    
    dynamic_data = find_dynamic_mesh_ips(force=force).get("nodes", {})
    updated_nodes = {}
    for node_id, static_data in MESH_NODES.items():
        node = dict(static_data)
        if node_id in dynamic_data:
            dyn = dynamic_data[node_id]
            if dyn.get("local_ip"):
                node["local_ip"] = dyn["local_ip"]
            if dyn.get("tailscale_ip"):
                node["tailscale_ip"] = dyn["tailscale_ip"]
            if dyn.get("tb4_ip"):
                node["tb4_ip"] = dyn["tb4_ip"]
            if dyn.get("adb_target"):
                node["adb_target"] = dyn["adb_target"]
            if "online" in dyn:
                node["online"] = dyn["online"]
            if dyn.get("mac_address"):
                node["mac_address"] = dyn["mac_address"]
            node["dynamic_source"] = dyn.get("source", "static_config")
        updated_nodes[node_id] = node

    # Merge newly auto-discovered peers (e.g. lauburu-sentinel-node, linuxmini)
    for node_id, dyn in dynamic_data.items():
        if node_id not in updated_nodes:
            updated_nodes[node_id] = {
                "id": node_id,
                "name": dyn.get("name", node_id),
                "role": dyn.get("role", "Dynamic Mesh Node"),
                "local_ip": dyn.get("local_ip"),
                "tailscale_ip": dyn.get("tailscale_ip"),
                "tb4_ip": None,
                "ssh_host": dyn.get("ssh_host", node_id),
                "os": dyn.get("os", "Linux"),
                "arch": dyn.get("arch", "Dynamic Architecture"),
                "ram_total_gb": 8.0,
                "npu_name": "Dynamic Worker Co-Processor",
                "npu_cores": 4,
                "npu_tops": 5.0,
                "is_local": False,
                "is_dynamic": True,
                "online": dyn.get("online", False),
                "dynamic_source": dyn.get("source", "dynamic_discovery")
            }
    return updated_nodes

# Hardware Capabilities Matrix across all 8 mesh layers
DEVICE_CAPABILITIES = {
    "l1_mac_mini": {
        "device_id": "l1_mac_mini",
        "name": "Mac Mini M4 Pro (Host L1)",
        "max_bandwidth_gbps": 80.0,
        "max_transport": "Thunderbolt 5 / USB4 Gen 4 (80/120 Gbps)",
        "supported_interfaces": [
            {"type": "Thunderbolt 5 / USB4", "max_gbps": 80.0, "notes": "3x TB5/USB4 Ports"},
            {"type": "1000BASE-T Ethernet", "max_gbps": 1.0, "notes": "Gigabit RJ45 (en0)"},
            {"type": "Wi-Fi 7 (802.11be)", "max_gbps": 2.4, "notes": "MLO Support (en1)"},
            {"type": "Bluetooth 5.3", "max_gbps": 0.003, "notes": "Master Controller Foundation"}
        ],
        "bluetooth": {
            "mac": "5e:30:9d:be:28:75",
            "role": "Master Host Bluetooth Controller",
            "proximity_wake_sender": True
        }
    },
    "l2_macbook_pro": {
        "device_id": "l2_macbook_pro",
        "name": "Intel MacBook Pro (L2)",
        "max_bandwidth_gbps": 40.0,
        "max_transport": "Thunderbolt 4 / USB4 (40 Gbps)",
        "supported_interfaces": [
            {"type": "Thunderbolt 4 / USB4", "max_gbps": 40.0, "notes": "PCIe Gen 3 DMA Tunneling"},
            {"type": "USB 3.2 Gen 2", "max_gbps": 10.0, "notes": "SuperSpeed+ 10Gbps"},
            {"type": "Wi-Fi 6E / 7", "max_gbps": 2.4, "notes": "High-Speed Air Link"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Encrypted Mesh"},
            {"type": "Bluetooth 5.3", "max_gbps": 0.003, "notes": "Foundation Anchor / Wake Receiver"}
        ],
        "bluetooth": {
            "mac": "a4:83:e7:d1:7c:82",
            "name": "aarons-MBP",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l3_linux_head": {
        "device_id": "l3_linux_head",
        "name": "Linux Head Node (L3)",
        "max_bandwidth_gbps": 1.0,
        "max_transport": "1000BASE-T Gigabit Ethernet (1.0 Gbps)",
        "supported_interfaces": [
            {"type": "1000BASE-T Ethernet", "max_gbps": 1.0, "notes": "Realtek Gigabit LAN"},
            {"type": "USB 3.2 Gen 2", "max_gbps": 10.0, "notes": "Type-A SuperSpeed+"},
            {"type": "Wi-Fi 5 (802.11ac)", "max_gbps": 0.866, "notes": "Dual-Band Wi-Fi"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Kernel Overlay"},
            {"type": "Bluetooth 5.0 (RFCOMM)", "max_gbps": 0.002, "notes": "Foundation Anchor / Daemon Ingress"}
        ],
        "bluetooth": {
            "mac": "00:41:0e:14:28:44",
            "name": "linux",
            "role": "Foundation Control Plane Anchor (RFCOMM)",
            "proximity_wake_target": True
        }
    },
    "l4_linux_tablet": {
        "device_id": "l4_linux_tablet",
        "name": "Linux Tablet (L4)",
        "max_bandwidth_gbps": 0.433,
        "max_transport": "Wi-Fi 5 (802.11ac 433 Mbps)",
        "supported_interfaces": [
            {"type": "Wi-Fi 5 (802.11ac)", "max_gbps": 0.433, "notes": "Mobile WLAN"},
            {"type": "USB 2.0 OTG", "max_gbps": 0.48, "notes": "Charge / Data"},
            {"type": "Tailscale WireGuard", "max_gbps": 0.3, "notes": "Lightweight Overlay"},
            {"type": "Bluetooth 5.0", "max_gbps": 0.002, "notes": "Foundation Anchor / Touch DSP"}
        ],
        "bluetooth": {
            "mac": "76:1c:bf:4f:03:51",
            "name": "Lenovo-Idea-Tab",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l5_macbook_air": {
        "device_id": "l5_macbook_air",
        "name": "MacBook Air M4 (L5)",
        "max_bandwidth_gbps": 40.0,
        "max_transport": "Thunderbolt 4 / USB4 (40 Gbps)",
        "supported_interfaces": [
            {"type": "Thunderbolt 4 / USB4", "max_gbps": 40.0, "notes": "PCIe CIO Link"},
            {"type": "USB 3.2 Gen 2", "max_gbps": 10.0, "notes": "SuperSpeed+ 10Gbps"},
            {"type": "Wi-Fi 7", "max_gbps": 2.4, "notes": "High-Speed Air Link"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Encrypted Mesh"},
            {"type": "Bluetooth 5.3", "max_gbps": 0.003, "notes": "Foundation Anchor / Wake Receiver"}
        ],
        "bluetooth": {
            "mac": "66:74:75:d8:16:fb",
            "name": "aarons-macbook-air",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l6_pixel_10": {
        "device_id": "l6_pixel_10",
        "name": "Pixel 10 Pro XL (L6)",
        "max_bandwidth_gbps": 10.0,
        "max_transport": "USB 3.2 Gen 2 (10 Gbps) / Wi-Fi 7 MLO (2.4-5.8 Gbps)",
        "supported_interfaces": [
            {"type": "USB 3.2 Gen 2", "max_gbps": 10.0, "notes": "High-Speed Wired ADB / DP Alt Mode"},
            {"type": "Wi-Fi 7 (802.11be MLO)", "max_gbps": 2.4, "notes": "Ultra-Low Latency Air Link"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Mesh"},
            {"type": "Bluetooth 5.4 / LE Audio", "max_gbps": 0.003, "notes": "Foundation Anchor / Proximity BLE"}
        ],
        "bluetooth": {
            "mac": "30:e0:44:6d-18-ec",
            "name": "Pixel",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l7_samsung_s20": {
        "device_id": "l7_samsung_s20",
        "name": "Samsung Galaxy S20+ (L7)",
        "max_bandwidth_gbps": 5.0,
        "max_transport": "USB 3.2 Gen 1 (5.0 Gbps) / Wi-Fi 6 (1.2 Gbps)",
        "supported_interfaces": [
            {"type": "USB 3.2 Gen 1", "max_gbps": 5.0, "notes": "SuperSpeed 5Gbps Wired Port"},
            {"type": "Wi-Fi 6 (802.11ax)", "max_gbps": 1.2, "notes": "High-Speed Local Wi-Fi"},
            {"type": "USB 2.0 High Speed", "max_gbps": 0.48, "notes": "Charge-Only Cable Fallback"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Mesh"},
            {"type": "Bluetooth 5.0", "max_gbps": 0.002, "notes": "Foundation Anchor / Keepalive"}
        ],
        "bluetooth": {
            "mac": "5c:cb:99:05:81-41",
            "name": "Aaron's S20+",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l8_linux_mini": {
        "device_id": "l8_linux_mini",
        "name": "Linux Mini Compute Vault (L8)",
        "max_bandwidth_gbps": 1.0,
        "max_transport": "1000BASE-T Gigabit Ethernet / Wi-Fi (1.0 Gbps)",
        "supported_interfaces": [
            {"type": "1000BASE-T Ethernet", "max_gbps": 1.0, "notes": "Gigabit LAN Interface"},
            {"type": "Wi-Fi (802.11ac)", "max_gbps": 0.866, "notes": "Dual-Band Wi-Fi (192.168.8.184)"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Encrypted Mesh (100.121.247.8)"},
            {"type": "Bluetooth 5.0", "max_gbps": 0.002, "notes": "Foundation Anchor / RFCOMM Bridge"}
        ],
        "bluetooth": {
            "mac": "10:82:a3:fe:9e:ae",
            "name": "lauburu",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "l9_iphone_16": {
        "device_id": "l9_iphone_16",
        "name": "iPhone 16 Pro (L9)",
        "max_bandwidth_gbps": 10.0,
        "max_transport": "USB 3.2 Gen 2 (10 Gbps) / Wi-Fi 7 (2.4 Gbps)",
        "supported_interfaces": [
            {"type": "USB-C (USB 3.2 Gen 2)", "max_gbps": 10.0, "notes": "High-Speed Wired / DP Alt Mode"},
            {"type": "Wi-Fi 7 (802.11be)", "max_gbps": 2.4, "notes": "Dual-Band Wi-Fi 7"},
            {"type": "Tailscale WireGuard", "max_gbps": 1.0, "notes": "Layer 3 Mesh (100.122.52.89)"},
            {"type": "Bluetooth 5.3", "max_gbps": 0.003, "notes": "Layer 0 BLE / Proximity Anchor"},
            {"type": "5G Cellular", "max_gbps": 1.0, "notes": "Out-of-Band Cellular WAN Fallback"}
        ],
        "bluetooth": {
            "mac": "74:cc:40:20:8e:10",
            "name": "Aaron’s iPhone",
            "role": "Foundation Control Plane Anchor",
            "proximity_wake_target": True
        }
    },
    "gw_router": {
        "device_id": "gw_router",
        "name": "GL.iNet Gateway Router (GW)",
        "max_bandwidth_gbps": 2.5,
        "max_transport": "2.5GbE WAN / 1.0GbE LAN / Wi-Fi 7 MLO (3.6 Gbps)",
        "supported_interfaces": [
            {"type": "2.5GBASE-T WAN", "max_gbps": 2.5, "notes": "Multi-Gig WAN Uplink"},
            {"type": "1000BASE-T LAN", "max_gbps": 1.0, "notes": "Gigabit Switch Ports"},
            {"type": "Wi-Fi 7 (802.11be)", "max_gbps": 3.6, "notes": "BE3600 Dual-Band MLO"}
        ]
    }
}

# Active Reverse Engineering Targets for Local AI Model Distillation & Feature Value-Add
REVERSE_ENGINEERING_TARGETS: Dict[str, Dict[str, Any]] = {
    "whatcable_vdm_emarker_decoder": {
        "id": "TASK-RE-04",
        "track_id": "RE_06_WHATCABLE_SOP_VDM_EMARKER",
        "name": "WhatCable USB-C SOP' VDM E-Marker Decoder",
        "category": "USB-C & USB-PD 3.1 Protocol",
        "status": "QUEUED_FOR_LOCAL_LORA_DISTILLATION",
        "priority": "Priority #2 (High Cable Analyzer Value)",
        "feature_value": (
            "Eliminates ~180ms external CLI subprocess spawn overhead by parsing USB-PD SOP' VDM "
            "directly in-process in <2ms. Extends hardware E-marker discovery across Linux (L3/L4) "
            "and Android (L6/L7) via /sys/class/typec kernel interfaces."
        ),
        "target_subprotocols": [
            "USB-PD SOP' VDM (Discover Identity, SVIDs, Modes)",
            "E-Marker VDO Parsing (Active/Passive, USB4/TB4 40Gbps, Gen 1/2/3)",
            "Extended Power Range (EPR 240W 48V/5A vs SPR 100W 20V/5A)",
            "Counterfeit VID/PID & Spoofed VDO Detection"
        ],
        "assigned_models": {
            "tier_a_spec": "Local Spec Model (Port 8082)",
            "tier_b_implementer": "Local Implementer Model (Port 8082)",
            "master_orchestrator": "Local Master Orchestrator (Port 8082)",
            "red_team": "Local Red Team (Port 8083)",
            "red_team_auditor": "Local Auditor (Port 8083)"
        },
        "clean_room_language": "C11 / Rust FFI",
        "latency_target_ms": 2.0
    },
    "sharkwire_link_frame_dissector": {
        "id": "TASK-RE-05",
        "track_id": "RE_07_SHARKWIRE_PACKET_FRAME_ANALYZER",
        "name": "Shark Wire / WireShark USB & L2 Link Packet Dissector",
        "category": "Wire Protocol Analysis & CRC Error Sniffing",
        "status": "QUEUED_FOR_LOCAL_LORA_DISTILLATION",
        "priority": "Priority #2 (High Cable Analyzer Value)",
        "feature_value": (
            "Upgrades the Cable Analyzer from static link negotiation to real-time physical wire health "
            "monitoring. Dissects USB transactions and Layer 2 frames, measuring live CRC32 error rates, "
            "frame retries, and jitter to catch loose connectors, damaged pins, and cable degradation."
        ),
        "target_subprotocols": [
            "USB Transaction Framing (Setup, Data, Handshake, SOF, Link Commands)",
            "Layer 2 Ethernet BPF / pcap Frame Inspection",
            "CRC16 / CRC32 FCS Error Frame Counter",
            "Physical Link Jitter & Packet Retransmission Detection"
        ],
        "assigned_models": {
            "tier_a_spec": "Local Spec Model (Port 8083)",
            "tier_b_implementer": "Local Implementer Model (Port 8082)",
            "master_orchestrator": "Local Master Orchestrator (Port 8082)",
            "red_team": "Local Red Team (Port 8082)",
            "red_team_auditor": "Local Auditor (Port 8083)"
        },
        "clean_room_language": "Rust / Tokio / C11",
        "frame_budget_us": 50
    }
}



