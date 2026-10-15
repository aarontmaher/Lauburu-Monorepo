"""
00_core_infrastructure/lens_bootstrapper/orchestrator/thermal_rebalancer.py
===========================================================================
Milestone 3 (Feature F13): Thermal Spike Detection, Peer Evacuation & Dynamic Rebalancer.

Provides sub-100ms detection of thermal pressure spikes (via /tmp/thermal_offload_signal.json
or Darwin <notify.h>), dynamic layer evacuation away from throttled nodes (evacuating L1
down to <= 4 layers) onto Thunderbolt 4 peers (L1b and L5), and emission of validated
configuration JSON adhering strictly to Interface Contract 3 (prima_mesh_config.json).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("ThermalRebalancer")

# Ensure module can resolve sibling imports
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .prima_mesh_orchestrator import PrimaMeshOrchestrator
except ImportError:
    from prima_mesh_orchestrator import PrimaMeshOrchestrator

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "prima_mesh_config.json"
DEFAULT_SIGNAL_PATH = Path("/tmp/thermal_offload_signal.json")


class ThermalRebalancer:
    """
    Sub-100ms Thermal Spike Rebalancing Engine.
    
    Detects hardware thermal spikes and shifts layer boundaries away from
    hot hosts to prevent thermal throttling and ACIO2 panics.
    """

    def __init__(
        self,
        config_path: Optional[Path | str] = None,
        signal_path: Optional[Path | str] = None,
        orchestrator: Optional[PrimaMeshOrchestrator] = None,
    ) -> None:
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH)
        self.signal_path = Path(signal_path or DEFAULT_SIGNAL_PATH)
        self.orchestrator = orchestrator or PrimaMeshOrchestrator()
        self.last_rebalance_latency_ms: float = 0.0

    def read_thermal_signal(self) -> Optional[Dict[str, Any]]:
        """
        Reads and parses the thermal offload signal from /tmp/thermal_offload_signal.json.
        Returns parsed dict or None if file does not exist or is invalid.
        """
        if not self.signal_path.exists():
            return None

        try:
            raw = self.signal_path.read_text(encoding="utf-8").strip()
            if not raw:
                return None
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read thermal signal file: {e}")
            return None

    def detect_thermal_spike(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detects whether an active thermal spike is present.
        Checks:
        1. /tmp/thermal_offload_signal.json (trigger_offload == True or thermal_level >= 2)
        2. Darwin notify.h state (if available on macOS)
        
        Returns (is_spike_active, signal_details)
        """
        signal_data = self.read_thermal_signal()
        if signal_data is not None:
            trigger = signal_data.get("trigger_offload", False)
            level = signal_data.get("thermal_level", 0)
            if trigger or level >= 2:
                return True, signal_data

        # Fallback to Darwin notify.h check on macOS
        if sys.platform == "darwin":
            try:
                import ctypes
                c_notify = ctypes.CDLL(None)
                token = ctypes.c_int()
                status = c_notify.notify_register_check(
                    b"com.apple.system.thermalpressurelevel", ctypes.byref(token)
                )
                if status == 0:
                    state = ctypes.c_uint64()
                    c_notify.notify_get_state(token, ctypes.byref(state))
                    c_notify.notify_cancel(token)
                    if state.value >= 2:
                        return True, {
                            "thermal_level": int(state.value),
                            "thermal_state": "SERIOUS" if state.value == 2 else "CRITICAL",
                            "trigger_offload": True,
                            "source": "darwin_notify_h",
                        }
            except Exception:
                pass

        return False, None

    def rebalance_thermal_spike(
        self,
        node_name: str = "L1_mac_mini",
        thermal_level: int = 2,
        total_layers: int = 64,
        model: str = "qwen_38_max_27b",
        trigger: str = "SIMULATED_THERMAL_SPIKE",
        write_config: bool = True,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Executes thermal spike layer evacuation and updates prima_mesh_config.json.
        
        Sub-100ms execution:
        - Evacuates throttled node (L1 down to <= 4 layers)
        - Transfers evacuated layers onto Thunderbolt 4 peers (L1b & L5)
        - Preserves strict layer conservation: sum(layers) == total_layers
        - Emits validated configuration JSON adhering to Interface Contract 3
        
        Returns:
            (config_dict, elapsed_ms)
        """
        t0 = time.perf_counter()

        # 1. Recalculate 7-node layer allocation with thermal override
        allocations = self.orchestrator.allocate_layers(
            total_layers=total_layers,
            thermal_overrides={node_name: thermal_level},
        )

        # 2. Verify layer conservation
        current_sum = sum(node["layers"] for node in allocations.values())
        if current_sum != total_layers:
            raise ValueError(
                f"Layer conservation violated during thermal spike: sum={current_sum}, expected {total_layers}"
            )

        # 3. Verify L1 evacuation invariant
        if node_name == "L1_mac_mini" and thermal_level >= 2:
            l1_layers = allocations["L1_mac_mini"]["layers"]
            if l1_layers > 4:
                raise ValueError(
                    f"Thermal evacuation invariant violated: L1 has {l1_layers} layers, must be <= 4"
                )

        # 4. Assemble configuration payload per Interface Contract 3
        config_data = self.orchestrator.generate_mesh_config(
            allocations=allocations,
            model=model,
            total_layers=total_layers,
            thermal_spike_active=True,
            trigger=trigger,
            timestamp=int(time.time()),
        )

        # 5. Validate schema
        self.validate_config_schema(config_data)

        # 6. Write configuration file atomically if requested
        if write_config:
            self.write_config_file(config_data)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.last_rebalance_latency_ms = elapsed_ms

        logger.info(
            f"Thermal spike rebalance completed in {elapsed_ms:.2f} ms: "
            f"L1 evacuated to {allocations.get('L1_mac_mini', {}).get('layers')} layers"
        )
        return config_data, elapsed_ms

    def restore_nominal(
        self,
        total_layers: int = 64,
        model: str = "qwen_38_max_27b",
        write_config: bool = True,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Restores nominal sharding distribution once thermal spike clears.
        """
        t0 = time.perf_counter()

        allocations = self.orchestrator.allocate_layers(
            total_layers=total_layers,
            thermal_overrides={"L1_mac_mini": 0},
        )

        config_data = self.orchestrator.generate_mesh_config(
            allocations=allocations,
            model=model,
            total_layers=total_layers,
            thermal_spike_active=False,
            timestamp=int(time.time()),
        )

        self.validate_config_schema(config_data)

        if write_config:
            self.write_config_file(config_data)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.last_rebalance_latency_ms = elapsed_ms
        return config_data, elapsed_ms

    def check_and_rebalance(
        self,
        total_layers: int = 64,
        model: str = "qwen_38_max_27b",
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Polls for thermal spike signal and executes rebalancing if triggered.
        Returns (config_data, latency_ms) if rebalance was executed, or None.
        """
        spike_active, details = self.detect_thermal_spike()
        if spike_active:
            node = details.get("node", "L1_mac_mini") if details else "L1_mac_mini"
            level = details.get("thermal_level", 2) if details else 2
            trigger = details.get("trigger", "THERMAL_SPIKE_OFFLOAD") if details else "THERMAL_SPIKE_OFFLOAD"
            return self.rebalance_thermal_spike(
                node_name=node,
                thermal_level=level,
                total_layers=total_layers,
                model=model,
                trigger=trigger,
                write_config=True,
            )
        return None

    def write_config_file(self, config_data: Dict[str, Any], target_path: Optional[Path | str] = None) -> None:
        """
        Safely and atomically writes configuration JSON to disk.
        """
        out_path = Path(target_path or self.config_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temporary file
        temp_dir = out_path.parent
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump(config_data, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name

        os.replace(temp_name, out_path)

    @staticmethod
    def validate_config_schema(config_data: Dict[str, Any]) -> bool:
        """
        Validates configuration dictionary against Interface Contract 3.
        Raises ValueError if invalid, returns True if valid.
        """
        required_top_keys = ["model", "total_layers", "world_size", "timestamp", "thermal_spike_active", "nodes"]
        for key in required_top_keys:
            if key not in config_data:
                raise ValueError(f"Missing required top-level key: '{key}'")

        if not isinstance(config_data["model"], str) or not config_data["model"]:
            raise ValueError("Field 'model' must be a non-empty string")

        if not isinstance(config_data["total_layers"], int) or config_data["total_layers"] <= 0:
            raise ValueError("Field 'total_layers' must be a positive integer")

        if not isinstance(config_data["world_size"], int) or config_data["world_size"] <= 0:
            raise ValueError("Field 'world_size' must be a positive integer")

        if not isinstance(config_data["thermal_spike_active"], bool):
            raise ValueError("Field 'thermal_spike_active' must be a boolean")

        nodes = config_data.get("nodes", {})
        if not isinstance(nodes, dict) or len(nodes) != config_data["world_size"]:
            raise ValueError(f"Nodes count ({len(nodes)}) does not match world_size ({config_data['world_size']})")

        total_allocated = 0
        required_node_keys = ["rank", "ip", "layers", "vram_mb", "thermal_state"]

        for name, node in nodes.items():
            if not isinstance(node, dict):
                raise ValueError(f"Node '{name}' must be a dictionary")
            for nk in required_node_keys:
                if nk not in node:
                    raise ValueError(f"Node '{name}' missing required key: '{nk}'")

            if not isinstance(node["rank"], int) or node["rank"] < 0:
                raise ValueError(f"Node '{name}' rank must be non-negative integer")

            if not isinstance(node["ip"], str) or not node["ip"]:
                raise ValueError(f"Node '{name}' ip must be valid string")

            if not isinstance(node["layers"], int) or node["layers"] < 0:
                raise ValueError(f"Node '{name}' layers must be non-negative integer")

            if not isinstance(node["vram_mb"], int) or node["vram_mb"] <= 0:
                raise ValueError(f"Node '{name}' vram_mb must be positive integer")

            if node["thermal_state"] not in {"NOMINAL", "MODERATE", "SERIOUS", "CRITICAL"}:
                raise ValueError(f"Node '{name}' invalid thermal_state: '{node['thermal_state']}'")

            total_allocated += node["layers"]

        if total_allocated != config_data["total_layers"]:
            raise ValueError(
                f"Total allocated layers ({total_allocated}) does not match total_layers ({config_data['total_layers']})"
            )

        return True

    def write_thermal_signal(
        self,
        thermal_level: int = 2,
        thermal_state: str = "SERIOUS",
        trigger_offload: bool = True,
        node: str = "L1_mac_mini",
    ) -> Path:
        """
        Helper method to create /tmp/thermal_offload_signal.json for testing or triggering offload.
        """
        payload = {
            "timestamp": int(time.time()),
            "node": node,
            "thermal_level": thermal_level,
            "thermal_state": thermal_state,
            "trigger_offload": trigger_offload,
        }
        self.signal_path.parent.mkdir(parents=True, exist_ok=True)
        self.signal_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.signal_path

    def clear_thermal_signal(self) -> None:
        """Removes the thermal signal file if present."""
        if self.signal_path.exists():
            try:
                self.signal_path.unlink()
            except OSError:
                pass
