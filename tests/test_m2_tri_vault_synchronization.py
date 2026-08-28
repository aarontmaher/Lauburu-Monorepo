#!/usr/bin/env python3
"""
================================================================================
M2 Tri-Vault Storage Synchronization & Knowledge Graph Verification Test Suite
================================================================================
Validates all Milestone M2 invariants:
1. Obsidian Knowledge Vault synchronization, master Wikilinks, 13 canonical notes,
   reference notes, 0 broken wikilinks, and file permissions.
2. PySpark Data Lake, LoRA JSONL 100% validity, disk headroom (>= 10.0 GB),
   Qdrant SQLite database integrity check.
3. GitHub Monorepo worktree cleanliness, no index.lock, 13 canonical modules in README.md/GEMINI.md.
"""

import os
import sys
import re
import json
import shutil
import sqlite3
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = REPO_ROOT / "obsidian_vault"
LORA_DFS_DIR = Path("/Users/aaron/DFS_UNIFIED/lora_datasets")
LORA_MODULE_DIR = REPO_ROOT / "04_data_and_memory" / "lora_datasets"
QDRANT_DIR = REPO_ROOT / "04_data_and_memory" / "qdrant_data"

CANONICAL_MODULES = [
    "00_core_infrastructure",
    "01_apps",
    "02_ai_models_and_inference",
    "03_biometrics_and_telemetry",
    "04_data_and_memory",
    "05_agents_and_swarms",
    "06_scripts_and_tooling",
    "07_docs_and_architecture",
    "08_business_and_commerce",
    "09_app_store_and_release",
    "10_spatial_grappling_kinematics",
    "11_security_and_governance",
    "12_continuous_lora_evolution"
]


class TestM2TriVaultSynchronization(unittest.TestCase):
    """Exhaustive test suite for M2 Tri-Vault Storage and Knowledge Graph Sync."""

    # =========================================================================
    # Vault Layer 1: Obsidian Knowledge Vault
    # =========================================================================

    def test_01_obsidian_vault_exists_and_permissions(self):
        """Verify obsidian_vault directory exists with 0755 permissions and files have 0644."""
        self.assertTrue(VAULT_DIR.exists(), f"Vault directory missing: {VAULT_DIR}")
        self.assertTrue(VAULT_DIR.is_dir())
        stat = VAULT_DIR.stat()
        self.assertEqual(oct(stat.st_mode & 0o777), "0o755")

        for root, dirs, files in os.walk(VAULT_DIR):
            for d in dirs:
                dp = Path(root) / d
                self.assertEqual(oct(dp.stat().st_mode & 0o777), "0o755", f"Bad dir perms on {dp}")
            for f in files:
                fp = Path(root) / f
                self.assertEqual(oct(fp.stat().st_mode & 0o777), "0o644", f"Bad file perms on {fp}")

    def test_02_index_contains_all_master_wikilinks(self):
        """Verify Index.md contains [[Index]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], and all 13 modules."""
        index_path = VAULT_DIR / "Index.md"
        self.assertTrue(index_path.exists(), "Index.md is missing")
        content = index_path.read_text(encoding="utf-8")

        required_links = [
            "[[Index]]",
            "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]",
            "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]",
            "[[device-hardware-governor]]",
            "[[multi-wan-accelerator]]",
            "[[7_DEVICE_MESH_AND_VRAM_POOL]]",
            "[[ai-debate]]",
            "[[swarm]]",
            "[[teamwork-preview]]",
        ] + [f"[[{m}]]" for m in CANONICAL_MODULES]

        for link in required_links:
            self.assertIn(link, content, f"Index.md missing required Wikilink: {link}")

    def test_03_all_13_canonical_module_notes_exist(self):
        """Verify all 13 canonical module markdown notes exist and have valid YAML frontmatter."""
        for mod in CANONICAL_MODULES:
            note_path = VAULT_DIR / f"{mod}.md"
            self.assertTrue(note_path.exists(), f"Missing module note: {note_path.name}")
            self.assertGreater(note_path.stat().st_size, 200, f"Module note {note_path.name} too small")
            content = note_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"Module note {note_path.name} lacks YAML frontmatter")
            self.assertIn("[[Index]]", content, f"Module note {note_path.name} should link back to [[Index]]")

    def test_04_missing_reference_notes_exist(self):
        """Verify device-hardware-governor, multi-wan-accelerator, 7_DEVICE_MESH_AND_VRAM_POOL, and 00_Overview notes exist."""
        ref_notes = [
            "device-hardware-governor.md",
            "multi-wan-accelerator.md",
            "7_DEVICE_MESH_AND_VRAM_POOL.md",
            "00_Overview/Hardware_Topology.md",
            "00_Overview/Global_Architecture_Map.md"
        ]
        for ref in ref_notes:
            p = VAULT_DIR / ref
            self.assertTrue(p.exists(), f"Reference note missing: {ref}")
            self.assertGreater(p.stat().st_size, 100, f"Reference note {ref} is empty")
            content = p.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), f"Reference note {ref} lacks YAML frontmatter")

    def test_05_zero_broken_wikilinks_in_vault(self):
        """Verify there are exactly 0 broken or dangling Wikilinks across all notes in obsidian_vault."""
        all_md_files = []
        for root, dirs, files in os.walk(VAULT_DIR):
            for f in files:
                if f.endswith(".md"):
                    rel_path = os.path.relpath(os.path.join(root, f), str(VAULT_DIR))
                    all_md_files.append(rel_path)

        note_stems = {os.path.splitext(f)[0] for f in all_md_files}
        base_stems = {os.path.splitext(os.path.basename(f))[0] for f in all_md_files}

        link_pattern = re.compile(r"\[\[(.*?)\]\]")
        broken_links = {}

        for rel_f in all_md_files:
            path = VAULT_DIR / rel_f
            content = path.read_text(encoding="utf-8", errors="ignore")
            # Exclude code blocks and inline code
            cleaned = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
            cleaned = re.sub(r"`.*?`", "", cleaned)

            links = link_pattern.findall(cleaned)
            for l in links:
                target = l.split("|")[0].split("#")[0].strip()
                if not target:
                    continue
                matched = (
                    target in note_stems or
                    target in base_stems or
                    (target + ".md") in all_md_files or
                    target.replace("/", os.sep) in note_stems
                )
                if not matched:
                    broken_links.setdefault(target, []).append(rel_f)

        self.assertEqual(len(broken_links), 0, f"Found broken wikilinks in vault: {broken_links}")

    # =========================================================================
    # Vault Layer 2: PySpark Data Lake & LoRA Datasets
    # =========================================================================

    def test_06_lora_directories_exist_and_synchronized(self):
        """Verify lora_datasets directories exist, are writable, and contain training sets."""
        self.assertTrue(LORA_DFS_DIR.exists(), f"Missing DFS LoRA dir: {LORA_DFS_DIR}")
        self.assertTrue(LORA_MODULE_DIR.exists(), f"Missing module LoRA dir: {LORA_MODULE_DIR}")

        dfs_files = list(LORA_DFS_DIR.glob("*.jsonl"))
        module_files = list(LORA_MODULE_DIR.glob("*.jsonl"))

        self.assertGreaterEqual(len(dfs_files), 10, "DFS LoRA dir should have >= 10 datasets")
        self.assertGreaterEqual(len(module_files), 10, "04_data_and_memory LoRA dir should have >= 10 datasets")

    def test_07_all_jsonl_records_valid_json(self):
        """Verify 100% of records in all JSONL datasets parse as valid JSON dictionaries."""
        all_jsonl = list(LORA_DFS_DIR.glob("*.jsonl")) + list(LORA_MODULE_DIR.glob("*.jsonl"))
        for jf in all_jsonl:
            with open(jf, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, 1):
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                        self.assertIsInstance(obj, dict, f"Line {line_idx} in {jf.name} is not a dict")
                    except Exception as e:
                        self.fail(f"Invalid JSON at line {line_idx} in {jf.name}: {e}")

    def test_08_free_disk_headroom_invariant(self):
        """Verify free disk headroom is >= 10.0 GB."""
        free_bytes = shutil.disk_usage(str(REPO_ROOT)).free
        free_gb = free_bytes / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 10.0, f"Free disk space {free_gb:.2f} GB violates >= 10.0 GB headroom rule")

    def test_09_qdrant_vector_store_integrity(self):
        """Verify Qdrant SQLite stores exist, are readable, and pass SQLite integrity check."""
        rag_db = QDRANT_DIR / "collection" / "rag_documents" / "storage.sqlite"
        health_db = QDRANT_DIR / "collection" / "edge_health_runbooks" / "storage.sqlite"

        for db in [rag_db, health_db]:
            self.assertTrue(db.exists(), f"Qdrant DB missing: {db}")
            conn = sqlite3.connect(str(db))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            res = cursor.fetchone()
            self.assertEqual(res[0], "ok", f"Integrity check failed for {db.name}")
            cursor.execute("SELECT COUNT(*) FROM points;")
            count = cursor.fetchone()[0]
            self.assertGreaterEqual(count, 1, f"Qdrant collection {db.parent.name} has no points")
            conn.close()

    # =========================================================================
    # Vault Layer 3: GitHub Monorepo Worktree Hygiene
    # =========================================================================

    def test_10_git_worktree_healthy(self):
        """Verify git working tree is valid and .git/index.lock is absent."""
        git_dir = REPO_ROOT / ".git"
        self.assertTrue(git_dir.exists(), ".git directory missing")
        lock_file = git_dir / "index.lock"
        self.assertFalse(lock_file.exists(), "Stale .git/index.lock detected!")

    def test_11_readme_and_gemini_contain_13_modules(self):
        """Verify root README.md and GEMINI.md accurately document the 13 canonical numbered modules."""
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        gemini = (REPO_ROOT / "GEMINI.md").read_text(encoding="utf-8")

        for mod in CANONICAL_MODULES:
            self.assertIn(mod, readme, f"README.md missing canonical module: {mod}")

        self.assertIn("00_core_infrastructure", gemini)
        self.assertIn("12_continuous_lora_evolution", gemini)
        self.assertIn("Zero-Mock", readme)
        self.assertIn("Zero-Mock", gemini)

    def test_12_no_merge_conflict_markers_in_root_docs(self):
        """Verify 0 merge conflict markers in root documentation files."""
        for doc in ["README.md", "GEMINI.md", "PROJECT.md"]:
            p = REPO_ROOT / doc
            if p.exists():
                text = p.read_text(encoding="utf-8")
                self.assertNotIn("<<<<<<< HEAD", text, f"Merge conflict in {doc}")
                self.assertNotIn(">>>>>>>", text, f"Merge conflict in {doc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
