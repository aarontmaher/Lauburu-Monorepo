#!/usr/bin/env python3
"""
06_scripts_and_tooling/edge_chat_rag_agent_sdk.py
=================================================
Monorepo Tooling Forwarder for the Edge Chat, Tri-Vault RAG & Antigravity Agent SDK Suite.
Target: 01_apps/screen_lens/sandbox_evolution/edge_chat_rag_agent_sdk/
=================================================
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path

_SANDBOX_PATH = Path("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/edge_chat_rag_agent_sdk")
if str(_SANDBOX_PATH) not in sys.path:
    sys.path.insert(0, str(_SANDBOX_PATH))

try:
    from edge_chat_engine import EdgeChatEngine, ChatMessage, EdgeChatSession
    from tri_vault_rag_engine import TriVaultRAGEngine
    from antigravity_agent_sdk import Agent, DynamicModelSelector, AutoSubagentCreator
    from specialized_agents import bootstrap_all_specialists
    from loop_autonomous_executor import LoopAutonomousExecutor
except ImportError as e:
    raise ImportError(f"Failed to load edge_chat_rag_agent_sdk from {_SANDBOX_PATH}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Edge Chat, RAG & Antigravity Agent SDK CLI")
    parser.add_argument("--query", "-q", type=str, help="Search Tri-Vault RAG or run direct chat")
    parser.add_argument("--chat", action="store_true", help="Start interactive Edge Chat session")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    parser.add_argument("--rag", action="store_true", help="Run Tri-Vault RAG retrieval")
    parser.add_argument("--hand-off", type=str, choices=["scout", "reverse", "neo", "biometrics"], help="Execute automatic specialist hand-off")
    parser.add_argument("--top-k", type=int, default=3, help="Top K RAG results")
    args = parser.parse_args()

    if args.test:
        from test_edge_chat_rag_agent_sdk import main as run_tests
        run_tests()
        return

    if args.rag and args.query:
        print(f"=== Searching Tri-Vault RAG for: '{args.query}' ===")
        rag = TriVaultRAGEngine()
        hits = rag.search(args.query, top_k=args.top_k)
        for h in hits:
            print(f"- [{h.source_tier}] {h.to_citation()}")
            print(f"  Snippet: {h.content[:160]}...\n")
        return

    if args.hand_off:
        agent = Agent()
        bootstrap_all_specialists(agent)
        mapping = {
            "scout": ("OpenSourceScoutAgent", args.query or "/open-source-software-scout audit and compare SeaweedFS vs MinIO"),
            "reverse": ("ReverseEngineeringAgent", args.query or "/closed-source-reverse-engineering decompile movesense BLE GATT service"),
            "neo": ("NeoBridgeAgent", args.query or "/neo resolve canonical monorepo root"),
            "biometrics": ("BiometricsDSPAgent", args.query or "Process 512Hz ECG window with Pan-Tompkins QRS detector"),
        }
        target_name, task = mapping[args.hand_off]
        print(f"=== Executing Automatic Hand-Off to {target_name} ===")
        res = agent.hand_off(target_name, task)
        print(f"Status: {res.status} | Latency: {res.latency_ms} ms | SHA: {res.hand_off_sha[:16]}")
        print(f"Result: {json.dumps(res.result, indent=2)}")
        return

    # Default: Run test suite or display usage
    if args.query:
        agent = Agent()
        res = agent.chat(args.query)
        print(f"[{res.get('model_used', 'Local')}] {res.get('response', '')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
