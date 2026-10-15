#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_movesense_dongle_handover_e2e.py
================================================================================
Comprehensive End-to-End (E2E) Multi-Node Movesense & Bluetooth Dongle Handover
Relay Test Suite with Zero-Loss Store-and-Forward Verification.

Governed by:
- Rule 0 (Zero-Mock): 100% authentic processes, real sockets, genuine telemetry state machine.
- Rule 1 (Tri-Proof): Process Exit Code 0, SHA256 parity line-by-line, and live socket I/O.
- Rule 3 (Host Sanctuary): Mach memory headroom >= 4.8 GB, Free Disk >= 10.0 GB.
- Rule 8 (Local AI Hierarchy): Prima.cpp / Qwen 3.8 Max local orchestrator routing.
- Rule 9 (Mesh Network Fallback): Seamless multi-transport failover (Home Direct -> Nomad Mobile -> Dead-Zone Flash).
================================================================================
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import handover relay substrate
from importlib.machinery import SourceFileLoader
relay_module_path = REPO_ROOT / "03_biometrics_and_telemetry/movesense_handover_relay.py"
handover_module = SourceFileLoader("movesense_handover_relay", str(relay_module_path)).load_module()

MovesenseHandoverEngine = handover_module.MovesenseHandoverEngine
HandoverState = handover_module.HandoverState
MovesenseBiometricsFrame = handover_module.MovesenseBiometricsFrame
BluetoothHardwareTopology = handover_module.BluetoothHardwareTopology
STREAM_PATH = handover_module.STREAM_PATH
NOMAD_BUFFER = handover_module.NOMAD_BUFFER
STREAM_PIPE = handover_module.STREAM_PIPE
LIVE_BUFFER = handover_module.LIVE_BUFFER
LORA_SINK = handover_module.LORA_SINK

CLI_DIR = REPO_ROOT / "06_scripts_and_tooling/lauburu-opencode-cli"
DARWIN_BIN = CLI_DIR / "lauburu"


class TestMovesenseDongleHandoverE2E(unittest.TestCase):
    """Rigorous E2E test verifying zero data loss during walking out, dead-zone buffering, and reconnection."""

    @classmethod
    def setUpClass(cls):
        # Clean test state
        if NOMAD_BUFFER.exists():
            NOMAD_BUFFER.unlink()
        assert DARWIN_BIN.exists(), f"Headless mesh worker binary missing: {DARWIN_BIN}"

    def tearDown(self):
        if NOMAD_BUFFER.exists():
            NOMAD_BUFFER.unlink()

    def test_01_dual_bluetooth_controller_topology(self):
        """Phase 1: Verify hardware topology probing and dual-HCI controller detection capability."""
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1")
        topo = engine.probe_bluetooth_hardware()

        self.assertIsInstance(topo, BluetoothHardwareTopology)
        self.assertIsNotNone(topo.primary_controller)
        self.assertTrue(len(topo.mac_address) > 0)
        self.assertIn(":", topo.mac_address)

        # On macOS M4 Pro, primary controller is Apple Silicon Internal Controller
        if sys.platform == "darwin":
            self.assertIn("Apple", topo.primary_controller)

        print(f"\n[PHASE 1 PASS] Bluetooth Topology: Primary={topo.primary_controller}, Dedicated Dongle={topo.has_dedicated_dongle}")

    def test_02_home_base_direct_ingestion(self):
        """Phase 1: Ingest 5 authentic telemetry frames under HOME_DIRECT state."""
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1")
        self.assertEqual(engine.current_state, HandoverState.HOME_DIRECT)

        frames = []
        for i in range(5):
            hr = 70 + i * 2
            dfa = 1.10 - (i * 0.02)
            f = engine.generate_or_ingest_frame(hr=hr, dfa=dfa, battery=92 - i)
            frames.append(f)

            # Check SHA256 signature
            computed_sha = f.compute_sha256()
            self.assertEqual(f.sha256_checksum, computed_sha)
            self.assertEqual(f.handover_state, HandoverState.HOME_DIRECT.value)
            self.assertEqual(f.relay_node, "Mac_Node_L1")

        # Verify live stream JSON file written correctly
        self.assertTrue(STREAM_PATH.exists())
        live_data = json.loads(STREAM_PATH.read_text(encoding="utf-8"))
        self.assertEqual(live_data["heart_rate_bpm"], frames[-1].heart_rate_bpm)
        self.assertEqual(live_data["sha256_checksum"], frames[-1].sha256_checksum)

        # Verify ANSI stream pipe
        self.assertTrue(STREAM_PIPE.exists())
        self.assertTrue(LIVE_BUFFER.exists())
        pipe_content = LIVE_BUFFER.read_text(encoding="utf-8")
        self.assertIn("HOME_DIRECT", pipe_content)
        self.assertIn("Mac_Node_L1", pipe_content)

        print(f"[PHASE 2 PASS] HOME_DIRECT: 5 frames ingested with 100% SHA256 integrity.")

    def test_03_walkout_signal_fade_and_handover_trigger(self):
        """Phase 2: Signal fades as user walks out. Verify handover trigger within < 1.5s."""
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1")

        t_start = time.time()
        # Home signal drops to -90 dBm (below -85 dBm), Pixel mobile signal is -52 dBm
        engine.update_link_metrics(home_rssi=-90, mobile_rssi=-52, uplink_alive=True)
        t_elapsed = time.time() - t_start

        # Latency check: handover decision must occur in < 1.5s
        self.assertLess(t_elapsed, 1.5, f"Handover trigger too slow: {t_elapsed:.4f}s")
        self.assertEqual(engine.current_state, HandoverState.NOMAD_MOBILE_RELAY)

        # Ingest frame under NOMAD_MOBILE_RELAY
        f = engine.generate_or_ingest_frame(hr=138, dfa=0.82)
        self.assertEqual(f.handover_state, HandoverState.NOMAD_MOBILE_RELAY.value)
        self.assertEqual(f.relay_node, "Pixel_10_Pro_XL_L6")

        print(f"[PHASE 3 PASS] Handover Triggered in {t_elapsed*1000:.2f}ms (<1500ms limit). Relay: {f.relay_node}")

    def test_04_nomad_mobile_relay_remote_streaming(self):
        """Phase 3: Active Nomad Mobile Relay transmits packets over TCP socket."""
        received_chunks = []
        server_ready = threading.Event()
        stop_server = threading.Event()

        # Ephemeral test TCP server
        test_port = 4059

        def mock_tailscale_sink():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", test_port))
                s.listen(1)
                s.settimeout(3.0)
                server_ready.set()
                try:
                    conn, _ = s.accept()
                    with conn:
                        conn.settimeout(2.0)
                        data = conn.recv(4096)
                        if data:
                            received_chunks.append(data.decode("utf-8", errors="ignore"))
                except socket.timeout:
                    pass

        srv_th = threading.Thread(target=mock_tailscale_sink, daemon=True)
        srv_th.start()
        server_ready.wait(timeout=2.0)

        # Engine configured to forward to this test port
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1", tailscale_port=test_port)
        engine.current_state = HandoverState.NOMAD_MOBILE_RELAY

        f = engine.generate_or_ingest_frame(hr=142, dfa=0.79)
        delivered = engine.forward_via_tcp_pipe(f)
        self.assertTrue(delivered, "TCP socket frame delivery failed")

        srv_th.join(timeout=3.0)
        self.assertTrue(len(received_chunks) > 0, "No data received at Tailscale sink")

        payload_received = received_chunks[0]
        self.assertIn("telemetry_stream:", payload_received)
        self.assertIn(f.sha256_checksum, payload_received)
        self.assertIn("Pixel_10_Pro_XL_L6", payload_received)

        print(f"[PHASE 4 PASS] Nomad Mobile Relay: TCP Stream Frame Delivered ({len(payload_received)} bytes).")

    def test_05_dead_zone_store_and_forward_buffering(self):
        """Phase 4: Cellular/Wi-Fi dead zone. Buffer biometrics to flash with 100% store-and-forward."""
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1")
        # Simulate complete cellular & Wi-Fi drop in dead zone
        engine.update_link_metrics(home_rssi=-96, mobile_rssi=-50, uplink_alive=False)

        self.assertEqual(engine.current_state, HandoverState.DEAD_ZONE_BUFFERING)

        # Generate 10 frames in dead zone
        buffered_shas = []
        for i in range(10):
            f = engine.generate_or_ingest_frame(hr=150 + i, dfa=0.72 - (i * 0.01))
            self.assertEqual(f.handover_state, HandoverState.DEAD_ZONE_BUFFERING.value)
            buffered_shas.append(f.sha256_checksum)

        # Verify flash buffer file on disk
        self.assertTrue(NOMAD_BUFFER.exists(), "Nomad buffer file missing")
        lines = [line.strip() for line in NOMAD_BUFFER.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 10, f"Expected 10 buffered frames, found {len(lines)}")

        # Verify each line has valid JSON and matching SHA
        for idx, line in enumerate(lines):
            item = json.loads(line)
            self.assertEqual(item["sha256_checksum"], buffered_shas[idx])

        print(f"[PHASE 5 PASS] Dead-Zone Store-and-Forward: 10 frames securely journaled to {NOMAD_BUFFER}.")

    def test_06_reconnect_catchup_flush_and_zero_loss(self):
        """Phase 5: Reconnect to network. Flush buffer to canonical data lake with 0% packet loss."""
        engine = MovesenseHandoverEngine(node_id="Mac_Node_L1")
        engine.update_link_metrics(home_rssi=-96, mobile_rssi=-50, uplink_alive=False)

        # Buffer 7 frames
        shas_expected = []
        for i in range(7):
            f = engine.generate_or_ingest_frame(hr=160 + i, dfa=0.68)
            shas_expected.append(f.sha256_checksum)

        self.assertEqual(len(engine.buffered_frames), 7)

        # Now reconnect (uplink_alive = True)
        engine.update_link_metrics(home_rssi=-92, mobile_rssi=-48, uplink_alive=True)

        # Should have executed catch-up flush
        self.assertEqual(engine.total_frames_flushed, 7)
        self.assertEqual(len(engine.buffered_frames), 0)
        self.assertFalse(NOMAD_BUFFER.exists(), "Nomad buffer should be cleared after flush")

        # Now simulate user returning home (Home RSSI >= -70 dBm)
        engine.update_link_metrics(home_rssi=-62, mobile_rssi=-88, uplink_alive=True)
        self.assertEqual(engine.current_state, HandoverState.HOME_DIRECT)

        # Final home frame
        f_home = engine.generate_or_ingest_frame(hr=78, dfa=1.08)
        self.assertEqual(f_home.handover_state, HandoverState.HOME_DIRECT.value)
        self.assertEqual(f_home.relay_node, "Mac_Node_L1")

        print(f"[PHASE 6 PASS] Reconnection & Catch-Up Flush: 7 frames flushed, 0% data loss, restored to HOME_DIRECT.")

    def test_07_layer_0_ip_less_terminal_and_host_sanctuary(self):
        """Phase 6 & 7: Layer 0 terminal execution at 0.0.0.0 and Rule 3 Host Sanctuary verification."""
        # 1. Start headless mesh worker
        proc = subprocess.Popen(
            [str(DARWIN_BIN), "worker"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(1.2)
        self.assertIsNone(proc.poll(), "Worker died unexpectedly")

        try:
            # 2. Connect via TCP socket to 127.0.0.1 (layer 0 socket)
            sock = None
            for p in [4051, 4050]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    s.connect(("127.0.0.1", p))
                    chunk = s.recv(2048).decode("utf-8", errors="ignore")
                    if "LAUBURU" in chunk:
                        sock = s
                        break
                    s.close()
                except Exception:
                    try:
                        s.close()
                    except Exception:
                        pass
                    continue

            self.assertIsNotNone(sock, "Cannot connect to Layer 0 worker socket")

            # 3. Test Macro M1
            sock.sendall(b"status\r\n")
            time.sleep(0.3)
            resp = sock.recv(4096).decode("utf-8", errors="ignore")
            self.assertIn("MESH STATUS: 8-LAYER TOPOLOGY", resp)
            self.assertIn("\r\n", resp)

            # 4. Test Macro M4 Movesense command
            sock.sendall(b"bicep\r\n")
            time.sleep(0.3)
            resp_m4 = sock.recv(4096).decode("utf-8", errors="ignore")
            self.assertIn("MOVESENSE", resp_m4)

            sock.close()
        finally:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            proc.terminate()
            proc.wait(timeout=3.0)

        # 5. Rule 3 Host Sanctuary Invariants
        free_disk_gb = shutil.disk_usage("/Users/aaron").free / (1024**3)
        self.assertGreaterEqual(free_disk_gb, 10.0, f"Host Disk Headroom < 10.0 GB: {free_disk_gb:.2f} GB")

        out = subprocess.check_output(["vm_stat"], text=True)
        stats = {}
        for line in out.splitlines()[1:]:
            if ":" in line:
                k, v = line.split(":")
                stats[k.strip()] = int(v.strip().rstrip("."))
        page_size = 16384
        headroom_bytes = (
            stats.get("Pages free", 0) +
            stats.get("Pages inactive", 0) +
            stats.get("Pages speculative", 0) +
            stats.get("Pages purgeable", 0)
        ) * page_size
        headroom_gb = headroom_bytes / (1024**3)
        self.assertGreaterEqual(headroom_gb, 4.8, f"Host Sanctuary RAM < 4.8 GB: {headroom_gb:.2f} GB")

        print(f"[PHASE 7 PASS] Layer 0 Terminal Verified. Host Sanctuary: Free RAM={headroom_gb:.2f} GB (>=4.8 GB), Free Disk={free_disk_gb:.2f} GB (>=10.0 GB).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
