"""
multi_wan/dashboard.py - Real-Time Dashboard Web Server & REST API.

Serves an embedded HTML Control Center Web Dashboard on port 5050 and provides REST endpoints:
- GET  /api/stats: Live metrics for active WAN nodes, download/upload speeds, mode, pooled throughput, hardware telemetry, and Local AGI truth audit.
- GET  /api/transports: Real-time Device-to-Device transport channels breakdown (9 methods).
- GET  /api/hardware: Real-time system hardware utilization (CPU, RAM, GPU, NPU, Storage, Network Hardware).
- GET  /api/hardware/device?id=<device_id>: Target device hardware telemetry (apple_m4, google_pixel, samsung_tablet, all_mesh).
- POST /api/transports/toggle: Interactive multi-selection toggle (include/exclude) for online & offline channels.
- POST /api/mode: Switch multiplexing strategy (aggregate, lowest_latency, redundant).
- POST /api/benchmark/run: Execute empirical comparative multi-WAN speedtest.
- POST /api/benchmark/d2d_stress: Execute real-data payload stress test across all device transport channels.
- POST /api/storage/backup: Trigger proactive Google Drive offloading.
- POST /api/pixel/sync: Force sync telemetry with Google Pixel Nano Local AGI (100.73.38.87).

STRICT MANDATE: ZERO SIMULATED DATA. Reports 0.0 Mbps when idle and updates live during active transfers.
Runs strict Local AGI Empirical Truth Audits against RULE 0.1 and RULE 0.
"""

import os
import sys
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional

try:
    from .agi_bridge import LocalAGIBridge
    from .benchmark import BenchmarkRunner
    from .connectivity import DeviceConnectivityOptimizer
    from .discovery import InterfaceTracker
    from .hardware_telemetry import HardwareTelemetryMonitor
    from .pixel_nano import PixelNanoBridge
    from .proxy import BondingProxyServer
    from .storage import StorageManager
    from .genetic_ai import GeneticAIOptimizer
except (ImportError, ValueError):
    from multi_wan.agi_bridge import LocalAGIBridge
    from multi_wan.benchmark import BenchmarkRunner
    from multi_wan.connectivity import DeviceConnectivityOptimizer
    from multi_wan.discovery import InterfaceTracker
    from multi_wan.hardware_telemetry import HardwareTelemetryMonitor
    from multi_wan.pixel_nano import PixelNanoBridge
    from multi_wan.proxy import BondingProxyServer
    from multi_wan.storage import StorageManager
    from multi_wan.genetic_ai import GeneticAIOptimizer

logger = logging.getLogger("multi_wan.dashboard")

EMBEDDED_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lauburu Multi-WAN Aggregation Dashboard</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --accent: #a855f7;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
        }
        h1 {
            font-size: 1.8rem;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-live {
            background: rgba(34, 197, 94, 0.2);
            color: var(--success);
            border: 1px solid var(--success);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }
        .card-title {
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary);
        }
        .card-subtext {
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-top: 4px;
        }
        .progress-bar-bg {
            background: #0f172a;
            border-radius: 6px;
            height: 8px;
            width: 100%;
            overflow: hidden;
            margin-top: 8px;
            border: 1px solid var(--border-color);
        }
        .progress-bar-fill {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 0.3s ease;
        }
        .section-title {
            font-size: 1.25rem;
            margin-bottom: 16px;
            font-weight: 600;
        }
        .controls-panel {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
        }
        .btn-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            border: 1px solid var(--border-color);
            background-color: #0f172a;
            color: var(--text-main);
            transition: all 0.2s ease;
        }
        .btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        .btn.active {
            background-color: var(--primary);
            color: #0f172a;
            border-color: var(--primary);
        }
        .btn-action {
            background: var(--accent);
            color: white;
            border: none;
        }
        .btn-action:hover {
            background: #9333ea;
        }
        .btn-backup {
            background: #059669;
            color: white;
            border: none;
        }
        .btn-backup:hover {
            background: #047857;
        }
        .toggle-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }
        @media (max-width: 768px) {
            .toggle-container { grid-template-columns: 1fr; }
        }
        .toggle-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toggle-pill {
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid var(--border-color);
            background: #0f172a;
            color: var(--text-muted);
            transition: all 0.2s ease;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .toggle-pill.included {
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            border-color: var(--primary);
        }
        .toggle-pill.excluded {
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
            border-color: rgba(239, 68, 68, 0.4);
            text-decoration: line-through;
            opacity: 0.7;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 24px;
        }
        th, td {
            padding: 14px 18px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        th {
            background: #0f172a;
            color: var(--text-muted);
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        .status-badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .status-ACTIVE, .status-CONNECTED { background: rgba(34, 197, 94, 0.2); color: var(--success); }
        .status-DEGRADED { background: rgba(234, 179, 8, 0.2); color: var(--warning); }
        .status-DOWN, .status-DISCONNECTED { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .benchmark-box {
            background: #020617;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            font-family: monospace;
            font-size: 0.875rem;
            color: #38bdf8;
            height: 220px;
            overflow-y: auto;
        }
        .log-entry { margin-bottom: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Lauburu Multi-WAN Aggregation</h1>
            <span class="badge-live">SYSTEM ACTIVE</span>
        </header>

        <div class="grid-stats">
            <div class="card">
                <div class="card-title">Live Download Speed (Rx)</div>
                <div class="card-value" id="stat-download" style="color: var(--success);">0.0 Mbps</div>
                <div class="card-subtext" id="stat-download-mbs">0.00 MB/s</div>
            </div>
            <div class="card">
                <div class="card-title">Live Upload Speed (Tx)</div>
                <div class="card-value" id="stat-upload" style="color: var(--primary);">0.0 Mbps</div>
                <div class="card-subtext" id="stat-upload-mbs">0.00 MB/s</div>
            </div>
            <div class="card">
                <div class="card-title">Active WAN Nodes</div>
                <div class="card-value" id="stat-nodes">0</div>
                <div class="card-subtext" id="stat-transfer-state">IDLE (0 active connections)</div>
            </div>
            <div class="card">
                <div class="card-title">Active Bonding Mode</div>
                <div class="card-value" id="stat-mode" style="font-size: 1.4rem; text-transform: uppercase;">aggregate</div>
                <div class="card-subtext">Multiplexing Strategy</div>
            </div>
            <div class="card">
                <div class="card-title">Local AGI Bridge</div>
                <div class="card-value" id="stat-truth-status" style="font-size: 1.1rem; color: var(--success);">EMPIRICAL_VERIFIED</div>
                <div class="card-subtext" id="stat-truth-details">Mandate: Zero Simulated Data</div>
            </div>
            <div class="card">
                <div class="card-title">Pixel Nano AGI (100.73.38.87)</div>
                <div class="card-value" id="stat-pixel-status" style="font-size: 1.4rem;">DISCONNECTED</div>
                <div class="card-subtext" id="stat-pixel-interface">Mobile: Disconnected | Rules: Verified</div>
            </div>
            <div class="card">
                <div class="card-title">Storage Manager</div>
                <div class="card-value" id="stat-storage-usage" style="font-size: 1.4rem;">OPTIMAL</div>
                <div class="card-subtext">Proactive Cloud Offloading</div>
            </div>
        </div>

        <div class="section-title">🖥️ System Hardware Telemetry & Real-Time Resource Utilization</div>
        <div class="controls-panel" style="margin-bottom: 16px;">
            <div>
                <div class="card-title" style="margin-bottom: 8px;">Select Device Telemetry Node</div>
                <div class="btn-group">
                    <button class="btn active" id="btn-hw-apple_m4" onclick="selectDeviceHardware('apple_m4')">🍏 Apple M4 MacBook Pro</button>
                    <button class="btn" id="btn-hw-iphone" onclick="selectDeviceHardware('iphone')">📱 Apple iPhone 16 Pro Max</button>
                    <button class="btn" id="btn-hw-google_pixel" onclick="selectDeviceHardware('google_pixel')">📱 Google Pixel 10 Pro XL</button>
                    <button class="btn" id="btn-hw-samsung_s20" onclick="selectDeviceHardware('samsung_s20')">📱 Samsung Galaxy S20</button>
                    <button class="btn" id="btn-hw-linux_node" onclick="selectDeviceHardware('linux_node')">🖥️ Linux Distributed Node</button>
                    <button class="btn" id="btn-hw-all_mesh" onclick="selectDeviceHardware('all_mesh')">🌐 All Mesh Devices</button>
                </div>
            </div>
        </div>
        <div class="grid-stats" id="hardware-grid">
            <div class="card">
                <div class="card-title">🤖 AI Running Score</div>
                <div class="card-value" id="hw-ai-score" style="color: var(--accent);">0.0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-ai-bar" style="background: var(--accent);"></div></div>
                <div class="card-subtext" id="hw-ai-rank">Device Ranking System</div>
            </div>
            <div class="card">
                <div class="card-title">💻 CPU Utilization</div>
                <div class="card-value" id="hw-cpu-usage">0.0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-cpu-bar"></div></div>
                <div class="card-subtext" id="hw-cpu-brand">Loading CPU specs...</div>
            </div>
            <div class="card">
                <div class="card-title">🧠 RAM Memory</div>
                <div class="card-value" id="hw-ram-usage">0.0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-ram-bar"></div></div>
                <div class="card-subtext" id="hw-ram-details">0.0 GB / 0.0 GB Used</div>
            </div>
            <div class="card">
                <div class="card-title">🎮 GPU Acceleration</div>
                <div class="card-value" id="hw-gpu-usage">0.0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-gpu-bar" style="background: var(--accent);"></div></div>
                <div class="card-subtext" id="hw-gpu-name">Apple M4 (Metal 4)</div>
            </div>
            <div class="card">
                <div class="card-title">⚡ NPU / Neural Engine</div>
                <div class="card-value" id="hw-npu-usage">0.0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-npu-bar" style="background: var(--warning);"></div></div>
                <div class="card-subtext" id="hw-npu-details">16-Core ANE (38 TOPS)</div>
            </div>
            <div class="card">
                <div class="card-title">💾 Storage Disk I/O</div>
                <div class="card-value" id="hw-storage-io">0.0 MB/s</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="hw-storage-bar" style="background: var(--success);"></div></div>
                <div class="card-subtext" id="hw-storage-details">Read: 0.0 MB/s | Write: 0.0 MB/s</div>
            </div>
        </div>

        <div class="section-title">🌐 Full Network Hardware Telemetry & Adapter Counters</div>
        <table>
            <thead>
                <tr>
                    <th>Interface</th>
                    <th>Hardware Chipset / Driver</th>
                    <th>IP Address</th>
                    <th>MAC Address</th>
                    <th>PHY Speed & MTU</th>
                    <th>Live Tx Speed (Upload)</th>
                    <th>Live Rx Speed (Download)</th>
                    <th>Packets (Tx / Rx)</th>
                    <th>Drops / Errors</th>
                </tr>
            </thead>
            <tbody id="network-hw-table-body">
                <tr><td colspan="9" style="text-align: center;">Loading network hardware adapter telemetry...</td></tr>
            </tbody>
        </table>

        <div class="controls-panel">
            <div>
                <div class="card-title" style="margin-bottom: 8px;">Select Bonding Mode</div>
                <div class="btn-group">
                    <button class="btn active" id="btn-aggregate" onclick="setMode('aggregate')">Aggregate</button>
                    <button class="btn" id="btn-lowest_latency" onclick="setMode('lowest_latency')">Lowest Latency</button>
                    <button class="btn" id="btn-redundant" onclick="setMode('redundant')">Redundant (Race)</button>
                </div>
            </div>
            <div class="btn-group">
                <button class="btn btn-action" style="background: #0284c7;" onclick="triggerPixelSync()">📱 Sync Pixel Nano AGI</button>
                <button class="btn btn-backup" onclick="triggerBackup()">💾 Trigger Proactive Backup</button>
                <button class="btn btn-action" style="background: #10b981;" onclick="enforceConnections()">🔌 Force Connect Mesh</button>
                <button class="btn btn-action" style="background: #eab308; color: #0f172a;" onclick="runD2DStressTest()">🧪 Multi-Device Stress Test</button>
                <button class="btn btn-action" onclick="runBenchmark()">🚀 Run Speedtest</button>
            </div>
        </div>

        <div class="section-title">🎛️ Device Transport Toggle List (Click to Include / Exclude)</div>
        <div class="toggle-container">
            <div class="card">
                <div class="card-title" style="color: var(--accent); font-weight: 700; margin-bottom: 12px;">⚡ Offline Local Transports</div>
                <div class="toggle-group" id="offline-toggle-group">
                    <!-- Rendered dynamically -->
                </div>
            </div>
            <div class="card">
                <div class="card-title" style="color: var(--primary); font-weight: 700; margin-bottom: 12px;">🌐 Online Overlay Transports</div>
                <div class="toggle-group" id="online-toggle-group">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        </div>

        <div class="section-title">Network Interface Topology & Mesh Health</div>
        <table>
            <thead>
                <tr>
                    <th>Interface / Node Name</th>
                    <th>IP Address</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Latency (RTT)</th>
                    <th>Capacity / Est. Throughput</th>
                    <th>Mesh Type</th>
                </tr>
            </thead>
            <tbody id="nodes-table-body">
                <tr><td colspan="7" style="text-align: center;">Loading topology metrics...</td></tr>
            </tbody>
        </table>

        <div class="section-title">Benchmark & System Logs</div>
        <div class="benchmark-box" id="benchmark-log">
            <div class="log-entry">[SYSTEM] Multi-WAN Monitoring Dashboard initialized on port 5050.</div>
        </div>
    </div>

    <script>
        let currentTransports = {};
        let selectedDeviceId = "apple_m4";

        async function fetchStats() {
            try {
                const resp = await fetch('/api/stats');
                const data = await resp.json();
                
                const rxSpeed = data.live_download_speed_mbps !== undefined ? data.live_download_speed_mbps : 0.0;
                const txSpeed = data.live_upload_speed_mbps !== undefined ? data.live_upload_speed_mbps : 0.0;
                const rxMbs = data.live_download_speed_mbs !== undefined ? data.live_download_speed_mbs : 0.0;
                const txMbs = data.live_upload_speed_mbs !== undefined ? data.live_upload_speed_mbs : 0.0;

                document.getElementById('stat-download').innerText = rxSpeed.toFixed(1) + ' Mbps';
                document.getElementById('stat-download-mbs').innerText = rxMbs.toFixed(2) + ' MB/s';
                document.getElementById('stat-upload').innerText = txSpeed.toFixed(1) + ' Mbps';
                document.getElementById('stat-upload-mbs').innerText = txMbs.toFixed(2) + ' MB/s';

                document.getElementById('stat-transfer-state').innerText = data.live_transfer_state || 'IDLE';
                document.getElementById('stat-nodes').innerText = data.active_nodes_count;
                document.getElementById('stat-mode').innerText = data.mode;

                if (data.local_agi_truth_audit) {
                    const audit = data.local_agi_truth_audit;
                    const tStat = document.getElementById('stat-truth-status');
                    if (tStat) {
                        tStat.innerText = audit.status;
                        tStat.style.color = audit.status === 'EMPIRICAL_PROOF_VERIFIED' ? 'var(--success)' : 'var(--danger)';
                    }
                    const tDet = document.getElementById('stat-truth-details');
                    if (tDet) {
                        tDet.innerText = `Audited ${audit.metrics_audited_count} metrics | Discrepancies: ${audit.discrepancies_found}`;
                    }
                }

                if (data.pixel_nano) {
                    const pStat = document.getElementById('stat-pixel-status');
                    if (pStat) {
                        pStat.innerText = data.pixel_nano.pixel_connected ? 'CONNECTED' : 'DISCONNECTED';
                        pStat.style.color = data.pixel_nano.pixel_connected ? 'var(--success)' : 'var(--danger)';
                    }
                    const pIface = document.getElementById('stat-pixel-interface');
                    if (pIface) {
                        const mob = (data.pixel_nano.pixel_metrics && data.pixel_nano.pixel_metrics.mobile_interface_status) || 'Disconnected';
                        const truth = (data.pixel_nano.truth_verification_status && data.pixel_nano.truth_verification_status.verified) ? 'Verified' : 'Pending';
                        pIface.innerText = `Mobile: ${mob} | Rules: ${truth}`;
                    }
                }

                // Fetch selected device hardware telemetry
                fetchDeviceHardware(selectedDeviceId);

                // Render Transports Toggle Lists
                if (data.transports_summary && data.transports_summary.transports) {
                    currentTransports = data.transports_summary.transports;
                    renderTransportToggles(currentTransports);
                }

                // Update active button state
                ['aggregate', 'lowest_latency', 'redundant'].forEach(m => {
                    const btn = document.getElementById('btn-' + m);
                    if (btn) {
                        if (m === data.mode) btn.classList.add('active');
                        else btn.classList.remove('active');
                    }
                });

                // Update table
                const tbody = document.getElementById('nodes-table-body');
                tbody.innerHTML = '';
                data.nodes.forEach(node => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${node.name}</strong></td>
                        <td>${node.ip}</td>
                        <td>${node.type.toUpperCase()}</td>
                        <td><span class="status-badge status-${node.status}">${node.status}</span></td>
                        <td>${node.latency_ms.toFixed(1)} ms</td>
                        <td>${node.throughput_mbps.toFixed(1)} Mbps</td>
                        <td>${node.is_tailscale ? 'Tailscale Peer' : 'Local Egress'}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (e) {
                console.error("Fetch stats error:", e);
            }
        }

        async function fetchDeviceHardware(deviceId) {
            try {
                const resp = await fetch(`/api/hardware/device?id=${deviceId}`);
                const hw = await resp.json();
                renderHardwareGauges(hw);
                if (hw.network_hardware && hw.network_hardware.adapters) {
                    renderNetworkHardwareTable(hw.network_hardware.adapters);
                }
            } catch (e) {
                console.error("Fetch device hardware error:", e);
            }
        }

        function selectDeviceHardware(deviceId) {
            selectedDeviceId = deviceId;
            ['apple_m4', 'iphone', 'google_pixel', 'samsung_s20', 'linux_node', 'all_mesh'].forEach(id => {
                const btn = document.getElementById('btn-hw-' + id);
                if (btn) {
                    if (id === deviceId) btn.classList.add('active');
                    else btn.classList.remove('active');
                }
            });
            fetchDeviceHardware(deviceId);
        }

        function renderHardwareGauges(hw) {
            if (!hw) return;
            if (hw.ai_running_score_percent) {
                document.getElementById('hw-ai-score').innerText = hw.ai_running_score_percent;
                const scoreVal = hw.ai_running_score || 0;
                document.getElementById('hw-ai-bar').style.width = Math.min(100, scoreVal) + '%';
                document.getElementById('hw-ai-rank').innerText = hw.ai_rank || 'Ranking System Active';
            }
            if (hw.cpu) {
                document.getElementById('hw-cpu-usage').innerText = hw.cpu.usage_percent.toFixed(1) + '%';
                document.getElementById('hw-cpu-bar').style.width = Math.min(100, hw.cpu.usage_percent) + '%';
                document.getElementById('hw-cpu-brand').innerText = `${hw.cpu.brand} (${hw.cpu.logical_cores} Cores)`;
            }
            if (hw.ram) {
                document.getElementById('hw-ram-usage').innerText = hw.ram.percent_used.toFixed(1) + '%';
                document.getElementById('hw-ram-bar').style.width = Math.min(100, hw.ram.percent_used) + '%';
                document.getElementById('hw-ram-details').innerText = `${hw.ram.used_gb} GB / ${hw.ram.total_gb} GB Used (${hw.ram.free_gb} GB Free)`;
            }
            if (hw.gpu) {
                document.getElementById('hw-gpu-usage').innerText = hw.gpu.usage_percent.toFixed(1) + '%';
                document.getElementById('hw-gpu-bar').style.width = Math.min(100, hw.gpu.usage_percent) + '%';
                document.getElementById('hw-gpu-name').innerText = `${hw.gpu.name} (${hw.gpu.cores} Cores)`;
            }
            if (hw.npu) {
                document.getElementById('hw-npu-usage').innerText = hw.npu.usage_percent.toFixed(1) + '%';
                document.getElementById('hw-npu-bar').style.width = Math.min(100, hw.npu.usage_percent) + '%';
                document.getElementById('hw-npu-details').innerText = `${hw.npu.name} (${hw.npu.tops_capacity})`;
            }
            if (hw.storage) {
                const totalIo = (hw.storage.read_speed_mbps + hw.storage.write_speed_mbps).toFixed(1);
                document.getElementById('hw-storage-io').innerText = totalIo + ' MB/s';
                document.getElementById('hw-storage-bar').style.width = Math.min(100, hw.storage.percent_used) + '%';
                document.getElementById('hw-storage-details').innerText = `Read: ${hw.storage.read_speed_mbps} MB/s | Write: ${hw.storage.write_speed_mbps} MB/s | ${hw.storage.free_gb} GB Free`;
            }
        }

        function renderNetworkHardwareTable(adapters) {
            const tbody = document.getElementById('network-hw-table-body');
            tbody.innerHTML = '';
            if (!adapters || adapters.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No physical/logical network hardware adapters detected</td></tr>';
                return;
            }

            adapters.forEach(nic => {
                const tr = document.createElement('tr');
                const statusBadge = nic.is_up ? '<span class="status-badge status-CONNECTED">UP</span>' : '<span class="status-badge status-DISCONNECTED">DOWN</span>';
                const txSpeed = nic.tx_speed_mbps > 0 ? `<strong style="color:var(--primary);">${nic.tx_speed_mbps} Mbps</strong>` : '0.0 Mbps';
                const rxSpeed = nic.rx_speed_mbps > 0 ? `<strong style="color:var(--success);">${nic.rx_speed_mbps} Mbps</strong>` : '0.0 Mbps';

                tr.innerHTML = `
                    <td><strong>${nic.interface}</strong> ${statusBadge}</td>
                    <td>${nic.driver_chipset}</td>
                    <td>${nic.ip_address}</td>
                    <td><code>${nic.mac_address}</code></td>
                    <td>${nic.link_speed_mbps > 0 ? nic.link_speed_mbps + ' Mbps' : 'Auto'} (MTU: ${nic.mtu})</td>
                    <td>${txSpeed}</td>
                    <td>${rxSpeed}</td>
                    <td>Tx: ${formatBytes(nic.bytes_sent)} | Rx: ${formatBytes(nic.bytes_recv)}</td>
                    <td>Drops: ${nic.drop_in + nic.drop_out} | Errs: ${nic.err_in + nic.err_out}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function renderTransportToggles(transports) {
            const offlineGroup = document.getElementById('offline-toggle-group');
            const onlineGroup = document.getElementById('online-toggle-group');
            
            let offlineHTML = '';
            let onlineHTML = '';

            Object.values(transports).forEach(t => {
                const isInc = t.enabled !== false;
                const statusIcon = t.status === 'CONNECTED' ? '🟢' : '🔴';
                const pillHTML = `
                    <div class="toggle-pill ${isInc ? 'included' : 'excluded'}" onclick="toggleTransport('${t.key}', ${isInc})">
                        <span>${statusIcon} ${t.name}</span>
                        <span style="font-size: 0.75rem; font-weight: 700;">${isInc ? '✓ INCLUDED' : '✗ EXCLUDED'}</span>
                    </div>
                `;
                if (t.category === 'offline_local') {
                    offlineHTML += pillHTML;
                } else {
                    onlineHTML += pillHTML;
                }
            });

            offlineGroup.innerHTML = offlineHTML || '<em>No offline transports registered</em>';
            onlineGroup.innerHTML = onlineHTML || '<em>No online transports registered</em>';
        }

        async function toggleTransport(key, currentEnabled) {
            const newEnabled = !currentEnabled;
            logMessage(`[TOGGLE] Setting transport '${key}' -> ${newEnabled ? 'INCLUDED' : 'EXCLUDED'}`);
            try {
                const resp = await fetch('/api/transports/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key: key, enabled: newEnabled })
                });
                if (resp.ok) {
                    fetchStats();
                }
            } catch (e) {
                logMessage(`[TOGGLE ERROR] Failed to toggle ${key}: ${e}`);
            }
        }

        async function setMode(mode) {
            try {
                const resp = await fetch('/api/mode', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: mode })
                });
                if (resp.ok) {
                    fetchStats();
                    logMessage(`[MODE] Bonding mode updated to ${mode.toUpperCase()}`);
                }
            } catch (e) {
                console.error("Set mode error:", e);
            }
        }

        async function runD2DStressTest() {
            logMessage("[STRESS TEST] Executing real-data payload transfer across all transport channels...");
            try {
                const resp = await fetch('/api/benchmark/d2d_stress', { method: 'POST' });
                const result = await resp.json();
                if (result.bottleneck_summary) {
                    result.bottleneck_summary.forEach(b => logMessage("[STRESS BOTTLENECK] " + b));
                }
                logMessage(`[STRESS RESULT] Merged Accumulative Throughput: ${result.accumulative_merged_mbps} Mbps across ${result.transports_tested_count} transports`);
                fetchStats();
            } catch (e) {
                logMessage("[STRESS ERROR] Multi-device stress test failed: " + e);
            }
        }

        async function runBenchmark() {
            logMessage("[BENCHMARK] Initiating comparative speedtest...");
            try {
                const resp = await fetch('/api/benchmark/run', { method: 'POST' });
                const result = await resp.json();
                if (result.log) {
                    result.log.forEach(msg => logMessage(msg));
                }
                logMessage(`[BENCHMARK RESULT] Verified Speedup Ratio: ${result.speedup_ratio}x | Pixel Speedup: ${result.pixel_speedup_ratio}x`);
            } catch (e) {
                logMessage("[BENCHMARK ERROR] Failed to complete benchmark run: " + e);
            }
        }

        async function triggerBackup() {
            logMessage("[STORAGE] Triggering proactive backup...");
            try {
                const resp = await fetch('/api/storage/backup', { method: 'POST' });
                const result = await resp.json();
                logMessage(`[STORAGE BACKUP] Status: ${result.status} | Method: ${result.method} | ${result.message}`);
                fetchStats();
            } catch (e) {
                logMessage("[STORAGE ERROR] Proactive backup failed: " + e);
            }
        }

        async function triggerPixelSync() {
            logMessage("[PIXEL] Triggering manual telemetry sync with Pixel Nano AGI (100.73.38.87)...");
            try {
                const resp = await fetch('/api/pixel/sync', { method: 'POST' });
                const result = await resp.json();
                logMessage(`[PIXEL SYNC] Connected: ${result.pixel_connected} | Last Sync: ${result.last_sync_timestamp || 'Never'}`);
                fetchStats();
            } catch (e) {
                logMessage("[PIXEL ERROR] Manual sync failed: " + e);
            }
        }

        async function enforceConnections() {
            logMessage("[ENFORCEMENT] Forcing connection to offline mesh nodes...");
            try {
                const resp = await fetch('/api/transports/connect', { method: 'POST' });
                const result = await resp.json();
                if (result.status === "success") {
                    logMessage("[ENFORCEMENT] Connection attempts dispatched.");
                    fetchStats();
                }
            } catch (e) {
                logMessage("[ENFORCEMENT ERROR] Failed: " + e);
            }
        }

        function logMessage(msg) {
            const box = document.getElementById('benchmark-log');
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        setInterval(fetchStats, 2000);
        fetchStats();
    </script>
</body>
</html>
"""


class DashboardServer:
    """HTTP Monitoring Web Server & API listening on port 5050."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5050,
        proxy_server: Optional[BondingProxyServer] = None,
        tracker: Optional[InterfaceTracker] = None,
        agi_bridge: Optional[LocalAGIBridge] = None,
        storage_manager: Optional[StorageManager] = None,
        pixel_nano: Optional[PixelNanoBridge] = None,
    ):
        self.host = host
        self.port = port
        self.proxy_server = proxy_server
        self.tracker = tracker or (proxy_server.tracker if proxy_server else InterfaceTracker())
        self.agi_bridge = agi_bridge or LocalAGIBridge()
        self.storage_manager = storage_manager or StorageManager(agi_bridge=self.agi_bridge)
        self.pixel_nano = pixel_nano or PixelNanoBridge()
        self.optimizer = DeviceConnectivityOptimizer()
        storage_p = "/Volumes/REAL_SMB_POOL"
        self.hardware_monitor = HardwareTelemetryMonitor(storage_p)
        self.benchmark_runner = BenchmarkRunner(self.proxy_server)
        self.server: Optional[object] = None
        self.genetic_ai = GeneticAIOptimizer()
        self.genetic_ai.start_training()
        self._running = False

    async def start(self) -> object:
        """Starts the HTTP dashboard server."""
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self._running = True
        logger.info(f"DashboardServer listening on {self.host}:{self.port}")
        return self.server

    async def stop(self):
        """Stops the dashboard server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("DashboardServer stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles incoming HTTP API and dashboard requests."""
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            req_str = request_line.decode("utf-8", errors="ignore").strip()
            parts = req_str.split()
            if len(parts) < 2:
                writer.close()
                return

            method, path = parts[0], parts[1]

            headers = {}
            content_length = 0
            while True:
                line_bytes = await reader.readline()
                if line_bytes in (b"\r\n", b"\n", b""):
                    break
                line = line_bytes.decode("utf-8", errors="ignore").strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            if "content-length" in headers:
                try:
                    content_length = int(headers["content-length"])
                except ValueError:
                    content_length = 0

            body_bytes = b""
            if content_length > 0:
                body_bytes = await reader.readexactly(content_length)

            # Route Request
            if path == "/api/stats" and method == "GET":
                await self._handle_get_stats(writer)

            elif path in ("/api/transports", "/api/transports/") and method == "GET":
                await self._handle_get_transports(writer)

            elif path.startswith("/api/hardware") and method == "GET":
                await self._handle_get_hardware(writer, path)

            elif path in ("/api/transports/toggle", "/api/transports/toggle/") and method == "POST":
                await self._handle_post_transports_toggle(writer, body_bytes)

            elif path in ("/api/transports/connect", "/api/transports/connect/") and method == "POST":
                await self._handle_post_transports_connect(writer)

            elif path == "/api/mode" and method == "POST":
                await self._handle_post_mode(writer, body_bytes)

            elif path in ("/api/benchmark/run", "/api/benchmark/run/") and method in ("GET", "POST"):
                await self._handle_run_benchmark(writer)

            elif path in ("/api/benchmark/d2d_stress", "/api/benchmark/d2d_stress/") and method in ("GET", "POST"):
                await self._handle_run_d2d_stress(writer)

            elif path in ("/api/benchmark/offline_swap", "/api/benchmark/offline_swap/") and method in ("GET", "POST"):
                await self._handle_run_offline_swap(writer)

            elif path in ("/api/ports/live", "/api/ports/live/") and method == "GET":
                await self._handle_get_ports_live(writer)

            elif path in ("/api/storage/backup", "/api/storage/backup/") and method == "POST":
                await self._handle_post_storage_backup(writer)

            elif path in ("/api/pixel/sync", "/api/pixel/sync/") and method == "POST":
                await self._handle_post_pixel_sync(writer, body_bytes)

            elif path in ("/api/truth_audit", "/api/truth_audit/") and method in ("GET", "POST"):
                await self._handle_truth_audit(writer, body_bytes)

            elif path in ("/api/full_network_health", "/api/full_network_health/") and method == "GET":
                await self._handle_get_full_network_health(writer)

            elif path in ("/api/auto_scan", "/api/auto_scan/") and method in ("GET", "POST"):
                await self._handle_get_auto_scan(writer)

            elif path in ("/api/telemetry/spikes", "/api/telemetry/spikes/") and method == "GET":
                await self._handle_get_telemetry_spikes(writer)




            elif path in ("/api/ai/training_stream", "/api/ai/training_stream/") and method == "GET":
                await self._handle_get_ai_training_stream(writer)

            elif path in ("/api/ai/leaderboard", "/api/ai/leaderboard/") and method == "GET":
                await self._handle_get_ai_leaderboard(writer)
            elif path in ("/", "/dashboard", "/index.html") and method in ("GET", "HEAD"):
                await self._handle_get_dashboard(writer)

            else:
                await self._send_json(writer, {"error": "Not Found"}, status=404)

        except Exception as e:
            logger.error(f"Dashboard request handling error: {e}")
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_get_stats(self, writer: asyncio.StreamWriter):
        """Returns JSON metrics for active WAN nodes, health/latency/throughput, mode, pooled throughput, AGI bridge, and storage manager."""
        all_nodes = self.tracker.get_all_interfaces()
        active_nodes = [n for n in all_nodes if n.status != "DOWN"]

        active_conns = self.proxy_server.multiplexer.active_connections if self.proxy_server else 0
        is_transferring = active_conns > 0
        total_pooled_tp = sum(n.throughput_mbps for n in active_nodes)
        mode = self.proxy_server.multiplexer.mode if self.proxy_server else "aggregate"

        net_hw = self.hardware_monitor.get_network_hardware_telemetry()
        live_rx = net_hw.get("total_live_rx_mbps", 0.0) if is_transferring else 0.0
        live_tx = net_hw.get("total_live_tx_mbps", 0.0) if is_transferring else 0.0

        proxy_stats = {
            "total_bytes_transferred": self.proxy_server.multiplexer.total_bytes_transferred if self.proxy_server else 0,
            "active_connections": active_conns,
            "total_requests": self.proxy_server.multiplexer.total_requests if self.proxy_server else 0,
        }

        stats_data = {
            "status": "online",
            "mode": mode,
            "live_transfer_state": "ACTIVE_TRANSMISSION" if is_transferring else "IDLE (No active data transfer)",
            "live_download_speed_mbps": live_rx,
            "live_upload_speed_mbps": live_tx,
            "live_download_speed_mbs": round(live_rx / 8.0, 2),
            "live_upload_speed_mbs": round(live_tx / 8.0, 2),
            "live_transfer_speed_mbps": round(live_rx + live_tx, 2) if is_transferring else 0.0,
            "capacity_pooled_throughput_mbps": round(total_pooled_tp, 2),
            "total_pooled_throughput_mbps": round(total_pooled_tp, 2),
            "active_nodes_count": len(active_nodes),
            "nodes": [n.to_dict() for n in all_nodes],
            "proxy_stats": proxy_stats,
            "transports_summary": self.optimizer.get_accumulative_summary(),
            "hardware": self.hardware_monitor.get_full_telemetry(),
            "agi_bridge": self.agi_bridge.get_status(),
            "storage_status": self.storage_manager.get_metrics(),
            "pixel_nano": self.pixel_nano.get_status(),
            "service_keepalive_24_7": self.keepalive_mgr.get_status_summary() if hasattr(self, "keepalive_mgr") and self.keepalive_mgr else {
                "24_7_system_status": "ACTIVE" if (self.tracker and len(self.tracker.get_active_interfaces()) > 0) else "UNINITIALIZED",
                "online_services": len(self.tracker.get_active_interfaces()) if self.tracker else 0,
                "total_services": len(self.tracker.get_all_interfaces()) if self.tracker else 0,
            },
        }

        loop = asyncio.get_event_loop()
        truth_audit = await loop.run_in_executor(None, self.agi_bridge.run_truth_audit, stats_data)
        stats_data["local_agi_truth_audit"] = truth_audit

        await self._send_json(writer, stats_data)

    async def _handle_get_transports(self, writer: asyncio.StreamWriter):
        """Returns JSON transport methods breakdown for device-to-device connectivity optimization."""
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(None, self.optimizer.get_accumulative_summary)
        await self._send_json(writer, summary)

    async def _handle_get_hardware(self, writer: asyncio.StreamWriter, path: str):
        """Returns detailed real-time hardware & network adapter telemetry for a selected device (apple_m4, google_pixel, samsung_tablet, all_mesh)."""
        device_id = "apple_m4"
        if "?" in path:
            query_str = path.split("?", 1)[1]
            for param in query_str.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    if k.lower() in ("id", "device_id", "device"):
                        device_id = v.strip()

        telemetry = self.hardware_monitor.get_device_telemetry(device_id)
        await self._send_json(writer, telemetry)

    async def _handle_post_transports_toggle(self, writer: asyncio.StreamWriter, body_bytes: bytes):
        """Toggles inclusion/exclusion of specific transport methods (multi-selection supported)."""
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            if "enabled_transports" in data:
                self.optimizer.set_enabled_transports(data["enabled_transports"])
            elif "key" in data and "enabled" in data:
                self.optimizer.set_transport_enabled(data["key"], bool(data["enabled"]))

            summary = self.optimizer.get_accumulative_summary()
            await self._send_json(writer, {"status": "success", "summary": summary})
        except Exception as e:
            logger.error(f"Error toggling transports: {e}")
            await self._send_json(writer, {"error": str(e)}, status=400)

    async def _handle_post_transports_connect(self, writer: asyncio.StreamWriter):
        """Forces connections for disconnected transports."""
        try:
            self.optimizer.enforce_connections()
            summary = self.optimizer.get_accumulative_summary()
            await self._send_json(writer, {"status": "success", "summary": summary})
        except Exception as e:
            logger.error(f"Error enforcing connections: {e}")
            await self._send_json(writer, {"error": str(e)}, status=500)

    async def _handle_run_d2d_stress(self, writer: asyncio.StreamWriter):
        """Executes real-data device transport stress test across all device transport channels."""
        res = await self.benchmark_runner.run_device_mesh_stress_test()
        await self._send_json(writer, res)

    async def _handle_run_offline_swap(self, writer: asyncio.StreamWriter):
        """Executes real-data payload swap with non-Tailscale offline local devices."""
        res = await self.benchmark_runner.run_offline_device_data_swap()
        await self._send_json(writer, res)

    async def _handle_post_mode(self, writer: asyncio.StreamWriter, body_bytes: bytes):
        """Updates active bonding mode (aggregate, lowest_latency, redundant)."""
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            new_mode = data.get("mode")
            if new_mode in ("aggregate", "lowest_latency", "redundant"):
                if self.proxy_server:
                    self.proxy_server.multiplexer.set_mode(new_mode)
                if self.agi_bridge:
                    self.agi_bridge.enqueue_network_event("BONDING_MODE_CHANGED", {"new_mode": new_mode})
                await self._send_json(writer, {"status": "success", "mode": new_mode})
            else:
                await self._send_json(writer, {"error": f"Invalid mode '{new_mode}'"}, status=400)
        except Exception as e:
            await self._send_json(writer, {"error": str(e)}, status=400)

    async def _handle_run_benchmark(self, writer: asyncio.StreamWriter):
        """Executes comparative benchmark runner."""
        try:
            result = await self.benchmark_runner.run_benchmark()
            if self.agi_bridge:
                self.agi_bridge.enqueue_network_event("SPEEDTEST_COMPLETED", result)
            await self._send_json(writer, result)
        except Exception as e:
            await self._send_json(writer, {"status": "error", "message": str(e)}, status=500)

    async def _handle_post_storage_backup(self, writer: asyncio.StreamWriter):
        """Triggers proactive storage backup on demand."""
        try:
            result = self.storage_manager.trigger_proactive_backup()
            await self._send_json(writer, result)
        except Exception as e:
            await self._send_json(writer, {"status": "error", "message": str(e)}, status=500)

    async def _handle_get_ports_live(self, writer: asyncio.StreamWriter):
        """Scans live active listening ports across all mesh nodes."""
        now = time.time()
        cached_data = getattr(self.tracker, "_cached_scanned_data", None) if self.tracker else None
        if (
            isinstance(cached_data, dict)
            and "timestamp" in cached_data
            and (now - cached_data["timestamp"]) < 2.0
        ):
            ports_data = cached_data
        else:
            if hasattr(self.tracker, "scan_live_ports_async"):
                ports_data = await self.tracker.scan_live_ports_async()
            elif hasattr(self.tracker, "async_scan_live_ports"):
                ports_data = await self.tracker.async_scan_live_ports()
            else:
                ports_data = self.tracker.scan_live_ports()

        if isinstance(ports_data, dict):
            if "status" not in ports_data:
                ports_data["status"] = "ok"
            if "timestamp" not in ports_data:
                ports_data["timestamp"] = time.time()
            if "nodes" not in ports_data:
                nodes_list = []
                registry = ports_data.get("live_port_registry", {})
                for name, info in registry.items():
                    nodes_list.append({"name": name, "ip": info.get("ip", "")})
                ports_data["nodes"] = nodes_list
            if "ports" not in ports_data:
                ports_map = {}
                registry = ports_data.get("live_port_registry", {})
                for name, info in registry.items():
                    ports_map[name] = info.get("open_ports", [])
                ports_data["ports"] = ports_map

        await self._send_json(writer, ports_data)

    async def _handle_post_pixel_sync(self, writer: asyncio.StreamWriter, body_bytes: bytes):
        """Triggers manual telemetry sync with Pixel Nano Local AGI."""
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            wan_metrics = data.get("wan_metrics")
            speedtest_results = data.get("speedtest_results")

            if wan_metrics is None:
                all_nodes = self.tracker.get_all_interfaces()
                active_nodes = [n for n in all_nodes if n.status != "DOWN"]
                wan_metrics = {
                    "total_pooled_throughput_mbps": round(sum(n.throughput_mbps for n in active_nodes), 2),
                    "active_nodes_count": len(active_nodes),
                    "active_paths": [n.name for n in active_nodes],
                    "latency_ms": round(sum(n.latency_ms for n in active_nodes) / max(len(active_nodes), 1), 2),
                }

            if hasattr(self.pixel_nano, "async_sync_telemetry"):
                sync_res = await self.pixel_nano.async_sync_telemetry(
                    wan_metrics=wan_metrics,
                    speedtest_results=speedtest_results,
                )
            else:
                loop = asyncio.get_running_loop()
                sync_res = await loop.run_in_executor(
                    None,
                    lambda: self.pixel_nano.sync_telemetry(
                        wan_metrics=wan_metrics,
                        speedtest_results=speedtest_results,
                    ),
                )
            status_dict = self.pixel_nano.get_status()
            status_dict["sync_result"] = sync_res
            await self._send_json(writer, status_dict)
        except Exception as e:
            logger.error(f"Pixel Nano sync error: {e}")
            await self._send_json(writer, {"status": "error", "message": str(e)}, status=500)

    async def _handle_truth_audit(self, writer: asyncio.StreamWriter, body_bytes: bytes = b""):
        """Runs Dual Local AI vs Paid Cloud AI Truth Audit loop and returns JSON result."""
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        except Exception:
            payload = None
        def _run_truth_audit_sync(p):
            from .hybrid_mesh import HybridMeshOrchestrator
            orchestrator = HybridMeshOrchestrator()
            return orchestrator.run_truth_audit(p)

        loop = asyncio.get_event_loop()
        audit_res = await loop.run_in_executor(None, _run_truth_audit_sync, payload)
        await self._send_json(writer, audit_res)

    async def _handle_get_full_network_health(self, writer: asyncio.StreamWriter):
        """Returns full network mesh health status (strictly HEALTHY only if all devices & ports connected)."""
        if hasattr(self, "keepalive_mgr") and self.keepalive_mgr:
            loop = asyncio.get_event_loop()
            health_data = await loop.run_in_executor(None, self.keepalive_mgr.probe_full_network_mesh)
        else:
            all_nodes = self.tracker.get_all_interfaces() if self.tracker else []
            active_nodes = [n for n in all_nodes if n.status == "ACTIVE"]
            total_count = len(all_nodes)
            active_count = len(active_nodes)
            all_connected = (active_count == total_count and total_count > 0)
            missing = [n.name for n in all_nodes if n.status != "ACTIVE"]
            status_str = "HEALTHY" if all_connected else ("DEGRADED" if active_count > 0 else ("UNINITIALIZED" if total_count == 0 else "OFFLINE"))
            health_data = {
                "overall_mesh_status": status_str,
                "all_nodes_connected": all_connected,
                "total_nodes": total_count,
                "connected_nodes_count": active_count,
                "missing_nodes": missing,
                "missing_ports": [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        await self._send_json(writer, health_data)

    async def _handle_get_auto_scan(self, writer: asyncio.StreamWriter):
        """Triggers live autonomous AI service port scan and returns discovered endpoints."""
        from .dynamic_port_scanner import DynamicPortScanner
        scanner = DynamicPortScanner()
        loop = asyncio.get_event_loop()
        scan_data = await loop.run_in_executor(None, scanner.scan_all)
        await self._send_json(writer, scan_data)


    async def _handle_get_ai_training_stream(self, writer: asyncio.StreamWriter):
        logs = self.genetic_ai.get_logs()
        await self._send_json(writer, logs)

    async def _handle_get_ai_leaderboard(self, writer: asyncio.StreamWriter):
        leaderboard = self.genetic_ai.get_leaderboard()
        await self._send_json(writer, leaderboard)


    async def _handle_get_telemetry_spikes(self, writer: asyncio.StreamWriter):
        """Returns live timestamped hardware telemetry spikes correlated with Local AI claims."""
        corr_file = "/Volumes/Lauburu-Monorepo/session_logs/ai_hardware_correlations.json"
        data = []
        if os.path.exists(corr_file):
            try:
                with open(corr_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        await self._send_json(writer, {
            "status": "SUCCESS",
            "total_correlated_events": len(data),
            "events": data[-25:]
        })

    async def _handle_get_dashboard(self, writer: asyncio.StreamWriter):
        """Serves embedded single-page HTML web dashboard."""
        html_bytes = EMBEDDED_DASHBOARD_HTML.encode("utf-8")
        hdr = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(hdr.encode("utf-8") + html_bytes)
        await writer.drain()
        writer.close()

    async def _send_json(self, writer: asyncio.StreamWriter, data: dict, status: int = 200):
        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        status_text = "OK" if status == 200 else ("Not Found" if status == 404 else "Bad Request")
        hdr = (
            f"HTTP/1.1 {status} {status_text}\r\n"
            f"Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(json_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(hdr.encode("utf-8") + json_bytes)
        await writer.drain()
        writer.close()

async def main():
    server = DashboardServer(host="0.0.0.0", port=5050)
    await server.start()
    print("🚀 Lauburu Multi-WAN Aggregation Dashboard running on http://0.0.0.0:5050")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
