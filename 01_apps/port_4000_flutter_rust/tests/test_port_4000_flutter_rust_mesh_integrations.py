#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("port_4000_flutter_rust_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("port_4000_flutter_rust_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "Port4000FlutterRustPrimaBinding")
NetworkClass = getattr(pan_mod, "Port4000FlutterRustNetworkTransport")

def test_port_4000_flutter_rust_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "port_4000_flutter_rust"
    assert "ai_mesh" in status

def test_port_4000_flutter_rust_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "port_4000_flutter_rust"
    assert "transport" in topo
