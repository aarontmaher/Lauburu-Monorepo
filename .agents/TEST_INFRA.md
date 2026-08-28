# E2E Test Infra: Obsidian Architecture Explorer

## Test Philosophy
- Opaque-box, requirement-driven. Derives strictly from ORIGINAL_REQUEST.md (§R1, §R2, §R3, Acceptance Criteria).
- Methodology: Category-Partition (Tier 1) + Boundary Value Analysis (Tier 2) + Pairwise Combinatorial (Tier 3) + Real-World Workloads (Tier 4).
- Headless asynchronous testing using Textual Pilot (`App.run_test()`) and `pytest-asyncio`.

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------|:------:|:------:|:------:|:------:|
| F1 | Frontmatter Extraction | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F2 | Wikilink Resolution | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F3 | In-Memory Graph Indexing | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F4 | Vault Category Classifier | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F5 | ASCII Topological Layout | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F6 | ANSI Box-Drawing Renderer | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F7 | Dual-Layout View Mount | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F8 | Interactive Tree Widget | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F9 | Markdown Detail Pane | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F10 | Dynamic Search Input Bar | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F11 | Category Chip Toggles | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F12 | TUI Integration & Keybindings | Acceptance Criteria | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Unit Suite (`tests/unit/test_obsidian_parser.py`)**: Tests parser functionality on synthetic and mock markdown files, checking frontmatter extraction, wikilink parsing, bidirectional edges, and category classification.
- **Unit Suite (`tests/unit/test_ascii_graph_renderer.py`)**: Tests topological ranking, Tarjan SCC cycle isolation, diamond bus convergence, and ANSI box drawing.
- **E2E Pilot Suite (`tests/e2e/test_explorer_view.py`)**: Tests Textual Pilot interactions, verifying simultaneous side-by-side display of Tree and ASCII canvas, selection updates to Markdown detail, dynamic search typing, chip clicking, and terminal resize responsiveness.
- **Master 4-Tier Suite (`tests/e2e/test_explorer_4tier_suite.py`)**: Comprehensive 115-test battery verifying Tiers 1-4, performance benchmarks (<50ms for 100-node graph), zero memory leaks, and live vault crawl integrity.

## Coverage Thresholds
- Tier 1: ≥5 per feature (Total ≥ 60 tests)
- Tier 2: ≥5 per feature with boundary conditions (Total ≥ 35 tests)
- Tier 3: Pairwise coverage of interaction matrices (Total ≥ 20 tests)
- Tier 4: Live monorepo vault crawl & stress workloads (Total ≥ 10 tests)
- **Total Suite Target: ≥ 115 tests**
