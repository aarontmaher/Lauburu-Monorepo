"""
Tests for Neo MCP Server & Skill Ecosystem Integration.
Complies with Rule 0 (Zero-Mock Empirical Verification), Rule 2 (Tri-Vault), and Rule 3.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")


class TestNeoMcpAndSkillIntegration(unittest.TestCase):
    """Rigorous end-to-end verification of Neo MCP server, schemas, launcher, and skills."""

    EXPECTED_TOOLS = {
        "neo_submit_task",
        "neo_task_status",
        "neo_get_messages",
        "neo_send_feedback",
        "neo_pause_task",
        "neo_resume_task",
        "neo_stop_task",
        "neo_list_integrations",
        "neo_add_integration",
        "neo_remove_integration",
        "neo_test_integration",
        "neo_list_tasks",
        "neo_list_byok_profiles",
        "neo_add_byok_profile",
        "neo_set_byok_profile",
        "neo_remove_byok_profile",
        "neo_list_byok_models",
    }

    def test_schema_files_in_all_runtimes(self):
        """Ensure all 17 tool schemas exist and are valid JSON in antigravity runtimes."""
        mcp_dirs = [
            Path("/Users/aaron/.gemini/antigravity/mcp/neo"),
            Path("/Users/aaron/.gemini/antigravity-cli/mcp/neo"),
            Path("/Users/aaron/.gemini/antigravity-ide/mcp/neo"),
        ]

        for mcp_dir in mcp_dirs:
            self.assertTrue(mcp_dir.is_dir(), f"Directory missing: {mcp_dir}")
            schemas = {p.stem for p in mcp_dir.glob("*.json")}
            self.assertEqual(
                schemas,
                self.EXPECTED_TOOLS,
                f"Missing or mismatched tools in {mcp_dir}: {self.EXPECTED_TOOLS - schemas}",
            )

            # Validate JSON formatting of each schema
            for json_file in mcp_dir.glob("*.json"):
                data = json.loads(json_file.read_text(encoding="utf-8"))
                self.assertIn("name", data)
                self.assertIn("description", data)
                self.assertIn("parameters", data)

    def test_mcp_launcher_and_binary(self):
        """Verify neo-mcp-launcher and neo-mcp binaries exist, are executable, and report status."""
        launcher = Path("/Users/aaron/.local/bin/neo-mcp-launcher")
        binary = Path("/Users/aaron/.local/bin/neo-mcp")

        self.assertTrue(launcher.exists(), "neo-mcp-launcher missing")
        self.assertTrue(os.access(launcher, os.X_OK), "neo-mcp-launcher not executable")
        self.assertTrue(binary.exists(), "neo-mcp binary missing")
        self.assertTrue(os.access(binary, os.X_OK), "neo-mcp not executable")

        # Execute status on launcher
        res = subprocess.run(
            [str(launcher), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(res.returncode, 0, f"Launcher failed: {res.stderr}")
        data_launcher = json.loads(res.stdout)
        self.assertTrue(data_launcher.get("secret_key_present"), "Launcher secret_key_present should be True")
        self.assertEqual(data_launcher.get("mode"), "stdio-daemon-first")

        # Execute status on binary
        res_bin = subprocess.run(
            [str(binary), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(res_bin.returncode, 0, f"Binary failed: {res_bin.stderr}")
        data_bin = json.loads(res_bin.stdout)
        self.assertTrue(data_bin.get("secret_key_present"), "Binary secret_key_present should be True")

    def test_mcp_config_registration(self):
        """Verify neo server is registered in mcp_config.json and settings.json."""
        config_path = Path("/Users/aaron/.gemini/config/mcp_config.json")
        self.assertTrue(config_path.exists())
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("neo", config_data.get("mcpServers", {}))
        self.assertEqual(
            config_data["mcpServers"]["neo"]["command"],
            "/Users/aaron/.local/bin/neo-mcp-launcher",
        )

        settings_path = Path("/Users/aaron/.gemini/settings.json")
        self.assertTrue(settings_path.exists())
        settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("neo", settings_data.get("mcpServers", {}))
        self.assertEqual(
            settings_data["mcpServers"]["neo"]["command"],
            "/Users/aaron/.local/bin/neo-mcp-launcher",
        )

    def test_skills_synchronization(self):
        """Verify Neo skill is present in Gemini, Claude, and Agent SDK locations."""
        skills = [
            Path("/Users/aaron/.gemini/config/skills/neo/SKILL.md"),
            Path("/Users/aaron/.claude/skills/neo.md"),
            Path("/Users/aaron/.agents/skills/neo/SKILL.md"),
        ]

        for skill_path in skills:
            self.assertTrue(skill_path.exists(), f"Skill missing: {skill_path}")
            content = skill_path.read_text(encoding="utf-8")
            self.assertIn("name: neo", content, f"name: neo missing in {skill_path}")
            self.assertIn("neo_submit_task", content, f"neo_submit_task missing in {skill_path}")
            self.assertIn("neo_list_byok_profiles", content, f"neo_list_byok_profiles missing in {skill_path}")
            self.assertIn("neo_add_byok_profile", content, f"neo_add_byok_profile missing in {skill_path}")
            self.assertIn("neo_set_byok_profile", content, f"neo_set_byok_profile missing in {skill_path}")
            self.assertIn("neo_remove_byok_profile", content, f"neo_remove_byok_profile missing in {skill_path}")
            self.assertIn("neo_list_byok_models", content, f"neo_list_byok_models missing in {skill_path}")


if __name__ == "__main__":
    unittest.main()
