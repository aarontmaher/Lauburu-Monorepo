## 2026-08-26T11:05:35Z
You are the Marionette MCP Worker in the Lauburu Swarm.

Your working directory is: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1_1
Project root: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Authoritative User Request: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md
Scope & Architecture: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
Survey & Architecture Report: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_marionette_1/report.md

## Exclusive Write Ownership
You exclusively own: \`00_core_infrastructure/mcp_servers/marionette-mcp/\`

## Objective
Develop and verify the complete Node.js stdio MCP server (\`marionette-mcp\`) per Requirement 1:
1. Initialize package in \`00_core_infrastructure/mcp_servers/marionette-mcp/\` with \`@modelcontextprotocol/sdk\`, \`zod\`, \`selenium-webdriver\`, and \`geckodriver\`.
2. Implement stdio MCP server exposing tools matching the \`chrome-devtools-mcp\` API:
   - \`navigate_page\`, \`navigate\`, \`take_screenshot\`, \`screenshot\`, \`take_snapshot\`, \`get_ax_tree\`, \`click\`, \`fill\`, \`fill_form\`, \`evaluate_script\`, \`wait_for\`, \`list_pages\`, \`new_page\`, \`close_page\`, \`select_page\`, \`resize_page\`, etc.
3. Implement GeckoDriver / Marionette session manager controlling headless Firefox with automatic port management and clean process teardown.
4. Implement injected JavaScript accessibility tree serializer with UID markers for fast DOM interaction.
5. Provide a standalone programmatic test (\`test/test_marionette.js\` or \`test_mcp.py\`) verifying launching Firefox/driver, navigating to a local URL / data URL, and returning a valid base64 PNG screenshot via MCP tool call.
6. Run the test suite and verify 100% pass rate.
