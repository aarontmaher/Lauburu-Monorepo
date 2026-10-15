#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Research Autonomous Runner & Continuous Tournament Daemon
=============================================================
Subsystem: 06_scripts_and_tooling/deep_research_autonomous_runner.py
Lauburu Mesh Ecosystem — 2026

CLI controller and background loop for autonomous deep research:
1. Scans monorepo for architectural bottlenecks.
2. Runs parallel Dual-Track deep research (Local Qwen 3.8 Max vs Gemini 3.8 Flash).
3. Evaluates Head-to-Head Tournament with Bradley-Terry ELO updates.
4. Posts research to Gemini Deep Research chat for adversarial critique.
5. Streams DPO training triplets into the LoRA data lake.
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add paths
root_path = Path("/Volumes/Lauburu-Monorepo")
for p in [
    str(root_path),
    str(root_path / "01_apps/screen_lens"),
    str(root_path / "01_apps/screen_lens/src"),
    str(root_path / "06_scripts_and_tooling")
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from research.deep_research_topic_scanner import DeepResearchTopicScanner
from research.dual_track_research_engine import DualTrackResearchEngine
from research.research_tournament_judge import ResearchTournamentJudge
from research.gemini_chat_poster import GeminiChatPoster
from integrations.gemini_deep_research_bridge import GeminiDeepResearchBridge

def cmd_scan(args):
    scanner = DeepResearchTopicScanner(str(root_path))
    topics = scanner.scan_monorepo_for_topics(limit=args.limit)
    print("=" * 70)
    print(f"🔬 LAUBURU DEEP RESEARCH TOPIC SCANNER ({len(topics)} Topics Identified)")
    print("=" * 70)
    for i, t in enumerate(topics, 1):
        print(f"\n{i}. [{t.topic_id}] {t.title}")
        print(f"   Domain: {t.domain}")
        print(f"   Files : {', '.join(t.context_files)}")
        print(f"   Issue : {t.technical_problem[:120]}...")
    print("=" * 70)

def cmd_run(args):
    bridge = GeminiDeepResearchBridge(str(root_path))
    scanner = DeepResearchTopicScanner(str(root_path))
    topics = scanner.scan_monorepo_for_topics(limit=5)
    
    target_topic = None
    if args.topic:
        for t in topics:
            if args.topic.lower() in t.title.lower() or args.topic in t.topic_id:
                target_topic = t
                break
    if not target_topic:
        target_topic = topics[0]

    print("=" * 70)
    print(f"🚀 EXECUTING DEEP RESEARCH CYCLE: {target_topic.title}")
    print("=" * 70)
    res = bridge.execute_autonomous_cycle(brief=target_topic, use_gui_paste=args.gui_paste)
    print(f"\n🏆 Tournament Winner : {res['tournament_winner']}")
    print(f"📊 Local Score       : {res['local_score']}/100 (Qwen 3.8 Max)")
    print(f"📊 Cloud Score       : {res['cloud_score']}/100 (Gemini 3.8 Flash)")
    print(f"📈 Bradley-Terry ELO : +{res['elo_delta']} pts")
    print(f"💬 Peer Review Post  : {res['submission_channel']}")
    print(f"📁 DPO Dataset Lake  : {res['dpo_triplet_appended']}")
    print("=" * 70)

def cmd_tournament(args):
    scanner = DeepResearchTopicScanner(str(root_path))
    engine = DualTrackResearchEngine(str(root_path))
    judge = ResearchTournamentJudge(str(root_path))
    topics = scanner.scan_monorepo_for_topics(limit=args.limit)
    
    print("=" * 70)
    print(f"⚔️ DEEP RESEARCH TOURNAMENT SWEEP ({len(topics)} Matches)")
    print("=" * 70)
    
    local_wins, cloud_wins, ties = 0, 0, 0
    for i, t in enumerate(topics, 1):
        print(f"\n[Match {i}/{len(topics)}] {t.title}")
        tracks = engine.run_dual_track(t)
        verdict = judge.evaluate_match(t, tracks["local"], tracks["cloud"])
        print(f"  -> Winner: {verdict.winner} (Local: {verdict.local_score} | Cloud: {verdict.cloud_score}) | ELO: +{verdict.elo_delta}")
        if verdict.winner == "LOCAL_AI":
            local_wins += 1
        elif verdict.winner == "CLOUD_GEMINI":
            cloud_wins += 1
        else:
            ties += 1

    print("\n" + "=" * 70)
    print(f"🏆 TOURNAMENT RESULTS: Local Wins: {local_wins} | Cloud Wins: {cloud_wins} | Ties: {ties}")
    print("=" * 70)

def cmd_daemon(args):
    print(f"🔄 Starting Deep Research Daemon (Interval: {args.interval}s)...")
    bridge = GeminiDeepResearchBridge(str(root_path))
    scanner = DeepResearchTopicScanner(str(root_path))
    
    while True:
        try:
            topics = scanner.scan_monorepo_for_topics(limit=5)
            # Pick a topic round-robin based on current time
            idx = int(time.time() // args.interval) % len(topics)
            topic = topics[idx]
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running cycle for: {topic.title}")
            res = bridge.execute_autonomous_cycle(brief=topic, use_gui_paste=False)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Finished: Winner={res['tournament_winner']} | ELO=+{res['elo_delta']}")
        except Exception as e:
            print(f"Daemon error: {e}")
        time.sleep(args.interval)

def main():
    parser = argparse.ArgumentParser(
        description="Lauburu Autonomous Deep Research Controller & Tournament Engine",
        prog="deep-research-loop"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan codebase for prioritized research topics")
    p_scan.add_argument("-n", "--limit", type=int, default=5, help="Number of topics to scan")
    p_scan.set_defaults(func=cmd_scan)

    # run
    p_run = subparsers.add_parser("run", help="Execute single deep research cycle and tournament")
    p_run.add_argument("-t", "--topic", type=str, default=None, help="Filter by topic title/ID")
    p_run.add_argument("--gui-paste", action="store_true", help="Paste directly into Gemini.app chat window")
    p_run.set_defaults(func=cmd_run)

    # tournament
    p_tourn = subparsers.add_parser("tournament", help="Run tournament sweep across all identified topics")
    p_tourn.add_argument("-n", "--limit", type=int, default=3, help="Number of matches to run")
    p_tourn.set_defaults(func=cmd_tournament)

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run continuous background research loop")
    p_daemon.add_argument("--interval", type=int, default=1800, help="Interval in seconds between research runs")
    p_daemon.set_defaults(func=cmd_daemon)

    args = parser.parse_args()
    if not args.command:
        # Default action: run scan
        class Dummy:
            limit = 5
        cmd_scan(Dummy())
    else:
        args.func(args)

if __name__ == "__main__":
    main()
