"""
00_core_infrastructure/lens_bootstrapper/tests/test_prima_mesh_orchestrator.py
=============================================================================
Comprehensive Unit and Integration Test Suite for Milestone 3:
- Feature F11: Prima.cpp Mesh Sharding Allocator (Dynamic 7-device allocation & conservation)
- Feature F12: Prima.cpp PRP Parameter Generator (ZeroMQ Piped-Ring Parallelism CLI flags)
- Feature F13: Sub-100ms Thermal Spike Detection, Evacuation & JSON Config Emission

Run via:
    python3 -m unittest -v 00_core_infrastructure/lens_bootstrapper/tests/test_prima_mesh_orchestrator.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict

# Ensure repository root and orchestrator directory are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ORCHESTRATOR_DIR = REPO_ROOT / "00_core_infrastructure" / "lens_bootstrapper" / "orchestrator"
if str(ORCHESTRATOR_DIR) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_DIR))

from prima_mesh_orchestrator import (
    PrimaMeshOrchestrator,
    PrimaMeshAllocator,
    MeshNodeProfile,
)
from thermal_rebalancer import ThermalRebalancer


class TestFeatureF11MeshShardingAllocator(unittest.TestCase):
    """Unit and edge-case tests for Feature F11: Dynamic Layer Calculation Engine."""

    def setUp(self):
        self.orchestrator = PrimaMeshOrchestrator()

    def test_layer_conservation_64_layers(self):
        """F11.1: Verify strict layer conservation for 64-layer models (sum(l_i) == 64)."""
        alloc = self.orchestrator.allocate_layers(total_layers=64)
        total = sum(n["layers"] for n in alloc.values())
        self.assertEqual(total, 64, f"Layer conservation failed: sum={total}, expected 64")

    def test_layer_conservation_80_layers(self):
        """F11.2: Verify strict layer conservation for 80-layer models (70B frontier model)."""
        alloc = self.orchestrator.allocate_layers(total_layers=80)
        total = sum(n["layers"] for n in alloc.values())
        self.assertEqual(total, 80, f"Layer conservation failed: sum={total}, expected 80")

    def test_layer_conservation_various_sizes(self):
        """F11.3: Verify layer conservation across various standard LLM architectures."""
        for total_layers in [16, 28, 32, 40, 64, 80, 128]:
            alloc = self.orchestrator.allocate_layers(total_layers=total_layers)
            total = sum(n["layers"] for n in alloc.values())
            self.assertEqual(total, total_layers, f"Failed conservation for total={total_layers}")

    def test_seven_physical_mesh_devices_present(self):
        """F11.4: Verify all 7 physical mesh devices from Rule 0 Hardware Matrix are mapped."""
        alloc = self.orchestrator.allocate_layers(total_layers=64)
        expected_nodes = {
            "L1_mac_mini",
            "L1b_mac_mini_m2",
            "L5_mac_air_m4",
            "L2_macbook_intel",
            "L3_linux_amd",
            "L6_pixel_10",
            "L7_galaxy_s20",
        }
        self.assertEqual(set(alloc.keys()), expected_nodes)
        self.assertEqual(len(alloc), 7)

    def test_node_metadata_fields_and_types(self):
        """F11.5: Verify every node carries rank, ip, layers, vram_mb, and thermal_state."""
        alloc = self.orchestrator.allocate_layers(total_layers=64)
        ranks = set()
        for name, data in alloc.items():
            self.assertIn("rank", data)
            self.assertIn("ip", data)
            self.assertIn("layers", data)
            self.assertIn("vram_mb", data)
            self.assertIn("thermal_state", data)
            self.assertIsInstance(data["rank"], int)
            self.assertIsInstance(data["layers"], int)
            self.assertGreaterEqual(data["layers"], 0)
            self.assertGreater(data["vram_mb"], 0)
            self.assertEqual(data["thermal_state"], "NOMINAL")
            ranks.add(data["rank"])
        # Ranks must span 0 through 6
        self.assertEqual(ranks, set(range(7)))

    def test_thunderbolt_ring_density_preference(self):
        """F11.6: Verify Thunderbolt 40Gbps DMA nodes (L1, L1b, L5) absorb > 50% of layers."""
        alloc = self.orchestrator.allocate_layers(total_layers=64)
        tb_layers = (
            alloc["L1_mac_mini"]["layers"]
            + alloc["L1b_mac_mini_m2"]["layers"]
            + alloc["L5_mac_air_m4"]["layers"]
        )
        peripheral_layers = sum(
            alloc[n]["layers"]
            for n in ["L2_macbook_intel", "L3_linux_amd", "L6_pixel_10", "L7_galaxy_s20"]
        )
        self.assertGreater(
            tb_layers,
            peripheral_layers,
            f"TB4 ring density violated: TB4={tb_layers}, Peripherals={peripheral_layers}",
        )

    def test_non_negative_layer_counts(self):
        """F11.7: Verify no node receives negative layer count."""
        alloc = self.orchestrator.allocate_layers(total_layers=64)
        for name, data in alloc.items():
            self.assertGreaterEqual(data["layers"], 0)

    def test_invalid_total_layers_raises_error(self):
        """F11.8: Verify non-positive total_layers raises ValueError."""
        with self.assertRaises(ValueError):
            self.orchestrator.allocate_layers(total_layers=0)
        with self.assertRaises(ValueError):
            self.orchestrator.allocate_layers(total_layers=-10)

    def test_compatibility_alias_prima_mesh_allocator(self):
        """F11.9: Verify PrimaMeshAllocator alias functions identically."""
        alloc = PrimaMeshAllocator.allocate_layers(total_layers=64)
        self.assertEqual(sum(n["layers"] for n in alloc.values()), 64)


class TestFeatureF12PRPParameterGenerator(unittest.TestCase):
    """Unit and integration tests for Feature F12: Upstream Prima.cpp ZeroMQ PRP Flags."""

    def setUp(self):
        self.orchestrator = PrimaMeshOrchestrator()
        self.alloc = self.orchestrator.allocate_layers(total_layers=64)

    def test_prp_cli_args_contain_all_mandatory_flags(self):
        """F12.1: Verify generated CLI arguments contain all ZeroMQ PRP flags."""
        args = self.orchestrator.generate_prp_cli_args("L1_mac_mini", self.alloc)
        mandatory_flags = [
            "--world",
            "--rank",
            "--master",
            "--next",
            "--data-port",
            "--signal-port",
            "--gpu-mem",
            "--gpu-layers",
            "--prefetch",
        ]
        for flag in mandatory_flags:
            self.assertIn(flag, args, f"Mandatory PRP flag '{flag}' missing from CLI args")

    def test_rank_zero_master_invariant(self):
        """F12.2: Verify Rank 0 is master and --master IP matches rank 0 node IP."""
        args_l1 = self.orchestrator.generate_prp_cli_args("L1_mac_mini", self.alloc)
        rank_idx = args_l1.index("--rank") + 1
        self.assertEqual(args_l1[rank_idx], "0")

        master_idx = args_l1.index("--master") + 1
        self.assertEqual(args_l1[master_idx], self.alloc["L1_mac_mini"]["ip"])

    def test_piped_ring_topology_closure(self):
        """F12.3: Verify ring closure: Node i -> Node (i+1) mod N forming closed circular ring."""
        world_size = len(self.alloc)
        # Check that rank 0 points to rank 1
        args_0 = self.orchestrator.generate_prp_cli_args("L1_mac_mini", self.alloc)
        next_idx_0 = args_0.index("--next") + 1
        self.assertEqual(args_0[next_idx_0], self.alloc["L1b_mac_mini_m2"]["ip"])

        # Check that last node (rank 6) points back to rank 0
        args_6 = self.orchestrator.generate_prp_cli_args("L7_galaxy_s20", self.alloc)
        next_idx_6 = args_6.index("--next") + 1
        self.assertEqual(args_6[next_idx_6], self.alloc["L1_mac_mini"]["ip"])

    def test_custom_data_and_signal_ports(self):
        """F12.4: Verify custom data-port and signal-port configurations."""
        args = self.orchestrator.generate_prp_cli_args(
            "L1b_mac_mini_m2", self.alloc, data_port=9050, signal_port=10050
        )
        self.assertEqual(args[args.index("--data-port") + 1], "9050")
        self.assertEqual(args[args.index("--signal-port") + 1], "10050")

    def test_prefetch_toggle(self):
        """F12.5: Verify prefetch flag can be toggled."""
        args_with = self.orchestrator.generate_prp_cli_args("L1_mac_mini", self.alloc, prefetch=True)
        self.assertIn("--prefetch", args_with)

        args_without = self.orchestrator.generate_prp_cli_args("L1_mac_mini", self.alloc, prefetch=False)
        self.assertNotIn("--prefetch", args_without)

    def test_generate_all_prp_cli_args(self):
        """F12.6: Verify batch generation of PRP arguments for all 7 devices."""
        all_args = self.orchestrator.generate_all_prp_cli_args(self.alloc)
        self.assertEqual(len(all_args), 7)
        for name in self.alloc:
            self.assertIn(name, all_args)
            self.assertIn("--world", all_args[name])

    def test_generate_prp_command_line(self):
        """F12.7: Verify command-line string formatting for llama-cli execution."""
        cmd = self.orchestrator.generate_prp_command_line(
            "L1_mac_mini",
            self.alloc,
            model_path="download/qwen_38_max_27b.gguf",
            binary_path="/Users/aaron/prima.cpp/build/bin/llama-cli",
        )
        self.assertTrue(cmd.startswith("/Users/aaron/prima.cpp/build/bin/llama-cli -m download/qwen_38_max_27b.gguf"))
        self.assertIn("--world 7", cmd)
        self.assertIn("--rank 0", cmd)
        self.assertIn("--master 169.254.186.211", cmd)


class TestFeatureF13ThermalRebalancer(unittest.TestCase):
    """Unit, integration and timing tests for Feature F13 & Acceptance Criterion 4."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "prima_mesh_config.json"
        self.signal_path = Path(self.temp_dir.name) / "thermal_offload_signal.json"
        self.rebalancer = ThermalRebalancer(
            config_path=self.config_path,
            signal_path=self.signal_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_thermal_spike_reallocation_conserves_total_layers(self):
        """F13.1: Verify total layers remain strictly conserved (64) during thermal spike."""
        config_data, latency_ms = self.rebalancer.rebalance_thermal_spike(
            node_name="L1_mac_mini", thermal_level=2, total_layers=64
        )
        total = sum(n["layers"] for n in config_data["nodes"].values())
        self.assertEqual(total, 64)
        self.assertTrue(config_data["thermal_spike_active"])

    def test_evacuation_away_from_throttled_l1(self):
        """F13.2: Verify throttled L1 node is evacuated down to <= 4 layers upon thermal spike."""
        nominal_alloc = self.rebalancer.orchestrator.allocate_layers(total_layers=64)
        nominal_l1 = nominal_alloc["L1_mac_mini"]["layers"]

        config_data, _ = self.rebalancer.rebalance_thermal_spike(
            node_name="L1_mac_mini", thermal_level=2, total_layers=64
        )
        hot_l1 = config_data["nodes"]["L1_mac_mini"]["layers"]

        self.assertLess(hot_l1, nominal_l1, f"L1 did not evacuate: hot={hot_l1}, nominal={nominal_l1}")
        self.assertLessEqual(hot_l1, 4, f"L1 exceeded 4 layer evacuation ceiling: got {hot_l1}")
        self.assertEqual(config_data["nodes"]["L1_mac_mini"]["thermal_state"], "SERIOUS")

    def test_thunderbolt_peers_absorb_evacuated_layers(self):
        """F13.3: Verify healthy Thunderbolt 4 peers (L1b and L5) absorb evacuated layers."""
        nominal_alloc = self.rebalancer.orchestrator.allocate_layers(total_layers=64)
        config_data, _ = self.rebalancer.rebalance_thermal_spike(
            node_name="L1_mac_mini", thermal_level=2, total_layers=64
        )

        l1b_gain = config_data["nodes"]["L1b_mac_mini_m2"]["layers"] - nominal_alloc["L1b_mac_mini_m2"]["layers"]
        l5_gain = config_data["nodes"]["L5_mac_air_m4"]["layers"] - nominal_alloc["L5_mac_air_m4"]["layers"]

        self.assertGreater(
            l1b_gain + l5_gain, 0, "Thunderbolt peers must absorb layers evacuated from L1"
        )
        self.assertGreaterEqual(l1b_gain, 0)
        self.assertGreaterEqual(l5_gain, 0)

    def test_sub_100ms_rebalance_latency(self):
        """F13.4: Empirically verify thermal spike rebalance completes in < 100 ms (Acceptance Criterion 4)."""
        latencies = []
        for _ in range(5):
            _, latency_ms = self.rebalancer.rebalance_thermal_spike(
                node_name="L1_mac_mini", thermal_level=2, total_layers=64, write_config=True
            )
            latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        self.assertLess(
            max_latency,
            100.0,
            f"Thermal adaptation latency exceeded: max={max_latency:.2f} ms (must be < 100 ms)",
        )
        self.assertLess(
            avg_latency,
            50.0,
            f"Average adaptation latency excessive: avg={avg_latency:.2f} ms",
        )

    def test_config_json_written_and_schema_validated(self):
        """F13.5: Verify emitted prima_mesh_config.json file matches Interface Contract 3."""
        self.rebalancer.rebalance_thermal_spike(
            node_name="L1_mac_mini", thermal_level=2, total_layers=64, write_config=True
        )
        self.assertTrue(self.config_path.exists())

        raw_json = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertTrue(self.rebalancer.validate_config_schema(raw_json))
        self.assertEqual(raw_json["model"], "qwen_38_max_27b")
        self.assertEqual(raw_json["total_layers"], 64)
        self.assertEqual(raw_json["world_size"], 7)
        self.assertTrue(raw_json["thermal_spike_active"])
        self.assertEqual(raw_json["nodes"]["L1_mac_mini"]["thermal_state"], "SERIOUS")
        self.assertLessEqual(raw_json["nodes"]["L1_mac_mini"]["layers"], 4)

    def test_signal_file_detection_and_automatic_rebalance(self):
        """F13.6: Verify /tmp/thermal_offload_signal.json triggers automatic check_and_rebalance."""
        self.rebalancer.write_thermal_signal(
            thermal_level=2, thermal_state="SERIOUS", trigger_offload=True
        )
        is_spike, details = self.rebalancer.detect_thermal_spike()
        self.assertTrue(is_spike)
        self.assertIsNotNone(details)

        result = self.rebalancer.check_and_rebalance(total_layers=64)
        self.assertIsNotNone(result)
        config_data, latency_ms = result
        self.assertTrue(config_data["thermal_spike_active"])
        self.assertLess(latency_ms, 100.0)

        # Cleanup signal and test clearing
        self.rebalancer.clear_thermal_signal()
        is_spike_after, _ = self.rebalancer.detect_thermal_spike()
        self.assertFalse(is_spike_after)

    def test_restore_nominal_distribution(self):
        """F13.7: Verify restore_nominal restores original layers and marks thermal_spike_active=False."""
        # First trigger spike
        self.rebalancer.rebalance_thermal_spike("L1_mac_mini", 2, 64)
        # Then restore
        config_data, latency_ms = self.rebalancer.restore_nominal(total_layers=64)
        self.assertFalse(config_data["thermal_spike_active"])
        self.assertGreater(config_data["nodes"]["L1_mac_mini"]["layers"], 4)
        self.assertEqual(config_data["nodes"]["L1_mac_mini"]["thermal_state"], "NOMINAL")
        self.assertEqual(sum(n["layers"] for n in config_data["nodes"].values()), 64)

    def test_schema_validator_catches_invalid_payloads(self):
        """F13.8: Verify validate_config_schema rejects malformed configurations."""
        valid_config, _ = self.rebalancer.restore_nominal(total_layers=64, write_config=False)
        self.assertTrue(self.rebalancer.validate_config_schema(valid_config))

        # Missing key
        bad_config = dict(valid_config)
        del bad_config["model"]
        with self.assertRaises(ValueError):
            self.rebalancer.validate_config_schema(bad_config)

        # Non-conserved layer count
        bad_layers_config = json.loads(json.dumps(valid_config))
        bad_layers_config["nodes"]["L1_mac_mini"]["layers"] += 5
        with self.assertRaises(ValueError):
            self.rebalancer.validate_config_schema(bad_layers_config)

        # Invalid thermal state string
        bad_state_config = json.loads(json.dumps(valid_config))
        bad_state_config["nodes"]["L1_mac_mini"]["thermal_state"] = "ON_FIRE"
        with self.assertRaises(ValueError):
            self.rebalancer.validate_config_schema(bad_state_config)


if __name__ == "__main__":
    unittest.main()
