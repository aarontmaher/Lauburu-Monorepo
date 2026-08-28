"""
Unit Tests for Distributed AI Mesh Adapters & MeshScaffoldingCard
Comprehensive unit and edge-case testing covering:
1. TailscaleAdapter: CLI parsing, peer discovery, ping, route management, fallbacks, timeout handling, and serialization.
2. SpeedifyAdapter: Adapter listing, multi-WAN bonding stats, priority switching, bonding modes, fallbacks.
3. ExoAdapter: P2P ring topology on Port 52415, shard mapping, benchmark execution, REST API handling.
4. AccelerateAdapter: Environment inspection, backend detection (MPS/CUDA), process scanning, launch tracking.
5. LlamaRpcAdapter: Port 50052 RPC latency matrix, server health on Ports 8081-8085, custom targets.
6. MeshScaffoldingCard: Status badge rendering, telemetry update, async audit with error resilience.
7. ToolingView & ToolingScreen: Panel 5 integration, composition, and button event wiring.
"""

import os
import sys
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from services.mesh_adapters import (
    TailscaleAdapter, TailscalePeerInfo, TailscalePingResult, TailscaleStatusResult,
    SpeedifyAdapter, SpeedifyAdapterInfo, SpeedifyStats, SpeedifyStatusResult,
    ExoAdapter, ExoPeerInfo, ExoShardMapping, ExoBenchmarkResult, ExoTopologyResult,
    AccelerateAdapter, AccelerateEnvInfo, AccelerateJobInfo, AccelerateStatusResult,
    LlamaRpcAdapter, LlamaRpcTarget, LlamaServerHealth, LlamaRpcClusterStatus
)
from widgets.mesh_scaffolding_card import MeshScaffoldingCard
from views.tooling_view import ToolingView
from screens.tooling_screen import ToolingScreen


# ============================================================================
# 1. TAILSCALE ADAPTER TESTS
# ============================================================================

class TestTailscaleAdapter:
    @pytest.mark.asyncio
    async def test_tailscale_init_and_detection(self):
        adapter = TailscaleAdapter(binary_path="/mock/tailscale")
        assert adapter.binary_path == "/mock/tailscale"
        assert adapter.timeout_seconds == 1.5

    def test_tailscale_is_installed_check(self):
        adapter = TailscaleAdapter(binary_path="/nonexistent/path/to/tailscale")
        assert adapter.is_installed() is False

    @pytest.mark.asyncio
    async def test_tailscale_fallback_status(self):
        adapter = TailscaleAdapter(binary_path="/nonexistent/tailscale")
        status = await adapter.get_status()
        assert isinstance(status, TailscaleStatusResult)
        assert status.online is True
        assert len(status.peers) >= 7
        assert status.self_name == "Mac_Node"
        assert status.self_ip == "100.119.199.76"
        assert "error" in status.to_dict()
        assert status.to_json() is not None

    @pytest.mark.asyncio
    async def test_tailscale_mock_json_parsing(self):
        mock_output = {
            "Self": {
                "HostName": "Custom_Mac_Node",
                "TailscaleIPs": ["100.119.199.76"],
                "Online": True,
                "OS": "macOS"
            },
            "Peer": {
                "node1": {
                    "HostName": "MacBook_Pro",
                    "TailscaleIPs": ["100.103.212.21"],
                    "Online": True,
                    "Active": True,
                    "OS": "macOS",
                    "Relay": "",
                    "RxBytes": 1024,
                    "TxBytes": 2048,
                    "LastSeen": "2026-08-27T17:00:00Z",
                    "CurAddr": "192.168.8.127:41641"
                },
                "node2": {
                    "HostName": "Linux_Head_Node",
                    "TailscaleIPs": ["100.101.39.98"],
                    "Online": True,
                    "Active": False,
                    "OS": "linux",
                    "Relay": "syd-1",
                    "RxBytes": 512,
                    "TxBytes": 128
                }
            }
        }
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        res = adapter._parse_status_json(mock_output, json.dumps(mock_output))
        assert res.self_name == "Custom_Mac_Node"
        assert res.online is True
        assert len(res.peers) == 2
        assert res.direct_mesh_count == 1
        assert res.derp_relay_count == 1

        p1 = next(p for p in res.peers if p.name == "MacBook_Pro")
        assert p1.relay == "Direct WireGuard"
        assert p1.status == "ONLINE"
        assert p1.rx_bytes == 1024
        assert p1.cur_addr == "192.168.8.127:41641"
        assert p1.to_dict()["cur_addr"] == "192.168.8.127:41641"

        p2 = next(p for p in res.peers if p.name == "Linux_Head_Node")
        assert p2.relay == "DERP Relay"

    @pytest.mark.asyncio
    async def test_tailscale_subprocess_mock_success(self):
        mock_data = {
            "Self": {"HostName": "Live_Mac", "TailscaleIPs": ["100.1.1.1"], "Online": True},
            "Peer": {}
        }
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (json.dumps(mock_data).encode("utf-8"), b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                status = await adapter.get_status()
                assert status.self_name == "Live_Mac"
                assert status.online is True
                assert status.error is None

    @pytest.mark.asyncio
    async def test_tailscale_subprocess_timeout(self):
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale", timeout_seconds=0.01)
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.side_effect = asyncio.TimeoutError()
            mock_proc.kill = MagicMock()
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                status = await adapter.get_status()
                assert "timed out" in status.error

    @pytest.mark.asyncio
    async def test_tailscale_subprocess_error_code(self):
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", b"daemon is stopped")
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                status = await adapter.get_status()
                assert "daemon is stopped" in status.error

    @pytest.mark.asyncio
    async def test_tailscale_ping_peer(self):
        adapter = TailscaleAdapter(binary_path="/nonexistent/tailscale")
        res = await adapter.ping_peer("100.103.212.21")
        assert isinstance(res, TailscalePingResult)
        assert res.ip == "100.103.212.21"
        assert res.to_dict()["ip"] == "100.103.212.21"

    @pytest.mark.asyncio
    async def test_tailscale_ping_mock_subprocess_success(self):
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"pong from 100.103.212.21 in 3.45ms", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                res = await adapter.ping_peer("100.103.212.21")
                assert res.success is True
                assert res.latency_ms == 3.45
                assert res.relay_mode == "Direct WireGuard"

    @pytest.mark.asyncio
    async def test_tailscale_ping_derp_relay(self):
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"pong via DERP(syd) in 24.10ms", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                res = await adapter.ping_peer("100.103.212.21")
                assert res.success is True
                assert res.relay_mode == "DERP Relay"
                assert res.latency_ms == 24.10

    @pytest.mark.asyncio
    async def test_tailscale_set_mesh_state(self):
        adapter = TailscaleAdapter(binary_path="/usr/bin/tailscale")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"Success", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                up_res = await adapter.set_mesh_state(up=True, routes=["10.0.0.0/24"])
                assert up_res is True

                down_res = await adapter.set_mesh_state(up=False)
                assert down_res is True


# ============================================================================
# 2. SPEEDIFY ADAPTER TESTS
# ============================================================================

class TestSpeedifyAdapter:
    @pytest.mark.asyncio
    async def test_speedify_init_and_adapters_fallback(self):
        adapter = SpeedifyAdapter(cli_path="/nonexistent/speedify_cli")
        adapters = await adapter.get_adapters()
        assert len(adapters) == 3
        names = [a.name for a in adapters]
        assert any("Wi-Fi 7" in n for n in names)
        assert any("Thunderbolt 4" in n for n in names)
        assert any("5G USB" in n for n in names)

    def test_speedify_is_installed(self):
        adapter = SpeedifyAdapter(cli_path="/nonexistent/path")
        assert adapter.is_installed() is False

    @pytest.mark.asyncio
    async def test_speedify_stats_fallback(self):
        adapter = SpeedifyAdapter(cli_path="/nonexistent/speedify_cli")
        stats = await adapter.get_stats()
        assert isinstance(stats, SpeedifyStats)
        assert stats.connected is True
        assert stats.download_mbps >= 2400.0
        assert stats.upload_mbps >= 100.0
        assert stats.bonded_count == 3
        assert stats.to_dict()["download_mbps"] >= 2400.0

    @pytest.mark.asyncio
    async def test_speedify_get_status_aggregation(self):
        adapter = SpeedifyAdapter(cli_path="/nonexistent/speedify_cli")
        status = await adapter.get_status()
        assert isinstance(status, SpeedifyStatusResult)
        assert len(status.adapters) == 3
        assert status.stats.bonded_count == 3
        d = status.to_dict()
        assert "adapters" in d
        assert "stats" in d
        assert status.to_json() is not None

    @pytest.mark.asyncio
    async def test_speedify_mock_adapters_subprocess(self):
        mock_raw = [
            {"adapterID": "en0", "name": "Wi-Fi Interface", "interface": "en0", "type": "Wi-Fi", "state": "CONNECTED", "priority": "ALWAYS", "rateUpBps": 1000000, "rateDownBps": 50000000}
        ]
        adapter = SpeedifyAdapter(cli_path="/usr/bin/speedify_cli")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (json.dumps(mock_raw).encode("utf-8"), b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                ad_list = await adapter.get_adapters()
                assert len(ad_list) == 1
                assert ad_list[0].adapter_id == "en0"
                assert ad_list[0].state == "CONNECTED"
                assert ad_list[0].priority == "ALWAYS"

    @pytest.mark.asyncio
    async def test_speedify_mock_stats_subprocess(self):
        mock_stats = {
            "connections": [{"name": "en0"}, {"name": "bridge0"}],
            "uploadSpeedBps": 15000000,
            "downloadSpeedBps": 300000000,
            "lossPercentage": 0.01,
            "latencyMs": 1.25,
            "state": "CONNECTED"
        }
        adapter = SpeedifyAdapter(cli_path="/usr/bin/speedify_cli")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (json.dumps(mock_stats).encode("utf-8"), b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                stats = await adapter.get_stats()
                assert stats.connected is True
                assert stats.upload_mbps == 120.0
                assert stats.download_mbps == 2400.0
                assert stats.latency_ms == 1.25
                assert stats.bonded_count == 2

    @pytest.mark.asyncio
    async def test_speedify_control_methods(self):
        adapter = SpeedifyAdapter(cli_path="/usr/bin/speedify_cli")
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"ok", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            with patch.object(adapter, "is_installed", return_value=True):
                p_res = await adapter.set_adapter_priority("en0", "always")
                assert p_res is True

                m_res = await adapter.set_bonding_mode("speed")
                assert m_res is True


# ============================================================================
# 3. EXO ADAPTER TESTS
# ============================================================================

class TestExoAdapter:
    @pytest.mark.asyncio
    async def test_exo_init_and_probe(self):
        adapter = ExoAdapter(host="127.0.0.1", port=52415)
        assert adapter.port == 52415
        is_up = await adapter.probe_socket()
        assert isinstance(is_up, bool)

    @pytest.mark.asyncio
    async def test_exo_topology_canonical_fallback(self):
        adapter = ExoAdapter(host="127.0.0.1", port=52415)
        top = await adapter.get_topology()
        assert isinstance(top, ExoTopologyResult)
        assert top.port == 52415
        assert top.topology_type == "Ring-P2P"
        assert len(top.peers) == 4
        assert top.shard_mapping is not None
        assert top.shard_mapping.total_shards == 4
        assert "exo-01" in top.shard_mapping.shards_by_peer
        assert top.to_json() is not None
        assert top.peers[0].to_dict()["node_id"] == "exo-01"

    @pytest.mark.asyncio
    async def test_exo_parse_topology_dict(self):
        mock_raw = {
            "topology_type": "Ring-P2P",
            "active_model": "mistral-7b",
            "peers": [
                {"node_id": "p1", "name": "Node 1", "ip": "127.0.0.1", "memory_free_gb": 16.0, "vram_free_gb": 14.0, "shards_assigned": ["shard-0"], "status": "ACTIVE"}
            ],
            "shard_mapping": {
                "model_id": "mistral-7b",
                "total_shards": 1,
                "shards_by_peer": {"p1": [0, 1, 2]}
            }
        }
        adapter = ExoAdapter()
        top = adapter._parse_topology_dict(mock_raw)
        assert top.connected is True
        assert top.active_model == "mistral-7b"
        assert len(top.peers) == 1
        assert top.shard_mapping.total_shards == 1

    @pytest.mark.asyncio
    async def test_exo_benchmark_and_sync(self):
        adapter = ExoAdapter(host="127.0.0.1", port=52415)
        bench = await adapter.run_benchmark(model="llama-3-8b", tokens=32)
        assert isinstance(bench, ExoBenchmarkResult)
        assert bench.success is True
        assert bench.tokens_per_second > 0.0
        assert bench.ring_nodes_count == 4
        assert bench.to_dict()["model"] == "llama-3-8b"

        sync_res = await adapter.sync_ring()
        assert sync_res is True

        peers = await adapter.get_peers()
        assert len(peers) == 4


# ============================================================================
# 4. ACCELERATE ADAPTER TESTS
# ============================================================================

class TestAccelerateAdapter:
    @pytest.mark.asyncio
    async def test_accelerate_init_and_env_detection(self):
        adapter = AccelerateAdapter()
        env = await adapter.get_environment()
        assert isinstance(env, AccelerateEnvInfo)
        assert env.backend in ["MPS (Apple Silicon Metal Performance Shaders)", "MPS (Apple Silicon Metal)", "MPS (Apple Silicon)", "CPU / Host Threading", "CUDA GPU", "CPU"]
        assert env.mixed_precision in ["fp16", "fp32", "bf16", "no"]
        assert env.num_processes >= 1
        assert env.to_dict()["num_processes"] >= 1

    @pytest.mark.asyncio
    async def test_accelerate_parse_env_output(self):
        mock_raw = """
        - `Accelerate` version: 1.2.0
        - Platform: macOS-15.0-arm64
        - Python version: 3.13.0
        - Number of devices: 1
        - Mixed precision: fp16
        - Distributed type: MULTI_PROCESS
        - MPS: True
        """
        adapter = AccelerateAdapter()
        parsed = adapter._parse_env_output(mock_raw)
        assert parsed.use_mps is True
        assert parsed.mixed_precision == "fp16"
        assert parsed.distributed_type == "MULTI_PROCESS"

    @pytest.mark.asyncio
    async def test_accelerate_cuda_parse(self):
        mock_cuda = """
        - `Accelerate` version: 1.2.0
        - Number of devices: 2
        - Mixed precision: bf16
        - Distributed type: MULTI_GPU
        - CUDA: True
        """
        adapter = AccelerateAdapter()
        parsed = adapter._parse_env_output(mock_cuda)
        assert parsed.use_cuda is True
        assert parsed.backend == "CUDA GPU"
        assert parsed.mixed_precision == "bf16"

    @pytest.mark.asyncio
    async def test_accelerate_get_status_and_jobs(self):
        adapter = AccelerateAdapter()
        status = await adapter.get_status()
        assert isinstance(status, AccelerateStatusResult)
        assert status.env is not None
        assert isinstance(status.running_jobs, list)
        assert status.to_json() is not None
        assert "env" in status.to_dict()


# ============================================================================
# 5. LLAMA RPC ADAPTER TESTS
# ============================================================================

class TestLlamaRpcAdapter:
    @pytest.mark.asyncio
    async def test_llama_rpc_init_and_targets(self):
        adapter = LlamaRpcAdapter()
        assert len(adapter.rpc_targets) == 3
        assert len(adapter.server_ports) == 5

    @pytest.mark.asyncio
    async def test_llama_rpc_socket_latency_probe(self):
        adapter = LlamaRpcAdapter()
        # Test probing localhost on an unused port (should return None safely)
        lat = await adapter.probe_socket_latency("127.0.0.1", 59999, timeout=0.01)
        assert lat is None or isinstance(lat, float)

    @pytest.mark.asyncio
    async def test_llama_rpc_probe_cluster(self):
        adapter = LlamaRpcAdapter()
        cluster_status = await adapter.probe_rpc_cluster()
        assert isinstance(cluster_status, LlamaRpcClusterStatus)
        assert cluster_status.sharding_strategy == "-ts 28,28,24"
        assert cluster_status.total_sharded_layers == 80
        assert len(cluster_status.rpc_nodes) == 3
        assert len(cluster_status.server_endpoints) == 5
        assert cluster_status.to_json() is not None
        assert cluster_status.rpc_nodes[0].to_dict()["layers_sharded"] == 28

    @pytest.mark.asyncio
    async def test_llama_server_health(self):
        adapter = LlamaRpcAdapter()
        h8081 = await adapter.get_server_health(8081, "Kimi Master Gateway")
        assert isinstance(h8081, LlamaServerHealth)
        assert h8081.port == 8081
        assert h8081.role == "Kimi Master Gateway"
        assert h8081.to_dict()["port"] == 8081


# ============================================================================
# 6. MESH SCAFFOLDING CARD WIDGET TESTS
# ============================================================================

class TestMeshScaffoldingCard:
    def test_card_instantiation_and_render(self):
        card = MeshScaffoldingCard()
        assert card is not None
        assert card.ts_adapter is not None
        assert card.speedify_adapter is not None
        assert card.exo_adapter is not None
        assert card.accel_adapter is not None
        assert card.rpc_adapter is not None

        # Verify initial refresh card populates defaults
        card.refresh_card()
        assert card.ts_status is not None
        assert card.speedify_status is not None
        assert card.exo_status is not None
        assert card.accel_status is not None
        assert card.rpc_status is not None

    @pytest.mark.asyncio
    async def test_card_async_mesh_audit(self):
        card = MeshScaffoldingCard()
        audit_res = await card.run_mesh_audit_async()
        assert "tailscale" in audit_res
        assert "speedify" in audit_res
        assert "exo" in audit_res
        assert "accelerate" in audit_res
        assert "llama_rpc" in audit_res

    def test_card_update_telemetry(self):
        card = MeshScaffoldingCard()
        card.refresh_card()
        custom_ts = TailscaleStatusResult(
            self_name="Test_Node",
            self_ip="100.1.2.3",
            online=True,
            peers=[TailscalePeerInfo(name="P1", ip="100.1.2.4", status="ONLINE", relay="Direct WireGuard")]
        )
        card.update_telemetry(ts=custom_ts)
        assert card.ts_status.self_name == "Test_Node"

    @pytest.mark.asyncio
    async def test_card_audit_resilience_to_exceptions(self):
        card = MeshScaffoldingCard()
        with patch.object(card.ts_adapter, "get_status", side_effect=RuntimeError("ts exploded")):
            with patch.object(card.exo_adapter, "get_topology", side_effect=TimeoutError("exo timed out")):
                audit_res = await card.run_mesh_audit_async()
                assert audit_res["tailscale"] is None
                assert audit_res["exo"] is None
                assert audit_res["speedify"] is not None


# ============================================================================
# 7. TOOLING VIEW & SCREEN INTEGRATION TESTS
# ============================================================================

class TestToolingIntegration:
    def test_tooling_view_instantiation_and_composition(self):
        view = ToolingView()
        assert view is not None

    def test_tooling_screen_instantiation_and_composition(self):
        screen = ToolingScreen()
        assert screen is not None

    def test_button_pressed_handlers(self):
        view = ToolingView()
        view.notify = MagicMock()
        view.refresh_views = MagicMock()
        view.query_one = MagicMock(return_value=None)

        btn_mock = MagicMock()
        btn_mock.button.id = "btn-mesh-audit"
        view.on_button_pressed(btn_mock)
        view.notify.assert_called()

        btn_mock.button.id = "btn-probe-rpc"
        view.on_button_pressed(btn_mock)
        view.notify.assert_called()

        btn_mock.button.id = "btn-sync-exo"
        view.on_button_pressed(btn_mock)
        view.notify.assert_called()

        btn_mock.button.id = "btn-accel-env"
        view.on_button_pressed(btn_mock)
        view.notify.assert_called()

        btn_mock.button.id = "btn-refresh-mesh"
        view.on_button_pressed(btn_mock)
        view.notify.assert_called()

    def test_tooling_screen_button_pressed_handlers(self):
        screen = ToolingScreen()
        screen.notify = MagicMock()
        screen.refresh_views = MagicMock()
        screen.query_one = MagicMock(return_value=None)

        btn_mock = MagicMock()
        btn_mock.button.id = "btn-mesh-audit"
        screen.on_button_pressed(btn_mock)
        screen.notify.assert_called()

        btn_mock.button.id = "btn-probe-rpc"
        screen.on_button_pressed(btn_mock)
        screen.notify.assert_called()

        btn_mock.button.id = "btn-sync-exo"
        screen.on_button_pressed(btn_mock)
        screen.notify.assert_called()

        btn_mock.button.id = "btn-accel-env"
        screen.on_button_pressed(btn_mock)
        screen.notify.assert_called()

        btn_mock.button.id = "btn-refresh-mesh"
        screen.on_button_pressed(btn_mock)
        screen.notify.assert_called()
