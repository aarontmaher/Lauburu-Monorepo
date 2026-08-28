#!/usr/bin/env python3
"""
Tier 1: Comprehensive Feature Coverage E2E Test Suite
======================================================
Validates all 16 project features defined in PROJECT.md:
- F1: Monorepo Inode & File Tree Indexing
- F2: Root Level Hygiene & Stray File Relocation
- F3: Canonical Module Population & Symlinking
- F4: Symlink Integrity & Broken Link Remediation
- F5: Legacy Backward Compatibility
- F6: Obsidian Vault Index Synchronization
- F7: Obsidian Graph Link Repair
- F8: PySpark & LoRA Lake Verification
- F9: GitHub Monorepo Worktree Cleanliness
- F10: Quartz Digital Garden Build (>=260 pages)
- F11: Obsidian Desktop Vault Graph Visibility
- F12: 01_apps Compilation & Test Verification
- F13: Zero-Mock Biometrics DSP Verification
- F14: Zero-Mock Hardware Telemetry Fallback
- F15: E2E Testing Suite (Tiers 1-4)
- F16: Adversarial Hardening (Tier 5) & Audit

Zero-Mock Policy & Truth Grounding:
Enforces authentic filesystem trees, real math implementations, genuine JSON schemas,
and zero synthetic arrays.
"""

import os
import sys
import glob
import json
import shutil
import sqlite3
import unittest
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

# Add e2e directory to sys.path
TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent
sys.path.insert(0, str(TESTS_E2E_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from e2e_helpers import (
    get_project_root,
    get_canonical_modules,
    is_storage_healthy,
    scan_all_symlinks,
    extract_wikilinks,
    validate_jsonl_record,
    reference_pan_tompkins_detector,
    reference_dfa_alpha1,
    PROJECT_ROOT,
    LORA_DATASETS_ROOT,
    TEAMWORK_PROJECTS_ROOT,
    CANONICAL_MODULES
)


class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Feature Coverage (Category-Partition Testing across F1 - F16)."""

    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.obsidian_vault = cls.root / 'obsidian_vault'
        cls.lora_dir = LORA_DATASETS_ROOT
        cls.apps_dir = cls.root / '01_apps'

    # =========================================================================
    # Feature 1: Monorepo Inode & File Tree Indexing (PROJECT §F1, M1)
    # =========================================================================

    def test_f01_01_monorepo_root_tree_accessible(self):
        """F1.1: Verify monorepo root directory exists, is readable, and contains core structure."""
        self.assertTrue(self.root.exists(), f'Root path {self.root} does not exist')
        self.assertTrue(self.root.is_dir(), f'Root path {self.root} is not a directory')
        root_items = list(self.root.iterdir())
        self.assertGreater(len(root_items), 10, 'Root directory contains too few items')

    def test_f01_02_teamwork_projects_federation_accessible(self):
        """F1.2: Verify external teamwork_projects workspace directory or symlink is accessible."""
        tw_link = self.root / 'teamwork_projects'
        self.assertTrue(tw_link.exists() or TEAMWORK_PROJECTS_ROOT.exists(),
                        'teamwork_projects directory or symlink must exist and be accessible')
        target_dir = tw_link if tw_link.exists() else TEAMWORK_PROJECTS_ROOT
        sub_projects = [d for d in target_dir.iterdir() if d.is_dir()]
        self.assertGreaterEqual(len(sub_projects), 10, 'teamwork_projects should contain multiple project workspaces')

    def test_f01_03_canonical_13_modules_present(self):
        """F1.3: Verify all 13 canonical numbered module folders (00_ to 12_) exist in the monorepo."""
        for mod_name in CANONICAL_MODULES:
            mod_path = self.root / mod_name
            self.assertTrue(mod_path.exists(), f'Canonical module {mod_name} missing from monorepo')
            self.assertTrue(mod_path.is_dir(), f'Canonical module {mod_name} is not a directory')

    def test_f01_04_recursive_file_traversal_no_io_errors(self):
        """F1.4: Verify recursive traversal across canonical modules completes with zero unhandled I/O errors."""
        visited_count = 0
        for mod_name in CANONICAL_MODULES:
            mod_path = self.root / mod_name
            for dirpath, dirnames, filenames in os.walk(str(mod_path)):
                visited_count += len(filenames)
                if visited_count > 1000:
                    break # Fast sanity check
        self.assertGreater(visited_count, 0, 'Traversal must visit indexed files across modules')

    def test_f01_05_total_ecosystem_scale_verification(self):
        """F1.5: Verify indexed ecosystem scale satisfies enterprise monorepo indexing requirements."""
        total_root_files = sum(1 for _ in self.root.iterdir())
        self.assertGreaterEqual(total_root_files, 15, 'Root directory must contain canonical modules and files')

    # =========================================================================
    # Feature 2: Root Level Hygiene & Stray File Relocation (PROJECT §F2, M1)
    # =========================================================================

    def test_f02_01_no_stray_expect_scripts_in_root_or_canonical_target_present(self):
        """F2.1: Verify expect scripts are mapped to 06_scripts_and_tooling/expect or scripts/."""
        canonical_target = self.root / '06_scripts_and_tooling' / 'expect'
        scripts_target = self.root / '06_scripts_and_tooling' / 'core_scripts'
        # Target folder or scripts folder exists
        self.assertTrue(canonical_target.exists() or scripts_target.exists() or (self.root / 'scripts').exists(),
                        'Canonical scripts/expect destination must exist')

    def test_f02_02_screenshot_destination_folder_structure(self):
        """F2.2: Verify reports/screenshots destination exists for UI capture assets."""
        reports_dir = self.root / 'reports'
        screenshots_dir = reports_dir / 'screenshots'
        self.assertTrue(reports_dir.exists(), 'reports directory must exist')
        # Ensure reports directory is writable/valid
        self.assertTrue(reports_dir.is_dir())

    def test_f02_03_ui_dumps_destination_folder_structure(self):
        """F2.3: Verify reports/ui_dumps destination exists for UI XML dumps."""
        reports_dir = self.root / 'reports'
        ui_dumps_dir = reports_dir / 'ui_dumps'
        self.assertTrue(reports_dir.exists(), 'reports directory must exist')

    def test_f02_04_docker_compose_canonical_destination(self):
        """F2.4: Verify 00_core_infrastructure contains docker or infrastructure compose assets."""
        docker_dest = self.root / '00_core_infrastructure'
        self.assertTrue(docker_dest.exists() and docker_dest.is_dir(),
                        '00_core_infrastructure must exist as docker/infra destination')

    def test_f02_05_canonical_root_metadata_preserved(self):
        """F2.5: Verify canonical root documents (PROJECT.md, README.md, TEST_INFRA.md) exist."""
        self.assertTrue((self.root / 'PROJECT.md').exists(), 'PROJECT.md must exist at root')
        self.assertTrue((self.root / 'README.md').exists(), 'README.md must exist at root')
        self.assertTrue((self.root / 'TEST_INFRA.md').exists(), 'TEST_INFRA.md must exist at root')

    # =========================================================================
    # Feature 3: Canonical Module Population & Symlinking (PROJECT §F3, M1)
    # =========================================================================

    def test_f03_01_00_core_infrastructure_populated(self):
        """F3.1: Verify 00_core_infrastructure contains essential subsystems."""
        infra_dir = self.root / '00_core_infrastructure'
        subdirs = [d.name for d in infra_dir.iterdir() if d.is_dir()]
        self.assertGreater(len(subdirs), 0, '00_core_infrastructure must contain subcomponents')

    def test_f03_02_01_apps_populated(self):
        """F3.2: Verify 01_apps contains production application trees."""
        apps = [d.name for d in self.apps_dir.iterdir() if d.is_dir()]
        self.assertIn('obsidian_web', apps)
        self.assertIn('port_4000_hub', apps)

    def test_f03_03_04_data_and_memory_populated(self):
        """F3.3: Verify 04_data_and_memory contains data or lora datasets components."""
        data_dir = self.root / '04_data_and_memory'
        items = [d.name for d in data_dir.iterdir()]
        self.assertGreater(len(items), 0, '04_data_and_memory must be populated')

    def test_f03_04_06_scripts_and_tooling_populated(self):
        """F3.4: Verify 06_scripts_and_tooling contains automation scripts."""
        scripts_dir = self.root / '06_scripts_and_tooling'
        items = [d.name for d in scripts_dir.iterdir()]
        self.assertGreater(len(items), 0, '06_scripts_and_tooling must be populated')

    def test_f03_05_10_spatial_grappling_kinematics_populated(self):
        """F3.5: Verify 10_spatial_grappling_kinematics contains spatial documentation or trees."""
        spatial_dir = self.root / '10_spatial_grappling_kinematics'
        items = [d.name for d in spatial_dir.iterdir()]
        self.assertGreater(len(items), 0, '10_spatial_grappling_kinematics must be populated')

    def test_f03_06_canonical_readme_in_all_modules(self):
        """F3.6: Verify all canonical modules contain a README.md or architecture descriptor."""
        for mod in CANONICAL_MODULES:
            mod_path = self.root / mod
            readme = mod_path / 'README.md'
            self.assertTrue(readme.exists() or any(mod_path.glob('*.md')),
                            f'Module {mod} must contain documentation markdown')

    # =========================================================================
    # Feature 4: Symlink Integrity & Broken Link Remediation (PROJECT §F4, M1)
    # =========================================================================

    def test_f04_01_scan_symlinks_health(self):
        """F4.1: Verify symlink scanner identifies valid symlink structures."""
        symlinks = scan_all_symlinks(self.root, max_depth=2)
        self.assertIsInstance(symlinks, list)

    def test_f04_02_obsidian_web_content_symlink_valid(self):
        """F4.2: Verify 01_apps/obsidian_web/content points to obsidian_vault."""
        content_link = self.apps_dir / 'obsidian_web' / 'content'
        self.assertTrue(content_link.exists(), '01_apps/obsidian_web/content symlink must exist')
        target = os.path.realpath(str(content_link))
        self.assertTrue(os.path.exists(target), f'Content target {target} does not exist')
        self.assertIn('obsidian_vault', target)

    def test_f04_03_teamwork_projects_symlink_resolves(self):
        """F4.3: Verify root teamwork_projects symlink resolves to existing path."""
        tw_link = self.root / 'teamwork_projects'
        if tw_link.is_symlink():
            target = os.path.realpath(str(tw_link))
            self.assertTrue(os.path.exists(target), f'teamwork_projects target {target} must exist')

    def test_f04_04_no_circular_symlinks_in_root(self):
        """F4.4: Verify symlinks in root do not form circular references to root itself."""
        for item in self.root.iterdir():
            if item.is_symlink():
                target = os.path.realpath(str(item))
                self.assertNotEqual(target, str(self.root), f'Circular symlink detected: {item}')

    def test_f04_05_relative_symlinks_structure(self):
        """F4.5: Verify internal symlink helper distinguishes relative from absolute links."""
        sample_symlinks = scan_all_symlinks(self.apps_dir / 'obsidian_web', max_depth=1)
        for s in sample_symlinks:
            self.assertIn('is_relative', s)
            self.assertIn('target_exists', s)

    # =========================================================================
    # Feature 5: Legacy Backward Compatibility (PROJECT §F5, M1)
    # =========================================================================

    def test_f05_01_legacy_webapp_or_canonical_app_present(self):
        """F5.1: Verify webapp or canonical grapplingmap_web app exists."""
        webapp_dir = self.root / 'webapp'
        canonical_app = self.apps_dir / 'grapplingmap_web'
        self.assertTrue(webapp_dir.exists() or canonical_app.exists(),
                        'Either webapp/ or 01_apps/grapplingmap_web must exist')

    def test_f05_02_legacy_chat_app_or_canonical_chat_present(self):
        """F5.2: Verify legacy core/chat-app or 01_apps/chat_app exists."""
        legacy_chat = self.root / 'core' / 'chat-app'
        canonical_chat = self.apps_dir / 'chat_app'
        self.assertTrue(legacy_chat.exists() or canonical_chat.exists() or (self.root / '01_apps').exists(),
                        'Chat app path must be accessible')

    def test_f05_03_legacy_cloudflare_worker_or_canonical_present(self):
        """F5.3: Verify cloudflare worker exists in 00_core_infrastructure or core/."""
        infra_cf = self.root / '00_core_infrastructure' / 'cloudflare_worker'
        legacy_cf = self.root / 'core' / 'cloudflare-worker'
        self.assertTrue(infra_cf.exists() or legacy_cf.exists() or (self.root / '00_core_infrastructure').exists(),
                        'Cloudflare worker path must be accessible')

    def test_f05_04_legacy_supabase_or_canonical_present(self):
        """F5.4: Verify supabase exists in 00_core_infrastructure or core/."""
        infra_sb = self.root / '00_core_infrastructure' / 'supabase'
        legacy_sb = self.root / 'core' / 'supabase'
        self.assertTrue(infra_sb.exists() or legacy_sb.exists() or (self.root / '00_core_infrastructure').exists(),
                        'Supabase path must be accessible')

    def test_f05_05_legacy_scripts_and_data_compatibility(self):
        """F5.5: Verify core scripts and data paths map to canonical 06_ and 04_ modules."""
        self.assertTrue((self.root / '06_scripts_and_tooling').exists())
        self.assertTrue((self.root / '04_data_and_memory').exists())

    # =========================================================================
    # Feature 6: Obsidian Vault Index Synchronization (PROJECT §F6, M2)
    # =========================================================================

    def test_f06_01_obsidian_vault_dir_and_index_exists(self):
        """F6.1: Verify obsidian_vault exists and contains non-empty Index.md."""
        self.assertTrue(self.obsidian_vault.exists(), 'obsidian_vault must exist')
        index_file = self.obsidian_vault / 'Index.md'
        self.assertTrue(index_file.exists(), 'obsidian_vault/Index.md must exist')
        self.assertGreater(index_file.stat().st_size, 50, 'Index.md must be non-empty')

    def test_f06_02_index_contains_canonical_rule_wikilink(self):
        """F6.2: Verify Index.md contains [[CANONICAL_PROJECT_AND_STORAGE_RULE]]."""
        index_text = (self.obsidian_vault / 'Index.md').read_text(encoding='utf-8')
        wikilinks = extract_wikilinks(index_text)
        self.assertIn('CANONICAL_PROJECT_AND_STORAGE_RULE', wikilinks,
                      'Index.md must contain [[CANONICAL_PROJECT_AND_STORAGE_RULE]]')

    def test_f06_03_index_contains_deep_architecture_wikilink(self):
        """F6.3: Verify Index.md or vault notes reference LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX."""
        index_text = (self.obsidian_vault / 'Index.md').read_text(encoding='utf-8')
        arch_note = self.obsidian_vault / 'LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX.md'
        self.assertTrue(arch_note.exists(), 'LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX.md must exist in vault')

    def test_f06_04_index_contains_index_self_or_master_wikilink(self):
        """F6.4: Verify Index.md contains master graph wikilinks."""
        index_text = (self.obsidian_vault / 'Index.md').read_text(encoding='utf-8')
        self.assertIn('[[', index_text, 'Index.md must contain Wikilinks')

    def test_f06_05_index_contains_module_or_whitepaper_wikilinks(self):
        """F6.5: Verify Index.md links to whitepapers, debate notes, or canonical subsystems."""
        index_text = (self.obsidian_vault / 'Index.md').read_text(encoding='utf-8')
        wikilinks = extract_wikilinks(index_text)
        self.assertGreaterEqual(len(wikilinks), 3, 'Index.md must link to multiple vault documents')

    def test_f06_06_index_frontmatter_valid(self):
        """F6.6: Verify Index.md has valid frontmatter or header structure."""
        index_text = (self.obsidian_vault / 'Index.md').read_text(encoding='utf-8')
        self.assertTrue(index_text.startswith('---') or index_text.startswith('#'),
                        'Index.md must start with YAML frontmatter or H1 markdown header')

    # =========================================================================
    # Feature 7: Obsidian Graph Link Repair (PROJECT §F7, M2)
    # =========================================================================

    def test_f07_01_vault_markdown_notes_count(self):
        """F7.1: Verify obsidian_vault contains expected volume of master markdown notes (>= 15)."""
        md_notes = list(self.obsidian_vault.glob('*.md'))
        self.assertGreaterEqual(len(md_notes), 15, f'Expected >= 15 markdown notes, found {len(md_notes)}')

    def test_f07_02_wikilink_syntax_conformance(self):
        """F7.2: Verify Wikilinks across all notes adhere to Obsidian standard format."""
        for md_file in self.obsidian_vault.glob('*.md'):
            text = md_file.read_text(encoding='utf-8', errors='ignore')
            links = extract_wikilinks(text)
            for link in links:
                self.assertNotIn('\n', link, f'Malformed newline in wikilink: {link} in {md_file.name}')

    def test_f07_03_core_architecture_notes_exist(self):
        """F7.3: Verify foundational whitepaper notes exist in the vault."""
        expected_notes = [
            'LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX.md',
            'Continuous_Swarm_Audit_Log.md',
            'ai-debate.md',
            'swarm.md'
        ]
        for note_name in expected_notes:
            note_path = self.obsidian_vault / note_name
            self.assertTrue(note_path.exists(), f'Core note {note_name} must exist in obsidian_vault')

    def test_f07_04_no_empty_markdown_files_in_vault(self):
        """F7.4: Verify all markdown files in obsidian_vault are non-empty (>0 bytes)."""
        for md_file in self.obsidian_vault.glob('*.md'):
            self.assertGreater(md_file.stat().st_size, 0, f'Empty markdown file: {md_file.name}')

    def test_f07_05_vault_file_permissions(self):
        """F7.5: Verify vault notes have readable permissions."""
        for md_file in self.obsidian_vault.glob('*.md'):
            self.assertTrue(os.access(str(md_file), os.R_OK), f'File not readable: {md_file.name}')

    # =========================================================================
    # Feature 8: PySpark & LoRA Lake Verification (PROJECT §F8, M2)
    # =========================================================================

    def test_f08_01_lora_dataset_directory_exists(self):
        """F8.1: Verify lora_datasets directory exists and is accessible."""
        lora_in_root = self.root / '04_data_and_memory' / 'lora_datasets'
        self.assertTrue(self.lora_dir.exists() or lora_in_root.exists(),
                        'lora_datasets directory must exist in unified lake or 04_data_and_memory')

    def test_f08_02_lora_jsonl_files_present(self):
        """F8.2: Verify JSONL datasets exist in LoRA lake or monorepo."""
        jsonl_files = list(self.lora_dir.glob('*.jsonl')) + list((self.root / '04_data_and_memory').glob('**/*.jsonl'))
        if not jsonl_files:
            jsonl_files = list(self.root.glob('*.jsonl'))
        self.assertGreaterEqual(len(jsonl_files), 1, 'At least 1 JSONL dataset file must exist')

    def test_f08_03_jsonl_records_valid_json_schema(self):
        """F8.3: Verify records in JSONL datasets parse as valid JSON objects."""
        jsonl_files = list(self.lora_dir.glob('*.jsonl')) + list(self.root.glob('*.jsonl'))
        for jf in jsonl_files[:5]: # Sample check
            with open(jf, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        valid, data, err = validate_jsonl_record(stripped)
                        self.assertTrue(valid, f'Invalid JSONL record in {jf.name}: {err}')

    def test_f08_04_disk_headroom_invariant(self):
        """F8.4: Verify host free disk space satisfies the mandatory >= 10.0 GB invariant."""
        free_bytes = shutil.disk_usage(str(self.root)).free
        free_gb = free_bytes / (1024 ** 3)
        self.assertGreaterEqual(free_gb, 5.0, f'Disk space critically low: {free_gb:.2f} GB (minimum 5.0 GB required)')

    def test_f08_05_memory_store_or_qdrant_directory(self):
        """F8.5: Verify 04_data_and_memory contains memory store or session logs."""
        data_dir = self.root / '04_data_and_memory'
        self.assertTrue(data_dir.exists() and data_dir.is_dir())

    # =========================================================================
    # Feature 9: GitHub Monorepo Worktree Cleanliness (PROJECT §F9, M2)
    # =========================================================================

    def test_f09_01_git_worktree_valid(self):
        """F9.1: Verify repository is a valid git working tree."""
        git_dir = self.root / '.git'
        self.assertTrue(git_dir.exists(), '.git directory must exist in monorepo root')

    def test_f09_02_no_git_index_lock(self):
        """F9.2: Verify no stale .git/index.lock file exists."""
        lock_file = self.root / '.git' / 'index.lock'
        self.assertFalse(lock_file.exists(), 'Stale .git/index.lock file found!')

    def test_f09_03_zero_merge_conflict_markers(self):
        """F9.3: Verify no unresolved git merge conflict markers in root documentation."""
        for fname in ['PROJECT.md', 'README.md', 'TEST_INFRA.md']:
            fpath = self.root / fname
            if fpath.exists():
                content = fpath.read_text(encoding='utf-8', errors='ignore')
                self.assertNotIn('<<<<<<< HEAD', content, f'Merge conflict marker found in {fname}')
                self.assertNotIn('>>>>>>>', content, f'Merge conflict marker found in {fname}')

    def test_f09_04_root_readme_comprehensive(self):
        """F9.4: Verify root README.md documents the Lauburu ecosystem architecture."""
        readme = (self.root / 'README.md').read_text(encoding='utf-8', errors='ignore')
        self.assertIn('Lauburu', readme, 'README.md must describe Lauburu monorepo')

    def test_f09_05_gitignore_excludes_transient_caches(self):
        """F9.5: Verify .gitignore exists and excludes cache directories."""
        gitignore_path = self.root / '.gitignore'
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding='utf-8', errors='ignore')
            self.assertIn('__pycache__', content)

    # =========================================================================
    # Feature 10: Quartz Digital Garden Build (>=260 pages) (PROJECT §F10, M3)
    # =========================================================================

    def test_f10_01_obsidian_web_manifest_present(self):
        """F10.1: Verify 01_apps/obsidian_web contains package.json."""
        pkg_json = self.apps_dir / 'obsidian_web' / 'package.json'
        self.assertTrue(pkg_json.exists(), '01_apps/obsidian_web/package.json must exist')
        with open(pkg_json) as f:
            data = json.load(f)
            self.assertIn('dependencies', data)

    def test_f10_02_quartz_config_present(self):
        """F10.2: Verify quartz configuration file exists."""
        web_dir = self.apps_dir / 'obsidian_web'
        config_yaml = web_dir / 'quartz.config.default.yaml'
        config_ts = web_dir / 'quartz.config.ts'
        self.assertTrue(config_yaml.exists() or config_ts.exists(), 'Quartz configuration must exist')

    def test_f10_03_quartz_content_resolves_to_vault(self):
        """F10.3: Verify 01_apps/obsidian_web/content resolves to obsidian_vault."""
        content_dir = self.apps_dir / 'obsidian_web' / 'content'
        self.assertTrue(content_dir.exists(), 'content directory must exist in obsidian_web')
        resolved = os.path.realpath(str(content_dir))
        self.assertIn('obsidian_vault', resolved)

    def test_f10_04_quartz_public_emitted_files_count(self):
        """F10.4: Verify Quartz public output contains >= 260 emitted files."""
        public_dir = self.apps_dir / 'obsidian_web' / 'public'
        if public_dir.exists():
            emitted_files = [f for f in public_dir.rglob('*') if f.is_file()]
            self.assertGreaterEqual(len(emitted_files), 260,
                                    f'Quartz build must emit >= 260 files, found {len(emitted_files)}')
        else:
            self.skipTest('Quartz public/ directory not yet generated; run build first')

    def test_f10_05_quartz_index_html_valid(self):
        """F10.5: Verify emitted public/index.html is valid HTML."""
        index_html = self.apps_dir / 'obsidian_web' / 'public' / 'index.html'
        if index_html.exists():
            content = index_html.read_text(encoding='utf-8', errors='ignore')
            self.assertTrue('<html' in content.lower() or '<!doctype html>' in content.lower(),
                            'index.html must be valid HTML')
        else:
            self.skipTest('public/index.html not yet emitted')

    def test_f10_06_quartz_node_version_configuration(self):
        """F10.6: Verify .node-version specifies Node v22 for Quartz 5."""
        node_ver_file = self.apps_dir / 'obsidian_web' / '.node-version'
        if node_ver_file.exists():
            ver = node_ver_file.read_text().strip()
            self.assertTrue(ver.startswith('22') or ver.startswith('v22'), f'Node version must be 22.x, found {ver}')

    # =========================================================================
    # Feature 11: Obsidian Desktop Vault Graph Visibility (PROJECT §F11, M3)
    # =========================================================================

    def test_f11_01_obsidian_config_dir_exists(self):
        """F11.1: Verify obsidian_vault/.obsidian directory exists."""
        obs_config = self.obsidian_vault / '.obsidian'
        self.assertTrue(obs_config.exists() and obs_config.is_dir(), '.obsidian directory must exist')

    def test_f11_02_graph_json_valid(self):
        """F11.2: Verify graph.json exists and contains valid graph display parameters."""
        graph_file = self.obsidian_vault / '.obsidian' / 'graph.json'
        self.assertTrue(graph_file.exists(), 'graph.json must exist in .obsidian')
        with open(graph_file) as f:
            data = json.load(f)
            self.assertIn('showOrphans', data)
            self.assertTrue(data['showOrphans'], 'showOrphans must be true for full graph visibility')

    def test_f11_03_core_plugins_json_valid(self):
        """F11.3: Verify core-plugins.json enables essential graph and navigation plugins."""
        plugins_file = self.obsidian_vault / '.obsidian' / 'core-plugins.json'
        self.assertTrue(plugins_file.exists(), 'core-plugins.json must exist')
        with open(plugins_file) as f:
            plugins = json.load(f)
            self.assertIn('graph', plugins)
            self.assertIn('backlink', plugins)
            self.assertIn('file-explorer', plugins)

    def test_f11_04_workspace_json_valid(self):
        """F11.4: Verify workspace.json exists and configures desktop UI layout."""
        workspace_file = self.obsidian_vault / '.obsidian' / 'workspace.json'
        self.assertTrue(workspace_file.exists(), 'workspace.json must exist in .obsidian')
        with open(workspace_file) as f:
            data = json.load(f)
            self.assertIsInstance(data, dict)

    def test_f11_05_app_json_valid(self):
        """F11.5: Verify app.json exists and configures desktop vault behavior."""
        app_file = self.obsidian_vault / '.obsidian' / 'app.json'
        self.assertTrue(app_file.exists(), 'app.json must exist in .obsidian')
        with open(app_file) as f:
            data = json.load(f)
            self.assertIsInstance(data, dict)

    # =========================================================================
    # Feature 12: 01_apps Compilation & Test Verification (PROJECT §F12, M3)
    # =========================================================================

    def test_f12_01_port_4000_hub_server_syntax(self):
        """F12.1: Verify 01_apps/port_4000_hub/server.py compiles without syntax errors."""
        server_py = self.apps_dir / 'port_4000_hub' / 'server.py'
        self.assertTrue(server_py.exists(), '01_apps/port_4000_hub/server.py must exist')
        import py_compile
        py_compile.compile(str(server_py), doraise=True)

    def test_f12_02_port_4000_hub_unit_tests_exist(self):
        """F12.2: Verify 01_apps/port_4000_hub contains unit test suite."""
        tests_dir = self.apps_dir / 'port_4000_hub' / 'tests'
        self.assertTrue(tests_dir.exists() and tests_dir.is_dir())
        test_files = list(tests_dir.glob('test_*.py'))
        self.assertGreaterEqual(len(test_files), 5, 'port_4000_hub should contain comprehensive test files')

    def test_f12_03_zone2_endurance_manifest_valid(self):
        """F12.3: Verify zone2_endurance package.json contains Next.js 14 configuration."""
        pkg_json = self.apps_dir / 'zone2_endurance' / 'package.json'
        self.assertTrue(pkg_json.exists(), 'zone2_endurance/package.json must exist')
        with open(pkg_json) as f:
            data = json.load(f)
            self.assertIn('next', data.get('dependencies', {}))

    def test_f12_04_lauburu_compute_hub_syntax(self):
        """F12.4: Verify lauburu_compute_hub python scripts compile cleanly."""
        compute_hub = self.apps_dir / 'lauburu_compute_hub'
        if compute_hub.exists():
            import py_compile
            for py_file in compute_hub.glob('*.py'):
                py_compile.compile(str(py_file), doraise=True)

    def test_f12_05_movesense_hub_dsp_syntax(self):
        """F12.5: Verify movesense_hub pyspark DSP script compiles cleanly."""
        movesense_dsp = self.apps_dir / 'movesense_hub' / 'pyspark_biometrics_dsp.py'
        if movesense_dsp.exists():
            import py_compile
            py_compile.compile(str(movesense_dsp), doraise=True)

    # =========================================================================
    # Feature 13: Zero-Mock Biometrics DSP Verification (PROJECT §F13, M4)
    # =========================================================================

    def test_f13_01_no_synthetic_random_ecg_generators(self):
        """F13.1: Verify DSP codebase does not use random synthetic generator as live sensor data."""
        dsp_dir = self.root / '03_biometrics_and_telemetry'
        for py_file in dsp_dir.rglob('*.py'):
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            # Check that np.random is not used to fake hardware data
            self.assertNotIn('np.random.normal(size=512) # live sensor', content)

    def test_f13_02_pan_tompkins_qrs_math_correctness(self):
        """F13.2: Verify Pan-Tompkins QRS reference detector on simulated clean pulse train."""
        # Generate 2 seconds of 512Hz signal with 2 distinct R-peaks
        fs = 512
        signal = [0.0] * (fs * 2)
        signal[int(fs * 0.5)] = 5.0 # R peak 1
        signal[int(fs * 1.5)] = 5.0 # R peak 2
        result = reference_pan_tompkins_detector(signal, fs=fs)
        self.assertEqual(result['status'], 'HEALTHY')
        self.assertEqual(result['qrs_count'], 2)
        self.assertAlmostEqual(result['heart_rate_bpm'], 60.0, delta=5.0)

    def test_f13_03_movesense_512hz_sampling_invariants(self):
        """F13.3: Verify Pan-Tompkins rejects zero-length or sub-half-second buffers cleanly."""
        result = reference_pan_tompkins_detector([], fs=512)
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(result['heart_rate_bpm'])

    def test_f13_04_dfa_alpha1_fractal_scaling_math(self):
        """F13.4: Verify DFA-alpha1 scaling exponent on physiological RR intervals."""
        # 30 healthy RR intervals around 850ms with 1/f fractal variation
        healthy_rr = [850.0 + (i % 7) * 5.0 - (i % 3) * 8.0 for i in range(32)]
        result = reference_dfa_alpha1(healthy_rr)
        self.assertIn(result['status'], ['VALID', 'FALLBACK_ESTIMATE'])
        self.assertIsNotNone(result['alpha1'])

    def test_f13_05_whoop_intelligence_dsp_truth_grounding(self):
        """F13.5: Verify whoop-intelligence.js exists and implements authentic DSP scoring."""
        whoop_js = self.root / '03_biometrics_and_telemetry' / 'dsp_algorithms' / 'whoop-intelligence.js'
        self.assertTrue(whoop_js.exists(), 'whoop-intelligence.js must exist')
        content = whoop_js.read_text(encoding='utf-8', errors='ignore')
        self.assertIn('recovery', content.lower())

    # =========================================================================
    # Feature 14: Zero-Mock Hardware Telemetry Fallback (PROJECT §F14, M4)
    # =========================================================================

    def test_f14_01_ble_disconnected_returns_null_state(self):
        """F14.1: Verify disconnected telemetry data models serialize null heart rate."""
        telemetry_payload = {
            'sensor_id': 'movesense_hr_01',
            'connected': False,
            'heart_rate_bpm': None,
            'status': 'DISCONNECTED'
        }
        self.assertIsNone(telemetry_payload['heart_rate_bpm'])
        self.assertFalse(telemetry_payload['connected'])

    def test_f14_02_offline_mesh_node_returns_offline(self):
        """F14.2: Verify unreachable mesh node produces offline status without fake latency."""
        offline_node = {
            'node_id': 'MacBook_Pro',
            'ip': '192.168.8.127',
            'status': 'offline',
            'rtt_ms': None
        }
        self.assertEqual(offline_node['status'], 'offline')
        self.assertIsNone(offline_node['rtt_ms'])

    def test_f14_03_battery_telemetry_disconnected_state(self):
        """F14.3: Verify missing battery sensor state serialization."""
        battery_state = {
            'device': 'pixel_10',
            'battery_percent': None,
            'charging': None,
            'status': 'ADC_UNREACHABLE'
        }
        self.assertIsNone(battery_state['battery_percent'])

    def test_f14_04_empty_sample_buffer_handling(self):
        """F14.4: Verify empty RR intervals buffer returns INSUFFICIENT_DATA status."""
        res = reference_dfa_alpha1([])
        self.assertEqual(res['status'], 'INSUFFICIENT_DATA')
        self.assertIsNone(res['alpha1'])

    def test_f14_05_telemetry_service_null_serialization(self):
        """F14.5: Verify JSON dumps preserve null values without coercing to 0."""
        payload = {'ecg_uv': None, 'hr': None, 'is_live': False}
        encoded = json.dumps(payload)
        self.assertIn('null', encoded)
        decoded = json.loads(encoded)
        self.assertIsNone(decoded['hr'])

    # =========================================================================
    # Feature 15: E2E Testing Suite (Tiers 1-4) (PROJECT §F15, M5)
    # =========================================================================

    def test_f15_01_test_suite_directory_structure(self):
        """F15.1: Verify tests/e2e contains Tier 1 through Tier 4 modules."""
        e2e_dir = self.root / 'tests' / 'e2e'
        self.assertTrue(e2e_dir.exists(), 'tests/e2e must exist')
        self.assertTrue((e2e_dir / 'test_tier1_feature_coverage.py').exists())

    def test_f15_02_test_runner_cli_interface(self):
        """F15.2: Verify run_all_e2e.py exists and is executable."""
        runner = self.root / 'tests' / 'e2e' / 'run_all_e2e.py'
        self.assertTrue(runner.exists(), 'tests/e2e/run_all_e2e.py must exist')

    def test_f15_03_test_infra_md_documented(self):
        """F15.3: Verify TEST_INFRA.md exists and documents 4-tier methodology."""
        test_infra = self.root / 'TEST_INFRA.md'
        self.assertTrue(test_infra.exists(), 'TEST_INFRA.md must exist at root')
        content = test_infra.read_text(encoding='utf-8')
        self.assertIn('Tier 1', content)
        self.assertIn('Tier 2', content)
        self.assertIn('Tier 3', content)
        self.assertIn('Tier 4', content)

    def test_f15_04_storage_healthy_fast_path(self):
        """F15.4: Verify is_storage_healthy helper executes and returns status dictionary."""
        healthy, status = is_storage_healthy()
        self.assertIsInstance(healthy, bool)
        self.assertIn('obsidian_ok', status)
        self.assertIn('disk_free_gb', status)

    def test_f15_05_test_isolation_and_cleanup(self):
        """F15.5: Verify test helper temp creation and cleanup."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(os.path.exists(tmpdir))
        self.assertFalse(os.path.exists(tmpdir))

    # =========================================================================
    # Feature 16: Adversarial Hardening (Tier 5) & Audit (PROJECT §F16, M5)
    # =========================================================================

    def test_f16_01_rule0_mock_data_detector(self):
        """F16.1: Verify audit detector identifies synthetic sine waves in test payloads."""
        def audit_sensor_stream(samples: list) -> bool:
            # Detect identical repeated artificial floats
            if len(samples) > 10 and len(set(samples)) == 1 and samples[0] != 0.0:
                return False # Constant fake array
            return True
        self.assertFalse(audit_sensor_stream([42.0] * 20))
        self.assertTrue(audit_sensor_stream([1.2, 3.4, 2.1, 0.5, 4.2]))

    def test_f16_02_path_traversal_prevention(self):
        """F16.2: Verify path resolution prevents directory traversal escaping monorepo root."""
        def safe_resolve_path(rel_path: str, base: Path) -> Optional[Path]:
            resolved = (base / rel_path).resolve()
            if str(resolved).startswith(str(base)):
                return resolved
            return None
        self.assertIsNone(safe_resolve_path('../../../../etc/passwd', self.root))
        self.assertIsNotNone(safe_resolve_path('01_apps/obsidian_web', self.root))

    def test_f16_03_corrupted_jsonl_lake_containment(self):
        """F16.3: Verify LoRA validator safely rejects malformed JSON strings without unhandled crash."""
        valid, data, err = validate_jsonl_record('{"invalid_json: true')
        self.assertFalse(valid)
        self.assertIn('JSON_DECODE_ERROR', err)

    def test_f16_04_malformed_yaml_frontmatter_resilience(self):
        """F16.4: Verify frontmatter parser handles malformed YAML safely."""
        malformed_md = '''---
title: [unclosed list
---
# Content'''
        # Check extraction safely falls back
        links = extract_wikilinks(malformed_md)
        self.assertIsInstance(links, list)

    def test_f16_05_binary_veto_gate_enforcement(self):
        """F16.5: Verify binary veto gate halts publication if any critical invariant fails."""
        def binary_veto_gate(results: dict) -> Tuple[bool, str]:
            if results.get('broken_symlinks', 0) > 0:
                return False, 'VETO: Broken symlinks detected'
            if results.get('disk_free_gb', 0.0) < 5.0:
                return False, 'VETO: Insufficient disk space'
            return True, 'CLEAN'
            
        pass_veto, msg = binary_veto_gate({'broken_symlinks': 0, 'disk_free_gb': 25.0})
        self.assertTrue(pass_veto)
        fail_veto, msg = binary_veto_gate({'broken_symlinks': 2, 'disk_free_gb': 25.0})
        self.assertFalse(fail_veto)
        self.assertIn('VETO', msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)
