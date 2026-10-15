#!/usr/bin/env python3
"""
Lauburu Endless Pit - Live Telemetry TUI
"""

import time
import json
from pathlib import Path
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

LORA_PATH = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
ELO_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/endless_pit/elo_rankings.json")

def generate_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="log", size=10)
    )
    layout["main"].split_row(
        Layout(name="standard"),
        Layout(name="abliterated")
    )
    return layout

def update_ui(layout: Layout):
    # Read ELO
    elo_data = {"Alpha_Qwen_Max": 1200, "Omega_Qwen_Abliterated": 1200, "total_battles": 0}
    try:
        if ELO_PATH.exists():
            with open(ELO_PATH, "r") as f:
                elo_data = json.load(f)
    except Exception:
        pass

    # Read latest dataset entry
    latest_record = None
    log_entries = []
    try:
        if LORA_PATH.exists():
            with open(LORA_PATH, "r") as f:
                lines = f.readlines()
                pit_records = []
                for line in lines:
                    try:
                        rec = json.loads(line)
                        if "endless_pit" in rec.get("domain", ""):
                            pit_records.append(rec)
                    except Exception:
                        pass
                
                if pit_records:
                    latest_record = pit_records[-1]
                
                # Get last 5 for log
                for rec in pit_records[-5:]:
                    winner = rec.get("winner") or "DRAW"
                    domain_s = rec.get("standard", {}).get("result", {}).get("domain", "Unknown")
                    domain_a = rec.get("abliterated", {}).get("result", {}).get("domain", "Unknown")
                    log_entries.append(f"[{rec['timestamp']}] Cycle {rec.get('cycle', '?')}: {domain_s} vs {domain_a} -> WINNER: {winner}")
    except Exception:
        pass

    # Header
    header = Table.grid(expand=True)
    header.add_column(justify="center", ratio=1)
    header.add_row(f"[bold cyan]⚔️ THE ENDLESS PIT - LIVE ADVERSARIAL TELEMETRY ⚔️[/bold cyan] | BATTLES: {elo_data.get('total_battles', 0)}")
    layout["header"].update(Panel(header, style="white"))

    # Standard
    std_text = Text()
    std_text.append(f"ELO: {elo_data.get('Alpha_Qwen_Max', 1200)}\n\n", style="bold green")
    if latest_record:
        std_data = latest_record.get("standard", {})
        std_text.append(f"THESIS:\n", style="bold")
        std_text.append(f"\"{std_data.get('thesis', '')}\"\n\n", style="italic cyan")
        res = std_data.get("result", {})
        std_text.append(f"TASK: {res.get('domain', '')}\n")
        std_text.append(f"ACTION: {res.get('action', '')}\n")
        if 'compiled_size_kb' in res:
            std_text.append(f"SIZE: {res.get('compiled_size_kb')} KB\n", style="yellow")
    layout["standard"].update(Panel(std_text, title="[🧠] AGENT STANDARD (QWEN 3.8 MAX)", border_style="cyan"))

    # Abliterated
    abl_text = Text()
    abl_text.append(f"ELO: {elo_data.get('Omega_Qwen_Abliterated', 1200)}\n\n", style="bold red")
    if latest_record:
        abl_data = latest_record.get("abliterated", {})
        abl_text.append(f"THESIS:\n", style="bold")
        abl_text.append(f"\"{abl_data.get('thesis', '')}\"\n\n", style="italic magenta")
        res = abl_data.get("result", {})
        abl_text.append(f"TASK: {res.get('domain', '')}\n")
        abl_text.append(f"ACTION: {res.get('action', '')}\n")
        if 'compiled_size_kb' in res:
            abl_text.append(f"SIZE: {res.get('compiled_size_kb')} KB\n", style="yellow")
    layout["abliterated"].update(Panel(abl_text, title="[🌪️] AGENT ABLITERATED (27B)", border_style="red"))

    # Log
    log_text = Text("\n".join(log_entries))
    layout["log"].update(Panel(log_text, title="[⚖️] TRI-PROOF AUDIT LOG", border_style="white"))

if __name__ == "__main__":
    layout = generate_layout()
    with Live(layout, refresh_per_second=2, screen=True):
        try:
            while True:
                update_ui(layout)
                time.sleep(1)
        except KeyboardInterrupt:
            pass
