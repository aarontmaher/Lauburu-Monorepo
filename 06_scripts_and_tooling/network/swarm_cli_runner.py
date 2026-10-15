#!/usr/bin/env python3
"""
================================================================================
🐝 Sovereign Swarm CLI Tool Training Engine & Execution Harness (Generation 32)
================================================================================
Subsystem: 06_scripts_and_tooling/network/swarm_cli_runner.py
Governed by:
  - Rule 0 (Zero-Mock): Authentic hardware endpoints & genuine kernel execution
  - Rule 1 (Tri-Proof): Exact process exit codes, SHA256 hashes, verified telemetry
  - Rule 2 (Tri-Vault): Obsidian Vault, PySpark LoRA lake, GitHub Monorepo
  - Rule 5 (Tri-Proof Interceptor): Empirical validation of all CLI states

Capabilities:
  • Autonomous Swarm CLI tool training and programmatic execution for:
    1. OpenWrt LuCI Web Console JSON-RPC (/cgi-bin/luci/rpc/) & UBUS Microbus
    2. Tailscale WireGuard Mesh CLI (status --json, ping, ip -4, netcheck)
    3. WireGuard CLI (wg show, wg genkey, wg pubkey) with Curve25519 X25519 verification
  • Captures structured outputs, execution latencies, exit codes, and cryptographic SHA256
  • Extracts normalized network parameters (carrier, IPs, TX/RX counters) for cross-verification
================================================================================
"""

import os
import sys
import json
import time
import shutil
import base64
import socket
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

# Default Constants across Lauburu 7-Layer Mesh
ROUTER_IP = "192.168.8.1"
ROUTER_USER = "root"
ROUTER_SSH_PORT = 22
ROUTER_HTTP_PORT = 8080
ROUTER_LUCI_PATH = "/cgi-bin/luci/rpc"
TAILSCALE_LOCAL_BIN_CANDIDATES = [
    "/Users/aaron/.local/bin/tailscale",
    "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
    "/usr/local/bin/tailscale",
    "/opt/homebrew/bin/tailscale"
]


@dataclass
class CLIExecutionResult:
    """Standardized empirical execution result for Swarm CLI tool calls."""
    tool_name: str
    command_line: str
    execution_target: str
    transport: str
    timestamp_iso: str
    timestamp_unix: float
    duration_ms: float
    exit_code: int
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str
    parsed_json: Optional[Dict[str, Any]] = None
    extracted_network_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SwarmCLIRunner:
    """
    Sovereign Swarm CLI Runner training engine.
    Executes programmatic calls across LuCI JSON-RPC/UBUS, Tailscale, and WireGuard.
    """

    def __init__(
        self,
        router_ip: str = ROUTER_IP,
        router_user: str = ROUTER_USER,
        router_port: int = ROUTER_SSH_PORT,
        tailscale_bin: Optional[str] = None
    ):
        self.router_ip = router_ip
        self.router_user = router_user
        self.router_port = router_port
        self.tailscale_bin = tailscale_bin or self._resolve_tailscale_bin()

    def _resolve_tailscale_bin(self) -> Optional[str]:
        for candidate in TAILSCALE_LOCAL_BIN_CANDIDATES:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        found = shutil.which("tailscale")
        return found if found else None

    # =========================================================================
    # 1. LuCI Web Console JSON-RPC & OpenWrt UBUS Engine
    # =========================================================================

    def execute_luci_rpc(
        self,
        module: str,
        method: str,
        params: Optional[List[Any]] = None,
        timeout_sec: float = 5.0
    ) -> CLIExecutionResult:
        """
        Executes a LuCI JSON-RPC call against the gateway router HTTP endpoint.
        Falls back gracefully to SSH ubus execution if HTTP RPC endpoint is firewalled.
        """
        t0 = time.perf_counter()
        ts_unix = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_unix))
        params = params or []
        payload = {
            "jsonrpc": "2.0",
            "id": int(ts_unix * 1000),
            "method": method,
            "params": params
        }
        cmd_str = f"luci_rpc://{self.router_ip}:{ROUTER_HTTP_PORT}/{module}/{method}"
        data_bytes = json.dumps(payload).encode("utf-8")
        url = f"http://{self.router_ip}:{ROUTER_HTTP_PORT}{ROUTER_LUCI_PATH}/{module}"

        stdout_str = ""
        stderr_str = ""
        exit_code = 0
        parsed: Optional[Dict[str, Any]] = None

        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json", "User-Agent": "SwarmCLIRunner/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_out = resp.read().decode("utf-8", errors="replace")
                stdout_str = raw_out
                exit_code = 0
                try:
                    parsed = json.loads(raw_out)
                except Exception:
                    parsed = None
        except Exception as http_err:
            # Fallback to direct router ubus execution via SSH for zero-mock reliability
            stderr_str = f"HTTP RPC failed: {http_err}. Engaging SSH ubus bridge."
            param_str = json.dumps(params[0]) if params else "{}"
            ssh_cmd = f"ubus call {module} {method} '{param_str}'"
            ssh_res = self._run_ssh_command(ssh_cmd, timeout_sec=timeout_sec)
            stdout_str = ssh_res.stdout
            stderr_str += f"\nSSH bridge stderr: {ssh_res.stderr}".strip()
            exit_code = ssh_res.exit_code
            parsed = ssh_res.parsed_json

        dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        extracted = self._extract_network_state("luci_ubus", stdout_str, parsed)

        return CLIExecutionResult(
            tool_name="luci_json_rpc",
            command_line=cmd_str,
            execution_target=f"gw_router ({self.router_ip})",
            transport="http_json_rpc" if not stderr_str.startswith("HTTP RPC failed") else "ssh_bridge",
            timestamp_iso=ts_iso,
            timestamp_unix=ts_unix,
            duration_ms=dur_ms,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            stdout_sha256=hashlib.sha256(stdout_str.encode("utf-8")).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr_str.encode("utf-8")).hexdigest(),
            parsed_json=parsed,
            extracted_network_state=extracted
        )

    def execute_ubus(
        self,
        subsystem: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_sec: float = 5.0
    ) -> CLIExecutionResult:
        """
        Directly invokes OpenWrt's native microbus (`ubus`) on the GL.iNet router via SSH.
        Example: `ubus call network.interface.wan status`
        """
        t0 = time.perf_counter()
        ts_unix = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_unix))
        params = params or {}
        param_arg = f" '{json.dumps(params)}'" if params else ""
        cmd_str = f"ubus call {subsystem} {method}{param_arg}"

        ssh_res = self._run_ssh_command(cmd_str, timeout_sec=timeout_sec)
        dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        extracted = self._extract_network_state("ubus", ssh_res.stdout, ssh_res.parsed_json)

        return CLIExecutionResult(
            tool_name="openwrt_ubus",
            command_line=cmd_str,
            execution_target=f"gw_router ({self.router_ip})",
            transport="ssh_direct",
            timestamp_iso=ts_iso,
            timestamp_unix=ts_unix,
            duration_ms=dur_ms,
            exit_code=ssh_res.exit_code,
            stdout=ssh_res.stdout,
            stderr=ssh_res.stderr,
            stdout_sha256=hashlib.sha256(ssh_res.stdout.encode("utf-8")).hexdigest(),
            stderr_sha256=hashlib.sha256(ssh_res.stderr.encode("utf-8")).hexdigest(),
            parsed_json=ssh_res.parsed_json,
            extracted_network_state=extracted
        )

    def execute_uci(
        self,
        action: str,
        config_path: str,
        value: Optional[str] = None,
        timeout_sec: float = 5.0
    ) -> CLIExecutionResult:
        """
        Executes OpenWrt UCI commands (`uci show`, `uci get`, `uci set`, `uci commit`) over SSH.
        """
        t0 = time.perf_counter()
        ts_unix = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_unix))

        if action == "set" and value is not None:
            cmd_str = f"uci set {config_path}='{value}'"
        else:
            cmd_str = f"uci {action} {config_path}"

        ssh_res = self._run_ssh_command(cmd_str, timeout_sec=timeout_sec)
        dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        extracted = {"action": action, "config_path": config_path}

        return CLIExecutionResult(
            tool_name="openwrt_uci",
            command_line=cmd_str,
            execution_target=f"gw_router ({self.router_ip})",
            transport="ssh_direct",
            timestamp_iso=ts_iso,
            timestamp_unix=ts_unix,
            duration_ms=dur_ms,
            exit_code=ssh_res.exit_code,
            stdout=ssh_res.stdout,
            stderr=ssh_res.stderr,
            stdout_sha256=hashlib.sha256(ssh_res.stdout.encode("utf-8")).hexdigest(),
            stderr_sha256=hashlib.sha256(ssh_res.stderr.encode("utf-8")).hexdigest(),
            parsed_json=ssh_res.parsed_json,
            extracted_network_state=extracted
        )

    # =========================================================================
    # 2. Tailscale WireGuard Mesh CLI Engine
    # =========================================================================

    def execute_tailscale(
        self,
        subcommand: str,
        args: Optional[List[str]] = None,
        timeout_sec: float = 10.0
    ) -> CLIExecutionResult:
        """
        Executes Tailscale CLI subcommands locally (`status --json`, `ping`, `ip -4`, `netcheck`).
        """
        t0 = time.perf_counter()
        ts_unix = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_unix))
        args = args or []

        if not self.tailscale_bin:
            return CLIExecutionResult(
                tool_name="tailscale",
                command_line=f"tailscale {subcommand} {' '.join(args)}",
                execution_target="localhost",
                transport="local_process",
                timestamp_iso=ts_iso,
                timestamp_unix=ts_unix,
                duration_ms=0.0,
                exit_code=127,
                stdout="",
                stderr="Tailscale CLI binary not found on host filesystem.",
                stdout_sha256=hashlib.sha256(b"").hexdigest(),
                stderr_sha256=hashlib.sha256(b"Tailscale CLI binary not found on host filesystem.").hexdigest(),
                parsed_json=None,
                extracted_network_state={"status": "NOT_INSTALLED"}
            )

        cmd_list = [self.tailscale_bin, subcommand] + args
        cmd_str = " ".join(cmd_list)

        try:
            res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout_sec)
            dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            stdout_str = res.stdout.strip()
            stderr_str = res.stderr.strip()
            exit_code = res.returncode

            parsed: Optional[Dict[str, Any]] = None
            if subcommand == "status" and "--json" in args:
                try:
                    parsed = json.loads(stdout_str)
                except Exception:
                    parsed = None

            extracted = self._extract_network_state("tailscale", stdout_str, parsed)

            return CLIExecutionResult(
                tool_name="tailscale",
                command_line=cmd_str,
                execution_target="localhost (L1 Mac Mini)",
                transport="local_process",
                timestamp_iso=ts_iso,
                timestamp_unix=ts_unix,
                duration_ms=dur_ms,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                stdout_sha256=hashlib.sha256(stdout_str.encode("utf-8")).hexdigest(),
                stderr_sha256=hashlib.sha256(stderr_str.encode("utf-8")).hexdigest(),
                parsed_json=parsed,
                extracted_network_state=extracted
            )
        except subprocess.TimeoutExpired:
            dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return CLIExecutionResult(
                tool_name="tailscale",
                command_line=cmd_str,
                execution_target="localhost (L1 Mac Mini)",
                transport="local_process",
                timestamp_iso=ts_iso,
                timestamp_unix=ts_unix,
                duration_ms=dur_ms,
                exit_code=124,
                stdout="",
                stderr=f"Command timed out after {timeout_sec}s",
                stdout_sha256=hashlib.sha256(b"").hexdigest(),
                stderr_sha256=hashlib.sha256(b"timeout").hexdigest(),
                parsed_json=None,
                extracted_network_state={"status": "TIMEOUT"}
            )

    # =========================================================================
    # 3. WireGuard CLI Engine (wg show, wg genkey, wg pubkey)
    # =========================================================================

    def execute_wireguard(
        self,
        subcommand: str,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None,
        target_mode: str = "auto",
        timeout_sec: float = 5.0
    ) -> CLIExecutionResult:
        """
        Executes WireGuard commands.
        If local `wg` binary exists, runs locally.
        Otherwise executes natively against the GL.iNet router (/usr/bin/wg).
        For key generation without binary, uses python's cryptographic Curve25519 X25519.
        """
        t0 = time.perf_counter()
        ts_unix = time.time()
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_unix))
        args = args or []
        local_wg = shutil.which("wg")

        # Determine target execution
        if target_mode == "local" or (target_mode == "auto" and local_wg):
            cmd_list = [local_wg or "wg", subcommand] + args
            cmd_str = " ".join(cmd_list)
            try:
                res = subprocess.run(
                    cmd_list,
                    input=stdin_input,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                stdout_str = res.stdout.strip()
                stderr_str = res.stderr.strip()
                extracted = self._extract_network_state("wireguard", stdout_str, None)

                return CLIExecutionResult(
                    tool_name="wireguard",
                    command_line=cmd_str,
                    execution_target="localhost",
                    transport="local_process",
                    timestamp_iso=ts_iso,
                    timestamp_unix=ts_unix,
                    duration_ms=dur_ms,
                    exit_code=res.returncode,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    stdout_sha256=hashlib.sha256(stdout_str.encode("utf-8")).hexdigest(),
                    stderr_sha256=hashlib.sha256(stderr_str.encode("utf-8")).hexdigest(),
                    parsed_json=None,
                    extracted_network_state=extracted
                )
            except Exception as e:
                dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                return CLIExecutionResult(
                    tool_name="wireguard",
                    command_line=cmd_str,
                    execution_target="localhost",
                    transport="local_process",
                    timestamp_iso=ts_iso,
                    timestamp_unix=ts_unix,
                    duration_ms=dur_ms,
                    exit_code=1,
                    stdout="",
                    stderr=str(e),
                    stdout_sha256=hashlib.sha256(b"").hexdigest(),
                    stderr_sha256=hashlib.sha256(str(e).encode()).hexdigest(),
                    parsed_json=None,
                    extracted_network_state={}
                )

        # Route to GL.iNet router (/usr/bin/wg) via SSH
        if subcommand in ["genkey", "pubkey", "show"]:
            if subcommand == "genkey":
                ssh_cmd = "wg genkey"
            elif subcommand == "pubkey" and stdin_input:
                clean_in = stdin_input.strip()
                ssh_cmd = f"echo '{clean_in}' | wg pubkey"
            elif subcommand == "show":
                iface_arg = f" {args[0]}" if args else ""
                ssh_cmd = f"wg show{iface_arg}"
            else:
                ssh_cmd = f"wg {subcommand} {' '.join(args)}"

            ssh_res = self._run_ssh_command(ssh_cmd, timeout_sec=timeout_sec)
            dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            extracted = self._extract_network_state("wireguard", ssh_res.stdout, None)

            # If SSH connection succeeds or even if wg interface is empty, return exact output
            if ssh_res.exit_code == 0 or ssh_res.stdout:
                return CLIExecutionResult(
                    tool_name="wireguard",
                    command_line=f"ssh root@{self.router_ip} {ssh_cmd}",
                    execution_target=f"gw_router ({self.router_ip})",
                    transport="ssh_direct",
                    timestamp_iso=ts_iso,
                    timestamp_unix=ts_unix,
                    duration_ms=dur_ms,
                    exit_code=ssh_res.exit_code,
                    stdout=ssh_res.stdout,
                    stderr=ssh_res.stderr,
                    stdout_sha256=hashlib.sha256(ssh_res.stdout.encode("utf-8")).hexdigest(),
                    stderr_sha256=hashlib.sha256(ssh_res.stderr.encode("utf-8")).hexdigest(),
                    parsed_json=None,
                    extracted_network_state=extracted
                )

        # Fallback to native python cryptographic X25519 implementation
        if subcommand in ["genkey", "pubkey"]:
            py_res = self._crypto_fallback_wireguard(subcommand, stdin_input)
            dur_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return CLIExecutionResult(
                tool_name="wireguard",
                command_line=f"python_crypto_x25519 {subcommand}",
                execution_target="localhost (crypto_fallback)",
                transport="python_x25519_kernel",
                timestamp_iso=ts_iso,
                timestamp_unix=ts_unix,
                duration_ms=dur_ms,
                exit_code=0 if py_res[0] else 1,
                stdout=py_res[0],
                stderr=py_res[1],
                stdout_sha256=hashlib.sha256(py_res[0].encode("utf-8")).hexdigest(),
                stderr_sha256=hashlib.sha256(py_res[1].encode("utf-8")).hexdigest(),
                parsed_json=None,
                extracted_network_state={"curve": "Curve25519", "key_type": subcommand}
            )

        return CLIExecutionResult(
            tool_name="wireguard",
            command_line=f"wg {subcommand} {' '.join(args)}",
            execution_target="none",
            transport="unavailable",
            timestamp_iso=ts_iso,
            timestamp_unix=ts_unix,
            duration_ms=0.0,
            exit_code=127,
            stdout="",
            stderr="WireGuard binary not available locally or on router.",
            stdout_sha256=hashlib.sha256(b"").hexdigest(),
            stderr_sha256=hashlib.sha256(b"error").hexdigest(),
            parsed_json=None,
            extracted_network_state={}
        )

    def _crypto_fallback_wireguard(self, subcommand: str, stdin_input: Optional[str]) -> Tuple[str, str]:
        """Cryptographic Curve25519 fallback for WireGuard key generation."""
        try:
            from cryptography.hazmat.primitives.asymmetric import x25519
            from cryptography.hazmat.primitives import serialization

            if subcommand == "genkey":
                priv = x25519.X25519PrivateKey.generate()
                priv_bytes = priv.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                return base64.b64encode(priv_bytes).decode("ascii"), ""
            elif subcommand == "pubkey" and stdin_input:
                clean_in = stdin_input.strip()
                priv_bytes = base64.b64decode(clean_in)
                priv = x25519.X25519PrivateKey.from_private_bytes(priv_bytes)
                pub = priv.public_key()
                pub_bytes = pub.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
                return base64.b64encode(pub_bytes).decode("ascii"), ""
            else:
                return "", "Missing stdin_input for pubkey"
        except Exception as e:
            return "", str(e)

    # =========================================================================
    # 4. Helper Utilities & State Extraction
    # =========================================================================

    def _run_ssh_command(self, remote_command: str, timeout_sec: float = 5.0) -> Any:
        """Executes a remote command against the OpenWrt router over SSH."""
        ssh_args = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=2",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(self.router_port),
            f"{self.router_user}@{self.router_ip}",
            remote_command
        ]
        try:
            res = subprocess.run(ssh_args, capture_output=True, text=True, timeout=timeout_sec)
            stdout_str = res.stdout.strip()
            stderr_str = res.stderr.strip()
            parsed: Optional[Dict[str, Any]] = None
            try:
                parsed = json.loads(stdout_str)
            except Exception:
                parsed = None

            class SSHRes:
                exit_code = res.returncode
                stdout = stdout_str
                stderr = stderr_str
                parsed_json = parsed

            return SSHRes()
        except Exception as e:
            class SSHErr:
                exit_code = 255
                stdout = ""
                stderr = str(e)
                parsed_json = None
            return SSHErr()

    def _extract_network_state(
        self,
        source_type: str,
        raw_stdout: str,
        parsed_json: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extracts verified network state (carrier, IP addresses, transfer byte counters)
        from CLI command stdout for cross-verification.
        """
        state: Dict[str, Any] = {
            "ip_addresses": [],
            "carrier_status": None,
            "rx_bytes": None,
            "tx_bytes": None,
            "peers": []
        }

        if source_type in ["ubus", "luci_ubus"] and parsed_json:
            # Check carrier in device status
            if "carrier" in parsed_json:
                state["carrier_status"] = bool(parsed_json.get("carrier"))
            elif "up" in parsed_json:
                state["carrier_status"] = bool(parsed_json.get("up"))

            # Check IPs in interface status
            if "ipv4-address" in parsed_json and isinstance(parsed_json["ipv4-address"], list):
                for entry in parsed_json["ipv4-address"]:
                    if isinstance(entry, dict) and "address" in entry:
                        state["ip_addresses"].append(entry["address"])

            # Check statistics
            if "statistics" in parsed_json and isinstance(parsed_json["statistics"], dict):
                stats = parsed_json["statistics"]
                state["rx_bytes"] = stats.get("rx_bytes")
                state["tx_bytes"] = stats.get("tx_bytes")

        elif source_type == "tailscale":
            if parsed_json:
                # Extract self IPs
                if "TailscaleIPs" in parsed_json:
                    state["ip_addresses"].extend(parsed_json.get("TailscaleIPs", []))
                # Backend status
                backend_state = parsed_json.get("BackendState", "")
                state["carrier_status"] = (backend_state == "Running")
                # Peers
                peers_dict = parsed_json.get("Peer", {})
                if isinstance(peers_dict, dict):
                    for p_key, p_val in peers_dict.items():
                        if isinstance(p_val, dict):
                            host = p_val.get("HostName", "")
                            ips = p_val.get("TailscaleIPs", [])
                            rx = p_val.get("RxBytes")
                            tx = p_val.get("TxBytes")
                            state["peers"].append({
                                "hostname": host,
                                "ips": ips,
                                "rx_bytes": rx,
                                "tx_bytes": tx
                            })
            else:
                # Raw text output parsing
                lines = raw_stdout.splitlines()
                for line in lines:
                    line = line.strip()
                    if line and ("." in line or ":" in line) and " " not in line:
                        state["ip_addresses"].append(line)

        elif source_type == "wireguard":
            lines = raw_stdout.splitlines()
            current_peer: Optional[Dict[str, Any]] = None
            for line in lines:
                line = line.strip()
                if line.startswith("peer:"):
                    current_peer = {"peer": line.split(":", 1)[1].strip()}
                    state["peers"].append(current_peer)
                elif line.startswith("transfer:") and current_peer:
                    parts = line.split(":", 1)[1].strip().split(",")
                    if len(parts) >= 2:
                        current_peer["transfer_raw"] = line

        return state

    # =========================================================================
    # 5. Swarm Training Scenarios Suite
    # =========================================================================

    def run_training_suite(self) -> Dict[str, Any]:
        """
        Runs the full suite of Swarm CLI training scenarios across all 3 subsystems:
          1. LuCI Web Console / UBUS Telemetry (LAN status, bridge device status)
          2. Tailscale WireGuard Mesh CLI (status --json, ip -4)
          3. WireGuard Cryptographic CLI (wg genkey, wg pubkey, wg show)
        """
        results: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scenarios_executed": 0,
            "scenarios_passed": 0,
            "executions": []
        }

        # Scenario 1: OpenWrt UBUS LAN status
        r1 = self.execute_ubus("network.interface.lan", "status")
        results["executions"].append(r1.to_dict())
        if r1.exit_code == 0:
            results["scenarios_passed"] += 1
        results["scenarios_executed"] += 1

        # Scenario 2: OpenWrt UBUS device status (br-lan)
        r2 = self.execute_ubus("network.device", "status", {"name": "br-lan"})
        results["executions"].append(r2.to_dict())
        if r2.exit_code == 0:
            results["scenarios_passed"] += 1
        results["scenarios_executed"] += 1

        # Scenario 3: Tailscale status --json
        r3 = self.execute_tailscale("status", ["--json"])
        results["executions"].append(r3.to_dict())
        if r3.exit_code == 0:
            results["scenarios_passed"] += 1
        results["scenarios_executed"] += 1

        # Scenario 4: Tailscale ip -4
        r4 = self.execute_tailscale("ip", ["-4"])
        results["executions"].append(r4.to_dict())
        if r4.exit_code == 0:
            results["scenarios_passed"] += 1
        results["scenarios_executed"] += 1

        # Scenario 5: WireGuard Key Generation & Public Key Derivation
        r5_key = self.execute_wireguard("genkey")
        results["executions"].append(r5_key.to_dict())
        if r5_key.exit_code == 0 and r5_key.stdout:
            results["scenarios_passed"] += 1
            # Derive public key
            r5_pub = self.execute_wireguard("pubkey", stdin_input=r5_key.stdout.strip())
            results["executions"].append(r5_pub.to_dict())
            if r5_pub.exit_code == 0 and r5_pub.stdout:
                results["scenarios_passed"] += 1
            results["scenarios_executed"] += 1
        results["scenarios_executed"] += 1

        # Scenario 6: WireGuard Interface Show
        r6 = self.execute_wireguard("show")
        results["executions"].append(r6.to_dict())
        if r6.exit_code == 0:
            results["scenarios_passed"] += 1
        results["scenarios_executed"] += 1

        results["success"] = (results["scenarios_passed"] == results["scenarios_executed"])
        return results


def main():
    parser = argparse.ArgumentParser(description="🐝 Sovereign Swarm CLI Tool Training Engine")
    parser.add_argument("--tool", choices=["luci", "ubus", "tailscale", "wireguard", "uci"], help="CLI tool to execute")
    parser.add_argument("--cmd", type=str, help="Subcommand or microbus path (e.g. 'status --json', 'network.interface.lan status')")
    parser.add_argument("--params", type=str, default="{}", help="JSON params for ubus/rpc")
    parser.add_argument("--train", action="store_true", help="Execute complete Swarm CLI training suite")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    runner = SwarmCLIRunner()

    if args.train or not args.tool:
        suite_res = runner.run_training_suite()
        if args.json:
            print(json.dumps(suite_res, indent=2))
        else:
            print("================================================================================")
            print("🐝 SWARM CLI TOOL TRAINING ENGINE — EXECUTION REPORT")
            print("================================================================================")
            print(f"Timestamp:          {suite_res['timestamp']}")
            print(f"Scenarios Executed: {suite_res['scenarios_executed']}")
            print(f"Scenarios Passed:   {suite_res['scenarios_passed']}")
            print(f"Overall Status:     {'✅ ALL PASSED' if suite_res['success'] else '⚠️ PARTIAL'}")
            print("--------------------------------------------------------------------------------")
            for exec_item in suite_res["executions"]:
                status_glyph = "✅" if exec_item["exit_code"] == 0 else "❌"
                print(f"{status_glyph} [{exec_item['tool_name']:<14}] {exec_item['command_line']:<45} ({exec_item['duration_ms']}ms)")
                print(f"    Target: {exec_item['execution_target']} | SHA256: {exec_item['stdout_sha256'][:16]}...")
            print("================================================================================")
        sys.exit(0 if suite_res["success"] else 1)

    # Individual tool execution
    if args.tool == "ubus":
        parts = (args.cmd or "system info").split(maxsplit=1)
        subsys = parts[0]
        meth = parts[1] if len(parts) > 1 else "info"
        p_dict = json.loads(args.params)
        res = runner.execute_ubus(subsys, meth, p_dict)
    elif args.tool == "tailscale":
        sub_parts = (args.cmd or "status").split()
        subcmd = sub_parts[0]
        subargs = sub_parts[1:]
        res = runner.execute_tailscale(subcmd, subargs)
    elif args.tool == "wireguard":
        sub_parts = (args.cmd or "genkey").split()
        subcmd = sub_parts[0]
        subargs = sub_parts[1:]
        res = runner.execute_wireguard(subcmd, subargs)
    elif args.tool == "uci":
        parts = (args.cmd or "show network").split(maxsplit=1)
        action = parts[0]
        path = parts[1] if len(parts) > 1 else "network"
        res = runner.execute_uci(action, path)
    else:
        res = runner.execute_luci_rpc("sys", "info")

    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(f"[{res.tool_name}] Exit Code: {res.exit_code} | Duration: {res.duration_ms}ms")
        print(f"SHA256: {res.stdout_sha256}")
        print("Stdout:")
        print(res.stdout)
        if res.stderr:
            print("Stderr:", res.stderr)
    sys.exit(res.exit_code)


if __name__ == "__main__":
    main()
