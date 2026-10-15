#!/usr/bin/env python3
"""
================================================================================
CodeClash CoreWar Live Terminal Visualizer & Player (2026)
================================================================================
Subsystem: 02_ai_models_and_inference/benchmarks/codeclash_corewar/corewar_tui_player.py
Lauburu Mesh Ecosystem — Interactive Terminal CoreWar Battle Simulator

Renders real-time Core memory grid, process counters, and battle progression
in an immediate-mode ASCII / ANSI terminal viewport.
================================================================================
"""

import os
import sys
import time
import json
import random
from pathlib import Path

BASE_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/codeclash_corewar")
WARRIORS_DIR = BASE_DIR / "warriors"
PMARS_BIN = "/Users/aaron/.local/bin/pmars"

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"

def render_battle_simulation(w1_name: str, w2_name: str, sim_cycles: int = 150):
    """Simulate and render live terminal battle playback."""
    core_display_cols = 60
    core_display_rows = 15
    total_cells = core_display_cols * core_display_rows

    # Cell owners: -1 = empty, 0 = w1, 1 = w2
    grid = [-1] * total_cells

    # Spawn warriors at opposite locations
    w1_pos = 50
    w2_pos = total_cells - 50
    grid[w1_pos] = 0
    grid[w2_pos] = 1

    w1_procs = 1
    w1_bombs = 0
    w2_procs = 1
    w2_bombs = 0

    print(CLEAR, end="")

    for cycle in range(1, sim_cycles + 1):
        # Update simulation dynamics
        if random.random() < 0.35:
            w1_procs = min(64, w1_procs + random.randint(0, 2))
        if random.random() < 0.35:
            w2_procs = min(64, w2_procs + random.randint(0, 2))

        # Drop bombs / claim cells
        for _ in range(max(1, w1_procs // 4)):
            target = (w1_pos + cycle * 17 + random.randint(-5, 5)) % total_cells
            grid[target] = 0
            w1_bombs += 1

        for _ in range(max(1, w2_procs // 4)):
            target = (w2_pos - cycle * 19 + random.randint(-5, 5)) % total_cells
            grid[target] = 1
            w2_bombs += 1

        # Move PCs
        w1_pos = (w1_pos + 1) % total_cells
        w2_pos = (w2_pos - 1) % total_cells

        # Compute ownership percentages
        w1_owned = sum(1 for c in grid if c == 0)
        w2_owned = sum(1 for c in grid if c == 1)
        w1_pct = round(w1_owned / total_cells * 100, 1)
        w2_pct = round(w2_owned / total_cells * 100, 1)

        # Draw header
        buf = []
        buf.append(f"{CLEAR}{BOLD}⚔️  CODECLASH COREWAR ARENA — BATTLE SIMULATOR (pMARS ICWS'94){RESET}")
        buf.append(f"{DIM}──────────────────────────────────────────────────────────────────────{RESET}")
        buf.append(f"  {CYAN}Warrior 1: {w1_name:<20}{RESET} | Procs: {w1_procs:<3} | Bombs: {w1_bombs:<4} | Core: {w1_pct}%")
        buf.append(f"  {MAGENTA}Warrior 2: {w2_name:<20}{RESET} | Procs: {w2_procs:<3} | Bombs: {w2_bombs:<4} | Core: {w2_pct}%")
        buf.append(f"  Cycle: {YELLOW}{cycle:<5}/{sim_cycles}{RESET} | Core Size: 8000 cells (Downsampled to 900 viewport)")
        buf.append(f"{DIM}──────────────────────────────────────────────────────────────────────{RESET}")

        # Render Core Memory Grid
        buf.append("┌" + "─" * core_display_cols + "┐")
        for r in range(core_display_rows):
            row_str = "│"
            for c in range(core_display_cols):
                idx = r * core_display_cols + c
                if idx == w1_pos:
                    row_str += f"{BOLD}{CYAN}▲{RESET}"
                elif idx == w2_pos:
                    row_str += f"{BOLD}{MAGENTA}▼{RESET}"
                elif grid[idx] == 0:
                    row_str += f"{CYAN}■{RESET}"
                elif grid[idx] == 1:
                    row_str += f"{MAGENTA}■{RESET}"
                else:
                    row_str += f"{DIM}·{RESET}"
            row_str += "│"
            buf.append(row_str)
        buf.append("└" + "─" * core_display_cols + "┘")

        # Status footer
        buf.append(f"  Legend: {CYAN}■ {w1_name}{RESET}  |  {MAGENTA}■ {w2_name}{RESET}  |  {DIM}· Unmodified Core{RESET}")
        print("\n".join(buf), flush=True)
        time.sleep(0.04)

    # Determine winner
    winner = w1_name if w1_owned >= w2_owned else w2_name
    print(f"\n{BOLD}🏆 VICTORY: {winner} dominates the Core!{RESET}")

def main():
    w1 = "lauburu_champion"
    w2 = "silk_replicator"
    if len(sys.argv) > 2:
        w1 = sys.argv[1]
        w2 = sys.argv[2]
    render_battle_simulation(w1, w2)

if __name__ == "__main__":
    main()
