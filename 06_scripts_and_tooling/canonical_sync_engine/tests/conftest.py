"""
tests/conftest.py
Global pytest fixtures and isolated vault sandboxes for canonical_sync_engine.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict
import pytest

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.verification.self_healer import CANONICAL_INDEX_MD_CONTENT


@pytest.fixture
def test_sync_config(tmp_path: Path) -> SyncConfig:
    """Provides an isolated, sandboxed SyncConfig pointing to subdirectories in tmp_path."""
    return SyncConfig.for_testing(tmp_path)


@pytest.fixture
def mock_vault_sandbox(tmp_path: Path) -> Dict[str, Path]:
    """
    Constructs a fully populated, healthy Quad-Vault mock filesystem:
    - obsidian_vault/ with valid Index.md
    - lora_datasets/ with valid sample JSONL
    - 04_data_and_memory/ directory
    - git_repo/ with initialized .git directory
    - gdrive_mount/ and data/gdrive_cache/ directories
    """
    obsidian_dir = tmp_path / "obsidian_vault"
    pyspark_dir = tmp_path / "lora_datasets"
    memory_dir = tmp_path / "04_data_and_memory"
    git_dir = tmp_path / "git_repo"
    gdrive_mount = tmp_path / "gdrive_mount"
    gdrive_cache = tmp_path / "data" / "gdrive_cache"

    for d in [obsidian_dir, pyspark_dir, memory_dir, git_dir, gdrive_mount, gdrive_cache]:
        d.mkdir(parents=True, exist_ok=True)

    # Populate valid Obsidian master Index.md
    index_md = obsidian_dir / "Index.md"
    index_md.write_text(CANONICAL_INDEX_MD_CONTENT, encoding="utf-8")

    # Populate valid sample PySpark jsonl
    sample_jsonl = pyspark_dir / "sample_dataset.jsonl"
    sample_jsonl.write_text('{"record_id": "r1", "valid": true}\n', encoding="utf-8")

    # Populate Git repo .git
    dot_git = git_dir / ".git"
    dot_git.mkdir(parents=True, exist_ok=True)

    return {
        "base": tmp_path,
        "obsidian": obsidian_dir,
        "pyspark": pyspark_dir,
        "memory": memory_dir,
        "git": git_dir,
        "gdrive_mount": gdrive_mount,
        "gdrive_cache": gdrive_cache,
    }


@pytest.fixture
def sample_truth_artifact() -> TruthArtifact:
    """Standard verified truth audit artifact."""
    return TruthArtifact(
        artifact_id="art-test-001",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Test Baseline Truth Artifact",
        payload={
            "status": "verified",
            "passed_checks": 14,
            "failed_checks": 0,
            "metrics": {"qps": 4200.0, "latency_ms": 1.25},
        },
        source_node="Mac_Node",
        timestamp="2026-08-27T00:00:00Z",
        tags=["audit", "m1", "test"],
        metadata={"reviewer": "sentinel", "version": "1.0.0"},
    )


@pytest.fixture
def sample_ai_debate_artifact() -> TruthArtifact:
    """AI debate consensus artifact."""
    return TruthArtifact(
        artifact_id="art-debate-002",
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title="Tri-Orchestrator Consensus on Quad-Vault Storage",
        payload={
            "consensus_score": 0.992,
            "quorum_reached": True,
            "participants": ["Gemini_Pro", "Gemini_Flash", "Kimi_Tandem", "Qwen_Max"],
            "resolution": "Adopt deterministic SHA-256 with sorted keys.",
        },
        source_node="Mac_Node",
        timestamp="2026-08-27T01:00:00Z",
        tags=["consensus", "architecture"],
        metadata={"round": 3},
    )
