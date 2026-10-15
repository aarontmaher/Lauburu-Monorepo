#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import pytest

APP_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/scaffolded_ui")

def load_mod(name, rel_path):
    p = APP_DIR / rel_path
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

prima_mod = load_mod("scaffolded_ui_prima", "src/ai_bindings/prima_binding.py")
pan_mod = load_mod("scaffolded_ui_pan", "src/network/pan_transport.py")

PrimaClass = getattr(prima_mod, "ScaffoldedUiPrimaBinding")
NetworkClass = getattr(pan_mod, "ScaffoldedUiNetworkTransport")

def test_scaffolded_ui_prima_status():
    binding = PrimaClass()
    status = binding.get_service_status()
    assert status["app"] == "scaffolded_ui"
    assert "ai_mesh" in status

def test_scaffolded_ui_network_transport():
    transport = NetworkClass()
    topo = transport.get_network_topology()
    assert topo["app"] == "scaffolded_ui"
    assert "transport" in topo

def test_readiness_gauge_card_component():
    tsx_file = APP_DIR / "ReadinessGaugeCard.tsx"
    assert tsx_file.exists()
    content = tsx_file.read_text(encoding="utf-8")
    
    # Verify component declaration & props
    assert "export const ReadinessGaugeCard" in content
    assert "ReadinessGaugeCardProps" in content
    assert "status?: 'IDLE' | 'ACTIVE' | 'CONNECTED' | 'DISCONNECTED'" in content
    
    # Verify WCAG AA accessibility compliance
    assert 'role="region"' in content
    assert 'aria-label={title}' in content
    assert 'aria-label="Execute action"' in content
    assert "focus:ring-2 focus:ring-sky-400" in content
    assert "text-slate-100" in content

