#!/usr/bin/env python3
"""
Nexus Terminal Extension Provisioner & Synchronizer
Configures sentriflow.vscode-nexterminal for Antigravity IDE and VS Code.
Synchronizes profiles across state.vscdb, settings.json, and nexus-config-shared.json.

Streamlined Architecture:
- Default: "The Nexus Server" — Single Sovereign Host (Mac Mini M4 Pro on 127.0.0.1:22)
  with Mother Ship (:4050), AI inference tunnels, local shells, and macros.
- Full Mesh Archive: Saved to nexus-mesh-full-topology.json for 7-layer cluster orchestration.
"""

import os
import sys
import json
import uuid
import shutil
import sqlite3
import datetime

# --- Validation Helpers (Identical to extension.js internal validators) ---
def vt(s): return isinstance(s, str) and len(s) > 0
def Yd(n): return isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 65535
def Xn(s): return s is None or vt(s)
def Km(a): return a is None or (isinstance(a, list) and all(isinstance(x, str) for x in a))
def FW(d): return d is None or (isinstance(d, dict) and all(isinstance(v, str) for v in d.values()))

def validate_server(t):
    if not isinstance(t, dict): return False
    if t.get('protocol') is not None and t['protocol'] not in ('ssh', 'telnet'): return False
    addressless = t.get('addressless') is True
    if not (vt(t.get('id')) and vt(t.get('name')) and (t.get('host') == '' if addressless else vt(t.get('host'))) and (isinstance(t.get('port'), (int, float)) if addressless else Yd(t.get('port'))) and (isinstance(t.get('username'), str) if t.get('protocol') == 'telnet' else vt(t.get('username'))) and t.get('authType') in ('password', 'key', 'agent')):
        return False
    if t.get('keyPath') is not None and not isinstance(t['keyPath'], str): return False
    return True

def validate_tunnel(t):
    if not isinstance(t, dict): return False
    return vt(t.get('id')) and vt(t.get('name')) and Yd(t.get('localPort')) and vt(t.get('remoteIP')) and (Yd(t.get('remotePort')) or (t.get('tunnelType') == 'dynamic' and t.get('remotePort') == 0))

def validate_local_shell(t):
    if not isinstance(t, dict): return False
    if not (vt(t.get('id')) and vt(t.get('name'))): return False
    if t.get('launchMode') == 'vscodeProfile':
        if not vt(t.get('vscodeProfileName')): return False
    elif t.get('launchMode') == 'custom':
        if not vt(t.get('shellPath')): return False
    else: return False
    return Km(t.get('shellArgs')) and FW(t.get('env')) and Xn(t.get('group')) and Xn(t.get('cwd')) and Xn(t.get('startupCommand'))

def validate_local_server(t):
    if not isinstance(t, dict): return False
    if not (vt(t.get('id')) and vt(t.get('name')) and vt(t.get('executable'))): return False
    return Km(t.get('args')) and FW(t.get('env')) and Xn(t.get('group')) and Xn(t.get('cwd')) and Xn(t.get('description'))

def validate_auth_profile(t):
    if not isinstance(t, dict): return False
    return vt(t.get('id')) and vt(t.get('name')) and vt(t.get('username')) and t.get('authType') in ('password', 'key', 'agent') and (t.get('keyPath') is None or isinstance(t.get('keyPath'), str))

def validate_macro(t):
    return isinstance(t, dict) and isinstance(t.get('name'), str) and isinstance(t.get('text'), str)


# --- Deterministic UUID Generation for Stable Mesh Profiles ---
NAMESPACE = uuid.UUID("7a3e8e60-46f3-4df4-8d4e-60f1b29a8f4c")
def make_id(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name))


def generate_mesh_inventory(mode: str = "sovereign"):
    """
    Generates inventory for Nexus Terminal.
    mode='sovereign': Streamlined single-server configuration ("The Nexus Server" on 127.0.0.1:22).
    mode='full_mesh': Complete 7-layer hardware topology with all 9 peripheral servers.
    """
    auth_profiles = [
        {
            "id": make_id("auth-aaron-agent"),
            "name": "Aaron (SSH Agent / Sovereign)",
            "username": "aaron",
            "authType": "agent"
        }
    ]

    if mode == "full_mesh":
        auth_profiles.extend([
            {
                "id": make_id("auth-termux-agent"),
                "name": "Android Termux (SSH Agent)",
                "username": "u0_a260",
                "authType": "agent"
            },
            {
                "id": make_id("auth-router-root"),
                "name": "GL.iNet Router Root",
                "username": "root",
                "authType": "agent"
            }
        ])

    host_server_id = make_id("server-sovereign-nexus")

    if mode == "sovereign":
        servers = [
            {
                "id": host_server_id,
                "name": "👑 Sovereign Nexus Host (Mac Mini M4 Pro)",
                "host": "127.0.0.1",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.230",
                "group": "Nexus Sovereign/Host",
                "notes": "Master Memory Governor & Single-Chat Nexus Mother Ship (:4050)"
            }
        ]
        groups = [
            "Nexus Sovereign",
            "Nexus Sovereign/Host",
            "Nexus Sovereign/Local Consoles",
            "Nexus Sovereign/Daemons",
            "Nexus Sovereign/Services",
            "Nexus Sovereign/AI Inference",
            "Nexus Sovereign/Vision",
            "Nexus Sovereign/Storage",
            "Nexus Sovereign/Infrastructure",
            "Nexus Sovereign/Commands"
        ]
    else:
        # Full 9-layer hardware matrix
        servers = [
            {
                "id": host_server_id,
                "name": "🖥️ L1 - Host Mac Mini (M4 Pro)",
                "host": "127.0.0.1",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.230",
                "group": "Lauburu Mesh/Core Compute",
                "notes": "Master Memory Governor & Prompt Ingestion (24GB RAM, 90% Cap)"
            },
            {
                "id": make_id("server-L2"),
                "name": "💻 L2 - MacBook Pro (Intel / Metal RPC)",
                "host": "100.103.212.21",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "169.254.187.138",
                "group": "Lauburu Mesh/Core Compute",
                "notes": "40Gbps TB4 Bridge RPC Target (285GB SSD Model Vault)"
            },
            {
                "id": make_id("server-L3"),
                "name": "🐧 L3 - Linux Head Node (Ryzen 7 5700U)",
                "host": "100.101.39.98",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.224",
                "group": "Lauburu Mesh/Core Compute",
                "notes": "Docker Hub, Continuous AI Training & Petals DHT (16GB RAM)"
            },
            {
                "id": make_id("server-L4"),
                "name": "📱 L4 - Linux Tablet (Debian Touch DSP)",
                "host": "100.91.85.70",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.173",
                "group": "Lauburu Mesh/Peripheral Nodes",
                "notes": "Mobile Debian Linux Compute & Lightweight Biometrics (8GB RAM)"
            },
            {
                "id": make_id("server-L5"),
                "name": "🍏 L5 - MacBook Air (M4 / LoRA Distillation)",
                "host": "100.93.158.96",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.222",
                "group": "Lauburu Mesh/Peripheral Nodes",
                "notes": "Secondary Metal Performance Shaders Worker (16GB RAM)"
            },
            {
                "id": make_id("server-L6"),
                "name": "📱 L6 - Pixel 10 Pro XL (Tensor G5 / Termux)",
                "host": "100.73.38.87",
                "port": 8022,
                "protocol": "ssh",
                "username": "u0_a260",
                "authType": "agent",
                "authProfileId": make_id("auth-termux-agent"),
                "group": "Lauburu Mesh/Android Edges",
                "notes": "8K Vision Stream & Edge TPU (16GB RAM, termux-wake-lock)"
            },
            {
                "id": make_id("server-L7"),
                "name": "📱 L7 - Samsung Galaxy S20+ (Exynos 990 / Termux)",
                "host": "100.78.206.96",
                "port": 8022,
                "protocol": "ssh",
                "username": "u0_a260",
                "authType": "agent",
                "authProfileId": make_id("auth-termux-agent"),
                "group": "Lauburu Mesh/Android Edges",
                "notes": "Dedicated Automated UI Tester & OpenClaw Target (12GB RAM)"
            },
            {
                "id": make_id("server-L8"),
                "name": "🐧 L8 - Linux Mini (Intel 2018 Compute)",
                "host": "100.121.247.8",
                "port": 22,
                "protocol": "ssh",
                "username": "aaron",
                "authType": "agent",
                "authProfileId": make_id("auth-aaron-agent"),
                "altHost": "192.168.8.28",
                "group": "Lauburu Mesh/Compute Hub",
                "notes": "Secondary Docker Hub & RPC Sharding"
            },
            {
                "id": make_id("server-GW"),
                "name": "🛰️ GW - GL.iNet Sovereign Gateway (GL-MT3600BE)",
                "host": "192.168.8.1",
                "port": 22,
                "protocol": "ssh",
                "username": "root",
                "authType": "agent",
                "authProfileId": make_id("auth-router-root"),
                "altHost": "100.112.203.121",
                "group": "Lauburu Mesh/Network Infrastructure",
                "notes": "Wi-Fi 7 Sovereign Gateway, USB ADB Bridge & Core Healer"
            }
        ]
        groups = [
            "Lauburu Mesh",
            "Lauburu Mesh/Core Compute",
            "Lauburu Mesh/Peripheral Nodes",
            "Lauburu Mesh/Android Edges",
            "Lauburu Mesh/Compute Hub",
            "Lauburu Mesh/Network Infrastructure",
            "Lauburu Mesh/Local Consoles",
            "Lauburu Mesh/Daemons",
            "Lauburu Mesh/Services",
            "Lauburu Mesh/AI Inference",
            "Lauburu Mesh/Vision",
            "Lauburu Mesh/Commands"
        ]

    prefix = "Nexus Sovereign" if mode == "sovereign" else "Lauburu Mesh"

    local_shells = [
        {
            "id": make_id("shell-lauburu-monorepo"),
            "name": "⚡ Lauburu Monorepo Root Shell",
            "launchMode": "custom",
            "shellPath": "/bin/zsh",
            "shellArgs": ["-l"],
            "cwd": "/Volumes/Lauburu-Monorepo",
            "group": f"{prefix}/Local Consoles",
            "startupCommand": "echo '⚡ Sovereign Nexus Server Active — Host: M4 Pro Mac Mini'"
        },
        {
            "id": make_id("shell-screen-lens"),
            "name": "👁️ Screen Lens Sovereign Console",
            "launchMode": "custom",
            "shellPath": "/bin/zsh",
            "shellArgs": ["-l"],
            "cwd": "/Volumes/Lauburu-Monorepo/01_apps/screen_lens",
            "env": {
                "SCREEN_LENS_PORT": "4003",
                "NEXUS_MOTHER_SHIP": "http://127.0.0.1:4050"
            },
            "group": f"{prefix}/Local Consoles",
            "startupCommand": "nexus lens status"
        },
        {
            "id": make_id("shell-neo-execution"),
            "name": "⚡ Neo AI/ML Execution Terminal",
            "launchMode": "custom",
            "shellPath": "/bin/zsh",
            "shellArgs": ["-l"],
            "cwd": "/Volumes/Lauburu-Monorepo",
            "env": {
                "NEXUS_MOTHER_SHIP": "http://127.0.0.1:4050",
                "NEO_AUTO_ROUTING": "1"
            },
            "group": f"{prefix}/Local Consoles",
            "startupCommand": "nexus neo status"
        },
        {
            "id": make_id("shell-nexus-cli"),
            "name": "💬 Single-Chat Nexus Interactive CLI",
            "launchMode": "custom",
            "shellPath": "/bin/zsh",
            "shellArgs": ["-l"],
            "cwd": "/Volumes/Lauburu-Monorepo",
            "group": f"{prefix}/Local Consoles",
            "startupCommand": "nexus status"
        }
    ]

    local_servers = [
        {
            "id": make_id("localserver-nexus-chat"),
            "name": "💬 Single-Chat Nexus Mother Ship (:4050)",
            "executable": "/Users/aaron/.local/bin/nexus",
            "args": ["chat"],
            "cwd": "/Volumes/Lauburu-Monorepo",
            "group": f"{prefix}/Daemons",
            "description": "Sovereign Mother Ship Chat & SQLite Tri-Vault Gateway",
            "autoRestart": True,
            "maxAutoRestarts": 5
        },
        {
            "id": make_id("localserver-screen-lens-daemon"),
            "name": "👁️ Screen Lens Live MJPEG Daemon (:4003)",
            "executable": "/bin/bash",
            "args": ["-c", "lsof -i:4003 | grep LISTEN || (cd /Volumes/Lauburu-Monorepo/01_apps/screen_lens && python3 src/sovereign_remote_desktop_server.py)"],
            "cwd": "/Volumes/Lauburu-Monorepo/01_apps/screen_lens",
            "group": f"{prefix}/Daemons",
            "description": "Screen Lens Live Multipart MJPEG Stream and Local OCR Ingestion",
            "autoRestart": True,
            "maxAutoRestarts": 5
        }
    ]

    tunnels = [
        {
            "id": make_id("tunnel-nexus-chat"),
            "name": "💬 Single-Chat Nexus Mother Ship (Port 4050)",
            "tunnelType": "local",
            "localPort": 4050,
            "remoteIP": "127.0.0.1",
            "remotePort": 4050,
            "group": f"{prefix}/Services",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-prima-master"),
            "name": "👑 prima.cpp Master Orchestrator (Port 8082)",
            "tunnelType": "local",
            "localPort": 8082,
            "remoteIP": "127.0.0.1",
            "remotePort": 8082,
            "group": f"{prefix}/AI Inference",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-qwen-redteam"),
            "name": "🔥 Qwen 3.8 Max Abliterated Red Team (Port 8083)",
            "tunnelType": "local",
            "localPort": 8083,
            "remoteIP": "127.0.0.1",
            "remotePort": 8083,
            "group": f"{prefix}/AI Inference",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-qwen-coder"),
            "name": "⚡ Qwen 2.5 Coder 7B Syntax Worker (Port 8081)",
            "tunnelType": "local",
            "localPort": 8081,
            "remoteIP": "127.0.0.1",
            "remotePort": 8081,
            "group": f"{prefix}/AI Inference",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-screen-lens-mjpeg"),
            "name": "👁️ Screen Lens Live MJPEG Stream (Port 4003)",
            "tunnelType": "local",
            "localPort": 4003,
            "remoteIP": "127.0.0.1",
            "remotePort": 4003,
            "group": f"{prefix}/Vision",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-seaweedfs"),
            "name": "🌊 SeaweedFS Distributed DFS Filer (Port 8888)",
            "tunnelType": "local",
            "localPort": 8888,
            "remoteIP": "127.0.0.1",
            "remotePort": 8888,
            "group": f"{prefix}/Storage",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-self-healing-hub"),
            "name": "🛡️ Self-Healing Hub Orchestrator (Port 18802)",
            "tunnelType": "local",
            "localPort": 18802,
            "remoteIP": "127.0.0.1",
            "remotePort": 18802,
            "group": f"{prefix}/Infrastructure",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-neo-engine"),
            "name": "⚡ Neo AI Execution Engine (L8 Linux Mini Port 8080)",
            "tunnelType": "local",
            "localPort": 8080,
            "remoteIP": "192.168.2.3",
            "remotePort": 8080,
            "group": f"{prefix}/AI Inference",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-s20-router-control"),
            "name": "📱 Samsung S20+ Sovereign Router Control Center (Port 9090)",
            "tunnelType": "local",
            "localPort": 9090,
            "remoteIP": "192.168.8.131",
            "remotePort": 9090,
            "group": f"{prefix}/Infrastructure",
            "defaultServerId": host_server_id
        },
        {
            "id": make_id("tunnel-seaweedfs-webdav"),
            "name": "🌊 SeaweedFS WebDAV Storage Gateway (Port 7333)",
            "tunnelType": "local",
            "localPort": 7333,
            "remoteIP": "100.119.199.76",
            "remotePort": 7333,
            "group": f"{prefix}/Storage",
            "defaultServerId": host_server_id
        }
    ]

    macros = [
        {
            "id": make_id("macro-mesh-status"),
            "name": "Nexus: Mesh Status",
            "text": "nexus status\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-nexus-health"),
            "name": "Nexus: Query Health",
            "text": "curl -s http://127.0.0.1:4050/api/health | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-nexus-threads"),
            "name": "Nexus: List Chat Threads",
            "text": "curl -s http://127.0.0.1:4050/api/chat/nexus/threads | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-lora-sync"),
            "name": "Nexus: Trigger LoRA Sync",
            "text": "curl -s -X POST http://127.0.0.1:4050/api/chat/nexus/lora/sync | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-enable-pan"),
            "name": "Nexus: Escalate to Bluetooth PAN",
            "text": "nexus dispatch --target all --directive ENABLE_PAN\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-status"),
            "name": "Screen Lens: Status",
            "text": "nexus lens status\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-latest"),
            "name": "Screen Lens: Latest OCR",
            "text": "nexus lens latest --limit 3\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-report"),
            "name": "Screen Lens: Report to Nexus VLA",
            "text": "nexus lens report\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-open-stream"),
            "name": "Screen Lens: Open Live Stream (:4003)",
            "text": "open http://localhost:4003/stream.mjpg\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-scrcpy-pixel"),
            "name": "Screen Lens: Scrcpy Pixel 10 GUI",
            "text": "bash 06_scripts_and_tooling/screen_lens/open_scrcpy_gui.sh pixel\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-scrcpy-s20"),
            "name": "Screen Lens: Scrcpy Samsung S20 GUI",
            "text": "bash 06_scripts_and_tooling/screen_lens/open_scrcpy_gui.sh s20\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-screen-lens-stream"),
            "name": "Screen Lens: Stream Telemetry",
            "text": "tail -f /Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md\n",
            "group": f"{prefix}/Vision",
            "secret": False
        },
        {
            "id": make_id("macro-neo-status"),
            "name": "Neo: Check Integrations",
            "text": "nexus neo status\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-neo-task"),
            "name": "Neo: Dispatch AI/ML Task",
            "text": "nexus neo task \"Verify movesense 512Hz stream and Screen Lens live OCR\"\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-spec11-audit"),
            "name": "Spec-11: Security Red/Blue Audit",
            "text": "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/security/spec11_security_auditor.py\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-s20-router-status"),
            "name": "S20+ Router: Query Status & WAN IPv6",
            "text": "curl -s http://192.168.8.131:9090/router/status | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-s20-router-clients"),
            "name": "S20+ Router: Query Connected Clients",
            "text": "curl -s http://192.168.8.131:9090/router/clients | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-neo-health-check"),
            "name": "Neo: Query L8 Health Server",
            "text": "curl -s http://192.168.2.3:8080/health | jq .\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-wireguard-status"),
            "name": "WireGuard: Check Public IPv6 Peers",
            "text": "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/wireguard_manager.py\n",
            "group": f"{prefix}/Commands",
            "secret": False
        },
        {
            "id": make_id("macro-mobile-dfs-sync"),
            "name": "Storage: Sync S20+ & Pixel 10 to DFS",
            "text": "bash /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/storage/mobile_dfs_sync.sh\n",
            "group": f"{prefix}/Storage",
            "secret": False
        }
    ]

    settings = {
        "nexus.ssh.trustNewHosts": True,
        "nexus.ssh.keepaliveInterval": 15,
        "nexus.ssh.keepaliveCountMax": 4,
        "nexus.ssh.multiplexing.enabled": True,
        "nexus.terminal.keyboardPassthrough": True,
        "nexus.terminal.openLocation": "terminal",
        "nexus.ui.showTreeDescriptions": True,
        "nexus.logging.sessionTranscripts": True,
        "nexus.logging.sessionLogDirectory": "/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/nexus_transcripts",
        "nexus.scripts.path": "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/nexus",
        "nexus.terminal.macros.autoTrigger": True
    }

    return {
        "version": 2,
        "exportType": "share",
        "exportedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "inventoryStatusPollPerSource": True,
        "servers": servers,
        "tunnels": tunnels,
        "serialProfiles": [],
        "localShellProfiles": local_shells,
        "localServers": local_servers,
        "authProfiles": auth_profiles,
        "groups": groups,
        "macros": macros,
        "settings": settings
    }


def validate_all(inventory):
    print("=== VALIDATING PROFILES ===")
    for s in inventory["servers"]:
        assert validate_server(s), f"Server failed validation: {s['name']}"
    print(f"✓ All {len(inventory['servers'])} servers validated successfully.")

    for t in inventory["tunnels"]:
        assert validate_tunnel(t), f"Tunnel failed validation: {t['name']}"
    print(f"✓ All {len(inventory['tunnels'])} tunnels validated successfully.")

    for sh in inventory["localShellProfiles"]:
        assert validate_local_shell(sh), f"Local shell failed validation: {sh['name']}"
    print(f"✓ All {len(inventory['localShellProfiles'])} local shell profiles validated successfully.")

    for ls in inventory["localServers"]:
        assert validate_local_server(ls), f"Local server failed validation: {ls['name']}"
    print(f"✓ All {len(inventory['localServers'])} local servers validated successfully.")

    for a in inventory["authProfiles"]:
        assert validate_auth_profile(a), f"Auth profile failed validation: {a['name']}"
    print(f"✓ All {len(inventory['authProfiles'])} auth profiles validated successfully.")

    for m in inventory["macros"]:
        assert validate_macro(m), f"Macro failed validation: {m['name']}"
    print(f"✓ All {len(inventory['macros'])} macros validated successfully.")


def provision_state_db(inventory, db_path):
    print(f"\n=== PROVISIONING STATE DATABASE: {db_path} ===")
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping DB update.")
        return

    # Backup first
    backup_path = db_path + ".pre_nexus_provision.bak"
    shutil.copy2(db_path, backup_path)
    print(f"Backed up SQLite DB to {backup_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load existing extension state
    cur.execute("SELECT value FROM ItemTable WHERE key = 'sentriflow.vscode-nexterminal'")
    row = cur.fetchone()
    state = json.loads(row[0]) if row else {}

    # Purge any bogus or corrupt servers (e.g. host containing '.json' or empty)
    existing_servers = state.get("nexus.servers", [])
    clean_existing = [s for s in existing_servers if isinstance(s, dict) and not s.get("host", "").endswith(".json")]

    # Overwrite state fields with clean sovereign inventory
    state["nexus.inventory.statusPollSettingMigrated"] = True
    state["nexus.servers"] = inventory["servers"]
    state["nexus.tunnels"] = inventory["tunnels"]
    state["nexus.serialProfiles"] = inventory["serialProfiles"]
    state["nexus.localShellProfiles"] = inventory["localShellProfiles"]
    state["nexus.localServers"] = inventory["localServers"]
    state["nexus.authProfiles"] = inventory["authProfiles"]
    state["nexus.groups"] = inventory["groups"]
    state["nexus.macros"] = inventory["macros"]

    new_val = json.dumps(state)
    cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('sentriflow.vscode-nexterminal', ?)", (new_val,))

    # Ensure workbench activity pinned
    cur.execute("SELECT value FROM ItemTable WHERE key = 'workbench.activity.pinnedViewlets2'")
    pv_row = cur.fetchone()
    if pv_row:
        pinned = json.loads(pv_row[0])
        has_nexus = any(x.get("id") == "workbench.view.extension.nexus" for x in pinned)
        if not has_nexus:
            pinned.append({"id": "workbench.view.extension.nexus", "pinned": True, "visible": True, "order": 23})
            cur.execute("UPDATE ItemTable SET value = ? WHERE key = 'workbench.activity.pinnedViewlets2'", (json.dumps(pinned),))
            print("Pinned Nexus viewlet to Activity Bar.")

    # Ensure all Nexus views are unhidden
    hidden_views = [
        {"id": "nexusCommandCenter", "isHidden": False},
        {"id": "nexusTunnels", "isHidden": False},
        {"id": "nexusNetworkServers", "isHidden": False},
        {"id": "nexusFileExplorer", "isHidden": False},
        {"id": "nexusMacros", "isHidden": False},
        {"id": "nexusScripts", "isHidden": False},
        {"id": "nexusSettings", "isHidden": False}
    ]
    cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('workbench.view.extension.nexus.state.hidden', ?)", (json.dumps(hidden_views),))

    conn.commit()
    conn.close()
    print(f"✓ Successfully updated SQLite state in {db_path}")


def update_settings_json(settings_path, new_settings):
    print(f"\n=== UPDATING SETTINGS: {settings_path} ===")
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    existing = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse existing {settings_path}: {e}")

    existing.update(new_settings)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4)
    print(f"✓ Successfully updated {len(new_settings)} settings in {settings_path}")


def main():
    print("🚀 Initializing Nexus Terminal Extension Provisioner for Sovereign Nexus Server...")
    
    # 1. Generate Sovereign Server Inventory (Default: The Nexus Server)
    sovereign_inv = generate_mesh_inventory(mode="sovereign")
    validate_all(sovereign_inv)

    # 2. Export canonical sovereign configuration to nexus-config-shared.json
    monorepo_export = "/Volumes/Lauburu-Monorepo/nexus-config-shared.json"
    with open(monorepo_export, "w", encoding="utf-8") as f:
        json.dump(sovereign_inv, f, indent=2)
    print(f"\n✓ Exported Sovereign Nexus Server configuration to {monorepo_export}")

    # 3. Export full mesh topology archive to nexus-mesh-full-topology.json
    mesh_inv = generate_mesh_inventory(mode="full_mesh")
    validate_all(mesh_inv)
    mesh_export = "/Volumes/Lauburu-Monorepo/nexus-mesh-full-topology.json"
    with open(mesh_export, "w", encoding="utf-8") as f:
        json.dump(mesh_inv, f, indent=2)
    print(f"✓ Exported Full 9-Layer Mesh Topology archive to {mesh_export}")

    # 4. Update Antigravity IDE globalStorage state.vscdb
    antigravity_db = os.path.expanduser("~/Library/Application Support/Antigravity IDE/User/globalStorage/state.vscdb")
    provision_state_db(sovereign_inv, antigravity_db)

    # 5. Update VS Code globalStorage state.vscdb if present
    vscode_db = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/state.vscdb")
    if os.path.exists(vscode_db):
        provision_state_db(sovereign_inv, vscode_db)

    # 6. Update Antigravity IDE User settings.json
    antigravity_settings = os.path.expanduser("~/Library/Application Support/Antigravity IDE/User/settings.json")
    update_settings_json(antigravity_settings, sovereign_inv["settings"])

    # 7. Update Workspace .vscode/settings.json
    workspace_settings = "/Volumes/Lauburu-Monorepo/.vscode/settings.json"
    update_settings_json(workspace_settings, sovereign_inv["settings"])

    print("\n🎉 The Nexus Server configuration successfully provisioned and synchronized!")

if __name__ == "__main__":
    main()
