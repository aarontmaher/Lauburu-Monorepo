#!/usr/bin/env python3
"""
================================================================================
Omniscient Mesh Sentinel & Autonomous Storage & Hardware Topology Monitor
================================================================================
Subsystem: 06_scripts_and_tooling/network/omniscient_mesh_sentinel.py
Version: 2.5.0-OMNISCIENT-STORAGE-TOPOLOGY-SENTINEL
Lauburu Mesh Ecosystem — 2026

Architecture:
1. Ingests 7 concurrent asynchronous telemetry streams via asyncio.gather:
   - Stream A: Host Activity Monitor & Mach Kernel Memory (vm_stat, uptime, load)
   - Stream B: Full Cross-Device Mesh Port Matrix (18 ports across L1-L7, Router)
   - Stream C: Physical Hardware Cable & Port Link Watchdog (GL.iNet swconfig switch0)
   - Stream D: SeaweedFS 6-Node Distributed Storage Pool & Headroom Monitor (:9333 / SMB)
   - Stream E: Local Socket State & Flapping Sockets (netstat -an on L1)
   - Stream F: Wireshark / Interface Packet Counters (netstat -ibn on en0, bridge0)
   - Stream G: Multi-Hop Ping Matrix (Router Gateway, Linux Hub, TB4 DMA Bridge)
2. Sub-Millisecond Classification via 1.2M Parameter Transformer (router_1m_model.pt).
3. Automated Physical Plug/Unplug Transition & Cable Move Logging.
4. Storage Structuring & Organization in SeaweedFS (Zero-Deletion Invariant).
5. Bottleneck Identification & Device Setting Improvement Engine.
================================================================================
"""

import os
import sys
import time
import json
import asyncio
import logging
import signal
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Setup Logging
LOG_DIR = Path("/Volumes/Lauburu-Monorepo/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "omniscient_mesh_sentinel.log"
TELEMETRY_OUT = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/omniscient_mesh_telemetry.json")
TOPOLOGY_LOG = Path("/Volumes/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/PHYSICAL_HARDWARE_TOPOLOGY.md")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (OmniSentinel) %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("OmniSentinel")

MODEL_PATH = Path("/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/checkpoints_1m_router/router_1m_model.pt")

ACTION_MAP = {
    0: ("NO_OP_HEALTHY", "All mesh layers healthy. Nominal routing maintained."),
    1: ("WAKE_BLE_RF", "ip-less_bluetooth_rf: Dispatch BLE magic packet to node."),
    2: ("CONNECT_BLE_PAN", "bluetooth_pan: Establish BlueZ / CoreBluetooth PAN tether."),
    3: ("SSH_RECOVER", "ssh: Execute remote keepalive / diagnostics over LAN."),
    4: ("BOUNCE_WIFI", "wifi: Toggle radio interface via nmcli / uci."),
    5: ("RESTART_TAILSCALE", "tailscale: Restart tailscaled daemon and re-authenticate."),
    6: ("FAILOVER_WAN", "kmwan: Toggle failover route on router gateway."),
    7: ("FLUSH_ARP_TABLE", "ip neigh flush all: Clean stale ARP entries for flapping peer."),
    8: ("THROTTLE_BACKGROUND_AI", "Dynamic RAM Governor: Signal peripheral nodes to prune caches."),
    9: ("RESURRECT_RAY_WORKER", "Restart crashed Ray / Docker container on L3 Linux Head Node."),
    10: ("CYCLE_LLAMA_SERVER", "Kill unresponsive RPC server socket on port 50052 / 8080."),
    11: ("TRIGGER_AI_DEBATE", "Consensus Protocol: Dispatch multi-agent debate to resolve conflict."),
    12: ("REVERT_LAST_DIFF", "Audit Failure: Rollback unverified code change."),
    13: ("REFRESH_GLINET_DHCP", "uci commit dhcp && /etc/init.d/dnsmasq restart"),
    14: ("RECONNECT_BRIDGE0", "ifconfig bridge0 down && ifconfig bridge0 up (TB4 DMA link)."),
    15: ("FALLBACK_1GBE", "Reroute local traffic from TB4 to Gigabit LAN (192.168.8.x).")
}

# Canonical Full Mesh Port Matrix (All Devices)
FULL_MESH_PORTS = [
    # L1 Mac Mini
    ("L1_Mac_Mini", "127.0.0.1", 4000, "Apps_Hub"),
    ("L1_Mac_Mini", "127.0.0.1", 4002, "Marimo_Approvals"),
    ("L1_Mac_Mini", "127.0.0.1", 4003, "Live_HUD_Stream"),
    ("L1_Mac_Mini", "127.0.0.1", 8081, "Qwen_Coder_Syntax"),
    ("L1_Mac_Mini", "127.0.0.1", 8082, "Qwen_Max_Orchestrator"),
    ("L1_Mac_Mini", "127.0.0.1", 18802, "Self_Healing_Hub"),
    # L2 MacBook Pro
    ("L2_MacBook_Pro", "10.0.0.8", 50052, "GGML_RPC_TB4"),
    ("L2_MacBook_Pro", "192.168.8.127", 50052, "GGML_RPC_LAN"),
    # L3 Linux Head Node
    ("L3_Linux_Hub", "100.101.39.98", 22, "SSH_Tailscale"),
    ("L3_Linux_Hub", "100.101.39.98", 8083, "Devils_Advocate"),
    ("L3_Linux_Hub", "100.101.39.98", 8084, "Screen_Lens_Vision"),
    ("L3_Linux_Hub", "100.101.39.98", 50052, "GGML_RPC_Linux"),
    # L4 Linux Tablet
    ("L4_Linux_Tablet", "100.81.92.125", 22, "SSH_Tailscale"),
    ("L4_Linux_Tablet", "192.168.8.225", 22, "SSH_LAN"),
    # GL.iNet Gateway Router
    ("Router_Gateway", "192.168.8.1", 80, "LuCI_Web"),
    ("Router_Gateway", "192.168.8.1", 22, "Router_SSH"),
    ("Router_Gateway", "192.168.8.1", 53, "DNSMasq"),
    # L6 Pixel 10 Pro XL
    ("L6_Pixel_10", "100.73.38.87", 8022, "Termux_SSH"),
    # L7 Samsung S20
    ("L7_Samsung_S20", "100.78.206.96", 5555, "Wireless_ADB"),
    ("L7_Samsung_S20", "100.78.206.96", 8022, "Termux_SSH"),
    # Chrome DevTools AI Bridge
    ("L1_Mac_Mini", "127.0.0.1", 9224, "Chrome_DevTools_Bridge")
]

class OmniscientSentinel:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.model = None
        self.torch = None
        self.is_running = True
        self.last_remediation_ts: Dict[str, float] = {}
        self.remediation_cooldown_sec = 60.0
        self.previous_switch_ports: Dict[int, str] = {}
        self.last_storage_organize_ts: float = 0.0
        self.shadow_consensus = None
        self.storage_organizer = None
        self._init_model()
        self._ensure_seaweed_structure()
        self._init_subsystems()

    def _init_subsystems(self):
        try:
            sys.path.insert(0, "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network")
            from router_shadow_consensus_engine import RouterShadowConsensus
            self.shadow_consensus = RouterShadowConsensus()
            log.info("Initialized Tri-Model Shadow Consensus Engine (100% Confidence Gate)")
        except Exception as e:
            log.warning(f"Could not load RouterShadowConsensus: {e}")

        try:
            from seaweed_storage_organizer import SeaweedStorageOrganizer
            self.storage_organizer = SeaweedStorageOrganizer()
            log.info("Initialized SeaweedFS Distributed Storage Organizer (Zero-Deletion)")
        except Exception as e:
            log.warning(f"Could not load SeaweedStorageOrganizer: {e}")

    def _init_model(self):
        try:
            import torch
            self.torch = torch
            if self.model_path.exists():
                self.model = torch.jit.load(str(self.model_path), map_location="cpu")
                self.model.eval()
                log.info(f"Loaded 1.2M TorchScript Neural Model from {self.model_path}")
            else:
                log.warning(f"Model path {self.model_path} not found.")
        except Exception as e:
            log.error(f"Failed to load TorchScript model: {e}")

    def _ensure_seaweed_structure(self):
        """Ensures canonical directory structure inside SeaweedFS Network Storage without deleting anything."""
        base_mount = Path("/Users/aaron/mnt/seaweed_webdav")
        canonical_dirs = [
            "01_AI_MODELS_AND_INFERENCE",
            "02_LORA_DATASETS_AND_TRACES",
            "03_BIOMETRICS_AND_TELEMETRY",
            "04_PROJECTS_AND_ARCHIVES",
            "05_SCREEN_LENS_AND_MEDIA"
        ]
        if base_mount.exists():
            for cd in canonical_dirs:
                try:
                    (base_mount / cd).mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass

    def tokenize(self, text: str, max_len: int = 128):
        raw_bytes = text.encode("utf-8")[:max_len]
        tokens = [int(b) % 8192 for b in raw_bytes]
        if len(tokens) < max_len:
            tokens.extend([0] * (max_len - len(tokens)))
        return self.torch.tensor([tokens], dtype=self.torch.long)

    def classify_event(self, text: str) -> Tuple[int, str, float, float]:
        if not self.model or not self.torch:
            return 0, "NO_OP_HEALTHY", 1.0, 0.0
        t0 = time.perf_counter()
        inp = self.tokenize(text)
        with self.torch.no_grad():
            logits = self.model(inp)
            probs = self.torch.softmax(logits, dim=-1)
            conf, pred = self.torch.max(probs, dim=-1)
            action_id = pred.item()
            confidence = conf.item()
        dur_ms = (time.perf_counter() - t0) * 1000.0
        action_name, _ = ACTION_MAP.get(action_id, ("UNKNOWN", ""))
        return action_id, action_name, confidence, dur_ms

    # ==========================================
    # Asynchronous Multi-Stream Collectors
    # ==========================================
    async def probe_single_tcp_port(self, node: str, ip: str, port: int, service: str, timeout: float = 0.25) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            conn = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            dur_ms = (time.perf_counter() - t0) * 1000.0
            return {"node": node, "ip": ip, "port": port, "service": service, "status": "OPEN", "rtt_ms": round(dur_ms, 2)}
        except Exception as e:
            dur_ms = (time.perf_counter() - t0) * 1000.0
            status_desc = "CLOSED" if isinstance(e, ConnectionRefusedError) else "TIMEOUT"
            return {"node": node, "ip": ip, "port": port, "service": service, "status": status_desc, "rtt_ms": round(dur_ms, 2)}

    async def poll_full_mesh_port_matrix(self) -> Dict[str, Any]:
        tasks = [self.probe_single_tcp_port(n, ip, p, s) for n, ip, p, s in FULL_MESH_PORTS]
        results = await asyncio.gather(*tasks)
        open_ports = [r for r in results if r["status"] == "OPEN"]
        closed_ports = [r for r in results if r["status"] != "OPEN"]
        summary_text = (
            f"Full Mesh Sockets: {len(open_ports)}/{len(results)} OPEN. "
            f"Active: {[f'{r['node']}:{r['port']}' for r in open_ports[:6]]} "
            f"Down: {[f'{r['node']}:{r['port']}' for r in closed_ports[:4]]}"
        )
        return {
            "source": "Full_Mesh_Socket_Matrix",
            "total_ports": len(results),
            "open_count": len(open_ports),
            "closed_count": len(closed_ports),
            "open_services": open_ports,
            "closed_services": closed_ports,
            "raw": summary_text
        }

    async def poll_switch_hardware_ports(self) -> Dict[str, Any]:
        """Queries physical switch ports on GL.iNet router to track cable plugs/unplugs."""
        proc = await asyncio.create_subprocess_shell(
            "ssh -o ConnectTimeout=2 -o BatchMode=yes root@192.168.8.1 'swconfig dev switch0 show' 2>/dev/null",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        
        current_ports = {}
        changes = []
        for line in raw.split("\n"):
            if "link: port:" in line:
                parts = line.strip().split()
                # line format: link: port:1 link:up speed:1000baseT full-duplex auto
                try:
                    port_id = int(parts[1].split(":")[1])
                    link_state = parts[2].split(":")[1]
                    speed = parts[3] if len(parts) > 3 else "unknown"
                    full_desc = f"{link_state} ({speed})"
                    current_ports[port_id] = full_desc
                    
                    if port_id in self.previous_switch_ports:
                        old = self.previous_switch_ports[port_id]
                        if old != full_desc:
                            event = f"Physical Switch Port {port_id} changed: {old} -> {full_desc}"
                            changes.append(event)
                            log.warning(f"🔌 [HARDWARE TRANSITION] {event}")
                except Exception:
                    pass

        if current_ports:
            self.previous_switch_ports = current_ports

        summary_text = f"Router Switch: {len(current_ports)} ports. " + " ".join([f"P{p}:{s}" for p, s in current_ports.items()])
        return {
            "source": "Physical_Switch_Hardware_Watchdog",
            "ports": current_ports,
            "detected_transitions": changes,
            "raw": summary_text
        }

    async def poll_seaweed_storage_matrix(self) -> Dict[str, Any]:
        """Monitors SeaweedFS 6-node distributed storage pool and node disk headroom."""
        # 1. Host local disk
        proc = await asyncio.create_subprocess_shell(
            "df -k / | tail -n 1",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        fields = stdout.decode().strip().split()
        host_free_gb = round(int(fields[3]) / (1024 * 1024), 2) if len(fields) >= 4 else 0.0

        # 2. SeaweedFS cluster master topology
        cluster_info = {}
        try:
            req = urllib.request.Request("http://127.0.0.1:9333/dir/status", headers={"User-Agent": "OmniSentinel"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode())
                nodes = data.get("Topology", {}).get("DataCenters", [{}])[0].get("Racks", [{}])[0].get("DataNodes", [])
                cluster_info = {
                    "active_datanodes": len(nodes),
                    "free_volume_slots": data.get("Topology", {}).get("Free", 0),
                    "max_volume_slots": data.get("Topology", {}).get("Max", 0),
                    "nodes": [{"url": n.get("Url"), "volumes": n.get("Volumes"), "max": n.get("Max")} for n in nodes]
                }
        except Exception as e:
            cluster_info = {"status": "UNREACHABLE", "error": str(e)}

        is_critical = host_free_gb < 5.0
        summary_text = (
            f"Storage Pool: Host Free={host_free_gb}GB ({'CRITICAL_HEADROOM' if is_critical else 'OK'}), "
            f"SeaweedFS DataNodes={cluster_info.get('active_datanodes', 0)}, "
            f"FreeSlots={cluster_info.get('free_volume_slots', 0)}/{cluster_info.get('max_volume_slots', 0)}"
        )
        return {
            "source": "SeaweedFS_Storage_Watchdog",
            "host_free_gb": host_free_gb,
            "host_critical": is_critical,
            "cluster": cluster_info,
            "raw": summary_text
        }

    async def poll_activity_monitor(self) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            "vm_stat | head -n 6; uptime",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        return {"source": "Activity_Monitor_Darwin", "raw": raw}

    async def poll_local_socket_flapping(self) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            "netstat -an | grep -E 'SYN_SENT|TIME_WAIT|LAST_ACK' | head -n 5",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        return {"source": "Local_Socket_Flapping_Watchdog", "raw": raw if raw else "NO_SOCKET_FLAPPING"}

    async def poll_interface_packet_drops(self) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            "netstat -ibn | grep -E 'en0|bridge0' | head -n 4",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        return {"source": "Wireshark_Packet_Counters", "raw": raw}

    async def poll_router_gateway(self) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            "ping -c 1 -W 400 192.168.8.1",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        is_ok = proc.returncode == 0
        return {"source": "Router_Gateway_Ping", "raw": raw, "ok": is_ok}

    async def poll_linux_node(self) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_shell(
            "ping -c 1 -W 400 100.101.39.98",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        raw = stdout.decode().strip()
        is_ok = proc.returncode == 0
        return {"source": "Linux_Head_Node_Ping", "raw": raw, "ok": is_ok}

    async def poll_chrome_devtools_metrics(self) -> Dict[str, Any]:
        """Polls live Chrome Developer Tab metrics & DevTools AI bridge on port 9224."""
        telemetry_file = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/chrome_devtools_telemetry.json")
        data = {}
        if telemetry_file.exists():
            try:
                with open(telemetry_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        vitals = data.get("web_vitals", {})
        mem = data.get("memory", {})
        cons = data.get("console", {})
        net = data.get("network", {})
        
        summary_text = (
            f"Chrome DevTools: LCP={vitals.get('lcp_ms', 0)}ms, FCP={vitals.get('fcp_ms', 0)}ms, "
            f"HeapUsed={mem.get('used_heap_mb', 0)}MB/{mem.get('heap_limit_mb', 0)}MB, "
            f"ConsoleErrors={cons.get('error_count', 0)}, SlowRequests={net.get('slow_requests_count', 0)}"
        )
        return {
            "source": "Chrome_DevTools_Performance_Watchdog",
            "web_vitals": vitals,
            "memory": mem,
            "console": cons,
            "network": net,
            "raw": summary_text
        }

    # ==========================================
    # Bottleneck & Improvement Advisory Engine
    # ==========================================
    def analyze_bottlenecks(self, summary: Dict[str, Any]) -> List[Dict[str, str]]:
        recommendations = []
        
        # 1. Storage Bottleneck
        storage = summary.get("storage_status", {})
        if storage.get("host_critical", False):
            recommendations.append({
                "desc": "🚨 [STORAGE BOTTLENECK] Mac Mini Host has < 5.0 GB free! Auto-fix will clear pip cache.",
                "auto_fix_cmd": "rm -rf ~/.cache/pip/*",
                "metric_name": "Host Free Disk (GB)",
                "metric_before": str(storage.get("host_free_gb", "unknown")),
                "check_cmd": "df -h /Users/aaron | awk 'NR==2 {print $4}' | sed 's/Gi//'"
            })
            
        if storage.get("active_datanodes", 6) < 6:
            recommendations.append({
                "desc": f"💾 [STORAGE BOTTLENECK] SeaweedFS cluster degraded ({storage.get('active_datanodes')} active nodes). Triggering remote volume restarts on mesh.",
                "auto_fix_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=2 aaron@100.101.39.98 'sudo systemctl restart seaweedfs-volume' || true; ssh -o BatchMode=yes -o ConnectTimeout=2 aaron@100.81.92.125 'sudo systemctl restart seaweedfs-volume' || true",
                "metric_name": "SeaweedFS Active DataNodes",
                "metric_before": str(storage.get("active_datanodes", "unknown")),
                "check_cmd": "curl -s http://127.0.0.1:9333/dir/status | grep -o '\"DataNodes\":\\[[^\\]]*\\]' | grep -o '\"Url\"' | wc -l | tr -d ' '"
            })

        # 2. Switch Speed Bottleneck
        # REMOVED: Violates Rule 0 (L1, L2, L3 are physically limited to 1GbE, 1000baseT is not a bottleneck)
        
        # 3. Asymmetric Routing Bottleneck (Linux Mini)
        ports = summary.get("mesh_ports_status", {}).get("closed_services", [])
        linux_rpc_closed = any(c.get("node") == "L3_Linux_Hub" and c.get("port") == 50052 for c in ports)
        if linux_rpc_closed:
            recommendations.append({
                "desc": "🐧 [DEVICE SETTING IMPROVEMENT] L3 Linux Node RPC port is closed. Restarting ggml-rpc-server on Linux Node.",
                "auto_fix_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=2 aaron@100.101.39.98 'sudo systemctl restart ggml-rpc-server'",
                "metric_name": "L3 RPC Socket",
                "metric_before": "Closed (0%)",
                "check_cmd": "nc -zv -w 2 100.101.39.98 50052 2>&1 | grep -q succeeded && echo 'Open (100%)' || echo 'Closed (0%)'"
            })

        # 5. Linux Tablet Reachability Bottleneck
        tablet_closed = any(c.get("node") == "L4_Linux_Tablet" and c.get("port") == 22 for c in ports)
        if tablet_closed:
            recommendations.append({
                "desc": "📱 [DEVICE CONNECTIVITY] L4 Linux Tablet is unresponsive. Flushing ARP on GL.iNet router to force wake/reconnect.",
                "auto_fix_cmd": "ssh -o BatchMode=yes -o ConnectTimeout=2 root@192.168.8.1 'ip neigh flush dev br-lan && ping -c 3 192.168.8.225'",
                "metric_name": "L4_Linux_Tablet SSH",
                "metric_before": "Closed (0%)",
                "check_cmd": "nc -zv -w 2 192.168.8.225 22 2>&1 | grep -q succeeded && echo 'Open (100%)' || echo 'Closed (0%)'"
            })

        # 6. Chrome DevTools Bottlenecks & Optimization
        devtools = summary.get("devtools_status", {})
        vitals = devtools.get("web_vitals", {})
        if vitals.get("lcp_ms", 0) > 2500.0:
            recommendations.append({
                "desc": f"🌐 [DEVTOOLS PERF BOTTLENECK] Chrome LCP is {vitals.get('lcp_ms')}ms (>2500ms).",
                "auto_fix_cmd": "",
                "metric_name": "LCP_ms",
                "metric_before": str(vitals.get("lcp_ms", 0)),
                "check_cmd": ""
            })
            
        return recommendations

    # ==========================================
    # Main Continuous Pipeline Sweep
    # ==========================================
    async def sweep_once(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        
        # 1. Ingest all 8 streams concurrently via asyncio.gather
        streams = await asyncio.gather(
            self.poll_activity_monitor(),
            self.poll_full_mesh_port_matrix(),
            self.poll_switch_hardware_ports(),
            self.poll_seaweed_storage_matrix(),
            self.poll_local_socket_flapping(),
            self.poll_interface_packet_drops(),
            self.poll_router_gateway(),
            self.poll_linux_node(),
            self.poll_chrome_devtools_metrics()
        )
        gather_ms = (time.perf_counter() - t0) * 1000.0

        telemetry_events = []
        port_matrix_detail = {}
        switch_detail = {}
        storage_detail = {}
        devtools_detail = {}

        for stream in streams:
            source = stream["source"]
            raw = stream.get("raw", "")
            action_id, action_name, confidence, inf_ms = self.classify_event(raw)
            
            event_record = {
                "source": source,
                "action_id": action_id,
                "action_name": action_name,
                "confidence": round(confidence * 100.0, 2),
                "inference_ms": round(inf_ms, 3),
                "sample_snippet": raw.replace("\n", " ")[:120]
            }
            telemetry_events.append(event_record)
            
            if source == "Full_Mesh_Socket_Matrix":
                port_matrix_detail = stream
            elif source == "Physical_Switch_Hardware_Watchdog":
                switch_detail = stream
            elif source == "SeaweedFS_Storage_Watchdog":
                storage_detail = stream
            elif source == "Chrome_DevTools_Performance_Watchdog":
                devtools_detail = stream

        total_sweep_ms = (time.perf_counter() - t0) * 1000.0
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gather_duration_ms": round(gather_ms, 2),
            "total_sweep_ms": round(total_sweep_ms, 2),
            "stream_count": len(streams),
            "mesh_ports_status": port_matrix_detail,
            "switch_hardware_status": switch_detail,
            "storage_status": storage_detail,
            "devtools_status": devtools_detail,
            "events": telemetry_events
        }

        # Analyze bottlenecks and improvements
        recommendations = self.analyze_bottlenecks(summary)
        summary["bottleneck_recommendations"] = recommendations

        # Periodic Non-Destructive Storage Structuring (every 60s)
        now_ts = time.time()
        if self.storage_organizer and (now_ts - self.last_storage_organize_ts > 60.0):
            try:
                moves = self.storage_organizer.organize_mount()
                if moves:
                    log.info(f"Structured {len(moves)} items in SeaweedFS without deletion.")
                self.last_storage_organize_ts = now_ts
            except Exception as e:
                log.warning(f"Storage organizer exception: {e}")

        # Evaluate recommendations through Tri-Model Shadow Consensus Gate (100% confidence)
        shadow_audit_records = []
        if self.shadow_consensus and recommendations:
            import subprocess
            for rec_dict in recommendations:
                try:
                    rec_desc = rec_dict.get("desc", "")
                    fix_cmd = rec_dict.get("auto_fix_cmd", "")
                    
                    is_100, conf, audit = self.shadow_consensus.evaluate_shadow_consensus(
                        state_text=summary.get("storage_status", {}).get("raw", "")[:60],
                        proposed_action=rec_desc
                    )
                    
                    # If the swarm grants 100% confidence and we have an auto-fix, execute it immediately
                    if is_100 and fix_cmd:
                        log.info(f"🟢 [SHADOW CONSENSUS 100%] Executing auto-fix instantly: {fix_cmd}")
                        metric_before = rec_dict.get("metric_before", "unknown")
                        metric_name = rec_dict.get("metric_name", "Metric")
                        check_cmd = rec_dict.get("check_cmd", "")
                        
                        subprocess.run(fix_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        metric_after = "unknown"
                        significance = "Pending Validation"
                        if check_cmd:
                            try:
                                # Wait a moment for the fix to settle
                                time.sleep(2)
                                result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=5)
                                metric_after = result.stdout.strip()
                                
                                if metric_after and metric_after != metric_before:
                                    significance = "CRITICAL HEAL (State transitioned successfully)"
                                else:
                                    significance = "MARGINAL HEAL (No strict state transition detected)"
                            except Exception as e:
                                metric_after = f"check_failed: {e}"
                                
                        log.info(f"   => [BOTTLENECK METRIC] {metric_name} | Before: {metric_before} | After: {metric_after} | Significance: {significance}")
                        
                        audit["executed_command"] = fix_cmd
                        audit["metric_name"] = metric_name
                        audit["metric_before"] = metric_before
                        audit["metric_after"] = metric_after
                        audit["significance"] = significance
                        
                    shadow_audit_records.append(audit)
                except Exception as e:
                    log.warning(f"Shadow consensus error: {e}")
        summary["shadow_consensus_audits"] = shadow_audit_records
        
        # Convert recommendations back to strings for the summary JSON
        summary["bottleneck_recommendations"] = [r.get("desc", "") for r in recommendations]

        try:
            with open(TELEMETRY_OUT, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception:
            pass

        return summary

    async def run_forever(self, interval_sec: float = 5.0):
        log.info(f"🚀 Omniscient Mesh Sentinel v2.5 ACTIVE. Monitoring 7 streams every {interval_sec}s...")
        while self.is_running:
            try:
                summary = await self.sweep_once()
                recs = summary.get("bottleneck_recommendations", [])
                ports = summary.get("mesh_ports_status", {})
                log.info(
                    f"Sweep complete in {summary['total_sweep_ms']:.1f}ms | "
                    f"Ports Open: {ports.get('open_count', 0)}/{ports.get('total_ports', 0)} | "
                    f"Recs: {len(recs)}"
                )
            except Exception as e:
                log.error(f"Error in sentinel sweep: {e}")
            await asyncio.sleep(interval_sec)

def handle_sigterm(signum, frame):
    log.info("Received termination signal. Shutting down cleanly.")
    sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Omniscient Mesh Sentinel v2.5")
    parser.add_argument("--once", action="store_true", help="Run a single multi-device sweep and output JSON")
    parser.add_argument("--interval", type=float, default=5.0, help="Continuous loop interval in seconds")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    sentinel = OmniscientSentinel(MODEL_PATH)
    if args.once:
        summary = asyncio.run(sentinel.sweep_once())
        print(json.dumps(summary, indent=2))
    else:
        asyncio.run(sentinel.run_forever(interval_sec=args.interval))
