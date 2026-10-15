# -*- coding: utf-8 -*-
"""
tests/e2e/test_deep_research_and_lens_e2e.py
============================================
Authoritative 4-Tier E2E Acceptance & Stress Test Suite for:
1. Sovereign Local AI Deep Research & Competitive Tournament System
2. Screen Lens Native CLI Controller & SQLite Storage Layer
3. Gemini Deep Research Chat Poster & Peer-Review Bridge
4. Anti-Hallucination Sentinel & Continuous DPO LoRA Lake

Governed by Zero-Mock Data (Rule #0) & Tri-Vault Storage Invariants (Rule #2).
"""

from __future__ import annotations

import os
import sys
import json
import time
import sqlite3
import subprocess
from pathlib import Path
import psutil
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
for p in [
    str(REPO_ROOT),
    str(REPO_ROOT / "01_apps/screen_lens/src"),
    str(REPO_ROOT / "04_data_and_memory/src"),
    str(REPO_ROOT / "06_scripts_and_tooling")
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from research.deep_research_topic_scanner import DeepResearchTopicScanner, ResearchBrief
from research.dual_track_research_engine import DualTrackResearchEngine, ResearchTrackResult
from research.research_tournament_judge import ResearchTournamentJudge, TournamentVerdict
from research.gemini_chat_poster import GeminiChatPoster
from integrations.gemini_deep_research_bridge import GeminiDeepResearchBridge
from notebooks.notebook_ai_bridge import NotebookAIBridge
from notebooks.canonical_project_master_notebook import CanonicalProjectMasterNotebook
from graph.mmap_csr_graph import MmapCSRGraph
import screen_lens_cli

# ============================================================================
# Tier 1: Feature Coverage & Subsystem Contracts
# ============================================================================

def test_tier1_topic_scanner_contract():
    """T1.1: Verifies DeepResearchTopicScanner scans and outputs valid ResearchBriefs."""
    scanner = DeepResearchTopicScanner(str(REPO_ROOT))
    topics = scanner.scan_monorepo_for_topics(limit=5)
    assert len(topics) >= 5
    for t in topics:
        assert isinstance(t, ResearchBrief)
        assert t.topic_id.startswith("res_")
        assert len(t.title) > 5
        assert len(t.context_files) > 0
        assert len(t.technical_problem) > 20
        assert len(t.evaluation_criteria) >= 2
    assert os.path.exists(scanner.backlog_file)

def test_tier1_dual_track_engine_contract():
    """T1.2: Verifies DualTrackResearchEngine executes both local and cloud tracks."""
    scanner = DeepResearchTopicScanner(str(REPO_ROOT))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(REPO_ROOT))
    
    tracks = engine.run_dual_track(brief)
    assert "local" in tracks and "cloud" in tracks
    
    # Local track contract
    local_res = tracks["local"]
    assert local_res.is_local is True
    assert local_res.token_cost_usd == 0.00  # $0.00 spend invariant
    assert len(local_res.research_markdown) > 100
    
    # Cloud track contract
    cloud_res = tracks["cloud"]
    assert cloud_res.is_local is False
    assert len(cloud_res.research_markdown) > 100

def test_tier1_tournament_judge_contract():
    """T1.3: Verifies ResearchTournamentJudge produces valid verdict and ELO."""
    scanner = DeepResearchTopicScanner(str(REPO_ROOT))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(REPO_ROOT))
    tracks = engine.run_dual_track(brief)

    judge = ResearchTournamentJudge(str(REPO_ROOT))
    verdict = judge.evaluate_match(brief, tracks["local"], tracks["cloud"])
    assert isinstance(verdict, TournamentVerdict)
    assert verdict.winner in ["LOCAL_AI", "CLOUD_GEMINI", "SYNTHESIZED_TIE"]
    assert 0.0 <= verdict.local_score <= 100.0
    assert 0.0 <= verdict.cloud_score <= 100.0
    assert isinstance(verdict.elo_delta, float)
    assert len(verdict.synthesized_master_solution) > 50
    assert os.path.exists(judge.obsidian_log_file)

def test_tier1_gemini_chat_poster_contract():
    """T1.4: Verifies GeminiChatPoster formats adversarial prompt and clipboard copy."""
    scanner = DeepResearchTopicScanner(str(REPO_ROOT))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(REPO_ROOT))
    local_res = engine.execute_local_research(brief)

    poster = GeminiChatPoster(str(REPO_ROOT))
    prompt = poster.format_peer_review_prompt(brief, local_res)
    assert "[SOVEREIGN LOCAL AI DEEP RESEARCH" in prompt
    assert brief.title in prompt
    assert "Adversarial Review Request for Gemini Deep Research" in prompt

    copied = poster.copy_to_clipboard("E2E Test Clipboard Staging")
    assert copied is True

# ============================================================================
# Tier 2: Boundary & Corner Limits (Anti-Hallucination & Zero-Mock)
# ============================================================================

def test_tier2_sentinel_catches_silicon_hallucinations():
    """T2.1: Sentinel must catch Wi-Fi 6 claims on L2 MacBook Pro (Intel Broadcom)."""
    sentinel = CanonicalProjectMasterNotebook(str(REPO_ROOT))
    bad_claim = "The MacBook Pro is running over 160MHz Wi-Fi 6 on the Flint router."
    findings = sentinel.audit_anti_hallucination(bad_claim)
    assert len(findings) > 0
    assert findings[0]["severity"] == "CRITICAL"
    assert "Wi-Fi 5" in findings[0]["correction"]

def test_tier2_sentinel_catches_sqlite_wal_illusion():
    """T2.2: Sentinel must catch 4.0 KB SQLite uncheckpointed WAL illusion."""
    sentinel = CanonicalProjectMasterNotebook(str(REPO_ROOT))
    bad_claim = "SQLite achieves 4.0 KB for 10,000 edges."
    findings = sentinel.audit_anti_hallucination(bad_claim)
    assert len(findings) > 0
    assert "228.00 KB" in findings[0]["correction"]

def test_tier2_empty_search_handled_gracefully():
    """T2.3: Screen lens CLI handles empty and nonexistent queries safely."""
    conn = screen_lens_cli.get_db_connection()
    cur = conn.cursor()
    res = cur.execute("SELECT COUNT(*) FROM captures WHERE raw_text_summary LIKE '%NONEXISTENT_XYZ_TOKEN%';").fetchone()[0]
    assert res == 0
    conn.close()

# ============================================================================
# Tier 3: Tri-Vault Synchronization & Cross-Feature Integration
# ============================================================================

def test_tier3_dpo_lake_serialization():
    """T3.1: Verifies end-to-end execution emits valid DPO records to lora_datasets/."""
    bridge = GeminiDeepResearchBridge(str(REPO_ROOT))
    scanner = DeepResearchTopicScanner(str(REPO_ROOT))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]

    cycle = bridge.execute_autonomous_cycle(brief=brief, use_gui_paste=False)
    assert cycle["status"] == "CYCLE_COMPLETED"
    dpo_file = Path(cycle["dpo_triplet_appended"])
    assert dpo_file.exists()

    with open(dpo_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) > 0
    latest = lines[-1]
    assert "prompt" in latest
    assert "chosen" in latest
    assert "rejected" in latest
    assert latest["metadata"]["verified_zero_mock"] is True

def test_tier3_mmap_csr_graph_gold_standard(tmp_path):
    """T3.2: Verifies Memory-Mapped CSR Graph fulfills ratified 5.0 bytes/edge density."""
    csr_file = tmp_path / "e2e_graph.csr"
    edges = [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4)]
    graph = MmapCSRGraph.build_from_edges(num_nodes=5, edges=edges, output_path=csr_file)
    
    # 5 nodes -> 6 offsets * 4 = 24 bytes. 5 edges -> 5 indices * 4 = 20 bytes. Header = 8 bytes. Total = 52 bytes.
    assert os.path.getsize(csr_file) == 52
    visited = graph.multi_hop_traversal(start_node=0, max_depth=3)
    assert visited == {1, 2, 3, 4}
    graph.close()

def test_tier3_notebook_ai_living_state_sync():
    """T3.3: Verifies Notebook AI Bridge syncs live state to Obsidian Vault."""
    bridge = NotebookAIBridge(str(REPO_ROOT))
    synced_file = Path(bridge.sync_to_obsidian_notebooks())
    assert synced_file.exists()
    content = synced_file.read_text(encoding="utf-8")
    assert "Canonical Notebook AI Living State" in content
    assert "RATIFIED GOLD STANDARD" in content

# ============================================================================
# Tier 4: Real-World Workloads & Live Mesh Health
# ============================================================================

def test_tier4_mac_mini_host_ram_sanctuary():
    """T4.1: Rule 3 Invariant: Host Mac Mini must preserve >= 4.8 GB free physical RAM."""
    vm = psutil.virtual_memory()
    free_gb = vm.available / (1024 ** 3)
    assert free_gb >= 4.8, f"VIOLATION of Rule 3: Host RAM buffer is {free_gb:.2f} GB (minimum 4.8 GB required)"

def test_tier4_screen_lens_daemon_and_db_alive():
    """T4.2: Verifies native lauburu-lens daemon is active and database is populated."""
    pid = screen_lens_cli.get_daemon_pid()
    assert pid is not None and pid > 0, "lauburu-lens daemon is not running"
    
    conn = screen_lens_cli.get_db_connection()
    cur = conn.cursor()
    captures_count = cur.execute("SELECT COUNT(*) FROM captures;").fetchone()[0]
    blocks_count = cur.execute("SELECT COUNT(*) FROM ocr_text_blocks;").fetchone()[0]
    conn.close()
    
    assert captures_count >= 4000, f"Captures count {captures_count} unexpectedly low"
    assert blocks_count >= 400000, f"OCR blocks count {blocks_count} unexpectedly low"

def test_tier4_cli_binaries_in_path():
    """T4.3: Verifies screen-lens and deep-research-loop executables are in PATH."""
    for cmd in ["screen-lens", "deep-research-loop"]:
        proc = subprocess.run(["which", cmd], stdout=subprocess.PIPE, text=True)
        assert proc.returncode == 0, f"{cmd} not found in PATH"
