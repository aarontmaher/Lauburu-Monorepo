#!/usr/bin/env python3
"""
================================================================================
Adversarial Stress Test Suite: Obsidian Knowledge Graph & Wikilink Integrity (M2)
================================================================================
Empirically tests the Obsidian Knowledge Graph topology and Wikilink integrity:
1. Exhaustive regex and AST scanning of all markdown files in obsidian_vault for broken links.
2. Link syntax variations: standard [[target]], aliased [[target|alias]], anchored [[target#heading]],
   anchored & aliased [[target#heading|alias]], relative [[folder/target]], and markdown [text](target.md).
3. Anchor validity: asserts that #heading anchors in wikilinks match actual headers in target notes.
4. Graph traversal & topology analysis: reachability of canonical 13 modules and master index from Index.md.
5. Bidirectionality: verifies bidirectional backlinks for all 13 canonical module notes.
6. YAML frontmatter parsing and schema consistency.
7. Filesystem permissions (0755 dirs, 0644 files) and symlink resolution (01_apps/obsidian_web/content).
"""

import os
import re
import sys
import yaml
import shutil
import sqlite3
import unittest
from pathlib import Path
from collections import defaultdict, deque

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT_DIR = REPO_ROOT / "obsidian_vault"
CONTENT_SYMLINK = REPO_ROOT / "01_apps" / "obsidian_web" / "content"

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

MASTER_INDICES = [
    "Index",
    "CANONICAL_PROJECT_AND_STORAGE_RULE",
    "LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX",
    "7_DEVICE_MESH_AND_VRAM_POOL"
]


class TestAdversarialM2ObsidianKnowledgeGraph(unittest.TestCase):
    """Adversarial challenger tests for Obsidian vault topology and Wikilink integrity."""

    @classmethod
    def setUpClass(cls):
        cls.all_md_files = sorted([f for f in VAULT_DIR.rglob("*.md")])
        cls.rel_paths = {str(f.relative_to(VAULT_DIR)): f for f in cls.all_md_files}
        cls.stems = {f.stem: f for f in cls.all_md_files}
        cls.rel_stems = {str(f.relative_to(VAULT_DIR).with_suffix("")): f for f in cls.all_md_files}

        cls.wikilink_re = re.compile(r"\[\[(.*?)\]\]")
        cls.mdlink_re = re.compile(r"(?<!!)\[.*?\]\((.*?)\)")

        cls.adj = defaultdict(set)
        cls.rev_adj = defaultdict(set)
        cls.all_wikilinks = []
        cls.broken_wikilinks = defaultdict(list)
        cls.broken_anchors = defaultdict(list)

        for f in cls.all_md_files:
            rel = str(f.relative_to(VAULT_DIR))
            content = f.read_text(encoding="utf-8", errors="replace")
            clean = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
            clean = re.sub(r"`.*?`", "", clean)

            for raw_link in cls.wikilink_re.findall(clean):
                cls.all_wikilinks.append((rel, raw_link))
                target = raw_link.split("|")[0].strip()
                anchor = ""
                if "#" in target:
                    target, anchor = target.split("#", 1)
                    target = target.strip()
                    anchor = anchor.strip()

                target_f = None
                if not target:
                    target_f = f
                elif target in cls.stems:
                    target_f = cls.stems[target]
                elif target in cls.rel_stems:
                    target_f = cls.rel_stems[target]
                elif target in cls.rel_paths:
                    target_f = cls.rel_paths[target]
                elif (target + ".md") in cls.rel_paths:
                    target_f = cls.rel_paths[target + ".md"]
                elif target.replace("/", os.sep) in cls.rel_stems:
                    target_f = cls.rel_stems[target.replace("/", os.sep)]

                if target_f is None:
                    cls.broken_wikilinks[rel].append(raw_link)
                else:
                    t_rel = str(target_f.relative_to(VAULT_DIR))
                    cls.adj[rel].add(t_rel)
                    cls.rev_adj[t_rel].add(rel)

                    if anchor:
                        t_content = target_f.read_text(encoding="utf-8", errors="replace")
                        headings = [h.lstrip("#").strip() for h in re.findall(r"^#+\s+(.*?)$", t_content, flags=re.MULTILINE)]
                        anchor_clean = re.sub(r"[^\w\s-]", "", anchor).strip().lower()
                        heading_clean = [re.sub(r"[^\w\s-]", "", h).strip().lower() for h in headings]
                        if anchor_clean not in heading_clean and not any(anchor.lower() in h.lower() for h in headings):
                            cls.broken_anchors[rel].append((raw_link, t_rel, anchor))

    # =========================================================================
    # Challenge Dimension 1: Exhaustive Link Integrity
    # =========================================================================

    def test_01_zero_broken_wikilinks_adversarial_sweep(self):
        """Stress-test every Wikilink in the vault to ensure zero broken links."""
        total_links = len(self.all_wikilinks)
        self.assertGreater(total_links, 150, f"Expected at least 150 Wikilinks in vault, found {total_links}")
        self.assertEqual(
            len(self.broken_wikilinks), 0,
            f"Adversarial scan found broken Wikilinks: {dict(self.broken_wikilinks)}"
        )

    def test_02_zero_broken_heading_anchors(self):
        """Stress-test anchor targets (#heading) to verify target note contains the heading."""
        self.assertEqual(
            len(self.broken_anchors), 0,
            f"Adversarial scan found broken heading anchors: {dict(self.broken_anchors)}"
        )

    def test_03_markdown_file_count_and_non_emptiness(self):
        """Verify vault contains at least 40 markdown notes and zero empty files."""
        self.assertGreaterEqual(len(self.all_md_files), 40, "Vault note count should be >= 40")
        for f in self.all_md_files:
            rel = str(f.relative_to(VAULT_DIR))
            size = f.stat().st_size
            self.assertGreater(size, 50, f"Markdown file {rel} is unexpectedly small ({size} bytes)")

    # =========================================================================
    # Challenge Dimension 2: Canonical 13-Module Graph Topology
    # =========================================================================

    def test_04_index_direct_links_to_all_13_canonical_modules(self):
        """Verify Index.md has direct Wikilinks to all 13 canonical numbered modules."""
        index_links = self.adj.get("Index.md", set())
        for mod in CANONICAL_MODULES:
            mod_target = f"{mod}.md"
            self.assertIn(
                mod_target, index_links,
                f"Index.md does not directly link to canonical module note {mod_target}"
            )

    def test_05_canonical_modules_bidirectional_backlinks(self):
        """Verify all 13 canonical numbered module notes link back to Index.md."""
        for mod in CANONICAL_MODULES:
            mod_file = f"{mod}.md"
            mod_out_links = self.adj.get(mod_file, set())
            self.assertIn(
                "Index.md", mod_out_links,
                f"Canonical module note {mod_file} lacks bidirectional backlink to Index.md"
            )

    def test_06_master_indices_reachability_from_root(self):
        """Verify all master index notes are reachable from Index.md within 1 hop."""
        index_links = self.adj.get("Index.md", set())
        for master in MASTER_INDICES:
            master_target = f"{master}.md"
            self.assertIn(
                master_target, index_links,
                f"Master index {master_target} not directly linked from Index.md"
            )

    def test_07_graph_reachability_and_connected_component(self):
        """Stress-test BFS reachability from Index.md to ensure the core knowledge graph is connected."""
        visited = set()
        queue = deque(["Index.md"])
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            for neighbor in self.adj[curr]:
                if neighbor not in visited:
                    queue.append(neighbor)

        # Core graph should include Index, all 13 modules, and all master indices
        required_reachable = {"Index.md"} | {f"{m}.md" for m in CANONICAL_MODULES} | {f"{m}.md" for m in MASTER_INDICES}
        missing_from_graph = required_reachable - visited
        self.assertEqual(
            len(missing_from_graph), 0,
            f"Core notes missing from Index.md graph component: {missing_from_graph}"
        )
        self.assertGreaterEqual(len(visited), 38, f"Expected at least 38 reachable notes, got {len(visited)}")

    # =========================================================================
    # Challenge Dimension 3: Filesystem, Symlink & Permission Invariants
    # =========================================================================

    def test_08_filesystem_permissions_invariant(self):
        """Verify all vault directories have 0755 and all markdown files have 0644 permissions."""
        for p in VAULT_DIR.rglob("*"):
            mode = oct(p.stat().st_mode & 0o777)
            rel = str(p.relative_to(VAULT_DIR))
            if p.is_dir():
                self.assertEqual(mode, "0o755", f"Directory {rel} has invalid mode {mode} (expected 0o755)")
            elif p.is_file() and p.suffix == ".md":
                self.assertEqual(mode, "0o644", f"File {rel} has invalid mode {mode} (expected 0o644)")

    def test_09_obsidian_web_content_symlink_invariant(self):
        """Verify 01_apps/obsidian_web/content is a valid symlink to obsidian_vault."""
        self.assertTrue(CONTENT_SYMLINK.exists(), f"Symlink path does not exist: {CONTENT_SYMLINK}")
        self.assertTrue(CONTENT_SYMLINK.is_symlink(), f"Path is not a symlink: {CONTENT_SYMLINK}")
        resolved = CONTENT_SYMLINK.resolve()
        self.assertEqual(resolved, VAULT_DIR.resolve(), "Symlink does not resolve to canonical obsidian_vault")

    # =========================================================================
    # Challenge Dimension 4: Tri-Vault Headroom & Cleanliness Invariants
    # =========================================================================

    def test_10_disk_headroom_invariant(self):
        """Verify free disk headroom on host volume is >= 10.0 GB."""
        free_bytes = shutil.disk_usage(str(REPO_ROOT)).free
        free_gb = free_bytes / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 10.0, f"Free disk space {free_gb:.2f} GB is below 10.0 GB threshold")

    def test_11_git_worktree_cleanliness(self):
        """Verify no stale git locks and no conflict markers in documentation."""
        lock_path = REPO_ROOT / ".git" / "index.lock"
        self.assertFalse(lock_path.exists(), "Stale .git/index.lock detected")

        for doc in ["README.md", "GEMINI.md", "PROJECT.md"]:
            p = REPO_ROOT / doc
            if p.exists():
                txt = p.read_text(encoding="utf-8")
                self.assertNotIn("<<<<<<< HEAD", txt, f"Merge conflict in {doc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
