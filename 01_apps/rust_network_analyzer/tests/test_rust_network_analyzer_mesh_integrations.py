#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_network_analyzer")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("rust_network_analyzer_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("rust_network_analyzer_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "RustNetworkAnalyzerPrimaBinding")
NetworkClass = getattr(pan_mod, "RustNetworkAnalyzerNetworkTransport")

def test_rust_network_analyzer_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "rust_network_analyzer"
    assert "ai_mesh" in status

def test_rust_network_analyzer_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "rust_network_analyzer"
    assert "transport" in topo
