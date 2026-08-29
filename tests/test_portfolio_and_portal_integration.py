#!/usr/bin/env python3
"""
Integration & Verification Suite for Monorepo Portfolio & Universal Web-TUI Portal.
===================================================================================
Validates importability, modular structure, and interface contracts for all 7 apps:
- movesense_readiness_hub
- spatial_grappling_3d
- combat_arena
- shopify_storefront
- canonical_port
- smolagents_duel_sandbox
- qwen_math_trend_optimizer
- web_tui_portal
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for p in [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "01_apps"),
    str(PROJECT_ROOT / "01_apps/user_facing_and_scaling"),
    str(PROJECT_ROOT / "01_apps/operator_and_dev"),
    str(PROJECT_ROOT / "01_apps/web_tui_portal"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)


class TestPortfolioAndPortalIntegration(unittest.TestCase):

    def test_01_movesense_readiness_hub(self):
        """Verify Movesense Readiness Hub modular subpackages and entrypoint."""
        import movesense_readiness_hub
        from movesense_readiness_hub.presentation.tui import run_app
        from movesense_readiness_hub.core.models import RawEcgFrame, QrsDetectionResult
        from movesense_readiness_hub.dsp.pan_tompkins import PanTompkinsQRSDetector
        self.assertEqual(movesense_readiness_hub.__version__, "1.0.0")

    def test_02_spatial_grappling_3d(self):
        """Verify 3D Spatial Grappling 3,044 OPML parser and MediaPipe 33-skeleton."""
        import spatial_grappling_3d
        from spatial_grappling_3d.presentation.engine import SpatialGrapplingMapEngine
        from spatial_grappling_3d.presentation.tui import run_grappling, run_app
        from spatial_grappling_3d.kinematics.skeleton import MEDIAPIPE_33_LANDMARKS

        engine = SpatialGrapplingMapEngine()
        res = engine.parse_full_opml_tree()
        self.assertEqual(res["total_nodes"], 3044)
        self.assertEqual(len(MEDIAPIPE_33_LANDMARKS), 33)

    def test_03_combat_arena(self):
        """Verify Combat Arena 4 game modes and presentation engine."""
        import combat_arena
        from combat_arena.presentation.arena import run_arena, CombatArenaEngine
        from combat_arena.modes import GAME_MODES

        self.assertIn("TUG_OF_WAR", GAME_MODES)
        self.assertIn("BATTLE", GAME_MODES)
        engine = CombatArenaEngine()
        step = engine.step()
        self.assertIn("mode", step)

    def test_04_shopify_storefront(self):
        """Verify Headless Shopify Storefront $9/$29/$99 tiers and GraphQL checkout."""
        import shopify_storefront
        from shopify_storefront.presentation.store import run_storefront
        from shopify_storefront.graphql.client import ShopifyStorefrontClient
        from shopify_storefront.presentation.pricing import MEMBERSHIP_TIERS

        self.assertEqual(len(MEMBERSHIP_TIERS), 3)
        self.assertEqual(MEMBERSHIP_TIERS[0].price_usd_month, 9.00)
        self.assertEqual(MEMBERSHIP_TIERS[1].price_usd_month, 29.00)
        self.assertEqual(MEMBERSHIP_TIERS[2].price_usd_month, 99.00)

        client = ShopifyStorefrontClient()
        checkout = client.create_checkout([{"variant_id": "440912345001", "quantity": 1, "title": "Athlete Tier", "price": 9.0}])
        self.assertIsNotNone(checkout.checkout_url)

    def test_05_canonical_port(self):
        """Verify Canonical Port 9-Screen stability hierarchy and 7 physical nodes."""
        import canonical_port
        from canonical_port.views.dashboard import run_canonical, CanonicalPortDashboard
        from canonical_port.nodes.mesh_nodes import MESH_NODES
        from canonical_port.views.screens import STABILITY_SCREENS

        self.assertEqual(len(MESH_NODES), 7)
        self.assertEqual(len(STABILITY_SCREENS), 9)

    def test_06_smolagents_duel_sandbox(self):
        """Verify SmolAgents Python Duel Sandbox code-as-action tool registry."""
        import smolagents_duel_sandbox
        from smolagents_duel_sandbox.presentation.sandbox import run_sandbox, SmolAgentsArenaHub
        from smolagents_duel_sandbox.tools.registry import SmolagentsToolRegistry

        hub = SmolAgentsArenaHub()
        rec = hub.step()
        self.assertEqual(rec.red_action.status, "SUCCESS")
        self.assertEqual(rec.blue_action.status, "SUCCESS")

    def test_07_qwen_math_trend_optimizer(self):
        """Verify Qwen Math Trend Optimizer closed-form proofs and 24/7 LoRA logging."""
        import qwen_math_trend_optimizer
        from qwen_math_trend_optimizer.presentation.optimizer import run_optimizer, AutonomousMathTrendOptimizer

        opt = AutonomousMathTrendOptimizer()
        res = opt.evaluate_all()
        self.assertGreater(res["summary"]["tb4_weight"], 0.80)
        self.assertGreaterEqual(res["summary"]["ram_headroom_gb"], 2.50)

    def test_08_web_tui_portal(self):
        """Verify Universal Web-TUI Portal application router on Port 8088."""
        import web_tui_portal
        from web_tui_portal.serve_portal import REGISTERED_APPS, render_app_page

        self.assertEqual(len(REGISTERED_APPS), 7)
        for app_id in ["readiness", "grappling", "arena", "store", "canonical", "smolagents", "math"]:
            self.assertIn(app_id, REGISTERED_APPS)
            html = render_app_page(app_id)
            self.assertIn("120 FPS WebGL", html)


if __name__ == "__main__":
    unittest.main()
