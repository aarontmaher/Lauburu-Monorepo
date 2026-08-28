# Marionette MCP Server (`marionette-mcp`)

Firefox & GeckoDriver Model Context Protocol (MCP) Server implementing 100% schema parity with `chrome-devtools-mcp` across 29 tools.

## Architecture

```
                               +-------------------------------------+
                               | AI Client / Swarm Agent (JSON-RPC)   |
                               +-------------------------------------+
                                                  |  (Stdio Transport)
                                                  v
                               +-------------------------------------+
                               |      marionette-mcp Server          |
                               | (SessionManager / PageRegistry)     |
                               +-------------------------------------+
                                      |                       |
                 (Live GeckoDriver)   |                       | (Self-Contained Fallback)
                                      v                       v
                   +---------------------+          +---------------------+
                   | GeckoDriver Process |          | Embedded Headless   |
                   | (Port 4444 / 2828)  |          | DOM & AX Tree Engine|
                   +---------------------+          +---------------------+
                              |
                              v
                   +---------------------+
                   | Headless Firefox    |
                   +---------------------+
```

## 29 Supported Tools

1. `click`: Click on element by monotonic `uid` (supports double-click and snapshot attachment).
2. `close_page`: Closes tab/page by `pageId` (protects last open tab).
3. `drag`: Drag and drop from `from_uid` to `to_uid`.
4. `emulate`: Emulate viewport, user agent, color scheme, geolocation, network conditions, CPU throttling.
5. `evaluate_script`: Evaluate JavaScript function in page context with argument bindings and JSON return.
6. `fill`: Fill text, select dropdown options, or toggle checkboxes/radios on element by `uid`.
7. `fill_form`: Atomic batch form element filling for high-efficiency turn reduction.
8. `get_console_message`: Retrieve single console message by `msgid`.
9. `get_network_request`: Retrieve network request details and body by `reqid`.
10. `handle_dialog`: Accept/dismiss alerts, confirms, or prompts with prompt response text.
11. `hover`: Move cursor over element by `uid`.
12. `lighthouse_audit`: Produce accessibility, SEO, best practices, and agentic browsing audit score report.
13. `list_console_messages`: Paginated & filtered console messages since last navigation.
14. `list_network_requests`: Paginated & filtered network requests since last navigation.
15. `list_pages`: List all open pages/tabs with numeric `pageId`, URL, and selection status.
16. `navigate_page`: Navigate by URL, back, forward, or reload with cache controls and init scripts.
17. `new_page`: Open new tab with URL and optional isolated context.
18. `performance_analyze_insight`: Inspect performance insights (DocumentLatency, LCPBreakdown, CLSBreakdown).
19. `performance_start_trace`: Begin performance timeline recording with optional auto-reload.
20. `performance_stop_trace`: Stop trace recording and export Chrome DevTools trace JSON.
21. `press_key`: Trigger keyboard keys and combinations (`Enter`, `Control+A`, `Tab`, `Escape`).
22. `resize_page`: Set explicit viewport dimensions (`width` x `height`).
23. `select_page`: Switch active focus context to target `pageId`.
24. `take_heapsnapshot`: Dump V8 / SpiderMonkey heap memory distribution to `.heapsnapshot`.
25. `take_screenshot`: Capture full-page, viewport, or element screenshot as base64 PNG.
26. `take_snapshot`: Traverse accessibility tree and serialize text snapshot with monotonic `uid` markers.
27. `type_text`: Stream text typing into focused input with optional submit key.
28. `upload_file`: Upload files into file input element.
29. `wait_for`: Polling assertion waiting for target text strings to appear in DOM.

## Building and Running

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run build

# Run unit & integration tests
npm test

# Run MCP Server via Stdio
node dist/index.js
```

## Environment Variables

- `GECKODRIVER_PATH`: Custom path to `geckodriver` binary.
- `FIREFOX_BINARY_PATH`: Custom path to `firefox` binary.
- `GECKODRIVER_PORT`: GeckoDriver HTTP port (default `4444`).
- `MARIONETTE_PORT`: Marionette TCP port (default `2828`).
