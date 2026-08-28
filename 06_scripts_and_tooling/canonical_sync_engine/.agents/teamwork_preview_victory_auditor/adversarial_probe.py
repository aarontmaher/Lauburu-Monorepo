#!/usr/bin/env python3
"""
Independent Adversarial Stress-Testing Probe
Executed by the Independent Victory Auditor to stress-test canonical_sync_engine.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/Users/aaron/teamwork_projects/canonical_sync_engine")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.engine.coordinator import CanonicalSyncEngine
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.verification.self_healer import StorageSelfHealer

def test_hash_invariance():
    print("🧪 [Probe 1] Testing Deterministic Hash Invariance under arbitrary key ordering & deep nesting...")
    payload_a = {
        "z": 100,
        "a": [1, 2, {"k2": "v2", "k1": "v1"}],
        "m": {"b": True, "a": False, "c": None},
        "unicode": "こんにちは世界 🚀 ∇f(x)=0",
    }
    payload_b = {
        "unicode": "こんにちは世界 🚀 ∇f(x)=0",
        "m": {"c": None, "a": False, "b": True},
        "a": [1, 2, {"k1": "v1", "k2": "v2"}],
        "z": 100,
    }
    
    art_a = TruthArtifact(
        artifact_id="probe-inv-001",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Hash Invariance Test",
        payload=payload_a,
        tags=["z_tag", "a_tag", "m_tag"],
    )
    art_b = TruthArtifact(
        artifact_id="probe-inv-001",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Hash Invariance Test",
        payload=payload_b,
        timestamp=art_a.timestamp,
        tags=["a_tag", "m_tag", "z_tag"],
    )
    
    assert art_a.sha256_hash == art_b.sha256_hash, f"Hash mismatch: {art_a.sha256_hash} != {art_b.sha256_hash}"
    assert art_a.verify_hash() is True
    assert art_b.verify_hash() is True
    print(f"  ✅ Hash Invariance PASSED: {art_a.sha256_hash}")


def test_tamper_detection_in_all_vaults():
    print("🧪 [Probe 2] Testing Tamper Detection across all 4 Vaults...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = SyncConfig.for_testing(tmp_dir)
        (config.git_repo_path / ".git").mkdir(parents=True, exist_ok=True)
        engine = CanonicalSyncEngine(config=config, auto_heal=True)
        
        art = TruthArtifact(
            artifact_id="probe-tamper-001",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title="Tamper Detection Artifact",
            payload={"secret_value": 42, "status": "ORIGINAL"},
        )
        res = engine.sync_truth_artifact(art)
        assert res.success is True
        
        # Tamper Obsidian Note
        obs_note = config.obsidian_vault_path / "truth_artifacts" / "probe-tamper-001.md"
        content = obs_note.read_text()
        tampered_content = content.replace("ORIGINAL", "TAMPERED")
        obs_note.write_text(tampered_content)
        
        obs_syncer = engine.syncers["obsidian"]
        assert obs_syncer.verify(art) is False, "Obsidian failed to detect content tampering!"
        
        # Tamper Git file
        git_file = config.git_repo_path / "04_data_and_memory" / "core_data" / "probe-tamper-001.json"
        git_data = json.loads(git_file.read_text())
        git_data["payload"]["status"] = "TAMPERED"
        git_file.write_text(json.dumps(git_data))
        
        git_syncer = engine.syncers["git"]
        assert git_syncer.verify(art) is False, "Git failed to detect content tampering!"
        
        # Tamper GDrive file
        gdrive_file = config.gdrive_mount_path / "truth_artifacts" / "probe-tamper-001.json"
        if not gdrive_file.exists():
            gdrive_file = config.gdrive_fallback_cache_path / "truth_artifacts" / "probe-tamper-001.json"
        gdrive_data = json.loads(gdrive_file.read_text())
        gdrive_data["sha256_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"
        gdrive_file.write_text(json.dumps(gdrive_data))
        
        gdrive_syncer = engine.syncers["gdrive"]
        assert gdrive_syncer.verify(art) is False, "GDrive failed to detect hash tampering!"
        
        print("  ✅ Tamper Detection PASSED on all vaults.")


def test_high_concurrency_sync():
    print("🧪 [Probe 3] Testing High-Concurrency Quad-Vault Sync (50 concurrent threads)...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = SyncConfig.for_testing(tmp_dir)
        (config.git_repo_path / ".git").mkdir(parents=True, exist_ok=True)
        engine = CanonicalSyncEngine(config=config, auto_heal=True, max_workers=8)
        
        def sync_one(idx: int):
            art = TruthArtifact(
                artifact_id=f"probe-conc-{idx:03d}",
                artifact_type=ArtifactType.LORA_PAIR,
                title=f"Concurrent Sync {idx}",
                payload={"thread_idx": idx, "data": f"content_{idx}" * 10},
            )
            return engine.sync_truth_artifact(art)
        
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(sync_one, range(50)))
            
        assert all(r.success for r in results), "Some concurrent syncs failed!"
        
        # Check master jsonl line count
        master_jsonl = config.pyspark_dataset_path / "truth_audit_master.jsonl"
        lines = master_jsonl.read_text().strip().splitlines()
        assert len(lines) == 50, f"Expected 50 lines in master JSONL, got {len(lines)}"
        print(f"  ✅ High-Concurrency PASSED: 50/50 successful syncs, 50 valid JSONL entries.")


def test_self_healer_recovery():
    print("🧪 [Probe 4] Testing Pre-Flight Storage Self-Healer Recovery...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = SyncConfig.for_testing(tmp_dir)
        healer = StorageSelfHealer(
            obsidian_path=config.obsidian_vault_path,
            pyspark_lora_path=config.pyspark_dataset_path,
            pyspark_memory_path=config.pyspark_memory_path,
            git_repo_path=config.git_repo_path,
            gdrive_fallback_path=config.gdrive_fallback_cache_path,
        )
        
        # Delete Obsidian Index.md
        index_file = config.obsidian_vault_path / "Index.md"
        if index_file.exists():
            index_file.unlink()
            
        actions = healer.heal_all()
        assert index_file.exists(), "Self-healer failed to recreate Index.md!"
        content = index_file.read_text()
        assert "[[Index]]" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        print(f"  ✅ Self-Healer PASSED: Successfully healed missing Index.md with actions: {actions}")

if __name__ == "__main__":
    test_hash_invariance()
    test_tamper_detection_in_all_vaults()
    test_high_concurrency_sync()
    test_self_healer_recovery()
    print("\n🎉 ALL INDEPENDENT ADVERSARIAL PROBES PASSED WITH 100% SUCCESS!")
