"""
Test Suite: Frontier Swarm Consensus for Generation 32 (Mesh Load Balancing)
===========================================================================
Validates:
1. Canonical Document Presence & Mirroring:
   - Root: LOAD_BALANCING_CONSENSUS.md
   - Obsidian: obsidian_vault/APPS_AND_FEATURES/LOAD_BALANCING_CONSENSUS.md
   - Bit-for-bit SHA256 equality.
2. YAML Frontmatter & Voting Integrity:
   - Valid YAML schema with 8 participating frontier & sovereign models.
   - Unanimous consensus score 1.0 (8/8 approval).
   - Mandatory tags and domain metadata.
3. Master Obsidian Knowledge Graph Wikilinks:
   - [[Index]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]],
     [[00_canonical_hardware_matrix]], [[NEXUS_EXTENSION_SETUP_AND_MESH_HUB]], [[LOAD_BALANCING_CONSENSUS]].
4. Six Empirical Technical Vectors Coverage:
   - Vector 1: Bandwidth & Aggregate Throughput (10Gbps/2.5Gbps vs 480Mbps).
   - Vector 2: Latency & Jitter Under Contention (<0.1ms vs 1.5-5.0ms).
   - Vector 3: Kernel Driver Overhead (<1% DMA vs 18-35% CPU URBs).
   - Vector 4: Multi-Port Bonding (IEEE 802.3ad LACP vs zero kernel bonding).
   - Vector 5: Physical Failover & Resilience (sub-50ms carrier recovery vs TTY shuffle).
   - Vector 6: Systemic Topology Fit (pooling 82.8 GB VRAM across 7 layers).
5. Mathematical Formulations & Zero-Mock Compliance:
   - Throughput efficiency equations, queueing delay calculations, and CPU core utilization models.
6. Codification of the 5 Architectural Invariants:
   - Primary Ethernet Serial, Auxiliary USB Serial ADB, Layer 0 Bluetooth RFCOMM,
     Host RAM Sanctuary preservation, Fast-path carrier detection.
7. LoRA Training Dataset Persistence:
   - Record in /Users/aaron/DFS_UNIFIED/lora_datasets/frontier_consensus_dataset.jsonl.
   - Deterministic SHA256 checksum verification.
8. CLI Engine Verification Gate:
   - 06_scripts_and_tooling/ai/frontier_swarm_consensus.py --verify returns exit code 0.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
ROOT_DOC = REPO_ROOT / "LOAD_BALANCING_CONSENSUS.md"
OBSIDIAN_DOC = REPO_ROOT / "obsidian_vault/APPS_AND_FEATURES/LOAD_BALANCING_CONSENSUS.md"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/frontier_consensus_dataset.jsonl")
CONSENSUS_SCRIPT = REPO_ROOT / "06_scripts_and_tooling/ai/frontier_swarm_consensus.py"

def calculate_sha256(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def test_consensus_documents_exist_and_match_bit_for_bit():
    """Verify that LOAD_BALANCING_CONSENSUS.md exists at monorepo root and Obsidian Vault with identical SHA256."""
    assert ROOT_DOC.exists(), f"Missing root consensus document at {ROOT_DOC}"
    assert OBSIDIAN_DOC.exists(), f"Missing Obsidian vault mirrored document at {OBSIDIAN_DOC}"
    
    root_bytes = ROOT_DOC.read_bytes()
    obsidian_bytes = OBSIDIAN_DOC.read_bytes()
    
    assert len(root_bytes) > 5000, "Consensus document is too short or empty"
    assert root_bytes == obsidian_bytes, "Root document and Obsidian Vault mirror do not match bit-for-bit"
    
    root_sha = calculate_sha256(ROOT_DOC)
    obsidian_sha = calculate_sha256(OBSIDIAN_DOC)
    assert root_sha == obsidian_sha, f"SHA256 mismatch: root={root_sha}, obsidian={obsidian_sha}"

def test_yaml_frontmatter_and_unanimous_signoffs():
    """Verify frontmatter metadata, 8-model participating roster, and unanimous approval."""
    content = ROOT_DOC.read_text(encoding="utf-8")
    assert content.startswith("---"), "Document must begin with YAML frontmatter"
    
    # Parse frontmatter block
    parts = content.split("---", 2)
    assert len(parts) >= 3, "YAML frontmatter block must be closed with '---'"
    frontmatter = parts[1]
    
    assert "consensus_score: 1.0" in frontmatter
    assert "8/8 Unanimous" in frontmatter
    assert "mesh_load_balancing_and_hardware_transports" in frontmatter
    assert "generation: 32" in frontmatter
    
    # Verify all 8 models signed off
    expected_signoffs = [
        'gemini_31_pro: "APPROVED"',
        'gemini_38_flash: "APPROVED"',
        'claude_opus_46: "APPROVED"',
        'claude_sonnet_46: "APPROVED"',
        'gpt_6_astra: "APPROVED"',
        'gpt_oss_120b: "APPROVED"',
        'qwen_38_max_master: "APPROVED"',
        'qwen_38_max_abliterated: "APPROVED"'
    ]
    for signoff in expected_signoffs:
        assert signoff in frontmatter, f"Missing model signoff in frontmatter: {signoff}"

def test_master_obsidian_wikilinks():
    """Verify presence of master bidirectional Wikilinks for Obsidian knowledge graph traversal."""
    content = ROOT_DOC.read_text(encoding="utf-8")
    expected_wikilinks = [
        "[[Index]]",
        "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
        "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
        "[[00_canonical_hardware_matrix]]",
        "[[NEXUS_EXTENSION_SETUP_AND_MESH_HUB]]",
        "[[LOAD_BALANCING_CONSENSUS]]"
    ]
    for link in expected_wikilinks:
        assert link in content, f"Missing required Obsidian Wikilink: {link}"

def test_six_technical_vectors_coverage():
    """Verify exhaustive analysis of all 6 empirical technical vectors."""
    content = ROOT_DOC.read_text(encoding="utf-8")
    
    vectors = [
        "Vector 1: Bandwidth & Throughput",
        "Vector 2: Latency & Jitter",
        "Vector 3: Kernel Driver Overhead",
        "Vector 4: Multi-Port Bonding",
        "Vector 5: Physical Failover & Resilience",
        "Vector 6: Systemic Topology Fit"
    ]
    for vec in vectors:
        assert vec in content, f"Missing section for {vec}"
        
    # Check empirical hardware numbers
    assert "10GbE" in content
    assert "2.5GbE" in content
    assert "480 Mbps" in content
    assert "0.544ms RTT" in content or "0.544 ms RTT" in content
    assert "CAKE SQM" in content
    assert "IEEE 802.3ad LACP" in content
    assert "TTY Shuffle" in content
    assert "82.8 GB" in content

def test_mathematical_formulations():
    """Verify presence of mathematical models for bandwidth, latency, queueing, and CPU overhead."""
    content = ROOT_DOC.read_text(encoding="utf-8")
    assert "T_{\\text{payload}}" in content
    assert "D_{\\text{total}}" in content
    assert "\\text{CPU}_{\\text{overhead}}" in content
    assert "125\\text{ µs}" in content or "125 µs" in content

def test_five_architectural_invariants():
    """Verify codification of the 5 canonical architectural invariants."""
    content = ROOT_DOC.read_text(encoding="utf-8")
    invariants = [
        "Invariant 1: Ethernet Serial as Primary Mesh Transport",
        "Invariant 2: USB Serial Restricted to Edge ADB & Out-of-Band Recovery",
        "Invariant 3: Layer 0 Bluetooth RFCOMM as Emergency IP-Less Bootstrap",
        "Invariant 4: Host Sanctuary & Zero-Polling Enforcement",
        "Invariant 5: Fast-Path Carrier Detection Before Bluetooth Fallback"
    ]
    for inv in invariants:
        assert inv in content, f"Missing invariant: {inv}"

def test_lora_dataset_entry_integrity():
    """Verify that a valid consensus record is appended to lora_datasets/frontier_consensus_dataset.jsonl."""
    assert LORA_DATASET.exists(), f"LoRA dataset file not found at {LORA_DATASET}"
    
    with open(LORA_DATASET, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        
    assert len(lines) > 0, "LoRA dataset file is empty"
    
    # Check that at least one entry has the load balancing consensus task
    matching_entries = []
    for line in lines:
        try:
            record = json.loads(line)
            if "load balancing" in record.get("task", "").lower() or "load balancing" in record.get("domain", "").lower():
                matching_entries.append(record)
        except Exception:
            pass
            
    assert len(matching_entries) > 0, "No load balancing consensus record found in LoRA dataset"
    latest = matching_entries[-1]
    
    assert latest.get("verified") is True
    assert "sha256" in latest
    assert len(latest["sha256"]) == 64
    
    # Check that all 8 models are represented in responses
    responses = latest.get("responses", {})
    expected_models = [
        "gemini_pro", "gemini_flash", "opus", "sonnet", "gpt_6_astra", "gpt_oss",
        "qwen_38_max_master", "qwen_38_max_abliterated"
    ]
    for m in expected_models:
        assert m in responses, f"Missing model response for '{m}' in LoRA record"
        assert len(responses[m]) > 50, f"Model response for '{m}' is too brief"
        
    # Check document SHA256 matches
    expected_doc_sha = calculate_sha256(ROOT_DOC)
    assert latest.get("document_sha256") == expected_doc_sha, "LoRA record document_sha256 does not match physical document"

def test_cli_engine_verification_gate():
    """Execute 06_scripts_and_tooling/ai/frontier_swarm_consensus.py --verify and assert exit code 0."""
    assert CONSENSUS_SCRIPT.exists(), f"Consensus engine script missing at {CONSENSUS_SCRIPT}"
    
    res = subprocess.run(
        [sys.executable, str(CONSENSUS_SCRIPT), "--verify"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert res.returncode == 0, f"--verify failed with exit code {res.returncode}. Stderr: {res.stderr}"
    assert "All Frontier Swarm Consensus Artifacts PASSED Verification Gate" in res.stdout
