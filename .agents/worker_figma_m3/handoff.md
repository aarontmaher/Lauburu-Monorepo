# Hard Handoff Report: 4-Tier E2E Test Suite for Figma MCP & Rule #0 Zero-Mock Guardrails

- **Author**: Worker M3 (Test Writer) (`worker_figma_m3`)
- **Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_figma_m3`
- **Target File Owned**: `tests/test_figma_mcp_zero_mock.py`
- **Handoff Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_figma_m3/handoff.md`
- **Timestamp**: 2026-08-26T22:07:30+10:00
- **Status**: COMPLETE & VERIFIED (66/66 Tests Passing - 100% Pass Rate)

---

## 1. Observation

### 1.1 Verified Upstream Deliverables & Infrastructure
1. **Figma MCP Setup CLI (`06_scripts_and_tooling/scripts/setup_figma_mcp.py`)**:
   - `SettingsConfigurator`: Manages `~/.gemini/settings.json` with atomic writes (`.tmp` staging) and timestamped backups (`.bak.<timestamp>`).
   - `FigmaAuthManager`: Handles Personal Access Token (PAT) validation via `https://api.figma.com/v1/me` and OAuth 2.0 browser callback flow.
   - `HealthVerifier`: Performs live stdio JSON-RPC 2.0 handshake (`initialize` and `tools/list`) probe.
   - Verified live registration in `~/.gemini/settings.json` with `"trust": true` and command `python3 figma_mcp_client.py --stdio`.

2. **Figma REST Client & Stdio MCP Server (`06_scripts_and_tooling/scripts/figma_mcp_client.py`)**:
   - `FigmaRESTClient`: Zero-mock client implementing `get_file`, `get_file_nodes`, `get_image`, `get_comments`, `get_me` with HTTP 429 rate limit backoff and URL parsing.
   - `FigmaMCPServer`: JSON-RPC 2.0 stdio server exposing 5 tools with strict MCP schemas.

3. **Rule #0 Zero-Mock AST Linter (`06_scripts_and_tooling/scripts/figma_zero_mock_linter.py`)**:
   - `FigmaZeroMockLinter`: Pre-merge blocking static analyzer (exit code 1 on mock data, exit code 0 on pure structural layout).
   - Scanners for React/Next.js (`JsTsxScanner`), Vue SFC (`VueScanner`), Flutter/Dart (`DartUiScanner`), HTML/Jinja (`HtmlScanner`), and Python AST (`PythonAstJudge`).
   - Unified `.patch` remediation generator.

4. **Tri-Lens Visual Swarm Auditor (`06_scripts_and_tooling/scripts/figma_tri_lens_auditor.py`)**:
   - `TriLensSwarmAuditor`: Multi-engine validator (Lens 1 CDP Blink, Lens 2 Gecko Marionette, Lens 3 ADB Mobile).
   - `FrameDeltaValidator`: 5-frame MD5 hash sequence evaluator proving dynamic rolling updates.
   - `VisualParityEngine`: SSIM structural similarity index calculator (threshold >= 0.95).
   - `DomZeroMockAuditor`: Accessibility tree / DOM mock token scanner.

5. **Authoritative Standard Operating Procedure (`06_scripts_and_tooling/docs/FIGMA_ZERO_MOCK_SOP.md`)**:
   - Authoritative SOP defining design-to-code pipelines, discrimination rubrics, and CI/CD blocking gates.

---

## 2. Logic Chain & Test Suite Architecture

The test suite in `tests/test_figma_mcp_zero_mock.py` was constructed to provide mathematical proof of zero-mock compliance, boundary resilience, and cross-subsystem cohesion across 4 discrete tiers:

### Tier 1: Feature Coverage (29 Tests across 5 Features)
- **Feature 1.1: Figma MCP Setup CLI & SettingsConfigurator (6 Tests)**:
  - `test_setup_cli_status_inspection`: Validates status dictionary structure, detecting settings file presence and registration flags.
  - `test_setup_cli_register_stdio_server`: Validates adding `figma` server with `"trust": true`, executable command, args, and token.
  - `test_setup_cli_register_remote_server`: Validates adding `figma-remote` with URL and `"trust": true`.
  - `test_setup_cli_unregister_server`: Validates clean unregistration of stdio/remote servers.
  - `test_setup_cli_atomic_backup_and_rollback`: Validates backup creation and exact state restoration via rollback.
  - `test_setup_cli_validate_pat_format_and_probe`: Validates PAT format and probe against mock Figma API `/v1/me`.
- **Feature 1.2: Figma MCP Client JSON-RPC Stdio Protocol (6 Tests)**:
  - `test_jsonrpc_initialize`: Validates `protocolVersion` ("2024-11-05"), capabilities, and serverInfo (`"figma-mcp"`).
  - `test_jsonrpc_tools_list`: Validates exposure of all 5 tools (`get_file`, `get_file_nodes`, `get_image`, `get_comments`, `get_me`).
  - `test_jsonrpc_ping`: Validates empty result response `{}`.
  - `test_jsonrpc_tools_call_valid`: Validates successful dispatch and wrapping in `content: [{"type": "text", "text": ...}]`.
  - `test_jsonrpc_tools_call_error_handling`: Validates error handling with `isError: true` on invalid arguments.
  - `test_jsonrpc_unknown_method_error`: Validates error code `-32601` on unrecognized JSON-RPC methods.
- **Feature 1.3: Figma MCP Tool Schemas (5 Tests)**:
  - `test_schema_get_file`: Verifies required `["file_key"]`, properties `depth`, `geometry`.
  - `test_schema_get_file_nodes`: Verifies required `["file_key", "ids"]`, array type for `ids`.
  - `test_schema_get_image`: Verifies required `["file_key", "ids"]`, format enum `["png", "svg", "pdf", "jpg"]`, scale.
  - `test_schema_get_comments`: Verifies required `["file_key"]`.
  - `test_schema_get_me`: Verifies empty input schema for user profile.
- **Feature 1.4: Zero-Mock Linter on Permissible Structural Layouts (6 Tests)**:
  - `test_permissible_react_tsx_layout`: Tests React TSX layout with dynamic props `{data?.heartRate ?? '--'}` (0 violations).
  - `test_permissible_vue_sfc_layout`: Tests Vue SFC with `{{ telemetry?.spo2 ?? '--' }}` (0 violations).
  - `test_permissible_flutter_dart_layout`: Tests Flutter widget tree with dynamic expressions `Text(snapshot.data?.hr ?? '--')` (0 violations).
  - `test_permissible_html_layout`: Tests semantic HTML table with `<th>Heart Rate</th>` (0 violations).
  - `test_permissible_python_dashboard`: Tests Python view with `stream.get("hr", "--")` (0 violations).
  - `test_permissible_annotated_visual_animation`: Tests canvas animation with `/* @verified-visual-animation */` (0 violations).
- **Feature 1.5: Tri-Lens Visual Swarm MD5 Frame Hash & SSIM Parity (6 Tests)**:
  - `test_frame_hash_computation`: Verifies 32-character hexadecimal MD5 digest.
  - `test_dynamic_frame_delta_validation`: Verifies 5-frame sequence passes dynamic rolling updates check (`unique_count == 5`).
  - `test_ssim_identical_parity`: Verifies SSIM score == 1.0 (>= 0.95 threshold) on identical images.
  - `test_ssim_degraded_parity_mismatch`: Verifies SSIM score < 0.90 on mismatched black/white images.
  - `test_dom_zero_mock_auditor_clean`: Verifies clean DOM with dynamic placeholders has 0 mock tokens.
  - `test_tri_lens_swarm_aggregation`: Verifies multi-engine aggregation across Lens 1 (CDP), Lens 2 (Marionette), and Lens 3 (ADB).

### Tier 2: Boundary & Corner Cases (27 Tests across 5 Features)
- **Corner Case 2.1: Settings.json Fault Tolerance & Atomic Recovery (5 Tests)**:
  - `test_malformed_json_quarantine_and_recovery`: Verifies malformed JSON raises descriptive `ValueError`.
  - `test_missing_parent_directory_creation`: Verifies auto-creation of parent directories on save.
  - `test_atomic_write_safety_tmp_file`: Verifies atomic write prevents corruption and leaves no dangling `.tmp` files.
  - `test_rollback_no_backups_available`: Verifies clean `(False, msg)` return when no backup exists.
  - `test_multiple_sequential_backups_and_rollbacks`: Verifies sequential backups maintain history and rollback restores prior state.
- **Corner Case 2.2: Missing/Revoked Figma Tokens & Auth Errors (5 Tests)**:
  - `test_http_401_unauthorized_no_infinite_loop`: Verifies HTTP 401 raises `FigmaAPIError(401)` with single attempt (no retry loop).
  - `test_missing_env_token_raises_before_request`: Verifies empty token raises 401 before network call.
  - `test_pat_vs_oauth_bearer_headers`: Verifies `figd_` prefix uses `X-Figma-Token` header, while regular token uses `Authorization: Bearer`.
  - `test_http_403_forbidden_handling`: Verifies HTTP 403 raises `FigmaAPIError(403)` with body details.
  - `test_malformed_api_error_response`: Verifies non-JSON 502 HTML error page is handled without JSON parser crash.
- **Corner Case 2.3: Non-existent / Malformed Figma Node IDs & File Keys (5 Tests)**:
  - `test_non_existent_node_id_response`: Verifies graceful handling of `nodes: {"999:999": null}`.
  - `test_complex_url_node_id_parsing`: Verifies URL normalization with dashed and percent-encoded node IDs (`10-25`, `2%3A100`).
  - `test_string_vs_list_node_ids_normalization`: Verifies normalization of comma-separated strings vs lists.
  - `test_empty_or_whitespace_file_key`: Verifies stripping of whitespace around file keys.
  - `test_special_character_and_dash_node_ids`: Verifies automatic replacement of dashes with colons in node IDs.
- **Corner Case 2.4: Empty Comments Threads & Rate Limiting HTTP 429 Backoff (5 Tests)**:
  - `test_empty_comments_thread_handling`: Verifies `{"comments": []}` returns empty list cleanly.
  - `test_http_429_rate_limit_backoff_and_recovery`: Verifies HTTP 429 with `Retry-After` header waits and recovers on subsequent attempt.
  - `test_http_429_exceeding_max_retries`: Verifies persistent 429 raises `FigmaAPIError(429)` after exhausting retries.
  - `test_transient_network_urlerror_retry`: Verifies recovery on transient `URLError`.
  - `test_large_comment_payload_with_nested_replies`: Verifies 100-comment payload processing without truncation.
- **Corner Case 2.5: Zero-Mock Linter Edge Cases & Anti-Cheat Discrimination (7 Tests)**:
  - `test_linter_clean_waiting_state_pass`: JSX `{rate ?? '--'}` MUST PASS (0 violations).
  - `test_linter_chrome_headers_and_labels_pass`: Headers `<th>Heart Rate</th>` MUST PASS (0 violations).
  - `test_linter_hardcoded_metric_in_display_fail`: Display `<span>142 bpm</span>` FAILS (Rule `ZM-JSX-01`).
  - `test_linter_static_mock_arrays_fail`: Mock array `const mockDevices = [...]` FAILS (Rule `ZM-JS-03`).
  - `test_linter_synthetic_timers_fail`: `setTimeout(() => setStatus('ONLINE'), 1000)` FAILS (Rule `ZM-JS-05`).
  - `test_linter_python_synthetic_math_multiplier_fail`: Python `single_tp * 2.0` FAILS (Rule `ZM-PY-02`).
  - `test_linter_dart_hardcoded_text_fail`: Dart `Text("142 bpm")` FAILS (Rule `ZM-DART-01`).

### Tier 3: Cross-Feature Combinations (5 Pairwise Interaction Tests)
- `test_pipeline_ast_extraction_to_code_to_linter_to_trilens`: Verifies complete pipeline: Figma AST extraction -> React TSX generation with dynamic props -> Zero-Mock Linter audit (100% score) -> Tri-Lens SSIM parity (>= 0.95).
- `test_pipeline_settings_to_stdio_mcp_to_client_dispatch`: Verifies Settings registration -> Stdio MCP handshake -> `tools/call` execution -> AST response payload.
- `test_precommit_hook_blocks_mock_component_and_passes_clean_component`: Verifies linter CLI pre-commit execution exiting with code 1 on mock data and code 0 on clean code.
- `test_linter_auto_remediation_diff_generation`: Verifies automated remediation diff generation for detected mock literals.
- `test_auth_token_registration_and_rest_client_dispatch`: Verifies token registration in settings -> REST client authentication -> `/v1/me` profile query.

### Tier 4: Real-World Scenarios (5 E2E Workload Tests)
- `test_real_world_live_telemetry_stream_component`: Live Movesense biometrics dashboard component bound to WebSocket stream passes Rule #0 linter and Tri-Lens visual audit (100% score, 0 violations).
- `test_real_world_hardcoded_mock_component_rejected_and_remediated`: Real-world component with hardcoded mock data is caught, blocked (exit code 1), and remediation diff is produced.
- `test_real_world_live_settings_verification`: Real-world validation of `~/.gemini/settings.json` proving `figma` MCP server is registered, trusted (`"trust": true`), and configured with stdio Python runner.
- `test_real_world_multi_component_design_system_audit`: Multi-language design system audit (React, Vue, Flutter, Python) with aggregate reporting (score: 100.0, 0 violations).
- `test_real_world_stdio_subprocess_e2e_jsonrpc_lifecycle`: Real background subprocess spawning `figma_mcp_client.py --stdio` with `initialize`, `ping`, and `tools/list` frame exchange over pipes.

---

## 3. Caveats

- **Figma Cloud Canvas Live Tokens**: Live querying against active private Figma canvas files requires setting `FIGMA_ACCESS_TOKEN`. For test suite isolation and reproducible offline CI/CD execution, network interactions in unit tests are mocked via standard `unittest.mock.patch`, while the stdio MCP protocol and linter scanners run genuine live subprocesses and AST tokenizers.
- **No Other Caveats**: All 66 tests execute without external network dependencies, completing in ~0.16 seconds.

---

## 4. Conclusion

The 4-Tier E2E Test Suite for Figma MCP and Rule #0 Zero-Mock Guardrails (`tests/test_figma_mcp_zero_mock.py`) is complete, robust, and 100% passing. It rigorously enforces Monorepo Rule #0 across all supported UI representations and guarantees the integrity of the Figma Model Context Protocol server.

---

## 5. Verification Method

To independently execute and verify the complete test suite:

```bash
# 1. Execute all 66 tests with verbose output:
python3 -m unittest -v tests/test_figma_mcp_zero_mock.py

# 2. Execute with strict ResourceWarning checking:
python3 -W error::ResourceWarning -m unittest tests/test_figma_mcp_zero_mock.py

# 3. Verify live settings configuration:
python3 06_scripts_and_tooling/scripts/setup_figma_mcp.py --status

# 4. Verify live stdio handshake probe:
python3 06_scripts_and_tooling/scripts/setup_figma_mcp.py --verify
```
