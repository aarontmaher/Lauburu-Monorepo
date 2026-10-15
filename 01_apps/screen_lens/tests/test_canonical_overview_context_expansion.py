#!/usr/bin/env python3
"""
Unit tests for Canonical Overview Context-Window Parsing & Dynamic Expansion for Lens AI.
Verifies that all 4 canonical overview files exist, follow Tri-Vault synchronization,
and contain parseable context window tiers (Tier 0: 4K, Tier 1: 16K, Tier 2: 32K, Tier 3: 128K).
"""

import os
import re
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
VAULT_CANONICAL = REPO_ROOT / "obsidian_vault" / "canonical"

CANONICAL_FILES = [
    "CANONICAL_PROJECT_OVERVIEW.md",
    "CANONICAL_APPS_OVERVIEW.md",
    "CANONICAL_BUSINESS_PLAN_OVERVIEW.md",
    "LENS_AI_CANONICAL_OVERVIEW.md",
]

TIER_MARKERS = [
    ("TIER_0", r"<!-- CONTEXT_WINDOW_TIER_0_START: (.*?) -->", r"<!-- CONTEXT_WINDOW_TIER_0_END -->"),
    ("TIER_1", r"<!-- CONTEXT_WINDOW_TIER_1_START: (.*?) -->", r"<!-- CONTEXT_WINDOW_TIER_1_END -->"),
    ("TIER_2", r"<!-- CONTEXT_WINDOW_TIER_2_START: (.*?) -->", r"<!-- CONTEXT_WINDOW_TIER_2_END -->"),
    ("TIER_3", r"<!-- CONTEXT_WINDOW_TIER_3_START: (.*?) -->", r"<!-- CONTEXT_WINDOW_TIER_3_END -->"),
]


class TestCanonicalOverviewContextExpansion:
    """Validates structural integrity and context expansion capability for Lens AI."""

    @pytest.mark.parametrize("filename", CANONICAL_FILES)
    def test_canonical_file_exists_in_root_and_vault(self, filename):
        """Ensures all 4 files exist in both monorepo root and obsidian_vault/canonical/."""
        root_file = REPO_ROOT / filename
        vault_file = VAULT_CANONICAL / filename
        assert root_file.is_file(), f"Missing root file: {root_file}"
        assert vault_file.is_file(), f"Missing vault file: {vault_file}"
        assert root_file.stat().st_size > 1000, f"Root file too small: {filename}"
        assert vault_file.stat().st_size > 1000, f"Vault file too small: {filename}"

    @pytest.mark.parametrize("filename", CANONICAL_FILES)
    def test_all_context_window_tiers_present(self, filename):
        """Verifies that each canonical overview contains all 4 hierarchical context tiers."""
        content = (REPO_ROOT / filename).read_text(encoding="utf-8")
        for tier_name, start_regex, end_regex in TIER_MARKERS:
            start_match = re.search(start_regex, content)
            end_match = re.search(end_regex, content)
            assert start_match is not None, f"Missing start marker for {tier_name} in {filename}"
            assert end_match is not None, f"Missing end marker for {tier_name} in {filename}"
            assert start_match.start() < end_match.start(), f"Inverted markers for {tier_name} in {filename}"

    def test_lens_context_extraction_by_tier(self):
        """Simulates Lens AI dynamic context expansion by selective tier extraction."""
        project_doc = (REPO_ROOT / "CANONICAL_PROJECT_OVERVIEW.md").read_text(encoding="utf-8")

        # Extract Tier 0 (Micro Executive Core)
        t0_match = re.search(r"<!-- CONTEXT_WINDOW_TIER_0_START: (.*?) -->(.*?)<!-- CONTEXT_WINDOW_TIER_0_END -->", project_doc, re.DOTALL)
        assert t0_match is not None
        tier0_content = t0_match.group(2).strip()
        assert "Rule #0" in tier0_content
        assert "7-Layer Physical Mesh Hardware Matrix" in tier0_content
        # Tier 0 should be concise (<1,500 words for micro edge models)
        assert len(tier0_content.split()) < 1500

        # Extract Tier 1 (Subsystems)
        t1_match = re.search(r"<!-- CONTEXT_WINDOW_TIER_1_START: (.*?) -->(.*?)<!-- CONTEXT_WINDOW_TIER_1_END -->", project_doc, re.DOTALL)
        assert t1_match is not None
        tier1_content = t1_match.group(2).strip()
        assert "00_core_infrastructure" in tier1_content
        assert "01_apps" in tier1_content
        assert "02_ai_models_and_inference" in tier1_content

    def test_obsidian_index_wikilinks_synchronized(self):
        """Ensures obsidian_vault/Index.md links to all 4 canonical overview documents."""
        index_file = REPO_ROOT / "obsidian_vault" / "Index.md"
        assert index_file.exists(), "Missing obsidian_vault/Index.md"
        index_text = index_file.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_OVERVIEW]]" in index_text
        assert "[[CANONICAL_APPS_OVERVIEW]]" in index_text
        assert "[[CANONICAL_BUSINESS_PLAN_OVERVIEW]]" in index_text
        assert "[[LENS_AI_CANONICAL_OVERVIEW]]" in index_text
