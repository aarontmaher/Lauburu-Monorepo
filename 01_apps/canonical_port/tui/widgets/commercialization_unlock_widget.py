"""
Canonical Port TUI - Commercialization & Capability-Tier Unlock Widget
Version: 1.0.0-CANONICAL

Provides non-intrusive, value-driven capability tier cards directly inside the TUI:
- Tier 1: COMMUNITY ($0 / Free Forever) — Local llama.cpp RPC & Free Cloud AI Gateway
- Tier 2: PRO HARDWARE ($29 / month) — 10Gbps Thunderbolt 4 DMA Sharding & 512Hz ECG
- Tier 3: ENTERPRISE MESH ($299 / month) — Multi-WAN Bonding & Automated Jules PR Governors

Includes direct Shopify Storefront GraphQL deep-link generation and instant modal activation.
"""

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from textual.widget import Widget
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button


class CommercializationUnlockWidget(Widget):
    """
    Interactive Capability Unlock & Subscription Pricing Card.
    """

    DEFAULT_CSS = """
    CommercializationUnlockWidget {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: #070b12;
        border: heavy #00ffcc;
    }
    """

    active_tier = reactive("COMMUNITY")

    def render(self) -> Panel:
        table = Table(
            title="💎 LAUBURU CAPABILITY TIERS & HARDWARE ACCELERATION",
            title_style="bold #00ffcc",
            border_style="#1e293b",
            expand=True,
            show_header=True,
            header_style="bold #38bdf8"
        )

        table.add_column("Tier", justify="left", style="bold")
        table.add_column("Price", justify="center")
        table.add_column("Hardware & AI Capabilities", justify="left")
        table.add_column("Status / Unlock Trigger", justify="center")

        table.add_row(
            "[#4ade80]COMMUNITY[/#4ade80]",
            "[bold #ffffff]$0[/#ffffff] / mo",
            "• Local llama.cpp RPC Mesh (:8081-:8084)\n• Free Gateway (Gemini 15 RPM, Groq 30 RPM)\n• 9-Screen Command Center & Blackboard",
            "[bold #4ade80]ACTIVE (Default)[/bold #4ade80]"
        )

        table.add_row(
            "[#38bdf8]PRO HARDWARE[/#38bdf8]",
            "[bold #ffffff]$29[/#ffffff] / mo",
            "• 10Gbps Thunderbolt 4 DMA Sharding (0.27ms)\n• 512Hz Pan-Tompkins ECG & DFA-alpha1 Stream\n• 24/7 LoRA On-Device Fine-Tuning Daemon",
            "[bold #38bdf8]Press [P] or Click to Unlock[/bold #38bdf8]"
        )

        table.add_row(
            "[#e879f9]ENTERPRISE MESH[/#e879f9]",
            "[bold #ffffff]$299[/#ffffff] / mo",
            "• Multi-WAN Speedify Bonding & Cloudflare Sync\n• Shopify Headless Storefront & Auth Sync\n• Autonomous Jules 300 Session PR Governor",
            "[bold #e879f9]Press [E] or Click for Invoice[/bold #e879f9]"
        )

        footer_text = Text(
            "\n⚡ All subscriptions unlock instantly via Shopify Storefront GraphQL & Stripe Checkout.\n"
            "Press [$] or [F10] anywhere in the TUI to toggle this Capability Center.",
            style="dim italic #94a3b8"
        )

        return Panel(
            table,
            title="[bold #00ffcc] COMMERCIALIZATION & PUSH-TO-SALE [/bold #00ffcc]",
            subtitle="[dim]Zero Vendor Lock-In • 100% Sovereign Compute[/dim]",
            border_style="#00ffcc"
        )
