"""
Unit Tests for Canonical Storefront TUI & Product Catalog.
==========================================================
Subsystem: 01_apps/user_facing_and_scaling/tests/test_canonical_storefront.py
"""

import unittest
from pathlib import Path
import sys

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/user_facing_and_scaling"))

from shopify_storefront.core.models import CanonicalProduct, MembershipTier, HardwareBundle
from shopify_storefront.presentation.catalog import CANONICAL_PRODUCTS
from shopify_storefront.presentation.pricing import MEMBERSHIP_TIERS, HARDWARE_BUNDLES
from shopify_storefront.presentation.tui import StorefrontMembershipApp
from shopify_storefront.graphql.client import ShopifyStorefrontClient

class TestCanonicalStorefront(unittest.TestCase):
    """Verifies the canonical 12-product catalog, pricing, and TUI actions."""

    def test_canonical_products_count(self):
        """Assert exactly 12 active canonical products exist."""
        self.assertEqual(len(CANONICAL_PRODUCTS), 12)

    def test_vendor_distribution(self):
        """Assert products are properly mapped across Subliminator, ODMPOD, and Printful."""
        vendors = {p.vendor for p in CANONICAL_PRODUCTS}
        self.assertIn("Subliminator", vendors)
        self.assertIn("ODMPOD", vendors)
        self.assertIn("Printful", vendors)

    def test_symbol_scale_specifications(self):
        """Assert critical symbol scale deltas are enforced."""
        joggers = next(p for p in CANONICAL_PRODUCTS if "Joggers" in p.title)
        self.assertIn("Shrunk", joggers.symbol_scale)
        self.assertIn("90px", joggers.symbol_scale)

        backpack = next(p for p in CANONICAL_PRODUCTS if "Backpack" in p.title)
        self.assertIn("Color-Matched", backpack.symbol_scale)

        fanny = next(p for p in CANONICAL_PRODUCTS if "Fanny" in p.title)
        self.assertIn("75px", fanny.symbol_scale)

    def test_membership_tiers(self):
        """Assert 3 membership tiers exist with correct prices."""
        self.assertEqual(len(MEMBERSHIP_TIERS), 3)
        prices = [t.price_usd_month for t in MEMBERSHIP_TIERS]
        self.assertEqual(prices, [9.00, 29.00, 99.00])

    def test_headless_checkout_creation(self):
        """Assert client generates valid headless checkout sessions."""
        client = ShopifyStorefrontClient()
        session = client.create_checkout([
            {"variant_id": "gid://shopify/ProductVariant/test", "quantity": 1, "title": "Test Rashguard", "price": 65.0}
        ])
        self.assertTrue(session.checkout_url.startswith("https://"))
        self.assertIn("checkouts", session.checkout_url)

    def test_tui_app_initialization_and_actions(self):
        """Assert TUI app state and action handlers cycle products."""
        app = StorefrontMembershipApp()
        self.assertEqual(app.product_index, 0)
        app.action_next_product()
        self.assertEqual(app.product_index, 1)
        app.action_prev_product()
        self.assertEqual(app.product_index, 0)
        app.action_checkout()
        self.assertTrue(app.last_checkout_url.startswith("https://"))
        app.action_checkout_gear()
        self.assertTrue(app.last_checkout_url.startswith("https://"))

if __name__ == "__main__":
    unittest.main()
