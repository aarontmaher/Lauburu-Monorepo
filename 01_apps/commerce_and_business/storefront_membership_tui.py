#!/usr/bin/env python3
"""
Lauburu Headless Storefront, Membership Tiers & Merchandise Hub
==============================================================
User-facing commerce portal for athletes, gyms, and subscription members.
- Shopify Storefront GraphQL Integration
- Athlete Membership Tiers ($9/mo Athlete, $29/mo Pro, $99/mo Gym Team)
- Hardware Sensor Bundles (Movesense HR+ 512Hz Chest & Bicep straps)
- High-Performance Headless Checkout & Order Status
"""

import os
import sys
import json
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Horizontal, Vertical
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

class StorefrontMembershipApp(App):
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
        padding: 1;
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
    ]

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
            yield Static("🔒 Shopify Headless GraphQL Checkout • Cloudflare Edge • Press [q] Quit", id="status-text")
        yield Footer()

    def on_mount(self) -> None:
        self.render_store()

    def render_store(self) -> None:
        # Tier 1: Athlete
        t1 = Text()
        t1.append("🏃 ATHLETE MEMBERSHIP\n", style="bold cyan")
        t1.append(" $9 ", style="bold green reverse")
        t1.append(" / month\n\n", style="bold green")
        t1.append("• 512Hz ECG & Zone 2 Coaching\n", style="white")
        t1.append("• PTT Continuous Blood Pressure\n", style="white")
        t1.append("• Overnight Sleep Score & HRV", style="dim")
        self.query_one("#tier-athlete", Static).update(t1)

        # Tier 2: Pro
        t2 = Text()
        t2.append("🥋 PRO GRAPPLER\n", style="bold magenta")
        t2.append(" $29 ", style="bold gold1 reverse")
        t2.append(" / month\n\n", style="bold gold1")
        t2.append("• Full 3,044 OPML Kinematics Tree\n", style="white")
        t2.append("• MediaPipe 3D Skeleton Analysis\n", style="white")
        t2.append("• SmolAgents Custom AI Duelist", style="dim")
        self.query_one("#tier-pro", Static).update(t2)

        # Tier 3: Gym / Team
        t3 = Text()
        t3.append("🏛️ GYM & TEAM ROSTER\n", style="bold yellow")
        t3.append(" $99 ", style="bold red reverse")
        t3.append(" / month\n\n", style="bold red")
        t3.append("• Up to 25 Connected Movesense Pods\n", style="white")
        t3.append("• Live Mat Dashboard for Coaches\n", style="white")
        t3.append("• Local Airgap Vault Sync", style="dim")
        self.query_one("#tier-gym", Static).update(t3)

        # Hardware Products Table
        table_h = Table(title="📦 Official Hardware Pods & Sensor Accessories", expand=True, border_style="cyan")
        table_h.add_column("Product", style="cyan", width=26)
        table_h.add_column("Price", style="bold green", width=12)
        table_h.add_column("Stock / Availability", style="white")
        table_h.add_row("Movesense HR+ Pod (512Hz)", "$149.00 AUD", "[green]In Stock (Fast Dispatch)[/green]")
        table_h.add_row("Dual Bicep & Chest Strap Kit", "$39.00 AUD", "[green]In Stock[/green]")
        table_h.add_row("Mesh Node Mini Gateway", "$249.00 AUD", "[green]In Stock[/green]")
        table_h.add_row("Tatami Grappling Sensor Pod", "$199.00 AUD", "[yellow]Pre-Order (Batch 2)[/yellow]")
        self.query_one("#card-hardware", Static).update(table_h)

        # Headless Checkout & Cart
        table_c = Table(title="⚡ Secure Headless Shopify Checkout", expand=True, border_style="green")
        table_c.add_column("Cart Item", style="green")
        table_c.add_column("Qty", style="bold white", width=6)
        table_c.add_column("Total", style="bold gold1", width=14)
        table_c.add_row("Pro Grappler Membership (Annual)", "1", "$290.00 AUD")
        table_c.add_row("Movesense HR+ Pod Bundle", "1", "$149.00 AUD")
        table_c.add_row("[bold white]Order Total (Inc. GST)[/bold white]", "", "[bold green]$439.00 AUD[/bold green]")
        table_c.add_row("[dim]GraphQL Mutation[/dim]", "", "[dim]checkoutCreate(input: $cart)[/dim]")
        self.query_one("#card-checkout", Static).update(table_c)

if __name__ == "__main__":
    app = StorefrontMembershipApp()
    app.run()
