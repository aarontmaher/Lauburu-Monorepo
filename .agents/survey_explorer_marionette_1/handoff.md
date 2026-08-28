# Handoff Report: `marionette-mcp` Technical Survey & Architecture Design

## 1. Observation
- **Authoritative Dispatch & Request**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md` (Lines 81-83, 92-94) specifies:
  > "Develop a Node.js stdio MCP server (`marionette-mcp`) that utilizes GeckoDriver to control a headless Firefox instance. It must expose MCP tools (e.g., `navigate`, `screenshot`, `get_ax_tree`) that match the `chrome-devtools-mcp` API to enable the Tri-Lens visual audit architecture over Tailscale."
  > "Acceptance Criteria: A programmatic test verifies the `marionette-mcp` server can successfully launch Firefox, navigate to a local URL, and return a valid base64 screenshot via an MCP tool call."
- **Host Runtime Environment**:
  - `node -v` returned `v20.20.2`.
  - `npm -v` returned `10.8.2`.
  - `uname -a` confirmed `Darwin Aarons-Mac-mini.local 25.6.0 arm64`.
  - Homebrew is operational at `/Users/aaron/.local/bin/brew` (`Homebrew 6.0.19`).
- **Chrome DevTools MCP Inspection**:
  - Directory `/Users/aaron/.gemini/antigravity/mcp/chrome-devtools-mcp` contains 29 `.json` tool schemas:
    `navigate_page`, `take_screenshot`, `take_snapshot`, `click`, `fill`, `fill_form`, `evaluate_script`, `wait_for`, `hover`, `drag`, `press_key`, `type_text`, `new_page`, `close_page`, `list_pages`, `select_page`, `resize_page`, `handle_dialog`, `upload_file`, `list_console_messages`, `get_console_message`, `list_network_requests`, `get_network_request`, `emulate`, `take_heapsnapshot`, `lighthouse_audit`, `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`.
- **Ecosystem MCP Configurations**:
  - `~/.gemini/settings.json` contains active stdio MCP servers (`browser-use`, `computer-use`, `docker`, `obsidian`, `cloudflare`, `antigravity-models`).
  - Production MCP servers in Node.js utilize `@modelcontextprotocol/sdk` (version `^1.12.0` / `1.30.0`) with `McpServer` and `StdioServerTransport`.
- **Driver & Binary Availability**:
  - `geckodriver` is available as Homebrew formula 0.37.1 and as npm package `geckodriver` (v6.1.1) for automated cross-platform binary acquisition.
  - Firefox is installable via `brew install --cask firefox` (v154.0.1) or standard macOS application path `/Applications/Firefox.app/Contents/MacOS/firefox`.

## 2. Logic Chain
1. **Tri-Lens Architecture Role**: Lens 1 is Chromium CDP (`chrome-devtools-mcp` / `browser-use`). Lens 2 is Firefox Gecko (`marionette-mcp`). Lens 3 is Mobile Native (OpenClaw / Shizuku / scrcpy). To enable seamless drop-in switching for LLM agents without prompting modifications, `marionette-mcp` must implement 1-to-1 schema matching with `chrome-devtools-mcp`.
2. **Transport & Protocol Choice**: `@modelcontextprotocol/sdk` (`McpServer` + `StdioServerTransport`) provides standard JSON-RPC 2.0 framing over `process.stdin`/`stdout`. Keeping `process.stdout` strictly reserved for MCP JSON-RPC frames while redirecting all logging to `process.stderr` prevents framing corruption.
3. **Driver Supervision & Automation**: Wrapping `geckodriver` through `selenium-webdriver` and `geckodriver` npm package guarantees that the MCP server can start the driver on a dynamic ephemeral port, configure headless Firefox with `-headless -no-remote --width=1920 --height=1080`, and clean up all child processes upon exit, ensuring zero zombie PID leaks.
4. **Accessibility Tree & UID Serialization**: Implementing an injected JavaScript DOM traversal script during `take_snapshot` allows `marionette-mcp` to generate an indented ARIA accessibility tree with monotonic `uid` markers (`f-1`, `f-2`...), caching element references so that downstream `click({ uid })` and `fill({ uid, value })` calls execute deterministically.
5. **Monorepo Cohesion**: Placing `marionette-mcp` at `00_core_infrastructure/mcp_servers/marionette-mcp` adheres to project layout rules, keeping shared mesh infrastructure organized under `00_core_infrastructure`.

## 3. Caveats
- **Firefox Binary Prerequisite**: If Firefox is not pre-installed on the host or runner environment, `marionette-mcp` will throw an error upon session startup. The server code should detect missing binaries and provide clear instructions (`brew install --cask firefox`).
- **Lighthouse Tool Parity**: Chrome DevTools MCP runs native Chrome Lighthouse. In Firefox, accessibility audits in `lighthouse_audit` will run an embedded `axe-core` WCAG 2.1 AA evaluation engine to return equivalent accessibility issue lists and scores.

## 4. Conclusion
The technical architecture, dependency set, tool schema mappings, and monorepo structure for `marionette-mcp` are completely established and ready for implementation.
- **Output Report Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/report.md`
- **Target Monorepo Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/mcp_servers/marionette-mcp`
- **Primary Dependencies**: `@modelcontextprotocol/sdk`, `selenium-webdriver`, `geckodriver`, `zod`.

## 5. Verification Method
1. **Inspect Report**:
   ```bash
   cat /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/report.md
   ```
2. **Verify Tool Schema Parity**:
   Inspect the 29-tool comparative mapping table in Section 2 of `report.md` against `/Users/aaron/.gemini/antigravity/mcp/chrome-devtools-mcp/*.json`.
3. **Verify Implementation & Test Plan**:
   Review Section 5 of `report.md` covering the 7-step automated E2E test suite (JSON-RPC handshake, tool advertisement, local test server navigation, a11y tree snapshot, base64 PNG validation, DOM fill/click mutation, and clean process termination).
