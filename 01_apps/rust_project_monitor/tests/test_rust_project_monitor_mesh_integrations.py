#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/rust_project_monitor")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("rust_project_monitor_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("rust_project_monitor_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "RustProjectMonitorPrimaBinding")
NetworkClass = getattr(pan_mod, "RustProjectMonitorNetworkTransport")

def test_rust_project_monitor_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "rust_project_monitor"
    assert "ai_mesh" in status

def test_rust_project_monitor_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "rust_project_monitor"
    assert "transport" in topo
