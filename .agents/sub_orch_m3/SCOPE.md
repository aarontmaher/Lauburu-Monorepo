# Milestone 3 Scope & Execution Plan: Multi-WAN Resilience & Fleet Dark Mode Integrations

## Scope Breakdown

### 1. Network Data Models (`src/network/models.py`)
- `NetworkTransport` (Enum): `Thunderbolt4`, `10GbE`, `WiFi_7`, `Tailscale`
- `TransportHealth` (BaseModel): Existing health metrics (is_available, rtt_ms, ewma_rtt_ms, packet_loss_percent, bandwidth_gbps, priority, last_probe_time)
- `NetworkRoute` (BaseModel): route_id, transport, interface_name, gateway, metric, is_active, bandwidth_gbps, mtu, ewma_rtt_ms
- `LatencyMetric` (BaseModel): transport, timestamp, measured_rtt_ms, ewma_rtt_ms, jitter_ms, packet_loss_percent
- `FailoverEvent` (BaseModel): timestamp, previous_transport, active_transport, trigger_reason, failover_latency_ms, packet_loss_percent
- `BondStatus` (BaseModel): is_bonded, bonded_transports, primary_transport, aggregate_bandwidth_gbps, active_routes, last_rebalanced

### 2. Multi-WAN Health Monitor & Bonding (`src/network/multiwan_monitor.py`)
- Continuous probe tracking and EWMA RTT smoothing with configurable `alpha` (default 0.2).
- Composite bandwidth & quality scoring: `score = (bandwidth_gbps * 10) / (ewma_rtt_ms * (1 + packet_loss/10))`.
- Multi-path bonding calculation: `get_bonding_status() -> BondStatus` aggregating available interfaces.
- Structured route listing: `get_network_routes() -> List[NetworkRoute]`.
- Latency history and jitter tracking: `get_latency_metrics() -> List[LatencyMetric]`.

### 3. Sub-50ms Predictive Failover & Circuit Breaker (`src/network/failover_manager.py`)
- Predictive circuit breaker with state tracking (CLOSED, OPEN, HALF_OPEN).
- Sub-50ms failover execution upon link drops, packet loss >= 20%, or latency > 100ms.
- Fallback cascade: Thunderbolt 4 -> 10GbE -> Wi-Fi 7 -> Tailscale WireGuard.
- Automatic recovery / fallback when higher priority links become healthy.
- Observer listener registration for real-time notification.

### 4. Integrations Data Models (`src/integrations/models.py`)
- `ThemeMode` (Enum): `dark`, `light`, `auto`
- `PlatformThemeStatus` (BaseModel): platform, is_dark, applied_at, status_message
- `FleetThemeState` (BaseModel): mode, is_dark_active, contrast_ratio, platforms, last_updated
- `DarkModeState` (BaseModel): Alias/subclass of `FleetThemeState` with theme tokens and WCAG AAA compliance ratio.
- `DeviceAppearance` (BaseModel): node_id, platform, os_version, dark_mode_enabled, sync_command, contrast_ratio, last_synced
- `PowerStatus` (BaseModel): node_id, battery_percent, is_charging, thermal_celsius, power_saving_active, timestamp
- `WatchdogTrigger` (BaseModel): trigger_id, node_id, timestamp, trigger_type, battery_percent, thermal_celsius, action_taken, throttle_applied, dark_mode_forced
- `PowerTriggerEvent` (BaseModel): backward compatibility model.

### 5. Universal Fleet Dark Mode Sync (`src/integrations/dark_mode_sync.py`)
- Multi-OS command generators:
  - macOS: `osascript -e 'tell app "System Events" to tell appearance preferences to set dark mode to true'`
  - Linux: `gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'`
  - Android: `adb shell "cmd uimode night yes"`
  - Web: WCAG AAA compliant tokens with contrast ratio >= 7.0:1
- `get_platform_command(platform: str, is_dark: bool) -> str`
- `apply_platform_sync(platform: str, is_dark: bool, execute: bool = False) -> PlatformThemeStatus`
- Fleet-wide state synchronization and observer dispatch.

### 6. Autonomous Power & Thermal Watchdog (`src/integrations/power_watchdog.py`)
- Battery discharge thresholds: `<= 20%` (Low Battery -> Dark Mode & Light Throttling), `<= 5%` (Critical -> Emergency Suspend).
- Thermal threshold: `>= 85.0C` (Thermal Spike -> Dark Mode & Light Throttling).
- Safe handling of charging status (bypasses battery low triggers when charging).
- Returns both `WatchdogTrigger` and `PowerTriggerEvent`.

### 7. FastAPI Integration Endpoints (`src/server/network_routes.py`, `src/server/integration_routes.py`, `src/server/routes.py`)
- `/api/network/routes` (GET): active routes, bonding status, transports.
- `/api/network/failover` (GET/POST): evaluate or manual failover.
- `/api/network/transports` (GET): transport health metrics.
- `/api/network/active-route` (GET): active transport and latest failover event.
- `/api/network/probe` (POST): probe injection.
- `/api/network/inject-failure` (POST): simulate drop.
- `/api/network/restore-transport` (POST): restore link.
- `/api/integrations/dark-mode` (GET/POST): theme state and mode switch.
- `/api/integrations/dark-mode/toggle` (POST): toggle dark/light mode.
- `/api/integrations/power/evaluate` (POST): evaluate power/thermal telemetry.
- `/api/integrations/power-watchdog` (GET): watchdog trigger history and device power states.

### 8. Milestone 3 Verification Suite (`tests/test_m3_network_integrations.py`)
- Comprehensive suite testing all models, bonding, scoring, circuit breaker, failover timing, cross-platform dark mode commands, WCAG AAA tokens, power watchdog thresholds, and REST endpoints.
