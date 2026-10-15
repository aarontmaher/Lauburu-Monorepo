#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/ai_training_tui")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("ai_training_tui_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("ai_training_tui_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "AiTrainingTuiPrimaBinding")
NetworkClass = getattr(pan_mod, "AiTrainingTuiNetworkTransport")

def test_ai_training_tui_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "ai_training_tui"
    assert "ai_mesh" in status

def test_ai_training_tui_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "ai_training_tui"
    assert "transport" in topo
