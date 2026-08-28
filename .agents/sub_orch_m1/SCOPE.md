# Milestone 1 Scope & Work Breakdown Structure

## Objective
Implement the complete Mesh Telemetry & Deep Analytics Engine within `teamwork_projects/compute_pooling_app`.

## Component Deliverables

### 1. `src/telemetry/models.py`
- Pydantic v2 data models for node metrics and mesh snapshots:
  - `NodeMetrics`: `node_id`, `hostname`, `ip_address`, `layer` (1-7), `role`, `is_online`, `latency_ms`, `cpu_percent`, `ram_used_gb`, `ram_total_gb`, `ram_percent`, `vram_used_gb`, `vram_total_gb`, `thermal_celsius`, `battery_percent`, `is_charging`, `network_interface`, `last_updated`.
  - `MeshTelemetrySnapshot`: `timestamp`, `active_node_count`, `total_mesh_ram_gb`, `total_mesh_vram_gb`, `nodes: Dict[str, NodeMetrics]`.
  - `TelemetryAggregate`: statistical aggregations (min, max, mean, std, percentiles) over specified time windows.
  - `BatchTelemetryExport`: export structure designed for Gemini Pro 3.1 & Claude Opus 4.6 anomaly detection.

### 2. `src/telemetry/collector.py`
- `MeshTelemetryCollector`:
  - 1Hz polling scheduler across 7 physical mesh layers:
    - Layer 1: `Mac_Node` (M4 Mac Mini Host)
    - Layer 2: `MacBook_Pro` (M1 Max Vault)
    - Layer 3: `Linux_Head_Node` (AMD Ryzen 7 5700U)
    - Layer 4: `Linux_Tablet` (Debian Linux Tablet)
    - Layer 5: `Mac_Mini` (Mac Mini Compute Node)
    - Layer 6: `Pixel_10_Pro_XL` (Google Tensor G5)
    - Layer 7: `Samsung_S20` (Samsung Galaxy S20+)
  - Probing logic:
    - Local host: `psutil` real-time RAM, CPU, thermals (via `psutil.sensors_temperatures()` / `powermetrics` / `smc`), battery status (`psutil.sensors_battery()`).
    - Remote nodes: async socket latency probe (TCP connect to SSH/RPC/HTTP ports), RPC ping, and active status tracking with graceful offline fallback.
  - Periodic background collection loop with listener callback registration.

### 3. `src/telemetry/ring_buffer.py`
- `TelemetryRingBuffer`:
  - In-memory time-series circular buffer with configurable capacity (default 3600 entries for 1 hour at 1Hz).
  - Thread-safe / async-safe lock-protected operations.
  - Methods:
    - `append(snapshot: MeshTelemetrySnapshot)`
    - `get_latest() -> Optional[MeshTelemetrySnapshot]`
    - `get_history(window_seconds: int = 600) -> List[MeshTelemetrySnapshot]`
    - `get_node_history(node_id: str, window_seconds: int = 600) -> List[NodeMetrics]`
    - `get_aggregated_metrics(window_seconds: int = 600) -> TelemetryAggregate`
    - `export_batch_for_ai(window_minutes: int = 10) -> Dict[str, Any]`

### 4. `src/server/app.py` & `src/server/routes.py`
- FastAPI server running on Port 4000:
  - REST Endpoints:
    - `GET /api/health` -> Server status, uptime, buffer count.
    - `GET /api/telemetry/current` -> Latest `MeshTelemetrySnapshot`.
    - `GET /api/telemetry/nodes` -> List of all 7 node statuses.
    - `GET /api/telemetry/nodes/{node_id}` -> Specific node metrics and history.
    - `GET /api/telemetry/history?window_seconds=600` -> Rolling history.
    - `GET /api/telemetry/aggregate?window_seconds=600` -> Aggregated statistics.
    - `GET /api/telemetry/export?window_minutes=10` -> Batch export for cloud AI.
  - WebSocket Streaming:
    - `WS /ws/telemetry` -> Real-time 1Hz stream of snapshots to connected clients with auto-reconnect handling and client management.
  - Lifespan context manager to start/stop collector daemon cleanly.

### 5. `tests/test_m1_telemetry.py` & `tests/tier1_features/test_telemetry.py`
- Comprehensive test suite covering:
  - Schema validation, serialization/deserialization.
  - Ring buffer capacity, circular overwrite, time-window queries, statistical aggregations.
  - Collector 1Hz polling, local host metrics extraction, remote node probing, socket fallbacks.
  - FastAPI REST API endpoints, response models, HTTP error handling.
  - WebSocket client connection, real-time message broadcasting, disconnection handling.
  - Batch export format verification for AI anomaly detection.
