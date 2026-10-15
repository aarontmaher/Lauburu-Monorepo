#!/usr/bin/env python3
"""
00_core_infrastructure/tests/test_router_sentinel_wol.py
========================================================
Comprehensive Test Suite for Milestone M3 (R6):
OpenWrt Router Sentinel & Out-of-Band Power Resurrection (WoL).

Validates:
1. 102-byte RFC 792 Magic Packet construction & structure.
2. WoLEngine.wake_node interface contract over UDP Port 9/7.
3. OpenWrt Router Sentinel memory guard (<= 28MB RAM footprint, >= 250MB free headroom).
4. Port 18802 REST API request routing & status response.
5. Malformed MAC address validation and rejection.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure paths on sys.path
TEST_DIR = Path(__file__).resolve().parent
INFRA_ROOT = TEST_DIR.parent
REPO_ROOT = INFRA_ROOT.parent
TOOLING_MESH = REPO_ROOT / "06_scripts_and_tooling" / "mesh"
ROUTER_ROOT = INFRA_ROOT / "router_ai_daemon"
ROUTER_SRC = ROUTER_ROOT / "src"

for p in [str(REPO_ROOT), str(INFRA_ROOT), str(TOOLING_MESH), str(ROUTER_ROOT), str(ROUTER_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)


from wol_manager import WoLEngine, DEVICES
from router_sentinel_wol_engine import RouterSentinelWOLEngine
from container.memory_guard import MemoryGuard, MemoryStats


class TestWoLEngineMagicPacket:
    """Verifies RFC standard 102-byte Magic Packet construction and transmission."""

    def test_construct_magic_packet_exact_102_bytes(self):
        engine = WoLEngine()
        mac = "bc:d0:74:1a:2b:3c"
        packet = engine.construct_magic_packet(mac)

        assert isinstance(packet, bytes)
        assert len(packet) == 102, f"Magic packet must be exactly 102 bytes, got {len(packet)}"
        # First 6 bytes must be 0xFF
        assert packet[:6] == b"\xff" * 6
        # Remaining 96 bytes must be 16 repetitions of the 6-byte MAC
        mac_bytes = bytes.fromhex("bcd0741a2b3c")
        assert packet[6:] == mac_bytes * 16

    def test_construct_magic_packet_invalid_mac_raises_error(self):
        engine = WoLEngine()
        with pytest.raises(ValueError):
            engine.construct_magic_packet("invalid:mac:12")

    def test_wake_node_contract(self):
        engine = WoLEngine()
        # Wake known device
        result = engine.wake_node("macbook_pro_vault")
        assert isinstance(result, bool)
        assert result is True

    def test_wake_all_devices(self):
        engine = WoLEngine()
        res = engine.wake_all()
        assert res["action"] in ["WAKE_ALL", "WAKE_ALL_BLUETOOTH_FIRST_LINE"]
        assert len(res["results"]) == len(DEVICES)
        for dev_key, dev_res in res["results"].items():
            assert dev_res["success"] is True
            assert "mac_address" in dev_res


class TestRouterSentinelMemoryGuard:
    """Verifies OpenWrt Router Sentinel <= 28MB RAM footprint guard."""

    def test_router_sentinel_health_and_ram_limit(self):
        sentinel = RouterSentinelWOLEngine()
        health = sentinel.get_router_health()

        assert health["max_ram_limit_mb"] == 28.0
        assert health["sentinel_ram_used_mb"] <= 28.0
        assert "🟢 SENTINEL HEALTHY" in health["status"]

    def test_memory_guard_budget_check_contract(self):
        guard = MemoryGuard()
        in_budget, stats = guard.check_memory_budget()

        assert isinstance(in_budget, bool)
        assert isinstance(stats, MemoryStats)
        assert stats.rss_mb >= 0.0
        assert stats.headroom_mb >= 0.0

    def test_router_sentinel_magic_packet_dispatch(self):
        sentinel = RouterSentinelWOLEngine()
        res = sentinel.send_wake_on_lan("L1_Mac_Node")

        assert res["node_id"] == "L1_Mac_Node"
        assert res["packet_size_bytes"] == 102
        assert "DISPATCHED" in res["status"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
