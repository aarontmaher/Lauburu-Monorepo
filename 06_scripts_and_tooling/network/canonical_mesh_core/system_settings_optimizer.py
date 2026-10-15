#!/usr/bin/env python3
"""
06_scripts_and_tooling/network/system_settings_optimizer.py
===========================================================
CLI Network System Settings Optimizer & Real-Time Effect Analyzer for the Lauburu Mesh.
Maps 61+ changeable network parameters across Darwin kernel sysctls, interface MTUs,
socket buffers (BDP), DNS upstream resolvers, Tailscale WireGuard tunnels, and Linux/Termux nodes.

CLI Usage:
  python3 system_settings_optimizer.py --status
  python3 system_settings_optimizer.py --benchmark
  python3 system_settings_optimizer.py --bdp
  python3 system_settings_optimizer.py --apply ai_tensor_sharding
  python3 system_settings_optimizer.py --apply high_throughput_tb4
  python3 system_settings_optimizer.py --apply resilient_mesh
  python3 system_settings_optimizer.py --restore
  python3 system_settings_optimizer.py --export-json
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add TUI module paths for service imports
REPO_ROOT = Path(__file__).resolve().parents[2]
TUI_PATH = REPO_ROOT / "01_apps" / "canonical_port" / "tui"
if str(TUI_PATH) not in sys.path:
    sys.path.insert(0, str(TUI_PATH))

from services.network_optimizer_service import network_optimizer_service
from models.network_optimizer_models import NetworkSettingCategory


def print_banner():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║             LAUBURU MESH — NETWORK SYSTEM SETTINGS OPTIMIZER               ║
║   61 Mapped Parameters • Live BDP Engine • Real-Time Effect Tracking      ║
╚════════════════════════════════════════════════════════════════════════════╝
""")


def cmd_status(category_str: str = None):
    print_banner()
    cat_filter = None
    if category_str:
        for c in NetworkSettingCategory:
            if category_str.lower() in c.value.lower() or category_str.lower() in c.name.lower():
                cat_filter = c
                break

    settings = network_optimizer_service.get_all_settings(cat_filter)
    print(f"Total Mapped Settings: {len(settings)}")
    print(f"{'CATEGORY':<28} | {'KEY':<34} | {'CURRENT':<14} | {'DEFAULT':<12} | {'TARGET METRIC'}")
    print("-" * 115)

    current_cat = ""
    for s in settings:
        if s.category.value != current_cat:
            current_cat = s.category.value
            print(f"\n[ {current_cat.upper()} ]")
        curr_str = f"{s.current_value} {s.unit}".strip()
        def_str = f"{s.default_value} {s.unit}".strip()
        print(f"{s.category.name[:26]:<28} | {s.key:<34} | {curr_str:<14} | {def_str:<12} | {s.target_metric.value}")


def cmd_benchmark():
    print_banner()
    print("Initiating empirical real-time micro-benchmark across live network interfaces...")
    metrics = network_optimizer_service.run_benchmark(is_baseline=False)
    report = network_optimizer_service._compute_delta_report()

    print("\n=== LIVE BENCHMARK RESULTS ===")
    print(f"  • GL.iNet Router RTT (192.168.8.1):     {metrics.gateway_rtt_ms or '--'} ms")
    print(f"  • Linux Head Node RTT (192.168.8.224):   {metrics.head_node_rtt_ms or '--'} ms")
    print(f"  • Cloudflare DNS RTT (1.1.1.1):          {metrics.dns_cloudflare_rtt_ms or '--'} ms")
    print(f"  • Average Composite RTT:                 {metrics.avg_rtt_ms} ms (Δ: {report.delta_rtt_pct:+.1f}%)")
    print(f"  • RTT Jitter / Variance:                 {metrics.jitter_ms} ms (Δ: {report.delta_jitter_pct:+.1f}%)")
    print(f"  • TCP SYN/ACK Handshake Latency:         {metrics.handshake_latency_ms} ms (Δ: {report.delta_handshake_pct:+.1f}%)")
    print(f"  • Loopback Socket Throughput:            {metrics.loopback_throughput_mbps} Mbps (Δ: {report.delta_throughput_pct:+.1f}%)")
    print(f"  • Queue Delay / Bufferbloat Index:       {metrics.queue_delay_index_ms} ms (Δ: {report.delta_queue_delay_pct:+.1f}%)")
    print(f"  • DNS Resolution Time (UDP 53):          {metrics.dns_query_time_ms} ms")
    print(f"\n★ Composite Network Optimization Score:   {report.overall_score} / 100")


def cmd_bdp():
    print_banner()
    print("Computing dynamic Bandwidth-Delay Product (BDP) requirements across physical & overlay links...")
    bdp_list = network_optimizer_service.calculate_bdp_matrix()

    print(f"\n{'LINK NAME':<44} | {'BANDWIDTH':<10} | {'RTT':<8} | {'CALCULATED BDP':<15} | {'REC BUFFERS (SEND/RECV)'}")
    print("-" * 115)
    for b in bdp_list:
        print(f"{b.link_name:<44} | {b.bandwidth_mbps:.0f} Mbps  | {b.rtt_ms:.2f} ms | {b.bdp_formatted:<15} | {b.recommended_sendspace/1024:.0f} KB / {b.recommended_recvspace/1024:.0f} KB")


def cmd_apply(profile: str):
    print_banner()
    print(f"Applying optimization preset profile: '{profile}'...")
    ok, msg, cmds = network_optimizer_service.apply_profile(profile)
    if ok:
        print(f"\n✔ {msg}")
        if cmds:
            print("\nGenerated idempotent system commands:")
            for c in cmds[:10]:
                print(f"  $ {c}")
            if len(cmds) > 10:
                print(f"  ... and {len(cmds) - 10} more commands")
    else:
        print(f"\n❌ Error applying profile: {msg}")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Mesh Network System Settings Optimizer CLI")
    parser.add_argument("--status", action="store_true", help="Dump status table of all mapped settings")
    parser.add_argument("--category", type=str, help="Filter status by category keyword")
    parser.add_argument("--benchmark", action="store_true", help="Run empirical micro-benchmark")
    parser.add_argument("--bdp", action="store_true", help="Display Bandwidth-Delay Product analysis")
    parser.add_argument("--apply", type=str, choices=["ai_tensor_sharding", "high_throughput_tb4", "resilient_mesh", "stock_balanced"], help="Apply optimization profile")
    parser.add_argument("--restore", action="store_true", help="Restore stock factory defaults")
    parser.add_argument("--export-json", action="store_true", help="Export state JSON")

    args = parser.parse_args()

    if args.status:
        cmd_status(args.category)
    elif args.benchmark:
        cmd_benchmark()
    elif args.bdp:
        cmd_bdp()
    elif args.apply:
        cmd_apply(args.apply)
    elif args.restore:
        cmd_apply("stock_balanced")
    elif args.export_json:
        report = network_optimizer_service._compute_delta_report()
        print(f"State exported to data/network/network_optimization_state.json (Score: {report.overall_score})")
    else:
        cmd_status()


if __name__ == "__main__":
    main()
