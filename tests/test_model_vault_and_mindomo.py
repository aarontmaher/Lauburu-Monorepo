"""
Automated Test Suite: Mindomo 3D Mindmap & AI Model Storage Vault
"""
import os
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

REPO_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')

def test_mindomo_opml_structure():
    """Verify that Mindomo grappling OPML contains valid hierarchical nodes."""
    opml_path = REPO_ROOT / '10_spatial_grappling_kinematics/mindomo/grappling_mindmap_structure.opml'
    assert opml_path.exists(), f"Mindomo structure missing at {opml_path}"
    
    tree = ET.parse(opml_path)
    root = tree.getroot()
    
    # Assert OPML 2.0 valid format
    assert root.tag == 'opml'
    assert root.get('version') == '2.0'
    
    # Check node count
    outlines = root.findall('.//outline')
    assert len(outlines) >= 3000, f"Expected >= 3000 nodes, found {len(outlines)}"
    
    # Check top-level sections
    body = root.find('body')
    top_outline = body.find('outline')
    assert top_outline.get('text') == 'Grappling Mind Map'

def test_ai_model_vault_structure():
    """Verify that the AI Model Storage Vault hierarchy is intact."""
    vault_root = Path('/Users/aaron/DFS_UNIFIED/AI_Models_Vault')
    required_dirs = ['gguf_quantized', 'petals_dht_cache', 'exo_p2p_cache', 'lora_adapters']
    
    for d in required_dirs:
        target = vault_root / d
        assert target.exists() and target.is_dir(), f"Missing vault directory: {target}"
        
    manifest = REPO_ROOT / '02_ai_models_and_inference/model_vault_manifests/MODEL_STORAGE_VAULT_SPEC.md'
    assert manifest.exists(), f"Missing model vault manifest at {manifest}"

def test_mindomo_desktop_symlink():
    """Verify desktop/documents symlink exists on Mac Mini for user access."""
    doc_link = Path.home() / 'Documents/Mindomo_3D_Mindmap'
    assert doc_link.exists() or doc_link.is_symlink(), f"Symlink missing at {doc_link}"
    assert doc_link.resolve().exists(), f"Symlink target broken: {doc_link.resolve()}"
