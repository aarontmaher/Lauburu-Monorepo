# Project: Google Workspace & Gemini Enterprise Sovereign Integration & Evaluation

## Architecture
This project establishes a unified dual-plane architecture merging Google Workspace and Gemini Enterprise with the Lauburu Sovereign local offline infrastructure (PySpark data lakes, Neo/Memory knowledge graphs, PyCharm/Colab notebooks, Qdrant vector search, Obsidian Tri-Vault, and SeaweedFS).

```
                    ┌─────────────────────────────────────────────────────────┐
                    │          Google Workspace & Gemini Enterprise           │
                    │    Gmail │ Drive (30 TB) │ Sheets │ Docs │ Calendar     │
                    └──────────────┬───────────────────────────┬──────────────┘
                                   │                           │
          ┌────────────────────────┴─────────┐       ┌─────────┴───────────────────────┐
          │      Mode A: Headless APIs       │       │    Mode B: Screen Lens VLA      │
          │  OAuth2 / google-api-client      │       │  Chrome Profile 2 (Rule 14)     │
          │  Python: /opt/homebrew/bin/python│       │  CoreGraphics / AppleScript     │
          │  Refresh Token: workspace_token  │       │  Ports: 3037, 3035, 4003        │
          └────────────────┬─────────────────┘       └─────────┬───────────────────────┘
                           │                                   │
                           └─────────────────┬─────────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │ (Bridge 1) PySpark    │ (Bridge 2) Neo Graph │ (Bridge 3) PyCharm    │ (Bridge 4) Qdrant    │
      │ Sheets/Drive -> Lake  │ Memory MCP Triples   │ Colab GPU & Notebooks │ Semantic RAG Search  │
      ▼                       ▼                      ▼                       ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐        ┌──────────────┐       ┌──────────────┐
│PySpark 4.2.0 │       │Memory MCP &  │       │PyCharm 2026.2│        │Qdrant Vector │       │Obsidian Vault│
│Delta Engine  │       │Neo Launcher  │       │Jupyter/Marimo│        │(:6333/Disk)  │       │& SeaweedFS   │
│Parquet Sinks │       │Port 8095     │       │Voila (:8890) │        │4 Collections │       │Quad-Vault    │
└──────────────┘       └──────────────┘       └──────────────┘        └──────────────┘       └──────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1_HEADLESS_AUTH | Headless OAuth2 authentication & autonomous refresh token handling | M2 | Survey 1 |
| 2 | F2_HEADLESS_APIS | Google Workspace API client wrapper (Drive, Docs, Sheets, Calendar, Gmail) | M2 | Survey 1 |
| 3 | F3_SCREEN_LENS_ACTUATION | CoreGraphics Ctypes / AppleScript physical actuation & ActionReceipts | M2 | Survey 2 |
| 4 | F4_BROWSER_AUTOMATION | Screen Lens VLA Chrome Profile 2 browser automation & Rule 14 compliance | M2 | Survey 2 |
| 5 | F5_PYSPARK_BRIDGE | Bidirectional Google Sheets/Drive hydration with PySpark 4.2.0 data lake | M3 | Survey 3 |
| 6 | F6_NEO_MEMORY_BRIDGE | Workspace entity/relation extraction into Neo MCP & Memory graph | M3 | Survey 3 |
| 7 | F7_NOTEBOOK_INTEGRATION | PyCharm / Colab GPU offload & interactive notebook Workspace tools | M3 | Survey 3 |
| 8 | F8_QDRANT_RAG_BRIDGE | Workspace document semantic chunking & local Qdrant hybrid RAG sync | M3 | Survey 3 |
| 9 | F9_PROGRAMMATIC_TEST | Automated test script verifying headless read/write without human intervention | M4 | Acceptance Criteria |
| 10 | F10_SCREEN_LENS_TEST | Screen Lens VLA test script verifying physical UI interaction + visual proof | M4 | Acceptance Criteria |
| 11 | F11_UNIFICATION_REPORT | Comprehensive evaluation & recommendation report proving U_unified > U_offline | M1 & M4 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Deep Research & Unification Evaluation | In-depth comparative research and mathematical proof proving why Workspace + Local Offline creates a superior system (R1) | none | DONE |
| 2 | M2: Dual-Mode Integration | Headless OAuth2 backend API wrapper and Screen Lens VLA physical UI automation (R2) | none | DONE |
| 3 | M3: Unification Bridges | Implement 4 architectural bridges: PySpark data lake, Neo/Memory graphs, PyCharm notebooks, Qdrant vector search (R3) | M2 | DONE |
| 4 | M4: Verification Suite & Final Report | Programmatic test script, Screen Lens VLA test script, Tri-Proof validation, and definitive retention report (AC) | M1, M2, M3 | DONE |

## Interface Contracts

### Headless API Wrapper (`workspace_api_client.py`)
- Runtime: `/opt/homebrew/bin/python3`
- Credentials: `workspace_credentials.json`, `workspace_token.json`
- Class `WorkspaceAPIClient`:
  - `authenticate() -> Credentials`
  - `get_gmail_profile() -> dict`
  - `read_gmail_threads(max_results: int) -> list[dict]`
  - `send_gmail_message(to: str, subject: str, body: str) -> dict`
  - `read_drive_files(page_size: int) -> list[dict]`
  - `read_sheet_data(spreadsheet_id: str, range_name: str) -> list[list]`
  - `append_sheet_data(spreadsheet_id: str, range_name: str, values: list[list]) -> dict`
  - `create_document(title: str, content: str) -> dict`

### Screen Lens VLA Actuator (`workspace_vla_actuator.py`)
- Endpoints: `http://127.0.0.1:3037` (Actuate), `http://127.0.0.1:4003` (Stream/Frame), `http://127.0.0.1:3035` (OCR)
- Class `WorkspaceVLAActuator`:
  - `preflight_health_check() -> dict`
  - `capture_baseline_frame() -> str` (path to JPEG)
  - `launch_or_focus_workspace_app(app_url: str) -> bool`
  - `actuate_keystrokes(text: str) -> ActionReceipt`
  - `actuate_click(x: int, y: int) -> ActionReceipt`
  - `capture_verification_frame() -> str`
  - `verify_visual_state(expected_text: str) -> bool`

### PySpark Bridge (`workspace_pyspark_connector.py`)
- Function `hydrate_sheet_to_spark(spreadsheet_id: str, range_name: str) -> pyspark.sql.DataFrame`
- Function `export_spark_to_sheet(df: pyspark.sql.DataFrame, spreadsheet_id: str, range_name: str) -> dict`
- Function `archive_lakehouse_partition_to_gdrive(partition_path: str, gdrive_folder_id: str) -> dict`

### Neo / Memory Graph Bridge (`workspace_memory_bridge.py`)
- Function `extract_workspace_entities_to_memory(doc_metadata: dict, email_threads: list[dict]) -> dict`
- Function `sync_graph_to_workspace_digest(entity_list: list[dict]) -> str`

### Qdrant RAG Bridge (`workspace_qdrant_sync.py`)
- Function `sync_workspace_docs_to_qdrant(docs: list[dict], collection_name: str) -> dict`
- Function `query_unified_hybrid_rag(query_text: str) -> list[dict]`

## Code Layout
- `06_scripts_and_tooling/workspace_integration/`
  - `workspace_api_client.py` — Mode A headless OAuth2 and Workspace API client
  - `workspace_vla_actuator.py` — Mode B Screen Lens VLA physical actuation and visual verifier
  - `workspace_pyspark_connector.py` — Bridge 1: PySpark Data Lake <-> Google Sheets/Drive hydration
  - `workspace_memory_bridge.py` — Bridge 2: Workspace <-> Neo MCP & Memory knowledge graph
  - `workspace_notebook_connector.py` — Bridge 3: PyCharm & Colab notebook Workspace connectors
  - `workspace_qdrant_sync.py` — Bridge 4: Qdrant vector DB semantic indexing & hybrid RAG
  - `test_workspace_programmatic_api.py` — Acceptance Criterion 1 programmatic test
  - `test_screen_lens_workspace_vla.py` — Acceptance Criterion 2 Screen Lens physical UI test
  - `WORKSPACE_EVALUATION_AND_RETENTION_REPORT.md` — Final comprehensive evaluation and retention report
