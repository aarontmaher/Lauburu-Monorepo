#!/usr/bin/env python3
"""
Unit tests for Cross-Chat Swarm Harmonizer & Mesh Unison Coordinator.
Verifies that swarms across parallel chat sessions synchronize without resource collisions.
"""

import os
import json
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys_path = REPO_ROOT / "05_agents_and_swarms"
if str(sys_path) not in os.sys.path:
    os.sys.path.insert(0, str(sys_path))

from cross_chat_swarm_harmonizer import CrossChatSwarmHarmonizer, CHAT_A_ID, CHAT_B_ID


class TestCrossChatSwarmHarmonizer:
    """Validates cross-chat swarm synchronization and collision avoidance."""

    def test_harmonizer_initialization_and_active_chats(self):
        """Verifies that both Chat A and Chat B are tracked with proper roles."""
        harmonizer = CrossChatSwarmHarmonizer()
        assert CHAT_A_ID in harmonizer.state["active_chats"]
        assert CHAT_B_ID in harmonizer.state["active_chats"]
        assert "Macro Architecture" in harmonizer.state["active_chats"][CHAT_A_ID]["alias"]
        assert "Hierarchical Swarms" in harmonizer.state["active_chats"][CHAT_B_ID]["alias"]

    def test_audit_active_ports(self):
        """Verifies that port monitoring correctly checks critical system endpoints."""
        harmonizer = CrossChatSwarmHarmonizer()
        ports = harmonizer.audit_active_ports()
        port_numbers = [p["port"] for p in ports]
        assert 4000 in port_numbers
        assert 8081 in port_numbers
        assert 8082 in port_numbers
        assert 18802 in port_numbers
        assert 4004 in port_numbers  # Chat B Knowledge Hub

    def test_cross_pollinate_datasets(self):
        """Verifies that datasets from both chats are indexed into the total count."""
        harmonizer = CrossChatSwarmHarmonizer()
        total_dpo = harmonizer.cross_pollinate_datasets()
        assert total_dpo > 2000, f"Expected >2000 DPO pairs, got {total_dpo}"

    def test_execute_unison_cycle(self):
        """Verifies that a complete harmonization cycle executes successfully."""
        harmonizer = CrossChatSwarmHarmonizer()
        res = harmonizer.execute_unison_cycle()
        assert res["status"] == "SWARMS_IN_UNISON"
        assert res["ports_online"] >= 5
        assert res["total_cross_chat_dpo_pairs"] > 2000
        # Verify markdown report was generated in Obsidian Vault
        report_file = REPO_ROOT / "obsidian_vault" / "05_SWARMS" / "CROSS_CHAT_SWARM_SYNCHRONIZATION_MATRIX.md"
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "Chat A" in content
        assert "Chat B" in content
