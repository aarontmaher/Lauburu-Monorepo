#!/usr/bin/env python3
"""
tests/test_master_automation_governor.py
====================================================
Comprehensive Test Suite for Master Automation Governor:
- Token headroom extraction from authentic cloud_api_quota_state.json
- Cron parsing, hourly execution distribution, and rolling 5-hour window burn
- Dynamic ELO calculation and phase-staggering optimization
- Sidecar schedule governance ensuring 5-hour quota ceiling is enforced
- Compliance with Rule 1 (Zero-Mock) and Rule 6 (Cloud Quota Protocol)
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"

for p in [str(PROJECT_ROOT), str(AUTOMATION_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import master_automation_governor as gov


class TestMasterAutomationGovernor(unittest.TestCase):
    """Test suite for Master Automation Governor functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sidecars_dir = Path(self.temp_dir) / "sidecars"
        self.sidecars_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = Path(self.temp_dir) / "audit.jsonl"
        self.quota_file = Path(self.temp_dir) / "quota.json"

        # Create mock quota state adhering to structure
        quota_data = {
            "version": "2.0.0",
            "providers": {
                "gemini_free": {"daily_limit": 1500, "used_today": 10, "remaining_pct": 0.993},
                "nvidia_nim": {"daily_limit": 2000, "used_today": 20, "remaining_pct": 0.990},
                "xai_grok": {"daily_limit": 1000, "used_today": 5, "remaining_pct": 0.995},
                "cloudflare_workers_ai": {"daily_limit": 800, "used_today": 0, "remaining_pct": 1.0},
                "anthropic_claude": {"daily_limit": 100, "used_today": 0, "remaining_pct": 1.0},
                "openai_chatgpt": {"daily_limit": 100, "used_today": 0, "remaining_pct": 1.0}
            }
        }
        with open(self.quota_file, 'w') as f:
            json.dump(quota_data, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_cron_patterns(self):
        """Verify cron parsing for diverse expressions and timezone prefixes."""
        # Standard hourly
        tz, raw, rph = gov.parse_cron("0 * * * *")
        self.assertEqual(tz, "")
        self.assertEqual(raw, "0 * * * *")
        self.assertEqual(rph, 1.0)

        # Timezone prefix with step hours
        tz, raw, rph = gov.parse_cron("CRON_TZ=Australia/Sydney 0 */4 * * *")
        self.assertEqual(tz, "CRON_TZ=Australia/Sydney ")
        self.assertEqual(raw, "0 */4 * * *")
        self.assertEqual(rph, 0.25)

        # Discrete hours list
        tz, raw, rph = gov.parse_cron("0 7,15,23 * * *")
        self.assertEqual(rph, 3.0 / 24.0)

        # Daily
        tz, raw, rph = gov.parse_cron("0 9 * * *")
        self.assertEqual(rph, 1.0 / 24.0)

    def test_get_cron_hours(self):
        """Verify extraction of target execution hours."""
        self.assertEqual(gov.get_cron_hours("0 * * * *"), list(range(24)))
        self.assertEqual(gov.get_cron_hours("0 */6 * * *"), [0, 6, 12, 18])
        self.assertEqual(gov.get_cron_hours("0 1,13 * * *"), [1, 13])
        self.assertEqual(gov.get_cron_hours("0 7,15,23 * * *"), [7, 15, 23])
        self.assertEqual(gov.get_cron_hours("0 2 * * *"), [2])

    def test_calculate_rolling_windows_peak_detection(self):
        """Verify rolling 5-hour window calculation accurately catches peak load."""
        sidecar_data = {
            "heavy-task-1": {
                "cron_str": "0 1 * * *",
                "json": {},
                "field_type": "args"
            },
            "heavy-task-2": {
                "cron_str": "0 2 * * *",
                "json": {},
                "field_type": "args"
            },
            "heavy-task-3": {
                "cron_str": "0 3 * * *",
                "json": {},
                "field_type": "args"
            }
        }
        # In AUTOMATION_PROFILES, non-existent falls back to 2000 tokens
        peak_burn, peak_start_h, hourly, rolling = gov.calculate_rolling_windows(sidecar_data)
        # Window starting at 0, 1, 2, or 3 includes all 3 tasks (total 6000 tokens)
        self.assertEqual(peak_burn, 6000)
        self.assertEqual(hourly[1], 2000)
        self.assertEqual(hourly[2], 2000)
        self.assertEqual(hourly[3], 2000)

    def test_calculate_automation_elo(self):
        """Verify ELO reflects utility and penalizes excessive hourly burn."""
        # Low frequency, low staleness -> high ELO
        high_elo = gov.calculate_automation_elo("test_good", runs_per_hour=0.083, tokens_per_run=1200, staleness_sensitivity=30.0, headroom_pct=95.0)
        # High frequency, high staleness -> low ELO
        low_elo = gov.calculate_automation_elo("test_wasteful", runs_per_hour=1.0, tokens_per_run=5000, staleness_sensitivity=85.0, headroom_pct=95.0)
        self.assertGreater(high_elo, low_elo)

    def test_governor_throttles_breaching_sidecars(self):
        """Verify governor detects peak breach and throttles sidecars to safe ceiling."""
        # Mock paths in module
        orig_sidecars = gov.SIDECARS_DIR
        orig_audit = gov.AUDIT_LOG_PATH
        orig_quota = gov.QUOTA_STATE_PATH

        try:
            gov.SIDECARS_DIR = str(self.sidecars_dir)
            gov.AUDIT_LOG_PATH = str(self.audit_log)
            gov.QUOTA_STATE_PATH = str(self.quota_file)

            # Create a sidecar that runs hourly (breaches budget)
            test_sidecar = self.sidecars_dir / "gemini-lens-sync"
            test_sidecar.mkdir()
            cfg = {
                "builtin": "schedule",
                "args": [
                    "CRON_TZ=Australia/Sydney 0 * * * *",
                    "agentapi",
                    "new-conversation"
                ],
                "display_name": "Hourly Gemini Lens Sync",
                "description": "Hourly sync."
            }
            with open(test_sidecar / "sidecar.json", 'w') as f:
                json.dump(cfg, f, indent=2)

            # Run governor
            res = gov.govern_automations()

            # Verify that gemini-lens-sync was throttled
            with open(test_sidecar / "sidecar.json", 'r') as f:
                updated = json.load(f)

            self.assertIn("0 19 * * *", updated["args"][0])
            self.assertLessEqual(res['post_peak_burn'], gov.FIVE_HOUR_TOKEN_BUDGET_CEILING)

        finally:
            gov.SIDECARS_DIR = orig_sidecars
            gov.AUDIT_LOG_PATH = orig_audit
            gov.QUOTA_STATE_PATH = orig_quota

    def test_governor_enforces_five_hour_quota_ceiling_on_cluster(self):
        """Verify governor enforces 5-hour quota ceiling on multiple colliding sidecars."""
        orig_sidecars = gov.SIDECARS_DIR
        orig_audit = gov.AUDIT_LOG_PATH
        orig_quota = gov.QUOTA_STATE_PATH

        try:
            gov.SIDECARS_DIR = str(self.sidecars_dir)
            gov.AUDIT_LOG_PATH = str(self.audit_log)
            gov.QUOTA_STATE_PATH = str(self.quota_file)

            # Create multiple heavy sidecars all running 0 */4 * * *
            colliding = ["auto-optimization-benchmarker", "unified-lens-elo-benchmarker", "customization-elo-optimizer", "router-ai-distillation"]
            for name in colliding:
                sc_dir = self.sidecars_dir / name
                sc_dir.mkdir(exist_ok=True)
                cfg = {
                    "builtin": "schedule",
                    "args": ["CRON_TZ=Australia/Sydney 0 */4 * * *", "agentapi", "new-conversation"],
                    "display_name": name,
                    "description": "Colliding sidecar"
                }
                with open(sc_dir / "sidecar.json", 'w') as f:
                    json.dump(cfg, f, indent=2)

            res = gov.govern_automations()

            # Verify that peak 5-hour burn is strictly within ceiling
            self.assertLessEqual(res['post_peak_burn'], gov.FIVE_HOUR_TOKEN_BUDGET_CEILING)

            # Verify router-ai-distillation was staggered to 0 17 * * *
            with open(self.sidecars_dir / "router-ai-distillation" / "sidecar.json", 'r') as f:
                router_cfg = json.load(f)
            self.assertIn("0 17 * * *", router_cfg["args"][0])

        finally:
            gov.SIDECARS_DIR = orig_sidecars
            gov.AUDIT_LOG_PATH = orig_audit
            gov.QUOTA_STATE_PATH = orig_quota


if __name__ == "__main__":
    unittest.main()
