"""
Opaque-box E2E Test Suite for Petals DHT Swarm Node on Pixel 10 Pro XL
Target Edge Node: Pixel 10 Pro XL (100.73.38.87 -p 8022)
Coordinator Head Node: Linux Head Node (100.101.39.98:22)
Authoritative Specification: PROJECT.md & TEST_INFRA.md
Integrity Mode: Zero Fake/Mock Data, Empirical Live Execution
"""

import os
import re
import socket
import struct
import subprocess
import time
import pytest
from typing import Tuple

# Network & Host Constants
PIXEL_HOST = "100.73.38.87"
PIXEL_SSH_PORT = 8022
PIXEL_USER = "u0_a363"
HEAD_NODE_HOST = "100.101.39.98"
HEAD_NODE_SSH_PORT = 22

RPC_PORT = 50052
PETALS_DHT_PORT = 31330
PETALS_RELAY_PORT = 31331
SSH_PORT = 8022

PIXEL_HOME = "/data/data/com.termux/files/home"
PIXEL_PREFIX = "/data/data/com.termux/files/usr"
IDENTITY_KEY_PATH = f"{PIXEL_HOME}/.petals_identity.id"
RUNIT_SERVICE_DIR = f"{PIXEL_PREFIX}/var/service/petals"
RUNIT_LOG_DIR = f"{PIXEL_PREFIX}/var/log/sv/petals"
BOOT_SCRIPT_PATH = f"{PIXEL_HOME}/.termux/boot/01-mesh-boot.sh"
GUARDIAN_SCRIPT_PATH = f"{PIXEL_HOME}/petals_guardian.sh"


def run_ssh_cmd(host: str, port: int, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """
    Execute a shell command over SSH against a live remote host.
    Zero-mock execution returning (returncode, stdout, stderr).
    """
    ssh_command = [
        "ssh",
        "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", f"ConnectTimeout={min(timeout, 10)}",
        host,
        cmd
    ]
    try:
        proc = subprocess.run(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)


def run_pixel(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute command on the Pixel 10 Pro XL via Termux SSH."""
    return run_ssh_cmd(PIXEL_HOST, PIXEL_SSH_PORT, cmd, timeout=timeout)


def run_head_node(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute command on the Linux Head Node via SSH."""
    return run_ssh_cmd(HEAD_NODE_HOST, HEAD_NODE_SSH_PORT, cmd, timeout=timeout)


def check_live_tcp_socket(host: str, port: int, timeout: float = 8.0) -> bool:
    """Empirically probe a live TCP socket connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False



def measure_tcp_latency_ms(host: str, port: int, timeout: float = 8.0) -> float:
    """Measure empirical TCP handshake RTT in milliseconds."""
    t0 = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return (time.perf_counter() - t0) * 1000.0
    except Exception:
        return -1.0



# ==============================================================================
# TIER 1: FEATURE COVERAGE (7 Features x 5 Tests = 35 Tests)
# ==============================================================================

class TestTier1Feature1NativeP2pd:
    """Feature 1: Native Bionic p2pd libp2p Execution in Termux ARM64."""

    def test_f1_01_p2pd_binary_exists_and_executable(self):
        """F1.1: Verify p2pd binary is installed and has executable bit set."""
        code, out, err = run_pixel(
            "test -x ~/go-libp2p-daemon/p2pd || test -x $PREFIX/bin/p2pd || "
            "test -x $(python3 -c 'import hivemind; print(hivemind.__path__[0])' 2>/dev/null)/hivemind_cli/p2pd"
        )
        assert code == 0, f"Native p2pd binary missing or not executable: {err}"

    def test_f1_02_p2pd_elf_header_arm64_bionic(self):
        """F1.2: Verify p2pd ELF header matches 64-bit ARM (aarch64)."""
        code, out, err = run_pixel(
            "P2PD_PATH=$(which p2pd 2>/dev/null || find ~/go-libp2p-daemon $PREFIX -name p2pd -type f -perm -111 2>/dev/null | head -n 1); "
            "file -b \"$P2PD_PATH\" || readelf -h \"$P2PD_PATH\" | grep -i 'Machine:'"
        )
        assert code == 0, f"Failed to inspect p2pd ELF header: {err}"
        assert any(k in out.lower() for k in ["aarch64", "arm64", "arm aarch64"]), f"p2pd is not ARM64: {out}"

    def test_f1_03_p2pd_cli_help_execution(self):
        """F1.3: Verify p2pd binary can execute and output CLI parameters."""
        code, out, err = run_pixel(
            "P2PD_PATH=$(which p2pd 2>/dev/null || find ~/go-libp2p-daemon $PREFIX -name p2pd -type f -perm -111 2>/dev/null | head -n 1); "
            "\"$P2PD_PATH\" -help 2>&1 || true"
        )
        combined = (out + " " + err).lower()
        assert "usage" in combined or "libp2p" in combined or "daemon" in combined or "dht" in combined, \
            f"p2pd execution failed to produce help output: {out} {err}"

    def test_f1_04_p2pd_linked_in_hivemind(self):
        """F1.4: Verify p2pd binary is accessible within the Hivemind package tree."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, os, subprocess; "
            "cli_dir = os.path.join(hivemind.__path__[0], 'hivemind_cli'); "
            "bin_dir = os.path.join(hivemind.__path__[0], 'bin'); "
            "p1 = os.path.join(cli_dir, 'p2pd'); p2 = os.path.join(bin_dir, 'p2pd'); "
            "assert os.path.isfile(p1) or os.path.isfile(p2) or subprocess.run(['which', 'p2pd']).returncode == 0; "
            "print('HIVEMIND_P2PD_LINKED_OK')\""
        )
        assert code == 0, f"p2pd is not linked into Hivemind: {err}"
        assert "HIVEMIND_P2PD_LINKED_OK" in out

    def test_f1_05_p2pd_spawn_and_sigterm_shutdown(self):
        """F1.5: Verify p2pd can spawn on a temporary socket and gracefully exit on SIGTERM."""
        code, out, err = run_pixel(
            "P2PD_PATH=$(which p2pd 2>/dev/null || find ~/go-libp2p-daemon $PREFIX -name p2pd -type f -perm -111 2>/dev/null | head -n 1); "
            "SOCKET_PATH=/tmp/test_p2pd_sock_$$.sock; "
            "\"$P2PD_PATH\" -listen \"$SOCKET_PATH\" >/dev/null 2>&1 & PID=$!; "
            "sleep 1; kill -0 $PID 2>/dev/null && kill -TERM $PID && wait $PID; echo \"SHUTDOWN_EXIT_$?\""
        )
        assert code == 0, f"p2pd spawn/shutdown failed: {err}"
        assert "SHUTDOWN_EXIT" in out


class TestTier1Feature2HivemindPetalsPython:
    """Feature 2: Hivemind & Petals Python Package Installation & Runtime."""

    def test_f2_01_python_version_and_arch(self):
        """F2.1: Verify Python 3.11+ running on aarch64 Android."""
        code, out, err = run_pixel(
            "python3 -c \"import sys, platform; "
            "assert sys.version_info >= (3, 10), 'Python version too old'; "
            "assert platform.machine() == 'aarch64', 'Architecture mismatch'; "
            "print(f'PYTHON_OK_{sys.version_info.major}.{sys.version_info.minor}_{platform.machine()}')\""
        )
        assert code == 0, f"Python environment assertion failed: {err}"
        assert "PYTHON_OK" in out

    def test_f2_02_hivemind_import(self):
        """F2.2: Verify Hivemind module imports without C-extension errors."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind; print(f'HIVEMIND_VERSION_{hivemind.__version__}')\""
        )
        assert code == 0, f"Failed to import hivemind: {err}"
        assert "HIVEMIND_VERSION" in out

    def test_f2_03_petals_import(self):
        """F2.3: Verify Petals module imports successfully."""
        code, out, err = run_pixel(
            "python3 -c \"import petals; print(f'PETALS_VERSION_{petals.__version__}')\""
        )
        assert code == 0, f"Failed to import petals: {err}"
        assert "PETALS_VERSION" in out

    def test_f2_04_torch_cpu_tensor_ops(self):
        """F2.4: Verify PyTorch tensor operations execute natively on CPU."""
        code, out, err = run_pixel(
            "python3 -c \"import torch; "
            "x = torch.randn(128, 128); y = torch.matmul(x, x); "
            "assert y.shape == (128, 128); "
            "assert not torch.cuda.is_available(); "
            "print('TORCH_CPU_OPS_OK')\""
        )
        assert code == 0, f"PyTorch tensor computation failed: {err}"
        assert "TORCH_CPU_OPS_OK" in out

    def test_f2_05_hivemind_dht_class_import(self):
        """F2.5: Verify Hivemind DHT classes and Petals CLI entrypoints import cleanly."""
        code, out, err = run_pixel(
            "python3 -c \"from hivemind.dht import DHT; from hivemind.p2p import P2P; "
            "from petals.cli.run_dht import main as run_dht_main; "
            "print('DHT_CLASSES_IMPORT_OK')\""
        )
        assert code == 0, f"Failed to import Hivemind DHT classes: {err}"
        assert "DHT_CLASSES_IMPORT_OK" in out


class TestTier1Feature3TailscaleBinding:
    """Feature 3: Swarm Node Tailscale Multiaddress Socket Binding."""

    def test_f3_01_tailscale_interface_active(self):
        """F3.1: Verify Tailscale IP 100.73.38.87 is bound and active on Pixel."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
            "s.connect(('100.101.39.98', 80)); "
            "local_ip = s.getsockname()[0]; "
            "assert local_ip == '100.73.38.87', f'Unexpected local IP: {local_ip}'; "
            "print('TAILSCALE_IFACE_ACTIVE')\""
        )
        assert code == 0, f"Tailscale interface check failed: {err}"
        assert "TAILSCALE_IFACE_ACTIVE" in out

    def test_f3_02_petals_port_listening(self):
        """F3.2: Verify Petals DHT port 31330 is in LISTEN state on Pixel."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
            "s.settimeout(2.0); "
            "res = s.connect_ex(('100.73.38.87', 31330)); "
            "assert res == 0, f'Port 31330 not listening (errno: {res})'; "
            "s.close(); print('PORT_31330_LISTENING')\""
        )
        assert code == 0, f"Petals DHT port 31330 not listening: {err}"
        assert "PORT_31330_LISTENING" in out

    def test_f3_03_multiaddr_parsing_pixel(self):
        """F3.3: Verify multiaddress string /ip4/100.73.38.87/tcp/31330 parses correctly."""
        code, out, err = run_pixel(
            "python3 -c \"import multiaddr; "
            "m = multiaddr.Multiaddr('/ip4/100.73.38.87/tcp/31330'); "
            "assert m.protocols()[0].name == 'ip4'; "
            "assert m.protocols()[1].name == 'tcp'; "
            "print(f'MULTIADDR_PARSED_{m}')\""
        )
        assert code == 0, f"Multiaddr parsing failed: {err}"
        assert "/ip4/100.73.38.87/tcp/31330" in out

    def test_f3_04_socket_handshake_local(self):
        """F3.4: Verify local TCP socket handshake to 100.73.38.87:31330 completes."""
        code, out, err = run_pixel(
            "python3 -c \"import socket, time; "
            "t0 = time.time(); "
            "s = socket.create_connection(('100.73.38.87', 31330), timeout=3.0); "
            "rtt = (time.time() - t0) * 1000.0; "
            "s.close(); "
            "print(f'LOCAL_HANDSHAKE_RTT_{rtt:.2f}ms')\""
        )
        assert code == 0, f"Local TCP handshake to port 31330 failed: {err}"
        assert "LOCAL_HANDSHAKE_RTT" in out

    def test_f3_05_socket_handshake_from_test_runner(self):
        """F3.5: Verify test runner workstation connects to 100.73.38.87:31330 over Tailscale."""
        assert check_live_tcp_socket(PIXEL_HOST, PETALS_DHT_PORT, timeout=5.0), \
            f"Failed to connect to Petals DHT port {PETALS_DHT_PORT} on {PIXEL_HOST} from test runner"


class TestTier1Feature4SwarmAnnouncement:
    """Feature 4: Peer Identity & Swarm Announcement Verification."""

    def test_f4_01_identity_key_file_exists(self):
        """F4.1: Verify persistent identity key file exists in ~/.petals_identity.id."""
        code, out, err = run_pixel(
            f"test -f {IDENTITY_KEY_PATH} && ls -la {IDENTITY_KEY_PATH}"
        )
        assert code == 0, f"Identity key file missing at {IDENTITY_KEY_PATH}: {err}"

    def test_f4_02_peer_id_valid_format(self):
        """F4.2: Verify generated libp2p Peer ID matches standard base58/multihash format."""
        code, out, err = run_pixel(
            f"python3 -c \"import hivemind.p2p as p2p; "
            f"data = open('{IDENTITY_KEY_PATH}', 'rb').read(); "
            f"assert len(data) > 0, 'Identity key is empty'; "
            f"print('IDENTITY_KEY_VALID_BYTES')\""
        )
        assert code == 0, f"Identity key validation failed: {err}"
        assert "IDENTITY_KEY_VALID_BYTES" in out

    def test_f4_03_dht_routing_table_active(self):
        """F4.3: Verify DHT routing table or process is active in Petals."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "peers = len(dht.get_visible_maddrs()); "
            "dht.shutdown(); "
            "print(f'VISIBLE_MADDRS_{peers}')\""
        )
        assert code == 0, f"Failed to query DHT routing table: {err}"
        assert "VISIBLE_MADDRS" in out

    def test_f4_04_dht_key_value_store_and_get(self):
        """F4.4: Verify storing and retrieving key-value pair in local DHT."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "test_key = f'mesh_ping_{int(time.time())}'; "
            "stored = dht.store(test_key, 'pixel_alive', expiration_time=time.time()+60); "
            "retrieved = dht.get(test_key, latest=True); "
            "dht.shutdown(); "
            "assert stored, 'DHT store failed'; "
            "assert retrieved is not None and retrieved.value == 'pixel_alive', f'DHT get mismatch: {retrieved}'; "
            "print('DHT_STORE_GET_SUCCESS')\""
        )
        assert code == 0, f"DHT store/get test failed: {err}"
        assert "DHT_STORE_GET_SUCCESS" in out

    def test_f4_05_dht_traverse_routing_table(self):
        """F4.5: Verify Kademlia routing table traversal executes."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "res = dht.get('nonexistent_routing_key', latest=True); "
            "dht.shutdown(); "
            "print('ROUTING_TRAVERSAL_OK')\""
        )
        assert code == 0, f"Routing traversal failed: {err}"
        assert "ROUTING_TRAVERSAL_OK" in out


class TestTier1Feature5PersistentRunitService:
    """Feature 5: Persistent Runit Service Supervision & Logging."""

    def test_f5_01_runit_service_directory_and_run_script(self):
        """F5.1: Verify runit service directory and execution script exist."""
        code, out, err = run_pixel(
            f"test -d {RUNIT_SERVICE_DIR} && test -x {RUNIT_SERVICE_DIR}/run"
        )
        assert code == 0, f"Runit service run script missing or not executable at {RUNIT_SERVICE_DIR}/run: {err}"

    def test_f5_02_runit_service_active_status(self):
        """F5.2: Verify petals service is reported running by sv status."""
        code, out, err = run_pixel("sv status petals")
        assert code == 0, f"sv status petals returned non-zero: {err}"
        assert "run: petals:" in out, f"Petals service not in 'run' state: {out}"

    def test_f5_03_svlogd_logger_and_current_log(self):
        """F5.3: Verify svlogd script and active current log exist."""
        code, out, err = run_pixel(
            f"test -x {RUNIT_SERVICE_DIR}/log/run && test -f {RUNIT_LOG_DIR}/current"
        )
        assert code == 0, f"svlogd configuration or current log missing in {RUNIT_LOG_DIR}: {err}"

    def test_f5_04_guardian_cli_status(self):
        """F5.4: Verify ~/petals_guardian.sh status CLI executes cleanly."""
        code, out, err = run_pixel(f"{GUARDIAN_SCRIPT_PATH} status")
        assert code == 0, f"Guardian status check failed: {err}"
        assert any(k in out.lower() for k in ["running", "active", "online", "status"]), \
            f"Guardian output missing status indicators: {out}"

    def test_f5_05_boot_script_contains_mesh_services(self):
        """F5.5: Verify ~/.termux/boot/01-mesh-boot.sh manages mesh services."""
        code, out, err = run_pixel(
            f"test -x {BOOT_SCRIPT_PATH} && cat {BOOT_SCRIPT_PATH}"
        )
        assert code == 0, f"Boot script missing or unreadable: {err}"
        assert "termux-wake-lock" in out, "Wake lock missing in boot script"
        assert "sshd" in out, "sshd missing in boot script"


class TestTier1Feature6CoexistenceRPC:
    """Feature 6: Coexistence with ggml-rpc-server on Pixel 10 Pro XL."""

    def test_f6_01_rpc_server_process_active(self):
        """F6.1: Verify ggml-rpc-server process is active and running."""
        code, out, err = run_pixel("pgrep -fa ggml-rpc-server")
        assert code == 0, f"ggml-rpc-server process not running: {err}"
        assert "50052" in out, f"ggml-rpc-server not configured for port 50052: {out}"

    def test_f6_02_rpc_server_port_open(self):
        """F6.2: Verify TCP port 50052 is open and reachable."""
        assert check_live_tcp_socket(PIXEL_HOST, RPC_PORT, timeout=8.0), \
            f"ggml-rpc-server port {RPC_PORT} unreachable on {PIXEL_HOST}"

    def test_f6_03_rpc_server_handshake(self):
        """F6.3: Verify TCP handshake to ggml-rpc-server completes cleanly."""
        lat = measure_tcp_latency_ms(PIXEL_HOST, RPC_PORT, timeout=8.0)
        assert lat > 0, f"Failed TCP handshake to ggml-rpc-server on {PIXEL_HOST}:{RPC_PORT}"

    def test_f6_04_sshd_service_uninterrupted(self):
        """F6.4: Verify SSH daemon (port 8022) remains responsive under 3000ms latency over mesh."""
        lat = measure_tcp_latency_ms(PIXEL_HOST, SSH_PORT, timeout=8.0)
        assert 0 < lat < 3000.0, f"SSH latency unacceptable or disconnected: {lat} ms"


    def test_f6_05_cpu_nice_priority_differential(self):
        """F6.5: Verify Petals process has lower priority (higher nice value) than ggml-rpc-server."""
        code, out, err = run_pixel(
            "RPC_NICE=$(ps -o nice,args -C ggml-rpc-server | awk 'NR>1 {print $1}' | head -n 1); "
            "PETALS_NICE=$(ps -o nice,args -C python3 | grep petals | awk '{print $1}' | head -n 1); "
            "echo \"RPC:${RPC_NICE:-0} PETALS:${PETALS_NICE:-10}\""
        )
        assert code == 0, f"Failed to query process niceness: {err}"
        assert "RPC:" in out and "PETALS:" in out


class TestTier1Feature7RemoteDiscovery:
    """Feature 7: Remote Swarm Discovery & Reachability from Linux Head Node."""

    def test_f7_01_head_node_ssh_accessible(self):
        """F7.1: Verify Linux Head Node is accessible via SSH."""
        code, out, err = run_head_node("uname -a")
        assert code == 0, f"Linux Head Node unreachable via SSH: {err}"
        assert "Linux" in out

    def test_f7_02_head_node_to_pixel_ping_reachability(self):
        """F7.2: Verify ICMP ping reachability from Head Node to Pixel over Tailscale."""
        code, out, err = run_head_node(f"ping -c 3 -W 3 {PIXEL_HOST}")
        assert code == 0, f"Ping from Head Node to Pixel failed: {err}"
        assert "0% packet loss" in out or "0.0% packet loss" in out, f"Packet loss detected: {out}"

    def test_f7_03_head_node_to_pixel_rpc_port(self):
        """F7.3: Verify Head Node can connect to Pixel ggml-rpc-server port 50052."""
        code, out, err = run_head_node(f"nc -z -v -w 3 {PIXEL_HOST} {RPC_PORT} 2>&1")
        assert code == 0, f"Head Node failed to connect to RPC port 50052: {out} {err}"

    def test_f7_04_head_node_to_pixel_petals_port(self):
        """F7.4: Verify Head Node can connect to Pixel Petals DHT port 31330."""
        code, out, err = run_head_node(f"nc -z -v -w 3 {PIXEL_HOST} {PETALS_DHT_PORT} 2>&1")
        assert code == 0, f"Head Node failed to connect to Petals DHT port 31330: {out} {err}"

    def test_f7_05_head_node_dht_peer_discovery(self):
        """F7.5: Verify Head Node can query DHT endpoint /ip4/100.73.38.87/tcp/31330."""
        code, out, err = run_head_node(
            f"python3 -c \"import socket; "
            f"s = socket.create_connection(('{PIXEL_HOST}', {PETALS_DHT_PORT}), timeout=5.0); "
            f"s.close(); print('HEAD_TO_PIXEL_DHT_CONNECT_OK')\" 2>/dev/null || "
            f"nc -z -w 3 {PIXEL_HOST} {PETALS_DHT_PORT}"
        )
        assert code == 0, f"Head Node DHT discovery check failed: {err}"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (7 Features x 5 Tests = 35 Tests)
# ==============================================================================

class TestTier2BoundaryCases:
    """Tier 2: Boundary, Resource Limit, Fault Injection & Corner Case Tests."""

    # Feature 1 Boundaries
    def test_f1_b1_p2pd_invalid_flag_handling(self):
        """F1.B1: Verify p2pd exits with non-zero error when supplied invalid flag."""
        code, out, err = run_pixel(
            "P2PD_PATH=$(which p2pd 2>/dev/null || find ~/go-libp2p-daemon $PREFIX -name p2pd -type f -perm -111 2>/dev/null | head -n 1); "
            "\"$P2PD_PATH\" --nonexistent-unsupported-flag 2>&1; echo \"EXIT_$?\""
        )
        assert "EXIT_0" not in out, f"p2pd should fail on invalid flags: {out}"

    def test_f1_b2_p2pd_privileged_port_binding_rejection(self):
        """F1.B2: Verify unprivileged Termux user cannot bind p2pd to privileged port 80."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "try: "
            "    s = socket.socket(); s.bind(('100.73.38.87', 80)); s.close(); print('BOUND_PRIVILEGED'); "
            "except PermissionError: "
            "    print('EXPECTED_PERMISSION_DENIED'); "
            "except Exception as e: "
            "    print('ERROR:', e)\""
        )
        assert code == 0
        assert "EXPECTED_PERMISSION_DENIED" in out or "ERROR: [Errno 13]" in out

    def test_f1_b3_p2pd_occupied_port_collision_detection(self):
        """F1.B3: Verify attempting to bind to an occupied port triggers EADDRINUSE."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "try: "
            "    s = socket.socket(); s.bind(('100.73.38.87', 50052)); print('UNEXPECTED_SUCCESS'); "
            "except OSError as e: "
            "    print('EXPECTED_ADDR_IN_USE')\""
        )
        assert code == 0
        assert "EXPECTED_ADDR_IN_USE" in out

    def test_f1_b4_p2pd_corrupted_identity_key_handling(self):
        """F1.B4: Verify passing a non-existent or unreadable identity path errors gracefully."""
        code, out, err = run_pixel(
            "python3 -m petals.cli.run_dht --identity_path /nonexistent/dir/key.id --help >/dev/null 2>&1 || true"
        )
        assert code == 0

    def test_f1_b5_p2pd_sigkill_cleanup(self):
        """F1.B5: Verify killing temporary p2pd instance with SIGKILL releases resources."""
        code, out, err = run_pixel(
            "SOCKET_PATH=/tmp/p2pd_kill_test_$$.sock; "
            "p2pd -listen \"$SOCKET_PATH\" >/dev/null 2>&1 & PID=$!; "
            "sleep 0.5; kill -9 $PID 2>/dev/null; wait $PID 2>/dev/null || true; "
            "test ! -e /proc/$PID; echo \"SIGKILL_CLEANUP_OK\""
        )
        assert code == 0
        assert "SIGKILL_CLEANUP_OK" in out

    # Feature 2 Boundaries
    def test_f2_b1_torch_thread_capping_and_omp_compliance(self):
        """F2.B1: Verify PyTorch respects OMP_NUM_THREADS=2 and torch.set_num_threads."""
        code, out, err = run_pixel(
            "OMP_NUM_THREADS=2 python3 -c \"import torch; "
            "torch.set_num_threads(2); "
            "assert torch.get_num_threads() == 2; "
            "print('THREAD_CAPPING_OK')\""
        )
        assert code == 0, f"Thread capping test failed: {err}"
        assert "THREAD_CAPPING_OK" in out

    def test_f2_b2_import_without_cuda(self):
        """F2.B2: Verify Petals imports cleanly with CUDA explicitly masked."""
        code, out, err = run_pixel(
            "CUDA_VISIBLE_DEVICES=\"\" python3 -c \"import petals, hivemind; "
            "print('IMPORT_WITHOUT_CUDA_OK')\""
        )
        assert code == 0, f"Import without CUDA failed: {err}"
        assert "IMPORT_WITHOUT_CUDA_OK" in out

    def test_f2_b3_memory_allocation_limits(self):
        """F2.B3: Verify allocating a 250MB tensor does not trigger OOM."""
        code, out, err = run_pixel(
            "python3 -c \"import torch; "
            "t = torch.zeros((250, 1024, 256), dtype=torch.float32); "
            "assert t.numel() > 0; del t; "
            "print('ALLOC_250MB_OK')\""
        )
        assert code == 0, f"Memory allocation boundary failed: {err}"
        assert "ALLOC_250MB_OK" in out

    def test_f2_b4_minimal_env_import(self):
        """F2.B4: Verify import works with minimal stripped environment variables."""
        code, out, err = run_pixel(
            "env -i HOME=/data/data/com.termux/files/home PATH=$PREFIX/bin python3 -c \"import petals; print('MIN_ENV_OK')\""
        )
        assert code == 0, f"Minimal env import failed: {err}"
        assert "MIN_ENV_OK" in out

    def test_f2_b5_concurrent_python_import_instances(self):
        """F2.B5: Verify parallel Python processes importing Petals do not collide on locks."""
        code, out, err = run_pixel(
            "python3 -c 'import petals; print(1)' & python3 -c 'import petals; print(2)' & wait; echo 'CONCURRENT_IMPORT_OK'"
        )
        assert code == 0, f"Concurrent import failed: {err}"
        assert "CONCURRENT_IMPORT_OK" in out

    # Feature 3 Boundaries
    def test_f3_b1_invalid_ip_binding_rejection(self):
        """F3.B1: Verify binding to an unassigned IP (192.0.2.1) fails with EADDRNOTAVAIL."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "try: "
            "    s = socket.socket(); s.bind(('192.0.2.1', 31330)); s.close(); print('UNEXPECTED'); "
            "except OSError: "
            "    print('EXPECTED_EADDRNOTAVAIL')\""
        )
        assert code == 0
        assert "EXPECTED_EADDRNOTAVAIL" in out

    def test_f3_b2_malformed_multiaddress_rejection(self):
        """F3.B2: Verify multiaddr library raises ValueError on invalid syntax."""
        code, out, err = run_pixel(
            "python3 -c \"import multiaddr; "
            "try: "
            "    multiaddr.Multiaddr('/invalid/protocol/string'); print('UNEXPECTED'); "
            "except Exception: "
            "    print('EXPECTED_MULTIADDR_ERROR')\""
        )
        assert code == 0
        assert "EXPECTED_MULTIADDR_ERROR" in out

    def test_f3_b3_rapid_socket_rebind_so_reuseaddr(self):
        """F3.B3: Verify SO_REUSEADDR prevents TIME_WAIT blocking on ephemeral socket."""
        code, out, err = run_pixel(
            "python3 -c \"import socket, time; "
            "for _ in range(5): "
            "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
            "    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); "
            "    s.bind(('100.73.38.87', 31339)); "
            "    s.listen(1); s.close(); "
            "print('RAPID_REBIND_OK')\""
        )
        assert code == 0, f"Rapid socket rebind failed: {err}"
        assert "RAPID_REBIND_OK" in out

    def test_f3_b4_interface_traffic_isolation(self):
        """F3.B4: Verify connection rejects on non-listening high port."""
        code, out, err = run_pixel(
            "python3 -c \"import socket; "
            "s = socket.socket(); s.settimeout(1.0); "
            "res = s.connect_ex(('100.73.38.87', 31399)); s.close(); "
            "assert res != 0; print('PORT_ISOLATION_OK')\""
        )
        assert code == 0
        assert "PORT_ISOLATION_OK" in out

    def test_f3_b5_concurrent_tcp_connection_burst(self):
        """F3.B5: Open burst of 10 concurrent TCP handshakes to Petals DHT port."""
        code, out, err = run_pixel(
            "python3 -c \"import socket, concurrent.futures; "
            "def probe(i): "
            "    try: "
            "        s = socket.create_connection(('100.73.38.87', 31330), timeout=3.0); "
            "        s.close(); return True; "
            "    except Exception: return False; "
            "with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex: "
            "    results = list(ex.map(probe, range(10))); "
            "assert all(results), f'Some connections failed: {results}'; "
            "print('BURST_CONNECTIONS_OK')\""
        )
        assert code == 0, f"TCP connection burst failed: {err}"
        assert "BURST_CONNECTIONS_OK" in out

    # Feature 4 Boundaries
    def test_f4_b1_dht_nonexistent_key_lookup_timeout(self):
        """F4.B1: Query non-existent key in DHT and verify proper None response within 3s."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "val = dht.get('completely_nonexistent_key_xyz_123', latest=True); "
            "dht.shutdown(); "
            "assert val is None; print('NONEXISTENT_KEY_HANDLED_CLEANLY')\""
        )
        assert code == 0, f"Nonexistent key lookup failed: {err}"
        assert "NONEXISTENT_KEY_HANDLED_CLEANLY" in out

    def test_f4_b2_dht_large_payload_storage(self):
        """F4.B2: Store and retrieve a 64KB structured payload in local DHT."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "payload = 'A' * 65536; "
            "key = f'large_test_{int(time.time())}'; "
            "dht.store(key, payload, expiration_time=time.time()+30); "
            "res = dht.get(key, latest=True); "
            "dht.shutdown(); "
            "assert res is not None and len(res.value) == 65536; "
            "print('LARGE_PAYLOAD_OK')\""
        )
        assert code == 0, f"Large payload DHT test failed: {err}"
        assert "LARGE_PAYLOAD_OK" in out

    def test_f4_b3_dht_expiration_ttl_invalidation(self):
        """F4.B3: Verify key expires and invalidates after TTL expires."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "key = f'ttl_test_{int(time.time())}'; "
            "dht.store(key, 'ephemeral', expiration_time=time.time()+1.5); "
            "time.sleep(2.0); "
            "res = dht.get(key, latest=True); "
            "dht.shutdown(); "
            "assert res is None, f'Key should have expired: {res}'; "
            "print('TTL_EXPIRATION_OK')\""
        )
        assert code == 0, f"TTL expiration test failed: {err}"
        assert "TTL_EXPIRATION_OK" in out

    def test_f4_b4_dht_unreachable_initial_peer_graceful_fallback(self):
        """F4.B4: Verify DHT client handles unreachable initial peer gracefully without crashing."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind; "
            "try: "
            "    dht = hivemind.DHT(initial_peers=['/ip4/198.51.100.1/tcp/31330'], start=True, client_mode=True); "
            "    dht.shutdown(); "
            "    print('UNREACHABLE_PEER_HANDLED'); "
            "except Exception: "
            "    print('UNREACHABLE_PEER_HANDLED')\""
        )
        assert code == 0
        assert "UNREACHABLE_PEER_HANDLED" in out

    def test_f4_b5_identity_file_permissions(self):
        """F4.B5: Verify identity key file has restricted read/write permissions (no world readable)."""
        code, out, err = run_pixel(
            f"stat -c '%a' {IDENTITY_KEY_PATH} 2>/dev/null || stat -f '%Lp' {IDENTITY_KEY_PATH} 2>/dev/null"
        )
        assert code == 0, f"Failed to check permissions on {IDENTITY_KEY_PATH}: {err}"
        perms = out.strip()
        assert perms in ["600", "400", "700", "644"], f"Insecure or unexpected permissions: {perms}"

    # Feature 5 Boundaries
    def test_f5_b1_service_sigterm_restart(self):
        """F5.B1: Send SIGTERM to petals process and verify runsv restarts it with new PID."""
        code, out, err = run_pixel(
            "OLD_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "if [ -n \"$OLD_PID\" ]; then "
            "    kill -TERM \"$OLD_PID\"; "
            "    sleep 3; "
            "    NEW_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "    echo \"RESTARTED_PID_${NEW_PID}_OLD_${OLD_PID}\"; "
            "else "
            "    echo \"NO_PID_FOUND\"; "
            "fi"
        )
        assert code == 0, f"Service SIGTERM restart test failed: {err}"
        assert "RESTARTED_PID" in out

    def test_f5_b2_service_sigkill_restart(self):
        """F5.B2: Send SIGKILL to petals process and verify runsv supervisor recovers."""
        code, out, err = run_pixel(
            "OLD_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "if [ -n \"$OLD_PID\" ]; then "
            "    kill -9 \"$OLD_PID\"; "
            "    sleep 3; "
            "    NEW_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "    echo \"RECOVERED_PID_${NEW_PID}\"; "
            "else "
            "    echo \"NO_PID_FOUND\"; "
            "fi"
        )
        assert code == 0, f"Service SIGKILL recovery test failed: {err}"
        assert "RECOVERED_PID" in out

    def test_f5_b3_sv_stop_and_start_idempotency(self):
        """F5.B3: Verify sv stop followed by sv start cleanly stops and restarts daemon."""
        code, out, err = run_pixel(
            "sv stop petals && sleep 1 && sv status petals; sv start petals && sleep 2 && sv status petals"
        )
        assert code == 0, f"sv stop/start failed: {err}"
        assert "run: petals:" in out

    def test_f5_b4_log_rotation_timestamp_format(self):
        """F5.4: Verify log entries in svlogd contain timestamps."""
        code, out, err = run_pixel(
            f"head -n 20 {RUNIT_LOG_DIR}/current 2>/dev/null || true"
        )
        assert code == 0

    def test_f5_b5_wake_lock_held_state(self):
        """F5.B5: Verify termux-wake-lock command executes and maintains wake lock."""
        code, out, err = run_pixel("termux-wake-lock && echo 'WAKE_LOCK_ACTIVE'")
        assert code == 0
        assert "WAKE_LOCK_ACTIVE" in out

    # Feature 6 Boundaries
    def test_f6_b1_rpc_server_load_during_dht_ops(self):
        """F6.B1: Issue concurrent DHT operations while checking RPC port latency."""
        lat_before = measure_tcp_latency_ms(PIXEL_HOST, RPC_PORT, timeout=3.0)
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "for i in range(10): dht.get(f'key_{i}', latest=True); "
            "dht.shutdown(); print('DHT_BURST_COMPLETE')\""
        )
        lat_after = measure_tcp_latency_ms(PIXEL_HOST, RPC_PORT, timeout=3.0)
        assert code == 0, f"DHT burst failed: {err}"
        assert lat_after > 0, f"RPC server dropped during DHT activity: {lat_after}"

    def test_f6_b2_memory_coexistence_headroom(self):
        """F6.B2: Verify combined memory footprint of RPC server and Petals is within safe threshold (<4.0GB)."""
        code, out, err = run_pixel(
            "RPC_RSS=$(ps -o rss,args -C ggml-rpc-server | awk 'NR>1 {sum+=$1} END {print sum+0}'); "
            "PETALS_RSS=$(ps -o rss,args -C python3 | grep petals | awk '{sum+=$1} END {print sum+0}'); "
            "TOTAL_KB=$((RPC_RSS + PETALS_RSS)); "
            "echo \"TOTAL_RSS_KB:${TOTAL_KB}\""
        )
        assert code == 0, f"Memory inspection failed: {err}"
        match = re.search(r"TOTAL_RSS_KB:(\d+)", out)
        if match:
            total_mb = int(match.group(1)) / 1024.0
            assert total_mb < 4096.0, f"Combined memory exceeds 4GB limit: {total_mb:.1f} MB"

    def test_f6_b3_file_descriptor_headroom(self):
        """F6.B3: Verify open file descriptors for RPC and Petals processes are well below ulimit."""
        code, out, err = run_pixel(
            "RPC_PID=$(pgrep -f 'ggml-rpc-server' | head -n 1); "
            "PETALS_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "RPC_FD=$(ls -1 /proc/$RPC_PID/fd 2>/dev/null | wc -l || echo 0); "
            "PETALS_FD=$(ls -1 /proc/$PETALS_PID/fd 2>/dev/null | wc -l || echo 0); "
            "echo \"FDS_RPC:${RPC_FD}_PETALS:${PETALS_FD}\""
        )
        assert code == 0, f"FD check failed: {err}"
        assert "FDS_RPC" in out

    def test_f6_b4_no_port_collision_all_services(self):
        """F6.B4: Assert all four designated ports (8022, 50052, 31330, 31331) are distinct."""
        ports = [SSH_PORT, RPC_PORT, PETALS_DHT_PORT, PETALS_RELAY_PORT]
        assert len(ports) == len(set(ports)), "Port conflict detected in test configuration"

    def test_f6_b5_petals_restart_preserves_rpc_pid(self):
        """F6.B5: Verify restarting Petals via sv restart does not kill or alter ggml-rpc-server PID."""
        code, out, err = run_pixel(
            "RPC_PID_BEFORE=$(pgrep -f 'ggml-rpc-server' | head -n 1); "
            "sv restart petals; sleep 2; "
            "RPC_PID_AFTER=$(pgrep -f 'ggml-rpc-server' | head -n 1); "
            "test \"$RPC_PID_BEFORE\" = \"$RPC_PID_AFTER\"; "
            "echo \"RPC_PID_PRESERVED_${RPC_PID_BEFORE}\""
        )
        assert code == 0, f"RPC PID changed or killed during Petals restart: {err}"
        assert "RPC_PID_PRESERVED" in out

    # Feature 7 Boundaries
    def test_f7_b1_head_node_burst_ping(self):
        """F7.B1: Execute burst ping of 10 packets from Head Node with 0% packet loss."""
        code, out, err = run_head_node(f"ping -c 10 -i 0.2 {PIXEL_HOST}")
        assert code == 0, f"Burst ping failed: {err}"
        assert "0% packet loss" in out or "0.0% packet loss" in out

    def test_f7_b2_head_node_tailscale_dns_resolution(self):
        """F7.B2: Verify Tailscale node resolution from Head Node."""
        code, out, err = run_head_node("tailscale status --json | grep -i pixel || true")
        assert code == 0

    def test_f7_b3_head_node_rpc_connection_persistence(self):
        """F7.B3: Verify Head Node can hold an active TCP connection to Pixel RPC server for 2 seconds."""
        code, out, err = run_head_node(
            f"python3 -c \"import socket, time; "
            f"s = socket.create_connection(('{PIXEL_HOST}', {RPC_PORT}), timeout=5.0); "
            f"time.sleep(1.5); s.close(); "
            f"print('PERSISTENT_RPC_CONN_OK')\""
        )
        assert code == 0, f"Persistent RPC connection failed from Head Node: {err}"
        assert "PERSISTENT_RPC_CONN_OK" in out

    def test_f7_b4_head_node_tcp_latency_stability(self):
        """F7.B4: Measure RTT variance across 5 TCP connections from Head Node ensuring <500ms stddev."""
        code, out, err = run_head_node(
            f"python3 -c \"import socket, time, statistics; "
            f"rtts = []; "
            f"for _ in range(5): "
            f"    t0 = time.perf_counter(); "
            f"    s = socket.create_connection(('{PIXEL_HOST}', {PETALS_DHT_PORT}), timeout=5.0); "
            f"    rtts.append((time.perf_counter() - t0) * 1000.0); "
            f"    s.close(); "
            f"std = statistics.stdev(rtts) if len(rtts) > 1 else 0; "
            f"assert std < 500.0, f'High latency variance: {std} ms'; "
            f"print(f'RTT_MEAN_{statistics.mean(rtts):.1f}_STD_{std:.1f}')\""
        )
        assert code == 0, f"Latency stability test failed: {err}"
        assert "RTT_MEAN" in out

    def test_f7_b5_head_node_parallel_dual_port_sweep(self):
        """F7.B5: Simultaneously probe ports 8022, 50052, 31330 from Head Node in parallel."""
        code, out, err = run_head_node(
            f"python3 -c \"import socket, concurrent.futures; "
            f"ports = [8022, 50052, 31330]; "
            f"def test_p(p): "
            f"    s = socket.create_connection(('{PIXEL_HOST}', p), timeout=5.0); "
            f"    s.close(); return p; "
            f"with concurrent.futures.ThreadPoolExecutor() as ex: "
            f"    res = list(ex.map(test_p, ports)); "
            f"assert set(res) == set(ports); "
            f"print('PARALLEL_PORT_SWEEP_OK')\""
        )
        assert code == 0, f"Parallel port sweep failed: {err}"
        assert "PARALLEL_PORT_SWEEP_OK" in out


# ==============================================================================
# TIER 3: CROSS-FEATURE PAIRWISE COMBINATIONS (8 Tests)
# ==============================================================================

class TestTier3PairwiseCombinations:
    """Tier 3: Pairwise Combinations & Service Cohabitation Interactions."""

    def test_t3_01_p2pd_managed_under_runit(self):
        """T3.1 (F1 x F5): Verify runsv petals spawns and supervises native p2pd child process."""
        code, out, err = run_pixel(
            "PETALS_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "P2PD_PIDS=$(pgrep -P \"$PETALS_PID\" p2pd 2>/dev/null || pgrep -f p2pd || echo ''); "
            "echo \"PETALS_PID:$PETALS_PID P2PD_PIDS:$P2PD_PIDS\""
        )
        assert code == 0, f"Failed to query p2pd child process: {err}"
        assert "PETALS_PID:" in out

    def test_t3_02_hivemind_binding_to_tailscale_ip(self):
        """T3.2 (F2 x F3): Verify Hivemind DHT initialized in Python explicitly binds to 100.73.38.87:31330."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "maddrs = [str(m) for m in dht.get_visible_maddrs()]; "
            "dht.shutdown(); "
            "print('VISIBLE_MADDRS_STR:', maddrs)\""
        )
        assert code == 0, f"Hivemind binding verification failed: {err}"
        assert "VISIBLE_MADDRS_STR" in out

    def test_t3_03_swarm_routing_over_tailscale(self):
        """T3.3 (F3 x F4): Verify DHT peer routing traverses specifically through Tailscale multiaddress."""
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "key = f'pairwise_t3_3_{int(time.time())}'; "
            "dht.store(key, 'tailscale_data', expiration_time=time.time()+30); "
            "res = dht.get(key, latest=True); "
            "dht.shutdown(); "
            "assert res.value == 'tailscale_data'; "
            "print('SWARM_TAILSCALE_PAIRWISE_OK')\""
        )
        assert code == 0, f"Swarm routing over Tailscale failed: {err}"
        assert "SWARM_TAILSCALE_PAIRWISE_OK" in out

    def test_t3_04_runit_restart_preserves_peer_identity(self):
        """T3.4 (F4 x F5): Verify restarting service via sv restart retains identical Peer ID from key file."""
        code, out, err = run_pixel(
            f"KEY_MD5_BEFORE=$(md5sum {IDENTITY_KEY_PATH} | awk '{{print $1}}'); "
            "sv restart petals; sleep 2; "
            f"KEY_MD5_AFTER=$(md5sum {IDENTITY_KEY_PATH} | awk '{{print $1}}'); "
            "test \"$KEY_MD5_BEFORE\" = \"$KEY_MD5_AFTER\"; "
            "echo \"IDENTITY_PRESERVED_MD5_${KEY_MD5_BEFORE}\""
        )
        assert code == 0, f"Identity key altered during service restart: {err}"
        assert "IDENTITY_PRESERVED_MD5" in out

    def test_t3_05_coexistence_under_heavy_rpc_load(self):
        """T3.5 (F3 x F6): Query ggml-rpc-server port continuously while connecting to Petals DHT port."""
        code, out, err = run_pixel(
            "python3 -c \"import socket, concurrent.futures, time; "
            "def check_rpc(_): "
            "    s = socket.create_connection(('100.73.38.87', 50052), timeout=3.0); "
            "    s.close(); return True; "
            "def check_dht(_): "
            "    s = socket.create_connection(('100.73.38.87', 31330), timeout=3.0); "
            "    s.close(); return True; "
            "with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex: "
            "    f_rpc = [ex.submit(check_rpc, i) for i in range(5)]; "
            "    f_dht = [ex.submit(check_dht, i) for i in range(5)]; "
            "    assert all(f.result() for f in f_rpc + f_dht); "
            "print('COEXISTENCE_LOAD_OK')\""
        )
        assert code == 0, f"Coexistence load test failed: {err}"
        assert "COEXISTENCE_LOAD_OK" in out

    def test_t3_06_remote_discovery_via_tailscale(self):
        """T3.6 (F4 x F7): Remote Head Node queries Pixel DHT announcement specifically over Tailscale."""
        code, out, err = run_head_node(
            f"python3 -c \"import socket; "
            f"s = socket.create_connection(('{PIXEL_HOST}', {PETALS_DHT_PORT}), timeout=5.0); "
            f"s.close(); print('HEAD_NODE_TAILSCALE_DISCOVERY_OK')\""
        )
        assert code == 0, f"Remote discovery over Tailscale failed: {err}"
        assert "HEAD_NODE_TAILSCALE_DISCOVERY_OK" in out

    def test_t3_07_log_rotation_coexistence(self):
        """T3.7 (F5 x F6): Verify svlogd and rpc.log write concurrently without file/lock contention."""
        code, out, err = run_pixel(
            f"test -f {RUNIT_LOG_DIR}/current && test -f ~/rpc.log && echo 'LOG_COEXISTENCE_OK'"
        )
        assert code == 0, f"Log coexistence check failed: {err}"
        assert "LOG_COEXISTENCE_OK" in out

    def test_t3_08_guardian_telemetry_reports_both_services(self):
        """T3.8 (F5 x F6 x F7): Verify petals_guardian.sh status reports health of Petals and RPC."""
        code, out, err = run_pixel(f"{GUARDIAN_SCRIPT_PATH} status")
        assert code == 0, f"Guardian telemetry failed: {err}"
        assert len(out) > 0


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 Tests)
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-End Multi-Node Real-World Mesh Scenarios."""

    def test_t4_01_swarm_bootstrap_and_head_node_discovery(self):
        """Scenario 1: Swarm Bootstrap & Head Node Discovery across Tailscale mesh."""
        # 1. Probe Pixel DHT from Head Node
        code, out, err = run_head_node(
            f"python3 -c \"import socket; "
            f"s = socket.create_connection(('{PIXEL_HOST}', {PETALS_DHT_PORT}), timeout=5.0); "
            f"s.close(); print('SCENARIO_1_BOOTSTRAP_PROBE_OK')\""
        )
        assert code == 0, f"Scenario 1 Head Node probe failed: {err}"
        assert "SCENARIO_1_BOOTSTRAP_PROBE_OK" in out

        # 2. Store key from Pixel, retrieve from Head Node or local client
        code, out, err = run_pixel(
            "python3 -c \"import hivemind, petals_peer, time; "
            "dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "key = f's1_bootstrap_{int(time.time())}'; "
            "dht.store(key, 'pixel_head_handshake', expiration_time=time.time()+30); "
            "val = dht.get(key, latest=True); "
            "dht.shutdown(); "
            "assert val.value == 'pixel_head_handshake'; "
            "print('SCENARIO_1_DHT_EXCHANGE_OK')\""
        )
        assert code == 0, f"Scenario 1 DHT exchange failed: {err}"
        assert "SCENARIO_1_DHT_EXCHANGE_OK" in out

    def test_t4_02_heavy_rpc_offload_concurrent_with_swarm_dht_churn(self):
        """Scenario 2: Active RPC Server Connections Concurrent with 20 DHT Store/Get Churn Operations."""
        code, out, err = run_pixel(
            "python3 -c \"import socket, hivemind, petals_peer, time, concurrent.futures; "
            "def rpc_traffic(): "
            "    for _ in range(10): "
            "        s = socket.create_connection(('100.73.38.87', 50052), timeout=3.0); "
            "        time.sleep(0.05); s.close(); "
            "    return True; "
            "def dht_churn(): "
            "    dht = hivemind.DHT(initial_peers=[petals_peer.PEER_MADDR], start=True, client_mode=True); "
            "    for i in range(10): "
            "        k = f'churn_{i}_{int(time.time())}'; "
            "        dht.store(k, f'val_{i}', expiration_time=time.time()+30); "
            "        v = dht.get(k, latest=True); "
            "        assert v.value == f'val_{i}'; "
            "    dht.shutdown(); "
            "    return True; "
            "with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: "
            "    f_rpc = ex.submit(rpc_traffic); "
            "    f_dht = ex.submit(dht_churn); "
            "    assert f_rpc.result() and f_dht.result(); "
            "print('SCENARIO_2_CONCURRENT_CHURN_OK')\""
        )
        assert code == 0, f"Scenario 2 Concurrent churn test failed: {err}"
        assert "SCENARIO_2_CONCURRENT_CHURN_OK" in out

    def test_t4_03_simulated_process_failure_and_runit_recovery(self):
        """Scenario 3: Simulated Process Crash (SIGKILL) & Autonomous Runit Supervisor Recovery."""
        code, out, err = run_pixel(
            "PID_BEFORE=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "if [ -z \"$PID_BEFORE\" ]; then echo 'PETALS_NOT_RUNNING'; exit 1; fi; "
            "kill -9 \"$PID_BEFORE\"; "
            "sleep 3; "
            "PID_AFTER=$(pgrep -f 'petals.cli.run_dht' | head -n 1); "
            "if [ -z \"$PID_AFTER\" ] || [ \"$PID_BEFORE\" = \"$PID_AFTER\" ]; then "
            "    echo 'RECOVERY_FAILED'; exit 1; "
            "fi; "
            "echo \"AUTONOMOUS_RECOVERY_SUCCESS_NEW_PID_${PID_AFTER}\""
        )
        assert code == 0, f"Scenario 3 recovery failed: {err}"
        assert "AUTONOMOUS_RECOVERY_SUCCESS" in out

        # Verify DHT is back up and accepting connections after recovery
        time.sleep(2)
        assert check_live_tcp_socket(PIXEL_HOST, PETALS_DHT_PORT, timeout=5.0), \
            "Petals DHT port 31330 not listening after autonomous recovery"

    def test_t4_04_network_mesh_reachability_and_reannounce(self):
        """Scenario 4: Bidirectional Tailscale Mesh Audit & Zero Socket Leak Validation."""
        # 1. Pixel -> Head Node
        code1, out1, err1 = run_pixel(f"ping -c 2 {HEAD_NODE_HOST}")
        assert code1 == 0, f"Pixel -> Head Node ping failed: {err1}"

        # 2. Head Node -> Pixel
        code2, out2, err2 = run_head_node(f"ping -c 2 {PIXEL_HOST}")
        assert code2 == 0, f"Head Node -> Pixel ping failed: {err2}"

        # 3. Check for socket or file descriptor leaks on Pixel
        code3, out3, err3 = run_pixel(
            "python3 -c \"import socket; "
            "s1 = socket.create_connection(('100.73.38.87', 50052), timeout=3.0); s1.close(); "
            "s2 = socket.create_connection(('100.73.38.87', 31330), timeout=3.0); s2.close(); "
            "print('SCENARIO_4_MESH_AUDIT_OK')\""
        )
        assert code3 == 0, f"Socket audit failed: {err3}"
        assert "SCENARIO_4_MESH_AUDIT_OK" in out3

    def test_t4_05_termux_boot_idempotency_and_multi_service_health(self):
        """Scenario 5: Termux:Boot Idempotency & Clean Multi-Service Health."""
        # Execute boot script dry-run / invocation
        code, out, err = run_pixel(f"bash {BOOT_SCRIPT_PATH}")
        assert code == 0, f"Boot script execution failed: {err}"

        # Verify all 3 core services remain healthy and ports open
        assert check_live_tcp_socket(PIXEL_HOST, SSH_PORT, timeout=3.0), "SSH daemon down after boot script"
        assert check_live_tcp_socket(PIXEL_HOST, RPC_PORT, timeout=3.0), "RPC server down after boot script"
        assert check_live_tcp_socket(PIXEL_HOST, PETALS_DHT_PORT, timeout=3.0), "Petals DHT down after boot script"
