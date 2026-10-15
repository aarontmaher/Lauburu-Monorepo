# Project: Gemini Lens & PyCharm Bidirectional Integration

## Architecture
The system provides a robust, bidirectional, zero-mock integration synchronizing real-time perception context and telemetry between Screen Lens Sovereign, Gemini Spark / Gemini Notebook APIs, and the JetBrains IDE (PyCharm 2026.2), with concurrent dual-account execution (`aaron.t.maher@gmail.com` and `lauburu@lauburugrappling.com`) and resilient hourly sidecar automation.

```
                           +-------------------------------------+
                           |      Hourly Cron / Sidecar CLI      |
                           |  (sidecar.json / sync_engine.py)    |
                           +------------------+------------------+
                                              |
                   +--------------------------+--------------------------+
                   |                                                     |
       +-----------v-----------+                             +-----------v-----------+
       |   DualAccountManager  |                             |   ResilienceEngine    |
       | - Personal Admin ADC  |                             | - 429 Exponential     |
       | - Workspace DWD OAuth |                             |   Backoff & Cooldown  |
       | - Isolated genai      |                             | - Offline JSONL Queue |
       |   Client instances    |                             | - Sanctuary RAM Check |
       +-----------+-----------+                             +-----------+-----------+
                   |                                                     |
                   +--------------------------+--------------------------+
                                              |
       +--------------------------------------v--------------------------------------+
       |                         GeminiLensSyncOrchestrator                          |
       |  1. Harvest Lens context (Port 3037 / 3035 / 4003 / SQLite)                 |
       |  2. Query Gemini Spark MCP (Port 9999) / Google GenAI SDK                   |
       |  3. Package BidirectionalSyncPayload per account                            |
       +--------------------------------------+--------------------------------------+
                                              |
                   +--------------------------+--------------------------+
                   |                                                     |
       +-----------v-----------+                             +-----------v-----------+
       |   PyCharmIntegrator   |                             |   TelemetryRecorder   |
       | - Detect active       |                             | - Emit JSONL session  |
       |   workspace PID 40445 |                             |   telemetry per acct  |
       | - Atomic cell update  |                             | - Update status JSON  |
       |   in target notebook  |                             | - Tri-Proof SHA256    |
       | - .idea metadata sync |                             |   verification        |
       +-----------------------+                             +-----------------------+
```

## Code Layout
Project root: `/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/gemini_lens_integration`
- `config/sync_config.json`: Canonical configuration for endpoints, accounts, timeouts, and paths.
- `sidecar.json`: Hourly cron schedule configuration (`CRON_TZ=Australia/Sydney 0 * * * *`).
- `sync_engine.py`: CLI entrypoint supporting `--dry-run`, `--config`, `--sidecar`, `--account`, `--once`, `--verbose`.
- `auth_manager.py`: Dual-account authentication, credential loading, token refresh, and client isolation.
- `resilience.py`: HTTP 429 exponential backoff, circuit-breaker, offline buffering, and Darwin RAM sanctuary auditing.
- `lens_client.py`: Screen Lens Sovereign harvester querying ports 3037, 3035, 4003 with local SQLite fallback.
- `notebook_sync.py`: PyCharm active workspace detection, atomic notebook cell injection (`lens_global_orchestrator.ipynb`), and `.idea` metadata sync.
- `session_logs/`: Directory for runtime status and offline queue:
  - `session_logs/gemini_lens_sync_status.json`: Latest run status manifest.
  - `session_logs/pending_sync_queue.jsonl`: Durable offline buffer queue.
- `tests/`: E2E and unit test suites:
  - `tests/test_sync_dry_run.py`: Acceptance test for programmatic dry-run and simulated dual-account output.
  - `tests/test_auth_isolation.py`: Tests for credential separation between Personal Admin and Workspace accounts.
  - `tests/test_lens_pycharm_sync.py`: Tests for Screen Lens perception harvest and PyCharm notebook injection.
  - `tests/test_resilience.py`: Tests for 429 backoff, network timeout offline queueing, and missing credentials.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Personal Admin Auth Provider | ADC token loading and refresh for `aaron.t.maher@gmail.com` | M1 | Survey (spec_miner_survey_2) |
| 2 | Workspace OAuth Auth Provider | OAuth2 / DWD token refresh for `lauburu@lauburugrappling.com` | M1 | Survey (spec_miner_survey_2) |
| 3 | GenAI Client Isolation | Instantiate isolated `google.genai.Client` instances without global env collisions | M1 | Survey (spec_miner_survey_2) |
| 4 | Screen Lens Perception Harvester | Harvest active app, window, OCR snippet, and mesh health from Port 3037/3035/4003 | M2 | Survey (explorer_survey_1) |
| 5 | Screen Lens Local DB Fallback | Local SQLite fallback (`ocr_frames.db` / `screen_lens.sqlite`) when ports are offline | M2 | Survey (explorer_survey_1) |
| 6 | Gemini Spark MCP SSE Client | Client connecting to Port 9999 SSE bridge for tool and prompt synchronization | M2 | Survey (spec_miner_survey_2) |
| 7 | PyCharm Active Workspace Detector | Detect running PyCharm process (PID 40445, port 63342) and open project | M3 | Survey (explorer_survey_1) |
| 8 | Atomic Notebook Cell Injector | Atomically inject/update sync cell in `lens_global_orchestrator.ipynb` | M3 | Survey (explorer_survey_1) |
| 9 | PyCharm Metadata Synchronizer | Write `.idea/lens_context.json` for IDE plugins and file watchers | M3 | Survey (explorer_survey_1) |
| 10 | Colab GPU Offload State Manager | Audit host RAM against Rule 3 ($\ge 4.8\text{ GB}$) and record Colab offload state | M3 | Survey (spec_miner_survey_2) |
| 11 | HTTP 429 Exponential Backoff & Cooldown | 1s–32s jittered backoff and 60s cooldown for rate limits | M4 | Survey (explorer_survey_3) |
| 12 | Offline Queue & Buffer Manager | Durable JSONL offline queue (`pending_sync_queue.jsonl`) for network drops | M4 | Survey (explorer_survey_3) |
| 13 | Missing Credential Graceful Degradation | Safe degradation returning status manifest without throwing unhandled exceptions | M4 | Survey (explorer_survey_3) |
| 14 | Sidecar Cron Specification & Wrapper | Match `~/.gemini/config/sidecars/gemini-lens-sync/sidecar.json` hourly automation | M4 | Survey (explorer_survey_3) |
| 15 | Programmatic Dry-Run CLI Engine | CLI entrypoint with `--dry-run` returning Exit Code 0 and logging simulated sync output | M4 | ORIGINAL_REQUEST & Survey |
| 16 | Concurrent Dual-Account Execution Flow | Run both accounts concurrently within the global lens orchestrator notebook | M4 | ORIGINAL_REQUEST (R4) |
| 17 | E2E Test Suite Validation & Verification | 100% pass of Tiers 1-4 tests, followed by Tier 5 adversarial hardening | M5 | Project Pattern Mandate |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Dual-Account Auth & Isolation | `auth_manager.py`, `config/sync_config.json`, credential loaders, client isolation | none | DONE |
| 2 | M2: Screen Lens & Gemini Spark Sync | `lens_client.py`, Port 3037/3035 client, SQLite fallback, Spark MCP bridge | M1 | DONE |
| 3 | M3: PyCharm IDE Integration & Notebook Sync | `notebook_sync.py`, workspace detector, atomic notebook cell injection, `.idea` sync | M1, M2 | DONE |
| 4 | M4: Hourly Resilience, CLI & Dry-Run Engine | `resilience.py`, `sync_engine.py`, sidecar configuration, concurrent dual execution, exit code 0 dry run | M1, M2, M3 | DONE |
| 5 | M5: E2E Verification & Adversarial Hardening | Validate 100% E2E test pass across all tiers, perform adversarial hardening and forensic audit | M1, M2, M3, M4 | DONE |

## Interface Contracts
### `auth_manager` ↔ `sync_engine` & `notebook_sync`
- Class `DualAccountManager`:
  - `authenticate_account(account_id: str, dry_run: bool = False) -> AccountSession`
  - `authenticate_all(dry_run: bool = False) -> Dict[str, AccountSession]`
  - `get_genai_client(account_id: str) -> Optional[google.genai.Client]`
- Dataclass `AccountSession`:
  - `account_id: str`
  - `role: str`
  - `is_authenticated: bool`
  - `auth_method: str` ("adc", "oauth2", "simulated_dry_run")
  - `token_expiry: Optional[float]`
  - `client: Any`

### `lens_client` ↔ `sync_engine`
- Class `ScreenLensClient`:
  - `harvest_perception(timeout_s: float = 2.0) -> Dict[str, Any]`
  Returns dictionary:
  `{"timestamp": str, "active_app": str, "window_title": str, "ocr_snippet": str, "mesh_health": dict, "source": str}`

### `notebook_sync` ↔ `sync_engine`
- Class `NotebookSynchronizer`:
  - `detect_pycharm_workspace() -> Dict[str, Any]`
  - `sync_notebook_and_ide(payload: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]`
  Writes atomic JSON to `lens_global_orchestrator.ipynb` and `.idea/lens_context.json`.

### `resilience` ↔ `sync_engine`
- Class `ResilienceManager`:
  - `execute_with_retry(fn: Callable, max_backoff: float = 32.0) -> Any`
  - `queue_offline_payload(payload: Dict[str, Any]) -> str`
  - `drain_offline_queue(sender_fn: Callable) -> int`
  - `check_memory_sanctuary() -> Dict[str, Any]`
