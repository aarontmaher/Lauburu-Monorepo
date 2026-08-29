"""
Shopify Storefront Textual TUI Application.
===========================================
Subsystem: 01_apps/user_facing_and_scaling/shopify_storefront/presentation/tui.py
"""

import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.text import Text

from .pricing import MEMBERSHIP_TIERS, HARDWARE_BUNDLES
from ..graphql.client import ShopifyStorefrontClient

class StorefrontMembershipApp(App):
    """Interactive Headless Commerce & Membership TUI."""

    TITLE = "🛍️ LAUBURU STORE & MEMBERSHIP — HEADLESS COMMERCE"
    SUB_TITLE = "Athlete Subscriptions • Hardware Sensor Bundles • Headless GraphQL Checkout"

    CSS = """
    Screen {
        background: #070b12;
        color: #f8fafc;
    }
    #hero-container {
        height: 12;
        margin: 1 1;
    }
    .tier-card {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    .tier-card:hover {
        border: solid #38bdf8;
    }
    #body-container {
        height: 1fr;
        margin: 0 1 1 1;
    }
    .product-card {
        background: #0b111c;
        border: solid #1e293b;
        height: 100%;
        padding: 1 2;
    }
    #footer-bar {
        height: 3;
        background: #0b111c;
        border-top: solid #1e293b;
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "select_tier1", "Athlete Tier ($9)"),
        ("2", "select_tier2", "Pro Tier ($29)"),
        ("3", "select_tier3", "Gym Tier ($99)"),
        ("c", "checkout", "Checkout"),
    ]

    def __init__(self):
        super().__init__()
        self.client = ShopifyStorefrontClient()
        self.selected_tier = MEMBERSHIP_TIERS[1]  # Pro Tier
        self.last_checkout_url = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="hero-container"):
            yield Static(id="tier-athlete", classes="tier-card")
            yield Static(id="tier-pro", classes="tier-card")
            yield Static(id="tier-gym", classes="tier-card")

        with Horizontal(id="body-container"):
            yield Static(id="card-hardware", classes="product-card")
            yield Static(id="card-checkout", classes="product-card")

        with Horizontal(id="footer-bar"):
            yield Static("🔒 Shopify Headless GraphQL Checkout • [1] $9 [2] $29 [3] $99 • [c] Checkout • [q] Quit", id="status-text")
        yield Footer()

    def on_mount(self) -> None:
        self.render_store()

    def render_store(self) -> None:
        # Tier 1: Athlete
        t1 = Text()
        t1.append("🏃 ATHLETE MEMBERSHIP\n", style="bold cyan")
        t1.append(" $9 ", style="bold green reverse")
        t1.append(" / month\n\n", style="bold green")
        for f in MEMBERSHIP_TIERS[0].features:
            t1.append(f"• {f}\n", style="white")
        self.query_one("#tier-athlete", Static).update(t1)

        # Tier 2: Pro
        t2 = Text()
        t2.append("🥋 PRO ATHLETE & COACH (POPULAR)\n", style="bold yellow")
        t2.append(" $29 ", style="bold green reverse")
        t2.append(" / month\n\n", style="bold green")
        for f in MEMBERSHIP_TIERS[1].features:
            t2.append(f"• {f}\n", style="white")
        self.query_one("#tier-pro", Static).update(t2)

        # Tier 3: Gym
        t3 = Text()
        t3.append("🏛️ GYM & TEAM LICENSE\n", style="bold magenta")
        t3.append(" $99 ", style="bold green reverse")
        t3.append(" / month\n\n", style="bold green")
        for f in MEMBERSHIP_TIERS[2].features:
            t3.append(f"• {f}\n", style="white")
        self.query_one("#tier-gym", Static).update(t3)

        # Hardware Bundles
        hw = Text()
        hw.append("📦 MEDICAL HARDWARE SENSOR BUNDLES\n\n", style="bold green")
        for b in HARDWARE_BUNDLES:
            hw.append(f"• {b.name} (${b.price_usd:.2f})\n", style="bold cyan")
            hw.append(f"  {b.sensor_model} ({b.sample_rate_hz}Hz ECG)\n", style="dim")
        self.query_one("#card-hardware", Static).update(hw)

        # Active Checkout State
        chk = Text()
        chk.append("🛒 ACTIVE CART & CHECKOUT SESSION\n\n", style="bold blue")
        chk.append(f"• Selected Plan: {self.selected_tier.name} (${self.selected_tier.price_usd_month}/mo)\n", style="bold yellow")
        chk.append("• Headless API: Storefront GraphQL (2026-01)\n", style="white")
        if self.last_checkout_url:
            chk.append(f"• Live Checkout URL: {self.last_checkout_url}\n", style="bold green")
        else:
            chk.append("• Press [c] to initiate GraphQL checkout session\n", style="dim")
        chk.append("• 100% Fail-Closed Airgap: Zero biometrics in billing data", style="bold green")
        self.query_one("#card-checkout", Static).update(chk)

    def action_select_tier1(self) -> None:
        self.selected_tier = MEMBERSHIP_TIERS[0]
        self.render_store()

    def action_select_tier2(self) -> None:
        self.selected_tier = MEMBERSHIP_TIERS[1]
        self.render_store()

    def action_select_tier3(self) -> None:
        self.selected_tier = MEMBERSHIP_TIERS[2]
        self.render_store()

    def action_checkout(self) -> None:
        session = self.client.create_checkout([
            {
                "variant_id": self.selected_tier.shopify_variant_id,
                "quantity": 1,
                "title": self.selected_tier.name,
                "price": self.selected_tier.price_usd_month
            }
        ])
        self.last_checkout_url = session.checkout_url
        self.render_store()

def run_storefront():
    """Runs the Shopify Storefront Textual TUI Application."""
    app = StorefrontMembershipApp()
    app.run()

if __name__ == "__main__":
    run_storefront()
