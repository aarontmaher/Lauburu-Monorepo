import pytest
import sys
import os
from pathlib import Path

# Add paths
root_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.append(str(root_path / "01_apps/screen_lens/src"))
sys.path.append(str(root_path / "04_data_and_memory/src"))
sys.path.append(str(root_path / "05_agents_and_swarms"))

from notebooks.canonical_project_master_notebook import CanonicalProjectMasterNotebook
from integrations.tri_gemini_automation_bridge import TriGeminiAutomationBridge
from protocols.tri_gemini_training_and_learning_protocol import TriGeminiTrainingAndLearningProtocol
from graph.mmap_csr_graph import MmapCSRGraph

def test_canonical_notebook_anti_hallucination():
    notebook = CanonicalProjectMasterNotebook()
    
    # Test 1: Catches Wi-Fi 6 on L2/L3
    bad_claim = "The MacBook Pro supports Wi-Fi 6 on the new router."
    findings = notebook.audit_anti_hallucination(bad_claim)
    assert len(findings) > 0
    assert findings[0]["severity"] == "CRITICAL"
    assert "Wi-Fi 5" in findings[0]["correction"]

    # Test 2: Catches 4.0 KB SQLite WAL illusion
    bad_claim_wal = "SQLite 4.0 KB 10,000 edges"
    findings_wal = notebook.audit_anti_hallucination(bad_claim_wal)
    assert len(findings_wal) > 0
    assert "228.00 KB" in findings_wal[0]["correction"]

def test_tri_gemini_automation_bridge():
    bridge = TriGeminiAutomationBridge()
    cycle = bridge.execute_learning_protocol_cycle()
    assert cycle["spark"]["status"] == "OPERATIONAL"
    assert cycle["notebook"]["status"] == "SYNC_ACTIVE"

def test_mmap_csr_graph_mechanics(tmp_path):
    csr_path = tmp_path / "test_suite.csr"
    edges = [(0, 1), (0, 2), (1, 3), (2, 4)]
    graph = MmapCSRGraph.build_from_edges(num_nodes=5, edges=edges, output_path=csr_path)
    
    # Traversal test
    visited = graph.multi_hop_traversal(start_node=0, max_depth=2)
    assert visited == {1, 2, 3, 4}
    
    # Storage density test: 5 nodes, 4 edges -> header (8 bytes) + indptr (6*4=24 bytes) + indices (4*4=16 bytes) = 48 bytes
    assert os.path.getsize(csr_path) == 48
    graph.close()

def test_training_protocol_recording():
    protocol = TriGeminiTrainingAndLearningProtocol()
    res = protocol.validate_and_record_training_pair(
        prompt="Test Prompt",
        completion="Test Completion",
        verified_metrics={"test": 123}
    )
    assert res["status"] == "RECORDED_TO_LORA_LAKE"
