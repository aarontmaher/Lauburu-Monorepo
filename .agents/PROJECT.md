# Project: Obsidian Architecture Explorer in Canonical Port TUI

## Architecture
The Obsidian Architecture Explorer is an interactive, dual-layout visualization tool integrated directly into the Canonical Port Textual TUI (`01_apps/canonical_port`). It reads markdown documents from `obsidian_vault/`, extracts metadata/frontmatter and Obsidian Wikilinks (`[[...]]`), constructs an in-memory directed dependency graph, and displays the architecture through two simultaneous, side-by-side rendering strategies:
1. **Interactive Textual `Tree` Widget + Markdown Detail Pane** (Left 48% width): Collapsible hierarchy organized by category and node, displaying node details, tags, and features upon selection.
2. **Deterministic ASCII/ANSI Node-and-Edge Graph Canvas** (Right 52% width): Topological stratified DAG with Tarjan SCC cycle isolation, barycentric crossing reduction, and Unicode box-drawing connectors (`╭─╮`, `──▶`, `├──┴──▶`).
3. **Dynamic Filtering Engine**: Interactive search input and 10 category chip button toggles (`#chip-all` through `#chip-audit`) that filter nodes in real time, synchronizing both the Tree and ASCII canvas simultaneously.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CANONICAL PORT TUI                              │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ArchitectureExplorerScreen / ArchitectureExplorerView                   │ │
│ │                                                                         │ │
│ │ ┌───────────────────────────────┐ ┌───────────────────────────────────┐ │ │
│ │ │ Left Pane: Tree & Detail      │ │ Right Pane: ASCII/ANSI Graph      │ │ │
│ │ │ - Search & 10 Category Chips  │ │ - Topological DAG Canvas          │ │ │
│ │ │ - Textual Tree Widget         │ │ - Tarjan SCC Cycle Annotations    │ │ │
│ │ │ - Markdown Feature Detail     │ │ - Synchronized Highlight          │ │ │
│ │ └───────────────────────────────┘ └───────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                               ▲                                             │
│                               │ Queries & Filtered Subgraphs                │
│ ┌─────────────────────────────┴───────────────────────────────────────────┐ │
│ │ ArchitectureGraph & ObsidianVaultParser Service                          │ │
│ │ - Reads /obsidian_vault/*.md                                            │ │
│ │ - YAML Frontmatter & Wikilink [[...]] Parsing                           │ │
│ │ - In-Memory Adjacency Index (51 Nodes, 197 Edges, 9 Categories)         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
Every feature from the survey and user requirements is listed below:

| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| F1 | Obsidian YAML Frontmatter Parser | Parses YAML headers (`title`, `tags`, `category`, `updated`) with robust regex fallback for missing delimiters | M1 | DONE |
| F2 | Wikilink Dependency Extractor | Extracts standard `[[Node]]`, aliased `[[Node\|Alias]]`, anchored `[[Node#Sec]]`, and subfolder `[[00_Overview/Node]]` links | M1 | DONE |
| F3 | In-Memory Architecture Graph Model | Dataclass models (`VaultNode`, `VaultFeature`, `ArchitectureGraph`) indexing directed edges, in/out degrees, and dangling links | M1 | DONE |
| F4 | Vault Category Classifier | Deterministic classification into 9 canonical categories (Canonical Module, Infrastructure, Debate, Audit, etc.) | M1 | DONE |
| F5 | ASCII/ANSI Topological Graph Layout Engine | Sugiyama layered layout with Tarjan SCC cycle breaking and barycentric crossing reduction | M2 | DONE |
| F6 | Unicode Box-Drawing Graph Renderer | Renders styled nodes, directional arrows (`──▶`), multi-parent converging buses, and ANSI category color palettes | M2 | DONE |
| F7 | Dual-Layout Textual Split Container | Side-by-side split (`Horizontal`) containing Tree + Detail on left and ASCII Canvas on right | M2 | DONE |
| F8 | Interactive Textual Tree Widget | Hierarchical tree organized by category, populated with nodes and dependency sub-branches | M2 | DONE |
| F9 | Markdown Feature Detail Pane | Textual `Markdown` widget displaying selected node's title, category, tags, and extracted features list | M2 | DONE |
| F10 | Dynamic Search Input Bar | Real-time text search filtering nodes by title, stem, or feature text across Tree and ASCII graph | M3 | DONE |
| F11 | Category Filter Chip Toggles | Clickable button chips (`[All]`, `[Apps]`, `[Core]`, `[AI]`, `[Bio]`, `[Gov]`, etc.) updating both views instantly | M3 | DONE |
| F12 | TUI Screen Navigation & Keybinding Integration | Registration in `CanonicalPortApp` (`canonical_tui.py`), PinnedTabNavBar item, keybinding `'e'`/`'x'` | M3 | DONE |
| F13 | Programmatic Parser Verification Suite | `test_obsidian_parser.py` testing YAML frontmatter, wikilinks, graph queries, and boundary cases | M4 (E2E) | DONE |
| F14 | Textual Pilot E2E UI Test Suite | `test_explorer_view.py` testing dual-layout mount, side-by-side rendering, filter synchronization, and interaction | M4 (E2E) | DONE |
| F15 | 4-Tier Master Acceptance & Stress Test Suite | `test_explorer_4tier_suite.py` covering 115+ assertions (Tiers 1-4, performance < 50ms, zero leaks) | M4 (E2E) | DONE |

## Milestones

| # | Name | Scope | Dependencies | Status | Output Artifacts |
|---|------|-------|-------------|--------|------------------|
| E2E | E2E Testing Track | Test infrastructure, `test_obsidian_parser.py`, `test_explorer_view.py`, `test_explorer_4tier_suite.py`, `TEST_READY.md` | none | DONE | `TEST_READY.md` (117 tests passing) |
| M1 | Obsidian Vault Parser & Graph Engine | `tui/models/architecture_graph.py`, `tui/services/obsidian_vault_parser.py` | none | DONE | 51 live nodes, 197 directed edges indexed |
| M2 | Dual-Layout View & ASCII Graph Engine | `tui/services/ascii_graph_renderer.py`, `tui/views/architecture_explorer_view.py` | M1 | DONE | Sugiyama layout, Tarjan cycle annotations, ANSI canvas |
| M3 | Dynamic Filtering & TUI Integration | `tui/screens/architecture_explorer_screen.py`, `tui/canonical_tui.py` screen & nav integration | M2 | DONE | Screen ID `"explorer"`, keys `'e'`/`'x'`, 10 category chips |
| M4 | Final Gate Review & Hardening | Full multi-review, adversarial stress test, and forensic integrity audit | E2E, M3 | DONE | **Gate Result: PASS** (Reviewer 1 APPROVE, Reviewer 2 APPROVE, Challenger 1 APPROVE, Challenger 2 APPROVE, Auditor CLEAN) |

## Interface Contracts

### `ArchitectureGraph` ↔ `ObsidianVaultParser`
```python
class ObsidianVaultParser:
    def __init__(self, vault_path: Optional[Path] = None) -> None: ...
    def parse_vault(self) -> ArchitectureGraph: ...
    def parse_file(self, file_path: Path) -> VaultNode: ...
    def extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]: ...
    def extract_wikilinks(self, text: str) -> List[WikilinkRef]: ...
    def extract_features(self, text: str) -> List[VaultFeature]: ...
```

### `ArchitectureGraph` ↔ `AsciiGraphRenderer`
```python
class AsciiGraphRenderer:
    def __init__(self, graph: ArchitectureGraph) -> None: ...
    def render_ansi(self, filtered_nodes: Optional[Set[str]] = None, selected_node: Optional[str] = None, max_width: int = 120) -> str: ...
    def detect_cycles(self, node_ids: Set[str]) -> List[Tuple[str, str]]: ...
```

### `ArchitectureExplorerView` ↔ `CanonicalPortApp`
```python
class ArchitectureExplorerView(Vertical):
    def __init__(self, vault_path: Optional[Path] = None, **kwargs) -> None: ...
    def apply_filter(self, category: Optional[str] = None, query: str = "") -> None: ...
    def select_node(self, node_id: str) -> None: ...

class ArchitectureExplorerScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("slash", "focus_filter", "Search"),
        Binding("r", "refresh_vault", "Refresh"),
    ]
```

## Code Layout

```
01_apps/canonical_port/
├── tui/
│   ├── models/
│   │   └── architecture_graph.py       # Data models (VaultNode, VaultFeature, ArchitectureGraph)
│   ├── services/
│   │   ├── obsidian_vault_parser.py    # Vault parser & link resolver
│   │   └── ascii_graph_renderer.py     # Topological DAG layout & ANSI canvas renderer
│   ├── views/
│   │   └── architecture_explorer_view.py # Dual-layout view (Tree + Detail vs ASCII Canvas)
│   ├── screens/
│   │   └── architecture_explorer_screen.py # Screen wrapper for TUI
│   └── canonical_tui.py                # Main TUI app entrypoint (screen registration & tab nav)
└── tests/
    ├── unit/
    │   ├── test_obsidian_parser.py     # Unit test suite for parser & graph engine (28 tests)
    │   └── test_ascii_graph_renderer.py # Unit test suite for layout & box drawing (12 tests)
    └── e2e/
        ├── test_explorer_view.py       # Textual Pilot E2E test suite (9 tests)
        ├── test_explorer_4tier_suite.py # 4-Tier master acceptance test suite (68 tests)
        ├── test_adversarial_challenger_1.py # Fuzzing & boundary stress tests (47 tests)
        └── test_challenger_2_ui_dom_adversarial.py # UI/DOM conformance tests (45 tests)
```
