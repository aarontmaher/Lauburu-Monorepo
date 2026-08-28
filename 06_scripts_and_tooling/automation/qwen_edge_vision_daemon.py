#!/usr/bin/env python3
"""
⚡ Qwen2.5-VL-7B Edge Vision Daemon & Benchmark CLI
===================================================
CLI daemon and health manager for the ultra-fast local edge visual fallback
on Apple Silicon Metal Performance Shaders (Port 8084).

Usage:
  python3 06_scripts_and_tooling/automation/qwen_edge_vision_daemon.py --health
  python3 06_scripts_and_tooling/automation/qwen_edge_vision_daemon.py --benchmark
  python3 06_scripts_and_tooling/automation/qwen_edge_vision_daemon.py --audit-frame <path_to_frame>
  python3 06_scripts_and_tooling/automation/qwen_edge_vision_daemon.py --once
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
import time
from pathlib import Path

# Add project root and models directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
MODEL_DIR = REPO_ROOT / "02_ai_models_and_inference" / "models"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(MODEL_DIR))

from qwen_vl_edge_fallback import QwenVLEdgeClient, QwenVLEdgeConfig, QwenVLEdgeFallbackServer
from visual_frame_auditor import MultiTierVisualAuditor, Tier0EdgeVisualAuditor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [QWEN-EDGE-CLI] %(levelname)s - %(message)s"
)
logger = logging.getLogger("QwenEdgeVisionDaemon")


def run_health_check() -> int:
    """Probes Qwen2.5-VL-7B server status and Metal GPU health."""
    server = QwenVLEdgeFallbackServer()
    status = server.get_server_status()
    print(json.dumps(status, indent=2))
    return 0 if status["throughput_sla_met"] and status["host_dynamic_ceiling_compliant"] else 1


def run_benchmark(iterations: int = 5) -> int:
    """Executes throughput and latency benchmark over Apple Silicon Metal MPS."""
    client = QwenVLEdgeClient()
    logger.info(f"Running {iterations} benchmark iterations on Qwen2.5-VL-7B Metal MPS...")
    results = client.benchmark_throughput(num_iterations=iterations)
    print(json.dumps(results, indent=2))
    passed = results["throughput_sla_passed"]
    print(f"\nThroughput SLA (> 40 tok/s): {'PASS' if passed else 'FAIL'} (Measured: {results['mean_throughput_tokens_sec']} tok/s)")
    return 0 if passed else 1


def run_audit(frame_path: str, context: str = "CLI Visual Audit") -> int:
    """Audits a visual frame using the Multi-Tier Visual Auditor."""
    auditor = MultiTierVisualAuditor()
    path = Path(frame_path)
    if not path.exists():
        logger.error(f"Image frame not found at: {frame_path}")
        return 1

    verdict = auditor.run_full_audit(path, context_prompt=context)
    summary = {
        "audit_id": verdict.audit_id,
        "overall_verdict": verdict.overall_verdict,
        "visual_health_score": verdict.overall_visual_health_score,
        "zero_mock_certified": verdict.zero_mock_certified,
        "tier0_latency_ms": verdict.tier0_result.latency_ms,
        "tier0_sla_passed": verdict.tier0_result.sla_passed,
        "escalated_to_tier1": verdict.tier0_result.escalate_to_tier1,
        "escalation_reason": verdict.tier0_result.escalation_reason,
        "bounding_boxes_count": len(verdict.tier0_result.bounding_boxes),
        "lora_trace_persisted": verdict.lora_trace_persisted
    }
    print(json.dumps(summary, indent=2))
    return 0 if verdict.zero_mock_certified else 1


def run_once_cycle() -> int:
    """Executes single end-to-end verification cycle of health, benchmark, and audit."""
    print("=== ⚡ QWEN2.5-VL-7B EDGE VISION DAEMON ONCE CYCLE ===")
    h_code = run_health_check()
    print("\n--- Running Benchmark ---")
    b_code = run_benchmark(iterations=3)
    print("\n--- Running Sample Tier-0 Frame Audit ---")
    sample_frame = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 128).decode("ascii")
    auditor = MultiTierVisualAuditor()
    v = auditor.run_full_audit(sample_frame, context_prompt="Nomad Courier Automated Health Verification Pass")
    print(f"Sample Audit Result: {v.overall_verdict} (Score: {v.overall_visual_health_score}%, Latency: {v.tier0_result.latency_ms}ms)")
    return 0 if (h_code == 0 and b_code == 0 and v.zero_mock_certified) else 1


def main():
    parser = argparse.ArgumentParser(description="Qwen2.5-VL-7B Edge Vision Daemon & Benchmark CLI")
    parser.add_argument("--health", action="store_true", help="Probe server status & VRAM metrics")
    parser.add_argument("--benchmark", action="store_true", help="Execute throughput benchmark")
    parser.add_argument("--iterations", type=int, default=5, help="Number of benchmark iterations")
    parser.add_argument("--audit-frame", type=str, help="Path to image frame for Tier-0 visual audit")
    parser.add_argument("--context", type=str, default="CLI Visual Audit", help="Context prompt for audit")
    parser.add_argument("--once", action="store_true", help="Run a single end-to-end verification cycle")

    args = parser.parse_args()

    if args.health:
        sys.exit(run_health_check())
    elif args.benchmark:
        sys.exit(run_benchmark(args.iterations))
    elif args.audit_frame:
        sys.exit(run_audit(args.audit_frame, args.context))
    elif args.once:
        sys.exit(run_once_cycle())
    else:
        # Default to once cycle
        sys.exit(run_once_cycle())


if __name__ == "__main__":
    main()
