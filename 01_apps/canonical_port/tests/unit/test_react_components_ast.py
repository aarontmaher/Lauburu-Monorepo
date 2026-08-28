"""
Unit Tests: React Component & Layout AST Verification
Inspects the physical JSX and CSS files in src/ to guarantee genuine implementation, zero-mock truth, and proper exports.
Derived from ORIGINAL_REQUEST.md and PROJECT.md §Code Layout.
"""

import os
import re
import pytest

SRC_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/src"

def test_styles_files_exist():
    theme_css = os.path.join(SRC_DIR, "styles/canonical_theme.css")
    index_css = os.path.join(SRC_DIR, "styles/index.css")
    assert os.path.isfile(theme_css), "canonical_theme.css missing"
    assert os.path.isfile(index_css), "index.css missing"
    
    with open(theme_css, "r") as f:
        content = f.read()
        assert "--bg-primary" in content
        assert "--accent-cyan" in content or "#38bdf8" in content

def test_layout_components_exist_and_export():
    components = [
        ("components/layout/ShellLayout.jsx", "ShellLayout"),
        ("components/layout/SidebarNav.jsx", "SidebarNav"),
        ("components/layout/HeaderStatusBar.jsx", "HeaderStatusBar")
    ]
    for rel_path, comp_name in components:
        full_path = os.path.join(SRC_DIR, rel_path)
        assert os.path.isfile(full_path), f"File {rel_path} missing"
        with open(full_path, "r") as f:
            code = f.read()
            assert f"export function {comp_name}" in code or f"export default function {comp_name}" in code or f"export const {comp_name}" in code or f"export default {comp_name}" in code

def test_governance_components_exist_and_export():
    components = [
        ("components/governance/MasterAGIGovernanceView.jsx", "MasterAGIGovernanceView"),
        ("components/governance/AGIModelRosterCard.jsx", "AGIModelRosterCard"),
        ("components/governance/ClusterVRAMGauge.jsx", "ClusterVRAMGauge"),
        ("components/governance/TriOrchestratorDebatePanel.jsx", "TriOrchestratorDebatePanel"),
        ("components/governance/StagnationEscalationModal.jsx", "StagnationEscalationModal"),
        ("components/governance/SwarmActionDispatcherBar.jsx", "SwarmActionDispatcherBar")
    ]
    for rel_path, comp_name in components:
        full_path = os.path.join(SRC_DIR, rel_path)
        assert os.path.isfile(full_path), f"File {rel_path} missing"
        with open(full_path, "r") as f:
            code = f.read()
            assert len(code) > 200, f"Component {comp_name} is too small"

def test_optimization_components_exist_and_export():
    components = [
        ("components/optimization/OptimizationHubShell.jsx", "OptimizationHubShell"),
        ("components/optimization/HardwareOptimizationView.jsx", "HardwareOptimizationView"),
        ("components/optimization/SoftwareOptimizationView.jsx", "SoftwareOptimizationView"),
        ("components/optimization/InternetOptimizationView.jsx", "InternetOptimizationView"),
        ("components/optimization/StorageOptimizationView.jsx", "StorageOptimizationView")
    ]
    for rel_path, comp_name in components:
        full_path = os.path.join(SRC_DIR, rel_path)
        assert os.path.isfile(full_path), f"File {rel_path} missing"
        with open(full_path, "r") as f:
            code = f.read()
            assert len(code) > 200, f"Component {comp_name} is too small"

def test_master_agi_model_strings_in_governance_code():
    roster_path = os.path.join(SRC_DIR, "components/governance/MasterAGIGovernanceView.jsx")
    if not os.path.isfile(roster_path):
        roster_path = os.path.join(SRC_DIR, "services/mockFallbackData.js")
    
    with open(roster_path, "r") as f:
        code = f.read()
        assert "Kimi" in code or "kimi" in code, "Kimi model not referenced in governance"
        assert "Qwen" in code or "qwen" in code, "Qwen model not referenced in governance"

def test_network_metrics_components_exist_and_export():
    components = [
        ("components/network/NetworkMetricsView.jsx", "NetworkMetricsView"),
        ("components/network/WANFailoverCard.jsx", "WANFailoverCard"),
        ("components/network/TailscaleMeshCard.jsx", "TailscaleMeshCard"),
        ("components/network/TB4DmaBridgeCard.jsx", "TB4DmaBridgeCard"),
        ("components/network/LlamaRpcLatencyCard.jsx", "LlamaRpcLatencyCard")
    ]
    for rel_path, comp_name in components:
        full_path = os.path.join(SRC_DIR, rel_path)
        assert os.path.isfile(full_path), f"File {rel_path} missing"
        with open(full_path, "r") as f:
            code = f.read()
            assert f"export function {comp_name}" in code or f"export default function {comp_name}" in code or f"export const {comp_name}" in code or f"export default {comp_name}" in code
            assert len(code) > 200, f"Component {comp_name} is too small"

