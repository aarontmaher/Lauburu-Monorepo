# Milestone 4 Scope & Specification: Cloud AI Synergy & Standalone UI Dashboard

## 1. Objectives & Overview
Milestone 4 integrates high-level reasoning and commercial visualization into the Distributed Resource & Compute Pooling Manager:
1. **Cloud AI Escalation & Evaluator**: Intelligently routes complex incidents (resource contention deadlocks, multi-link failover ambiguity, thermal drift spikes) to frontier models (Gemini Pro 3.1 High / `gemini-3.1-pro-preview` and Claude Opus 4.6 / `claude-opus-4.6`) with deterministic heuristic confidence scoring and graceful offline fallbacks.
2. **Deep Batch Analytics Engine**: Aggregates time-series rolling windows (10-minute to 1-hour), computing empirical thermal drift rates, battery discharge curves, and memory growth slopes across the 7-node mesh.
3. **FastAPI Cloud REST API**: Implements `/api/cloud/evaluate`, `/api/cloud/anomalies/batch`, `/api/cloud/status`, and `/api/cloud/models`.
4. **Standalone Cybernetic UI Dashboard**: Modern, commercial-grade responsive dashboard (HTML5, Tailwind aesthetic, custom cybernetic CSS, vanilla ES6 JS) featuring:
   - 1Hz real-time WebSocket live HUD
   - 7-layer hardware topology cards with live telemetry
   - Interactive Opt-In sliders (Light 30%, Moderate 60%, Maximum 90%)
   - Fleet Dark Mode sync toggle with WCAG AAA token display
   - Multi-WAN failover topology status & trigger
   - Cloud AI incident escalation & batch anomaly analysis panel
5. **Comprehensive Test Suite**: `tests/test_m4_cloud_and_ui.py` covering models, evaluator logic, batch analytics, REST endpoints, and UI dashboard integrity.

## 2. Interface Contracts

### 2.1 Cloud Models (`src/cloud/models.py`)
- `IncidentType(str, Enum)`:
  - `RESOURCE_CONTENTION`
  - `NETWORK_FAILOVER_AMBIGUITY`
  - `THERMAL_DRIFT_SPIKE`
  - `BATTERY_DEGRADATION`
  - `MEMORY_PRESSURE_DEADLOCK`
  - `GENERAL_DEADLOCK`
- `AnomalyRiskLevel(str, Enum)`:
  - `LOW`
  - `MEDIUM`
  - `HIGH`
  - `CRITICAL`
- `EvaluatorRequest`:
  - `incident_type: str | IncidentType`
  - `context_data: dict = {}`
  - `suggested_actions: List[str] = []`
  - `priority: Optional[str] = "NORMAL"`
  - `telemetry_snapshot: Optional[dict] = None`
- `EvaluatorDecision`:
  - `decision_id: str`
  - `model_used: str`
  - `selected_action: str`
  - `rationale: str`
  - `confidence_score: float`
  - `fallback_used: bool = False`
  - `timestamp: datetime`
- `AnomalyReport`:
  - `timestamp: datetime`
  - `analysis_window_minutes: int`
  - `model_used: str`
  - `detected_anomalies: List[str]`
  - `thermal_drift_risk: str | AnomalyRiskLevel`
  - `battery_degradation_risk: str | AnomalyRiskLevel`
  - `recommended_optimizations: List[str]`
  - `memory_leak_risk: Optional[str | AnomalyRiskLevel]`
- `BatchAnalyticsResult`:
  - `window_minutes: int`
  - `sample_count: int`
  - `thermal_drift_rates: Dict[str, float]` (deg C / hour)
  - `battery_discharge_rates: Dict[str, float]` (% / hour)
  - `memory_growth_slopes: Dict[str, float]` (GB / hour)
  - `anomalies_detected: List[str]`
  - `risk_assessment: str | AnomalyRiskLevel`
  - `recommended_actions: List[str]`
  - `timestamp: datetime`
- `CloudAIStatus`:
  - `provider_models: List[str]`
  - `is_online: bool`
  - `default_model: str`
  - `total_evaluations: int`
  - `cache_hits: int`
  - `latency_ms: float`
  - `active_escalations: int`

### 2.2 Cloud Routes (`src/server/cloud_routes.py`)
- `POST /api/cloud/evaluate`: Evaluate complex incidents via Gemini/Opus or local fallback.
- `POST /api/cloud/anomalies/batch`: Run deep batch analytics on rolling telemetry window.
- `POST /api/cloud/anomalies`: Backward-compatible batch anomaly endpoint.
- `GET /api/cloud/status`: Health and performance status of Cloud AI subsystem.
- `GET /api/cloud/models`: Available models and capabilities.

### 2.3 Dashboard UI (`frontend/`)
- `frontend/index.html`: Responsive cybernetic HUD with header, KPI strip, 7-node mesh cards, Governor Opt-In controls, Multi-WAN status widget, Fleet Dark Mode controller, and Cloud AI synergy terminal.
- `frontend/static/css/style.css`: Cybernetic glowing borders, glassmorphism cards, pulsating animations, WCAG AAA tokens.
- `frontend/static/js/app.js`: WebSocket client (1Hz `/ws/telemetry`), REST API callers (`/api/governor/opt-in`, `/api/integrations/dark-mode/toggle`, `/api/network/failover/trigger`, `/api/cloud/evaluate`, `/api/cloud/anomalies/batch`), live graph rendering, and reactive HUD updates.

## 3. Verification Criteria
- 100% test pass on `pytest tests/test_m4_cloud_and_ui.py` + full regression suite (Tiers 1-5).
- Zero mock/fake data in production source code.
- Genuine statistical regression for slope and drift computations.
- Clean offline fallback behavior for Cloud AI evaluator.
