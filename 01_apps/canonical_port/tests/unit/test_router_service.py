"""
Unit Tests for GL.iNet MT3600BE & LuCI Router Service
Version: 3.0.0-CANONICAL
Tests asynchronous Dropbear SSH commands, ubus JSON parsing, UCI execution,
timeout resilience, and offline fallback models without event-loop starvation.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from tui.services.router_service import RouterService, LuciGlinetClient, router_service
from tui.models.network_telemetry import (
    RouterSystemInfo,
    RouterInterfaceStats,
    ConnectedClient,
    RouterCommandResult,
)


class TestRouterService:
    """Test suite for RouterService class."""

    def test_router_service_initialization(self):
        rs = RouterService(
            router_ip="192.168.8.1",
            ssh_port=22,
            ssh_user="root",
            timeout=3.0,
            tailscale_ip="100.122.185.123",
        )
        assert rs.router_ip == "192.168.8.1"
        assert rs.ssh_port == 22
        assert rs.ssh_user == "root"
        assert rs.timeout == 3.0
        assert rs.tailscale_ip == "100.122.185.123"
        assert LuciGlinetClient is RouterService

    def test_build_ssh_command(self):
        rs = RouterService(router_ip="192.168.8.1", ssh_port=2222, timeout=4.0)
        cmd = rs._build_ssh_command("ubus call system info")
        assert cmd[0] == "ssh"
        assert "-o" in cmd
        assert "BatchMode=yes" in cmd
        assert "StrictHostKeyChecking=no" in cmd
        assert "UserKnownHostsFile=/dev/null" in cmd
        assert "ConnectTimeout=4" in cmd
        assert "-p" in cmd
        assert "2222" in cmd
        assert "root@192.168.8.1" in cmd
        assert "ubus call system info" == cmd[-1]

    def test_format_uptime(self):
        assert RouterService._format_uptime(0) == "0s"
        assert RouterService._format_uptime(45) == "45s"
        assert RouterService._format_uptime(125) == "02m 05s"
        assert RouterService._format_uptime(3665) == "01h 01m 05s"
        assert RouterService._format_uptime(90065) == "1d 01h 01m 05s"

    @pytest.mark.asyncio
    async def test_execute_raw_cli_success(self):
        rs = RouterService()
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"output text\n", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            res = await rs.execute_raw_cli("echo test")
            assert res.success is True
            assert res.output == "output text"
            assert res.error is None
            assert res.execution_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_execute_raw_cli_timeout(self):
        rs = RouterService(timeout=0.1)
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = asyncio.TimeoutError()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            res = await rs.execute_raw_cli("sleep 10", timeout=0.1)
            assert res.success is False
            assert res.output == ""
            assert "timed out" in res.error

    @pytest.mark.asyncio
    async def test_execute_raw_cli_error(self):
        rs = RouterService()
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"command not found\n")
        mock_proc.returncode = 127

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            res = await rs.execute_raw_cli("badcommand")
            assert res.success is False
            assert res.error == "command not found"

    @pytest.mark.asyncio
    async def test_execute_uci_command(self):
        rs = RouterService()
        with patch.object(
            rs,
            "execute_raw_cli",
            return_value=RouterCommandResult(
                command="uci show network",
                success=True,
                output="network.wan=interface\nnetwork.wan.proto='dhcp'",
            ),
        ) as mock_exec:
            out = await rs.execute_uci_command("show network")
            assert "network.wan" in out
            mock_exec.assert_called_once_with("uci show network")

        with patch.object(
            rs,
            "execute_raw_cli",
            return_value=RouterCommandResult(
                command="uci get wireless.radio0.band",
                success=True,
                output="5g",
            ),
        ) as mock_exec:
            out = await rs.execute_uci_command("uci get wireless.radio0.band")
            assert out == "5g"
            mock_exec.assert_called_once_with("uci get wireless.radio0.band")

    @pytest.mark.asyncio
    async def test_execute_ubus_call(self):
        rs = RouterService()
        sample_json = json.dumps({"uptime": 12345, "load": [6553, 3276, 1638]})
        with patch.object(
            rs,
            "execute_raw_cli",
            return_value=RouterCommandResult(
                command="ubus call system info",
                success=True,
                output=sample_json,
            ),
        ):
            res = await rs.execute_ubus_call("system", "info")
            assert isinstance(res, dict)
            assert res["uptime"] == 12345

    @pytest.mark.asyncio
    async def test_execute_ubus_call_with_args(self):
        rs = RouterService()
        with patch.object(
            rs,
            "execute_raw_cli",
            return_value=RouterCommandResult(
                command="ubus call network.interface.wan status",
                success=True,
                output='{"up": true}',
            ),
        ) as mock_exec:
            res = await rs.execute_ubus_call("network.interface.wan", "status", {"verbose": True})
            assert res.get("up") is True
            assert "'{\"verbose\": true}'" in mock_exec.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_system_info_success(self):
        rs = RouterService()
        info_json = {
            "uptime": 1232810,
            "load": [7864, 5242, 3276],  # ~0.12, ~0.08, ~0.05
            "memory": {
                "total": 536870912,
                "free": 192937984,
                "buffered": 16777216,
                "cached": 33554432,
            },
        }
        board_json = {
            "model": "GL.iNet GL-MT3600BE",
            "hostname": "GL-MT3600BE",
            "kernel": "5.15.150",
            "release": {"distribution": "OpenWrt", "version": "23.05-SNAPSHOT"},
        }

        async def _mock_ubus(path, method, args=None):
            if path == "system" and method == "info":
                return info_json
            if path == "system" and method == "board":
                return board_json
            return {}

        with patch.object(rs, "execute_ubus_call", side_effect=_mock_ubus):
            sys_info = await rs.get_system_info(force_refresh=True)
            assert sys_info.status == "ONLINE"
            assert sys_info.model == "GL.iNet GL-MT3600BE"
            assert sys_info.hostname == "GL-MT3600BE"
            assert sys_info.uptime == 1232810
            assert "14d" in sys_info.uptime_formatted
            assert sys_info.memory_total_mb == 512.0
            assert sys_info.memory_free_mb == round((192937984 + 16777216 + 33554432) / (1024 * 1024), 1)
            assert len(sys_info.load_average) == 3
            assert sys_info.to_dict()["status"] == "ONLINE"

    @pytest.mark.asyncio
    async def test_get_system_info_offline_fallback(self):
        rs = RouterService(router_ip="192.168.8.1")
        with patch.object(rs, "execute_ubus_call", return_value={}):
            sys_info = await rs.get_system_info(force_refresh=True)
            assert sys_info.status == "OFFLINE"
            assert sys_info.ip == "192.168.8.1"
            assert sys_info.uptime == 0

    @pytest.mark.asyncio
    async def test_get_interface_stats(self):
        rs = RouterService()
        dump_data = {
            "interface": [
                {
                    "interface": "wan",
                    "l3_device": "eth0",
                    "up": True,
                    "ipv4-address": [{"address": "192.168.1.105", "mask": 24}],
                    "statistics": {
                        "rx_bytes": 1048576000,
                        "tx_bytes": 524288000,
                        "rx_packets": 750000,
                        "tx_packets": 420000,
                    },
                },
                {
                    "interface": "lan",
                    "l3_device": "br-lan",
                    "up": True,
                    "ipv4-address": [{"address": "192.168.8.1", "mask": 24}],
                    "statistics": {
                        "rx_bytes": 524288000,
                        "tx_bytes": 1048576000,
                    },
                },
            ]
        }
        with patch.object(rs, "execute_ubus_call", return_value=dump_data):
            ifaces = await rs.get_interface_stats()
            assert len(ifaces) == 2
            assert ifaces[0].name == "wan"
            assert ifaces[0].interface == "eth0"
            assert ifaces[0].up is True
            assert ifaces[0].ip_addresses == ["192.168.1.105/24"]
            assert ifaces[0].rx_bytes == 1048576000

    @pytest.mark.asyncio
    async def test_get_connected_clients(self):
        rs = RouterService()
        hostapd_data = {
            "clients": {
                "A4:83:E7:11:22:33": {
                    "signal": -42,
                    "tx": {"rate": 2400000},
                    "rx": {"rate": 2400000},
                    "connected_time": 1200,
                }
            }
        }
        arp_output = (
            "192.168.8.230 0x1 0x2 A4:83:E7:11:22:33 * br-lan\n"
            "192.168.8.127 0x1 0x2 3C:06:30:44:55:66 * br-lan\n"
        )

        async def _mock_ubus(path, method, args=None):
            if "hostapd" in path:
                return hostapd_data
            return {}

        with patch.object(rs, "execute_ubus_call", side_effect=_mock_ubus), \
             patch.object(rs, "execute_raw_cli", return_value=RouterCommandResult(
                 command="cat", success=True, output=arp_output
             )):
            clients = await rs.get_connected_clients()
            assert len(clients) >= 1
            wifi_client = next((c for c in clients if c.mac == "A4:83:E7:11:22:33"), None)
            assert wifi_client is not None
            assert wifi_client.ip == "192.168.8.230"
            assert wifi_client.rssi_dbm == -42
            assert wifi_client.tx_rate_mbps == 2400.0

    @pytest.mark.asyncio
    async def test_reload_wifi(self):
        rs = RouterService()
        with patch.object(
            rs,
            "execute_raw_cli",
            return_value=RouterCommandResult(command="wifi reload", success=True, output=""),
        ) as mock_exec:
            res = await rs.reload_wifi()
            assert res.success is True
            mock_exec.assert_called_once_with("wifi reload")

    def test_sync_wrappers(self):
        rs = RouterService()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="uci_output", stderr="")
            out = rs.execute_uci_command_sync("show network")
            assert out == "uci_output"
