#!/usr/bin/env python3
"""
tests/e2e/test_sync_pipeline.py
Acceptance Criteria Verification Test Script for canonical_sync_engine.

Acceptance Workflow:
1. Injects a synthetic dummy TruthArtifact (e.g., TRUTH_AUDIT or AI_DEBATE_CONSENSUS).
2. Executes the Quad-Vault synchronization pipeline via CanonicalSyncEngine.
3. Programmatically asserts and verifies:
   a. PySpark Data Lake: truth_audit_master.jsonl appended with valid JSON and matching SHA-256.
   b. Obsidian Knowledge Graph: truth_artifacts/<id>.md generated with YAML frontmatter,
      valid tags, and mandatory Wikilinks ([[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[{artifact_type}]]).
   c. Git Monorepo: 04_data_and_memory/core_data/<id>.json written with matching payload and SHA-256.
   d. Google Drive Cloud Mirror: /Volumes/Google Drive/My Drive/truth_artifacts/<id>.json (or local VFS fallback cache) written.
   e. Cryptographic Parity: Exact SHA-256 hash equality strictly asserted across all 4 destinations.
4. Returns exit code 0 on complete success, code 1 on any failure.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure parent path is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.engine.coordinator import CanonicalSyncEngine
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.sync_result import QuadVaultSyncResult
from canonical_sync_engine.verification.self_healer import CANONICAL_INDEX_MD_CONTENT


def create_synthetic_truth_audit_artifact(
    artifact_id: str = "art-acceptance-audit-001",
    title: str = "Acceptance Criteria Verification - Truth Audit Baseline",
) -> TruthArtifact:
    """Creates a high-fidelity synthetic TruthArtifact for acceptance testing."""
    return TruthArtifact(
        artifact_id=artifact_id,
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title=title,
        payload={
            "acceptance_criteria": "M4_E2E_VERIFICATION",
            "audit_scope": "Quad-Vault Canonical Sync",
            "nodes_scanned": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "GW"],
            "total_headroom_gb": 82.8,
            "verification_checks": {
                "rule_0_zero_mock": "PASS",
                "rule_6_storage_invariants": "PASS",
                "sha256_cryptographic_parity": "PASS",
                "fast_path_latency_ms": 1.15,
            },
            "metrics": {
                "qps": 5400.0,
                "ingest_throughput_mb_s": 142.5,
                "integrity_score": 1.0,
            },
        },
        source_node="Mac_Node",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        tags=["acceptance", "truth_audit", "quad_vault", "e2e", "milestone_4"],
        metadata={
            "orchestrator": "teamwork_preview_orchestrator",
            "verifier": "teamwork_preview_worker_m4",
            "suite_version": "1.0.0",
        },
    )


def create_synthetic_ai_debate_artifact(
    artifact_id: str = "art-acceptance-debate-002",
    title: str = "Tri-Orchestrator Swarm Consensus on Canonical Storage Parity",
) -> TruthArtifact:
    """Creates a synthetic AI_DEBATE_CONSENSUS TruthArtifact."""
    return TruthArtifact(
        artifact_id=artifact_id,
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title=title,
        payload={
            "debate_id": "DEBATE-2026-08-27-01",
            "topic": "Quad-Vault Zero-Mock Parity Protocol",
            "quorum_reached": True,
            "consensus_score": 0.998,
            "deliberation_rounds": 4,
            "council_participants": [
                {"agent": "Gemini_3.1_Pro_High", "vote": "APPROVE", "weight": 0.30},
                {"agent": "Gemini_3.7_Flash_High", "vote": "APPROVE", "weight": 0.25},
                {"agent": "Kimi_Tandem", "vote": "APPROVE", "weight": 0.25},
                {"agent": "Qwen_3.8_Max", "vote": "APPROVE", "weight": 0.20},
            ],
            "consensus_resolution": "Enforce deterministic SHA-256 sorting and atomic quad-vault mirroring.",
        },
        source_node="Mac_Node",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        tags=["acceptance", "ai_debate", "consensus", "swarm", "quad_vault"],
        metadata={"round": 4, "verdict": "UNANIMOUS_CONSENSUS"},
    )


def run_acceptance_pipeline(
    config: Optional[SyncConfig] = None,
    artifact: Optional[TruthArtifact] = None,
    verbose: bool = True,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Executes the complete Acceptance Criteria verification pipeline:
    1. Injects artifact.
    2. Runs CanonicalSyncEngine.
    3. Asserts PySpark, Obsidian, Git, and Google Drive destination propagation.
    4. Strictly verifies cryptographic SHA-256 parity across all 4 destinations.

    Returns:
        (success: bool, report: Dict[str, Any])
    """
    cleanup_temp = False
    temp_dir: Optional[tempfile.TemporaryDirectory] = None

    if config is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="canonical_sync_acceptance_")
        config = SyncConfig.for_testing(temp_dir.name)
        (config.git_repo_path / ".git").mkdir(parents=True, exist_ok=True)
        cleanup_temp = True

    if artifact is None:
        artifact = create_synthetic_truth_audit_artifact()

    report: Dict[str, Any] = {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type.value,
        "expected_sha256": artifact.sha256_hash,
        "destinations": {},
        "parity_verified": False,
        "engine_success": False,
        "errors": [],
    }

    def log(msg: str):
        if verbose:
            print(msg)

    try:
        log("=" * 80)
        log("🚀 CANONICAL SYNC ENGINE — ACCEPTANCE VERIFICATION RUNNER")
        log("=" * 80)
        log(f"📦 Injecting Dummy Artifact : [{artifact.artifact_type.value}] {artifact.artifact_id}")
        log(f"🔑 Expected SHA-256 Hash    : {artifact.sha256_hash}")
        log(f"📂 Sandbox Base Directory   : {config.obsidian_vault_path.parent}")
        log("-" * 80)

        # 1. Initialize Engine and execute Sync
        engine = CanonicalSyncEngine(config=config, auto_heal=True)
        sync_result: QuadVaultSyncResult = engine.sync_truth_artifact(
            artifact=artifact,
            verify_first=True,
            parallel=True,
        )

        report["engine_success"] = sync_result.success
        report["sync_result"] = sync_result.to_dict()

        if not sync_result.success:
            err = f"Engine synchronization failed: {sync_result.errors}"
            log(f"❌ {err}")
            report["errors"].append(err)
            return False, report

        log("✅ Engine Synchronization Pipeline Completed Successfully.")
        log("-" * 80)

        # ---------------------------------------------------------------------
        # 2a. Destination Assertion: PySpark Data Lake
        # ---------------------------------------------------------------------
        log("🔍 [1/4] Verifying PySpark Data Lake Propagation...")
        master_jsonl = config.pyspark_dataset_path / "truth_audit_master.jsonl"
        if not master_jsonl.exists():
            err = f"PySpark master JSONL not found at {master_jsonl}"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        pyspark_lines = master_jsonl.read_text(encoding="utf-8").strip().splitlines()
        pyspark_matched_record = None
        for line in pyspark_lines:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                if rec.get("artifact_id") == artifact.artifact_id:
                    pyspark_matched_record = rec
                    break
            except json.JSONDecodeError as je:
                log(f"  ⚠️ Warning: encountered unparseable line in JSONL: {je}")

        if pyspark_matched_record is None:
            err = f"PySpark JSONL does not contain artifact_id '{artifact.artifact_id}'"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        recon_pyspark = TruthArtifact.from_dict(pyspark_matched_record)
        pyspark_hash = recon_pyspark.compute_hash()
        pyspark_valid = (
            recon_pyspark.sha256_hash == artifact.sha256_hash
            and pyspark_hash == artifact.sha256_hash
        )

        report["destinations"]["pyspark"] = {
            "path": str(master_jsonl),
            "sha256_hash": recon_pyspark.sha256_hash,
            "computed_hash": pyspark_hash,
            "valid": pyspark_valid,
        }

        if not pyspark_valid:
            err = f"PySpark hash mismatch: Got {recon_pyspark.sha256_hash}, Expected {artifact.sha256_hash}"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        log(f"  ✅ PySpark JSONL verified (SHA-256: {pyspark_hash})")

        # ---------------------------------------------------------------------
        # 2b. Destination Assertion: Obsidian Knowledge Graph
        # ---------------------------------------------------------------------
        log("🔍 [2/4] Verifying Obsidian Knowledge Graph Propagation...")
        obsidian_note = config.obsidian_vault_path / "truth_artifacts" / f"{artifact.artifact_id}.md"
        if not obsidian_note.exists():
            # Check direct fallback
            direct_obsidian = config.obsidian_vault_path / f"{artifact.artifact_id}.md"
            if direct_obsidian.exists():
                obsidian_note = direct_obsidian
            else:
                err = f"Obsidian note file not found at {obsidian_note}"
                log(f"  ❌ {err}")
                report["errors"].append(err)
                return False, report

        obs_content = obsidian_note.read_text(encoding="utf-8")

        # Verify YAML frontmatter and mandatory fields
        has_frontmatter = obs_content.startswith("---") and "\n---\n" in obs_content
        has_id = f'artifact_id: "{artifact.artifact_id}"' in obs_content or f"artifact_id: '{artifact.artifact_id}'" in obs_content
        has_hash = artifact.sha256_hash in obs_content

        # Verify mandatory bidirectional Wikilinks
        mandatory_wikilinks = [
            "[[Index]]",
            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
            f"[[{artifact.artifact_type.value}]]",
        ]
        wikilinks_found = [link for link in mandatory_wikilinks if link in obs_content]
        missing_wikilinks = [link for link in mandatory_wikilinks if link not in obs_content]

        # Parse frontmatter and payload back into TruthArtifact
        obs_syncer = engine.syncers["obsidian"]
        recon_obs = obs_syncer.read(artifact.artifact_id)

        obs_valid = (
            has_frontmatter
            and has_id
            and has_hash
            and len(missing_wikilinks) == 0
            and recon_obs is not None
            and recon_obs.sha256_hash == artifact.sha256_hash
            and recon_obs.compute_hash() == artifact.sha256_hash
        )

        report["destinations"]["obsidian"] = {
            "path": str(obsidian_note),
            "sha256_hash": recon_obs.sha256_hash if recon_obs else "",
            "wikilinks": wikilinks_found,
            "missing_wikilinks": missing_wikilinks,
            "valid": obs_valid,
        }

        if not obs_valid:
            err = f"Obsidian validation failed: missing_wikilinks={missing_wikilinks}, valid={obs_valid}"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        log(f"  ✅ Obsidian note verified with Wikilinks {wikilinks_found} (SHA-256: {recon_obs.sha256_hash})")

        # ---------------------------------------------------------------------
        # 2c. Destination Assertion: Git Monorepo Working Tree
        # ---------------------------------------------------------------------
        log("🔍 [3/4] Verifying Git Monorepo Working Tree Propagation...")
        git_file = config.git_repo_path / "04_data_and_memory" / "core_data" / f"{artifact.artifact_id}.json"
        if not git_file.exists():
            alt_git = config.git_repo_path / "core_data" / f"{artifact.artifact_id}.json"
            if alt_git.exists():
                git_file = alt_git
            else:
                err = f"Git worktree JSON file not found at {git_file}"
                log(f"  ❌ {err}")
                report["errors"].append(err)
                return False, report

        git_content = git_file.read_text(encoding="utf-8")
        git_data = json.loads(git_content)
        recon_git = TruthArtifact.from_dict(git_data)
        git_hash = recon_git.compute_hash()

        git_valid = (
            recon_git.artifact_id == artifact.artifact_id
            and recon_git.sha256_hash == artifact.sha256_hash
            and git_hash == artifact.sha256_hash
            and recon_git.payload == artifact.payload
        )

        report["destinations"]["git"] = {
            "path": str(git_file),
            "sha256_hash": recon_git.sha256_hash,
            "computed_hash": git_hash,
            "valid": git_valid,
        }

        if not git_valid:
            err = f"Git worktree JSON validation failed: Got {recon_git.sha256_hash}, Expected {artifact.sha256_hash}"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        log(f"  ✅ Git worktree JSON verified (SHA-256: {git_hash})")

        # ---------------------------------------------------------------------
        # 2d. Destination Assertion: Google Drive Cloud Mirror / Fallback Cache
        # ---------------------------------------------------------------------
        log("🔍 [4/4] Verifying Google Drive Cloud Mirror Propagation...")
        gdrive_syncer = engine.syncers["gdrive"]
        dest_dir, tier_used = gdrive_syncer.resolve_destination()
        gdrive_file = dest_dir / f"{artifact.artifact_id}.json"

        if not gdrive_file.exists():
            # Check fallback path directly
            fallback_path = config.gdrive_fallback_cache_path / "truth_artifacts" / f"{artifact.artifact_id}.json"
            if fallback_path.exists():
                gdrive_file = fallback_path
            else:
                err = f"Google Drive artifact file not found at {gdrive_file} or {fallback_path}"
                log(f"  ❌ {err}")
                report["errors"].append(err)
                return False, report

        gdrive_content = gdrive_file.read_text(encoding="utf-8")
        gdrive_data = json.loads(gdrive_content)
        recon_gdrive = TruthArtifact.from_dict(gdrive_data)
        gdrive_hash = recon_gdrive.compute_hash()

        gdrive_valid = (
            recon_gdrive.artifact_id == artifact.artifact_id
            and recon_gdrive.sha256_hash == artifact.sha256_hash
            and gdrive_hash == artifact.sha256_hash
            and recon_gdrive.payload == artifact.payload
        )

        report["destinations"]["gdrive"] = {
            "path": str(gdrive_file),
            "tier_used": tier_used,
            "sha256_hash": recon_gdrive.sha256_hash,
            "computed_hash": gdrive_hash,
            "valid": gdrive_valid,
        }

        if not gdrive_valid:
            err = f"Google Drive validation failed: Got {recon_gdrive.sha256_hash}, Expected {artifact.sha256_hash}"
            log(f"  ❌ {err}")
            report["errors"].append(err)
            return False, report

        log(f"  ✅ Google Drive mirrored JSON verified via [{tier_used}] (SHA-256: {gdrive_hash})")

        # ---------------------------------------------------------------------
        # 2e. Cryptographic SHA-256 Parity Verification Across All 4 Destinations
        # ---------------------------------------------------------------------
        log("-" * 80)
        log("🔐 Asserting Strict Cryptographic SHA-256 Parity Across All 4 Vaults...")
        extracted_hashes = {
            "artifact": artifact.sha256_hash.lower(),
            "pyspark": report["destinations"]["pyspark"]["sha256_hash"].lower(),
            "obsidian": report["destinations"]["obsidian"]["sha256_hash"].lower(),
            "git": report["destinations"]["git"]["sha256_hash"].lower(),
            "gdrive": report["destinations"]["gdrive"]["sha256_hash"].lower(),
        }

        unique_hashes = set(extracted_hashes.values())
        if len(unique_hashes) != 1 or artifact.sha256_hash.lower() not in unique_hashes:
            err = f"Cryptographic parity violation! Hashes do not match: {extracted_hashes}"
            log(f"❌ {err}")
            report["errors"].append(err)
            report["parity_verified"] = False
            return False, report

        report["parity_verified"] = True
        report["exact_matched_sha256"] = artifact.sha256_hash

        log(f"✅ Cryptographic SHA-256 Parity Invariant Confirmed: {artifact.sha256_hash}")
        log("=" * 80)
        log("🎉 ALL ACCEPTANCE CRITERIA SATISFIED — CODE 0")
        log("=" * 80)
        return True, report

    finally:
        if cleanup_temp and temp_dir is not None:
            try:
                temp_dir.cleanup()
            except Exception:
                pass


# -----------------------------------------------------------------------------
# Pytest Integration Test Functions
# -----------------------------------------------------------------------------

def test_acceptance_criteria_e2e_pipeline_truth_audit(tmp_path: Path):
    """
    Pytest test case asserting full acceptance criteria for TRUTH_AUDIT artifact.
    """
    config = SyncConfig.for_testing(tmp_path)
    artifact = create_synthetic_truth_audit_artifact(artifact_id="art-test-audit-accept")
    success, report = run_acceptance_pipeline(config=config, artifact=artifact, verbose=False)
    assert success is True, f"Acceptance pipeline failed with errors: {report['errors']}"
    assert report["parity_verified"] is True
    assert report["engine_success"] is True
    assert report["destinations"]["pyspark"]["valid"] is True
    assert report["destinations"]["obsidian"]["valid"] is True
    assert report["destinations"]["git"]["valid"] is True
    assert report["destinations"]["gdrive"]["valid"] is True


def test_acceptance_criteria_e2e_pipeline_ai_debate_consensus(tmp_path: Path):
    """
    Pytest test case asserting full acceptance criteria for AI_DEBATE_CONSENSUS artifact.
    """
    config = SyncConfig.for_testing(tmp_path)
    artifact = create_synthetic_ai_debate_artifact(artifact_id="art-test-debate-accept")
    success, report = run_acceptance_pipeline(config=config, artifact=artifact, verbose=False)
    assert success is True, f"Acceptance pipeline failed with errors: {report['errors']}"
    assert report["parity_verified"] is True
    assert "[[ai_debate_consensus]]" in report["destinations"]["obsidian"]["wikilinks"]


def test_acceptance_strict_sha256_tamper_detection(tmp_path: Path):
    """
    Pytest test case asserting that tampered hash is immediately rejected
    and does not satisfy acceptance parity.
    """
    config = SyncConfig.for_testing(tmp_path)
    artifact = create_synthetic_truth_audit_artifact()
    artifact.sha256_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    success, report = run_acceptance_pipeline(config=config, artifact=artifact, verbose=False)
    assert success is False
    assert report["engine_success"] is False
    assert len(report["errors"]) > 0


# -----------------------------------------------------------------------------
# Standalone CLI Entry Point
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonical Sync Engine - Acceptance Verification Test Script"
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default=None,
        help="Optional base directory to run acceptance tests against (defaults to isolated temp sandbox).",
    )
    parser.add_argument(
        "--type",
        type=str,
        default="truth_audit",
        choices=["truth_audit", "ai_debate_consensus"],
        help="Artifact type to inject for acceptance verification.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON summary report.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable logs.",
    )

    args = parser.parse_args()

    config = None
    if args.base_dir:
        config = SyncConfig.for_testing(Path(args.base_dir))

    if args.type == "ai_debate_consensus":
        artifact = create_synthetic_ai_debate_artifact()
    else:
        artifact = create_synthetic_truth_audit_artifact()

    verbose = not args.quiet and not args.json
    success, report = run_acceptance_pipeline(
        config=config,
        artifact=artifact,
        verbose=verbose,
    )

    if args.json:
        print(json.dumps(report, indent=2))

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
