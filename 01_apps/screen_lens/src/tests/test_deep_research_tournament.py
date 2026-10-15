# -*- coding: utf-8 -*-
"""
Test Suite: Deep Research Tournament, Scanner, Judge & Chat Poster
==================================================================
Subsystem: 01_apps/screen_lens/src/tests/test_deep_research_tournament.py
Lauburu Mesh Ecosystem — 2026
"""

import pytest
import sys
import os
import json
from pathlib import Path

root_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.append(str(root_path / "01_apps/screen_lens/src"))
sys.path.append(str(root_path / "06_scripts_and_tooling"))

from research.deep_research_topic_scanner import DeepResearchTopicScanner, ResearchBrief
from research.dual_track_research_engine import DualTrackResearchEngine, ResearchTrackResult
from research.research_tournament_judge import ResearchTournamentJudge
from research.gemini_chat_poster import GeminiChatPoster
from integrations.gemini_deep_research_bridge import GeminiDeepResearchBridge

def test_topic_scanner_monorepo_coverage():
    scanner = DeepResearchTopicScanner(str(root_path))
    topics = scanner.scan_monorepo_for_topics(limit=3)
    assert len(topics) >= 1
    brief = topics[0]
    assert isinstance(brief, ResearchBrief)
    assert brief.topic_id.startswith("res_")
    assert len(brief.context_files) > 0
    assert os.path.exists(scanner.backlog_file)

def test_dual_track_execution():
    scanner = DeepResearchTopicScanner(str(root_path))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(root_path))
    
    local_res = engine.execute_local_research(brief)
    assert isinstance(local_res, ResearchTrackResult)
    assert local_res.is_local is True
    assert local_res.token_cost_usd == 0.00
    assert len(local_res.research_markdown) > 50

    cloud_res = engine.execute_cloud_research(brief)
    assert isinstance(cloud_res, ResearchTrackResult)
    assert cloud_res.is_local is False
    assert len(cloud_res.research_markdown) > 50

def test_tournament_judge_scoring_and_elo():
    scanner = DeepResearchTopicScanner(str(root_path))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(root_path))
    tracks = engine.run_dual_track(brief)

    judge = ResearchTournamentJudge(str(root_path))
    verdict = judge.evaluate_match(brief, tracks["local"], tracks["cloud"])

    assert verdict.winner in ["LOCAL_AI", "CLOUD_GEMINI", "SYNTHESIZED_TIE"]
    assert 0.0 <= verdict.local_score <= 100.0
    assert 0.0 <= verdict.cloud_score <= 100.0
    assert isinstance(verdict.elo_delta, float)
    assert os.path.exists(judge.obsidian_log_file)

def test_gemini_chat_poster_formatting():
    scanner = DeepResearchTopicScanner(str(root_path))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]
    engine = DualTrackResearchEngine(str(root_path))
    local_res = engine.execute_local_research(brief)

    poster = GeminiChatPoster(str(root_path))
    prompt = poster.format_peer_review_prompt(brief, local_res)
    assert "[SOVEREIGN LOCAL AI DEEP RESEARCH" in prompt
    assert brief.title in prompt
    assert "Adversarial Review Request" in prompt

    copied = poster.copy_to_clipboard("test clipboard")
    assert copied is True

def test_end_to_end_autonomous_cycle():
    bridge = GeminiDeepResearchBridge(str(root_path))
    scanner = DeepResearchTopicScanner(str(root_path))
    brief = scanner.scan_monorepo_for_topics(limit=1)[0]

    res = bridge.execute_autonomous_cycle(brief=brief, use_gui_paste=False)
    assert res["status"] == "CYCLE_COMPLETED"
    assert res["tournament_winner"] in ["LOCAL_AI", "CLOUD_GEMINI", "SYNTHESIZED_TIE"]
    assert os.path.exists(res["dpo_triplet_appended"])

    # Verify DPO file contents
    with open(res["dpo_triplet_appended"]) as f:
        records = [json.loads(line) for line in f if line.strip()]
    assert len(records) > 0
    latest = records[-1]
    assert "prompt" in latest
    assert "chosen" in latest
    assert "rejected" in latest
    assert latest["metadata"]["verified_zero_mock"] is True
