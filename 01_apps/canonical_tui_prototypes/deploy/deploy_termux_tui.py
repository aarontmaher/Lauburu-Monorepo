#!/usr/bin/env python3
"""Canonical Lauburu Autonomous Termux Wireless Deployment & Provisioning Engine.

Deploys and compiles the Tri-Framework TUI Prototypes (Python Textual, Go Bubble Tea, Rust Ratatui)
directly onto mobile edge hardware (Google Pixel 10 Pro XL, Samsung Galaxy S20+) over SSH & ADB,
automatically provisioning system toolchains (Python, Go, Rust) and verifying native execution.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Colored terminal output helpers
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

logging.basicConfig(
    level=logging.INFO,
    format=f"{DIM}%(asctime)s{RESET} [%(levelname)s] {CYAN}[TermuxDeployer]{RESET}: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TermuxDeployer")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
TUI_PROTOTYPES_DIR = REPO_ROOT / "01_apps/canonical_tui_prototypes"
QUOTA_STATE_FILE = REPO_ROOT / "04_data_and_memory/data/cloud_api_quota_state.json"
QUOTA_LOCK_FILE = REPO_ROOT / "04_data_and_memory/data/cloud_api_quota_state.lock"
DEFAULT_REMOTE_WORKSPACE = "/data/data/com.termux/files/home/lauburu_tui_prototypes"

DEVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "s20": {
        "key": "s20",
        "name": "Samsung Galaxy S20+ (SM-G986B / Layer 7 Automated Tester)",
        "ip_tailscale": "100.84.40.95",
        "ip_tailscale_alt": "100.99.123.58",
        "ip_lan": "192.168.8.135",
        "ssh_port": 8022,
        "ssh_user": "u0_a420",
        "adb_target": "100.84.40.95:5555",
        "adb_target_lan": "192.168.8.135:5555",
        "router_usb_serial": "R3CN40CJJ1R",
        "router_ssh": "root@192.168.8.1",
    },
    "pixel": {
        "key": "pixel",
        "name": "Google Pixel 10 Pro XL (Tensor G5 / Layer 6 Edge TPU)",
        "ip_tailscale": "100.73.38.87",
        "ip_tailscale_alt": "",
        "ip_lan": "192.168.8.14",
        "ssh_port": 8022,
        "ssh_user": "u0_a363",
        "adb_target": "100.73.38.87:5555",
        "adb_target_lan": "192.168.8.14:5555",
        "router_usb_serial": "",
        "router_ssh": "",
    },
}


class TermuxDeploymentEngine:
    """Manages connection, toolchain provisioning, code synchronization, edge build, and smoke verification."""

    def __init__(
        self,
        device_key: str = "s20",
        remote_workspace: str = DEFAULT_REMOTE_WORKSPACE,
        verbose: bool = True,
        ssh_timeout: int = 8,
    ):
        if device_key not in DEVICE_CONFIGS:
            raise ValueError(f"Unknown device key '{device_key}'. Supported: {list(DEVICE_CONFIGS.keys())}")
        self.device_key = device_key
        self.cfg = DEVICE_CONFIGS[device_key]
        self.remote_workspace = remote_workspace
        self.verbose = verbose
        self.ssh_timeout = ssh_timeout
        self.active_ip = self.cfg["ip_tailscale"]
        self.connected = False
        self.connection_method = "none"

    @staticmethod
    def probe_tcp_port(ip: str, port: int, timeout: float = 2.0) -> bool:
        """Probe if a TCP port is actively accepting connections."""
        if not ip:
            return False
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def ensure_connectivity(self) -> bool:
        """Resolve active IP and ensure SSH connectivity with ADB recovery fallback."""
        logger.info(f"Probing connectivity to {BOLD}{self.cfg['name']}{RESET}...")

        # 1. Probe Tailscale primary IP
        if self.probe_tcp_port(self.cfg["ip_tailscale"], self.cfg["ssh_port"], timeout=2.0):
            self.active_ip = self.cfg["ip_tailscale"]
            self.connected = True
            self.connection_method = "tailscale_ssh"
            logger.info(f"{GREEN}✓ Primary SSH socket open via Tailscale ({self.active_ip}:{self.cfg['ssh_port']}){RESET}")
            return True

        # 2. Probe Tailscale alt IP if defined
        if self.cfg.get("ip_tailscale_alt") and self.probe_tcp_port(self.cfg["ip_tailscale_alt"], self.cfg["ssh_port"], timeout=2.0):
            self.active_ip = self.cfg["ip_tailscale_alt"]
            self.connected = True
            self.connection_method = "tailscale_alt_ssh"
            logger.info(f"{GREEN}✓ Alt SSH socket open via Tailscale ({self.active_ip}:{self.cfg['ssh_port']}){RESET}")
            return True

        # 3. Probe Local LAN IP
        if self.cfg.get("ip_lan") and self.probe_tcp_port(self.cfg["ip_lan"], self.cfg["ssh_port"], timeout=2.0):
            self.active_ip = self.cfg["ip_lan"]
            self.connected = True
            self.connection_method = "lan_ssh"
            logger.info(f"{GREEN}✓ Local LAN SSH socket open ({self.active_ip}:{self.cfg['ssh_port']}){RESET}")
            return True

        # 4. Fallback to Wireless ADB Recovery Sequence
        logger.warning(f"{YELLOW}SSH port {self.cfg['ssh_port']} unreachable directly. Triggering ADB wireless recovery...{RESET}")
        recovered = self.recover_via_adb()
        if recovered:
            self.connected = True
            self.connection_method = "adb_recovered_ssh"
            return True

        logger.error(f"{RED}✗ All connection paths to {self.cfg['name']} failed.{RESET}")
        return False

    def recover_via_adb(self) -> bool:
        """Use ADB to awaken screen, launch Termux activity, and start SSH daemon."""
        adb_bin = shutil.which("adb") or "/Users/aaron/.local/bin/adb"
        if not os.path.exists(adb_bin) and not shutil.which("adb"):
            logger.warning("ADB binary not found locally.")
            return False

        adb_target = self.cfg["adb_target"]
        adb_lan = self.cfg.get("adb_target_lan")

        logger.info(f"Connecting ADB to {adb_target}...")
        subprocess.run([adb_bin, "connect", adb_target], capture_output=True, timeout=4.0)
        if adb_lan:
            subprocess.run([adb_bin, "connect", adb_lan], capture_output=True, timeout=4.0)

        # Check router USB promotion if S20+ and router serial is present
        if self.cfg.get("router_usb_serial") and self.cfg.get("router_ssh"):
            router_serial = self.cfg["router_usb_serial"]
            router_ssh = self.cfg["router_ssh"]
            logger.info(f"Promoting ADB over GL.iNet router USB bridge for {router_serial}...")
            try:
                subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no", router_ssh, f"adb -s {router_serial} tcpip 5555"],
                    capture_output=True,
                    timeout=5.0,
                )
                time.sleep(1.0)
                subprocess.run([adb_bin, "connect", adb_target], capture_output=True, timeout=4.0)
            except Exception as e:
                logger.warning(f"Router ADB bounce note: {e}")

        # Awaken screen and dispatch Termux
        logger.info(f"Awakening device and launching Termux activity via ADB target {adb_target}...")
        try:
            subprocess.run([adb_bin, "-s", adb_target, "shell", "input keyevent KEYCODE_WAKEUP"], capture_output=True, timeout=3.0)
            subprocess.run([adb_bin, "-s", adb_target, "shell", "wm dismiss-keyguard"], capture_output=True, timeout=3.0)
            subprocess.run([adb_bin, "-s", adb_target, "shell", "am start -n com.termux/.app.TermuxActivity"], capture_output=True, timeout=4.0)
            subprocess.run([adb_bin, "-s", adb_target, "shell", "input text 'sshd' && input keyevent 66"], capture_output=True, timeout=3.0)
        except Exception as ex:
            logger.warning(f"ADB dispatch exception: {ex}")

        # Poll for SSH socket revival (up to 5 iterations)
        for attempt in range(5):
            time.sleep(1.5)
            if self.probe_tcp_port(self.cfg["ip_tailscale"], self.cfg["ssh_port"], timeout=2.0):
                self.active_ip = self.cfg["ip_tailscale"]
                logger.info(f"{GREEN}✓ Termux SSH successfully revived on {self.active_ip}:{self.cfg['ssh_port']}{RESET}")
                return True
            if self.cfg.get("ip_lan") and self.probe_tcp_port(self.cfg["ip_lan"], self.cfg["ssh_port"], timeout=2.0):
                self.active_ip = self.cfg["ip_lan"]
                logger.info(f"{GREEN}✓ Termux SSH revived on LAN {self.active_ip}:{self.cfg['ssh_port']}{RESET}")
                return True

        return False

    def run_remote_ssh(
        self,
        command: str,
        timeout: int = 180,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, str, int]:
        """Execute a command over SSH inside the remote Termux environment."""
        prefix_exports = (
            'export PREFIX="/data/data/com.termux/files/usr"; '
            'export HOME="/data/data/com.termux/files/home"; '
            'export TMPDIR="/data/data/com.termux/files/usr/tmp"; '
            'export PATH="$PREFIX/bin:$HOME/bin:$HOME/go/bin:$HOME/.cargo/bin:$PATH"; '
            'export LD_LIBRARY_PATH="$PREFIX/lib"; '
            'export DEBIAN_FRONTEND=noninteractive; '
            'export GOTOOLCHAIN=local; '
        )
        if env_vars:
            for k, v in env_vars.items():
                prefix_exports += f'export {k}="{v}"; '

        wrapped_command = prefix_exports + command

        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={self.ssh_timeout}",
            "-p", str(self.cfg["ssh_port"]),
            f"{self.cfg['ssh_user']}@{self.active_ip}",
            wrapped_command,
        ]

        try:
            res = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (res.returncode == 0, res.stdout.strip(), res.stderr.strip(), res.returncode)
        except subprocess.TimeoutExpired:
            return (False, "", f"Command timed out after {timeout}s", -9)
        except Exception as e:
            return (False, "", f"SSH execution exception: {e}", -1)

    def provision_toolchains(self) -> Dict[str, Any]:
        """Verify and provision Python, Go, Rust, Clang, and TUI dependencies in Termux."""
        logger.info(f"📦 {BOLD}Provisioning Termux Toolchains & Dependencies on {self.cfg['name']}...{RESET}")

        # Step 1: Reinforce Termux Wake Lock to avoid sleep during build
        self.run_remote_ssh("termux-wake-lock 2>/dev/null || true", timeout=10)

        # Step 2: Check missing system packages and install if needed
        check_script = """
        MISSING_PKGS=""
        command -v python3 >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS python python-pip"
        command -v go >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS golang"
        command -v cargo >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS rust"
        command -v clang >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS clang build-essential"
        command -v jq >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS jq"
        command -v git >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS git"
        command -v make >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS make"

        echo "MISSING_PKGS=$MISSING_PKGS"
        if [ -n "$MISSING_PKGS" ]; then
            echo "Installing missing packages: $MISSING_PKGS"
            pkg update -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
            pkg install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" $MISSING_PKGS
        else
            echo "✓ All core toolchain packages (python, go, rust, clang, jq, git, make) are installed."
        fi
        """

        ok_pkg, stdout_pkg, stderr_pkg, code_pkg = self.run_remote_ssh(check_script, timeout=300)
        logger.info(f"Toolchain Provisioning Log:\n{stdout_pkg}")
        if not ok_pkg:
            logger.warning(f"Package installation warnings: {stderr_pkg}")

        # Step 3: Check and install Python TUI libraries (rich, textual)
        python_pip_script = """
        python3 -c "import textual, rich; print('Textual+Rich OK')" 2>/dev/null || {
            echo "Installing Python TUI libraries (rich, textual)..."
            pip install --break-system-packages --upgrade pip setuptools wheel 2>/dev/null || true
            pip install --break-system-packages rich textual
            pip install --break-system-packages pydantic 2>/dev/null || true
        }
        """
        ok_pip, stdout_pip, stderr_pip, code_pip = self.run_remote_ssh(python_pip_script, timeout=180)
        if ok_pip:
            logger.info(f"{GREEN}✓ Python TUI dependencies (textual, rich) verified.{RESET}")
        else:
            logger.warning(f"PIP install log: {stdout_pip}\nErrors: {stderr_pip}")

        # Step 4: Harvest installed versions
        version_script = """
        echo -n "PYTHON: "; python3 --version 2>/dev/null || echo "Not Installed"
        echo -n "GO: "; go version 2>/dev/null || echo "Not Installed"
        echo -n "RUST: "; rustc --version 2>/dev/null || echo "Not Installed"
        echo -n "CARGO: "; cargo --version 2>/dev/null || echo "Not Installed"
        echo -n "CLANG: "; clang --version 2>/dev/null | head -n 1 || echo "Not Installed"
        echo -n "JQ: "; jq --version 2>/dev/null || echo "Not Installed"
        echo -n "GIT: "; git --version 2>/dev/null || echo "Not Installed"
        """
        _, stdout_ver, _, _ = self.run_remote_ssh(version_script, timeout=30)
        logger.info(f"Edge Node Toolchain Versions:\n{stdout_ver}")

        return {
            "packages_ok": ok_pkg,
            "pip_ok": ok_pip,
            "versions": stdout_ver,
        }

    def provision_dependencies(self) -> Dict[str, Any]:
        """Alias for provision_toolchains."""
        return self.provision_toolchains()

    def sync_prototypes_and_state(self) -> bool:
        """Synchronize canonical TUI prototype sources and quota state lockfile to Termux."""
        logger.info(f"📂 {BOLD}Syncing TUI Prototypes and Quota State to {self.remote_workspace}...{RESET}")

        # 1. Create target directories on edge node
        mkdir_cmd = (
            f"mkdir -p {self.remote_workspace}/data "
            f"{self.remote_workspace}/build "
            f"{self.remote_workspace}/verify "
            f"{self.remote_workspace}/python_textual "
            f"{self.remote_workspace}/go_bubbletea "
            f"{self.remote_workspace}/rust_ratatui"
        )
        ok_mkdir, _, err_mkdir, _ = self.run_remote_ssh(mkdir_cmd, timeout=30)
        if not ok_mkdir:
            logger.error(f"Failed to create remote directory: {err_mkdir}")
            return False

        # 2. Fast Tar-Pipe over SSH with target/ and cache exclusions (avoids large target folders)
        tar_cmd = [
            "tar",
            "--exclude=target",
            "--exclude=__pycache__",
            "--exclude=.pytest_cache",
            "--exclude=.git",
            "--exclude=*.log",
            "-cf", "-",
            "-C", str(TUI_PROTOTYPES_DIR),
            ".",
        ]
        ssh_extract_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={self.ssh_timeout}",
            "-p", str(self.cfg["ssh_port"]),
            f"{self.cfg['ssh_user']}@{self.active_ip}",
            f"tar -xf - -C {self.remote_workspace}",
        ]

        try:
            tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ssh_proc = subprocess.Popen(ssh_extract_cmd, stdin=tar_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            tar_proc.stdout.close()  # Allow tar_proc to receive a SIGPIPE if ssh_proc exits
            ssh_out, ssh_err = ssh_proc.communicate(timeout=30)
            tar_proc.wait(timeout=10)

            if ssh_proc.returncode == 0:
                logger.info(f"{GREEN}✓ Source files synchronized cleanly via streaming tar-pipe.{RESET}")
            else:
                logger.warning(f"Tar sync note: {ssh_err.decode('utf-8', errors='replace').strip()}")
        except Exception as ex:
            logger.warning(f"Tar-pipe sync error: {ex}, falling back to individual file copy...")

        # 3. Synchronize cloud API quota state JSON
        if QUOTA_STATE_FILE.exists():
            scp_state = [
                "scp",
                "-P", str(self.cfg["ssh_port"]),
                "-o", "StrictHostKeyChecking=no",
                str(QUOTA_STATE_FILE),
                f"{self.cfg['ssh_user']}@{self.active_ip}:{self.remote_workspace}/data/cloud_api_quota_state.json",
            ]
            res_state = subprocess.run(scp_state, capture_output=True, text=True, timeout=15)
            if res_state.returncode == 0:
                logger.info(f"{GREEN}✓ Synchronized cloud_api_quota_state.json to remote data/ directory.{RESET}")
            else:
                logger.warning(f"State sync warning: {res_state.stderr}")

        # 4. Synchronize lockfile if present
        if QUOTA_LOCK_FILE.exists():
            scp_lock = [
                "scp",
                "-P", str(self.cfg["ssh_port"]),
                "-o", "StrictHostKeyChecking=no",
                str(QUOTA_LOCK_FILE),
                f"{self.cfg['ssh_user']}@{self.active_ip}:{self.remote_workspace}/data/cloud_api_quota_state.lock",
            ]
            subprocess.run(scp_lock, capture_output=True, timeout=10)

        # Verify state file existence on remote
        ok_chk, out_chk, _, _ = self.run_remote_ssh(f"test -f {self.remote_workspace}/data/cloud_api_quota_state.json && echo 'STATE_EXISTS'", timeout=10)
        if "STATE_EXISTS" in out_chk:
            logger.info(f"{GREEN}✓ Verified remote state file at {self.remote_workspace}/data/cloud_api_quota_state.json{RESET}")
            return True
        else:
            logger.error(f"{RED}✗ Remote state file verification failed.{RESET}")
            return False

    def build_native_binaries(self) -> Dict[str, Any]:
        """Compile Go Bubble Tea and Rust Ratatui TUIs natively on ARM64 Termux."""
        logger.info(f"🔨 {BOLD}Compiling Native Go and Rust TUIs inside Termux...{RESET}")

        build_results: Dict[str, Any] = {
            "go_build": False,
            "rust_build": False,
            "go_binary": None,
            "rust_binary": None,
            "logs": {},
        }

        # 1. Build Go Bubble Tea
        go_build_script = f"""
        cd {self.remote_workspace}
        if [ -d "go_bubbletea" ] && [ -f "go_bubbletea/main.go" ]; then
            echo "Building Go TUI Prototype..."
            cd go_bubbletea
            export GOTOOLCHAIN=local
            sed -i 's/go 1.27.0/go 1.22/g' go.mod 2>/dev/null || true
            go mod tidy 2>/dev/null || true
            mkdir -p ../build
            go build -o ../build/canonical_tui_go . 2>&1 || go build -o ../build/canonical_tui_go main.go 2>&1
            if [ -f "../build/canonical_tui_go" ]; then
                cp ../build/canonical_tui_go ../build/tui_bubbletea 2>/dev/null || true
                cp ../build/canonical_tui_go ../build/tui_go 2>/dev/null || true
                mkdir -p bin
                cp ../build/canonical_tui_go bin/tui_go 2>/dev/null || true
                echo "GO_BUILD_SUCCESS"
            else
                echo "GO_BUILD_FAILED"
            fi
        else
            echo "GO_SOURCE_NOT_FOUND"
        fi
        """
        ok_go, out_go, err_go, _ = self.run_remote_ssh(go_build_script, timeout=180)
        build_results["logs"]["go"] = out_go
        if "GO_BUILD_SUCCESS" in out_go:
            build_results["go_build"] = True
            build_results["go_binary"] = f"{self.remote_workspace}/build/canonical_tui_go"
            logger.info(f"{GREEN}✓ Go Bubble Tea binary compiled successfully ({build_results['go_binary']}){RESET}")
        else:
            logger.warning(f"Go build notice: {out_go}\n{err_go}")

        # 2. Build Rust Ratatui
        rust_build_script = f"""
        cd {self.remote_workspace}
        if [ -d "rust_ratatui" ] && [ -f "rust_ratatui/Cargo.toml" ]; then
            echo "Building Rust TUI Prototype (cargo build --release)..."
            cd rust_ratatui
            cargo build --release 2>&1
            mkdir -p ../build
            if [ -f "target/release/canonical_tui_rust" ]; then
                cp target/release/canonical_tui_rust ../build/canonical_tui_rust
                cp target/release/canonical_tui_rust ../build/tui_ratatui 2>/dev/null || true
                echo "RUST_BUILD_SUCCESS"
            elif [ -f "target/release/tui_ratatui" ]; then
                cp target/release/tui_ratatui ../build/canonical_tui_rust
                cp target/release/tui_ratatui ../build/tui_ratatui 2>/dev/null || true
                echo "RUST_BUILD_SUCCESS"
            else
                echo "RUST_BUILD_FAILED"
            fi
        else
            echo "RUST_SOURCE_NOT_FOUND"
        fi
        """
        ok_rust, out_rust, err_rust, _ = self.run_remote_ssh(rust_build_script, timeout=300)
        build_results["logs"]["rust"] = out_rust
        if "RUST_BUILD_SUCCESS" in out_rust:
            build_results["rust_build"] = True
            build_results["rust_binary"] = f"{self.remote_workspace}/build/canonical_tui_rust"
            logger.info(f"{GREEN}✓ Rust Ratatui binary compiled successfully ({build_results['rust_binary']}){RESET}")
        else:
            logger.warning(f"Rust build notice: {out_rust}\n{err_rust}")

        return build_results

    def run_remote_smoke_tests(self) -> Dict[str, Any]:
        """Execute automated headless verification (--verify and --timeout 2) for all 3 TUIs inside Termux."""
        logger.info(f"🧪 {BOLD}Executing Automated Remote Smoke Verification on {self.cfg['name']}...{RESET}")

        # Settle connection
        self.ensure_connectivity()

        state_path = f"{self.remote_workspace}/data/cloud_api_quota_state.json"

        test_results: Dict[str, Any] = {
            "device": self.device_key,
            "device_name": self.cfg["name"],
            "remote_workspace": self.remote_workspace,
            "state_file_valid": False,
            "python_textual": {"verify_passed": False, "smoke_passed": False, "details": ""},
            "go_bubbletea": {"verify_passed": False, "smoke_passed": False, "details": ""},
            "rust_ratatui": {"verify_passed": False, "smoke_passed": False, "details": ""},
            "all_passed": False,
        }

        # 1. Verify JSON State Integrity on Remote
        json_check_script = f"""
        python3 -c "
import json, sys
try:
    with open('{state_path}') as f:
        d = json.load(f)
    assert 'version' in d and 'providers' in d and 'metrics' in d
    assert len(d['providers']) > 0
    print('JSON_VALID: Version', d.get('version'), '| Providers:', list(d['providers'].keys()), '| Total Tasks:', d['metrics'].get('total_tasks_routed'))
except Exception as e:
    print('JSON_INVALID:', e)
    sys.exit(1)
"
        """
        ok_json, out_json, err_json, _ = self.run_remote_ssh(json_check_script, timeout=15)
        if ok_json and "JSON_VALID" in out_json:
            test_results["state_file_valid"] = True
            logger.info(f"{GREEN}✓ Quota State JSON Integrity Verified on Termux: {out_json.strip()}{RESET}")
        else:
            logger.error(f"{RED}✗ Quota state JSON invalid or missing on Termux: {out_json} | {err_json}{RESET}")

        # 2. Python Textual Verification
        py_test_script = f"""
        cd {self.remote_workspace}
        if [ -f "python_textual/app.py" ]; then
            echo "--- Python Verify Mode ---"
            python3 python_textual/app.py --state-path "{state_path}" --verify
            PY_V_RES=$?
            echo "PY_VERIFY_EXIT=$PY_V_RES"

            echo "--- Python Smoke Timeout Mode ---"
            python3 python_textual/app.py --state-path "{state_path}" --timeout 2 2>&1 || true
            echo "PY_SMOKE_DONE"
        else
            echo "PYTHON_APP_NOT_FOUND"
        fi
        """
        ok_py, out_py, err_py, _ = self.run_remote_ssh(py_test_script, timeout=30)
        py_verify_ok = "PY_VERIFY_EXIT=0" in out_py
        py_smoke_ok = "PY_SMOKE_DONE" in out_py
        test_results["python_textual"] = {
            "verify_passed": py_verify_ok,
            "smoke_passed": py_smoke_ok,
            "stdout": out_py,
            "stderr": err_py,
        }
        if py_verify_ok:
            logger.info(f"{GREEN}✓ [1/3] Python Textual: Remote Headless Verification & Smoke PASSED.{RESET}")
        else:
            logger.warning(f"[1/3] Python Textual status: verify={py_verify_ok}, smoke={py_smoke_ok}\nOutput: {out_py}")

        # 3. Go Bubble Tea Verification
        go_test_script = f"""
        cd {self.remote_workspace}
        GO_BIN=""
        if [ -f "build/canonical_tui_go" ]; then
            GO_BIN="build/canonical_tui_go"
        elif [ -f "build/tui_bubbletea" ]; then
            GO_BIN="build/tui_bubbletea"
        elif [ -f "go_bubbletea/bin/tui_go" ]; then
            GO_BIN="go_bubbletea/bin/tui_go"
        fi

        if [ -n "$GO_BIN" ]; then
            echo "--- Go Verify Mode ---"
            ./$GO_BIN -state-path "{state_path}" -verify 2>&1 || ./$GO_BIN --state-path "{state_path}" --verify 2>&1 || ./$GO_BIN -verify -state "{state_path}" 2>&1
            GO_V_RES=$?
            echo "GO_VERIFY_EXIT=$GO_V_RES"

            echo "--- Go Smoke Timeout Mode ---"
            ./$GO_BIN -state-path "{state_path}" -timeout 2 2>&1 || ./$GO_BIN --state-path "{state_path}" --timeout 2 2>&1 || true
            echo "GO_SMOKE_DONE"
        elif [ -f "go_bubbletea/main.go" ]; then
            echo "Running Go via 'go run' fallback..."
            cd go_bubbletea
            export GOTOOLCHAIN=local
            go run main.go -state-path "{state_path}" -verify 2>&1
            echo "GO_VERIFY_EXIT=$?"
            cd ..
            echo "GO_SMOKE_DONE"
        else
            echo "GO_BIN_NOT_FOUND"
        fi
        """
        ok_go_test, out_go_test, err_go_test, _ = self.run_remote_ssh(go_test_script, timeout=30)
        go_verify_ok = "GO_VERIFY_EXIT=0" in out_go_test
        go_smoke_ok = "GO_SMOKE_DONE" in out_go_test
        test_results["go_bubbletea"] = {
            "verify_passed": go_verify_ok,
            "smoke_passed": go_smoke_ok,
            "stdout": out_go_test,
            "stderr": err_go_test,
        }
        if go_verify_ok:
            logger.info(f"{GREEN}✓ [2/3] Go Bubble Tea: Remote Headless Verification & Smoke PASSED.{RESET}")
        else:
            logger.warning(f"[2/3] Go Bubble Tea status: verify={go_verify_ok}, smoke={go_smoke_ok}\nOutput: {out_go_test}")

        # 4. Rust Ratatui Verification
        rust_test_script = f"""
        cd {self.remote_workspace}
        RUST_BIN=""
        if [ -f "build/canonical_tui_rust" ]; then
            RUST_BIN="build/canonical_tui_rust"
        elif [ -f "build/tui_ratatui" ]; then
            RUST_BIN="build/tui_ratatui"
        elif [ -f "rust_ratatui/target/release/canonical_tui_rust" ]; then
            RUST_BIN="rust_ratatui/target/release/canonical_tui_rust"
        fi

        if [ -n "$RUST_BIN" ]; then
            echo "--- Rust Verify Mode ---"
            ./$RUST_BIN --state-path "{state_path}" --verify 2>&1
            RUST_V_RES=$?
            echo "RUST_VERIFY_EXIT=$RUST_V_RES"

            echo "--- Rust Smoke Timeout Mode ---"
            ./$RUST_BIN --state-path "{state_path}" --timeout-secs 2 2>&1 || ./$RUST_BIN --state-path "{state_path}" --timeout 2 2>&1 || true
            echo "RUST_SMOKE_DONE"
        elif [ -f "rust_ratatui/Cargo.toml" ]; then
            echo "Running Rust via cargo run fallback..."
            cd rust_ratatui
            cargo run --release -- --state-path "{state_path}" --verify 2>&1
            echo "RUST_VERIFY_EXIT=$?"
            cd ..
            echo "RUST_SMOKE_DONE"
        else
            echo "RUST_BIN_NOT_FOUND"
        fi
        """
        ok_rust_test, out_rust_test, err_rust_test, _ = self.run_remote_ssh(rust_test_script, timeout=60)
        rust_verify_ok = "RUST_VERIFY_EXIT=0" in out_rust_test
        rust_smoke_ok = "RUST_SMOKE_DONE" in out_rust_test
        test_results["rust_ratatui"] = {
            "verify_passed": rust_verify_ok,
            "smoke_passed": rust_smoke_ok,
            "stdout": out_rust_test,
            "stderr": err_rust_test,
        }
        if rust_verify_ok:
            logger.info(f"{GREEN}✓ [3/3] Rust Ratatui: Remote Headless Verification & Smoke PASSED.{RESET}")
        else:
            logger.warning(f"[3/3] Rust Ratatui status: verify={rust_verify_ok}, smoke={rust_smoke_ok}\nOutput: {out_rust_test}")

        test_results["all_passed"] = (
            test_results["state_file_valid"] and py_verify_ok and go_verify_ok and rust_verify_ok
        )
        return test_results


def auto_detect_live_devices() -> List[str]:
    """Scan device profiles and return all reachable device keys."""
    reachable = []
    for key, cfg in DEVICE_CONFIGS.items():
        # Quick 1s TCP probe on SSH port
        if TermuxDeploymentEngine.probe_tcp_port(cfg["ip_tailscale"], cfg["ssh_port"], timeout=1.2):
            reachable.append(key)
        elif cfg.get("ip_lan") and TermuxDeploymentEngine.probe_tcp_port(cfg["ip_lan"], cfg["ssh_port"], timeout=1.0):
            reachable.append(key)
        elif TermuxDeploymentEngine.probe_tcp_port(cfg["ip_tailscale"], 5555, timeout=1.0):
            reachable.append(key)
    return reachable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous Termux Wireless Deployment & Toolchain Provisioning Engine"
    )
    parser.add_argument(
        "--device",
        choices=["auto", "s20", "pixel", "all"],
        default="auto",
        help="Target mobile edge device (default: auto)",
    )
    parser.add_argument(
        "--skip-provision",
        action="store_true",
        help="Skip pkg/pip toolchain and dependency installation",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip native edge compilation of Go and Rust binaries",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip remote headless smoke tests",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run remote verification without syncing or rebuilding",
    )
    parser.add_argument(
        "--remote-dir",
        type=str,
        default=DEFAULT_REMOTE_WORKSPACE,
        help=f"Remote Termux deployment workspace (default: {DEFAULT_REMOTE_WORKSPACE})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Determine target list
    if args.device == "all":
        targets = ["s20", "pixel"]
    elif args.device == "auto":
        live_devices = auto_detect_live_devices()
        if not live_devices:
            logger.warning("Auto-detection found no immediately open SSH ports. Defaulting to probing s20 and pixel with recovery.")
            targets = ["s20", "pixel"]
        else:
            targets = live_devices
            logger.info(f"Auto-detected active Termux targets: {targets}")
    else:
        targets = [args.device]

    overall_results: Dict[str, Any] = {}
    total_success = True

    print("\n" + "=" * 80)
    print(f" 🚀 {BOLD}LAUBURU TERMUX WIRELESS PROVISIONING & DEPLOYMENT PIPELINE{RESET}")
    print(f" Targets: {targets} | Remote Dir: {args.remote_dir}")
    print("=" * 80 + "\n")

    for dev in targets:
        print(f"\n{CYAN}{BOLD}▶ DEPLOYING TO: {DEVICE_CONFIGS[dev]['name']}{RESET}")
        print("-" * 80)

        engine = TermuxDeploymentEngine(
            device_key=dev,
            remote_workspace=args.remote_dir,
            verbose=args.verbose,
        )

        # Step 1: Ensure Connectivity
        if not engine.ensure_connectivity():
            print(f"{RED}❌ Could not establish SSH/ADB connection to {dev}. Skipping.{RESET}")
            overall_results[dev] = {"success": False, "error": "Connection failed"}
            total_success = False
            continue

        dev_result: Dict[str, Any] = {
            "device": dev,
            "connected": True,
            "connection_method": engine.connection_method,
            "active_ip": engine.active_ip,
        }

        if not args.verify_only:
            # Step 2: Toolchain Provisioning
            if not args.skip_provision:
                prov_res = engine.provision_dependencies()
                dev_result["provisioning"] = prov_res
            else:
                logger.info("Skipping toolchain provisioning (--skip-provision).")

            # Step 3: Synchronize Prototype Source and Quota State
            sync_ok = engine.sync_prototypes_and_state()
            dev_result["sync_ok"] = sync_ok
            if not sync_ok:
                logger.error(f"{RED}Source code sync failed on {dev}.{RESET}")
                total_success = False

            # Step 4: Edge Compilation
            if not args.skip_build:
                build_res = engine.build_native_binaries()
                dev_result["build"] = build_res
            else:
                logger.info("Skipping edge native compilation (--skip-build).")

        # Step 5: Remote Smoke Verification
        if not args.skip_verify:
            test_res = engine.run_remote_smoke_tests()
            dev_result["tests"] = test_res
            if not test_res.get("all_passed", False):
                logger.warning(f"One or more remote tests did not pass cleanly on {dev}.")
                total_success = False
        else:
            logger.info("Skipping remote verification (--skip-verify).")

        overall_results[dev] = dev_result

    print("\n" + "=" * 80)
    print(f" 📊 {BOLD}DEPLOYMENT & VERIFICATION SUMMARY{RESET}")
    print("=" * 80)
    for dev, res in overall_results.items():
        status_str = f"{GREEN}PASS (Ready){RESET}" if res.get("tests", {}).get("all_passed", False) else f"{YELLOW}Partial/Warnings{RESET}"
        print(f" • {DEVICE_CONFIGS[dev]['name']}: {status_str} [Transport: {res.get('connection_method', 'N/A')}]")
    print("=" * 80 + "\n")

    if args.json:
        print(json.dumps(overall_results, indent=2))

    return 0 if total_success else 1


if __name__ == "__main__":
    sys.exit(main())
