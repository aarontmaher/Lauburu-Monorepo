# Scope: Figma MCP Integration & Rule #0 Zero-Mock Guardrails

## Architecture
This project establishes the official Figma Model Context Protocol (MCP) server integration and enforces the Monorepo Rule #0 Zero-Mock Pre-Merge Guardrail across all design-to-code pipelines.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             FIGMA MCP CLIENT                                │
│                (~/.gemini/settings.json / REST / OAuth)                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FIGMA DESIGN-TO-CODE PIPELINE                            │
│  • Layer AST Extraction (get_file, get_file_nodes, get_image)               │
│  • AutoLayout -> CSS Flexbox / Tailwind / Flutter Widget Mapping            │
│  • Dynamic Prop & Uninitialized Waiting State Generator                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               RULE #0 ZERO-MOCK PRE-MERGE BLOCKING GATE                     │
│  • AST & Regex Linter (blocks hardcoded mock arrays, fake data strings)     │
│  • Tri-Lens Visual Swarm Validator (Lens 1 CDP / Lens 2 Firefox Marionette) │
│  • Mandatory Exit Code 1 on mock data, Exit Code 0 on pure structural layout│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Figma MCP Registration | Register `@modelcontextprotocol/server-figma` in `~/.gemini/settings.json` with stdio/env configuration | M1 | USER_REQUEST §R1 |
| 2 | Figma Auth & Token Handler | OAuth browser Cloud Code auth flow & Personal Access Token (`FIGMA_ACCESS_TOKEN`) management | M1 | USER_REQUEST §R1 |
| 3 | Figma MCP Connection Verifier | Verification script/tool to test `get_file`, `get_file_nodes`, `get_image` API connectivity | M1 | USER_REQUEST §R1 |
| 4 | Rule #0 Zero-Mock AST Linter | Pre-merge static analysis tool detecting static placeholder data vs pure structural layout | M2 | USER_REQUEST §R2 |
| 5 | Design-to-Code Generator | Translates Figma AST nodes to React/TSX/Flutter with dynamic props and `--` uninitialized states | M2 | spec_report §3.4 |
| 6 | Tri-Lens Visual Parity SOP | Standard Operating Procedure & verification script enforcing multi-frame visual and AST audits | M2 | USER_REQUEST §R2 |
| 7 | Multi-Tier E2E Test Suite | 4-tier test harness covering feature tests, boundary conditions, combinatorial pairs, and real scenarios | M3 | USER_REQUEST §R3 |
| 8 | Forensic Integrity Audit | Independent forensic verification guaranteeing zero mock data and genuine MCP connectivity | M3 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Figma MCP Server Registration & Authentication Setup | `06_scripts_and_tooling/scripts/setup_figma_mcp.py`, `06_scripts_and_tooling/scripts/figma_mcp_client.py`, `~/.gemini/settings.json` registration & live auth verification | none | IN_PROGRESS |
| M2 | Rule #0 Zero-Mock Guardrail SOP & Tri-Lens Audit Harness | `06_scripts_and_tooling/scripts/figma_zero_mock_linter.py`, `06_scripts_and_tooling/scripts/figma_tri_lens_auditor.py`, `06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md` | M1 | PLANNED |
| M3 | E2E Dual-Track Test Suite & Live Verification | `tests/test_figma_mcp_zero_mock.py` 4-tier live test harness, empirical execution & Forensic Audit | M1, M2 | PLANNED |

## Interface Contracts

### `FigmaMCPClient` ↔ `FigmaREST/MCP`
- `get_file(file_key: str, depth: int = 2) -> dict`
- `get_file_nodes(file_key: str, node_ids: list[str]) -> dict`
- `get_image(file_key: str, node_ids: list[str], format: str = "png") -> dict`
- `get_comments(file_key: str) -> list[dict]`

### `ZeroMockLinter` ↔ `GitPreMerge/CI`
- `lint_ui_source(file_path: str) -> tuple[bool, list[str]]`
  - Returns `(True, [])` for pure structural layouts, design tokens, dynamic state bindings, and `{val ?? '--'}`
  - Returns `(False, ["Mock array detected at line X", "Hardcoded string in data field at line Y"])` for mock/fake data
- CLI exit code: `0` for PASS, `1` for FAIL (blocks merge)

### `TriLensAuditor` ↔ `VisualSwarm`
- Evaluates 5-frame MD5 hash delta
- Asserts zero static mock data in DOM/AX Tree
- Computes structural parity SSIM $\ge 0.95$

## Code Layout
- `06_scripts_and_tooling/scripts/setup_figma_mcp.py` — Figma MCP registration & auth configuration CLI
- `06_scripts_and_tooling/scripts/figma_mcp_client.py` — Figma MCP protocol client & API probe
- `06_scripts_and_tooling/scripts/figma_zero_mock_linter.py` — Rule #0 Zero-Mock pre-merge AST linter
- `06_scripts_and_tooling/scripts/figma_tri_lens_auditor.py` — Tri-Lens Visual Swarm audit harness
- `06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md` — Authoritative SOP documentation
- `tests/test_figma_mcp_zero_mock.py` — 4-tier comprehensive E2E test suite
