#!/usr/bin/env python3
"""Read-only connectivity audit for the canonical Lauburu compute mesh."""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = REPOSITORY_ROOT / "06_scripts_and_tooling/network/mesh_ip_matrix.json"
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
PRIVATE_MESH_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def is_private_mesh_address(address: str) -> bool:
    """Accept only addresses that can belong to the local mesh."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return (
        parsed.is_loopback
        or parsed.is_link_local
        or parsed in CGNAT_NETWORK
        or any(parsed in network for network in PRIVATE_MESH_NETWORKS)
    )


def addresses_for(node: dict[str, Any]) -> Iterable[tuple[str, str]]:
    """Yield unique, usable addresses in compute-preferred transport order."""
    sources = (
        ("thunderbolt", node.get("tier4_thunderbolt", {})),
        ("wireguard", {"ip": node.get("wireguard")}),
        ("tailscale", {"ip": node.get("tailscale")}),
        ("local", node.get("tier3_ethernet", {})),
        ("wifi", node.get("tier2_wifi", {})),
    )
    seen: set[str] = set()
    for transport, values in sources:
        for key, address in values.items():
            if not key.endswith("ip") and key != "ip":
                continue
            if not isinstance(address, str) or address in seen:
                continue
            if is_private_mesh_address(address):
                seen.add(address)
                yield transport, address


def ports_for(node: dict[str, Any]) -> list[int]:
    """Return every explicitly advertised service port, including SSH."""
    ports = [
        node.get("ssh_port"),
        node.get("lockdown_port"),
        node.get("tier5_ssh", {}).get("port"),
    ]
    ports.extend(node.get("tier6_services", {}).get("ports", []))
    for endpoint in node.get("tier2_adb", {}).values():
        if isinstance(endpoint, str):
            _, separator, port = endpoint.rpartition(":")
            if separator and port.isdecimal():
                ports.append(int(port))
    return list(dict.fromkeys(port for port in ports if isinstance(port, int) and 0 < port < 65536))


def probe(address: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((address, port), timeout=timeout):
            return {
                "address": address,
                "port": port,
                "reachable": True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
    except OSError as error:
        return {
            "address": address,
            "port": port,
            "reachable": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": str(error),
        }


def audit_node(node_id: str, node: dict[str, Any], timeout: float) -> dict[str, Any]:
    endpoints = [
        (transport, address, port)
        for transport, address in addresses_for(node)
        for port in ports_for(node)
    ]
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(endpoints)))) as executor:
        futures = [
            (transport, executor.submit(probe, address, port, timeout))
            for transport, address, port in endpoints
        ]
        results = [{"transport": transport, **future.result()} for transport, future in futures]

    return {
        "node_id": node_id,
        "name": node["name"],
        "role": node["role"],
        "status": "reachable" if any(result["reachable"] for result in results) else "unreachable",
        "probes": results,
    }


def load_inventory(inventory_path: Path) -> dict[str, dict[str, Any]]:
    with inventory_path.open(encoding="utf-8") as inventory_file:
        raw_inventory = json.load(inventory_file)
    return {
        node_id: node
        for node_id, node in raw_inventory.items()
        if isinstance(node, dict) and "name" in node and "role" in node
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit live connectivity to canonical mesh services.")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help="Path to the canonical mesh inventory JSON.",
    )
    parser.add_argument(
        "--node",
        action="append",
        dest="nodes",
        help="Audit only this node ID. Repeat to select multiple nodes.",
    )
    parser.add_argument("--timeout", type=float, default=0.5, help="TCP connect timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        print("--timeout must be positive.", file=sys.stderr)
        return 2

    try:
        inventory = load_inventory(args.inventory)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to load canonical mesh inventory: {error}", file=sys.stderr)
        return 2

    selected_nodes = args.nodes or list(inventory)
    unknown_nodes = sorted(set(selected_nodes) - inventory.keys())
    if unknown_nodes:
        print(f"Unknown mesh node ID(s): {', '.join(unknown_nodes)}", file=sys.stderr)
        return 2

    results = [audit_node(node_id, inventory[node_id], args.timeout) for node_id in selected_nodes]
    reachable_nodes = sum(result["status"] == "reachable" for result in results)
    report = {
        "inventory": str(args.inventory),
        "status": "healthy" if reachable_nodes == len(results) else "degraded",
        "reachable_nodes": reachable_nodes,
        "total_nodes": len(results),
        "nodes": results,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
