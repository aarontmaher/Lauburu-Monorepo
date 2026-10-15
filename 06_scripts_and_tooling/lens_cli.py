#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lauburu Screen Lens Sovereign CLI (lens)
========================================
Canonical Root CLI for Lauburu Mesh & Screen Lens Sovereign Ecosystem.
Supports natural language automation, direct command dispatch, and local AI speculative drafting.

Usage:
    lens [options] <request | intent | command>

Examples:
    lens status                         # Run mesh network diagnostics
    lens "screen lens"                  # Show Screen Lens daemon status & stats
    lens captures                       # Display latest OCR screen captures
    lens "query screen terminal"        # Search recent OCR text for keywords
    lens heal                           # Trigger autonomous mesh network healer
    lens "storage health"               # Inspect Tri-Vault storage headroom
    lens ram                            # Show macOS Darwin kernel memory stats
    lens "mesh gui"                     # Launch Sovereign Mesh HUD
    lens --dry-run "speedify test"      # Speculate command without executing
"""

import os
import sys
import json
from pathlib import Path

# Resolve monorepo paths
POSSIBLE_ROOTS = [
    Path(__file__).resolve().parent.parent,
    Path("/Volumes/Lauburu-Monorepo"),
    Path("/Volumes/AI_Projects/Lauburu_Master/Lauburu-Monorepo"),
    Path("/Volumes/Lauburu-Monorepo"),
    Path("/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo"),
    Path.home() / "DFS_UNIFIED/Lauburu-Monorepo",
    Path.home() / "lauburu_sync",
]

for root in POSSIBLE_ROOTS:
    scripts_dir = root / "06_scripts_and_tooling"
    if scripts_dir.exists() and str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    if root.exists() and str(root) not in sys.path:
        sys.path.insert(0, str(root))

try:
    from speculative_cli_data_engine import get_speculative_cli_engine
except ImportError as e:
    print(f"❌ Failed to load Speculative CLI Engine: {e}")
    sys.exit(1)

VERSION = "2.0.0"

HELP_TEXT = f"""👁️  Lauburu Screen Lens Sovereign CLI v{VERSION}
Unified natural language CLI, Neo4j + EmbeddingGemma 2 MRL RAG, 4-Stage Self-Healing,
Rooted Podman & 2TB Storage Orchestrator, Polyglot Go+Python Sharding/Training, and Py-Pi Companion.

Usage:
  lens [options] <natural language request | command>
  ./lens [options] <natural language request | command>

Options:
  -h, --help            Show this help manual and exit
  -v, --version         Show version information and exit
  -n, --dry-run         Draft and analyze command without executing
  --json                Output draft and execution results in JSON format
  --explain             Show detailed speculative reasoning and confidence scores

Common Sovereign Capabilities:
  • 4-Stage Self-Heal   lens heal-cascade
                        lens heal-s20
                        lens movesense-gatt
                        lens "bluetooth serial to kdeconnect ssh"
  • Storage & Podman    lens podman-storage
                        lens "storage health"
                        lens "podman spec"
                        lens "sync storage"
                        lens "model vault"
                        lens ram
  • Cognitive Memory    lens memory
                        lens accounts
                        lens accounts --service drive --json
                        lens accounts --service bigquery --json
                        lens auth status
  • Python & Pi Agents  lens py-pi --task "Inspect mesh storage and memory"
                        lens pi --version
                        lens deps
  • Voice Coder (7B)    lens voice-coder
                        lens voice-coder --voice-action transcribe-and-code --voice-utterance "define check underscore mesh open paren close paren colon return True"
                        lens voice-coder --voice-action stop
  • Junie TB4 Mesh      lens junie-mesh
                        lens junie-mesh --task "Audit and refactor monorepo across Thunderbolt 4 mesh"
  • Go & Py Protocols   lens protocols
                        lens sharding
  • IDE & Antigravity   lens ide
                        lens integrate-ides
                        lens specialists
                        lens specialists --target goland
                        lens specialists --target pycharm
                        lens specialists --target intellij
                        lens specialists --target chromium
                        lens specialists --target bt-serial
                        lens "configure agy and gemini"
                        lens "audit dependencies"
                        lens "boot services"
  • Network Benchmark   lens benchmark-network
                        lens "docker cloudflare vs tailscale"
  • AI Debate & 2x Pool lens debate --topic "Sharding vs TB4"
                        lens ai-debate
  • Qwen 3D VLA & Audit lens vla
                        lens audit-code
  • ELO & Self-Optimize lens elo
                        lens benchmark-70b-100b
                        lens benchmark-heavy
                        lens benchmark
                        lens benchmark-gemma2
                        lens benchmark-sharding
                        lens benchmark-training
                        lens elo-consensus
                        lens self-optimize --model gemma_4_31b --opinion-score 98
                        lens download-model
  • Project Gap Audit   lens review-project
                        lens overview
  • Neo4j & Gemma 2 RAG lens neo4j status
                        lens neo4j schema
                        lens neo4j seed
                        lens cypher "MATCH (n:MeshNode) RETURN n.node_id, n.root_uid"
                        lens embed "Multimodal MRL query" --mrl-dim 256
                        lens ingest --doc-id doc_1 --title "Spec" --text "..."
                        lens rag "How is EmbeddingGemma 2 MRL configured across the mesh?" --mrl-dim 256
  • Root Mesh Execution lens root --target all "id && uname -a"
                        lens root --target L3 "docker ps --filter name=neo4j_mesh"
  • Mesh Status         lens status
                        lens "network test"
                        lens "mesh topology"
                        lens "verify probes"
  • Screen Lens         lens "screen lens"
                        lens "captures"
                        lens "ocr"
                        lens "query screen <term>"
                        lens "screen lens start|stop|restart"
  • Network Healing     lens heal
                        lens "heal network health"
                        lens "resurrect mesh"
  • Cross-Mesh Actuate  lens "automate across network"
                        lens automate-247
                        lens automation-protocol
                        lens "run a 24/7 lens automation training protocol"
  • Local AI Training   lens train
                        lens "train gemini telemetry"
                        lens "train argontelemetry"
  • Hardware & Speedify lens "mesh gui"
                        lens "speedify interfaces"
                        lens "speedify test"
  • Security & Keys     lens "api key"
                        lens "key audit"

Zero-Mock Invariant:
  All telemetry originates from kernel syscalls, hardware probes, Neo4j 5.26.32, Qdrant MRL, and authentic SQLite stores.
"""


def print_help():
    print(HELP_TEXT)


def print_version():
    print(f"Lauburu Screen Lens Sovereign CLI v{VERSION} (Zero-Mock Certified)")


def main():
    args = sys.argv[1:]

    # Handle empty invocation
    if not args:
        print_help()
        sys.exit(0)

    # Intercept top-level help and version flags
    first_arg = args[0].strip().lower()
    if first_arg in ("-h", "--help", "help"):
        print_help()
        sys.exit(0)

    if first_arg in ("-v", "--version", "version"):
        print_version()
        sys.exit(0)

    # Direct subcommand pass-through to Dual-CLI Account Guard + Dual-Account Workspace/GCP Router
    if first_arg in ("accounts", "auth"):
        import subprocess
        if first_arg == "accounts" or "--service" in args or "--json" in args:
            for root in POSSIBLE_ROOTS:
                cand = root / "06_scripts_and_tooling/lens_sovereign_unified_system.py"
                if cand.exists():
                    proc = subprocess.run([sys.executable, str(cand), "accounts"] + args[1:])
                    sys.exit(proc.returncode)
        guard_script = None
        for root in POSSIBLE_ROOTS:
            cand = root / "06_scripts_and_tooling/lauburu_cli_account_guard.py"
            if cand.exists():
                guard_script = cand
                break
        if guard_script:
            sub_args = args[1:] if len(args) > 1 else ["enforce"]
            proc = subprocess.run([sys.executable, str(guard_script)] + sub_args)
            sys.exit(proc.returncode)

    # Direct subcommand pass-through to EmbeddingGemma 2 + Qwen 3D Telemetry/Visual Review & Sharding/Training ELO Benchmark
    benchmark_mode_map = {
        "benchmark": "full",
        "benchmark-gemma2": "gemma2",
        "benchmark-sharding": "sharding",
        "benchmark-training": "training",
        "elo-consensus": "elo",
    }
    if first_arg in benchmark_mode_map:
        import subprocess
        bench_script = None
        for root in POSSIBLE_ROOTS:
            cand = root / "06_scripts_and_tooling/lens_gemma2_qwen3d_elo_benchmark.py"
            if cand.exists():
                bench_script = cand
                break
        if bench_script:
            extra_args = args[1:]
            if "--mode" not in extra_args:
                extra_args = ["--mode", benchmark_mode_map[first_arg]] + extra_args
            proc = subprocess.run([sys.executable, str(bench_script)] + extra_args)
            sys.exit(proc.returncode)

    # Direct subcommand pass-through to Neo4j + EmbeddingGemma 2 + Root Orchestrator
    if first_arg in ("neo4j", "cypher", "embed", "ingest", "rag", "root", "search"):
        import subprocess
        orchestrator_script = None
        for root in POSSIBLE_ROOTS:
            cand = root / "06_scripts_and_tooling/lens_neo4j_gemma2_orchestrator.py"
            if cand.exists():
                orchestrator_script = cand
                break
        if orchestrator_script:
            sub_args = args[1:] if first_arg == "neo4j" else args
            if first_arg == "neo4j" and not sub_args:
                sub_args = ["status"]
            proc = subprocess.run([sys.executable, str(orchestrator_script)] + sub_args)
            sys.exit(proc.returncode)

    # Direct pass-through to `pi` CLI (`@earendil-works/pi-coding-agent`)
    if first_arg == "pi":
        import shutil
        import subprocess
        pi_bin = "/Users/aaron/.local/bin/pi" if os.path.exists("/Users/aaron/.local/bin/pi") else shutil.which("pi")
        if pi_bin and len(args) > 1:
            proc = subprocess.run([pi_bin] + args[1:])
            sys.exit(proc.returncode)
        elif pi_bin:
            proc = subprocess.run([pi_bin, "--version"])
            sys.exit(proc.returncode)

    # Direct subcommand pass-through to Sovereign Unified System Orchestrator
    unified_subcommands = (
        "overview",
        "podman-storage",
        "heal-cascade",
        "heal-s20",
        "tplink-audit",
        "movesense-gatt",
        "memory",
        "py-pi",
        "deps",
        "protocols",
        "sharding",
        "ide",
        "integrate-ides",
        "specialists",
        "deploy-network",
        "sync-network",
        "benchmark-network",
        "review-project",
        "debate",
        "ai-debate",
        "vla",
        "audit-code",
        "elo",
        "self-optimize",
        "download-model",
        "benchmark-70b-100b",
        "benchmark-heavy",
        "voice-coder",
        "junie-mesh",
        "automate-247",
        "automation-protocol",
    )
    specialist_shortcut_targets = {
        "langgo": "goland",
        "goland": "goland",
        "pycharm": "pycharm",
        "intellij": "intellij",
        "chromium": "chromium",
        "bt-serial": "bt-serial",
        "/polyglot-go-bubbletea-specialist": "goland",
        "/polyglot-kotlin-android-specialist": "intellij",
        "/polyglot-c-cpp-specialist": "bt-serial",
        "/polyglot-python-specialist": "pycharm",
        "/polyglot-rust-wgpu-specialist": "chromium",
        "/polyglot-typescript-web-specialist": "chromium",
    }
    slash_workflow_triggers = {
        "/screen-lens-sovereign",
        "/continus-lens-practice-automation",
        "/boost",
        "/teamwork-preview",
        "boost",
        "teamwork-preview",
        "--boost",
        "--teamwork-preview",
    }
    if (
        first_arg in unified_subcommands
        or (first_arg in specialist_shortcut_targets and "-n" not in args and "--dry-run" not in args)
        or (first_arg in slash_workflow_triggers and "-n" not in args and "--dry-run" not in args)
    ):
        import subprocess
        unified_script = None
        for root in POSSIBLE_ROOTS:
            cand = root / "06_scripts_and_tooling/lens_sovereign_unified_system.py"
            if cand.exists():
                unified_script = cand
                break
        if unified_script:
            if first_arg in specialist_shortcut_targets:
                target_val = specialist_shortcut_targets[first_arg]
                norm_args = ["specialists", "--target", target_val] + [
                    a for a in args[1:] if a != "--target"
                ]
                proc = subprocess.run([sys.executable, str(unified_script)] + norm_args)
            elif first_arg in slash_workflow_triggers:
                norm_args = ["automate-247"]
                for a in args:
                    al = a.strip().lower()
                    if al in ("/screen-lens-sovereign", "screen-lens-sovereign", "/continus-lens-practice-automation"):
                        continue
                    elif al in ("/boost", "boost", "--boost"):
                        if "--boost" not in norm_args:
                            norm_args.append("--boost")
                    elif al in ("/teamwork-preview", "teamwork-preview", "--teamwork-preview"):
                        if "--teamwork-preview" not in norm_args:
                            norm_args.append("--teamwork-preview")
                    else:
                        norm_args.append(a)
                proc = subprocess.run([sys.executable, str(unified_script)] + norm_args)
            else:
                proc = subprocess.run([sys.executable, str(unified_script)] + args)
            sys.exit(proc.returncode)


    # Parse CLI modifier options
    dry_run = False
    json_output = False
    explain = False
    clean_args = []

    for arg in args:
        if arg in ("-n", "--dry-run"):
            dry_run = True
        elif arg == "--json":
            json_output = True
        elif arg == "--explain":
            explain = True
        elif arg in ("-h", "--help"):
            print_help()
            sys.exit(0)
        elif arg in ("-v", "--version"):
            print_version()
            sys.exit(0)
        else:
            clean_args.append(arg)

    if not clean_args:
        print_help()
        sys.exit(0)

    intent = " ".join(clean_args)
    engine = get_speculative_cli_engine()

    if dry_run:
        draft = engine.drafter.draft(intent)
        draft_dict = draft.to_dict()
        if json_output:
            print(json.dumps(draft_dict, indent=2))
        else:
            print(f"👁️  Lens Analysis for: '{intent}' (Dry Run)")
            print(f"• Command Speculated : {draft.speculative_command} {' '.join(draft.suggested_args)}")
            print(f"• Drafter Model      : {draft.drafter_model}")
            print(f"• Confidence Score   : {draft.confidence_score:.2f}")
            print(f"• Safety Rating      : {draft.safety_rating}")
            print(f"• Rationale          : {draft.rationale}")
            print(f"• Latency            : {draft.latency_ms:.2f}ms")
        sys.exit(0)

    if not json_output:
        print(f"👁️  Lens analyzing request: '{intent}'")

    result = engine.speculate_and_execute(
        intent_or_command=intent,
        execute_if_safe=True,
        timeout_sec=60.0,
    )

    draft = result.get("draft", {})
    model = draft.get("drafter_model", "Unknown")
    conf = draft.get("confidence_score", 0.0)

    if json_output:
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("executed") and result.get("receipt", {}).get("exit_code", 0) == 0 else 1)

    # Truthful model feedback
    if "Local-Qwen" in model:
        print(f"🧠 Speculated with Local AI ({model}, confidence: {conf:.2f})")
    elif "Deterministic" in model:
        print(f"⚡ Matched deterministic system mapping ({model})")
    elif "Heuristic" in model:
        print(f"ℹ️  Parsed with Heuristic Tokenizer (Local AI offline or fell back, confidence: {conf:.2f})")
    else:
        print(f"🔎 Drafter: {model} (confidence: {conf:.2f})")

    if explain:
        print(f"• Rationale: {draft.get('rationale', 'N/A')}")
        print(f"• Safety   : {draft.get('safety_rating', 'UNKNOWN')}")

    if not result.get("executed"):
        print("\n⚠️  Lens halted execution.")
        print(f"Reason: {result.get('reason')}")
        suggestion = result.get("suggestion")
        if suggestion:
            print(f"💡 Suggestion: {suggestion}")
        if draft.get("speculative_command") and draft.get("speculative_command") != intent:
            print(f"Command Speculated: {draft.get('speculative_command')} {' '.join(draft.get('suggested_args', []))}")
        sys.exit(127)

    receipt = result.get("receipt", {})
    exit_code = receipt.get("exit_code", 0) if receipt else 0
    if exit_code == 0:
        print(f"\n✅ Lens execution succeeded (Exit Code: 0, Latency: {receipt.get('duration_ms', 0.0):.1f}ms).")
    else:
        print(f"\n❌ Lens execution failed (Exit Code: {exit_code}).")

    if receipt:
        stdout = receipt.get("stdout_lines", [])
        stderr = receipt.get("stderr_lines", [])
        if stdout:
            print("Output Snippet:\n" + "\n".join(stdout[:80]))
        if stderr:
            print("Error Snippet:\n" + "\n".join(stderr[:20]))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
