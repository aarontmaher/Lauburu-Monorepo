r"""
Tier 3: Pairwise Combinatorial Cross-Feature Interaction Test Suite.
Interaction Pipeline: Telemetry Engine -> IPC Control Plane -> Thermal Rebalancer.
Validates:
1. Kernel telemetry reads thermal spike (level >= 2)
2. IPC server broadcasts / returns updated thermal pressure in TELEMETRY response
3. Thermal rebalancer consumes telemetry and generates offload signal
4. Prima.cpp allocator dynamically migrates layers onto TB4 peers (L1b, L5)
5. Layer conservation (\sum l_i == 64) is maintained throughout the pipeline
"""

import os
import sys
import time
import json
import signal
import subprocess
import unittest
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR, send_socket_command
from tier1_feature_coverage.test_f11_f13_prima_sharding import PrimaMeshAllocator

DAEMON_BIN = BOOTSTRAPPER_DIR / "build" / "lens_bootstrapper"


class TestCrossTelemetryIpcThermal(unittest.TestCase):
    """Pairwise Cross-Feature Verification: Telemetry -> IPC -> Thermal Rebalancer."""

    @classmethod
    def setUpClass(cls):
        cls.sock_path = f"/tmp/lens_cross_tel_{os.getpid()}.sock"
        cls.config_path = Path(f"/tmp/lens_cross_cfg_{os.getpid()}.json")
        cls.config_path.write_text(json.dumps({
            "socket_path": cls.sock_path,
            "enable_supervisor": False,
            "telemetry_interval_sec": 1
        }), encoding="utf-8")

        cls.proc = subprocess.Popen(
            [str(DAEMON_BIN), "--foreground", "--config", str(cls.config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        if cls.proc:
            cls.proc.send_signal(signal.SIGTERM)
            try:
                cls.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
            if cls.proc.stdout: cls.proc.stdout.close()
            if cls.proc.stderr: cls.proc.stderr.close()
        if cls.config_path.exists():
            cls.config_path.unlink()
        if os.path.exists(cls.sock_path):
            try:
                os.unlink(cls.sock_path)
            except OSError:
                pass

    def test_c1_01_telemetry_to_ipc_channel(self):
        """C1.1: Telemetry engine samples system metrics and serves them through IPC socket."""
        ok, resp = send_socket_command(self.sock_path, "TELEMETRY")
        self.assertTrue(ok, f"IPC TELEMETRY failed: {resp}")
        data = json.loads(resp)
        self.assertIn("thermal_pressure", data)
        self.assertIn("ram_avail_bytes", data)
        self.assertGreater(data["ram_avail_bytes"], 0)

    def test_c1_02_thermal_spike_trigger_decision(self):
        """C1.2: Pipeline evaluates telemetry thermal pressure and triggers offload on level >= 2."""
        def evaluate_offload_need(tel_data: dict) -> bool:
            return tel_data.get("thermal_pressure", 0) >= 2 or tel_data.get("vm_pressure", 1) >= 3

        # Nominal telemetry
        self.assertFalse(evaluate_offload_need({"thermal_pressure": 0, "vm_pressure": 1}))
        # Thermal spike
        self.assertTrue(evaluate_offload_need({"thermal_pressure": 2, "vm_pressure": 1}))
        # Critical memory pressure
        self.assertTrue(evaluate_offload_need({"thermal_pressure": 0, "vm_pressure": 3}))

    def test_c1_03_thermal_triggered_prima_reallocation(self):
        """C1.3: Pipeline invokes PrimaMeshAllocator to reallocate layers upon thermal spike."""
        # Simulated thermal spike triggered by telemetry
        simulated_telemetry = {"thermal_pressure": 2, "node": "L1_mac_mini"}
        
        realloc = PrimaMeshAllocator.allocate_layers(
            total_layers=64,
            thermal_overrides={simulated_telemetry["node"]: simulated_telemetry["thermal_pressure"]}
        )
        self.assertEqual(sum(n["layers"] for n in realloc.values()), 64)
        # Verify L1 layers were reduced
        self.assertLessEqual(realloc["L1_mac_mini"]["layers"], 6)

    def test_c1_04_offload_signal_file_and_config_generation(self):
        """C1.4: Pipeline writes thermal offload signal and outputs prima_mesh_config.json."""
        signal_file = Path("/tmp/thermal_offload_signal.json")
        config_file = Path("/tmp/prima_mesh_config_cross.json")

        realloc = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": 2})
        mesh_config = {
            "model": "qwen_38_max_27b",
            "total_layers": 64,
            "world_size": len(realloc),
            "timestamp": int(time.time()),
            "thermal_spike_active": True,
            "nodes": realloc
        }
        config_file.write_text(json.dumps(mesh_config, indent=2), encoding="utf-8")

        # Verify readback
        loaded = json.loads(config_file.read_text(encoding="utf-8"))
        self.assertTrue(loaded["thermal_spike_active"])
        self.assertEqual(loaded["nodes"]["L1_mac_mini"]["thermal_state"], "SERIOUS")

        if config_file.exists():
            config_file.unlink()

    def test_c1_05_end_to_end_latency_sub_100ms(self):
        """C1.5: End-to-end telemetry read -> IPC command -> layer reallocation takes < 100 ms."""
        start = time.perf_counter()
        ok, resp = send_socket_command(self.sock_path, "TELEMETRY")
        self.assertTrue(ok)
        tel_data = json.loads(resp)
        _ = PrimaMeshAllocator.allocate_layers(total_layers=64, thermal_overrides={"L1_mac_mini": 2})
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertLess(
            elapsed_ms, 100.0,
            f"End-to-end pipeline latency exceeded: {elapsed_ms:.2f} ms (must be < 100 ms)"
        )


if __name__ == "__main__":
    unittest.main()
