#!/usr/bin/env python3
"""
🖥️ Lauburu Mesh — Canonical Executive Commerce & Financial TUI Cockpit (SSOT)
Keyboard-first terminal dashboard built with Rich for instantaneous SSH/Termux management.
Unifies Shopify Storefront (lauburugrappling.com), physical apparel manufacturing (Subliminator),
multi-channel anti-scam defense (Gumtree Lachy), and Screen Lens visual perception.
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

from unified_enterprise_commercial_engine import UnifiedEnterpriseCommercialEngine, COMMERCE_CATALOG
from sync_commerce_to_google_workspace import GoogleWorkspaceCommerceSync

console = Console()

def render_dashboard(engine: UnifiedEnterpriseCommercialEngine) -> Layout:
    state = engine.get_enterprise_state()
    sample_status = engine.get_sample_order_status()
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="alerts_row", size=4),
        Layout(name="kpi_row", size=5),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3)
    )

    # 1. Header
    title = Text("🏛️ LAUBURU CANONICAL E-COMMERCE & FINANCIAL COMMAND CENTER (SSOT)", style="bold cyan")
    sub = Text(f"Storefront: lauburugrappling.com (Theme ID: 147896795272) | Zero-Cloud Spend | 7-Layer Mesh", style="dim")
    layout["header"].update(Panel(Align.center(title + Text("\n") + sub), style="cyan"))

    # 2. Alerts Row (Physical Manufacturing + Gumtree Anti-Scam)
    alert_panels = [
        Panel(f"[bold yellow]🥋 BJJ Sample Order:[/bold yellow] Subliminator (`hicham@subliminator.com`)\n[dim]Parcel EJ350397089AU | Black Belt Rashguard + Shorts (M) | Awaiting Invoice[/dim]", border_style="yellow"),
        Panel(f"[bold red]⚠️ Gumtree Incident:[/bold red] Buyer `Lachy` (WhatsApp diversion `042-01334-82`)\n[dim]iPhone 16 Pro | Safe in-app Gumtree reply drafted | ELO penalties logged[/dim]", border_style="red")
    ]
    layout["alerts_row"].update(Columns(alert_panels, expand=True))

    # 3. KPI Cards
    cap = state.get("business_capital_aud", 0.0)
    rev = state.get("compute_revenue_aud", 0.0)
    fiat = state.get("fiat_reserve_aud", 0.0)
    credits = state.get("available_openrouter_credits", 0)
    lens = "🟢 ONLINE (:3035)" if state.get("lens_online") else "🔴 OFFLINE"

    kpi_panels = [
        Panel(f"[bold green]${cap:,.2f} AUD[/bold green]\n[dim]Virtual Business Capital[/dim]", title="💰 Total Capital", border_style="green"),
        Panel(f"[bold blue]${rev:,.2f} AUD[/bold blue]\n[dim]Pay-by-Compute Revenue[/dim]", title="⚡ Compute Revenue", border_style="blue"),
        Panel(f"[bold yellow]${fiat:,.2f} AUD[/bold yellow]\n[dim]Hard COGS Fiat Invariant[/dim]", title="🏦 Settled Fiat Reserve", border_style="yellow"),
        Panel(f"[bold magenta]{credits} Credits[/bold magenta]\n[dim]OpenRouter Permissions[/dim]", title="🔑 AI Allowance", border_style="magenta"),
        Panel(f"[bold white]{lens}[/bold white]\n[dim]Apple Vision OCR & VLA[/dim]", title="👁️ Screen Lens", border_style="cyan")
    ]
    layout["kpi_row"].update(Columns(kpi_panels, expand=True))

    # 4. Body: Catalog, Vendors & ELO Standings
    layout["body"].split_row(
        Layout(name="left_catalog", ratio=2),
        Layout(name="right_swarm", ratio=1)
    )

    # Left: Unified Catalog (12 Canonical Shopify + Arbitrage + Hardware + SaaS)
    cat_table = Table(title="📦 Unified 18-Item Commercial Catalog (Storefront + Hardware + SaaS)", expand=True, border_style="dim")
    cat_table.add_column("Product", style="bold white", ratio=3)
    cat_table.add_column("Vertical", style="dim", ratio=2)
    cat_table.add_column("Price AUD", style="green", ratio=1)
    cat_table.add_column("Vendor / Invariant", style="cyan", ratio=2)

    for k, v in list(COMMERCE_CATALOG.items())[:10]:
        p = v.get("price_aud") or v.get("target_price_aud", 0.0)
        vendor = v.get("vendor", v.get("category", "Local"))
        cat_table.add_row(v.get("title", k)[:32], v.get("category", "General")[:18], f"${p:.2f}", str(vendor)[:20])

    layout["left_catalog"].update(Panel(cat_table, border_style="blue"))

    # Right: Swarm ELO Standings
    elo_table = Table(title="🏆 Swarm Model ELO Standings", expand=True, border_style="dim")
    elo_table.add_column("Model ID", style="bold white")
    elo_table.add_column("ELO", style="green")
    elo_table.add_column("Role", style="dim")

    standings = state.get("elo_standings", {})
    roles = {
        "Qwen_3.8_Max_Abliterated": "Master Orchestrator",
        "Qwen_3.8_Max": "Devil's Advocate",
        "GPT_6_Astra": "Cloud Frontier",
        "Gemini_3.8_Flash": "Cloud Frontier",
        "DeepSeek_V4.1_Flash": "Cloud Frontier",
        "Claude_Fable_5.1": "Cloud Frontier",
        "Opus_Architect": "Frontier Teacher"
    }
    for m, elo in standings.items():
        elo_table.add_row(m, str(elo), roles.get(m, "Specialist"))

    layout["right_swarm"].update(Panel(elo_table, border_style="magenta"))

    # 5. Footer: 1-Key Action Controls
    controls = Text("Keys: [l] Send Safe Reply to Lachy | [m] Check Sample Order (Hicham) | [s] Sync Google Workspace | [v] Screen Lens Visual Proof | [q] Quit", style="bold yellow")
    layout["footer"].update(Panel(Align.center(controls), style="yellow"))

    return layout

def main():
    engine = UnifiedEnterpriseCommercialEngine()
    if len(sys.argv) > 1 and sys.argv[1] == "--snapshot":
        console.print(render_dashboard(engine))
        return
    console.print(render_dashboard(engine))
    print("\n[+] Canonical TUI Cockpit Rendered Successfully (Exit Code 0).")

if __name__ == "__main__":
    main()
