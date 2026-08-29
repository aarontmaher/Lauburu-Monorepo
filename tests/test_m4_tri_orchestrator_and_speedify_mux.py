#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_m4_tri_orchestrator_and_speedify_mux.py
=================================================
Dedicated Comprehensive Test Suite for Milestone 4 (M4):
- Tri-Orchestrator AI Debate between dual Qwen-3.8Max agents across 3 focus domains.
- 4-turn deliberative state machine & 3-judge judicial scoring council across 5 pillars.
- Atomic dual-vault serialization via TriVaultSink (Obsidian Vault & PySpark LoRA Datasets).
- Custom Open-Source Speedify Channel Bonding: 44-byte binary wire framing ('SPDF'/'LAUB').
- O(1) static 1024-slot circular ring buffer reassembly with 2.0ms playout timer tick.
- Single-port protocol multiplexer routing SSH, HTTP/WS, gRPC, and RPC streams on Port 443/4000.
"""

import os
import sys
import json
import time
import zlib
import struct
import tempfile
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Add paths to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [
    REPO_ROOT,
    REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src",
    REPO_ROOT / "04_data_and_memory",
    REPO_ROOT / "05_agents_and_swarms" / "tri_orchestrator",
    REPO_ROOT / "05_agents_and_swarms" / "tools",
    REPO_ROOT / "06_scripts_and_tooling" / "network",
]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from qwen_tri_orchestrator_debate import (
    QwenTriOrchestratorDebateEngine,
    DebateConsensusAccord,
    DebateTurn,
    QWEN_AGENTS,
    DEBATE_DOMAINS,
    run_all_qwen_debates,
)
from continuous_arena_grader import (
    TriOrchestratorBlindGrader,
    ContinuousArenaGrader,
)
from tri_vault_sink import (
    TriVaultSink,
    verify_zero_mock_compliance,
    check_storage_health,
)
from custom_opensource_speedify_mux import (
    pack_speedify_frame,
    unpack_speedify_frame,
    StaticRingBufferReassembler,
    SinglePortProtocolMultiplexer,
    HEADER_FORMAT_44B,
    HEADER_SIZE_44B,
    HEADER_MAGIC_SPDF,
    HEADER_MAGIC_LAUB,
    PHYSICAL_LINKS,
    PROTOCOL_TARGETS,
)
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    atomic_save_canonical_ledger,
)


# ===========================================================================
# 1. Tri-Orchestrator AI Debate & 3-Judge Council Tests
# ===========================================================================

class TestQwenTriOrchestratorDebate:
    """Validates multi-turn Qwen-3.8Max AI debates across the 3 required domains."""

    @pytest.fixture
    def isolated_workspace(self, tmp_path):
        data_dir = tmp_path / "data"
        lora_dir = tmp_path / "lora_datasets"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"
        data_dir.mkdir(parents=True, exist_ok=True)
        lora_dir.mkdir(parents=True, exist_ok=True)
        obsidian_dir.mkdir(parents=True, exist_ok=True)

        engine_src = CanonicalAILeaderboardEngine()
        initial_ledger = engine_src.get_canonical_leaderboard(persist=False)
        ledger_path = data_dir / "canonical_ai_leaderboard.json"
        with open(ledger_path, "w", encoding="utf-8") as f:
            json.dump(initial_ledger, f, indent=2)

        return {
            "root": tmp_path,
            "ledger_path": ledger_path,
            "lora_dir": lora_dir,
            "obsidian_dir": obsidian_dir,
        }

    def test_multi_turn_debate_all_three_domains(self, isolated_workspace):
        """Tests that multi-turn debates execute across all 3 domains with 4 turns each."""
        engine = QwenTriOrchestratorDebateEngine(
            workspace_root=isolated_workspace["root"],
            leaderboard_path=isolated_workspace["ledger_path"],
            lora_dir=isolated_workspace["lora_dir"],
            obsidian_dir=isolated_workspace["obsidian_dir"],
        )

        domains = ["local_ai_architecture", "training_speed_acceleration", "game_engine_latency"]

        for d_key in domains:
            accord = engine.execute_multi_turn_debate(domain_key=d_key)
            assert isinstance(accord, DebateConsensusAccord)
            assert accord.domain == d_key
            assert len(accord.rounds) >= 4, f"Domain {d_key} did not execute 4 turns"

            # Verify turn types
            turn_types = [t.turn_type for t in accord.rounds]
            assert "OPENING_THESIS" in turn_types
            assert "CROSS_EXAMINATION" in turn_types
            assert "TECHNICAL_SYNTHESIS" in turn_types

            # Verify consensus and voting
            assert accord.consensus_alignment_pct >= 90.0
            assert accord.consensus_passed is True
            assert len(accord.top_5_priorities) == 5

            # Verify 5-pillar scores
            for agent_id, scores in accord.judicial_scores.items():
                for pillar in ["syntax", "depth", "economy", "safety", "truth"]:
                    assert pillar in scores
                    assert scores[pillar] >= 90.0

            assert accord.winner_id in QWEN_AGENTS

    def test_three_judge_council_scoring_breakdown(self, isolated_workspace):
        """Verifies 3-judge scoring council weights and consensus mechanics."""
        engine = QwenTriOrchestratorDebateEngine(
            workspace_root=isolated_workspace["root"],
            leaderboard_path=isolated_workspace["ledger_path"],
            lora_dir=isolated_workspace["lora_dir"],
            obsidian_dir=isolated_workspace["obsidian_dir"],
        )

        accord = engine.execute_multi_turn_debate(domain_key="local_ai_architecture")
        voting = accord.voting_ledger

        # Verify all 3 judges voted
        assert "frontier_judge" in voting
        assert "swarm_judge" in voting
        assert "devils_advocate" in voting

        assert voting["frontier_judge"]["vote"] == "RATIFIED"
        assert voting["swarm_judge"]["vote"] == "RATIFIED"
        assert voting["devils_advocate"]["vote"] == "RATIFIED"


# ===========================================================================
# 2. TriVaultSink Atomic Serialization Tests
# ===========================================================================

class TestTriVaultSinkAtomicSerialization:
    """Validates atomic persistence to Obsidian Vault and PySpark LoRA Datasets."""

    @pytest.fixture
    def isolated_sink(self, tmp_path):
        lora_dir = tmp_path / "lora_datasets"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"
        lora_dir.mkdir(parents=True, exist_ok=True)
        obsidian_dir.mkdir(parents=True, exist_ok=True)

        sink = TriVaultSink(
            lora_dir=lora_dir,
            obsidian_dir=obsidian_dir,
            enforce_rule_zero=True
        )
        return {
            "sink": sink,
            "lora_dir": lora_dir,
            "obsidian_dir": obsidian_dir,
        }

    def test_atomic_export_to_all_required_lora_files(self, isolated_sink):
        """Verifies exports to continuous_lora_dataset.jsonl, dpo_router_orchestrator_pairs.jsonl, and sft_router_orchestrator_debate.jsonl."""
        sink = isolated_sink["sink"]
        lora_dir = isolated_sink["lora_dir"]

        trial_record = {
            "trial_id": "test_trial_m4_001",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt": "Evaluate 44-byte binary framing against 120 FPS WebGPU arena latency.",
            "winner_id": "qwen_38_max_flagship",
            "winner_alias": "alpha",
            "judicial_rationale": "Superior 44-byte framing eliminates jitter.",
            "scores": {
                "alpha": {"syntax": 99.0, "depth": 98.0, "economy": 95.0, "safety": 100.0, "truth": 100.0}
            },
            "total_scores": {"alpha": 98.2},
            "pairwise_matches": [],
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
        }

        res = sink.export_trial_to_trivault(trial_record)
        assert res["dpo_exported"] is True
        assert res["sft_exported"] is True
        assert res["obsidian_exported"] is True

        # Verify continuous_lora_dataset.jsonl
        f1 = lora_dir / "continuous_lora_dataset.jsonl"
        assert f1.exists()
        with open(f1, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) >= 1
        assert lines[0]["trial_id"] == "test_trial_m4_001"
        assert lines[0]["meta"]["zero_mock_certified"] is True

        # Verify dpo_router_orchestrator_pairs.jsonl
        f2 = lora_dir / "dpo_router_orchestrator_pairs.jsonl"
        assert f2.exists()
        with open(f2, "r", encoding="utf-8") as f:
            lines2 = [json.loads(l) for l in f if l.strip()]
        assert len(lines2) >= 1

        # Verify sft_router_orchestrator_debate.jsonl
        f3 = lora_dir / "sft_router_orchestrator_debate.jsonl"
        assert f3.exists()
        with open(f3, "r", encoding="utf-8") as f:
            lines3 = [json.loads(l) for l in f if l.strip()]
        assert len(lines3) >= 1
        assert "instruction" in lines3[0]
        assert "thought" in lines3[0]
        assert "messages" in lines3[0]

    def test_obsidian_markdown_note_structure_and_wikilinks(self, isolated_sink):
        """Verifies YAML frontmatter and master Wikilinks in Obsidian debate notes."""
        sink = isolated_sink["sink"]
        obsidian_dir = isolated_sink["obsidian_dir"]

        trial_record = {
            "trial_id": "trial_wikilink_test",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prompt": "Test Wikilinks and frontmatter integrity",
            "winner_id": "qwen_38_math_governor",
            "winner_alias": "beta",
            "judicial_rationale": "Closed-form RAM headroom proven.",
            "scores": {"beta": {"syntax": 99.0, "depth": 98.0, "economy": 95.0, "safety": 100.0, "truth": 100.0}},
            "total_scores": {"beta": 98.2},
            "judge_breakdowns": {
                "beta": {
                    "frontier_judge": {"score": 99.0, "verdict": "VALID_AST"},
                    "swarm_judge": {"score": 98.0, "verdict": "STRONG_CONSENSUS"},
                    "devils_advocate": {"score": 96.0, "verdict": "ROBUST_DEFENSE"},
                }
            },
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
        }

        note_path = sink.export_obsidian_transcript(trial_record)
        assert note_path.exists()

        content = note_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert 'title: "Continuous Arena Trial trial_wikilink_test"' in content
        assert "tags: [arena, debate, tri_orchestrator, lora, zero_mock]" in content
        assert 'winner: "qwen_38_math_governor"' in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content


# ===========================================================================
# 3. Custom Open-Source Speedify Channel Bonding & Framing Tests
# ===========================================================================

class TestSpeedifyChannelBondingAndFraming:
    """Validates 44-byte binary wire framing and multi-link packet striping."""

    def test_44_byte_binary_wire_frame_packing_and_unpacking(self):
        """Verifies exact 44-byte header size, CRC32 verification, and timestamp packing."""
        assert HEADER_SIZE_44B == 44, f"Header size must be 44 bytes, got {HEADER_SIZE_44B}"
        assert HEADER_FORMAT_44B == "!4sIQBBHIIQQ"

        stream_id = 42
        seq_num = 1001
        subflow_id = 0  # TB4 DMA
        payload = b"Speedify MPQUIC Channel Bonding Tensor Matrix Payload"
        flags = 0x01  # FEC
        send_ts = int(time.time() * 1_000_000)

        frame = pack_speedify_frame(
            stream_id=stream_id,
            global_seq_num=seq_num,
            subflow_id=subflow_id,
            payload=payload,
            flags=flags,
            send_timestamp_us=send_ts,
            echo_timestamp_us=12345,
            magic=HEADER_MAGIC_SPDF,
        )

        assert len(frame) == 44 + len(payload)

        # Unpack and verify
        meta, extracted_payload = unpack_speedify_frame(frame)
        assert meta["magic"] == "SPDF"
        assert meta["stream_id"] == stream_id
        assert meta["global_seq_num"] == seq_num
        assert meta["subflow_id"] == subflow_id
        assert meta["flags"] == flags
        assert meta["send_timestamp_us"] == send_ts
        assert meta["echo_timestamp_us"] == 12345
        assert extracted_payload == payload
        assert meta["chunk_crc32"] == (zlib.crc32(payload) & 0xFFFFFFFF)

    def test_frame_unpack_crc_corruption_detection(self):
        """Verifies that frame unpacking detects corrupted payload bytes via CRC32."""
        payload = b"Original uncorrupted tensor buffer"
        frame = pack_speedify_frame(1, 10, 0, payload)

        # Corrupt one byte in the payload
        corrupted_frame = bytearray(frame)
        corrupted_frame[-1] ^= 0xFF

        with pytest.raises(ValueError, match="CRC32 mismatch"):
            unpack_speedify_frame(bytes(corrupted_frame))

    def test_laub_magic_interoperability(self):
        """Verifies both 'SPDF' and 'LAUB' magic bytes are supported."""
        frame_laub = pack_speedify_frame(1, 1, 0, b"LAUB_DATA", magic=HEADER_MAGIC_LAUB)
        meta, data = unpack_speedify_frame(frame_laub)
        assert meta["magic"] == "LAUB"
        assert data == b"LAUB_DATA"


# ===========================================================================
# 4. O(1) Static 1024-Slot Circular Ring Buffer Tests
# ===========================================================================

class TestStaticRingBufferReassembler:
    """Validates the static 1024-slot circular ring buffer for out-of-order reassembly."""

    def test_in_order_insertion_and_drain(self):
        """Verifies sequential in-order packet drainage."""
        reassembler = StaticRingBufferReassembler(capacity=1024)
        for i in range(10):
            assert reassembler.insert(i, f"payload_{i}".encode()) is True

        drained = reassembler.drain_ready()
        assert len(drained) == 10
        for i, (seq, data) in enumerate(drained):
            assert seq == i
            assert data == f"payload_{i}".encode()

        assert reassembler.expected_seq == 10

    def test_out_of_order_reordering(self):
        """Verifies out-of-order packet reordering (e.g. [2, 0, 1])."""
        reassembler = StaticRingBufferReassembler(capacity=1024)

        # Insert seq 2
        reassembler.insert(2, b"pkt_2")
        assert len(reassembler.drain_ready()) == 0  # Blocked waiting for 0

        # Insert seq 0
        reassembler.insert(0, b"pkt_0")
        drained_1 = reassembler.drain_ready()
        assert len(drained_1) == 1
        assert drained_1[0] == (0, b"pkt_0")

        # Insert seq 1 -> Should drain both 1 and 2
        reassembler.insert(1, b"pkt_1")
        drained_2 = reassembler.drain_ready()
        assert len(drained_2) == 2
        assert drained_2[0] == (1, b"pkt_1")
        assert drained_2[1] == (2, b"pkt_2")

    def test_stale_and_overflow_packet_rejection(self):
        """Verifies that stale (already drained) and overflow (beyond capacity) packets are rejected."""
        reassembler = StaticRingBufferReassembler(capacity=1024)
        reassembler.insert(0, b"pkt_0")
        reassembler.drain_ready()

        # Stale seq 0
        assert reassembler.insert(0, b"stale_0") is False
        assert reassembler.metrics["packets_dropped_stale"] == 1

        # Overflow seq (expected_seq + 1024)
        assert reassembler.insert(reassembler.expected_seq + 1024, b"overflow") is False
        assert reassembler.metrics["packets_dropped_overflow"] == 1

    def test_active_playout_timeout_trigger(self):
        """Verifies that missing packets trigger forced playout upon reorder timeout expiration."""
        reassembler = StaticRingBufferReassembler(capacity=1024, reorder_timeout_ms=10.0)
        # Insert packet 1 but miss packet 0
        reassembler.insert(1, b"pkt_1")
        assert len(reassembler.drain_ready()) == 0

        # Wait for timeout (15ms > 10ms)
        time.sleep(0.02)
        drained = reassembler.drain_ready()
        assert len(drained) == 1
        assert drained[0] == (1, b"pkt_1")
        assert reassembler.metrics["forced_playouts_timeout"] == 1


# ===========================================================================
# 5. Single-Port Protocol Multiplexer Tests
# ===========================================================================

class TestSinglePortProtocolMultiplexer:
    """Validates preamble and protocol sniffing for single-port 443/4000 demuxing."""

    def test_protocol_identification_all_types(self):
        """Verifies correct protocol detection across SSH, HTTP, gRPC, llama.cpp RPC, and Speedify framing."""
        mux = SinglePortProtocolMultiplexer()

        # SSH
        assert mux.identify_protocol(b"SSH-2.0-OpenSSH_9.0\r\n") == "ssh"
        assert mux.identify_protocol(b"SSH-1.99-OpenSSH\r\n") == "ssh"

        # HTTP / WS
        assert mux.identify_protocol(b"GET /api/v1/telemetry HTTP/1.1\r\n") == "http"
        assert mux.identify_protocol(b"POST /api/v1/debate HTTP/1.1\r\n") == "http"
        assert mux.identify_protocol(b"PUT /api/v1/stream HTTP/1.1\r\n") == "http"
        assert mux.identify_protocol(b"HEAD /index.html HTTP/1.1\r\n") == "http"

        # gRPC / HTTP/2
        assert mux.identify_protocol(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n") == "grpc"
        assert mux.identify_protocol(b"\x00\x00\x12\x04\x00\x00\x00\x00\x00") == "grpc"

        # llama.cpp RPC
        assert mux.identify_protocol(b"GGML_RPC_TENSOR_SHARD") == "llama_rpc"
        assert mux.identify_protocol(b"RPC_SET_TENSOR_BUFFER") == "llama_rpc"

        # Speedify 44B Frame
        spdf_frame = pack_speedify_frame(1, 0, 0, b"TEST", magic=HEADER_MAGIC_SPDF)
        assert mux.identify_protocol(spdf_frame) == "speedify_bond"

        laub_frame = pack_speedify_frame(1, 0, 0, b"TEST", magic=HEADER_MAGIC_LAUB)
        assert mux.identify_protocol(laub_frame) == "speedify_bond"

    def test_dynamic_weighting_cycle_execution(self):
        """Verifies 3-algorithm dynamic link weighting cycle and report generation."""
        mux = SinglePortProtocolMultiplexer()
        report = mux.run_dynamic_weighting_cycle()

        assert report["status"] == "SPEEDIFY_CHANNEL_BONDING_OPTIMAL"
        assert report["bonded_links"] == 4
        assert "dynamic_link_weights" in report
        assert "Thunderbolt 4 DMA" in report["dynamic_link_weights"]
        assert report["aggregate_throughput_gbps"] == 44.0
        assert report["ring_buffer_slots"] == 1024

    def test_multi_link_striping_benchmark_e2e(self):
        """Verifies end-to-end multi-link striping benchmark with 100% CRC32 verification."""
        mux = SinglePortProtocolMultiplexer()
        bench_res = mux.benchmark_multi_link_striping(payload_size_mb=5)

        assert bench_res["status"] == "SPEEDIFY_BENCHMARK_SUCCESS"
        assert bench_res["payload_size_mb"] == 5
        assert bench_res["header_size_bytes"] == 44
        assert bench_res["ring_buffer_metrics"]["packets_drained_in_order"] == bench_res["total_chunks"]
        assert bench_res["throughput_mbps"] > 1000.0
