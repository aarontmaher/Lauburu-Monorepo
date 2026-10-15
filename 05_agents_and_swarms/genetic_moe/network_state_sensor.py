#!/usr/bin/env python3
"""
Autonomous Multi-Transport Network State Sensor
===============================================
Subsystem: 05_agents_and_swarms/genetic_moe/network_state_sensor.py
Lauburu 7-Layer Mesh — Dynamic Topology & Link Quality Evaluation

Senses physical connectivity media and classifies the active mesh state:
  1. AIR_GAPPED_SERIAL (Bluetooth RFCOMM /dev/rfcomm0 or USB CDC-ACM)
  2. AD_HOC_PEER_MESH (Bluetooth BNEP PAN 192.168.44.0/24, AWDL, Wi-Fi Direct)
  3. LOCAL_HIGH_BANDWIDTH_LAN (2.5GbE / 5GHz UNII-3 160MHz TP-Link + GL.iNet)
  4. NOMAD_MOBILE_HOTSPOT (Cellular 5G hotspot on Pixel/S20 or USB CDC Tethering)
  5. GLOBAL_ZERO_TRUST_OVERLAY (Tailscale WireGuard 100.64.0.0/10)
  6. ULTRA_CLUSTER_TB4_DMA (3-Mac 40 Gbps Thunderbolt 4 DMA Ring, sub-millisecond RTT)
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import subprocess
import platform
from enum import Enum
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class NetworkTopologyState(str, Enum):
    AIR_GAPPED_SERIAL = "AIR_GAPPED_SERIAL"
    AD_HOC_PEER_MESH = "AD_HOC_PEER_MESH"
    LOCAL_HIGH_BANDWIDTH_LAN = "LOCAL_HIGH_BANDWIDTH_LAN"
    NOMAD_MOBILE_HOTSPOT = "NOMAD_MOBILE_HOTSPOT"
    GLOBAL_ZERO_TRUST_OVERLAY = "GLOBAL_ZERO_TRUST_OVERLAY"
    ULTRA_CLUSTER_TB4_DMA = "ULTRA_CLUSTER_TB4_DMA"


@dataclass
class TransportLinkMetric:
    name: str
    interface: str
    is_up: bool
    ip_address: Optional[str] = None
    rtt_ms: Optional[float] = None
    bandwidth_mbps: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    score: float = 0.0


@dataclass
class NetworkStateSnapshot:
    timestamp: int
    active_topology: NetworkTopologyState
    effective_bandwidth_mbps: float
    overall_link_score: float
    transports: Dict[str, TransportLinkMetric] = field(default_factory=dict)
    recommended_model_tier: str = "T3_BALANCED"
    active_moe_top_k: int = 2
    sharding_protocol: str = "STANDALONE_OR_LOCAL_RPC"
    cloud_offload_allowed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["active_topology"] = self.active_topology.value
        return d

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class NetworkStateSensor:
    """Probes physical and logical network interfaces to evaluate link quality and topology state."""

    TB4_TARGETS = ["169.254.187.138", "169.254.224.29", "169.254.136.148"]
    LAN_GATEWAY = "192.168.8.1"
    BNEP_GATEWAY = "192.168.44.1"
    TAILSCALE_TARGETS = ["100.103.212.21", "100.101.39.98", "100.84.40.95", "100.73.38.87"]
    PUBLIC_DNS = "1.1.1.1"

    def __init__(self):
        self.is_darwin = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"

    def _measure_rtt_fast(self, host: str, timeout_s: float = 0.2) -> Optional[float]:
        """Measures network RTT via non-blocking TCP connect probe."""
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_s)
            # Try port 22 (SSH) or port 80 (HTTP)
            err = sock.connect_ex((host, 22))
            sock.close()
            if err == 0:
                return round((time.perf_counter() - start) * 1000.0, 3)
        except Exception:
            pass

        # Fallback to ICMP ping single packet with tight timeout
        try:
            count_flag = "-c"
            timeout_flag = "-W" if self.is_linux else "-t"
            cmd = ["ping", count_flag, "1", timeout_flag, "1" if self.is_darwin else "1000", host]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "time=" in line:
                        part = line.split("time=")[1].split()[0]
                        return round(float(part), 3)
        except Exception:
            pass
        return None

    def probe_tb4_dma(self) -> TransportLinkMetric:
        """Probes 40 Gbps Thunderbolt 4 DMA PCIe bridge."""
        best_rtt = None
        target_ip = None
        for ip in self.TB4_TARGETS:
            rtt = self._measure_rtt_fast(ip, timeout_s=0.1)
            if rtt is not None:
                if best_rtt is None or rtt < best_rtt:
                    best_rtt = rtt
                    target_ip = ip

        is_up = best_rtt is not None and best_rtt < 1.5
        score = 1.0 if (is_up and best_rtt and best_rtt < 0.5) else (0.85 if is_up else 0.0)
        return TransportLinkMetric(
            name="Thunderbolt 4 DMA Ring",
            interface="bridge0" if self.is_darwin else "thunderbolt0",
            is_up=is_up,
            ip_address=target_ip,
            rtt_ms=best_rtt,
            bandwidth_mbps=40000.0 if is_up else 0.0,
            jitter_ms=0.05 if is_up else 0.0,
            packet_loss_pct=0.0,
            score=score,
        )

    def probe_local_lan(self) -> TransportLinkMetric:
        """Probes local high-speed LAN (GL.iNet & TP-Link AP)."""
        rtt = self._measure_rtt_fast(self.LAN_GATEWAY, timeout_s=0.2)
        is_up = rtt is not None and rtt < 10.0
        score = 0.8 if (is_up and rtt and rtt < 3.0) else (0.6 if is_up else 0.0)
        return TransportLinkMetric(
            name="Local High-Bandwidth LAN",
            interface="en0" if self.is_darwin else "eth0",
            is_up=is_up,
            ip_address=self.LAN_GATEWAY,
            rtt_ms=rtt,
            bandwidth_mbps=1200.0 if is_up else 0.0,
            jitter_ms=0.5 if is_up else 0.0,
            packet_loss_pct=0.0,
            score=score,
        )

    def probe_bnep_pan(self) -> TransportLinkMetric:
        """Probes routerless Bluetooth BNEP PAN bridge (192.168.44.0/24)."""
        rtt = self._measure_rtt_fast(self.BNEP_GATEWAY, timeout_s=0.3)
        is_up = rtt is not None and rtt < 60.0
        score = 0.5 if is_up else 0.0
        return TransportLinkMetric(
            name="Bluetooth BNEP PAN Mesh",
            interface="pan0" if self.is_linux else "en_bnep",
            is_up=is_up,
            ip_address=self.BNEP_GATEWAY,
            rtt_ms=rtt,
            bandwidth_mbps=25.0 if is_up else 0.0,
            jitter_ms=5.0 if is_up else 0.0,
            packet_loss_pct=0.0 if is_up else 100.0,
            score=score,
        )

    def probe_rfcomm_serial(self) -> TransportLinkMetric:
        """Probes raw out-of-band hardware serial console (/dev/rfcomm0)."""
        is_up = False
        dev_path = "/dev/rfcomm0"
        if Path(dev_path).exists() or Path("/dev/cu.Bluetooth-Incoming-Port").exists():
            is_up = True

        score = 0.3 if is_up else 0.0
        return TransportLinkMetric(
            name="RFCOMM Hardware Serial Console",
            interface=dev_path,
            is_up=is_up,
            ip_address=None,
            rtt_ms=30.0 if is_up else None,
            bandwidth_mbps=0.092 if is_up else 0.0,  # 115,200 baud = 92.16 kbps
            jitter_ms=1.0 if is_up else 0.0,
            packet_loss_pct=0.0,
            score=score,
        )

    def probe_tailscale(self) -> TransportLinkMetric:
        """Probes global zero-trust Tailscale overlay."""
        best_rtt = None
        active_ip = None
        for ip in self.TAILSCALE_TARGETS:
            rtt = self._measure_rtt_fast(ip, timeout_s=0.25)
            if rtt is not None:
                if best_rtt is None or rtt < best_rtt:
                    best_rtt = rtt
                    active_ip = ip

        is_up = best_rtt is not None
        score = 0.7 if (is_up and best_rtt and best_rtt < 30.0) else (0.55 if is_up else 0.0)
        return TransportLinkMetric(
            name="Tailscale WireGuard Mesh",
            interface="utun" if self.is_darwin else "tailscale0",
            is_up=is_up,
            ip_address=active_ip,
            rtt_ms=best_rtt,
            bandwidth_mbps=80.0 if is_up else 0.0,
            jitter_ms=4.0 if is_up else 0.0,
            packet_loss_pct=0.0,
            score=score,
        )

    def probe_wan_internet(self) -> bool:
        """Checks public WAN connectivity."""
        rtt = self._measure_rtt_fast(self.PUBLIC_DNS, timeout_s=0.4)
        return rtt is not None

    def evaluate_state(self) -> NetworkStateSnapshot:
        """Evaluates all transport interfaces and determines optimal AI sharding strategy."""
        tb4 = self.probe_tb4_dma()
        lan = self.probe_local_lan()
        bnep = self.probe_bnep_pan()
        rfcomm = self.probe_rfcomm_serial()
        ts = self.probe_tailscale()
        wan_online = self.probe_wan_internet()

        transports = {
            "tb4_dma": tb4,
            "local_lan": lan,
            "bnep_pan": bnep,
            "rfcomm_serial": rfcomm,
            "tailscale": ts,
        }

        # Hierarchy of State Selection:
        if tb4.is_up and tb4.rtt_ms and tb4.rtt_ms < 1.0:
            active_topology = NetworkTopologyState.ULTRA_CLUSTER_TB4_DMA
            effective_bw = 40000.0
            overall_score = 0.98
            model_tier = "T5_FRONTIER_MOE"
            top_k = 4
            sharding_protocol = "LLAMA_CPP_RPC_TB4_DMA"
            cloud_offload = True

        elif lan.is_up and lan.bandwidth_mbps >= 500.0:
            active_topology = NetworkTopologyState.LOCAL_HIGH_BANDWIDTH_LAN
            effective_bw = lan.bandwidth_mbps
            overall_score = 0.85
            model_tier = "T4_SHARDED_32B"
            top_k = 3
            sharding_protocol = "PRIMA_CPP_PRP_RING"
            cloud_offload = wan_online

        elif ts.is_up and wan_online:
            active_topology = NetworkTopologyState.GLOBAL_ZERO_TRUST_OVERLAY
            effective_bw = ts.bandwidth_mbps
            overall_score = 0.72
            model_tier = "T3_SWARM_PROXY"
            top_k = 2
            sharding_protocol = "PERIPHERAL_NODE_OFFLOAD"
            cloud_offload = True

        elif bnep.is_up:
            active_topology = NetworkTopologyState.AD_HOC_PEER_MESH
            effective_bw = bnep.bandwidth_mbps
            overall_score = 0.50
            model_tier = "T2_SPECULATIVE_3B"
            top_k = 1
            sharding_protocol = "ROUTERLESS_SPECULATIVE_DRAFT"
            cloud_offload = False

        elif rfcomm.is_up:
            active_topology = NetworkTopologyState.AIR_GAPPED_SERIAL
            effective_bw = rfcomm.bandwidth_mbps
            overall_score = 0.25
            model_tier = "T1_EDGE_SLM_360M"
            top_k = 1
            sharding_protocol = "STANDALONE_OUT_OF_BAND_SLM"
            cloud_offload = False

        else:
            active_topology = NetworkTopologyState.AIR_GAPPED_SERIAL
            effective_bw = 0.0
            overall_score = 0.10
            model_tier = "T1_LOCAL_SOLO_SLM"
            top_k = 1
            sharding_protocol = "STANDALONE_OFFLINE"
            cloud_offload = False

        return NetworkStateSnapshot(
            timestamp=int(time.time()),
            active_topology=active_topology,
            effective_bandwidth_mbps=effective_bw,
            overall_link_score=overall_score,
            transports=transports,
            recommended_model_tier=model_tier,
            active_moe_top_k=top_k,
            sharding_protocol=sharding_protocol,
            cloud_offload_allowed=cloud_offload,
        )


if __name__ == "__main__":
    sensor = NetworkStateSensor()
    snap = sensor.evaluate_state()
    print(snap.to_json(indent=2))
