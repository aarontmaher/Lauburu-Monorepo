"""Unit tests for the read-only canonical mesh connectivity audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "02_ai_models_and_inference/llama_rpc_mesh/mesh_preflight.py"
)
SPEC = importlib.util.spec_from_file_location("mesh_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
mesh_preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mesh_preflight)


def test_addresses_prefer_private_compute_transports_and_remove_duplicates() -> None:
    node = {
        "wireguard": "10.1.0.10",
        "tailscale": "100.119.199.76",
        "tier4_thunderbolt": {"ip": "10.0.0.2"},
        "tier3_ethernet": {"ip": "192.168.8.230", "lan_ip": "192.168.8.230"},
    }

    assert list(mesh_preflight.addresses_for(node)) == [
        ("thunderbolt", "10.0.0.2"),
        ("wireguard", "10.1.0.10"),
        ("tailscale", "100.119.199.76"),
        ("local", "192.168.8.230"),
    ]


def test_addresses_exclude_public_targets() -> None:
    node = {
        "wireguard": "203.0.113.10",
        "tailscale": "100.119.199.76",
        "tier3_ethernet": {"ip": "8.8.8.8"},
    }

    assert list(mesh_preflight.addresses_for(node)) == [("tailscale", "100.119.199.76")]


def test_ports_include_ssh_and_advertised_services_once() -> None:
    node = {
        "ssh_port": 22,
        "lockdown_port": 62078,
        "tier5_ssh": {"port": 2222},
        "tier2_adb": {"tailscale_adb": "100.84.40.95:5555"},
        "tier6_services": {"ports": [22, 50052, 8083, 70000]},
    }

    assert mesh_preflight.ports_for(node) == [22, 62078, 2222, 50052, 8083, 5555]
