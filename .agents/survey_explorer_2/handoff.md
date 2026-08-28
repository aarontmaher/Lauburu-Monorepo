# Survey Explorer 2 — Handoff Report
**Milestone**: Survey & Architectural Design for Cloudflare Zero Trust Telemetry in Textual TUI (Screen 6 / Tab 1 Red/Blue Arena)  
**Target File**: `01_apps/canonical_port/tui/screens/training_screen.py` and related TUI files  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_2/`  
**Timestamp**: 2026-08-29T05:44:30+10:00  

---

## 1. Observation

Direct empirical inspection of the repository structure, source files, test suites, and environment configurations revealed the following:

### 1.1 `training_screen.py` Current State & Widget Hierarchy
- **File**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui/screens/training_screen.py` (71 lines)
- **Class**: `TrainingScreen(Screen)`
- **Key Binding**: `q -> app.pop_screen` ("Back to Hub"); In `canonical_tui.py`: key `'t'` and `'6'` navigate to `TrainingScreen` (Screen 6 in 9-Screen Stability Hierarchy).
- **Current Layout (`compose`)**:
  ```python
  def compose(self) -> ComposeResult:
      yield Header()
      with TabbedContent(initial="tab_debate"):
          with TabPane("Red/Blue Arena", id="tab_red_blue"):
              yield PlaceholderGymWidget("Gym 1: Adversarial Red/Blue Team Arena (SSH/Devil's Advocate)")
          with TabPane("Mesh Healing", id="tab_mesh_heal"):
              yield PlaceholderGymWidget("Gym 2: Multi-Transport Autonomous Network Healing (Tailscale/Bluetooth)")
          with TabPane("Stealth Compute", id="tab_stealth"):
              yield PlaceholderGymWidget("Gym 3: Tensor Routing & Stealth Compute (Bypassing Doze on Pixel 10)")
          with TabPane("Software Dev (ELO)", id="tab_elo"):
              yield PlaceholderGymWidget("Gym 4: Software Dev Training Game (Live ELO tracking via architect_leaderboard.json)")
          with TabPane("Spatial Grappling", id="tab_tatami"):
              yield PlaceholderGymWidget("Gym 5: 955-Node OPML Spatial Grappling & 3D Tatami Kinematics")
          with TabPane("Continuous Debate", id="tab_debate"):
              yield ContinuousDebateWidget()
      yield Footer()
  ```
- **Observations on Tab 1**:
  - Tab 1 identifier is `tab_red_blue` (Title: `"Red/Blue Arena"`).
  - Currently contains only a stub `PlaceholderGymWidget` rendering static text (`"Waiting for telemetry stream...\n- Status: OK"`).

### 1.2 Multi-View Architecture & Sibling Widgets
- **`01_apps/canonical_port/tui/widgets/lauburu_gyms_widget.py`** (447 lines):
  - Defines `LauburuGymsWidget(Container)` surfacing 5 gym tabs (`tab-gym-1` through `tab-gym-5`).
  - Tab 1 is `tab-gym-1` (`"1. Red/Blue Arena (🛡️)"`), rendering `#gym-1-view` (`Static`) using `_render_gym_1()`.
  - Uses reactive dictionary `gyms_data: reactive[Dict[str, Any]] = reactive(dict, always_update=True)` and watcher `watch_gyms_data()`.
  - Currently reads local arena JSON from `CANONICAL_ARENA_STATE_PATHS` (`game_arena_state.json`) via `backend/training_telemetry_collector.py`.
- **`01_apps/canonical_port/tui/views/training_view.py`** (337 lines):
  - Container view `TrainingView(Container)` embedding `TrainingPipelineWidget` and `LauburuGymsWidget`.
  - Structured into 4 primary tabs: `tab-lora` (LoRA Ingestion Pipeline), `tab-games` (The 5 Lauburu Gyms), `tab-metrics` (PySpark AST Metrics), and `tab-traces` (Swarm Action Ledger).
  - Action buttons: `#btn-harvest-lora`, `#btn-trigger-duel`, `#btn-refresh-train`, `#btn-test-gate`.
- **`01_apps/canonical_port/backend/training_telemetry_collector.py`** (1209 lines):
  - Implements `MPSCRingBuffer` (thread-safe bounded queue), async pollers, and `get_red_blue_arena_telemetry()`.
- **`00_core_infrastructure/cloudflare/workers/ai_gateway_router/wrangler.jsonc`**:
  - Active Cloudflare Account ID: `"16282271f1eccb56f0b96afed09d21ff"`.
  - Active Gateway Slug: `"lauburu-ai-gateway"`.
  - Tunnel Host: `openclaw-standalone.trycloudflare.com` / `openclaw.lauburugrappling.com`.

### 1.3 Dependency & Import Analysis
- **`pyproject.toml`** declares: `textual>=0.50.0`, `rich>=13.7.0`, `httpx>=0.27.0`, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`.
- **Import Finding**: `lauburu_gyms_widget.py` and `backend/training_telemetry_collector.py` import `numpy` and `scipy.signal` at top-level. When running in a slim venv without `numpy`, imports fail during pytest collection. All external math/signal imports must be protected with try/except fallbacks to maintain zero-crash resiliency.

---

## 2. Logic Chain

From these observations, we deduce the step-by-step architectural pathway for integrating live Cloudflare Zero Trust telemetry into Tab 1:

```
[Cloudflare GraphQL API /client/v4/graphql]
                 │
                 ▼  (HTTP POST JSON query with Bearer Token / API Key)
[06_scripts_and_tooling/cloudflare_telemetry.py]
  - query_waf_threat_blocks() -> firewallEventsAdaptive
  - query_access_authorizations() -> accessRequestsAdaptive
  - calculate_defense_metrics() -> block rates, attack vectors, geo distribution
                 │
                 ▼  (MPSC Ring Buffer / Async poller)
[01_apps/canonical_port/backend/training_telemetry_collector.py]
  - async_get_cloudflare_telemetry() / get_cloudflare_zero_trust_snapshot()
                 │
                 ▼  (@work thread worker / set_interval reactive binding)
[01_apps/canonical_port/tui/screens/training_screen.py (and LauburuGymsWidget)]
  - Tab 1: "Red/Blue Arena" (id="tab_red_blue" / "tab-gym-1")
  - Render Summary Status Cards (Tunnel state, Pass Count, Threat Blocks, RTT)
  - Render Braille Sparkline (WAF block & Access pass frequency)
  - Render Live Combat & Defense Ledger (DataTable / Rich Table with IP, Country, Action, Vector)
  - Render Attack Vector Summary & Geo Distribution breakdown
```

### Step 1: Telemetry Data Model
The collector must produce a structured dictionary:
```python
{
    "tunnel_endpoint": "openclaw-standalone.trycloudflare.com",
    "tunnel_status": "ONLINE",  # ONLINE | DEGRADED | DISCONNECTED
    "latency_ms": 48.2,
    "last_sync_iso": "2026-08-29T05:44:00Z",
    "blue_team": {
        "access_pass_count": 1420,
        "active_service_token": "openclaw-mesh-bridge",
        "resistance_buff_pct": 35.0,
        "recent_passes": [
            {"timestamp": "05:43:52", "identity": "aaron@lauburu.ai", "country": "AU", "app": "OpenClaw", "action": "ALLOW"}
        ]
    },
    "red_team": {
        "waf_threat_blocks": 87,
        "block_rate_pct": 5.8,
        "threat_level": "LOW",  # LOW | ELEVATED | CRITICAL
        "recent_breaches": [
            {"timestamp": "05:43:30", "client_ip": "198.51.100.42", "country": "DE", "action": "BLOCK", "vector": "Prompt Injection Probe", "path": "/v1/chat/completions", "rule_id": "waf_9012"}
        ],
        "top_attack_vectors": [
            {"vector": "Prompt Injection Probe", "count": 34},
            {"vector": "Port 50052 RPC Scanner", "count": 28},
            {"vector": "Path Traversal Probe", "count": 14}
        ],
        "geo_distribution": [
            {"country": "DE", "pct": 42.0},
            {"country": "US", "pct": 31.0},
            {"country": "NL", "pct": 18.0},
            {"country": "AU", "pct": 9.0}
        ]
    },
    "is_live": True,  # False when no API keys or offline
}
```

### Step 2: Textual UI Layout & Widget Selection for Tab 1
In `training_screen.py`, replace `PlaceholderGymWidget` inside `TabPane("Red/Blue Arena", id="tab_red_blue")` with a comprehensive adversarial dashboard:
1. **Status Metric Bar (Horizontal / Grid Layout)**:
   - Card 1: `Tunnel Status` — `[bold green]● ONLINE[/bold green] (openclaw-standalone.trycloudflare.com | 48.2ms RTT)`
   - Card 2: `Blue Team Fortress` — `[bold cyan]1,420 Access Passes[/bold cyan] (+35% mTLS Armor)`
   - Card 3: `Red Team Infiltration` — `[bold red]87 WAF Threat Blocks[/bold red] (5.8% Block Rate | Threat: LOW)`
2. **High-Density Sparklines**:
   - Double Braille sparklines (`render_braille_sparkline`) charting:
     - Blue Team Access Pass dynamics: `[⠋⠙⠹⠸⠼⠴⠦⠧]`
     - Red Team Attack frequency: `[⠂⠂⠄⠆⠖⠶⠶⠖]`
3. **Live Breach & Defense Combat Ledger (Rich Table / Textual DataTable)**:
   - Formatted with 6 columns: `Timestamp`, `Sentinel / Faction` (`RED INFILTRATOR` vs `BLUE SENTINEL`), `Client IP & Geo` (`198.51.100.42 (DE)`), `Target Vector / Path` (`/v1/chat/completions`), `Action Taken` (`BLOCKED [403]` / `CHALLENGED` / `PASSED [200]`), `Defense Rule ID` (`WAF: Prompt Injection Rule #9012`).
4. **Threat Vector & Geo Distribution Panels (2-Column Horizontal)**:
   - Panel A: Top 5 Target Vectors ranked by frequency.
   - Panel B: Geo-location origin distribution.
5. **Interactive Controls (Horizontal Button Bar)**:
   - `Button("🛡️ /cf_poll Force Telemetry Sync", id="btn-poll-cf", variant="primary")`
   - `Button("⚔️ /trigger_sim Red Team Breach Probe", id="btn-probe-cf", variant="warning")`
   - `Button("📜 /cf_logs View Full Audit Stream", id="btn-logs-cf", variant="default")`

### Step 3: Non-Blocking Event-Loop & Worker Pattern
To adhere strictly to Textual async standards without freezing the UI:
- Use `set_interval(2.0, self.refresh_cf_telemetry_async)` in `on_mount()`.
- Define an async poller in `TrainingScreen`:
  ```python
  async def refresh_cf_telemetry_async(self) -> None:
      loop = asyncio.get_running_loop()
      try:
          # Call data collector in executor to prevent blocking
          data = await loop.run_in_executor(None, get_cloudflare_zero_trust_telemetry)
          self.cf_telemetry_data = data
      except Exception:
          pass
  ```
- Use Textual reactive property with instant repainting watcher:
  ```python
  cf_telemetry_data: reactive[Dict[str, Any]] = reactive(dict, always_update=True)
  
  def watch_cf_telemetry_data(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> None:
      self._render_red_blue_arena()
  ```

### Step 4: Rule #0 Zero-Mock Truth Invariants
- If `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, or `CLOUDFLARE_ZONE_ID` are unset or if Cloudflare is unreachable:
  - All numerical counts must display `--` (e.g. `Access Passes: --`, `WAF Blocks: --`).
  - Status indicator must render: `[dim yellow]● DISCONNECTED (Awaiting Cloudflare Zero Trust API Credentials)[/dim yellow]`.
  - Ledger displays a single waiting state row: `[dim]No live Cloudflare Zero Trust telemetry active. (Awaiting live connection on openclaw-standalone.trycloudflare.com)[/dim]`.
  - Under NO circumstances may synthetic random numbers or simulated IP arrays be generated.

---

## 3. Caveats

1. **Dual Tab 1 Surface in Monorepo**:
   - There are two primary places where "Tab 1 Red/Blue Arena" exists:
     - Direct in `screens/training_screen.py` (`tab_red_blue`)
     - Embedded in `widgets/lauburu_gyms_widget.py` (`tab-gym-1`) / `views/training_view.py` (`tab-games`)
   - **Recommendation**: Both `training_screen.py` and `lauburu_gyms_widget.py` should import and share the same Red/Blue Arena rendering component (`RedBlueArenaWidget` or `render_red_blue_arena_panel()`) to ensure complete architectural harmony across standalone screen mode and embedded view mode.
2. **Cloudflare GraphQL API Credentials**:
   - Requires `CLOUDFLARE_API_KEY` (or `CLOUDFLARE_API_TOKEN`), `CLOUDFLARE_ACCOUNT_ID` (`16282271f1eccb56f0b96afed09d21ff`), and optionally `CLOUDFLARE_ZONE_ID`.
   - The collector must load from `os.environ` or `.env` safely without hardcoding secrets.
3. **Optional Dependency Fallbacks**:
   - `numpy`, `scipy`, `aiohttp`, and `psutil` must always be wrapped in `try/except ImportError` with zero-crash fallbacks so the TUI runs smoothly in all environments.

---

## 4. Conclusion

- **Feasibility & Integration Path**: The Textual architecture in `01_apps/canonical_port/tui/` is well-structured and fully capable of hosting live Cloudflare Zero Trust telemetry in Tab 1 (Red/Blue Arena).
- **Target Component Architecture**:
  - Create `06_scripts_and_tooling/cloudflare_telemetry.py` to query Cloudflare GraphQL analytics (`firewallEventsAdaptive` and `accessRequestsAdaptive`).
  - Wire `cloudflare_telemetry.py` into `01_apps/canonical_port/backend/training_telemetry_collector.py`.
  - Upgrade `01_apps/canonical_port/tui/screens/training_screen.py` Tab 1 (`tab_red_blue`) and `01_apps/canonical_port/tui/widgets/lauburu_gyms_widget.py` Tab 1 (`tab-gym-1`) to render:
    1. Tunnel & Sentinel summary status cards
    2. Blue Team Access Pass counters & mTLS armor badge
    3. Red Team WAF Threat Block metrics & threat severity level
    4. 4x subpixel Braille sparklines
    5. Real-time Combat & Defense Ledger (Rich Table with IP, Country, Action, Vector)
    6. Attack Vector distribution & Geo breakdown
    7. Non-blocking `@work` / `set_interval` reactive updates
    8. Strict Rule #0 Zero-Mock state when disconnected (`--`)

---

## 5. Verification Method

To independently verify this design and its implementation:

### Verification Commands:
1. **Module Import & Dependency Check**:
   ```bash
   python3 -c "from textual.screen import Screen; from rich.table import Table; print('Textual & Rich OK')"
   ```
2. **Unit & Lifecycle Test for TrainingScreen & TrainingView**:
   ```bash
   /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/pytest 01_apps/canonical_port/tests/unit/test_training_screen_and_view.py -v
   ```
3. **E2E Tabbed Navigation & Stress Tests**:
   ```bash
   /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/pytest 01_apps/canonical_port/tests/e2e/test_training_screen_e2e.py -v
   ```
4. **Standalone Pilot Launch**:
   ```bash
   /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/python 01_apps/canonical_port/tui/screens/training_screen.py
   ```
5. **Zero-Mock Disconnected Verification**:
   - Run without `CLOUDFLARE_API_KEY` set and verify that all metric fields render `--` without exceptions or fake data.
