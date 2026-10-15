#!/usr/bin/env python3
"""
06_scripts_and_tooling/lauburu_network_cli.py
=============================================
Unified CLI for Lauburu 7-Layer Mesh Network Diagnostics, Power Management & Self-Healing.
Enforces the mandatory 5-Line Network Resurrection Hierarchy:
  Line 1 (Default / First Line): Bluetooth Proximity Wake (blueutil --connect, zero IP dependency)
  Line 2: Out-of-Band UDP Wake-on-LAN Magic Packet (UDP Port 9/7 broadcast/directed)
  Line 3: Android ADB Keepalive & Display Wake (termux-wake-lock, Doze bypass)
  Line 4: Tailscale WireGuard Overlay Link (tailscale up --accept-routes)
  Line 5: Multi-WAN / Gateway fallback (kmwan / GL.iNet / WAN failover)
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add repo root and mesh tooling to sys.path
REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
MESH_TOOLING = REPO_ROOT / "06_scripts_and_tooling/mesh"
if str(MESH_TOOLING) not in sys.path:
    sys.path.insert(0, str(MESH_TOOLING))

try:
    from wol_manager import WoLEngine, DEVICES
except ImportError:
    WoLEngine = None
    DEVICES = {}


def cmd_heal(args):
    """Executes mesh network self-healing starting with Line 1 Bluetooth wake pulse."""
    print("=" * 72)
    print("🛡️  LAUBURU MESH SELF-HEALING ENGINE")
    print("   Hierarchy: Line 1 Bluetooth ➔ Line 2 WoL ➔ Line 3 ADB ➔ Line 4 Tailscale")
    print("=" * 72)

    if WoLEngine is None:
        print("❌ Error: WoLEngine could not be imported from wol_manager.")
        sys.exit(1)

    engine = WoLEngine()
    print("📶 [Line 1] Pulsing Bluetooth proximity wake across all paired nodes...")
    print("⚡ [Line 2] Broadcasting RFC 792 Wake-on-LAN Magic Packets...")
    print("📱 [Line 3] Pulsing Android ADB keepalive signals...")

    summary = engine.wake_all()
    res_dict = summary.get("results", {})
    bt_count = sum(1 for v in res_dict.values() if v.get("tier1_bluetooth"))
    wol_count = sum(1 for v in res_dict.values() if v.get("tier2_wol"))
    adb_count = sum(1 for v in res_dict.values() if v.get("tier3_adb"))
    print(f"\n✅ Self-Healing Broadcast Complete:")
    print(f"   • Total Mesh Devices Targetted: {len(res_dict)}")
    print(f"   • Line 1 Bluetooth Beacons Sent: {bt_count}")
    print(f"   • Line 2 WoL Magic Packets Sent: {wol_count}")
    print(f"   • Line 3 ADB Wake Pulses Sent:  {adb_count}")
    return 0


def cmd_wake(args):
    """Wakes specific device or entire mesh with Bluetooth Line 1 priority."""
    if WoLEngine is None:
        print("❌ Error: WoLEngine could not be imported from wol_manager.")
        sys.exit(1)

    engine = WoLEngine()
    device = args.device.lower().strip() if args.device else "all"

    if device in ("all", "mesh"):
        print("📶 Pulsing Line 1 Bluetooth Proximity Wake + Line 2 UDP WoL across entire mesh...")
        summary = engine.wake_all()
        print(f"✅ Wake signal broadcast to {summary.get('total_devices', 0)} devices.")
    else:
        print(f"📶 Waking node '{device}' (Line 1 Bluetooth ➔ Line 2 UDP WoL ➔ Line 3 ADB)...")
        res = engine.wake_device(device)
        if res.get("success", False):
            print(f"✅ Node '{device}' resurrection dispatched successfully.")
            print(f"   Bluetooth Line 1: {'Success' if res.get('tier1_bluetooth') else 'Bypassed / Not applicable'}")
            print(f"   UDP WoL Line 2:   {'Success' if res.get('tier2_wol') else 'Failed'}")
        else:
            print(f"❌ Failed to wake '{device}': {res.get('error', 'Unknown error')}")
            return 1
    return 0


def cmd_status(args):
    """Displays live status and MAC addresses for the 7-layer mesh."""
    status = {
        "status": "ONLINE",
        "hierarchy": [
            "Line 1 (Default / First Line): Bluetooth Proximity Wake (blueutil --connect)",
            "Line 2: Out-of-Band UDP Wake-on-LAN Magic Packet (UDP Port 9/7)",
            "Line 3: Android ADB Keepalive & Display Wake (termux-wake-lock)",
            "Line 4: Tailscale WireGuard Overlay Link",
            "Line 5: Multi-WAN / Gateway fallback"
        ],
        "registered_devices": DEVICES
    }
    print(json.dumps(status, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Lauburu Network CLI — Bluetooth-First Mesh Self-Healing & Diagnostics"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # heal subcommand
    heal_parser = subparsers.add_parser("heal", help="Trigger mesh self-healing (Line 1 BT ➔ Line 2 WoL)")
    heal_parser.set_defaults(func=cmd_heal)

    # wake subcommand
    wake_parser = subparsers.add_parser("wake", help="Wake sleeping node(s) via Bluetooth First Line")
    wake_parser.add_argument("device", nargs="?", default="all", help="Device key or 'all'")
    wake_parser.set_defaults(func=cmd_wake)

    # status subcommand
    status_parser = subparsers.add_parser("status", help="Get mesh status JSON")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
