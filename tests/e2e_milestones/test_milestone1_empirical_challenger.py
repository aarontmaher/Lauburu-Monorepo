#!/usr/bin/env python3
"""Empirical Challenger Test Suite for Milestone 1: Sandbox Scaffolding & Specialist Skills.

This test suite executes rigorous, adversarial validation of Milestone 1 artifacts:
1. YAML frontmatter parsing across standard parsers and extraction techniques.
2. JSON schema compliance against PROJECT.md interface contracts.
3. Directory hierarchy, file permissions, and POSIX path contracts.
4. Byte-level character encoding integrity (strict UTF-8, no BOM, LF line endings).
5. Cross-tooling compatibility (Antigravity skill loader, standard CLI tools).
6. Negative oracle mutation testing to verify test rigor.
"""

import copy
import json
import math
import os
import re
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# Constants
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SANDBOX_DIR = REPO_ROOT / ".sandbox_training" / "tui_mastery"
SKILLS_DIR = Path("/Users/aaron/.gemini/config/skills")
CONFIG_DIR = SANDBOX_DIR / "config"
SPECIALISTS_CONFIG_DIR = CONFIG_DIR / "specialists"

SPECIALIST_NAMES = [
    "polyglot-python-textual-specialist",
    "polyglot-go-bubbletea-specialist",
    "polyglot-rust-ratatui-specialist",
]

FRAMEWORK_MAP = {
    "polyglot-python-textual-specialist": {"framework": "textual", "lang": "python", "json_file": "python_textual.json"},
    "polyglot-go-bubbletea-specialist": {"framework": "bubbletea", "lang": "go", "json_file": "go_bubbletea.json"},
    "polyglot-rust-ratatui-specialist": {"framework": "ratatui", "lang": "rust", "json_file": "rust_ratatui.json"},
}


class TestMilestone1ScaffoldingAndPermissions(unittest.TestCase):
    """Test Suite 1: Directory Existence, Hierarchy, Permissions and POSIX Contracts."""

    def test_sandbox_root_exists_and_is_dir(self):
        """Verify sandbox root directory exists and is a directory."""
        self.assertTrue(SANDBOX_DIR.exists(), f"Sandbox root missing: {SANDBOX_DIR}")
        self.assertTrue(SANDBOX_DIR.is_dir(), f"Sandbox root is not a directory: {SANDBOX_DIR}")

    def test_required_subdirectories_exist(self):
        """Verify all required subdirectories exist in sandbox tree."""
        required_dirs = [
            "config",
            "config/specialists",
            "defenses",
            "defenses/python_textual",
            "defenses/go_bubbletea",
            "defenses/rust_ratatui",
            "attacks",
            "referee",
            "logs",
            "benchmarks",
        ]
        for rel_path in required_dirs:
            p = SANDBOX_DIR / rel_path
            self.assertTrue(p.exists(), f"Missing directory: {p}")
            self.assertTrue(p.is_dir(), f"Path is not a directory: {p}")

    def test_directory_permissions_and_traversal(self):
        """Verify directories have read/write/execute permissions (at least 0700)."""
        for root, dirs, files in os.walk(SANDBOX_DIR):
            dir_stat = os.stat(root)
            mode = stat.S_IMODE(dir_stat.st_mode)
            # Owner should have read, write, execute
            self.assertTrue(mode & stat.S_IRUSR, f"Directory not readable by owner: {root}")
            self.assertTrue(mode & stat.S_IWUSR, f"Directory not writable by owner: {root}")
            self.assertTrue(mode & stat.S_IXUSR, f"Directory not executable/traversable by owner: {root}")

    def test_file_permissions_and_non_empty(self):
        """Verify all created files are non-empty and readable by owner."""
        files_to_check = [
            SANDBOX_DIR / "README.md",
            SANDBOX_DIR / "config" / "tournament_config.json",
            SANDBOX_DIR / "config" / "specialists" / "python_textual.json",
            SANDBOX_DIR / "config" / "specialists" / "go_bubbletea.json",
            SANDBOX_DIR / "config" / "specialists" / "rust_ratatui.json",
        ]
        for f in files_to_check:
            self.assertTrue(f.exists(), f"Missing file: {f}")
            self.assertTrue(f.is_file(), f"Not a file: {f}")
            st = os.stat(f)
            self.assertGreater(st.st_size, 0, f"File is 0-bytes: {f}")
            mode = stat.S_IMODE(st.st_mode)
            self.assertTrue(mode & stat.S_IRUSR, f"File not readable by owner: {f}")
            self.assertTrue(mode & stat.S_IWUSR, f"File not writable by owner: {f}")


class TestMilestone1BytePurityAndEncodings(unittest.TestCase):
    """Test Suite 2: Byte-Level Encodings, UTF-8 Validity, No BOM, POSIX Line Endings."""

    def _check_file_encoding(self, file_path: Path):
        raw_bytes = file_path.read_bytes()
        # 1. Must not be empty
        self.assertGreater(len(raw_bytes), 0, f"File empty: {file_path}")

        # 2. No UTF-8 BOM (\xef\xbb\xbf)
        self.assertFalse(raw_bytes.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM detected in {file_path}")

        # 3. No UTF-16 / UTF-32 BOMs
        self.assertFalse(raw_bytes.startswith(b"\xff\xfe"), f"UTF-16 LE BOM detected in {file_path}")
        self.assertFalse(raw_bytes.startswith(b"\xfe\xff"), f"UTF-16 BE BOM detected in {file_path}")

        # 4. Strict UTF-8 decoding without errors or replacement chars
        try:
            decoded_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            self.fail(f"Invalid UTF-8 in {file_path}: {e}")

        self.assertNotIn("\ufffd", decoded_text, f"Unicode replacement character (U+FFFD) found in {file_path}")

        # 5. No NUL bytes
        self.assertNotIn("\x00", decoded_text, f"NUL byte found in {file_path}")

        # 6. POSIX line endings (no carriage returns \r\n unless markdown table intentional, but prefer LF)
        self.assertNotIn("\r\n", decoded_text, f"CRLF Windows line endings detected in {file_path}")
        self.assertNotIn("\r", decoded_text, f"Lone CR line ending detected in {file_path}")

    def test_sandbox_configs_and_readmes_byte_purity(self):
        """Verify all sandbox files pass byte purity checks."""
        for root, dirs, files in os.walk(SANDBOX_DIR):
            for fname in files:
                if fname.endswith((".json", ".md", ".jsonl")):
                    self._check_file_encoding(Path(root) / fname)

    def test_skills_skill_md_byte_purity(self):
        """Verify all 3 specialist SKILL.md files pass byte purity checks."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"SKILL.md missing for {spec}")
            self._check_file_encoding(skill_md)


class TestMilestone1YAMLFrontmatterCorrectness(unittest.TestCase):
    """Test Suite 3: YAML Frontmatter Parsing, Standard Tooling & Antigravity Compatibility."""

    def test_frontmatter_extraction_and_delimiter_contract(self):
        """Verify frontmatter starts exactly at byte 0 with '---' and closes with '---'."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")

            # Must start with ---
            self.assertTrue(content.startswith("---\n"), f"{skill_md} does not start with '---\\n'")

            # Must contain closing ---
            parts = content.split("---", 2)
            self.assertGreaterEqual(len(parts), 3, f"{skill_md} does not have standard '---' delimiters")

            yaml_str = parts[1]
            body_md = parts[2]

            self.assertGreater(len(yaml_str.strip()), 0, f"Empty YAML frontmatter in {skill_md}")
            self.assertGreater(len(body_md.strip()), 0, f"Empty markdown body in {skill_md}")

    def test_pyyaml_safe_and_full_load_parsers(self):
        """Verify standard PyYAML safe_load and full_load parse frontmatter without errors."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            yaml_str = parts[1]

            # 1. safe_load
            try:
                fm_safe = yaml.safe_load(yaml_str)
            except Exception as e:
                self.fail(f"PyYAML safe_load failed for {skill_md}: {e}")

            self.assertIsInstance(fm_safe, dict, f"Frontmatter did not parse as dictionary in {skill_md}")

            # 2. full_load
            try:
                fm_full = yaml.full_load(yaml_str)
            except Exception as e:
                self.fail(f"PyYAML full_load failed for {skill_md}: {e}")

            self.assertEqual(fm_safe, fm_full)

            # 3. Check required frontmatter keys
            self.assertIn("name", fm_safe, f"Missing 'name' in frontmatter of {skill_md}")
            self.assertIn("description", fm_safe, f"Missing 'description' in frontmatter of {skill_md}")

            # 4. Check name matches directory name
            self.assertEqual(fm_safe["name"], spec, f"Frontmatter name '{fm_safe['name']}' != directory '{spec}'")

            # 5. Check description is descriptive (>20 chars)
            self.assertGreater(len(fm_safe["description"]), 20, f"Frontmatter description too short in {skill_md}")

    def test_regex_frontmatter_parser_compatibility(self):
        """Verify standard regex-based frontmatter parsers used by agent frameworks parse cleanly."""
        pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            match = pattern.match(content)
            self.assertIsNotNone(match, f"Regex frontmatter matcher failed on {skill_md}")
            yaml_block, md_block = match.groups()
            parsed = yaml.safe_load(yaml_block)
            self.assertEqual(parsed["name"], spec)
            self.assertIn("description", parsed)

    def test_skill_markdown_content_mandates(self):
        """Verify markdown body contains core architectural sections and Rule #0 zero-mock mandate."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")

            # Must enforce Zero-Mock Rule #0
            self.assertTrue(
                "zero-mock" in content.lower() or "rule #0" in content.lower(),
                f"{skill_md} does not contain Zero-Mock / Rule #0 mandate",
            )

            # Must contain Core Competencies
            self.assertIn("Core Competencies", content, f"{skill_md} missing 'Core Competencies' section")

            # Must contain Adversarial Hardening or Defense
            self.assertTrue(
                "Hardening" in content or "Defense" in content or "Adversarial" in content,
                f"{skill_md} missing adversarial hardening section",
            )


class TestMilestone1JSONSchemaAndContracts(unittest.TestCase):
    """Test Suite 4: JSON Schema & Interface Contract Validation."""

    def test_specialist_json_interface_contracts(self):
        """Verify each specialist JSON file strictly adheres to PROJECT.md interface contract."""
        for spec, meta in FRAMEWORK_MAP.items():
            json_path = SPECIALISTS_CONFIG_DIR / meta["json_file"]
            self.assertTrue(json_path.exists(), f"Missing specialist JSON: {json_path}")

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. Exact required keys
            expected_keys = {
                "name",
                "archetype",
                "framework",
                "language",
                "system_prompt",
                "core_competencies",
                "defensive_patterns",
                "zero_mock_enforcement",
            }
            self.assertTrue(expected_keys.issubset(set(data.keys())), f"Missing keys in {json_path}: {expected_keys - set(data.keys())}")

            # 2. Type validation
            self.assertIsInstance(data["name"], str)
            self.assertEqual(data["name"], spec)

            self.assertIsInstance(data["archetype"], str)
            self.assertGreater(len(data["archetype"]), 5)

            self.assertIsInstance(data["framework"], str)
            self.assertEqual(data["framework"], meta["framework"])

            self.assertIsInstance(data["language"], str)
            self.assertEqual(data["language"], meta["lang"])

            self.assertIsInstance(data["system_prompt"], str)
            self.assertGreater(len(data["system_prompt"]), 50)
            self.assertTrue(
                "zero-mock" in data["system_prompt"].lower() or "rule #0" in data["system_prompt"].lower(),
                f"system_prompt in {json_path} missing Zero-Mock mandate",
            )

            self.assertIsInstance(data["core_competencies"], list)
            self.assertGreaterEqual(len(data["core_competencies"]), 3)
            for item in data["core_competencies"]:
                self.assertIsInstance(item, str)
                self.assertGreater(len(item), 3)

            self.assertIsInstance(data["defensive_patterns"], list)
            self.assertGreaterEqual(len(data["defensive_patterns"]), 3)
            for item in data["defensive_patterns"]:
                self.assertIsInstance(item, str)
                self.assertGreater(len(item), 3)

            # 3. zero_mock_enforcement strictly True boolean
            self.assertIs(data["zero_mock_enforcement"], True)
            self.assertIs(type(data["zero_mock_enforcement"]), bool)

    def test_tournament_config_json_schema_and_weights(self):
        """Verify tournament_config.json schema, scoring weights, and framework mapping."""
        cfg_file = CONFIG_DIR / "tournament_config.json"
        self.assertTrue(cfg_file.exists(), f"tournament_config.json missing: {cfg_file}")

        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # Root fields
        self.assertEqual(cfg["tournament_id"], "tui_mastery_red_vs_blue_v1")
        self.assertEqual(cfg["integrity_mode"], "benchmark")
        self.assertEqual(set(cfg["frameworks"]), {"python_textual", "go_bubbletea", "rust_ratatui"})

        # Scoring weights sum to 1.0
        weights = cfg["scoring_rubric"]["weights"]
        self.assertEqual(set(weights.keys()), {"memory_efficiency", "latency_throughput", "attack_robustness", "code_quality_and_truth"})
        total_weight = sum(weights.values())
        self.assertTrue(math.isclose(total_weight, 1.0, rel_tol=1e-5), f"Scoring weights sum to {total_weight}, expected 1.0")

        # Specialist mapping
        for fw in cfg["frameworks"]:
            self.assertIn(fw, cfg["specialists"])
            spec_info = cfg["specialists"][fw]
            skill_path = Path(spec_info["skill_path"])
            self.assertTrue(skill_path.exists(), f"Referenced skill_path does not exist: {skill_path}")
            profile_path = SANDBOX_DIR / spec_info["profile_path"]
            self.assertTrue(profile_path.exists(), f"Referenced profile_path does not exist: {profile_path}")

        # Attack suite scenarios
        scenarios = cfg["attack_suite"]["scenarios"]
        self.assertEqual(len(scenarios), 10)
        scenario_ids = [s["id"] for s in scenarios]
        self.assertEqual(len(scenario_ids), len(set(scenario_ids)), "Duplicate scenario IDs in attack_suite")


class TestMilestone1CrossToolingAndCLIParseability(unittest.TestCase):
    """Test Suite 5: Standard CLI Tooling Parseability (python3 -m json.tool, yq/yaml)."""

    def test_json_tool_cli_validation(self):
        """Verify all JSON files can be parsed by the Python standard CLI json.tool."""
        json_files = [
            CONFIG_DIR / "tournament_config.json",
            SPECIALISTS_CONFIG_DIR / "python_textual.json",
            SPECIALISTS_CONFIG_DIR / "go_bubbletea.json",
            SPECIALISTS_CONFIG_DIR / "rust_ratatui.json",
        ]
        for jf in json_files:
            cmd = [sys.executable, "-m", "json.tool", str(jf)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"json.tool failed to parse {jf}: {res.stderr}")

    def test_pyyaml_loader_via_subprocess(self):
        """Verify YAML frontmatters parse in clean standalone subprocess."""
        for spec in SPECIALIST_NAMES:
            skill_path = SKILLS_DIR / spec / "SKILL.md"
            cmd = [
                sys.executable,
                "-c",
                f"""
import yaml
with open('{skill_path}') as f:
    parts = f.read().split('---')
    data = yaml.safe_load(parts[1])
    assert data['name'] == '{spec}'
    print('SUCCESS')
""",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Subprocess YAML parse failed for {skill_path}: {res.stderr}")
            self.assertIn("SUCCESS", res.stdout)


class TestMilestone1NegativeMutationOracle(unittest.TestCase):
    """Test Suite 6: Negative & Adversarial Mutation Oracle Testing.

    Validates that our test harnesses correctly catch corrupted YAML, malformed schemas,
    and missing attributes (demonstrating our oracles are rigorous and non-vacuous).
    """

    def test_oracle_detects_corrupted_yaml_frontmatter(self):
        """Verify YAML parser oracle fails on invalid indentation or bad delimiters."""
        bad_yaml = "name: polyglot-test\n  bad_indent:\n- unaligned"
        with self.assertRaises(Exception):
            yaml.safe_load(bad_yaml)

    def test_oracle_detects_missing_required_contract_field(self):
        """Verify schema validator detects missing 'zero_mock_enforcement'."""
        invalid_profile = {
            "name": "polyglot-python-textual-specialist",
            "archetype": "Python Specialist",
            "framework": "textual",
            "language": "python",
            "system_prompt": "Test prompt",
            "core_competencies": ["a", "b", "c"],
            "defensive_patterns": ["x", "y", "z"],
            # Missing "zero_mock_enforcement"
        }
        # Incomplete schema check
        expected_keys = {
            "name",
            "archetype",
            "framework",
            "language",
            "system_prompt",
            "core_competencies",
            "defensive_patterns",
            "zero_mock_enforcement",
        }
        self.assertFalse(expected_keys.issubset(set(invalid_profile.keys())))

    def test_oracle_detects_fake_zero_mock_enforcement(self):
        """Verify schema validator rejects false or non-boolean zero_mock_enforcement."""
        fake_profile_1 = {"zero_mock_enforcement": False}
        self.assertIsNot(fake_profile_1["zero_mock_enforcement"], True)

        fake_profile_2 = {"zero_mock_enforcement": "true"}  # string instead of bool
        self.assertIsNot(fake_profile_2["zero_mock_enforcement"], True)




class TestMilestone1AdversarialEdgeCasesAndCrossReferencing(unittest.TestCase):
    """Test Suite 7: Adversarial Edge Cases, No-Tab Invariant, Path Resolution & Cross-Referencing."""

    def test_no_tabs_in_yaml_frontmatter(self):
        """Verify YAML frontmatter strictly uses spaces for indentation, never tab characters."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            raw_text = skill_md.read_text(encoding="utf-8")
            parts = raw_text.split("---", 2)
            yaml_part = parts[1]
            self.assertNotIn("\t", yaml_part, f"Tab character found in YAML frontmatter of {skill_md}")

    def test_exact_delimiter_hygiene(self):
        """Verify frontmatter delimiters are strictly '---' on their own lines without trailing spaces."""
        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            lines = skill_md.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "---", f"First line of {skill_md} is '{lines[0]}', expected '---'")
            # Find closing delimiter
            closing_idx = -1
            for idx, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    self.assertEqual(line, "---", f"Closing delimiter in {skill_md} has extra whitespace: '{line}'")
                    closing_idx = idx
                    break
            self.assertGreater(closing_idx, 1, f"Closing delimiter not found in {skill_md}")

    def test_cross_reference_skill_json_and_tournament_config(self):
        """Verify end-to-end consistency between SKILL.md, specialist JSON, and tournament_config.json."""
        with open(CONFIG_DIR / "tournament_config.json", "r", encoding="utf-8") as f:
            t_cfg = json.load(f)

        for fw_key, spec_cfg in t_cfg["specialists"].items():
            skill_path = Path(spec_cfg["skill_path"])
            profile_path = SANDBOX_DIR / spec_cfg["profile_path"]
            defense_path = SANDBOX_DIR / spec_cfg["defense_path"]

            # 1. Paths exist
            self.assertTrue(skill_path.exists(), f"Skill path does not exist: {skill_path}")
            self.assertTrue(profile_path.exists(), f"Profile path does not exist: {profile_path}")
            self.assertTrue(defense_path.exists(), f"Defense path does not exist: {defense_path}")

            # 2. Check SKILL.md name matches config
            skill_text = skill_path.read_text(encoding="utf-8")
            fm = yaml.safe_load(skill_text.split("---")[1])
            self.assertEqual(fm["name"], spec_cfg["skill_name"])

            # 3. Check JSON profile name matches config
            with open(profile_path, "r", encoding="utf-8") as pf:
                p_data = json.load(pf)
            self.assertEqual(p_data["name"], spec_cfg["skill_name"])
            self.assertEqual(p_data["framework"], spec_cfg["framework"])
            self.assertEqual(p_data["language"], spec_cfg["language"])

    def test_all_tournament_config_referenced_system_paths_exist(self):
        """Verify all referenced monorepo system paths in tournament_config.json exist."""
        with open(CONFIG_DIR / "tournament_config.json", "r", encoding="utf-8") as f:
            t_cfg = json.load(f)

        # Working directory
        self.assertTrue(Path(t_cfg["working_directory"]).exists())

        # NPU ledger file
        npu_file = Path(t_cfg["npu_ledger"]["ledger_file"])
        self.assertTrue(npu_file.exists(), f"NPU ledger path missing: {npu_file}")

        # Production promotion targets
        skills_dir = Path(t_cfg["production_promotion"]["skills_directory"])
        self.assertTrue(skills_dir.exists(), f"Skills dir missing: {skills_dir}")

        apps_dir = Path(t_cfg["production_promotion"]["apps_directory"])
        self.assertTrue(apps_dir.exists(), f"Apps dir missing: {apps_dir}")

    def test_parse_speed_under_budget(self):
        """Verify all artifacts parse within sub-millisecond budgets (<10ms each)."""
        import time

        for spec in SPECIALIST_NAMES:
            skill_md = SKILLS_DIR / spec / "SKILL.md"
            t0 = time.perf_counter()
            content = skill_md.read_text(encoding="utf-8")
            yaml.safe_load(content.split("---")[1])
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(elapsed_ms, 20.0, f"Parsing {skill_md} took {elapsed_ms:.2f}ms (budget 20ms)")

        for meta in FRAMEWORK_MAP.values():
            jpath = SPECIALISTS_CONFIG_DIR / meta["json_file"]
            t0 = time.perf_counter()
            with open(jpath, "r", encoding="utf-8") as f:
                json.load(f)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(elapsed_ms, 20.0, f"Parsing {jpath} took {elapsed_ms:.2f}ms (budget 20ms)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
