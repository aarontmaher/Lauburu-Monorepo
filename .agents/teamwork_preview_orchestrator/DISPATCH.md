# Dispatch Log

## 2026-08-27T07:18:54Z
Received user request to orchestrate the build of an Obsidian-style Project Architecture Explorer inside the Canonical Port TUI.

Task:
Build an Obsidian-style Project Architecture Explorer inside the Canonical Port TUI. It must provide a hierarchical or graph-like view of the Lauburu monorepo ecosystem, allowing users to filter by category (e.g., 'Applications') and visualize structural dependencies (e.g., showing which apps rely on the Compute Hub or Movesense), alongside their features.

Requirements:
- R1: Obsidian Vault Parsing Engine (markdown files in `obsidian_vault/`, frontmatter, Wikilinks `[[...]]`, dependency graph)
- R2: Dual-Layout UI (Tree vs. ASCII Graph side-by-side in Textual TUI, interactive Tree + markdown detail pane, ASCII/ANSI graph)
- R3: Dynamic Filtering (category/tag filter updating both components)
- Verification: `test_obsidian_parser.py` and `test_explorer_view.py` (Textual Pilot).
