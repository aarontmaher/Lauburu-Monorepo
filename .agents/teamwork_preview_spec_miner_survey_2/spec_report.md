# Authoritative Specification Report: Swarm Rule #0, Tri-Lens Visual Swarm & Figma MCP Zero-Mock Guardrail Harness

- **Author:** `teamwork_preview_spec_miner_survey_2`
- **Target File:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_spec_miner_survey_2/spec_report.md`
- **Timestamp:** 2026-08-26T02:26:00Z
- **Integrity Mode:** Strict Rule #0 Zero-Mock Specification Mining

---

## Executive Summary

This report establishes the authoritative specification, interface contracts, verification protocols, error handling behaviors, and edge cases for:
1. **Swarm Rule #0 Mandate:** Global zero-mock data integrity law, empirical proof verification (`Rule #0.1`), hardware grounding (`Rule #0.2`), automated truth remediation (`Rule #0.3`), and the exact structural layout vs. mock data discrimination rubric.
2. **Tri-Lens Visual Swarm Auditing Architecture:** Multi-engine visual verification across **Lens 1** (Chromium CDP), **Lens 2** (Gecko Marionette), and **Lens 3** (Native Android / OpenClaw / Shizuku / Local VLM), consensus auditor fleet, and 4-phase sequential click-through audit workflow.
3. **Figma MCP Registration, Authentication & Verification SOP / Harness:** Tool schemas (`get_file`, `get_file_nodes`, `get_image`, `get_comments`), registration in `~/.gemini/settings.json`, OAuth/PAT authentication protocols, design-to-code extraction pipelines, and automated zero-mock pre-merge blocking gates.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | **Rule #0 Truth Core** | Global Rule #0 Zero-Mock Mandate | Universal law strictly forbidding simulated, fake, or synthetic data across all UI and telemetry streams. Requires live hardware registers, authentic replays, or clean waiting states (`--`). | Application source code, telemetry streams, UI view components | Verified authentic telemetry, clean uninitialized states (`--`, `null`, spinner) | Instant failure, task rejection, and automated retraining loop trigger | System Prompt `RULE[user_global]`, `/Users/aaron/.gemini/config/skills/swarm/SKILL.md` (Sec 4.1) |
| 2 | **Rule #0 Verification** | Rule #0.1 Empirical Claim Verifier | Intercepts AI agent status claims, performs concurrent TCP socket probing across known system ports, verifies file byte sizes (`min_bytes >= 1`), and appends an immutable Empirical Proof Verification Table. | AI markdown text, system port map (`8265`, `8888`, `8087`, `8000`, `11434`, `5001`, `52415`, `18802`) | Annotated markdown output with verified/failed status rows, JSONL audit record | Annotates `UNPROVEN / FAILED ❌`, records failure in `claim_audit_history.jsonl` | `06_scripts_and_tooling/scripts/ai_claim_verifier.py`, `scripts/ai_claim_verifier.py` |
| 3 | **Rule #0 Hardware** | Rule #0.2 Silicon Register Grounding | Binds all compute/profiler telemetry directly to physical hardware registers (Apple Silicon Metal Performance Shaders, Tensor G5 TPU, Exynos NPU). | Hardware device handles, sysfs/GPU metrics | Empirical GEMM GFLOPs, bandwidth, memory headroom | Fallback to safe zero defaults (`0°`, `SAFE`, `null`) with error logging | `00_core_infrastructure/self_healing_hub/src/npu_vram_orchestrator_state.json`, `wgpu-rust-bridge/SKILL.md` |
| 4 | **Rule #0 Remediation** | Rule #0.3 Automated Truth Remediation | Automated diagnostic engine that attempts remediation of failed claims and computes a Gemini Spark Reward Score (0-100) and token allocation. | Failed claim text, error context dictionary | Remediation execution status, Spark score, reward points/tokens | If remediation fails, outputs failure diagnostics and escalates to human | `06_scripts_and_tooling/scripts/ai_claim_verifier.py` (lines 147-158) |
| 5 | **Tri-Lens Architecture** | Lens 1: Chromium CDP Inspector | Blink-based DOM inspection, CSS bounding box calculation, Accessibility Tree (AX Tree) snapshots (`take_snapshot`), UID element interactions (`click`, `fill`), and Lighthouse audits. | URL, pageId, script/selector payloads | DOM tree, AX tree with unique UIDs (`e-1`), base64 screenshots, Lighthouse scores | Returns structured error object (`isError: true`, message), non-zero exit code | `chrome-devtools-mcp` schema, `tests/e2e/test_tier4_real_world_scenarios.py` |
| 6 | **Tri-Lens Architecture** | Lens 2: Gecko Marionette Engine | Gecko layout engine verification, headless Mozilla Firefox via GeckoDriver / Marionette JSON-RPC (ports 4444/2828), cross-browser parity auditing over Tailscale. | URL, pageId, Marionette JSON-RPC 2.0 frames | Gecko AX tree with monotonic UIDs (`f-1`), base64 PNG snapshots, console logs | Spawns/reaps GeckoDriver cleanly; returns structured WebDriver error on failure | `survey_explorer_marionette_1/report.md`, `tests/e2e/mocks/mock_marionette_server.py` |
| 7 | **Tri-Lens Architecture** | Lens 3: Native Edge & Mobile Auditor | Android 15 (Pixel 10 Pro XL) and Android 14 (Samsung Galaxy S20+) mobile execution via Shizuku/ADB, capturing multi-frame rolling video streams. | ADB shell commands, Shizuku IPC, UI touch coordinates | 5 sequential frames (Cold Launch -> Nav -> Action -> Stream -> Notification) | Checks ADB connection state; triggers WoL / wake-lock retry on timeout | `05_agents_and_swarms/antigravity_skills/swarm/SKILL.md`, `survey_explorer_e2e_infra_1/report.md` |
| 8 | **Tri-Lens Verification** | Frame Delta Hash Verification | Multi-frame dynamic rendering validation computing MD5 hashes across 5 sequential frames to guarantee active rendering and eliminate static screen duplicates. | Array of 5 captured frame PNG byte arrays | Boolean verification (`len(set(MD5_hashes)) == 5`) | Fails audit if frame hashes are identical (detects frozen UI or static mock) | `swarm/SKILL.md` (Sec 4.3 Phase 2), `test_tier3_pairwise_combinatorial.py` |
| 9 | **Auditor Fleet** | Multi-Model Consensus Swarm | Tiered AI auditor fleet comprising Cloud AI (Gemini 3.7 Flash, Gemini 1.5 Pro, Claude 3.5 Sonnet, GPT-4o) and Local AI (`LocalVisionVLMAgent`, Qwen3-VL-32B, Llama-3.2-11B-Vision). | Visual screenshots, AX trees, source code diffs | Consensus audit verdict (`VERIFIED_EMPIRICAL` vs `DISQUALIFIED`), LoRA JSONL pairs | On disagreement, triggers AI Debate Protocol to reach ratified consensus | `swarm/SKILL.md` (Sec 4.2), `tests/e2e/mocks/mock_debate_orchestrators.py` |
| 10 | **Memory Ledger** | 24/7 LoRA Dataset Logging | Continuous serialization of verified system interactions, UI audits, and code corrections to master Google Drive memory ledger. | Structured instruction/input/output tuples, visual coordinates | Appended JSONL records in `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/` | Fallbacks to local NVMe `/Volumes/Lauburu-Monorepo/lora_datasets/` if Google Drive offline | `swarm/SKILL.md` (Sec 4.3 Phase 4, Sec 5.1), `scripts/adb_gemma_terminal_chat.py` |
| 11 | **Figma MCP Core** | Figma MCP Server Registration | Registration of official `@modelcontextprotocol/server-figma` or remote endpoint `https://mcp.figma.com/mcp` into `~/.gemini/settings.json` under `mcpServers`. | MCP server configuration JSON, command/args, environment variables | Active MCP stdio / SSE transport bridge | Stdio validation error, unrecognized binary error, or connection refusal | `~/.gemini/settings.json`, Official Figma MCP Protocol Specification |
| 12 | **Figma MCP Auth** | Figma OAuth & PAT Authentication | Authentication via browser-based OAuth flow (Cloud Code authorization URL) or Personal Access Token (`FIGMA_ACCESS_TOKEN` / `figd_*`). | Client ID / Secret or Personal Access Token | Authenticated session token, authorized API access to Figma REST endpoints | Returns HTTP 401 Unauthorized / Token Expired; triggers token refresh / re-auth prompt | Official Figma Developer Platform API Specification |
| 13 | **Figma MCP Tools** | `get_file` Document Retrieval | Fetches high-level document metadata, page hierarchy, canvas nodes, and top-level component sets from a Figma file. | `file_key: string`, `depth?: number` | JSON document AST (`DOCUMENT`, `CANVAS`, `FRAME`, `COMPONENT_SET`) | HTTP 404 Not Found (invalid file key) or HTTP 403 Forbidden | `@modelcontextprotocol/server-figma`, Figma REST API `/v1/files/:key` |
| 14 | **Figma MCP Tools** | `get_file_nodes` Granular AST Node Inspection | Retrieves detailed properties of specific nodes (geometry, AutoLayout flex attributes, padding, fills, typography, constraints). | `file_key: string`, `ids: string[]`, `depth?: number` | Granular node property dictionary (`layoutMode`, `itemSpacing`, `paddingLeft`, `fills`) | Returns empty nodes dict if node ID is invalid | `@modelcontextprotocol/server-figma`, Figma REST API `/v1/files/:key/nodes` |
| 15 | **Figma MCP Tools** | `get_image` Node Vector/Raster Rendering | Renders specified Figma nodes into downloadable image URLs or SVG vector markup for visual ground-truth comparison. | `file_key: string`, `ids: string[]`, `format: 'png'|'svg'|'pdf'`, `scale?: number` | Image URL map (`{ [node_id]: "https://..." }`) | HTTP 400 Bad Request or image render timeout | `@modelcontextprotocol/server-figma`, Figma REST API `/v1/images/:key` |
| 16 | **Figma MCP Tools** | `get_comments` Spec & Annotation Fetching | Retrieves designer comments, annotations, review threads, and component usage specifications. | `file_key: string` | Array of comment objects (`{ id, message, user, created_at, client_meta }`) | HTTP 404 Not Found or empty array | `@modelcontextprotocol/server-figma`, Figma REST API `/v1/files/:key/comments` |
| 17 | **Design-to-Code Gate** | Zero-Mock AST & Regex Pre-Merge Linter | Static analysis tool that parses generated UI code (JSX, TSX, Flutter Dart, Vue) and detects forbidden mock data patterns while allowing pure structural layout. | Generated source code file path / AST | Linter verdict (`PASS_ZERO_MOCK` vs `REJECT_MOCK_DETECTED`), line-numbered error list | Non-zero exit code (1), blocks git commit/merge, outputs remediation diff | Rule #0 Specification, Monorepo Zero-Mock Audit Engine |
| 18 | **Design-to-Code Gate** | Tri-Lens Visual Parity Diffing | Renders generated component in headless browser testbed (Lens 1/2) and compares against Figma `get_image` reference rendering using SSIM / pixel-diff. | Rendered component URL/snapshot, Figma reference image | Visual similarity score (SSIM $\ge 0.95$), visual diff mask PNG | Fails if SSIM < 0.95 or significant layout bounding box displacement detected | `tests/e2e/test_tier4_real_world_scenarios.py`, `survey_explorer_marionette_1` |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Rule #0 Linter | Component contains clean waiting state `{data?.heartRate ?? '--'}` | **ALLOWED (PASS)**: Evaluated as valid fallback uninitialized placeholder, NOT static mock data. |
| 2 | Rule #0 Linter | Component contains hardcoded string `<span>142 bpm</span>` | **REJECTED (FAIL)**: Flagged as hardcoded mock data masquerading as live telemetry. Blocks merge. |
| 3 | Rule #0 Linter | Component contains hardcoded array `const mockData = [{ id: 1, name: 'Alice' }]` | **REJECTED (FAIL)**: Flagged as forbidden mock dataset. Merge rejected with exit code 1. |
| 4 | Rule #0 Linter | Component contains static UI labels (e.g. `<h2>Hardware Diagnostics</h2>`) | **ALLOWED (PASS)**: Identified as structural layout / static chrome header, permissible under Rule #0. |
| 5 | Rule #0 Linter | Synthetic `setTimeout` simulation in button handler (`setTimeout(() => setDone(true), 1500)`) | **REJECTED (FAIL)**: Flagged as synthetic simulation. Requires actual backend API call or WebSocket dispatch. |
| 6 | Figma MCP Registration | Malformed JSON in `~/.gemini/settings.json` | MCP client fails during startup; logs JSON parse error; other MCP servers fail to load. Graceful recovery requires atomic file rewrite with schema validation. |
| 7 | Figma MCP Auth | Expired or revoked `FIGMA_ACCESS_TOKEN` | MCP server returns `HTTP 401 Unauthorized`. Harness catches error, outputs clear authentication prompt, and suppresses recursive retry storms. |
| 8 | Figma MCP `get_file_nodes` | Invalid or deleted `node_id` requested | Figma API returns `{"nodes": {}}` without throwing exception. Harness asserts `node_id in response['nodes']` before proceeding to AST extraction. |
| 9 | Tri-Lens Visual Parity | Web page has non-deterministic CSS animations (pulsing glow, marquee) | MD5 frame delta succeeds, but static visual screenshot diff fluctuates. Parity diff harness must disable CSS animations via `@media (prefers-reduced-motion)` or freeze CSS clock before frame capture. |
| 10 | Marionette Headless | GeckoDriver process crashes during `take_snapshot` | `marionette-mcp` detects broken stdio pipe, terminates lingering Firefox child processes, returns structured error JSON-RPC, and auto-restarts GeckoDriver on next call. |
| 11 | Shizuku Android Edge | Device screen locks during long test run | Android CPU enters Doze mode, dropping ADB TCP/IP connection. Harness issues `termux-wake-lock` and executes Wake-on-LAN / USB ADB wakeup before test invocation. |
| 12 | Figma Design Tokens | Figma file uses unbounded text frames or missing AutoLayout | Node extraction yields absolute x/y coordinates rather than flex attributes. Generator emits warning and falls back to responsive CSS grid layout rather than absolute positioning. |

---

## 1. Swarm Rule #0: Comprehensive Specification & Integrity Rubric

### 1.1 The Fundamental Law
Global Rule #0 ("CRITICAL TRUTH & VERIFICATION RULES") is the foundational operating law across the Lauburu Monorepo and all Swarm agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SWARM RULE #0 HIERARCHY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Zero Fake Data: Never use simulated, randomized, or mock arrays.        │
│ 2. Zero Hallucinations: 100% of claims must be truth-audited.               │
│ 3. Verification First: Never claim completion until verified by live run.  │
│ 4. End-to-End Visual Audit: UI must pass multi-frame sequential validation. │
│ 5. Punishment Protocol: Violations trigger immediate retraining loops.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Rule #0 Sub-Rules in Codebase & Tooling
1. **Rule #0.1 — Empirical Proof Mandate (`ai_claim_verifier.py`)**:
   - Every AI response claiming system status (`online`, `running`, `completed`, `active`, `port`) is automatically parsed.
   - Sockets are tested in real time (`connect_ex == 0`).
   - File byte counts are verified (`os.path.getsize(f) >= min_bytes`).
   - An immutable Markdown proof block is appended to the output.
2. **Rule #0.2 — Silicon Register Grounding**:
   - Hardware telemetry (VRAM, GPU compute passes, NPU TOPS, ECG sample rates) must query kernel sysfs or Metal/Vulkan/PyTorch device properties directly.
   - Synthetic profilers (e.g. returning hardcoded `"149.8 GFLOPs"`) are classified as critical integrity violations.
3. **Rule #0.3 — Automated Truth Remediation & Gemini Spark Reward**:
   - Failed claims trigger automated Docker/daemon remediation.
   - Gemini Spark evaluation calculates integrity score (0-100) and awards or penalizes training tokens.

### 1.3 Structural Layout vs. Mock Data Discrimination Rubric

To enable automated CI/CD and pre-merge linter enforcement, the boundary between acceptable structural layouts and blocked mock data is formally defined:

```
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│        PERMISSIBLE STRUCTURAL LAYOUT         │          STRICTLY FORBIDDEN MOCK DATA        │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ • HTML/JSX DOM hierarchy & container tags    │ • Hardcoded string literals in data fields   │
│   (<div className="metric-card">)            │   (<span>120 bpm</span>, <p>John Doe</p>)    │
│ • Flexbox / Grid layout definitions          │ • Hardcoded arrays/objects in source         │
│   (display: 'flex', gap: '1rem')             │   (const users = [{ name: 'Test' }])         │
│ • Design tokens & theme variables            │ • Synthetic client-side simulation timers    │
│   (color: 'var(--text-primary)', #0f172a)    │   (setTimeout(() => setDone(true), 1500))    │
│ • Dynamic state & prop bindings              │ • Hardcoded profiler / benchmark results     │
│   ({device.vram ?? '--'}, {props.status})    │   (gemmGflops: '149.8 GFLOPs' as literal)    │
│ • Clean fallback / waiting state indicators  │ • Fabricated mock API response fixtures in   │
│   ('--', 'N/A', loading spinners, skeletons) │   production components                      │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 2. Tri-Lens Visual Swarm: Architecture, Protocols & Acceptance Criteria

### 2.1 Multi-Engine Tri-Lens Architecture

```
                               ┌─────────────────────────────┐
                               │  Swarm Truth Auditor Fleet  │
                               │ (Gemini 3.7 Flash + Qwen3)  │
                               └──────────────┬──────────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              ▼                               ▼                               ▼
     ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
     │     LENS 1      │             │     LENS 2      │             │     LENS 3      │
     │  Chromium CDP   │             │Gecko Marionette │             │Native Mobile/ADB│
     ├─────────────────┤             ├─────────────────┤             ├─────────────────┤
     │ • Blink engine  │             │ • Gecko engine  │             │ • Android 14/15 │
     │ • DevTools MCP  │             │ • Firefox head- │             │ • Shizuku root- │
     │ • AX Tree `e-*` │             │   less stdio    │             │   less execution│
     │ • Lighthouse    │             │ • AX Tree `f-*` │             │ • OpenClaw VLM  │
     │ • WCAG 2.1 AA   │             │ • Cross-browser │             │ • Multi-frame   │
     │ • Network timing│             │   parity diff   │             │   video buffer  │
     └─────────────────┘             └─────────────────┘             └─────────────────┘
```

### 2.2 The 4-Phase Audit Workflow
1. **Phase 1: Feature Intent Comprehension**:
   - Reads prompt, Figma design specs, interface contracts, and target endpoints.
   - Defines concrete success criteria: "Component must render responsive flex layout, bind live telemetry, and display `--` when uninitialized."
2. **Phase 2: OpenClaw Multi-Frame Sequential Click-Through**:
   - Executes 5 sequential states: Cold Launch $\rightarrow$ Navigation $\rightarrow$ Action Click $\rightarrow$ Data Streaming $\rightarrow$ System Notification.
   - Computes MD5 hash of each frame: $\text{len}(\text{unique}(\text{hashes})) == 5$. Fails if static screen duplicate detected.
3. **Phase 3: Zero-Tolerance Truth & Accuracy Analysis**:
   - Verifies data origin (live WebSockets, REST APIs, or local ledgers).
   - Scans AST for zero mock arrays.
   - Triple-Vision consensus: Gemini 3.7 Flash + Qwen3-VL-32B + Llama-3.2-11B-Vision.
4. **Phase 4: LoRA Training Handoff & Memory Ledger**:
   - Serializes verified diffs and UI coordinates to `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/ui_ux_improvements.jsonl`.
   - Continuous 24/7 background mesh fine-tuning.

---

## 3. Figma MCP Verification SOP & Harness Specification

### 3.1 Figma MCP Registration Protocol

#### Configuration in `~/.gemini/settings.json`
```json
{
  "mcpServers": {
    "figma": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-figma"
      ],
      "env": {
        "FIGMA_ACCESS_TOKEN": "${FIGMA_ACCESS_TOKEN}"
      },
      "trust": true,
      "description": "Figma Model Context Protocol server for extracting design tokens, layer trees, and component ASTs."
    }
  }
}
```

#### Remote HTTP / SSE Alternative
```json
{
  "mcpServers": {
    "figma-remote": {
      "url": "https://mcp.figma.com/mcp",
      "trust": true,
      "description": "Official Figma Remote MCP endpoint with OAuth browser authentication."
    }
  }
}
```

### 3.2 Authentication Flows
1. **Method 1: OAuth 2.0 Browser Cloud Code**:
   - MCP client triggers authorization URL: `https://www.figma.com/oauth?client_id=...&scope=file_read&response_type=code`.
   - Agent displays terminal authentication link; user authorizes in browser.
   - Local callback listener captures authorization code and exchanges for Bearer token.
2. **Method 2: Personal Access Token (PAT)**:
   - User generates token in Figma: Settings $\rightarrow$ Security $\rightarrow$ Personal Access Tokens (`figd_*`).
   - Token is injected into `FIGMA_ACCESS_TOKEN` environment variable.

### 3.3 Figma MCP Tool Catalog & Schemas

```
┌──────────────────┬──────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Tool Name        │ Input Schema                             │ Output Schema                                          │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_file         │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "name": string,                                      │
│                  │   "depth"?: number                       │   "document": { "id": "0:0", "type": "DOCUMENT", ... },│
│                  │ }                                        │   "components": { ... }, "schemaVersion": 0            │
│                  │                                          │ }                                                      │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_file_nodes   │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "nodes": {                                           │
│                  │   "ids": string[],                       │     "<node_id>": {                                     │
│                  │   "depth"?: number                       │       "document": { "type": "FRAME", ... },            │
│                  │ }                                        │       "components": { ... }                            │
│                  │                                          │     }                                                  │
│                  │                                          │   }                                                    │
│                  │                                          │ }                                                      │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_image        │ {                                        │ {                                                      │
│                  │   "file_key": string,                    │   "err": null,                                         │
│                  │   "ids": string[],                       │   "images": { "<node_id>": "https://figma-alpha..." }  │
│                  │   "format"?: "png"|"svg"|"pdf",          │ }                                                      │
│                  │   "scale"?: number                       │                                                        │
│                  │ }                                        │                                                        │
├──────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ get_comments     │ {                                        │ {                                                      │
│                  │   "file_key": string                     │   "comments": [                                        │
│                  │ }                                        │     { "id": "1", "message": "...", "user": { ... } }   │
│                  │                                          │   ]                                                    │
│                  │                                          │ }                                                      │
└──────────────────┴──────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

### 3.4 Automated Zero-Mock Verification Harness Architecture

The verification harness operates as a 5-stage automated gate:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FIGMA ZERO-MOCK VERIFICATION HARNESS                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Stage 1: MCP Server Handshake & Health Check                             │
│    • Validate JSON-RPC 2.0 handshake (`tools/list`).                        │
│    • Test connectivity by invoking `get_file` on test canvas.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Stage 2: Layer AST & Design Token Extraction                             │
│    • Extract layout structure (`layoutMode`, `padding`, `itemSpacing`).     │
│    • Extract color tokens, typography scales, border radii.                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Stage 3: Zero-Mock AST Code Generation                                   │
│    • Map AutoLayout to clean CSS Flexbox / Tailwind / Flutter widgets.      │
│    • Generate dynamic prop interfaces with `{prop ?? '--'}` fallbacks.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Stage 4: Rule #0 Pre-Merge AST Linter Guardrail (BLOCKING GATE)          │
│    • Scan code AST for static data strings, mock arrays, simulated timers.  │
│    • If mock data detected -> ABORT & EXIT CODE 1 (Merge Blocked).          │
│    • If only structural layout + dynamic props -> PASS & EXIT CODE 0.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. Stage 5: Tri-Lens Visual Parity Verification                             │
│    • Render generated code in Lens 1 (Chromium) and Lens 2 (Firefox).       │
│    • Compare rendered snapshot with Figma `get_image` reference (SSIM>=0.95)│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Verification Method

To verify the specifications and tool mappings documented in this report:

1. **Verify Existing Rule #0.1 Verifier**:
   ```bash
   python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/scripts/ai_claim_verifier.py
   ```
2. **Verify Swarm Truth Audit Specification**:
   ```bash
   view_file /Users/aaron/.gemini/config/skills/swarm/SKILL.md (lines 236-320)
   ```
3. **Verify Tri-Lens Marionette MCP Survey**:
   ```bash
   view_file /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/report.md
   ```
4. **Verify E2E Tri-Lens Scenario Test**:
   ```bash
   python3 -m unittest /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/tests/e2e/test_tier4_real_world_scenarios.py
   ```
5. **Verify Figma MCP Package Availability**:
   ```bash
   npx -y @modelcontextprotocol/server-figma --help 2>&1 | head -n 10
   ```

---
*Report certified by `teamwork_preview_spec_miner_survey_2` under Rule #0 Data Authenticity Protocol.*
