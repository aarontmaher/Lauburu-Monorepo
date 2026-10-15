#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/web_arena_visualizer")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("web_arena_visualizer_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("web_arena_visualizer_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "WebArenaVisualizerPrimaBinding")
NetworkClass = getattr(pan_mod, "WebArenaVisualizerNetworkTransport")

def test_web_arena_visualizer_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "web_arena_visualizer"
    assert "ai_mesh" in status

def test_web_arena_visualizer_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "web_arena_visualizer"
    assert "transport" in topo

def test_static_index_html():
    index_file = APP_DIR / "static" / "index.html"
    assert index_file.exists()
    assert index_file.stat().st_size > 30000
    content = index_file.read_text(encoding="utf-8")
    assert "<canvas" in content or "arena" in content.lower()

