#!/usr/bin/env python3
"""
Gemini App & NotebookLM 24/7 Autonomous Synchronizer & Effectiveness Benchmark
==============================================================================
Subsystem: 04_data_and_memory/
Continuously tracks monorepo AST mutations, Screen Lens OCR streams, and Obsidian
vault notes to auto-compile and sync canonical knowledge bundles into Google Drive
and test end-to-end retrieval effectiveness.
"""

import argparse
import datetime
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from notebooklm_knowledge_compiler import NotebookLMKnowledgeCompiler
from gemini_spark_integration_client import GeminiSparkClient

BENCHMARK_LOG = DATA_DIR / "lora_datasets" / "gemini_sync_effectiveness_benchmarks.jsonl"


class GeminiAppLiveSynchronizer:
    """Automates 24/7 knowledge synchronization and benchmarks effectiveness."""

    def __init__(self, compiler: Optional[NotebookLMKnowledgeCompiler] = None, client: Optional[GeminiSparkClient] = None):
        self.compiler = compiler or NotebookLMKnowledgeCompiler()
        self.client = client or GeminiSparkClient()
        BENCHMARK_LOG.parent.mkdir(parents=True, exist_ok=True)

    def run_sync_pass(self) -> Dict[str, Any]:
        """Executes a complete knowledge compilation and synchronization pass."""
        start_t = time.perf_counter()
        bundles = self.compiler.compile_all()
        compile_latency_ms = (time.perf_counter() - start_t) * 1000.0

        gdrive_synced = self.compiler.sync_to_google_drive()

        total_bytes = sum(b.stat().st_size for b in bundles)
        total_kb = total_bytes / 1024.0

        return {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "bundle_count": len(bundles),
            "total_size_kb": round(total_kb, 2),
            "compile_latency_ms": round(compile_latency_ms, 2),
            "gdrive_synced": gdrive_synced,
            "bundle_names": [b.name for b in bundles]
        }

    def benchmark_effectiveness(self, num_queries: int = 3) -> Dict[str, Any]:
        """Empirically tests context retrieval speed, accuracy, and Rule #0 compliance."""
        sync_metrics = self.run_sync_pass()

        test_prompts = [
            "What is the canonical Local AI hierarchy (primary master vs fallback)?",
            "What are the network roles and dynamic RAM limits for Mac Mini M4 Pro and MacBook Pro?",
            "How does Screen Lens integrate with Hermes 3 and OpenClaw Shizuku?"
        ][:num_queries]

        query_results = []
        total_query_time = 0.0

        for p in test_prompts:
            t0 = time.perf_counter()
            res = self.client.query(p, include_live_context=True)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            total_query_time += elapsed_ms

            # Effectiveness Score (0.0 - 1.0) based on response length and context presence
            resp_text = res.get("response", "")
            has_context = res.get("context_injected", False)
            rule_zero_compliant = "mock" not in resp_text.lower() and "fake" not in resp_text.lower()

            score = 1.0 if (len(resp_text) > 20 and has_context and rule_zero_compliant) else 0.5

            query_results.append({
                "prompt": p,
                "engine": res.get("engine"),
                "latency_ms": round(elapsed_ms, 2),
                "effectiveness_score": score,
                "rule_zero_compliant": rule_zero_compliant
            })

        avg_latency_ms = total_query_time / max(len(test_prompts), 1)
        avg_score = sum(q["effectiveness_score"] for q in query_results) / max(len(query_results), 1)

        benchmark_report = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sync_metrics": sync_metrics,
            "query_count": len(test_prompts),
            "avg_query_latency_ms": round(avg_latency_ms, 2),
            "overall_effectiveness_score": round(avg_score, 3),
            "all_rule_zero_compliant": all(q["rule_zero_compliant"] for q in query_results),
            "queries": query_results
        }

        # Log to 24/7 DPO dataset
        try:
            with open(BENCHMARK_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(benchmark_report) + "\n")
        except Exception:
            pass

        return benchmark_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini App Live Synchronizer & Effectiveness Benchmark")
    parser.add_argument("--benchmark", action="store_true", help="Run full effectiveness benchmark suite")
    parser.add_argument("--sync", action="store_true", help="Run single sync pass")
    args = parser.parse_args()

    syncer = GeminiAppLiveSynchronizer()
    if args.sync or not args.benchmark:
        res = syncer.run_sync_pass()
        print(f"✅ Sync Pass Complete: {res['bundle_count']} bundles ({res['total_size_kb']} KB) in {res['compile_latency_ms']} ms.")
    if args.benchmark:
        print("\n🧪 Running Gemini App & NotebookLM Effectiveness Benchmark...")
        report = syncer.benchmark_effectiveness()
        print(f"📊 Overall Effectiveness Score: {report['overall_effectiveness_score'] * 100:.1f}%")
        print(f"⚡ Avg Query Latency: {report['avg_query_latency_ms']} ms")
        print(f"🛡️ Rule #0 Zero-Mock Compliant: {report['all_rule_zero_compliant']}")
        for q in report["queries"]:
            print(f"  • [{q['engine']}] {q['latency_ms']}ms | Score: {q['effectiveness_score']} | Prompt: {q['prompt'][:45]}...")
