#!/usr/bin/env python3
"""
tests/test_kimi_tandem_sharding.py
==================================
Milestone M1 Verification Suite:
Kimi Tandem Distributed VRAM Sharding, Dynamic RAM Ceilings & MCP Routing.

Verifies:
1. Kimi Tandem 80-layer distributed tensor split (-ts 28,28,24 on Port 50052)
2. Dynamic memory ceilings (Mac 90%, Linux 80%, Pixel 85%, S20+ 75%, Tablet 75%)
3. 82.8 GB pooled VRAM cluster capacity and multi-node RPC fill-up hierarchy
4. Antigravity MCP Models Server (antigravity-models) routing to Port 8081 with automated Exo/Petals failover
5. Zero-mock empirical data assertions across physical hardware specs
"""

import os
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
MESH_PATH = REPO_ROOT / "02_ai_models_and_inference" / "llama_rpc_mesh"
MCP_SRC_PATH = Path("/Users/aaron/teamwork_projects/antigravity_mcp_models/src")

for p in [REPO_ROOT, INFRA_PATH, MESH_PATH, MCP_SRC_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from kimi_tandem_orchestrator import (
    calculate_usable_vram,
    calculate_min_os_buffer,
    compute_kimi_layer_split,
    format_tensor_split_arg,
    format_rpc_servers_arg,
    build_kimi_dev_72b_command,
    build_kimi_vl_thinking_command,
    get_cluster_headroom_status,
    DYNAMIC_MEMORY_CEILINGS,
    RPC_PORT,
    MASTER_SERVER_PORT,
    VISION_SERVER_PORT,
    EDGE_SERVER_PORT
)

from ram_autoscaler_governor import (
    MeshRAMAutoScalerSentinel,
    HEADROOM_REQUIREMENTS,
    HEADROOM_THRESHOLDS_GB
)


class TestKimiTandemShardingMathematics:
    """Verifies exact layer splitting, VRAM allocation, and CLI directives for Kimi Tandem."""

    def test_kimi_dev_72b_80_layer_split(self):
        """Verify that 80 transformer layers split into exactly 28, 28, 24 across Linux, MBP, Mac Mini."""
        split = compute_kimi_layer_split(80)
        assert split == (28, 28, 24), f"Expected (28, 28, 24), got {split}"
        assert sum(split) == 80

        ts_arg = format_tensor_split_arg(split)
        assert ts_arg == "28,28,24"

    def test_kimi_layer_split_custom_layer_scaling(self):
        """Verify mathematical scaling for non-standard layer counts."""
        # 40 layers (half scale)
        split_40 = compute_kimi_layer_split(40)
        assert split_40 == (14, 14, 12)
        assert sum(split_40) == 40

        # Boundary: 0 layers
        assert compute_kimi_layer_split(0) == (0, 0, 0)

    def test_rpc_servers_argument_formatting(self):
        """Verify RPC multi-node connection string with Thunderbolt 4 DMA bridge."""
        # With TB4
        rpc_tb4 = format_rpc_servers_arg(use_tb4=True)
        assert rpc_tb4 == "100.101.39.98:50052,169.254.187.138:50052,127.0.0.1:50052"
        assert f":{RPC_PORT}" in rpc_tb4

        # Fallback LAN
        rpc_lan = format_rpc_servers_arg(use_tb4=False)
        assert rpc_lan == "100.101.39.98:50052,100.103.212.21:50052,127.0.0.1:50052"

    def test_llama_server_cli_generation(self):
        """Verify complete CLI construction for distributed Kimi-Dev-72B and Kimi-VL."""
        cmd_72b = build_kimi_dev_72b_command(
            model_path="/Volumes/NAS/AI_Models/kimi-dev-72b-instruct-q4_k_m.gguf",
            ctx_size=16384,
            port=8081
        )
        assert "llama-server" in cmd_72b
        assert "--rpc" in cmd_72b
        assert "-ts" in cmd_72b
        assert "28,28,24" in cmd_72b
        assert "--port" in cmd_72b
        assert "8081" in cmd_72b
        assert "-ngl" in cmd_72b
        assert "999" in cmd_72b

        cmd_vl = build_kimi_vl_thinking_command(
            model_path="/Volumes/NAS/AI_Models/kimi-vl-thinking-2506-q4_k_m.gguf",
            mmproj_path="/Volumes/NAS/AI_Models/kimi-vl-thinking-2506-mmproj-f16.gguf",
            ctx_size=32768,
            port=8085
        )
        assert "llama-server" in cmd_vl
        assert "--mmproj" in cmd_vl
        assert "--port" in cmd_vl
        assert "8085" in cmd_vl
        assert "--ctx-size" in cmd_vl
        assert "32768" in cmd_vl


class TestDynamicMemoryCeilingsAndHeadroom:
    """Verifies node memory limits: Mac 90%, Linux 80%, Pixel 85%, S20+ 75%, Tablet 75%."""

    def test_dynamic_memory_ceilings_percentages(self):
        """Verify dynamic memory ceiling percentages per platform."""
        assert DYNAMIC_MEMORY_CEILINGS["mac_host"] == 90.0
        assert DYNAMIC_MEMORY_CEILINGS["macbook_pro"] == 90.0
        assert DYNAMIC_MEMORY_CEILINGS["macbook_air"] == 90.0
        assert DYNAMIC_MEMORY_CEILINGS["linux_node"] == 80.0
        assert DYNAMIC_MEMORY_CEILINGS["linux_tablet"] == 75.0
        assert DYNAMIC_MEMORY_CEILINGS["pixel_10"] == 85.0
        assert DYNAMIC_MEMORY_CEILINGS["samsung_s20"] == 75.0

    def test_usable_vram_and_min_os_buffer_calculations(self):
        """Verify mathematical calculation of usable VRAM and OS buffer."""
        # Mac Host: 24.0 GB * 90% = 21.6 GB usable, 2.4 GB OS buffer
        assert calculate_usable_vram(24.0, 90.0) == 21.60
        assert calculate_min_os_buffer(24.0, 90.0) == 2.40

        # MacBook Pro: 16.0 GB * 90% = 14.4 GB usable, 1.6 GB OS buffer
        assert calculate_usable_vram(16.0, 90.0) == 14.40
        assert calculate_min_os_buffer(16.0, 90.0) == 1.60

        # Linux Head Node: 16.0 GB * 80% = 12.8 GB usable, 3.2 GB OS buffer
        assert calculate_usable_vram(16.0, 80.0) == 12.80
        assert calculate_min_os_buffer(16.0, 80.0) == 3.20

        # Pixel 10 Pro XL: 16.0 GB * 85% = 13.6 GB usable, 2.4 GB OS buffer
        assert calculate_usable_vram(16.0, 85.0) == 13.60
        assert calculate_min_os_buffer(16.0, 85.0) == 2.40

        # Samsung S20+: 12.0 GB * 75% = 9.0 GB usable, 3.0 GB OS buffer
        assert calculate_usable_vram(12.0, 75.0) == 9.00
        assert calculate_min_os_buffer(12.0, 75.0) == 3.00

        # Linux Tablet: 8.0 GB * 75% = 6.0 GB usable, 2.0 GB OS buffer
        assert calculate_usable_vram(8.0, 75.0) == 6.00
        assert calculate_min_os_buffer(8.0, 75.0) == 2.00

    def test_cluster_usable_vram_pooled_capacity(self):
        """Verify cluster pooled VRAM and Kimi Tandem utilization."""
        status = get_cluster_headroom_status()
        assert status["total_physical_ram_gb"] >= 100.0
        assert status["total_usable_vram_gb"] >= 82.8
        assert status["total_allocated_vram_gb"] == 48.80
        assert status["cluster_free_vram_headroom_gb"] >= 34.0
        assert status["all_nodes_compliant"] is True

    def test_ram_autoscaler_governor_sharding_integration(self):
        """Verify integration with ram_autoscaler_governor.py."""
        governor = MeshRAMAutoScalerSentinel()
        sharding_info = governor.compute_kimi_sharding_split(80)
        assert sharding_info["total_layers"] == 80
        assert sharding_info["split"] == [28, 28, 24]
        assert sharding_info["tensor_split_arg"] == "28,28,24"
        assert sharding_info["rpc_port"] == 50052
        assert sharding_info["master_http_port"] == 8081
        assert sharding_info["sharding_verified"] is True

    def test_rpc_fillup_hierarchy_ordering(self):
        """Verify strict priority ordering in fill-up hierarchy."""
        governor = MeshRAMAutoScalerSentinel()
        hierarchy = governor.validate_rpc_fillup_hierarchy()
        node_order = [h["node"] for h in hierarchy]
        # Priority 1 (Linux Head, Linux Tablet) -> Priority 2 (MacBook Pro) -> Priority 3 (MacBook Air)
        # -> Priority 4 (Mac Mini) -> Priority 5 (Samsung S20+) -> Priority 6 (Pixel 10)
        assert node_order[0] in ["linux_node", "linux_tablet"]
        assert "macbook_pro" in node_order[2:4]
        assert node_order[-1] == "pixel_10"


class TestAntigravityMCPModelsRouting:
    """Verifies Antigravity MCP Models Server configuration, routing to Port 8081, and auto-failover."""

    def test_settings_json_llamacpp_base_url(self):
        """Verify ~/.gemini/settings.json points LLAMACPP_BASE_URL to Port 8081."""
        settings_path = Path("/Users/aaron/.gemini/settings.json")
        assert settings_path.exists()
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        
        mcp_servers = settings.get("mcpServers", {})
        assert "antigravity-models" in mcp_servers
        models_server = mcp_servers["antigravity-models"]
        env_vars = models_server.get("env", {})
        assert env_vars.get("LLAMACPP_BASE_URL") == "http://127.0.0.1:8081"
        assert env_vars.get("PETALS_BASE_URL") == "https://chat.petals.dev"
        assert env_vars.get("EXO_BASE_URL") == "http://127.0.0.1:52415"

    def test_manifest_file_structure_and_invariants(self):
        """Verify kimi_tandem_sharding_manifest.json exists and is schema-valid."""
        manifest_file = REPO_ROOT / "02_ai_models_and_inference" / "llama_rpc_mesh" / "kimi_tandem_sharding_manifest.json"
        assert manifest_file.exists()
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "kimi_tandem_sharding_manifest" in data
        manifest = data["kimi_tandem_sharding_manifest"]
        assert manifest["cluster_architecture"]["pooled_vram_gb"] == 82.8
        assert manifest["cluster_architecture"]["rpc_sharding_port"] == 50052
        assert manifest["cluster_architecture"]["master_inference_port"] == 8081
        assert manifest["tandem_summary"]["layer_split"] == [28, 28, 24]
        assert manifest["tandem_summary"]["combined_footprint_gb"] == 48.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
