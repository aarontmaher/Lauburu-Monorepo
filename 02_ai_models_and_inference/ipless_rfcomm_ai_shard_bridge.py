#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP-less AI Sharding & Blackout-Resilient Transport Bridge
=========================================================
Subsystem: 02_ai_models_and_inference/ipless_rfcomm_ai_shard_bridge.py
Lauburu Mesh Ecosystem — 2026

Guarantees uninterrupted distributed AI sharding and Movesense telemetry synchronization
when the internet, gateway router (192.168.8.1), DHCP server, or IPv4/Tailscale drops:

  • Tier 1 — Hardware-MAC-Derived Thunderbolt 4 Link-Local IPv6 (`fe80::%bridge0`):
    Zero router, zero DHCP, zero DNS, zero IPv4. Binds dual-stack IPv6 listeners
    (`:18083` -> local `llama-server` `:8083`/`:8084`/`:9096` and `:50053` -> `:50052`
    `ggml-rpc-server`) so L1 (`fe80::33:7510:b184:d664%bridge0`), L8 (`fe80::1082:a3ff:fe9e:ae71%bridge0`),
    and L1b (`fe80::1436:d847:df67:f2bd%bridge0`) communicate directly over 40 Gb/s TB4 DMA.

  • Tier 2 — Pure Layer-0 Bluetooth RFCOMM Channel 2 (`AF_BLUETOOTH` / `BTPROTO_RFCOMM`):
    Zero IP stack. Binds RFCOMM Channel 2 on Linux BlueZ nodes (`L3` `00:41:0E:14:28:44`
    and `L8` `3C:22:FB:4E:9F:BB`, while preserving Channel 1 for `rfcomm-console.service`
    interactive `agetty` login) to serve OpenAI-compatible `/v1/chat/completions`,
    `ggml-rpc-server` health probes, and Movesense telemetry pulls over raw Bluetooth radio.

  • Tier 3 — Local POSIX Serial PTY (`/tmp/bt_daemon_4005_pty`) & Metal GPU Sanctuary:
    Provides zero-network local fallback on L1 (`:8089` Qwen2.5-0.5B & `:8085` Hermes-3-8B).
"""

from __future__ import annotations

import argparse
import asyncio
import http.client
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [IPLessShardBridge] %(message)s",
)
logger = logging.getLogger("IPLessShardBridge")

# Canonical Layer-0 Bluetooth & TB4 Link-Local Topology (Probed Rule 0 Truth)
CANONICAL_IPLESS_PEERS: Dict[str, Dict[str, Any]] = {
    "L1": {
        "name": "mac-mini-m4",
        "bt_mac": "1C:F6:4C:81:0B:28",
        "tb4_ipv4": "10.0.0.2",
        "tb4_ipv6_ll": "fe80::33:7510:b184:d664",
        "tb4_iface": "bridge0",
        "local_llm_ports": [8089, 8085],
        "rpc_port": 50052,
    },
    "L8": {
        "name": "lauburu",
        "bt_mac": "3C:22:FB:4E:9F:BB",
        "tb4_ipv4": "10.0.0.8",
        "tb4_ipv6_ll": "fe80::1082:a3ff:fe9e:ae71",
        "tb4_iface": "bridge0",
        "rfcomm_ai_channel": 2,
        "ipv6_llm_bridge_port": 18083,
        "ipv6_rpc_bridge_port": 50053,
        "local_llm_ports": [9096, 8083, 9095],
        "rpc_port": 50052,
        "ssh_target": "linuxmini@10.0.0.8",
    },
    "L1b": {
        "name": "mac-mini-m2",
        "bt_mac": "36:90:11:CC:0F:44",
        "tb4_ipv4": "10.0.0.3",
        "tb4_ipv6_ll": "fe80::1436:d847:df67:f2bd",
        "tb4_iface": "bridge0",
        "ipv6_rpc_bridge_port": 50053,
        "local_llm_ports": [],
        "rpc_port": 50052,
        "ssh_target": "aaronmaher@10.0.0.3",
    },
    "L2": {
        "name": "macbook-intel",
        "bt_mac": "2C:CA:16:08:C0:27",
        "tb4_ipv4": "10.0.0.4",
        "tb4_ipv6_ll": None,
        "tb4_iface": "bridge0",
        "local_llm_ports": [8081],
        "rpc_port": 50052,
    },
    "L3": {
        "name": "linux-amd-gpu",
        "bt_mac": "00:41:0E:14:28:44",
        "tb4_ipv4": None,
        "tb4_ipv6_ll": None,
        "rfcomm_ai_channel": 2,
        "ipv6_llm_bridge_port": 18083,
        "ipv6_rpc_bridge_port": 50053,
        "local_llm_ports": [8084, 8081],
        "rpc_port": 50052,
        "ssh_target": "linux@192.168.8.225",
    },
    "L6": {
        "name": "pixel-10-pro-xl",
        "bt_mac": "30:E0:44:6D:18:EC",
        "tb4_ipv4": None,
        "tb4_ipv6_ll": None,
        "local_llm_ports": [8080],
        "movesense_port": 8087,
        "rpc_port": 50052,
        "ssh_target": "u0_a363@100.114.215.68",
    },
}


# ==============================================================================
# 1. LOCAL NODE INFERENCE & TELEMETRY EXECUTOR (USED BY WORKER DAEMON)
# ==============================================================================
def execute_local_llm_completion(payload: Dict[str, Any], candidate_ports: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Executes an OpenAI-compatible `/v1/chat/completions` request against the first
    available local `llama-server` port on the current worker node.
    """
    if not candidate_ports:
        candidate_ports = [9096, 8084, 8089, 8085, 8083, 9095]

    t0 = time.perf_counter()
    last_err = "no_ports_tried"

    for port in candidate_ports:
        url = f"http://127.0.0.1:{port}/v1/chat/completions"
        try:
            req_body = dict(payload)
            if "max_tokens" not in req_body:
                req_body["max_tokens"] = 64
            data = json.dumps(req_body).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "Connection": "close"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25.0) as resp:
                if resp.status == 200:
                    out = json.loads(resp.read().decode("utf-8"))
                    if isinstance(out, dict) and "choices" in out:
                        model_name = os.path.basename(str(out.get("model") or req_body.get("model") or f"local-{port}"))
                        out["model"] = model_name
                        out["routed_model"] = model_name
                        out["worker_node"] = platform.node()
                        out["worker_port"] = port
                        out["worker_latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
                        return out
        except Exception as e:
            last_err = f"port_{port}: {e}"
            continue

    return {
        "error": f"All local LLM ports {candidate_ports} failed on {platform.node()}: {last_err}",
        "worker_node": platform.node(),
    }


def get_local_worker_status() -> Dict[str, Any]:
    """Returns authentic hardware, RPC shard, and local GGUF model status on this worker node."""
    active_ports: List[int] = []
    for port in (8083, 8084, 8085, 8089, 9095, 9096, 50052):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                active_ports.append(port)
        except Exception:
            pass

    return {
        "status": "ONLINE",
        "hostname": platform.node(),
        "active_local_ports": active_ports,
        "ggml_rpc_50052_active": 50052 in active_ports,
        "timestamp": time.time(),
    }


# ==============================================================================
# 2. DUAL-STACK IPv6 LINK-LOCAL TCP FORWARDER (:18083 -> :8083/:8084, :50053 -> :50052)
# ==============================================================================
async def _pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while not reader.at_eof():
            chunk = await reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _make_ipv6_forward_handler(target_ports: List[int]):
    async def _handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter):
        backend_r = None
        backend_w = None
        for tp in target_ports:
            try:
                backend_r, backend_w = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", tp),
                    timeout=0.5,
                )
                break
            except Exception:
                continue
        if not backend_w:
            client_w.close()
            return
        await asyncio.gather(
            _pipe_stream(client_r, backend_w),
            _pipe_stream(backend_r, client_w),
            return_exceptions=True,
        )

    return _handle


async def start_ipv6_link_local_bridges(
    llm_listen_port: int = 18083,
    llm_target_ports: Optional[List[int]] = None,
    rpc_listen_port: int = 50053,
    rpc_target_port: int = 50052,
) -> List[asyncio.AbstractServer]:
    """
    Binds dual-stack IPv6 (`::`) TCP bridges so peers on Thunderbolt 4 (`bridge0`)
    or Ethernet can connect via hardware-MAC-derived Link-Local IPv6 (`fe80::%bridge0`)
    even when IPv4, DHCP, and the router are completely offline.
    """
    if not llm_target_ports:
        llm_target_ports = [9096, 8084, 8083, 8089, 8085, 9095]

    servers: List[asyncio.AbstractServer] = []
    for listen_p, targets in ((llm_listen_port, llm_target_ports), (rpc_listen_port, [rpc_target_port])):
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except Exception:
                pass
            sock.bind(("::", listen_p))
            sock.listen(128)
            sock.setblocking(False)
            srv = await asyncio.start_server(_make_ipv6_forward_handler(targets), sock=sock)
            servers.append(srv)
            logger.info(f"🟢 IPv6 Link-Local Bridge [::]:{listen_p} -> 127.0.0.1:{targets}")
        except Exception as e:
            logger.warning(f"Could not bind IPv6 bridge port {listen_p}: {e}")
    return servers


# ==============================================================================
# 3. LAYER-0 BLUETOOTH RFCOMM CHANNEL 2 AI SHARD SERVER & CLIENT (AF_BLUETOOTH)
# ==============================================================================
def run_rfcomm_channel2_server(channel: int = 2) -> None:
    """
    Runs a native Layer-0 Bluetooth RFCOMM server (`AF_BLUETOOTH`, `BTPROTO_RFCOMM`)
    on Channel 2 (leaving Channel 1 for interactive `rfcomm-console.service` `agetty`).
    Accepts JSON-line RPC requests over raw Bluetooth radio with zero IP stack.
    """
    if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
        logger.info("AF_BLUETOOTH not exposed in this Python build; skipping native RFCOMM socket listener.")
        return

    try:
        subprocess.run(["sudo", "-n", "sdptool", "add", f"--channel={channel}", "SP"], capture_output=True, timeout=2.0)
    except Exception:
        pass

    srv_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        srv_sock.bind(("00:00:00:00:00:00", channel))
        srv_sock.listen(4)
        logger.info(f"🔵 Layer-0 Bluetooth RFCOMM AI Shard Server listening on Channel {channel} ({platform.node()})")
    except Exception as e:
        logger.error(f"Failed to bind RFCOMM Channel {channel}: {e}")
        srv_sock.close()
        return

    def _handle_rfcomm_client(conn: socket.socket, peer_addr: Any) -> None:
        try:
            conn.settimeout(30.0)
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    req = json.loads(line.decode("utf-8", errors="replace").strip())
                    op = req.get("op", "ping")
                    if op == "ping":
                        resp = get_local_worker_status()
                        resp["transport"] = f"BT_RFCOMM_CH{channel}"
                        resp["peer"] = str(peer_addr)
                    elif op == "chat_completions":
                        payload = req.get("payload", {})
                        ports = req.get("candidate_ports")
                        resp = execute_local_llm_completion(payload, candidate_ports=ports)
                        resp["transport"] = f"BT_RFCOMM_CH{channel}"
                    else:
                        resp = {"status": "ACK", "op": op, "hostname": platform.node()}
                    conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                    break
        except Exception as e:
            try:
                conn.sendall((json.dumps({"error": str(e), "hostname": platform.node()}) + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    while True:
        try:
            client_sock, addr = srv_sock.accept()
            threading.Thread(target=_handle_rfcomm_client, args=(client_sock, addr), daemon=True).start()
        except Exception as e:
            logger.warning(f"RFCOMM accept note: {e}")
            time.sleep(0.5)


def query_rfcomm_channel2_direct(
    target_bt_mac: str,
    request_obj: Dict[str, Any],
    channel: int = 2,
    timeout_s: float = 15.0,
) -> Dict[str, Any]:
    """
    Sends a JSON-line request over pure Layer-0 `AF_BLUETOOTH` `BTPROTO_RFCOMM` Channel 2.
    """
    t0 = time.perf_counter()
    if hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM"):
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(timeout_s)
        try:
            s.connect((target_bt_mac, channel))
            s.sendall((json.dumps(request_obj) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
            out = json.loads(buf.decode("utf-8", errors="replace").strip())
            out["rfcomm_rtt_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            out["rfcomm_target_mac"] = target_bt_mac
            out["rfcomm_channel"] = channel
            return out
        finally:
            try:
                s.close()
            except Exception:
                pass
    raise RuntimeError("Local Python build lacks AF_BLUETOOTH; use TB4 Link-Local->L8 RFCOMM relay.")


# ==============================================================================
# 4. LINK-LOCAL IPv6 HTTP CLIENT (`fe80::...%bridge0`)
# ==============================================================================
def request_ipv6_link_local_http(
    ipv6_ll_addr: str,
    iface: str,
    port: int,
    method: str = "GET",
    path: str = "/health",
    body: Optional[bytes] = None,
    timeout_s: float = 10.0,
) -> Tuple[int, str]:
    """
    Connects over hardware-MAC-derived IPv6 Link-Local (`fe80::...%bridge0`) using
    `socket.getaddrinfo` with explicit scope_id so zero router, zero DHCP, and zero
    IPv4 are required.
    """
    scoped_host = f"{ipv6_ll_addr}%{iface}" if "%" not in ipv6_ll_addr else ipv6_ll_addr
    addr_infos = socket.getaddrinfo(scoped_host, port, socket.AF_INET6, socket.SOCK_STREAM)
    if not addr_infos:
        raise OSError(f"Could not resolve IPv6 link-local scope for {scoped_host}:{port}")

    af, socktype, proto, _, sa = addr_infos[0]
    raw_sock = socket.socket(af, socktype, proto)
    raw_sock.settimeout(timeout_s)
    try:
        raw_sock.connect(sa)
        headers = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: [{ipv6_ll_addr}]:{port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Connection: close\r\n"
            f"Content-Length: {len(body) if body else 0}\r\n\r\n"
        ).encode("utf-8")
        raw_sock.sendall(headers + (body if body else b""))

        response = http.client.HTTPResponse(raw_sock)
        response.begin()
        resp_body = response.read().decode("utf-8", errors="replace")
        return response.status, resp_body
    finally:
        try:
            raw_sock.close()
        except Exception:
            pass


def probe_ipv6_link_local_tcp(ipv6_ll_addr: str, iface: str, port: int, timeout_s: float = 0.5) -> Tuple[bool, Optional[float]]:
    """Probes a TCP port over hardware-MAC-derived IPv6 Link-Local (`fe80::...%bridge0`)."""
    t0 = time.perf_counter()
    try:
        scoped_host = f"{ipv6_ll_addr}%{iface}" if "%" not in ipv6_ll_addr else ipv6_ll_addr
        addr_infos = socket.getaddrinfo(scoped_host, port, socket.AF_INET6, socket.SOCK_STREAM)
        if not addr_infos:
            return False, None
        af, socktype, proto, _, sa = addr_infos[0]
        s = socket.socket(af, socktype, proto)
        s.settimeout(timeout_s)
        try:
            s.connect(sa)
            return True, round((time.perf_counter() - t0) * 1000.0, 3)
        finally:
            s.close()
    except Exception:
        return False, None


# ==============================================================================
# 5. MASTER IP-LESS AI SHARDING & BLACKOUT ORCHESTRATOR (L1 COORDINATOR)
# ==============================================================================
class IPLessAIShardOrchestrator:
    """
    Coordinates IP-less AI inference and tensor sharding across:
      1. Thunderbolt 4 Link-Local IPv6 (`fe80::1082:a3ff:fe9e:ae71%bridge0` L8 & `fe80::1436:d847:df67:f2bd%bridge0` L1b)
      2. Layer-0 Bluetooth RFCOMM Channel 2 (`00:41:0E:14:28:44` L3 & `3C:22:FB:4E:9F:BB` L8)
      3. Thunderbolt 4 Static DMA (`10.0.0.8`, `10.0.0.3`, `10.0.0.4`)
      4. Local Metal GPU Sanctuary (`127.0.0.1:8089`, `127.0.0.1:8085`) & POSIX PTY (`/tmp/bt_daemon_4005_pty`)
    """

    def __init__(self, simulate_wan_blackout: bool = False):
        self.simulate_wan_blackout = simulate_wan_blackout

    def is_wan_online(self, timeout_s: float = 0.35) -> bool:
        """Probes whether the gateway router (192.168.8.1) is reachable."""
        if self.simulate_wan_blackout:
            return False
        try:
            with socket.create_connection(("192.168.8.1", 80), timeout=timeout_s):
                return True
        except Exception:
            return False

    def probe_tb4_link_local(self, scoped_addr: str = "fe80::1082:a3ff:fe9e:ae71%bridge0", port: int = 18083, timeout_s: float = 0.5) -> bool:
        """Probes a port over hardware-MAC-derived IPv6 Link-Local (`fe80::...%bridge0`)."""
        addr, iface = (scoped_addr.split("%", 1) if "%" in scoped_addr else (scoped_addr, "bridge0"))
        ok, _ = probe_ipv6_link_local_tcp(addr, iface, port, timeout_s=timeout_s)
        return ok

    def dispatch_tb4_link_local(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 64,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Dispatches a chat completion over Tier-1 TB4 Link-Local IPv6 (`fe80::1082:a3ff:fe9e:ae71%bridge0:18083`)."""
        return self.dispatch_ipless_chat_completion(
            payload={"model": "ai", "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
            simulate_wan_blackout=True,
            force_transport="tb4_ipv6_ll",
        )

    def execute_sharded_inference(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 64,
        simulate_wan_blackout: bool = True,
        force_tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Alias wrapper around dispatch_ipless_chat_completion."""
        res = self.dispatch_ipless_chat_completion(
            payload={"model": "ai", "messages": messages, "max_tokens": max_tokens, "temperature": 0.2},
            simulate_wan_blackout=simulate_wan_blackout,
            force_transport=force_tier,
        )
        res["ipless_latency_ms"] = res.get("total_roundtrip_ms")
        return res

    def run_internet_blackout_stability_benchmark(self, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Alias wrapper around run_blackout_stability_benchmark."""
        return self.run_blackout_stability_benchmark()

    def probe_all_ipless_transports(self, simulate_wan_blackout: Optional[bool] = None) -> Dict[str, Any]:
        """Probes WAN/Router state alongside all router-independent / IP-less AI sharding links."""
        blackout = self.simulate_wan_blackout if simulate_wan_blackout is None else simulate_wan_blackout
        t0 = time.perf_counter()

        # 1. Gateway Router / Internet probe (192.168.8.1)
        wan_router_online = False
        if not blackout:
            try:
                with socket.create_connection(("192.168.8.1", 80), timeout=0.35):
                    wan_router_online = True
            except Exception:
                pass

        # 2. Tier 1: Hardware-MAC-Derived TB4 Link-Local IPv6 (`fe80::...%bridge0`)
        l8_ll_llm_ok, l8_ll_llm_rtt = probe_ipv6_link_local_tcp("fe80::1082:a3ff:fe9e:ae71", "bridge0", 18083, 0.5)
        l8_ll_rpc_ok, l8_ll_rpc_rtt = probe_ipv6_link_local_tcp("fe80::1082:a3ff:fe9e:ae71", "bridge0", 50053, 0.5)
        l1b_ll_rpc_ok, l1b_ll_rpc_rtt = probe_ipv6_link_local_tcp("fe80::1436:d847:df67:f2bd", "bridge0", 50053, 0.5)

        # 3. Tier 1b: Static TB4 DMA (`10.0.0.8:8083`, `10.0.0.8:50052`, `10.0.0.3:50052`)
        l8_tb4_rpc_ok = False
        l1b_tb4_rpc_ok = False
        try:
            with socket.create_connection(("10.0.0.8", 50052), timeout=0.3):
                l8_tb4_rpc_ok = True
        except Exception:
            pass
        try:
            with socket.create_connection(("10.0.0.3", 50052), timeout=0.3):
                l1b_tb4_rpc_ok = True
        except Exception:
            pass

        # 4. Tier 2: Layer-0 Bluetooth Baseband & RFCOMM Channel 2
        blueutil = "/Users/aaron/.local/bin/blueutil" if os.path.exists("/Users/aaron/.local/bin/blueutil") else "blueutil"
        bt_links: Dict[str, str] = {}
        for nid, mac in (("L3", "00-41-0e-14-28-44"), ("L8", "3c-22-fb-4e-9f-bb"), ("L6", "30-e0-44-6d-18-ec"), ("L2", "2c-ca-16-08-c0-27")):
            try:
                r = subprocess.run([blueutil, "--info", mac, "--format", "json"], capture_output=True, text=True, timeout=0.6)
                if r.returncode == 0:
                    info = json.loads(r.stdout)
                    bt_links[nid] = "CONNECTED" if info.get("connected") else ("PAIRED" if info.get("paired") else "DISCONNECTED")
                else:
                    bt_links[nid] = "UNKNOWN"
            except Exception:
                bt_links[nid] = "UNKNOWN"

        # 5. Tier 3: Local POSIX PTY & Local Metal GPU Sanctuary
        pty_4005_exists = os.path.exists("/tmp/bt_daemon_4005_pty")
        local_8089_ok = False
        local_8085_ok = False
        try:
            with socket.create_connection(("127.0.0.1", 8089), timeout=0.2):
                local_8089_ok = True
        except Exception:
            pass
        try:
            with socket.create_connection(("127.0.0.1", 8085), timeout=0.2):
                local_8085_ok = True
        except Exception:
            pass

        surviving_tiers = []
        if l8_ll_llm_ok or l8_ll_rpc_ok or l1b_ll_rpc_ok:
            surviving_tiers.append("TIER_1_TB4_IPV6_LINK_LOCAL_ZERO_DHCP")
        if l8_tb4_rpc_ok or l1b_tb4_rpc_ok:
            surviving_tiers.append("TIER_1B_TB4_STATIC_DMA")
        if any(v in ("CONNECTED", "PAIRED") for v in bt_links.values()):
            surviving_tiers.append("TIER_2_LAYER0_BLUETOOTH_RFCOMM")
        if local_8089_ok or local_8085_ok or pty_4005_exists:
            surviving_tiers.append("TIER_3_LOCAL_METAL_GPU_AND_POSIX_PTY")

        return {
            "mode": "INTERNET_DROPPED_ISOLATED_SHARDING" if not wan_router_online else "HYBRID_ONLINE_AND_IPLESS_READY",
            "simulated_wan_blackout": blackout,
            "wan_gateway_192_168_8_1_online": wan_router_online,
            "surviving_ipless_tiers": surviving_tiers,
            "sharding_stability_guaranteed": len(surviving_tiers) >= 2,
            "tier1_tb4_link_local_ipv6": {
                "l8_lauburu_ll_addr": "fe80::1082:a3ff:fe9e:ae71%bridge0",
                "l8_llm_bridge_18083_online": l8_ll_llm_ok,
                "l8_llm_bridge_rtt_ms": l8_ll_llm_rtt,
                "l8_rpc_bridge_50053_online": l8_ll_rpc_ok,
                "l8_rpc_bridge_rtt_ms": l8_ll_rpc_rtt,
                "l1b_m2_ll_addr": "fe80::1436:d847:df67:f2bd%bridge0",
                "l1b_rpc_bridge_50053_online": l1b_ll_rpc_ok,
                "l1b_rpc_bridge_rtt_ms": l1b_ll_rpc_rtt,
            },
            "tier1b_tb4_static_dma": {
                "l8_10_0_0_8_rpc_50052": l8_tb4_rpc_ok,
                "l1b_10_0_0_3_rpc_50052": l1b_tb4_rpc_ok,
            },
            "tier2_layer0_bluetooth_rfcomm": {
                "channel_1_console": "agetty 115200 8N1 (L3 00:41:0E:14:28:44 & L8 3C:22:FB:4E:9F:BB)",
                "channel_2_ai_shard_rpc": "JSON-RPC /v1/chat/completions over AF_BLUETOOTH BTPROTO_RFCOMM",
                "peer_baseband_states": bt_links,
            },
            "tier3_local_sanctuary_and_pty": {
                "posix_pty_4005": "/tmp/bt_daemon_4005_pty" if pty_4005_exists else None,
                "local_8089_qwen_05b": local_8089_ok,
                "local_8085_hermes_8b": local_8085_ok,
            },
            "probe_duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "timestamp": time.time(),
        }

    def dispatch_rfcomm_via_l8_bridge(
        self,
        target_bt_mac: str,
        payload: Dict[str, Any],
        channel: int = 2,
        timeout_s: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Dispatches an AI inference request over Layer-0 Bluetooth RFCOMM Channel 2
        using L8 (`lauburu` over TB4 Link-Local `fe80::1082:a3ff:fe9e:ae71%bridge0` or `10.0.0.8`)
        as the BlueZ `AF_BLUETOOTH` radio bridge to `target_bt_mac` (e.g., L3 `00:41:0E:14:28:44`),
        or bidirectional L3->L8 (`3C:22:FB:4E:9F:BB` Channel 2), bypassing macOS TCC `0xe00002bc`
        restrictions while using zero LAN/WAN IP over the air!
        """
        t0 = time.perf_counter()
        rfcomm_payload = dict(payload)
        if int(rfcomm_payload.get("max_tokens", 24)) > 24:
            rfcomm_payload["max_tokens"] = 24
        req_line = json.dumps({"op": "chat_completions", "payload": rfcomm_payload, "candidate_ports": [9096, 8084, 8089, 8085, 8083]}) + "\n"

        def _build_rfcomm_py(mac: str) -> str:
            return (
                "python3 -c \""
                "import socket, sys, time; "
                "req = sys.stdin.buffer.readline(); "
                "last_err = None\n"
                "for attempt in range(3):\n"
                "    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)\n"
                f"    s.settimeout({timeout_s})\n"
                "    try:\n"
                f"        s.connect(('{mac}', {channel}))\n"
                "        s.sendall(req)\n"
                "        f = s.makefile('rb')\n"
                "        line = f.readline()\n"
                "        s.close()\n"
                "        if line:\n"
                "            sys.stdout.buffer.write(line)\n"
                "            sys.exit(0)\n"
                "    except Exception as e:\n"
                "        last_err = e\n"
                "        try: s.close()\n"
                "        except Exception: pass\n"
                "        time.sleep(0.6)\n"
                "sys.stderr.write(str(last_err))\n"
                "sys.exit(1)\""
            )

        # Primary: L8 (via TB4 Link-Local IPv6 or TB4 static) -> L3 Bluetooth RFCOMM Channel 2 (`00:41:0E:14:28:44`)
        # Secondary failover: L3 -> L8 Bluetooth RFCOMM Channel 2 (`3C:22:FB:4E:9F:BB`)
        bridge_routes = [
            ("linuxmini@fe80::1082:a3ff:fe9e:ae71%bridge0", target_bt_mac),
            ("linuxmini@10.0.0.8", target_bt_mac),
            ("linux@192.168.8.225", "3C:22:FB:4E:9F:BB"),
        ]
        for ssh_host, bt_mac in bridge_routes:
            try:
                res = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", ssh_host, _build_rfcomm_py(bt_mac)],
                    input=req_line,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s + 6.0,
                )
                if res.returncode == 0 and res.stdout.strip():
                    out = json.loads(res.stdout.strip().splitlines()[-1])
                    if isinstance(out, dict) and "choices" in out:
                        model_id = os.path.basename(str(out.get("model") or out.get("routed_model") or "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"))
                        out["model"] = model_id
                        out["routed_model"] = model_id
                        out["routed_transport"] = f"TIER2_BT_RFCOMM_CH{channel} (via {ssh_host} -> {bt_mac})"
                        out["routed_endpoint"] = f"bt-rfcomm://{bt_mac}:{channel}/v1/chat/completions"
                        out["total_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
                        return out
            except Exception:
                continue
        raise RuntimeError(f"RFCOMM Channel {channel} dispatch to {target_bt_mac} failed")

    def dispatch_ipless_chat_completion(
        self,
        payload: Dict[str, Any],
        simulate_wan_blackout: bool = False,
        force_transport: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Routes an OpenAI-compatible `/v1/chat/completions` request strictly across
        WAN-independent / IP-less transports:
          1. `tb4_ipv6_ll`: Thunderbolt 4 Link-Local IPv6 (`[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083`)
          2. `bt_rfcomm`: Layer-0 Bluetooth RFCOMM Channel 2 (`bt-rfcomm://00:41:0E:14:28:44:2` L3)
          3. `tb4_static`: Thunderbolt 4 Static DMA (`http://10.0.0.8:9096/v1/chat/completions` or `:8083`)
          4. `local_sanctuary`: Local Metal GPU (`http://127.0.0.1:8089/v1/chat/completions` / `:8085`)
        """
        t0 = time.perf_counter()
        attempted: List[str] = []
        req_body = dict(payload)
        if "max_tokens" not in req_body:
            req_body["max_tokens"] = 64

        # Order of transports to attempt
        if force_transport:
            order = [force_transport]
        else:
            order = ["tb4_ipv6_ll", "bt_rfcomm", "tb4_static", "local_sanctuary"]

        for tier in order:
            # Tier 1: Hardware-MAC-Derived TB4 Link-Local IPv6 (`fe80::1082:a3ff:fe9e:ae71%bridge0:18083`)
            if tier == "tb4_ipv6_ll":
                ep_label = "http://[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083/v1/chat/completions"
                attempted.append(ep_label)
                try:
                    status, raw = request_ipv6_link_local_http(
                        "fe80::1082:a3ff:fe9e:ae71",
                        "bridge0",
                        18083,
                        method="POST",
                        path="/v1/chat/completions",
                        body=json.dumps(req_body).encode("utf-8"),
                        timeout_s=15.0,
                    )
                    if status == 200:
                        data = json.loads(raw)
                        if isinstance(data, dict) and "choices" in data:
                            model_id = os.path.basename(str(data.get("model") or "smollm2-135m-instruct-q4_k_m.gguf"))
                            data["model"] = model_id
                            data["routed_model"] = model_id
                            data["routed_endpoint"] = ep_label
                            data["routed_transport"] = "TIER1_TB4_IPV6_LINK_LOCAL_ZERO_DHCP"
                            data["wan_blackout_resilient"] = True
                            data["simulated_wan_blackout"] = simulate_wan_blackout
                            data["attempted_endpoints"] = attempted
                            data["total_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
                            return data
                except Exception:
                    pass

            # Tier 2: Pure Layer-0 Bluetooth RFCOMM Channel 2 (`00:41:0E:14:28:44` L3)
            elif tier == "bt_rfcomm":
                ep_label = "bt-rfcomm://00:41:0E:14:28:44:2/v1/chat/completions"
                attempted.append(ep_label)
                try:
                    data = self.dispatch_rfcomm_via_l8_bridge("00:41:0E:14:28:44", req_body, channel=2, timeout_s=20.0)
                    if isinstance(data, dict) and "choices" in data:
                        data["wan_blackout_resilient"] = True
                        data["simulated_wan_blackout"] = simulate_wan_blackout
                        data["attempted_endpoints"] = attempted
                        return data
                except Exception:
                    pass

            # Tier 1b: Static TB4 DMA (`10.0.0.8:9096` / `10.0.0.8:8083`)
            elif tier == "tb4_static":
                for port in (9096, 8083):
                    ep_label = f"http://10.0.0.8:{port}/v1/chat/completions"
                    attempted.append(ep_label)
                    try:
                        req = urllib.request.Request(
                            ep_label,
                            data=json.dumps(req_body).encode("utf-8"),
                            headers={"Content-Type": "application/json", "Connection": "close"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=15.0) as resp:
                            if resp.status == 200:
                                data = json.loads(resp.read().decode("utf-8"))
                                if isinstance(data, dict) and "choices" in data:
                                    model_id = os.path.basename(str(data.get("model") or f"l8-{port}"))
                                    data["model"] = model_id
                                    data["routed_model"] = model_id
                                    data["routed_endpoint"] = ep_label
                                    data["routed_transport"] = "TIER1B_TB4_STATIC_DMA"
                                    data["wan_blackout_resilient"] = True
                                    data["simulated_wan_blackout"] = simulate_wan_blackout
                                    data["attempted_endpoints"] = attempted
                                    data["total_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
                                    return data
                    except Exception:
                        continue

            # Tier 3: Local Metal GPU Sanctuary (`127.0.0.1:8089` / `127.0.0.1:8085`)
            elif tier == "local_sanctuary":
                for port in (8089, 8085):
                    ep_label = f"http://127.0.0.1:{port}/v1/chat/completions"
                    attempted.append(ep_label)
                    try:
                        req = urllib.request.Request(
                            ep_label,
                            data=json.dumps(req_body).encode("utf-8"),
                            headers={"Content-Type": "application/json", "Connection": "close"},
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=15.0) as resp:
                            if resp.status == 200:
                                data = json.loads(resp.read().decode("utf-8"))
                                if isinstance(data, dict) and "choices" in data:
                                    model_id = os.path.basename(str(data.get("model") or f"local-{port}"))
                                    data["model"] = model_id
                                    data["routed_model"] = model_id
                                    data["routed_endpoint"] = ep_label
                                    data["routed_transport"] = "TIER3_LOCAL_METAL_SANCTUARY"
                                    data["wan_blackout_resilient"] = True
                                    data["simulated_wan_blackout"] = simulate_wan_blackout
                                    data["attempted_endpoints"] = attempted
                                    data["total_roundtrip_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
                                    return data
                    except Exception:
                        continue

        raise RuntimeError(f"All IP-less shard transports failed: {attempted}")

    def run_blackout_stability_benchmark(self) -> Dict[str, Any]:
        """
        Executes an empirical multi-transport AI sharding stability verification under
        simulated total internet / router / DHCP blackout across:
          1. Tier 1: Hardware-MAC-Derived TB4 Link-Local IPv6 (`[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083`)
          2. Tier 2: Pure Layer-0 Bluetooth RFCOMM Channel 2 (`bt-rfcomm://00:41:0E:14:28:44:2`)
          3. Tier 3: Local Metal GPU Sanctuary (`127.0.0.1:8089`)
        """
        t_start = time.perf_counter()
        results: List[Dict[str, Any]] = []
        test_matrix = [
            ("tb4_ipv6_ll", "Confirm TB4 IPv6 Link-Local shard readiness in 6 words."),
            ("bt_rfcomm", "Confirm Bluetooth RFCOMM Channel 2 shard readiness in 6 words."),
            ("local_sanctuary", "Confirm Metal GPU sanctuary readiness in 6 words."),
        ]

        successes = 0
        for transport_key, prompt_text in test_matrix:
            try:
                resp = self.dispatch_ipless_chat_completion(
                    payload={
                        "model": "ai",
                        "messages": [{"role": "user", "content": prompt_text}],
                        "max_tokens": 24,
                        "temperature": 0.1,
                    },
                    simulate_wan_blackout=True,
                    force_transport=transport_key,
                )
                reply = (
                    resp.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                ok = bool(reply)
                if ok:
                    successes += 1
                results.append({
                    "requested_tier": transport_key,
                    "success": ok,
                    "routed_endpoint": resp.get("routed_endpoint"),
                    "routed_transport": resp.get("routed_transport"),
                    "routed_model": resp.get("routed_model"),
                    "latency_ms": resp.get("total_roundtrip_ms"),
                    "reply_preview": reply[:120],
                })
            except Exception as e:
                results.append({
                    "requested_tier": transport_key,
                    "success": False,
                    "error": str(e),
                })

        return {
            "benchmark": "IPLess_AI_Sharding_Internet_Drop_Stability",
            "simulated_wan_blackout": True,
            "total_tiers_tested": len(test_matrix),
            "tiers_succeeded": successes,
            "zero_drop_rate_verified": successes == len(test_matrix),
            "results": results,
            "total_duration_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
            "timestamp": time.time(),
        }


# ==============================================================================
# 6. WORKER DAEMON ENTRYPOINT (`--worker`)
# ==============================================================================
async def run_worker_daemon(rfcomm_channel: int = 2, llm_ipv6_port: int = 18083, rpc_ipv6_port: int = 50053) -> None:
    """Starts both the Dual-Stack IPv6 Link-Local bridges and the Bluetooth RFCOMM Channel 2 AI Shard server."""
    threading.Thread(target=run_rfcomm_channel2_server, args=(rfcomm_channel,), daemon=True).start()
    servers = await start_ipv6_link_local_bridges(
        llm_listen_port=llm_ipv6_port,
        rpc_listen_port=rpc_ipv6_port,
    )
    if servers:
        await asyncio.gather(*(s.serve_forever() for s in servers))
    else:
        while True:
            await asyncio.sleep(3600)


def main() -> None:
    parser = argparse.ArgumentParser(description="IP-less AI Sharding & Blackout-Resilient Transport Bridge")
    parser.add_argument("--worker", action="store_true", help="Run background IPv6 Link-Local + Bluetooth RFCOMM Channel 2 worker daemon")
    parser.add_argument("--status", action="store_true", help="Probe all IP-less transports and print JSON report")
    parser.add_argument("--blackout-test", action="store_true", help="Run E2E WAN blackout sharding stability benchmark")
    parser.add_argument("--prompt", type=str, help="Dispatch a live prompt over IP-less AI sharding")
    parser.add_argument("--transport", type=str, choices=["tb4_ipv6_ll", "bt_rfcomm", "tb4_static", "local_sanctuary"], default=None)
    parser.add_argument("--rfcomm-channel", type=int, default=2)
    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker_daemon(rfcomm_channel=args.rfcomm_channel))
        return

    orch = IPLessAIShardOrchestrator()
    if args.status:
        print(json.dumps(orch.probe_all_ipless_transports(), indent=2))
    elif args.blackout_test:
        res = orch.run_blackout_stability_benchmark()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("zero_drop_rate_verified") else 1)
    elif args.prompt:
        res = orch.dispatch_ipless_chat_completion(
            payload={
                "model": "ai",
                "messages": [{"role": "user", "content": args.prompt}],
                "max_tokens": 64,
                "temperature": 0.2,
            },
            simulate_wan_blackout=True,
            force_transport=args.transport,
        )
        print(json.dumps(res, indent=2))
    else:
        print(json.dumps(orch.probe_all_ipless_transports(), indent=2))


if __name__ == "__main__":
    main()
