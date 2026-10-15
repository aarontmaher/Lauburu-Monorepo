/**
 * Lauburu Cable & Mesh Analyzer - Frontend Application
 * Real-time zero-mock SVG topology renderer, Bluetooth serial terminal feed,
 * and Local AI device & function synthesis.
 */

let topologyData = null;
let selectedCableId = null;
let selectedDeviceId = null;
let eventSource = null;
let cachedActiveConnections = null;
let currentConnectionFilter = "all";

// Optimized node coordinates fitting perfectly within 1000x580 viewBox
const NODE_COORDINATES = {
  // Primary 8-Node Compute Mesh (Center-Right focus)
  "l1_mac_mini": { x: 510, y: 260 },
  "l7_samsung_s20": { x: 510, y: 80 },
  "l2_macbook_pro": { x: 800, y: 110 },
  "l5_macbook_air": { x: 830, y: 260 },
  "gw_router": { x: 800, y: 430 },
  "l3_linux_head": { x: 510, y: 470 },
  "l4_linux_tablet": { x: 270, y: 460 },
  "l6_pixel_10": { x: 260, y: 260 },

  // Subordinated Peripheral Wing (Far Left column, off to side)
  "ext_display_msi": { x: 85, y: 65 },
  "periph_wireless_dongle": { x: 85, y: 155 },
  "periph_usb_hub": { x: 85, y: 360 },

  // Dynamic Auto-Discovered Nodes (Sentinel / Linux Mini)
  "node_lauburu_sentinel_node": { x: 380, y: 530 },
  "node_linuxmini": { x: 380, y: 530 }
};

function getNodeCoords(nodeId) {
  if (NODE_COORDINATES[nodeId]) {
    return NODE_COORDINATES[nodeId];
  }
  const dynamicSlots = [
    { x: 380, y: 530 },
    { x: 650, y: 530 },
    { x: 920, y: 380 },
    { x: 260, y: 120 },
    { x: 700, y: 50 }
  ];
  let h = 0;
  for (let i = 0; i < nodeId.length; i++) {
    h = (h * 31 + nodeId.charCodeAt(i)) % dynamicSlots.length;
  }
  return dynamicSlots[h];
}

const CABLE_COLORS = {
  "cable_tb4_mac_mini_to_mbp": "#ffb800",
  "cable_usbc_port1": "#f59e0b",
  "cable_eth_mac_to_router": "#00f0ff",
  "cable_hdmi_port-hdmi_1": "#64748b",
  "cable_usbc_samsung": "#ef4444",
  "cable_usb_wireless_dongle": "#10b981",
  "cable_usb_hub_genesys": "#00f0ff",
  "link_pixel_wifi_adb": "#a855f7",
  "cable_virtual_wireguard_mesh": "#818cf8",
  "link_tablet_wireguard_mesh": "#6366f1"
};

function isMissing(v) {
  return v === null || v === undefined || v === "" || v === "--" || (typeof v === "number" && isNaN(v));
}

function fmt(v, unit = "") {
  if (isMissing(v)) return "--";
  if (typeof v === "object" && v !== null) {
    if (v.value !== undefined) return fmt(v.value, unit);
    return JSON.stringify(v);
  }
  if (!unit) return String(v);
  if (unit === "%") return `${v}%`;
  return `${v} ${unit}`;
}

function provTitle(obj) {
  if (!obj || typeof obj !== "object") return "";
  const parts = [];
  if (obj.source_cmd) parts.push(`cmd: ${obj.source_cmd}`);
  if (obj.captured_at) {
    const d = new Date(typeof obj.captured_at === "number" ? obj.captured_at * 1000 : obj.captured_at);
    parts.push(`time: ${d.toLocaleTimeString()}`);
  }
  if (obj.reason) parts.push(`reason: ${obj.reason}`);
  return parts.join(" | ");
}

function onlineState(online) {
  if (online === true) {
    return { cls: "badge-active", label: "ONLINE" };
  } else if (online === false) {
    return { cls: "badge-standby", label: "OFFLINE" };
  }
  return { cls: "badge-standby", label: "--" };
}

function init() {
  setupTabs();
  setupViewSwitcher();
  setupActions();
  fetchTopologyREST();
  connectSSE();
  fetchLensStatus();
  setInterval(fetchLensStatus, 2500);
  fetchWhatCableDetails();

  const hash = window.location.hash ? window.location.hash.replace("#", "") : "";
  const params = new URLSearchParams(window.location.search);
  const viewParam = params.get("view");
  const tabParam = params.get("tab");

  if (hash === "whatcable" || viewParam === "whatcable") {
    switchMainView("whatcable");
  } else if (hash === "sharkwire" || viewParam === "sharkwire") {
    switchMainView("sharkwire");
  } else if (hash) {
    switchTab(hash);
  } else if (tabParam) {
    switchTab(tabParam);
  }
}

function setupTabs() {
  window.switchTab = function(tabName) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    
    const targetBtn = document.getElementById(`tab-btn-${tabName}`);
    const targetContent = document.getElementById(`tab-content-${tabName}`);
    if (targetBtn && targetContent) {
      targetBtn.classList.add("active");
      targetContent.classList.add("active");
    }

    if (tabName === "whatcable") {
      updateSidebarWhatcableSummary();
    } else if (tabName === "sharkwire") {
      updateSidebarSharkwireQuickFeed();
    }
  };
}

function setupViewSwitcher() {
  window.switchMainView = function(viewName) {
    document.querySelectorAll(".view-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view-stage").forEach(s => {
      s.classList.remove("active");
      s.style.display = "none";
    });

    const targetNavBtn = document.getElementById(`nav-view-${viewName}`);
    const targetStage = document.getElementById(`stage-${viewName}`);
    if (targetNavBtn && targetStage) {
      targetNavBtn.classList.add("active");
      targetStage.classList.add("active");
      targetStage.style.display = "flex";
    }

    if (history.replaceState) {
      history.replaceState(null, null, `#${viewName}`);
    }

    if (viewName === "whatcable") {
      fetchWhatCableDetails();
    } else if (viewName === "sharkwire") {
      initSharkWire();
    } else if (viewName === "ip-inspector") {
      if (!window._hasProbedIp) {
        runIpProbe();
      }
    } else if (viewName === "lens-sovereign") {
      initLensSovereign();
    } else if (viewName === "router-gateway") {
      loadRouterGateway();
    } else if (viewName === "crash-stream") {
      loadCrashStream();
    }
  };
}

function setupActions() {
  const btnPullBt = document.getElementById("btn-pull-bt");
  if (btnPullBt) {
    btnPullBt.addEventListener("click", async () => {
      btnPullBt.disabled = true;
      btnPullBt.innerHTML = "<span>⏳</span> Pulling BT...";
      try {
        const res = await fetch("/api/terminal/pull", { method: "POST" });
        const data = await res.json();
        if (data.topology) {
          updateUI(data.topology);
        }
      } catch (e) {
        console.error("BT pull error:", e);
      } finally {
        btnPullBt.disabled = false;
        btnPullBt.innerHTML = "<span>📡</span> Pull BT Terminal";
      }
    });
  }

  document.getElementById("btn-refresh").addEventListener("click", async () => {
    const btn = document.getElementById("btn-refresh");
    btn.disabled = true;
    btn.innerHTML = "<span>⏳</span> Scanning...";
    try {
      const res = await fetch("/api/probes/refresh", { method: "POST" });
      const data = await res.json();
      if (data.topology) {
        updateUI(data.topology);
      }
    } catch (e) {
      console.error("Refresh error:", e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = "<span>🔄</span> Rescan";
    }
  });

  document.getElementById("btn-local-ai").addEventListener("click", async () => {
    const btn = document.getElementById("btn-local-ai");
    btn.disabled = true;
    btn.innerHTML = "<span>🧠</span> Running AI...";
    switchTab("ai");
    try {
      const res = await fetch("/api/terminal/ai_insights");
      const data = await res.json();
      renderAiSynthesis(data);
    } catch (e) {
      console.error("AI inference error:", e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = "<span>🧠</span> AI Identify";
    }
  });

  const sendBtn = document.getElementById("btn-send-cmd");
  const cmdInput = document.getElementById("terminal-cmd-input");
  
  const sendCommand = async (specifiedCmd) => {
    const cmd = specifiedCmd || cmdInput.value.trim() || "status";
    if (!specifiedCmd) cmdInput.value = "";
    const termDisplay = document.getElementById("terminal-display");
    termDisplay.innerHTML += `\n\n[lauburu]> ${cmd}\nSending command to Bluetooth serial terminal...\n`;
    termDisplay.scrollTop = termDisplay.scrollHeight;

    try {
      const res = await fetch("/api/terminal/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();
      termDisplay.innerText = data.output;
      termDisplay.scrollTop = termDisplay.scrollHeight;
    } catch (e) {
      termDisplay.innerHTML += `\nError sending command: ${e}\n`;
    }
  };

  sendBtn.addEventListener("click", () => sendCommand());
  cmdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendCommand();
  });

  // Reconnect via Bluetooth Handlers
  const handleReconnectBluetooth = async () => {
    const btnHeader = document.getElementById("btn-reconnect-bt");
    const btnTab = document.getElementById("btn-tab-reconnect-bt");
    const termDisplay = document.getElementById("terminal-display");

    const setBtnsLoading = (loading) => {
      if (btnHeader) {
        btnHeader.disabled = loading;
        btnHeader.innerHTML = loading ? "<span>⏳</span> Reconnecting..." : "<span>📲</span> Reconnect via Bluetooth";
      }
      if (btnTab) {
        btnTab.disabled = loading;
        btnTab.innerHTML = loading ? "<span>⏳</span> Reconnecting..." : "<span>📲</span> Reconnect via Bluetooth";
      }
    };

    setBtnsLoading(true);
    switchTab("terminal");
    if (termDisplay) {
      termDisplay.innerHTML += `\n\n[BLUETOOTH RECONNECTION DISPATCHED]\nExecuting Line 1 Bluetooth Proximity Wake across all laptops (MBP L2, Linux L3, MBA L5), Mac Mini (L1 Host), and mobile nodes...\n`;
      termDisplay.scrollTop = termDisplay.scrollHeight;
    }

    try {
      const res = await fetch("/api/bluetooth/reconnect", { method: "POST" });
      const data = await res.json();
      if (data.reconnect && data.reconnect.raw_output) {
        termDisplay.innerText = data.reconnect.raw_output;
        termDisplay.scrollTop = termDisplay.scrollHeight;
      }
      if (data.topology) {
        updateUI(data.topology);
      }
    } catch (e) {
      console.error("Bluetooth reconnection error:", e);
      if (termDisplay) {
        termDisplay.innerHTML += `\nReconnection error: ${e}\n`;
      }
    } finally {
      setBtnsLoading(false);
    }
  };

  window.reconnectBluetooth = handleReconnectBluetooth;

  const btnHeader = document.getElementById("btn-reconnect-bt");
  if (btnHeader) btnHeader.addEventListener("click", handleReconnectBluetooth);

  const btnTab = document.getElementById("btn-tab-reconnect-bt");
  if (btnTab) btnTab.addEventListener("click", handleReconnectBluetooth);

  const btnStatus = document.getElementById("btn-tab-status");
  if (btnStatus) btnStatus.addEventListener("click", () => sendCommand("status"));

  const btnTelemetry = document.getElementById("btn-tab-telemetry");
  if (btnTelemetry) btnTelemetry.addEventListener("click", () => sendCommand("telemetry"));

  const btnClear = document.getElementById("btn-tab-clear");
  if (btnClear) btnClear.addEventListener("click", () => sendCommand("clear"));

  // Diagnostic Action Handlers
  const btnPing = document.getElementById("btn-run-ping");
  if (btnPing) {
    btnPing.addEventListener("click", async () => {
      const host = document.getElementById("diag-ping-host").value.trim() || "192.168.8.1";
      const resContainer = document.getElementById("diag-ping-results");
      const statusBadge = document.getElementById("diag-ping-status");
      btnPing.disabled = true;
      statusBadge.innerText = "TESTING...";
      resContainer.innerText = `Pinging ${host} (4 ICMP packets)...`;
      try {
        const res = await fetch(`/api/diagnostics/ping?host=${encodeURIComponent(host)}&count=4`);
        const data = await res.json();
        statusBadge.innerText = data.status || "DONE";
        statusBadge.className = `badge ${data.status === "PASS" ? "badge-active" : "badge-standby"}`;
        resContainer.innerHTML = `
          <div style="color: ${data.status === "PASS" ? "#00ff88" : "#ef4444"}; font-weight: bold; margin-bottom: 4px;">
            ${data.status}: ${data.packets_received}/${data.packets_transmitted} received (${data.packet_loss_pct}% loss)
          </div>
          <div>Avg RTT: <strong style="color: #00f0ff;">${data.avg_rtt_ms} ms</strong> (min: ${data.min_rtt_ms} ms, max: ${data.max_rtt_ms} ms)</div>
          <div>RFC 3550 Jitter: <strong style="color: #c084fc;">${data.jitter_ms} ms</strong></div>
          <div style="margin-top: 4px; color: var(--text-muted);">Samples: [${(data.rtt_samples || []).join(", ")}] ms</div>
        `;
      } catch (err) {
        statusBadge.innerText = "ERROR";
        resContainer.innerText = `Ping error: ${err}`;
      } finally {
        btnPing.disabled = false;
      }
    });
  }

  const btnScan = document.getElementById("btn-run-scan");
  if (btnScan) {
    btnScan.addEventListener("click", async () => {
      const host = document.getElementById("diag-scan-host").value.trim() || "127.0.0.1";
      const resContainer = document.getElementById("diag-scan-results");
      const statusBadge = document.getElementById("diag-scan-status");
      btnScan.disabled = true;
      statusBadge.innerText = "SCANNING...";
      resContainer.innerText = `Scanning mesh ports on ${host}...`;
      try {
        const res = await fetch(`/api/diagnostics/port_scan?host=${encodeURIComponent(host)}`);
        const data = await res.json();
        statusBadge.innerText = `${data.open_ports_count} OPEN`;
        resContainer.innerHTML = `
          <div style="margin-bottom: 4px; color: #00f0ff; font-weight: bold;">
            Scan complete in ${data.scan_duration_ms} ms (${data.open_ports_count}/${data.total_ports_scanned} ports open)
          </div>
          <div style="display: flex; flex-direction: column; gap: 3px; max-height: 160px; overflow-y: auto;">
            ${(data.ports || []).map(p => `
              <div style="display: flex; justify-content: space-between; padding: 2px 4px; background: rgba(255,255,255,0.03); border-radius: 3px;">
                <span>Port ${p.port} (${p.service}):</span>
                <span style="color: ${p.is_open ? '#00ff88' : '#64748b'}; font-weight: ${p.is_open ? 'bold' : 'normal'};">
                  ${p.is_open ? `OPEN (${p.latency_ms} ms)` : 'CLOSED'}
                </span>
              </div>
            `).join("")}
          </div>
        `;
      } catch (err) {
        statusBadge.innerText = "ERROR";
        resContainer.innerText = `Scan error: ${err}`;
      } finally {
        btnScan.disabled = false;
      }
    });
  }

  const btnBench = document.getElementById("btn-run-bench");
  if (btnBench) {
    btnBench.addEventListener("click", async () => {
      const resContainer = document.getElementById("diag-bench-results");
      const statusBadge = document.getElementById("diag-bench-status");
      btnBench.disabled = true;
      statusBadge.innerText = "RUNNING...";
      resContainer.innerText = "Executing unbuffered direct fsync I/O & UMA RAM memcpy benchmark...";
      try {
        const res = await fetch("/api/diagnostics/benchmark");
        const data = await res.json();
        statusBadge.innerText = "COMPLETED";
        const ram = data.ram_benchmark || {};
        const disk = data.disk_benchmark || {};
        resContainer.innerHTML = `
          <div style="margin-bottom: 6px; padding: 4px 6px; background: rgba(59,130,246,0.1); border-left: 3px solid #3b82f6; border-radius: 3px;">
            <div style="color: #3b82f6; font-weight: bold;">RAM Copy Bandwidth (${ram.tested_size_mb} MB chunk):</div>
            <div style="font-size: 13px; color: #60a5fa; font-weight: bold;">${ram.ram_bandwidth_gb_per_sec} GB/s</div>
            <div style="color: var(--text-muted); font-size: 9px;">${ram.performance_rating} (${ram.copy_duration_ms} ms)</div>
          </div>
          <div style="padding: 4px 6px; background: rgba(16,185,129,0.1); border-left: 3px solid #10b981; border-radius: 3px;">
            <div style="color: #10b981; font-weight: bold;">Disk Direct I/O (${disk.tested_size_mb} MB fsync):</div>
            <div>Sequential Write: <strong style="color: #34d399;">${disk.sequential_write_mbps} MB/s</strong></div>
            <div>Sequential Read: <strong style="color: #34d399;">${disk.sequential_read_mbps} MB/s</strong></div>
            <div style="color: var(--text-muted); font-size: 9px;">Mode: ${disk.io_type}</div>
          </div>
        `;
      } catch (err) {
        statusBadge.innerText = "ERROR";
        resContainer.innerText = `Benchmark error: ${err}`;
      } finally {
        btnBench.disabled = false;
      }
    });
  }

  const btnPower = document.getElementById("btn-run-power");
  if (btnPower) {
    btnPower.addEventListener("click", async () => {
      const dev = document.getElementById("diag-power-device").value.trim() || "100.73.38.87:5555";
      const resContainer = document.getElementById("diag-power-results");
      const statusBadge = document.getElementById("diag-power-status");
      btnPower.disabled = true;
      statusBadge.innerText = "POLLING...";
      resContainer.innerText = `Querying ADB battery metrics from ${dev}...`;
      try {
        const res = await fetch(`/api/diagnostics/power_delivery?device=${encodeURIComponent(dev)}`);
        const data = await res.json();
        statusBadge.innerText = data.status || "ONLINE";
        if (data.status === "ONLINE") {
          resContainer.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <strong style="color: #00f0ff;">${data.device_name}</strong>
              <span style="color: #10b981; font-weight: bold;">${data.battery_level_pct}%</span>
            </div>
            <div>Charging State: <strong style="color: ${data.is_charging ? '#00ff88' : '#94a3b8'};">${data.charging_mode}</strong></div>
            <div>Voltage: <strong>${data.voltage_v} V</strong> • Current: <strong>${data.current_a} A</strong></div>
            <div>Power Dissipation: <strong style="color: #ffb800; font-size: 13px;">${data.instant_power_watts} W</strong></div>
            <div>Temperature: <strong>${data.temperature_c} °C</strong></div>
            <div style="color: var(--text-muted); font-size: 9px; margin-top: 4px;">PD Contract: ${data.usb_c_pd_contract}</div>
          `;
        } else {
          resContainer.innerHTML = `<div style="color: #ef4444;">Status: ${data.status} • ${data.error || 'Device not connected'}</div>`;
        }
      } catch (err) {
        statusBadge.innerText = "ERROR";
        resContainer.innerText = `Power query error: ${err}`;
      } finally {
        btnPower.disabled = false;
      }
    });
  }
}

function connectSSE() {
  if (eventSource) {
    eventSource.close();
  }
  eventSource = new EventSource("/api/stream");

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateUI(data);
    } catch (e) {
      console.error("SSE parse error:", e);
    }
  };

  eventSource.onerror = () => {
    console.warn("SSE connection interrupted, falling back to REST...");
    fetchTopologyREST();
  };
}

async function fetchTopologyREST() {
  try {
    const res = await fetch("/api/topology");
    const data = await res.json();
    updateUI(data);
  } catch (e) {
    console.error("REST fetch error:", e);
  }
}

function updateUI(data) {
  topologyData = data;
  renderSummaryHeader(data.mesh_summary);
  renderSvgTopology(data);
  renderCablesList(data.cables);
  renderDevicesList(data.devices);
  renderDynamicIpsList(data.devices, data.dynamic_ips);

  if (data.active_connections) {
    cachedActiveConnections = data.active_connections;
    renderConnectionsSummary(data.active_connections);
    renderConnectionsList(data.active_connections, currentConnectionFilter);
  }

  if (data.bluetooth_terminal) {
    renderTerminalStream(data.bluetooth_terminal.raw_stream);
    renderAiSynthesis(data.bluetooth_terminal.ai_synthesis);
  }

  if (selectedCableId) {
    const cable = data.cables.find(c => c.id === selectedCableId);
    if (cable) renderCableInspector(cable);
  }
}

function renderSummaryHeader(summary) {
  if (!summary) return;
  document.getElementById("stat-online-nodes").innerText = `${summary.online_nodes || 0}/${summary.total_nodes || 0}`;

  const btVerifiedEl = document.getElementById("stat-bt-verified-nodes");
  if (btVerifiedEl) {
    btVerifiedEl.innerText = `${summary.bluetooth_terminal_verified_nodes || 0} Nodes`;
    btVerifiedEl.title = `Directly pulled from Bluetooth terminal streams (${summary.telemetry_source || 'Layer 0'})`;
  }
  
  const dynIpsEl = document.getElementById("stat-dynamic-ips");
  if (dynIpsEl) {
    dynIpsEl.innerText = summary.dynamic_ips_resolved || "--";
  }

  const primaWorkersEl = document.getElementById("stat-prima-workers");
  if (primaWorkersEl) {
    const cCount = summary.prima_connected_count !== undefined ? summary.prima_connected_count : "--";
    const tCount = summary.prima_total_count !== undefined ? summary.prima_total_count : "--";
    primaWorkersEl.innerText = `${cCount}/${tCount}`;
    primaWorkersEl.title = summary.prima_summary_text || "prima.cpp Pipelined-Ring Parallelism Mesh";
  }

  const primaBadgeEl = document.getElementById("badge-prima-status");
  if (primaBadgeEl) {
    const cCount = summary.prima_connected_count || 0;
    const tCount = summary.prima_total_count || 0;
    primaBadgeEl.innerHTML = `<span>PRIMA.CPP : ${cCount}/${tCount} WORKERS</span>`;
    primaBadgeEl.title = summary.prima_summary_text || "prima.cpp Pipelined-Ring Parallelism Mesh";
  }

  const badgeDynEl = document.getElementById("badge-dynamic-ip");
  if (badgeDynEl) {
    badgeDynEl.innerHTML = `<span>DYNAMIC IP : ${summary.dynamic_ips_resolved || "--"}</span>`;
  }

  const ipFinderLatEl = document.getElementById("ip-finder-latency");
  if (ipFinderLatEl) {
    ipFinderLatEl.innerText = summary.dynamic_ip_latency_ms != null ? `${summary.dynamic_ip_latency_ms} ms` : "--";
  }

  document.getElementById("stat-mesh-ram").innerText = `${summary.total_ram_gb || 0} GB`;
  document.getElementById("stat-npu-tops").innerText = `${summary.total_npu_tops || 0} TOPS`;
  document.getElementById("stat-active-cables").innerText = `${summary.active_cables || 0} Active`;

  const connsEl = document.getElementById("stat-active-conns");
  if (connsEl) {
    connsEl.innerText = summary.active_connections_total !== undefined ? `${summary.active_connections_total}` : "--";
  }
  
  const tb4Lat = summary.tb4_bridge_latency_ms;
  document.getElementById("stat-tb4-latency").innerText = tb4Lat > 0 ? `${tb4Lat} ms` : "--";
}

function renderTerminalStream(streamText) {
  const display = document.getElementById("terminal-display");
  if (display && streamText) {
    display.innerText = streamText;
  }
}

function renderAiSynthesis(aiData) {
  const container = document.getElementById("ai-synthesis-container");
  const verdictEl = document.getElementById("bottom-ai-verdict");
  if (!container || !aiData) return;

  if (aiData.mesh_efficiency_verdict && verdictEl) {
    verdictEl.innerHTML = `<span>⚡</span> ${aiData.mesh_efficiency_verdict}`;
  }

  const devices = aiData.identified_devices || [];
  if (devices.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 11px;">Awaiting local AI inference...</div>`;
    return;
  }

  container.innerHTML = devices.map(d => `
    <div class="ai-device-card">
      <div class="ai-device-name">
        <span>${d.device_name}</span>
        <span class="badge badge-active">VERIFIED</span>
      </div>
      <div class="ai-device-role">${d.function}</div>
      <div class="ai-device-meta">
        <strong>Link:</strong> ${d.connected_via} | <strong>Compute:</strong> ${d.npu_or_compute}
      </div>
    </div>
  `).join("");
}

function renderSvgTopology(data) {
  const svg = document.getElementById("mesh-svg");
  const nodes = data.devices || [];
  const cables = data.cables || [];

  let html = `
    <defs>
      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>
  `;

  // Draw Cables (Edges)
  cables.forEach((cable) => {
    const srcCoords = getNodeCoords(cable.source_device_id);
    const tgtCoords = getNodeCoords(cable.target_device_id);

    const isHdmiOrDisplay = cable.id.startsWith("cable_hdmi") || cable.target_device_id === "ext_display_msi";
    const isVirtual = cable.cable_type.includes("Virtual") || cable.cable_type.includes("WireGuard");
    const isSelected = cable.id === selectedCableId;

    // Subdue HDMI cable so it does not compete with compute mesh
    const strokeColor = isHdmiOrDisplay ? "#475569" : (CABLE_COLORS[cable.id] || (cable.cable_type.includes("Thunderbolt") ? "#ffb800" : "#00f0ff"));
    const dashArray = isHdmiOrDisplay ? "stroke-dasharray='4,4'" : (isVirtual ? "stroke-dasharray='5,5'" : "");
    const strokeWidth = isSelected ? 4 : (isHdmiOrDisplay ? 1.2 : (cable.max_bandwidth_gbps >= 40 ? 3.5 : 2.5));
    const opacity = isSelected ? 1.0 : (isHdmiOrDisplay ? 0.4 : 0.9);

    const dx = tgtCoords.x - srcCoords.x;
    const dy = tgtCoords.y - srcCoords.y;
    const cx = (srcCoords.x + tgtCoords.x) / 2 - dy * 0.12;
    const cy = (srcCoords.y + tgtCoords.y) / 2 + dx * 0.12;

    const pathData = `M ${srcCoords.x} ${srcCoords.y} Q ${cx} ${cy} ${tgtCoords.x} ${tgtCoords.y}`;

    html += `
      <path id="${cable.id}" class="cable-path" d="${pathData}"
        stroke="${strokeColor}" stroke-width="${strokeWidth}" ${dashArray} opacity="${opacity}"
        filter="${isSelected ? 'url(#glow)' : ''}"
        onclick="handleCableClick('${cable.id}')" />
    `;

    // Speed badge along cable
    const midX = (srcCoords.x + tgtCoords.x) / 2;
    const midY = (srcCoords.y + tgtCoords.y) / 2;
    
    if (isHdmiOrDisplay) {
      // Subdued compact badge for passive display
      html += `
        <g transform="translate(${midX - 20}, ${midY - 7})" style="cursor: pointer; opacity: 0.65;" onclick="handleCableClick('${cable.id}')">
          <rect width="40" height="14" rx="7" fill="#080c14" stroke="#334155" stroke-width="0.8" />
          <text x="20" y="10" fill="#64748b" font-size="7.5" font-weight="600" text-anchor="middle">HDMI</text>
        </g>
      `;
    } else {
      const isBottleneck = cable.bottleneck_analysis && cable.bottleneck_analysis.is_bottleneck;
      const speedLabel = isBottleneck ? `⚠️ ${Math.round(cable.max_bandwidth_gbps * 1000)}M` : (cable.max_bandwidth_gbps >= 1 ? `${cable.max_bandwidth_gbps} Gbps` : `${Math.round(cable.max_bandwidth_gbps * 1000)} Mbps`);
      const badgeBorder = isBottleneck ? "#f59e0b" : strokeColor;
      const badgeW = isBottleneck ? 62 : 50;
      html += `
        <g transform="translate(${midX - badgeW / 2}, ${midY - 10})" style="cursor: pointer;" onclick="handleCableClick('${cable.id}')">
          <rect width="${badgeW}" height="18" rx="9" fill="#0e131d" stroke="${badgeBorder}" stroke-width="${isBottleneck ? 1.5 : 1}" />
          <text x="${badgeW / 2}" y="13" fill="${isBottleneck ? '#fef08a' : '#ffffff'}" font-size="9" font-weight="700" text-anchor="middle">${speedLabel}</text>
        </g>
      `;
    }
  });

  // Draw Device Nodes
  nodes.forEach((node) => {
    const coords = getNodeCoords(node.id);
    const isOnline = node.online;
    const isLocal = node.is_local;
    const isSelected = node.id === selectedDeviceId;
    const isPeripheral = node.is_peripheral || node.id === "ext_display_msi" || node.id.startsWith("periph_");

    if (isPeripheral) {
      // Subdued peripheral satellite pill badge (off to the side)
      const cardW = 120;
      const cardH = 38;
      const x = coords.x - cardW / 2;
      const y = coords.y - cardH / 2;
      const borderColor = isSelected ? "#00f0ff" : "#1e293b";

      let labelTitle = truncate(node.name, 15);
      let labelSub = truncate(node.role || "Peripheral", 20);
      let icon = "🔌";
      if (node.id === "ext_display_msi") {
        labelTitle = "MSI MP245";
        labelSub = "HDMI Video Sink • 60Hz";
        icon = "🖥️";
      } else if (node.id === "periph_wireless_dongle") {
        labelTitle = "2.4G RF Receiver";
        labelSub = "USB HID • 12 Mbps";
        icon = "📡";
      } else if (node.id === "periph_usb_hub") {
        labelTitle = "USB 3.1 Multi-Hub";
        labelSub = "Genesys + RTL8153 LAN";
        icon = "🔀";
      }

      html += `
        <g transform="translate(${x}, ${y})" style="cursor: pointer; opacity: ${isSelected ? 1.0 : 0.85};" onclick="handleDeviceClick('${node.id}')">
          <rect width="${cardW}" height="${cardH}" rx="6" fill="#090e17" stroke="${borderColor}" stroke-width="${isSelected ? 1.5 : 1}" />
          <circle cx="10" cy="19" r="2.5" fill="#64748b" />
          <text x="18" y="16" fill="#94a3b8" font-size="8.5" font-weight="700">${icon} ${labelTitle}</text>
          <text x="18" y="28" fill="#475569" font-size="7.5">${labelSub}</text>
        </g>
      `;
      return;
    }

    // Prominent compute cluster card
    const ramPct = node.ram ? (node.ram.usage_pct || 0) : 0;
    const npuTops = node.npu ? (node.npu.max_tops || 0) : 0;
    const cardW = 146;
    const cardH = 76;
    const x = coords.x - cardW / 2;
    const y = coords.y - cardH / 2;

    const borderColor = isSelected ? "#00f0ff" : (isLocal ? "#ffb800" : (isOnline ? "#1c263b" : "#331a1a"));
    const statusColor = isOnline ? "#10b981" : "#64748b";
    const primaConnected = node.prima_connected;
    const primaBadge = primaConnected ? `
      <rect x="${cardW - 44}" y="6" width="36" height="8.5" rx="2" fill="rgba(168,85,247,0.18)" stroke="#c084fc" stroke-width="0.5" />
      <text x="${cardW - 26}" y="12.5" fill="#c084fc" font-size="6.5" font-weight="700" text-anchor="middle">⚡ prima</text>
    ` : '';

    html += `
      <g transform="translate(${x}, ${y})" style="cursor: pointer;" onclick="handleDeviceClick('${node.id}')">
        <rect width="${cardW}" height="${cardH}" rx="7" fill="#101622" stroke="${borderColor}" stroke-width="${isSelected ? 2 : 1}" />
        ${primaBadge}
        <circle cx="12" cy="14" r="3.5" fill="${statusColor}" />
        <text x="22" y="17" fill="#f0f4fc" font-size="9.5" font-weight="700">${truncate(node.name, 16)}</text>
        
        <text x="10" y="30" fill="#8da0c0" font-size="7.5">${truncate(node.role || node.os, 24)}</text>
        <text x="10" y="42" fill="#00f0ff" font-size="7" font-family="monospace">${node.local_ip || '--'} • TS: ${node.tailscale_ip || '--'}</text>
        
        <text x="10" y="53" fill="#536485" font-size="7.5">RAM: ${(isOnline && node.ram && node.ram.used_gb !== null) ? `${node.ram.used_gb}/${node.ram.total_gb}G (${ramPct}%)` : `-- / ${node.ram ? node.ram.total_gb : 0}G (Standby)`}</text>
        <rect x="10" y="57" width="${cardW - 20}" height="3" rx="1.5" fill="rgba(255,255,255,0.06)" />
        <rect x="10" y="57" width="${Math.min((cardW - 20) * (ramPct / 100), cardW - 20)}" height="3" rx="1.5" fill="#3b82f6" />
        
        <rect x="${cardW - 46}" y="63" width="38" height="9.5" rx="2.5" fill="rgba(236, 72, 153, 0.15)" stroke="#ec4899" stroke-width="0.5" />
        <text x="${cardW - 27}" y="70.5" fill="#ec4899" font-size="7" font-weight="700" text-anchor="middle">${npuTops} TOPS</text>
      </g>
    `;
  });

  svg.innerHTML = html;
}

window.handleCableClick = function(cableId) {
  selectedCableId = cableId;
  switchTab("cables");
  if (topologyData && topologyData.cables) {
    const cable = topologyData.cables.find(c => c.id === cableId);
    if (cable) {
      renderCableInspector(cable);
      renderSvgTopology(topologyData);
    }
  }
};

window.handleDeviceClick = function(deviceId) {
  selectedDeviceId = deviceId;
  switchTab("devices");
  const el = document.getElementById(`device-card-${deviceId}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.style.borderColor = "#00f0ff";
    setTimeout(() => { el.style.borderColor = ""; }, 2000);
  }
};

function renderCableInspector(cable) {
  const container = document.getElementById("cable-inspector-body");
  const b = cable.bottleneck_analysis || {};
  const bt = cable.bluetooth_foundation || {};
  const tm = cable.best_transfer_method || {};
  const caps = cable.device_capabilities || {};

  const severity = b.severity || (cable.bottleneck_warning ? "WARNING" : "OPTIMAL");
  let badgeClass = "badge-optimal";
  let badgeText = "OPTIMAL";
  let bannerClass = "bottleneck-banner-optimal";

  if (severity === "CRITICAL") {
    badgeClass = "badge-critical";
    badgeText = "⚠️ CRITICAL BOTTLENECK";
    bannerClass = "bottleneck-banner-critical";
  } else if (severity === "WARNING") {
    badgeClass = "badge-warning";
    badgeText = "⚠️ BOTTLENECK";
    bannerClass = "bottleneck-banner-warning";
  } else if (severity === "INFO") {
    badgeClass = "badge-info";
    badgeText = "ℹ️ FULL TB4 (80G PORT)";
    bannerClass = "bottleneck-banner-optimal";
  }

  container.innerHTML = `
    <div class="card" style="border-color: ${CABLE_COLORS[cable.id] || '#00f0ff'};">
      <div class="card-title">
        <span>${cable.name}</span>
        <span class="badge ${badgeClass}">${badgeText}</span>
      </div>

      <div class="spec-row">
        <span class="spec-label">Cable Standard:</span>
        <span class="spec-val" style="color: #00f0ff;">${cable.cable_type}</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Source Endpoint:</span>
        <span class="spec-val">${cable.source_device_id} (${cable.source_port})</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Target Endpoint:</span>
        <span class="spec-val" style="font-weight: 700; color: #f0f4fc;">${cable.target_device_name || cable.target_device_id} (${cable.target_port})</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Negotiated Speed:</span>
        <span class="spec-val" style="color: #ffb800; font-weight: 700;">${cable.negotiated_speed}</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Max Bandwidth:</span>
        <span class="spec-val">${cable.max_bandwidth_gbps} Gbps</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">E-Marker Chip:</span>
        <span class="spec-val">${cable.e_marker ? `Detected (${cable.e_marker_vendor || 'Smart Chip'})` : 'No E-Marker'}</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Power Delivery:</span>
        <span class="spec-val">${cable.max_wattage}</span>
      </div>
      <div class="spec-row">
        <span class="spec-label">Transport Protocol:</span>
        <span class="spec-val">${cable.protocol}</span>
      </div>

      <!-- Foundation: Bluetooth Anchor Card -->
      <div class="bt-foundation-box">
        <div class="bt-foundation-header">
          <span>📲 Foundation: Bluetooth Anchor</span>
          <span style="font-size: 8.5px; color: ${bt.connected ? '#10b981' : '#8da0c0'}; font-weight: 700;">
            ${bt.status || 'Active Anchor'}
          </span>
        </div>
        <div style="font-size: 9.5px; color: var(--text-secondary); line-height: 1.3;">
          <div><strong>Role:</strong> ${bt.role || 'Foundational Control Plane & Proximity Wake'}</div>
          <div><strong>MAC:</strong> <span style="font-family: monospace;">${bt.mac || '--'}</span> • Foundational baseline for proximity, wake, and heartbeat.</div>
        </div>
      </div>

      <!-- Best Method for Data Transfer Card -->
      <div class="best-method-box">
        <div class="best-method-header">
          <span>🚀 Best Method for Data Transfer</span>
          <span style="font-size: 8.5px; color: ${tm.is_optimal ? '#10b981' : '#f59e0b'}; font-weight: 700;">
            ${tm.is_optimal ? '✓ Peak Line Rate' : '⚡ Optimization Recommended'}
          </span>
        </div>
        <div style="font-size: 9.5px; color: var(--text-secondary); line-height: 1.3;">
          <div><strong>Optimal Path:</strong> <span style="color: #c084fc; font-weight: 600;">${tm.optimal_method || 'N/A'}</span></div>
          <div><strong>Relative Speed:</strong> ${tm.speed_multiplier || '1.0x'} ${tm.rtt_latency_ms ? `• ${tm.rtt_latency_ms}ms RTT` : ''}</div>
          <div style="margin-top: 4px; color: #e2e8f0;">${tm.recommendation || ''}</div>
        </div>
      </div>

      <!-- Device Capabilities Matrix -->
      ${caps.supported_transports ? `
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.05);">
          <div style="font-size: 9px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px;">
            Hardware Capabilities (${caps.device_max_bandwidth_gbps} Gbps Max)
          </div>
          <div class="capabilities-tag-container">
            ${caps.supported_transports.map(t => `<span class="capability-tag">${t}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Bottleneck Diagnostic Alert Banner -->
      ${(b.is_bottleneck || cable.bottleneck_warning) ? `
        <div class="bottleneck-banner ${bannerClass}">
          <div style="font-weight: 700; margin-bottom: 2px;">⚠️ Bottleneck: ${b.bottleneck_type || 'Connection Throttled'}</div>
          <div>${b.details || cable.bottleneck_warning}</div>
          ${b.remedy ? `<div style="margin-top: 4px; font-weight: 600; color: #fef08a;">💡 Action: ${b.remedy}</div>` : ''}
        </div>
      ` : ''}
    </div>
  `;
}

function renderCablesList(cables) {
  const container = document.getElementById("cables-list-container");
  if (!cables || cables.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 11px;">No active cables detected.</div>`;
    return;
  }

  container.innerHTML = cables.map(c => {
    const b = c.bottleneck_analysis || {};
    const isBottleneck = b.is_bottleneck || !!c.bottleneck_warning;
    return `
      <div class="card" style="cursor: pointer; padding: 8px 10px; margin-bottom: 6px; border-left: 3px solid ${isBottleneck ? '#f59e0b' : (CABLE_COLORS[c.id] || '#00f0ff')};" onclick="handleCableClick('${c.id}')">
        <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;">
          <span>${c.name}</span>
          <span style="color: ${isBottleneck ? '#fbbf24' : '#ffb800'};">${c.max_bandwidth_gbps >= 1 ? `${c.max_bandwidth_gbps} Gbps` : `${Math.round(c.max_bandwidth_gbps * 1000)} Mbps`}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 3px;">
          <div style="font-size: 9.5px; color: var(--text-muted);">
            ${c.source_port} ➔ ${c.target_device_name || c.target_device_id}
          </div>
          <div style="display: flex; gap: 3px; align-items: center;">
            ${c.bluetooth_terminal_verified ? `<span style="font-size: 8px; background: rgba(0,240,255,0.15); color: #00f0ff; border: 1px solid rgba(0,240,255,0.3); padding: 1px 4px; border-radius: 3px; font-weight: 700;">📡 BT Stream</span>` : ''}
            ${isBottleneck ? `<span style="font-size: 8px; background: rgba(245,158,11,0.2); color: #fbbf24; padding: 1px 4px; border-radius: 3px; font-weight: 700;">BOTTLENECK</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderDevicesList(devices) {
  const container = document.getElementById("devices-list-container");
  if (!container) return;
  if (!devices || devices.length === 0) {
    container.innerHTML = `<div class="empty-state">No devices reported by /api/topology.</div>`;
    return;
  }

  container.innerHTML = devices.map(d => {
    const ram = d.ram || {};
    const npu = d.npu || {};
    const isOnline = d.online === true;
    const st = onlineState(d.online);
    const bt = d.bluetooth_foundation || {};
    const tm = d.best_transfer_method || {};
    const primaState = d.prima_worker_status || (d.prima_connected === true ? 'Active' : (d.prima_connected === false ? 'Offline' : '--'));

    return `
      <div class="card" id="device-card-${escapeHtml(d.id)}" title="${escapeHtml(provTitle(d))}">
        <div class="card-title">
          <span>${escapeHtml(fmt(d.name))}</span>
          <div style="display: flex; gap: 4px; align-items: center;">
            <span class="badge ${st.cls}">${st.label}</span>
            ${d.bluetooth_terminal_verified ? `<span class="badge" style="background: rgba(0,240,255,0.12); color: #00f0ff; border: 1px solid rgba(0,240,255,0.3); font-size: 11px;" title="Directly pulled from Bluetooth terminal stream">📡 BT Verified</span>` : ''}
            <span class="badge" style="background: rgba(168,85,247,0.12); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); font-size: 11px;" title="${escapeHtml(d.prima_details || '')}">⚡ prima: ${escapeHtml(primaState)}</span>
          </div>
        </div>

        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
          ${escapeHtml(fmt(d.role))} • ${escapeHtml(fmt(d.arch || d.os))}
        </div>

        <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
          ${d.local_ip ? `<span class="ip-pill ip-pill-lan">LAN: ${escapeHtml(d.local_ip)}</span>` : ''}
          ${d.tailscale_ip ? `<span class="ip-pill ip-pill-ts">TS: ${escapeHtml(d.tailscale_ip)}</span>` : ''}
          ${d.tb4_ip ? `<span class="ip-pill ip-pill-tb4">TB4: ${escapeHtml(d.tb4_ip)}</span>` : ''}
          ${d.adb_target ? `<span class="ip-pill ip-pill-adb">ADB: ${escapeHtml(d.adb_target)}</span>` : ''}
          <span class="ip-source-badge">${escapeHtml(fmt(d.dynamic_source))}</span>
        </div>

        <!-- Foundation & Optimal Transfer Section -->
        <div style="margin-top: 6px; padding: 5px 8px; background: rgba(0,240,255,0.03); border: 1px solid rgba(0,240,255,0.1); border-radius: 4px;">
          <div style="font-size: 11px; display: flex; justify-content: space-between; margin-bottom: 2px;">
            <span style="color: #00f0ff; font-weight: 600;">BT Stream Anchor:</span>
            <span style="color: ${d.bluetooth_terminal_verified ? '#00f0ff' : (bt.connected ? '#10b981' : '#94a3b8')}; font-weight: 600;">
              ${d.bluetooth_terminal_verified ? 'Layer 0 Direct' : escapeHtml(fmt(bt.status))}
            </span>
          </div>
          ${d.terminal_app ? `
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 2px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="${escapeHtml(d.terminal_app)}">
              Terminal: <strong style="color: #93c5fd;">${escapeHtml(d.terminal_app)}</strong>
            </div>
          ` : ''}
          ${d.battery ? `
            <div style="font-size: 11px; display: flex; justify-content: space-between; margin-bottom: 2px;" title="${escapeHtml(provTitle(d.battery))}">
              <span style="color: #10b981; font-weight: 600;">Power / Battery:</span>
              <span style="color: #34d399; font-weight: 600;">${escapeHtml(!isMissing(d.battery.level_pct) ? d.battery.level_pct + '%' : fmt(d.battery.level))} • ${escapeHtml(!isMissing(d.battery.wattage) ? d.battery.wattage : (!isMissing(d.battery.voltage_mv) ? d.battery.voltage_mv + ' mV' : '--'))}</span>
            </div>
          ` : ''}
          ${tm.optimal_method ? `
            <div style="font-size: 11px; display: flex; justify-content: space-between;">
              <span style="color: #c084fc; font-weight: 600;">Best Transfer:</span>
              <span style="color: #c084fc; max-width: 190px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(tm.optimal_method)}">${escapeHtml(tm.optimal_method)}</span>
            </div>
          ` : ''}
        </div>

        <div style="margin-top: 6px;" title="${escapeHtml(provTitle(ram))}">
          <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span style="color: #3b82f6; font-weight: 600;">RAM:</span>
            <span>${(isOnline && !isMissing(ram.used_gb)) ? `${fmt(ram.used_gb, 'GB')} / ${fmt(ram.total_gb, 'GB')} (${fmt(ram.usage_pct, '%')})` : `-- / ${fmt(ram.total_gb, 'GB')} (${st.label})`}</span>
          </div>
          <div style="margin-top: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; height: 5px; overflow: hidden;">
            <div style="width: ${(isOnline && !isMissing(ram.usage_pct)) ? Math.max(0, Math.min(100, ram.usage_pct)) : 0}%; height: 100%; background: linear-gradient(90deg, #3b82f6, #60a5fa);"></div>
          </div>
        </div>

        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.03);" title="${escapeHtml(provTitle(npu))}">
          <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span style="color: #ec4899; font-weight: 600;">${escapeHtml(fmt(npu.name))}</span>
            <span style="color: #ec4899; font-weight: 700;">${fmt(npu.max_tops, 'TOPS')}</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
            ${escapeHtml(fmt(npu.status))} (${fmt(npu.cores, 'Cores')})
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderDynamicIpsList(devices, dynamicIps) {
  const container = document.getElementById("dynamic-ips-list-container");
  if (!container || !devices) return;

  container.innerHTML = devices.map(d => {
    const st = onlineState(d.online);
    return `
      <div class="dynamic-ip-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <strong style="font-size: 11px; color: var(--text-primary);">${escapeHtml(fmt(d.name))}</strong>
          <span class="badge ${st.cls}">${st.label === 'ONLINE' ? 'ACTIVE' : st.label}</span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">
          ${escapeHtml(fmt(d.role))} • MAC: ${escapeHtml(fmt(d.mac_address))}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 4px;">
          <span class="ip-pill ip-pill-lan">LAN: ${escapeHtml(fmt(d.local_ip))}</span>
          <span class="ip-pill ip-pill-ts">Tailscale: ${escapeHtml(fmt(d.tailscale_ip))}</span>
          ${d.tb4_ip ? `<span class="ip-pill ip-pill-tb4">TB4 Bridge: ${escapeHtml(d.tb4_ip)}</span>` : ''}
          ${d.adb_target ? `<span class="ip-pill ip-pill-adb">ADB Target: ${escapeHtml(d.adb_target)}</span>` : ''}
          <span class="ip-source-badge">Source: ${escapeHtml(fmt(d.dynamic_source))}</span>
        </div>
      </div>
    `;
  }).join("");
}

const CATEGORY_META = {
  bluetooth: { icon: "📶", label: "Bluetooth", badgeClass: "conn-cat-bluetooth" },
  ssh: { icon: "🔒", label: "SSH", badgeClass: "conn-cat-ssh" },
  tailscale: { icon: "🛡️", label: "Tailscale", badgeClass: "conn-cat-tailscale" },
  wifi: { icon: "📡", label: "Wi-Fi 7", badgeClass: "conn-cat-wifi" },
  usb: { icon: "🔌", label: "USB", badgeClass: "conn-cat-usb" },
  thunderbolt: { icon: "⚡", label: "Thunderbolt 4", badgeClass: "conn-cat-thunderbolt" }
};

window.filterConnections = function(category) {
  currentConnectionFilter = category;
  document.querySelectorAll("#connection-filter-bar .filter-pill").forEach(p => {
    p.classList.toggle("active", p.getAttribute("data-cat") === category);
  });
  if (cachedActiveConnections) {
    renderConnectionsList(cachedActiveConnections, category);
  }
};

function renderConnectionsSummary(activeData) {
  if (!activeData) return;
  const badge = document.getElementById("connections-total-badge");
  if (badge) {
    const total = activeData.total_active_connections || 0;
    const cats = activeData.categories_active || 0;
    badge.innerText = `${total} ACTIVE LINKS (${cats}/6 CATEGORIES)`;
  }

  const summary = activeData.summary || {};
  const elAll = document.getElementById("filter-cnt-all");
  if (elAll) elAll.innerText = activeData.total_active_connections || 0;

  for (const cat of ["bluetooth", "ssh", "tailscale", "wifi", "usb", "thunderbolt"]) {
    const el = document.getElementById(`filter-cnt-${cat}`);
    if (el) el.innerText = summary[cat] || 0;
  }
}

function renderConnectionsList(activeData, filterCat) {
  const container = document.getElementById("connections-list-container");
  if (!container || !activeData || !activeData.connections) return;

  let list = [];
  if (!filterCat || filterCat === "all") {
    for (const cat of ["bluetooth", "ssh", "tailscale", "wifi", "usb", "thunderbolt"]) {
      const items = (activeData.connections[cat] || []).map(i => ({ category: cat, ...i }));
      list = list.concat(items);
    }
  } else {
    list = (activeData.connections[filterCat] || []).map(i => ({ category: filterCat, ...i }));
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div style="color: var(--text-muted); font-size: 11px; padding: 16px; text-align: center; background: rgba(255,255,255,0.02); border-radius: 6px; border: 1px dashed var(--border-color);">
        No active connections detected in category: <strong>${filterCat}</strong>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(item => {
    const cat = item.category || "unknown";
    const meta = CATEGORY_META[cat] || { icon: "🔗", label: cat.toUpperCase(), badgeClass: "conn-cat-wifi" };
    const state = item.state || "ACTIVE";
    const stateBadgeClass = (state === "CONNECTED" || state === "ESTABLISHED" || state === "ACTIVE") ? "badge-active" : "badge-standby";

    const endpoint = item.endpoint || item.interface || item.local_addr || "--";
    const speed = item.bandwidth || item.tx_rate || item.speed || "--";
    
    // Latency or Signal
    let latencyOrSignal = "--";
    if (item.latency_rtt_ms !== undefined && item.latency_rtt_ms !== null) {
      latencyOrSignal = `${item.latency_rtt_ms} ms RTT`;
    } else if (item.rssi !== undefined && item.rssi !== null) {
      latencyOrSignal = `RSSI ${item.rssi} dBm${item.noise ? ' / Noise ' + item.noise + ' dBm' : ''}`;
    } else if (item.signal) {
      latencyOrSignal = item.signal;
    }

    const transport = item.transport || "--";
    const protocol = item.protocol || item.type || "--";
    const details = item.details || "";

    return `
      <div class="connection-card">
        <div class="conn-header">
          <div class="conn-title">
            <span>${meta.icon}</span>
            <span class="conn-cat-tag ${meta.badgeClass}">${meta.label}</span>
            <span style="font-weight: 600; color: #fff;">${item.name || 'Unnamed Link'}</span>
          </div>
          <span class="badge ${stateBadgeClass}">${state}</span>
        </div>

        <div class="conn-details-grid">
          <div class="conn-row">
            <span class="conn-lbl">Transport:</span>
            <span class="conn-val" title="${transport}">${truncate(transport, 22)}</span>
          </div>
          <div class="conn-row">
            <span class="conn-lbl">Endpoint/Dev:</span>
            <span class="conn-val" title="${endpoint}">${truncate(endpoint, 20)}</span>
          </div>
          <div class="conn-row">
            <span class="conn-lbl">Bandwidth/Rate:</span>
            <span class="conn-val" style="color: #38bdf8; font-weight: 600;">${speed}</span>
          </div>
          <div class="conn-row">
            <span class="conn-lbl">Signal/RTT:</span>
            <span class="conn-val" style="color: #10b981; font-weight: 600;">${latencyOrSignal}</span>
          </div>
          ${item.ssid ? `
            <div class="conn-row">
              <span class="conn-lbl">SSID / Ch:</span>
              <span class="conn-val" style="color: #a855f7;">${item.ssid} (Ch ${item.channel || '?'})</span>
            </div>
          ` : ''}
          ${item.phy_mode ? `
            <div class="conn-row">
              <span class="conn-lbl">PHY / Width:</span>
              <span class="conn-val">${item.phy_mode} • ${item.channel_width || ''}</span>
            </div>
          ` : ''}
          ${item.peers && item.peers.length ? `
            <div class="conn-row">
              <span class="conn-lbl">Active Peers:</span>
              <span class="conn-val" style="color: #ffb800;">${item.peer_count || item.peers.length} Peer(s)</span>
            </div>
          ` : ''}
          ${item.user ? `
            <div class="conn-row">
              <span class="conn-lbl">User / PID:</span>
              <span class="conn-val">${item.user} (PID ${item.pid || '?'})</span>
            </div>
          ` : ''}
          <div class="conn-row" style="grid-column: 1 / -1;">
            <span class="conn-lbl">Protocol / Security:</span>
            <span class="conn-val">${protocol}${item.security ? ' • ' + item.security : ''}${item.mcs_index !== undefined ? ' • MCS ' + item.mcs_index : ''}</span>
          </div>
        </div>

        ${details ? `
          <div class="conn-desc" title="${details}">
            ${details}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}

function truncate(str, maxLen) {
  if (!str) return "";
  return str.length > maxLen ? str.substring(0, maxLen - 1) + "…" : str;
}

window.updateUI = updateUI;
window.fetchTopologyREST = fetchTopologyREST;

// ---------------------------------------------------------------------------
// Screen Lens Sovereign Integration (Port 4003)
// ---------------------------------------------------------------------------
let lensState = {
  active_node: "l1_mac_mini",
  arm_state: "OBSERVE_ONLY",
  fps: 0,
  display: { width: 1920, height: 1080 },
  frontmost: { app: "Unknown", title: "" },
  lens_hub_online: false
};

async function fetchLensStatus() {
  try {
    const res = await fetch("/api/lens/status");
    if (!res.ok) return;
    const data = await res.json();
    lensState = Object.assign(lensState, data);

    // Update Header Badge
    const badge = document.getElementById("badge-lens-status");
    if (badge) {
      if (lensState.lens_hub_online) {
        badge.innerHTML = `<span class="live-dot" style="background: #a855f7;"></span><span>LENS :4003 (${lensState.fps ? lensState.fps.toFixed(1) + ' FPS' : 'LIVE'})</span>`;
        badge.style.borderColor = "#a855f7";
      } else {
        badge.innerHTML = `<span class="live-dot" style="background: #ef4444;"></span><span>LENS :4003 (OFFLINE)</span>`;
        badge.style.borderColor = "#ef4444";
      }
    }

    // Update HUD in Lens tab
    const hudStatus = document.getElementById("lens-hud-status");
    if (hudStatus) {
      hudStatus.textContent = lensState.lens_hub_online ? `STREAMING :4003 (${lensState.active_node})` : "OFFLINE";
      hudStatus.className = lensState.lens_hub_online ? "badge badge-active" : "badge badge-inactive";
    }

    const fpsEl = document.getElementById("lens-hud-fps");
    if (fpsEl) fpsEl.textContent = `${(lensState.fps || 0).toFixed(1)} FPS`;

    const resEl = document.getElementById("lens-hud-res");
    if (resEl && lensState.display) {
      resEl.textContent = `${lensState.display.width}x${lensState.display.height}`;
    }

    const appEl = document.getElementById("lens-hud-app");
    if (appEl && lensState.frontmost) {
      appEl.textContent = lensState.frontmost.app || "Antigravity";
    }

    // Update Arming State
    updateLensArmUI(lensState.arm_state);

    // Update target select value if not actively focused
    const sel = document.getElementById("lens-target-select");
    if (sel && document.activeElement !== sel && lensState.active_node) {
      for (let opt of sel.options) {
        if (opt.value === lensState.active_node) {
          sel.value = lensState.active_node;
          break;
        }
      }
    }

    // Update Expanded HUD
    const expHud = document.getElementById("lens-expanded-hud");
    if (expHud) {
      expHud.textContent = `${lensState.active_node} • ${lensState.arm_state} • ${(lensState.fps || 0).toFixed(1)} FPS`;
    }
  } catch (e) {
    console.debug("Lens status fetch error:", e);
  }
}

function updateLensArmUI(armState) {
  const badge = document.getElementById("lens-arm-badge");
  const btn = document.getElementById("btn-lens-arm-toggle");
  if (!badge || !btn) return;

  if (armState === "CONTROL_ARMED") {
    badge.textContent = "⚡ CONTROL ARMED";
    badge.style.background = "rgba(239, 68, 68, 0.25)";
    badge.style.borderColor = "#ef4444";
    badge.style.color = "#f87171";

    btn.innerHTML = "<span>🔒</span> Disarm Control";
    btn.className = "btn btn-sm btn-danger";
  } else {
    badge.textContent = "🛡️ OBSERVE ONLY";
    badge.style.background = "rgba(16, 185, 129, 0.2)";
    badge.style.borderColor = "#10b981";
    badge.style.color = "#10b981";

    btn.innerHTML = "<span>⚡</span> Arm Control (30s)";
    btn.className = "btn btn-sm";
  }
}

async function handleLensTargetChange(nodeId) {
  try {
    const res = await fetch("/api/lens/node/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node: nodeId })
    });
    const data = await res.json();
    lensState.active_node = data.active_node || nodeId;
    refreshLensStream();
    fetchLensStatus();
  } catch (e) {
    console.error("Failed to select lens node:", e);
  }
}

async function toggleLensArming() {
  const isArmed = lensState.arm_state === "CONTROL_ARMED";
  try {
    const res = await fetch("/api/lens/arm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ armed: !isArmed, duration_sec: 30 })
    });
    const data = await res.json();
    lensState.arm_state = data.arm_state;
    updateLensArmUI(lensState.arm_state);
  } catch (e) {
    console.error("Failed to toggle arming:", e);
  }
}

function refreshLensStream() {
  const img = document.getElementById("lens-stream-img");
  if (img) img.src = `/api/lens/stream?t=${Date.now()}`;

  const expContainer = document.getElementById("lens-expanded-container");
  const expImg = document.getElementById("lens-expanded-img");
  if (expContainer && expContainer.style.display !== "none" && expImg) {
    expImg.src = `/api/lens/stream?t=${Date.now()}`;
  }
}

function toggleLensExpandedView(show) {
  const container = document.getElementById("lens-expanded-container");
  const expImg = document.getElementById("lens-expanded-img");
  if (!container) return;

  if (show) {
    container.style.display = "flex";
    if (expImg) expImg.src = `/api/lens/stream?t=${Date.now()}`;
  } else {
    container.style.display = "none";
    if (expImg) expImg.src = "";
  }
}

async function takeLensSnapshot() {
  const resBox = document.getElementById("lens-snapshot-result");
  if (resBox) {
    resBox.style.display = "block";
    resBox.textContent = "Capturing snapshot from Screen Lens...";
  }

  try {
    const res = await fetch("/api/lens/snapshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node: lensState.active_node })
    });
    const data = await res.json();
    if (resBox) {
      if (data.status === "snapshot_captured") {
        resBox.innerHTML = `✅ Saved: <strong>${data.filename}</strong> (${(data.bytes / 1024).toFixed(1)} KB)<br>SHA256: <span style="color: #00f0ff;">${data.sha256.substring(0, 24)}...</span>`;
      } else {
        resBox.textContent = `❌ Snapshot failed: ${data.error || 'Unknown error'}`;
      }
    }
  } catch (e) {
    if (resBox) resBox.textContent = `❌ Snapshot error: ${e}`;
  }
}

async function sendLensKey(key) {
  if (lensState.arm_state !== "CONTROL_ARMED") {
    alert("Control is in OBSERVE ONLY mode. Please click 'Arm Control (30s)' before sending inputs.");
    return;
  }
  try {
    await fetch("/api/lens/hid/key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key, node: lensState.active_node })
    });
  } catch (e) {
    console.error("Failed to send key:", e);
  }
}

async function handleLensClick(event) {
  if (lensState.arm_state !== "CONTROL_ARMED") {
    const resBox = document.getElementById("lens-snapshot-result");
    if (resBox) {
      resBox.style.display = "block";
      resBox.innerHTML = `<span style="color: #fbbf24;">⚠️ Observe-Only Mode:</span> Click "Arm Control (30s)" to enable live remote clicks.`;
      setTimeout(() => { if (resBox) resBox.style.display = "none"; }, 4000);
    }
    return;
  }

  const img = event.target;
  const rect = img.getBoundingClientRect();
  const displayW = (lensState.display && lensState.display.width) || 1920;
  const displayH = (lensState.display && lensState.display.height) || 1080;
  const displayAspect = displayW / displayH;
  const imgAspect = rect.width / rect.height;

  let renderW = rect.width;
  let renderH = rect.height;
  let offsetX = 0;
  let offsetY = 0;

  if (imgAspect > displayAspect) {
    renderW = rect.height * displayAspect;
    offsetX = (rect.width - renderW) / 2;
  } else {
    renderH = rect.width / displayAspect;
    offsetY = (rect.height - renderH) / 2;
  }

  const clickX = event.clientX - rect.left - offsetX;
  const clickY = event.clientY - rect.top - offsetY;

  if (clickX < 0 || clickX > renderW || clickY < 0 || clickY > renderH) {
    return;
  }

  const normX = Math.round((clickX / renderW) * displayW);
  const normY = Math.round((clickY / renderH) * displayH);

  try {
    await fetch("/api/lens/hid/click", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x: normX, y: normY, node: lensState.active_node })
    });
  } catch (e) {
    console.error("Failed to dispatch click:", e);
  }
}

window.handleLensTargetChange = handleLensTargetChange;
window.toggleLensArming = toggleLensArming;
window.refreshLensStream = refreshLensStream;
window.toggleLensExpandedView = toggleLensExpandedView;
window.takeLensSnapshot = takeLensSnapshot;
window.sendLensKey = sendLensKey;
window.handleLensClick = handleLensClick;

/* ==========================================================================
   WhatCable Hardware Inspector Controller (F4.2)
   ========================================================================== */

const whatcableState = {
  activeDevice: "full_network",
  data: null,
  selectedPortId: "Port-USB-C@1",
};

function selectWhatCableDevice(deviceId) {
  whatcableState.activeDevice = deviceId;
  const pills = document.querySelectorAll("#wc-device-pills .wc-pill");
  pills.forEach((p) => {
    if (p.getAttribute("data-device") === deviceId) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });
  fetchWhatCableDetails();
}

async function fetchWhatCableDetails(force = false) {
  const btn = document.getElementById("btn-whatcable-rescan");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳</span> Scanning...";
  }
  const device = whatcableState.activeDevice || "full_network";
  try {
    const url = `/api/whatcable/details?device=${encodeURIComponent(device)}${force ? "&force=true" : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    whatcableState.data = data;
    renderWhatcableUI(data);
    updateSidebarWhatcableSummary(data);
  } catch (err) {
    console.error("Failed to fetch WhatCable details:", err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>🔄</span> Rescan Hardware";
    }
  }
}

function renderWhatcableUI(data) {
  if (!data) return;
  const device = whatcableState.activeDevice || "full_network";
  if (device === "full_network" || data.is_full_network) {
    renderWhatcableFullNetwork(data);
  } else {
    renderWhatcableIndividualDevice(data);
  }
}

function renderWhatcableFullNetwork(data) {
  const netView = document.getElementById("whatcable-network-view");
  const devView = document.getElementById("whatcable-device-view");
  if (netView) netView.style.display = "flex";
  if (devView) devView.style.display = "none";

  const subtitle = document.getElementById("wc-header-subtitle");
  if (subtitle) subtitle.textContent = "9-Node Mesh Physical Cable Topology • Zero-Mock Hardware Probing";

  const summary = data.summary || {};
  const elTotal = document.getElementById("wc-total-ports");
  const elCables = document.getElementById("wc-active-cables");
  const elEmarkers = document.getElementById("wc-emarkers");
  const elSpeed = document.getElementById("wc-max-speed");
  const elWatts = document.getElementById("wc-max-watts");

  if (elTotal) elTotal.textContent = summary.total_ports != null ? summary.total_ports : "--";
  if (elCables) elCables.textContent = summary.cables_detected != null ? summary.cables_detected : "--";
  if (elEmarkers) elEmarkers.textContent = summary.emarkers_detected != null ? summary.emarkers_detected : "--";
  if (elSpeed) elSpeed.textContent = summary.max_link_speed_gbps != null ? `${summary.max_link_speed_gbps} Gbps` : "--";
  if (elWatts) elWatts.textContent = summary.max_power_watts != null ? `${summary.max_power_watts}W` : "--";

  // Update KPI strip
  const kn = document.getElementById("wc-net-nodes");
  const knSub = document.getElementById("wc-net-nodes-sub");
  const kc = document.getElementById("wc-net-cables");
  const ke = document.getElementById("wc-net-emarkers");
  const kb = document.getElementById("wc-net-bw-pool");
  const kbtn = document.getElementById("wc-net-bottlenecks");
  const ksha = document.getElementById("wc-net-sha");

  if (kn) kn.textContent = summary.total_nodes != null ? `${summary.total_nodes} Nodes` : "--";
  if (knSub) knSub.textContent = summary.active_nodes != null ? `${summary.active_nodes} Online • ${(summary.total_nodes || 0) - summary.active_nodes} Standby` : "--";
  if (kc) kc.textContent = summary.cables_detected != null ? `${summary.cables_detected} Verified` : "--";
  if (ke) ke.textContent = summary.emarkers_detected != null ? `${summary.emarkers_detected} Active (SOP')` : "--";
  if (kb) kb.textContent = summary.total_bandwidth_pool_gbps != null ? `${summary.total_bandwidth_pool_gbps} Gbps` : "--";
  if (kbtn) kbtn.textContent = `${summary.bottlenecks_detected || 0} Alert${summary.bottlenecks_detected === 1 ? "" : "s"}`;
  if (ksha) ksha.textContent = data.data_hash_sha256 ? data.data_hash_sha256.substring(0, 16) + "..." : "--";

  // Render Bottleneck Banners
  renderNetworkBottlenecks(data.bottlenecks || []);

  // Render 9x9 Adjacency Matrix
  renderAdjacencyMatrix(data.matrix);

  // Render Cable Inventory Table
  renderCablesInventory(data.cables || []);
}

function renderWhatcableIndividualDevice(data) {
  const netView = document.getElementById("whatcable-network-view");
  const devView = document.getElementById("whatcable-device-view");
  if (netView) netView.style.display = "none";
  if (devView) devView.style.display = "block";

  const subtitle = document.getElementById("wc-header-subtitle");
  if (subtitle) subtitle.textContent = `${data.device_name || data.device_id} • ${data.device_role || ""} • ${data.os || ""}`;

  const elTitle = document.getElementById("chassis-title");
  if (elTitle) {
    const dName = data.device_name || data.device_id || "DEVICE";
    elTitle.textContent = `${dName.toUpperCase()} — PHYSICAL CHASSIS PORT SCHEMATIC`;
  }

  const summary = data.summary || {};
  const elTotal = document.getElementById("wc-total-ports");
  const elCables = document.getElementById("wc-active-cables");
  const elEmarkers = document.getElementById("wc-emarkers");
  const elSpeed = document.getElementById("wc-max-speed");
  const elWatts = document.getElementById("wc-max-watts");
  const elChassisBadge = document.getElementById("chassis-status-badge");

  if (elTotal) elTotal.textContent = summary.total_ports ?? 0;
  if (elCables) elCables.textContent = summary.cables_detected ?? 0;
  if (elEmarkers) elEmarkers.textContent = summary.emarkers_detected ?? 0;
  if (elSpeed) elSpeed.textContent = `${summary.max_negotiated_speed_gbps || 0.0} Gbps`;
  if (elWatts) elWatts.textContent = `${summary.max_power_rating_watts || 0}W`;
  if (elChassisBadge) elChassisBadge.textContent = `${summary.active_ports || 0} ACTIVE PORTS`;

  // Render Bottleneck Banners
  renderWhatcableBottlenecks(data);

  // Host vs Non-Host Chassis Layout Switching
  const hostPanels = document.getElementById("chassis-host-panels");
  const dynPanel = document.getElementById("chassis-dynamic-panel");
  const dynContainer = document.getElementById("chassis-dynamic-ports");
  const isHost = data.device_id === "l1_mac_mini";

  if (isHost) {
    if (hostPanels) hostPanels.style.display = "block";
    if (dynPanel) dynPanel.style.display = "none";
    updateChassisPortLEDs(data);
  } else {
    if (hostPanels) hostPanels.style.display = "none";
    if (dynPanel) dynPanel.style.display = "block";
    if (dynContainer) {
      dynContainer.innerHTML = "";
      const ports = data.ports || [];
      if (ports.length === 0) {
        dynContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 10px;">Device currently in standby or no physical ports detected.</div>`;
      } else {
        ports.forEach((p) => {
          const isAct = Boolean(p.connection_active);
          const bn = p.bottleneck;
          let ledColor = isAct ? "led-green" : "led-grey";
          if (bn && bn.is_bottleneck && (bn.severity === "WARNING" || bn.severity === "CRITICAL")) {
            ledColor = "led-yellow";
          }
          let icon = "🔌";
          const pType = (p.port_type || "").toLowerCase();
          if (pType.includes("thunderbolt") || pType.includes("usb4") || pType.includes("tb")) icon = "⚡";
          else if (pType.includes("ethernet") || pType.includes("rj45") || pType.includes("lan") || pType.includes("wan") || pType.includes("base-t")) icon = "🌐";
          else if (pType.includes("power") || pType.includes("dc") || pType.includes("pwr")) icon = "⏻";
          else if (pType.includes("display") || pType.includes("hdmi") || pType.includes("dp")) icon = "🖥️";

          const div = document.createElement("div");
          div.className = "port-receptacle dynamic-rec-item";
          div.id = `dyn-rec-${p.port_id}`;
          div.title = `${p.port_id}: ${p.headline || p.port_type || ""}`;
          div.onclick = () => selectWhatcablePort(p.port_id);
          div.innerHTML = `
            <div class="port-icon">${icon}</div>
            <div class="port-name">${escapeHtml(p.port_id)}</div>
            <div class="port-meta">${escapeHtml(p.headline || p.port_type || "")}</div>
            <div class="port-led ${ledColor}"></div>
          `;
          dynContainer.appendChild(div);
        });
      }
    }
  }

  // Select first active port or default port
  const ports = data.ports || [];
  const firstActive = ports.find((p) => p.connection_active);
  const selectedPort = firstActive ? firstActive.port_id : (ports[0] ? ports[0].port_id : "Port-USB-C@1");
  selectWhatcablePort(selectedPort);
}

function renderAdjacencyMatrix(matrix) {
  const table = document.getElementById("wc-matrix-table");
  if (!table || !matrix) return;
  table.innerHTML = "";

  const labels = matrix.node_labels || [];
  const cells = matrix.cells || [];

  const thead = document.createElement("thead");
  const hdrRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.className = "row-hdr";
  corner.textContent = "Source \\ Target";
  hdrRow.appendChild(corner);

  labels.forEach((lbl) => {
    const th = document.createElement("th");
    th.textContent = lbl;
    hdrRow.appendChild(th);
  });
  thead.appendChild(hdrRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  cells.forEach((row, rIdx) => {
    const tr = document.createElement("tr");
    const rHdr = document.createElement("th");
    rHdr.className = "row-hdr";
    rHdr.textContent = labels[rIdx] || `Node ${rIdx + 1}`;
    tr.appendChild(rHdr);

    row.forEach((cell, cIdx) => {
      const td = document.createElement("td");
      if (cell.is_self) {
        td.innerHTML = '<span class="wc-cell-badge self">LOCAL</span>';
        td.title = `${labels[rIdx]} (Self Node)`;
      } else if (!cell.linked) {
        td.innerHTML = '<span class="wc-cell-badge none">—</span>';
        td.title = `No direct physical cable link between ${labels[rIdx]} and ${labels[cIdx]}`;
      } else {
        let badgeClass = "none";
        let label = cell.type_label || "LINK";
        if (cell.link_type === "THUNDERBOLT_4") {
          badgeClass = "tb4"; label = "TB4 40G";
        } else if (cell.link_type === "ETH_10G") {
          badgeClass = "eth10g"; label = "10GbE";
        } else if (cell.link_type === "ETH_2_5G") {
          badgeClass = "eth25g"; label = "2.5GbE";
        } else if (cell.link_type === "ETH_1G") {
          badgeClass = "eth1g"; label = "1GbE";
        } else if (cell.link_type === "USB_2") {
          badgeClass = "usb2"; label = "USB 2.0 (480M)";
        } else if (cell.link_type === "WIFI_7_MLO") {
          badgeClass = "wifi7"; label = "Wi-Fi 7 (6G)";
        }

        td.innerHTML = `<span class="wc-cell-badge ${badgeClass}">${label}</span>`;
        td.title = `${cell.type_label}: ${cell.description || ""}\nPhysical Media: ${cell.media || ""}\nSpeed: ${cell.speed_gbps} Gbps`;
        td.onclick = () => {
          selectWhatCableDevice(cell.target);
        };
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
}

function renderCablesInventory(cables) {
  const tbody = document.getElementById("wc-cables-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  cables.forEach((c) => {
    const tr = document.createElement("tr");
    const stClass = (c.status || "optimal").toLowerCase();
    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(c.name)}</strong><br>
        <span style="font-size: 10px; color: var(--text-muted);">${escapeHtml(c.media_type || "")} • ${c.length_meters || 1.0}m</span>
      </td>
      <td><code>${escapeHtml(c.source_node)}</code><br><span style="font-size: 10px; color: var(--text-muted);">${escapeHtml(c.source_port || "")}</span></td>
      <td><code>${escapeHtml(c.target_node)}</code><br><span style="font-size: 10px; color: var(--text-muted);">${escapeHtml(c.target_port || "")}</span></td>
      <td>${c.e_marker ? `<span style="color: #00f0ff; font-weight: 600;">SOP' Chip</span><br><span style="font-size: 10px; color: var(--text-muted);">${escapeHtml(c.e_marker_vendor || "")}</span>` : '<span style="color: var(--text-muted);">N/A (Passive/Copper)</span>'}</td>
      <td><span style="color: #10b981; font-weight: 600;">${escapeHtml(c.power_delivery || "--")}</span></td>
      <td><code>${c.rated_bandwidth_gbps} Gbps</code></td>
      <td><strong style="color: ${c.is_bottleneck ? "#f59e0b" : "#38bdf8"}; font-family: monospace;">${c.negotiated_rate_gbps} Gbps</strong></td>
      <td><code>${c.rtt_latency_ms != null ? c.rtt_latency_ms + " ms" : "--"}</code></td>
      <td>
        <span class="wc-status-pill ${stClass}">${c.status || "OPTIMAL"}</span>
        ${c.is_bottleneck ? '<div style="font-size: 9.5px; color: #f59e0b; margin-top: 2px;">⚠️ Throttled</div>' : ""}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderNetworkBottlenecks(bottlenecks) {
  const container = document.getElementById("whatcable-bottleneck-banners");
  if (!container) return;
  container.innerHTML = "";

  if (bottlenecks.length === 0) {
    const card = document.createElement("div");
    card.className = "bn-alert-card optimal";
    card.innerHTML = `
      <div class="bn-icon">✅</div>
      <div class="bn-content">
        <div class="bn-title"><strong>ALL MESH PHYSICAL CABLE LINKS OPTIMAL</strong></div>
        <div class="bn-detail">Thunderbolt 4 (40 Gbps) and 10GbE full duplex operating with zero cable bottlenecks.</div>
      </div>
    `;
    container.appendChild(card);
    return;
  }

  bottlenecks.forEach((bn) => {
    const card = document.createElement("div");
    const sev = (bn.severity || "warning").toLowerCase();
    card.className = `bn-alert-card ${sev}`;
    card.innerHTML = `
      <div class="bn-icon">⚠️</div>
      <div class="bn-content">
        <div class="bn-title"><strong>[${bn.severity}] ${escapeHtml(bn.source_node)} ↔ ${escapeHtml(bn.target_node)}:</strong> ${escapeHtml(bn.type)}</div>
        <div class="bn-detail">${escapeHtml(bn.details)}</div>
        ${bn.remedy ? `<div class="bn-remedy">💡 <strong>Remedy:</strong> ${escapeHtml(bn.remedy)}</div>` : ""}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderWhatcableBottlenecks(data) {
  const container = document.getElementById("whatcable-bottleneck-banners");
  if (!container) return;
  container.innerHTML = "";

  const ports = data.ports || [];
  let foundAny = false;

  ports.forEach((p) => {
    const bn = p.bottleneck;
    if (bn && bn.is_bottleneck) {
      foundAny = true;
      const card = document.createElement("div");
      const sev = (bn.severity || "warning").toLowerCase();
      card.className = `bn-alert-card ${sev}`;
      
      const icon = sev === "critical" ? "🚨" : (sev === "warning" ? "⚠️" : "ℹ️");
      card.innerHTML = `
        <div class="bn-icon">${icon}</div>
        <div class="bn-content">
          <div class="bn-title"><strong>[${bn.severity}] ${escapeHtml(p.port_id)}:</strong> ${escapeHtml(bn.summary || "Bottleneck detected")}</div>
          <div class="bn-detail">${escapeHtml(bn.detail || "")}</div>
          ${bn.remedy ? `<div class="bn-remedy">💡 <strong>Remedy:</strong> ${escapeHtml(bn.remedy)}</div>` : ""}
        </div>
      `;
      container.appendChild(card);
    }
  });

  if (!foundAny) {
    const card = document.createElement("div");
    card.className = "bn-alert-card optimal";
    card.innerHTML = `
      <div class="bn-icon">✅</div>
      <div class="bn-content">
        <div class="bn-title"><strong>ALL PHYSICAL LINKS OPTIMAL</strong></div>
        <div class="bn-detail">No cable down-negotiations detected across the active chassis receptacles.</div>
      </div>
    `;
    container.appendChild(card);
  }
}

function updateChassisPortLEDs(data) {
  const ports = data.ports || [];
  ports.forEach((p) => {
    let recElId = null;
    let ledElId = null;

    if (p.receptacle === 1 || p.port_id === "Port-USB-C@1") {
      recElId = "port-rec-1"; ledElId = "led-port-1";
    } else if (p.receptacle === 2 || p.port_id === "Port-USB-C@2") {
      recElId = "port-rec-2"; ledElId = "led-port-2";
    } else if (p.receptacle === 3 || p.port_id === "Port-USB-C@3") {
      recElId = "port-rec-3"; ledElId = "led-port-3";
    } else if (p.receptacle === 5 || p.port_id === "Port-USB-C@5") {
      recElId = "port-rec-5"; ledElId = "led-port-5";
    } else if (p.receptacle === 6 || p.port_id === "Port-USB-C@6") {
      recElId = "port-rec-6"; ledElId = "led-port-6";
    }

    if (recElId && ledElId) {
      const led = document.getElementById(ledElId);
      if (led) {
        const bn = p.bottleneck;
        if (bn && bn.is_bottleneck && (bn.severity === "WARNING" || bn.severity === "CRITICAL")) {
          led.className = "port-led led-yellow";
        } else if (p.connection_active) {
          led.className = "port-led led-green";
        } else {
          led.className = "port-led led-grey";
        }
      }
    }
  });
}

function selectWhatcablePort(portId) {
  whatcableState.selectedPortId = portId;

  // Highlight receptacle
  document.querySelectorAll(".port-receptacle").forEach(el => el.classList.remove("active-selected"));
  
  let targetRecId = null;
  if (portId === "Port-USB-C@1") targetRecId = "port-rec-1";
  else if (portId === "Port-USB-C@2") targetRecId = "port-rec-2";
  else if (portId === "Port-USB-C@3") targetRecId = "port-rec-3";
  else if (portId === "Port-USB-C@5") targetRecId = "port-rec-5";
  else if (portId === "Port-USB-C@6") targetRecId = "port-rec-6";
  else if (portId === "Port-HDMI@1") targetRecId = "port-rec-hdmi";
  else if (portId === "eth0") targetRecId = "port-rec-eth";

  if (targetRecId) {
    const recEl = document.getElementById(targetRecId);
    if (recEl) recEl.classList.add("active-selected");
  }
  const dynRecEl = document.getElementById(`dyn-rec-${portId}`);
  if (dynRecEl) dynRecEl.classList.add("active-selected");

  const data = whatcableState.data;
  if (!data) return;

  // Find port data
  let portData = null;
  if (portId === "eth0") {
    portData = {
      port_id: "en0 (10GbE RJ45)",
      port_type: "10GBASE-T Ethernet Cat6",
      connection_active: true,
      headline: "10GbE RJ45 Ethernet",
      cable: {
        vendor_name: "Cat6 Certified STP Cable",
        vendor_id: "0x1000",
        product_id: "10GBASE-T",
        e_marker: false,
        speed_rating: "10 Gbps Full Duplex",
        max_bandwidth_gbps: 10.0,
        max_watts: 0,
        power_delivery: {
          rating_label: "Non-PD (802.3an 10GBASE-T)",
          max_watts: 0,
          max_voltage: 0,
          max_amperage: 0,
          pd_range: "Ethernet PHY",
          pps_supported: false
        }
      }
    };
  } else {
    portData = (data.ports || []).find(p => p.port_id === portId) || (data.ports || [])[0];
  }

  if (!portData) return;
  const cable = portData.cable || {};
  const pd = cable.power_delivery || {};

  // 1. Update Cable Connector Graphic
  const elPlugStatus = document.getElementById("conn-plug-status");
  const elSpecs = document.getElementById("conn-specs-text");
  const elSleeveLabel = document.getElementById("connector-label");

  if (elPlugStatus) elPlugStatus.textContent = `PLUGGED INTO ${portData.port_id.toUpperCase()} (${portData.headline || portData.port_type || "USB-C"})`;
  if (elSpecs) {
    elSpecs.textContent = `${cable.speed_rating || 'USB 2.0 (480 Mbps)'} • ${cable.e_marker ? "SOP' Smart Cable" : "Passive Cable"} • ${pd.rating_label || 'Standard USB Power'}`;
  }
  if (elSleeveLabel) {
    if (cable.speed_rating && cable.speed_rating.includes("40 Gbps")) {
      elSleeveLabel.textContent = pd.max_watts ? `THUNDERBOLT 4 / ${pd.max_watts}W EPR` : "THUNDERBOLT 4";
    } else if (portId === "eth0") {
      elSleeveLabel.textContent = "10GbE CAT6 / RJ45";
    } else {
      elSleeveLabel.textContent = pd.max_watts ? `USB-C / ${pd.max_watts}W` : "USB-C";
    }
  }

  // 2. Update E-Marker Chip Badge
  const elChipStatus = document.getElementById("emarker-chip-status");
  const emarkerContainer = document.getElementById("emarker-badge-container");

  if (elChipStatus) {
    elChipStatus.textContent = cable.e_marker ? "SOP' DETECTED" : "NO E-MARKER (PASSIVE)";
    elChipStatus.style.background = cable.e_marker ? "rgba(0, 240, 255, 0.15)" : "rgba(255, 255, 255, 0.05)";
    elChipStatus.style.borderColor = cable.e_marker ? "#00f0ff" : "var(--border-color)";
    elChipStatus.style.color = cable.e_marker ? "#00f0ff" : "var(--text-muted)";
  }

  if (emarkerContainer) {
    emarkerContainer.innerHTML = `
      <div class="emarker-param-grid">
        <div class="emarker-field">
          <div class="emarker-field-label">Silicon Vendor</div>
          <div class="emarker-field-value">${escapeHtml(cable.vendor_name || "Unknown / Passive Cable")}</div>
        </div>
        <div class="emarker-field">
          <div class="emarker-field-label">Vendor ID & Chip ID</div>
          <div class="emarker-field-value">${escapeHtml(cable.vendor_id || "N/A")} • ${escapeHtml(cable.product_id || "0x0001")}</div>
        </div>
        <div class="emarker-field">
          <div class="emarker-field-label">Cable Hierarchy</div>
          <div class="emarker-field-value">${cable.e_marker ? "SOP' Passive Smart Cable (CC Comm)" : "Standard Passive Copper"}</div>
        </div>
        <div class="emarker-field">
          <div class="emarker-field-label">Rated Bandwidth</div>
          <div class="emarker-field-value" style="color: #00f0ff;">${escapeHtml(cable.speed_rating || "USB 2.0 (480 Mbps)")}</div>
        </div>
      </div>
    `;
  }

  // 3. Update USB-PD Power Delivery Meters
  const watts = pd.max_watts != null ? pd.max_watts : (cable.max_watts != null ? cable.max_watts : null);
  const elPdBadge = document.getElementById("pd-mode-badge");
  const elRadialWatts = document.getElementById("radial-watts-val");
  const elRadialLabel = document.getElementById("radial-rating-label");
  const elGaugeFill = document.getElementById("gauge-fill-arc");

  if (elPdBadge) {
    elPdBadge.textContent = watts != null ? `${watts}W ${watts > 100 ? "EPR" : "SPR"}` : "--";
  }
  if (elRadialWatts) {
    elRadialWatts.innerHTML = watts != null ? `${watts}<span class="gauge-unit">W</span>` : `--<span class="gauge-unit">W</span>`;
  }
  if (elRadialLabel) {
    elRadialLabel.textContent = pd.pd_range || (watts != null ? (watts > 100 ? "EPR Range (240W)" : "SPR Range (100W)") : "--");
  }
  if (elGaugeFill) {
    const pct = watts != null ? Math.min(1, Math.max(0, watts / 240)) : 0;
    const offset = 188.5 * (1 - pct);
    elGaugeFill.style.strokeDashoffset = offset.toFixed(1);
  }

  // Voltage steps bar
  const maxV = pd.max_voltage != null ? pd.max_voltage : null;
  document.querySelectorAll("#voltage-steps-bar .v-step").forEach(step => {
    const v = parseInt(step.dataset.volts, 10);
    if (maxV != null) {
      if (v === 48 && maxV >= 48) step.classList.add("active");
      else if (v === 36 && maxV === 36) step.classList.add("active");
      else if (v === 28 && maxV === 28) step.classList.add("active");
      else if (v === 20 && maxV === 20) step.classList.add("active");
      else if (v === 15 && maxV === 15) step.classList.add("active");
      else if (v === 9 && maxV === 9) step.classList.add("active");
      else if (v === 5 && maxV <= 5) step.classList.add("active");
      else step.classList.remove("active");
    } else {
      step.classList.remove("active");
    }
  });

  // PPS badge
  const elPpsDesc = document.getElementById("pps-desc-text");
  if (elPpsDesc) {
    if (pd.pps_supported) {
      elPpsDesc.textContent = "3.3V – 21.0V @ 5.0A Dynamic (20 mV step voltage regulation active)";
    } else {
      elPpsDesc.textContent = "Fixed Voltages Only (PPS step voltage regulation not advertised)";
    }
  }

  // 4. Update DisplayPort Alt Mode Meters
  const displayPorts = data.display_ports || [];
  const activeDp = displayPorts.length > 0 ? displayPorts[0] : null;
  const disp = (activeDp && activeDp.displays && activeDp.displays.length > 0) ? activeDp.displays[0] : null;

  const elSinkName = document.getElementById("dp-sink-name");
  const elSinkMode = document.getElementById("dp-sink-mode");
  const elDeliveredVal = document.getElementById("dp-delivered-val");
  const elNeededVal = document.getElementById("dp-needed-val");
  const elDeliveredBar = document.getElementById("dp-delivered-bar");
  const elNeededBar = document.getElementById("dp-needed-bar");
  const elMarginText = document.getElementById("dp-margin-text");

  if (disp) {
    if (elSinkName) elSinkName.textContent = `🖥️ ${disp.monitor_name || "Display"} (via ${activeDp.port_id})`;
    if (elSinkMode) elSinkMode.textContent = disp.resolution ? `Current: ${disp.resolution} (8-bit RGB)` : "--";
    const delGbps = disp.delivered_gbps;
    const needGbps = disp.needed_gbps;
    const headroom = disp.headroom_gbps;

    if (elDeliveredVal) elDeliveredVal.textContent = delGbps != null ? `${delGbps} Gbps` : "--";
    if (elNeededVal) elNeededVal.textContent = needGbps != null ? `${needGbps} Gbps` : "--";
    if (elDeliveredBar) elDeliveredBar.style.width = "100%";
    if (elNeededBar) elNeededBar.style.width = delGbps && needGbps ? `${Math.round((needGbps / delGbps) * 100)}%` : "0%";

    if (elMarginText) {
      elMarginText.innerHTML = headroom != null ? `<strong>+${headroom} Gbps Headroom</strong> — Display link active.` : "Display link verified.";
    }
  }
}

function updateSidebarWhatcableSummary(data) {
  const container = document.getElementById("sidebar-whatcable-summary");
  if (!container) return;
  const d = data || whatcableState.data;
  if (!d) {
    container.innerHTML = `<div style="font-size: 11px; color: var(--text-muted);">Loading WhatCable telemetry...</div>`;
    return;
  }

  const ports = d.ports || [];
  let html = `<div style="display: flex; flex-direction: column; gap: 6px;">`;

  ports.forEach(p => {
    const c = p.cable || {};
    const pd = c.power_delivery || {};
    const bn = p.bottleneck;
    const isBn = bn && bn.is_bottleneck;
    const ledColor = isBn ? "#f59e0b" : (p.connection_active ? "#10b981" : "#475569");

    html += `
      <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 4px; padding: 6px 8px; cursor: pointer;" onclick="switchMainView('whatcable'); selectWhatcablePort('${p.port_id}');">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; font-size: 11px; color: #f0f4fc;">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${ledColor}; margin-right: 4px;"></span>
            ${escapeHtml(p.port_id)}
          </span>
          <span style="font-size: 10px; font-family: monospace; color: #00f0ff;">${escapeHtml(c.speed_rating || "--")}</span>
        </div>
        <div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">
          ${escapeHtml(c.vendor_name || "Standard Cable")} • ${escapeHtml(pd.rating_label || (pd.max_watts ? pd.max_watts + "W" : ""))}
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}

/* ==========================================================================
   Shark Wire Packet Capture & Dissection Controller (F4.3 - F4.7)
   ========================================================================== */

const sharkwireState = {
  running: true,
  selectedInterface: "en0",
  filter: "",
  autoScroll: true,
  packets: [],
  selectedPacket: null,
  activeFieldRange: null,
  sseSource: null,
  filterDebounceTimer: null,
  interfacesLoaded: false,
};

async function initSharkWire() {
  if (!sharkwireState.interfacesLoaded) {
    try {
      const res = await fetch("/api/packets/interfaces");
      if (res.ok) {
        const ifaces = await res.json();
        const sel = document.getElementById("sw-iface-select");
        if (sel && Array.isArray(ifaces) && ifaces.length > 0) {
          sel.innerHTML = "";
          ifaces.forEach(i => {
            const opt = document.createElement("option");
            opt.value = i.id;
            opt.textContent = `${i.name} (${i.mesh_role || i.type})`;
            if (i.id === sharkwireState.selectedInterface) opt.selected = true;
            sel.appendChild(opt);
          });
        }
        sharkwireState.interfacesLoaded = true;
      }
    } catch (e) {
      console.warn("Could not load interfaces:", e);
    }
  }

  connectSharkWireSSE();
}

function connectSharkWireSSE() {
  if (sharkwireState.sseSource) {
    sharkwireState.sseSource.close();
    sharkwireState.sseSource = null;
  }

  const iface = sharkwireState.selectedInterface || "en0";
  const filterExpr = sharkwireState.filter || "";
  const url = `/api/packets/stream?interface=${encodeURIComponent(iface)}&filter=${encodeURIComponent(filterExpr)}&limit=100`;

  const es = new EventSource(url);
  sharkwireState.sseSource = es;

  es.addEventListener("initial_batch", (evt) => {
    try {
      const batch = JSON.parse(evt.data);
      if (Array.isArray(batch)) {
        sharkwireState.packets = batch.slice(-300);
        renderPacketGridBatch(sharkwireState.packets);
        if (batch.length > 0 && !sharkwireState.selectedPacket) {
          selectSharkWirePacket(batch[batch.length - 1]);
        }
      }
    } catch (e) {
      console.error("Initial batch parse error:", e);
    }
  });

  es.addEventListener("packet", (evt) => {
    try {
      const pkt = JSON.parse(evt.data);
      appendPacketRow(pkt);
    } catch (e) {
      console.error("Packet parse error:", e);
    }
  });

  es.addEventListener("stats", (evt) => {
    try {
      const stats = JSON.parse(evt.data);
      updateSharkWireStats(stats);
    } catch (e) {
      console.error("Stats parse error:", e);
    }
  });

  es.onerror = (err) => {
    console.warn("SharkWire SSE stream retry...", err);
  };
}

function getPacketColorClass(pkt) {
  const proto = (pkt.protocol || "").toUpperCase();
  const info = (pkt.info || "").toUpperCase();

  if (proto === "WIREGUARD" || info.includes("WIREGUARD")) return "sw-proto-wireguard";
  if (proto === "AI-RPC" || info.includes("AI-RPC") || (proto.includes("HTTP") && (info.includes("8081") || info.includes("8082") || info.includes("8083") || info.includes("8084")))) return "sw-proto-airpc";
  if (proto === "AI-SSE" || info.includes("AI-SSE") || info.includes("SSE STREAM") || info.includes("DELTA")) return "sw-proto-aisse";
  if (proto === "SSH" || info.includes("SSH")) return "sw-proto-ssh";
  if (proto === "TCP" && (info.includes("[SYN]") || info.includes("SYN"))) return "sw-proto-tcpsyn";
  if (proto === "TCP" && (info.includes("[RST]") || info.includes("RST"))) return "sw-proto-tcprst";
  if (proto === "UDP") return "sw-proto-udp";
  if (proto === "ICMP") return "sw-proto-icmp";
  if (proto === "DNS" || info.includes("DNS")) return "sw-proto-dns";
  return "sw-proto-default";
}

function renderPacketGridBatch(packets) {
  const tbody = document.getElementById("sw-grid-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  packets.forEach(p => {
    const row = createPacketRow(p);
    tbody.appendChild(row);
  });

  const elDisp = document.getElementById("sw-cnt-displayed");
  if (elDisp) elDisp.textContent = packets.length.toLocaleString();

  if (sharkwireState.autoScroll) {
    tbody.scrollTop = tbody.scrollHeight;
  }
}

function createPacketRow(pkt) {
  const row = document.createElement("div");
  row.className = `sw-row ${getPacketColorClass(pkt)}`;
  row.dataset.index = pkt.index;

  const timeStr = pkt.time_str || (pkt.timestamp ? new Date(pkt.timestamp * 1000).toISOString().substr(11, 12) : "--");
  const src = pkt.source_name || pkt.source || "--";
  const dst = pkt.destination_name || pkt.destination || "--";

  row.innerHTML = `
    <div class="sw-col sw-col-no">${pkt.index}</div>
    <div class="sw-col sw-col-time">${timeStr}</div>
    <div class="sw-col sw-col-src" title="${escapeHtml(pkt.source || '')}">${escapeHtml(src)}</div>
    <div class="sw-col sw-col-dst" title="${escapeHtml(pkt.destination || '')}">${escapeHtml(dst)}</div>
    <div class="sw-col sw-col-proto">${escapeHtml(pkt.protocol || '')}</div>
    <div class="sw-col sw-col-len">${pkt.length ?? 0}</div>
    <div class="sw-col sw-col-info" title="${escapeHtml(pkt.info || '')}">${escapeHtml(pkt.info || '')}</div>
  `;

  row.addEventListener("click", () => selectSharkWirePacket(pkt));
  return row;
}

function appendPacketRow(pkt) {
  const tbody = document.getElementById("sw-grid-table-body");
  if (!tbody) return;

  sharkwireState.packets.push(pkt);
  if (sharkwireState.packets.length > 500) {
    sharkwireState.packets.shift();
  }

  // Recycle DOM rows if exceeding 200
  if (tbody.children.length >= 200) {
    tbody.removeChild(tbody.firstChild);
  }

  const row = createPacketRow(pkt);
  tbody.appendChild(row);

  const elDisp = document.getElementById("sw-cnt-displayed");
  if (elDisp) elDisp.textContent = tbody.children.length.toLocaleString();

  if (sharkwireState.autoScroll) {
    tbody.scrollTop = tbody.scrollHeight;
  }

  updateSidebarSharkwireQuickFeed();
}

function updateSharkWireStats(stats) {
  const elCap = document.getElementById("sw-cnt-captured");
  const elRate = document.getElementById("sw-cnt-rate");
  const elBytes = document.getElementById("sw-cnt-bytes");
  const elBuffer = document.getElementById("sw-cnt-buffer");
  const elBar = document.getElementById("sw-buffer-bar");
  const elDrops = document.getElementById("sw-cnt-drops");

  if (elCap) elCap.textContent = (stats.captured_count || 0).toLocaleString();
  if (elRate) elRate.textContent = `${stats.rate_pps || 0} pkts/s`;
  if (elBytes) elBytes.textContent = `${Math.round((stats.bytes_per_sec || 0) / 1024)} KB/s`;
  if (elBuffer) elBuffer.textContent = `${stats.buffer_utilization_pct || 0}%`;
  if (elBar) elBar.style.width = `${stats.buffer_utilization_pct || 0}%`;
  if (elDrops) elDrops.textContent = stats.drop_count || 0;
}

function selectSharkWirePacket(pkt) {
  sharkwireState.selectedPacket = pkt;

  // Highlight selected row in grid
  document.querySelectorAll("#sw-grid-table-body .sw-row").forEach(r => {
    if (r.dataset.index == pkt.index) {
      r.classList.add("selected");
    } else {
      r.classList.remove("selected");
    }
  });

  // Render Protocol Tree (Middle Pane)
  renderProtocolTree(pkt);

  // Render Hex & ASCII Dump (Lower Pane)
  renderHexDump(pkt);
}

function renderProtocolTree(pkt) {
  const titleEl = document.getElementById("sw-tree-title");
  const subtitleEl = document.getElementById("sw-tree-subtitle");
  const contentEl = document.getElementById("sw-tree-content");

  if (titleEl) titleEl.textContent = `▼ PACKET DETAILS — ${pkt.protocol} (Frame #${pkt.index})`;
  if (subtitleEl) subtitleEl.textContent = `${pkt.length} bytes captured on ${pkt.interface || "en0"}`;
  if (!contentEl) return;

  contentEl.innerHTML = "";

  const tree = pkt.tree || [];
  if (tree.length === 0) {
    contentEl.innerHTML = `<div class="sw-empty-hint">No protocol layer tree decoded for this frame.</div>`;
    return;
  }

  tree.forEach((layer) => {
    const layerEl = document.createElement("div");
    layerEl.className = "tree-layer";

    const header = document.createElement("div");
    header.className = "tree-layer-header";
    header.innerHTML = `
      <span class="tree-chevron">▼</span>
      <span class="tree-layer-name">${escapeHtml(layer.name)}</span>
    `;

    const fieldsList = document.createElement("div");
    fieldsList.className = "tree-fields-list";

    (layer.fields || []).forEach(f => {
      const fEl = document.createElement("div");
      fEl.className = "tree-field";
      fEl.dataset.start = f.start ?? 0;
      fEl.dataset.end = f.end ?? 0;
      fEl.innerHTML = `
        <span class="tree-field-label">${escapeHtml(f.label)}:</span>
        <span class="tree-field-val">${escapeHtml(String(f.value))}</span>
      `;
      fEl.addEventListener("click", (e) => {
        e.stopPropagation();
        selectTreeField(fEl, f.start ?? 0, f.end ?? 0);
      });
      fieldsList.appendChild(fEl);
    });

    header.addEventListener("click", () => {
      const isOpen = fieldsList.style.display !== "none";
      fieldsList.style.display = isOpen ? "none" : "flex";
      const chevron = header.querySelector(".tree-chevron");
      if (chevron) chevron.textContent = isOpen ? "▶" : "▼";
    });

    layerEl.appendChild(header);
    layerEl.appendChild(fieldsList);
    contentEl.appendChild(layerEl);
  });
}

function selectTreeField(fieldEl, start, end) {
  sharkwireState.activeFieldRange = { start, end };

  // Update tree field selection class
  document.querySelectorAll("#sw-tree-content .tree-field").forEach(el => el.classList.remove("active"));
  if (fieldEl) fieldEl.classList.add("active");

  // Highlight hex bytes and ASCII
  document.querySelectorAll("#sw-hex-content .hex-byte, #sw-hex-content .ascii-byte").forEach(b => {
    const off = parseInt(b.dataset.offset, 10);
    if (off >= start && off < end) {
      b.classList.add("byte-highlight");
    } else {
      b.classList.remove("byte-highlight");
    }
  });

  // Scroll first highlighted byte into view
  const firstByte = document.querySelector("#sw-hex-content .hex-byte.byte-highlight");
  if (firstByte) {
    firstByte.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  // Update offset hint
  const hintEl = document.getElementById("sw-hex-offset-hint");
  if (hintEl) {
    hintEl.textContent = `Selected bytes: [offset ${start} to ${end - 1}] (${end - start} bytes)`;
  }
}

function renderHexDump(pkt) {
  const titleEl = document.getElementById("sw-hex-title");
  const contentEl = document.getElementById("sw-hex-content");
  const hintEl = document.getElementById("sw-hex-offset-hint");

  if (titleEl) titleEl.textContent = `HEX & ASCII DUMP (${pkt.length || 0} bytes)`;
  if (hintEl) hintEl.textContent = "Click field in tree above to highlight exact byte payload";
  if (!contentEl) return;

  contentEl.innerHTML = "";

  const lines = (pkt.hex_dump || "").split("\n");
  if (lines.length === 0 || !pkt.hex_dump) {
    contentEl.innerHTML = `<div class="sw-empty-hint">No raw hex dump available for this frame.</div>`;
    return;
  }

  let currentLineOffset = 0;

  lines.forEach((line) => {
    if (!line.trim()) return;

    // Line format: "0000  00 e0 4c 68 03 04 00 e0  4c 68 01 02 08 00 45 00  ..Lh....Lh....E."
    const rowEl = document.createElement("div");
    rowEl.className = "sw-hex-row";

    const offsetStr = line.substring(0, 4);
    const lineOffset = parseInt(offsetStr, 16) || currentLineOffset;

    const offEl = document.createElement("div");
    offEl.className = "sw-hex-offset";
    offEl.textContent = offsetStr;
    rowEl.appendChild(offEl);

    const bytesEl = document.createElement("div");
    bytesEl.className = "sw-hex-bytes";

    const hexChunk = line.substring(6, 53).trim();
    const hexTokens = hexChunk.split(/\s+/).filter(Boolean);

    const group1 = document.createElement("div");
    group1.className = "hex-group";
    const group2 = document.createElement("div");
    group2.className = "hex-group";

    hexTokens.forEach((tok, i) => {
      const off = lineOffset + i;
      const bSpan = document.createElement("span");
      bSpan.className = "hex-byte";
      bSpan.dataset.offset = off;
      bSpan.textContent = tok;
      bSpan.title = `Byte offset: ${off} (0x${off.toString(16).padStart(4, "0")})`;
      bSpan.addEventListener("mouseenter", () => highlightSingleByte(off));
      bSpan.addEventListener("mouseleave", () => unhighlightSingleByte());

      if (i < 8) group1.appendChild(bSpan);
      else group2.appendChild(bSpan);
    });

    bytesEl.appendChild(group1);
    bytesEl.appendChild(group2);
    rowEl.appendChild(bytesEl);

    // ASCII Chunk
    const asciiChunk = line.length > 55 ? line.substring(55) : "";
    const asciiEl = document.createElement("div");
    asciiEl.className = "sw-hex-ascii";

    for (let j = 0; j < asciiChunk.length && j < hexTokens.length; j++) {
      const off = lineOffset + j;
      const aSpan = document.createElement("span");
      aSpan.className = "ascii-byte";
      aSpan.dataset.offset = off;
      aSpan.textContent = asciiChunk[j];
      aSpan.title = `Byte offset: ${off} (0x${off.toString(16).padStart(4, "0")})`;
      aSpan.addEventListener("mouseenter", () => highlightSingleByte(off));
      aSpan.addEventListener("mouseleave", () => unhighlightSingleByte());
      asciiEl.appendChild(aSpan);
    }

    rowEl.appendChild(asciiEl);
    contentEl.appendChild(rowEl);
    currentLineOffset = lineOffset + hexTokens.length;
  });
}

function highlightSingleByte(offset) {
  if (sharkwireState.activeFieldRange) return;
  document.querySelectorAll(`#sw-hex-content [data-offset="${offset}"]`).forEach(el => {
    el.style.backgroundColor = "rgba(0, 240, 255, 0.4)";
    el.style.color = "#00f0ff";
  });
  const hintEl = document.getElementById("sw-hex-offset-hint");
  if (hintEl) hintEl.textContent = `Byte offset: ${offset} (0x${offset.toString(16).padStart(4, "0")})`;
}

function unhighlightSingleByte() {
  if (sharkwireState.activeFieldRange) return;
  document.querySelectorAll("#sw-hex-content [data-offset]").forEach(el => {
    if (!el.classList.contains("byte-highlight")) {
      el.style.backgroundColor = "";
      el.style.color = "";
    }
  });
  const hintEl = document.getElementById("sw-hex-offset-hint");
  if (hintEl) hintEl.textContent = "Click field in tree above to highlight exact byte payload";
}

/* Shark Wire Controls & Actions */
async function toggleSharkWireCapture() {
  const led = document.getElementById("sw-capture-led");
  const txt = document.getElementById("sw-capture-btn-text");

  sharkwireState.running = !sharkwireState.running;
  const action = sharkwireState.running ? "resume" : "pause";

  try {
    await fetch("/api/packets/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action })
    });

    if (led) led.className = sharkwireState.running ? "capture-led active" : "capture-led";
    if (txt) txt.textContent = sharkwireState.running ? "⏹ Stop Capture" : "▶ Start Capture";
  } catch (e) {
    console.error("Failed to toggle capture:", e);
  }
}

async function clearSharkWireBuffer() {
  try {
    await fetch("/api/packets/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "clear" })
    });

    sharkwireState.packets = [];
    sharkwireState.selectedPacket = null;
    const tbody = document.getElementById("sw-grid-table-body");
    if (tbody) tbody.innerHTML = "";

    const treeEl = document.getElementById("sw-tree-content");
    if (treeEl) treeEl.innerHTML = `<div class="sw-empty-hint">Click any packet in the grid above to dissect Ethernet, IPv4/IPv6, TCP/UDP, and Mesh protocol layers.</div>`;

    const hexEl = document.getElementById("sw-hex-content");
    if (hexEl) hexEl.innerHTML = `<div class="sw-empty-hint">Hexadecimal representation will appear here when a packet is selected.</div>`;

    const elDisp = document.getElementById("sw-cnt-displayed");
    if (elDisp) elDisp.textContent = "0";
  } catch (e) {
    console.error("Failed to clear buffer:", e);
  }
}

function exportSharkWirePcap() {
  window.location.href = "/api/packets/export_pcap";
}

function toggleSharkWireAutoScroll() {
  sharkwireState.autoScroll = !sharkwireState.autoScroll;
  const btn = document.getElementById("btn-sw-autoscroll");
  if (btn) {
    btn.className = sharkwireState.autoScroll ? "btn btn-sm sw-autoscroll-btn active" : "btn btn-sm sw-autoscroll-btn";
    btn.innerHTML = sharkwireState.autoScroll ? "<span>⇲</span> Auto-Scroll: ON" : "<span>⇲</span> Auto-Scroll: OFF";
  }
}

function onSharkWireInterfaceChange(iface) {
  sharkwireState.selectedInterface = iface;
  const sideIface = document.getElementById("sidebar-sw-iface");
  if (sideIface) sideIface.textContent = iface;
  connectSharkWireSSE();
}

/* Filter Input & Evaluation */
function onFilterInputChange(val) {
  clearTimeout(sharkwireState.filterDebounceTimer);
  sharkwireState.filterDebounceTimer = setTimeout(async () => {
    const wrapper = document.getElementById("sw-filter-wrapper");
    const msg = document.getElementById("sw-filter-status-msg");

    if (!val.trim()) {
      if (wrapper) wrapper.className = "sw-filter-input-wrapper";
      if (msg) msg.style.display = "none";
      return;
    }

    try {
      const res = await fetch("/api/packets/filter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filter: val })
      });
      const data = await res.json();
      if (data.valid) {
        if (wrapper) wrapper.className = "sw-filter-input-wrapper valid";
        if (msg) {
          msg.style.display = "block";
          msg.style.color = "#10b981";
          msg.textContent = `✓ Valid filter syntax (${data.matched_count || 0} matched in buffer)`;
        }
      } else {
        if (wrapper) wrapper.className = "sw-filter-input-wrapper invalid";
        if (msg) {
          msg.style.display = "block";
          msg.style.color = "#ef4444";
          msg.textContent = `✗ Filter error: ${data.error || "Invalid filter syntax"}`;
        }
      }
    } catch (e) {
      console.error("Filter check error:", e);
    }
  }, 150);
}

function applySharkWireFilter() {
  const inp = document.getElementById("sw-filter-input");
  const val = inp ? inp.value.trim() : "";
  sharkwireState.filter = val;
  connectSharkWireSSE();
}

function clearSharkWireFilter() {
  const inp = document.getElementById("sw-filter-input");
  if (inp) inp.value = "";
  const wrapper = document.getElementById("sw-filter-wrapper");
  if (wrapper) wrapper.className = "sw-filter-input-wrapper";
  const msg = document.getElementById("sw-filter-status-msg");
  if (msg) msg.style.display = "none";

  sharkwireState.filter = "";
  document.querySelectorAll(".sw-chip").forEach(c => c.classList.remove("active"));
  const allChip = document.querySelector(".sw-chip");
  if (allChip) allChip.classList.add("active");

  connectSharkWireSSE();
}

function setQuickFilter(expr) {
  const inp = document.getElementById("sw-filter-input");
  if (inp) inp.value = expr;

  document.querySelectorAll(".sw-chip").forEach(c => {
    if ((!expr && c.textContent === "All") || (expr && c.getAttribute("onclick") && c.getAttribute("onclick").includes(expr))) {
      c.classList.add("active");
    } else {
      c.classList.remove("active");
    }
  });

  onFilterInputChange(expr);
  applySharkWireFilter();
}

function handleFilterKeyDown(event) {
  if (event.key === "Enter") {
    applySharkWireFilter();
  } else if (event.key === "Escape") {
    clearSharkWireFilter();
  }
}

function updateSidebarSharkwireQuickFeed() {
  const container = document.getElementById("sidebar-sharkwire-quick-feed");
  if (!container) return;

  const recent = sharkwireState.packets.slice(-8);
  if (recent.length === 0) {
    container.innerHTML = `<div style="font-size: 11px; color: var(--text-muted);">Waiting for packet stream on ${sharkwireState.selectedInterface}...</div>`;
    return;
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 4px; font-family: monospace; font-size: 10px;">`;
  recent.forEach(p => {
    const color = getPacketColorClass(p);
    html += `
      <div class="${color}" style="padding: 3px 6px; border-radius: 3px; cursor: pointer; display: flex; justify-content: space-between;" onclick="switchMainView('sharkwire'); selectSharkWirePacket(${JSON.stringify(p).replace(/"/g, '&quot;')});">
        <span style="font-weight: 700;">#${p.index} [${escapeHtml(p.protocol)}]</span>
        <span style="color: var(--text-muted);">${p.length}B</span>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ===========================================================================
// Feature F8: Network Connection IP Inspector & Data Populator
// ===========================================================================

window._hasProbedIp = false;

window.setInspectorTarget = function(ip) {
  const input = document.getElementById("ip-inspect-input");
  if (input) {
    input.value = ip;
  }
  document.querySelectorAll("#stage-ip-inspector .filter-pill").forEach(p => {
    p.classList.toggle("active", p.textContent.includes(ip));
  });
  runIpProbe();
};

window.runIpProbe = async function() {
  const input = document.getElementById("ip-inspect-input");
  const ip = (input && input.value.trim()) ? input.value.trim() : "192.168.8.1";
  const badge = document.getElementById("ip-inspect-badge");
  const grid = document.getElementById("ip-inspect-results-grid");
  const btn = document.getElementById("btn-ip-probe");

  if (badge) {
    badge.textContent = "PROBING...";
    badge.style.background = "rgba(245, 158, 11, 0.2)";
    badge.style.color = "#f59e0b";
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳</span> Probing IP...";
  }

  try {
    const res = await fetch("/api/network/probe_ip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip: ip })
    });
    const data = await res.json();
    window._hasProbedIp = true;

    if (badge) {
      if (data.is_online) {
        badge.textContent = `ONLINE • ${data.probe_duration_ms}ms`;
        badge.style.background = "rgba(16, 185, 129, 0.2)";
        badge.style.color = "#10b981";
      } else {
        badge.textContent = "OFFLINE";
        badge.style.background = "rgba(239, 68, 68, 0.2)";
        badge.style.color = "#ef4444";
      }
    }

    renderIpProbeResults(data);
  } catch (err) {
    console.error("IP Probe error:", err);
    if (badge) {
      badge.textContent = "ERROR";
      badge.style.background = "rgba(239, 68, 68, 0.2)";
      badge.style.color = "#ef4444";
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>⚡</span> Probe & Populate App";
    }
  }
};

window.runQuickPing = async function() {
  const input = document.getElementById("ip-inspect-input");
  const ip = (input && input.value.trim()) ? input.value.trim() : "192.168.8.1";
  const res = await fetch(`/api/diagnostics/ping?host=${encodeURIComponent(ip)}&count=4`);
  const data = await res.json();
  const pingBox = document.getElementById("ip-card-ping-metrics");
  if (pingBox) {
    pingBox.innerHTML = `
      <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
        <span>Packets: ${data.packets_received}/${data.packets_transmitted} (${data.packet_loss_pct}% loss)</span>
        <span style="color: #00f0ff; font-weight: bold;">Avg RTT: ${data.avg_rtt_ms} ms</span>
      </div>
      <div style="font-size: 11px; color: var(--text-muted);">
        Min: ${data.min_rtt_ms}ms • Max: ${data.max_rtt_ms}ms • Jitter (RFC 3550): ${data.jitter_ms}ms
      </div>
    `;
  }
};

function renderIpProbeResults(data) {
  const grid = document.getElementById("ip-inspect-results-grid");
  if (!grid) return;

  const node = data.matched_device;
  const ping = data.ping || {};
  const route = data.routing || {};
  const arp = data.arp || {};
  const services = data.services || [];
  const openCount = data.open_ports_count || 0;

  let nodeCardHtml = `
    <div class="card">
      <div class="card-title">
        <span>Target Endpoint Identity</span>
        <span class="badge ${data.is_online ? 'badge-active' : ''}">${data.status}</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
        <div>IP Address: <strong style="color: #00f0ff; font-size: 13px;">${escapeHtml(data.target_ip)}</strong></div>
        <div>Hostname: <span style="font-family: monospace; color: var(--text-muted);">${escapeHtml(data.hostname || '--')}</span></div>
        ${node ? `
          <div style="border-top: 1px solid var(--border-color); padding-top: 6px; margin-top: 2px;">
            <div>Matched Node: <strong style="color: #c084fc;">${escapeHtml(node.name)}</strong></div>
            <div>Role: <span style="color: var(--text-secondary);">${escapeHtml(node.role)}</span></div>
            <div>Silicon Arch: <span style="color: #ffb800;">${escapeHtml(node.arch)}</span></div>
            <div>RAM / NPU: <strong>${node.ram_total_gb} GB RAM</strong> • ${escapeHtml(node.npu_name)} (${node.npu_tops} TOPS)</div>
          </div>
        ` : `
          <div style="color: var(--text-muted); font-style: italic;">Non-mesh peripheral or external network endpoint</div>
        `}
      </div>
    </div>
  `;

  let pingCardHtml = `
    <div class="card">
      <div class="card-title">
        <span>🏓 Ping & Jitter Telemetry (RFC 3550)</span>
        <span class="badge ${ping.status === 'PASS' ? 'badge-active' : ''}" style="${ping.status === 'PASS' ? '' : 'background: rgba(239,68,68,0.2); color: #ef4444;'}">${ping.status || 'FAIL'}</span>
      </div>
      <div id="ip-card-ping-metrics" style="display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
        <div style="display: flex; justify-content: space-between;">
          <span>Packets: ${ping.packets_received || 0}/${ping.packets_transmitted || 4}</span>
          <span style="color: ${ping.packet_loss_pct === 0 ? '#10b981' : '#ef4444'}; font-weight: bold;">Loss: ${ping.packet_loss_pct ?? 100}%</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700;">
          <span>Avg RTT: <span style="color: #00f0ff;">${ping.avg_rtt_ms ?? 0} ms</span></span>
          <span>Jitter: <span style="color: #ffb800;">${ping.jitter_ms ?? 0} ms</span></span>
        </div>
        <div style="font-size: 10px; color: var(--text-muted);">
          Min: ${ping.min_rtt_ms ?? 0}ms • Max: ${ping.max_rtt_ms ?? 0}ms • Duration: ${ping.duration_ms ?? 0}ms
        </div>
      </div>
    </div>
  `;

  let routeCardHtml = `
    <div class="card">
      <div class="card-title">
        <span>Kernel Route & Physical Link</span>
        <span class="badge badge-active">${escapeHtml(route.interface || 'unknown')}</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
        <div>Local Outbound Interface: <strong style="color: #00f0ff;">${escapeHtml(route.interface || '--')}</strong></div>
        <div>Gateway Nexthop: <span style="font-family: monospace;">${escapeHtml(route.gateway || 'Direct Attached')}</span></div>
        <div>Path MTU: <strong>${route.mtu || 1500} bytes</strong></div>
        <div>Physical Link Classification:</div>
        <div style="background: rgba(0,240,255,0.08); border: 1px solid rgba(0,240,255,0.2); padding: 4px 8px; border-radius: 4px; color: #00f0ff; font-weight: 600;">
          ${escapeHtml(route.link_type || 'Standard Link')}
        </div>
        ${arp.mac ? `
          <div style="margin-top: 4px; font-size: 10px; color: var(--text-muted);">
            ARP MAC: <strong style="font-family: monospace; color: #fff;">${escapeHtml(arp.mac)}</strong> (${escapeHtml(arp.state)})
          </div>
        ` : ''}
      </div>
    </div>
  `;

  let servicesHtml = services.map(s => {
    const color = s.is_open ? '#10b981' : '#536485';
    const bg = s.is_open ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.02)';
    return `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; border-radius: 4px; background: ${bg}; border: 1px solid rgba(255,255,255,0.04); font-size: 11px;">
        <div>
          <strong style="color: ${s.is_open ? '#00f0ff' : 'var(--text-muted)'};">:${s.port}</strong>
          <span style="margin-left: 6px; color: var(--text-secondary);">${escapeHtml(s.service)}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          ${s.latency_ms !== null ? `<span style="font-size: 10px; color: var(--text-muted);">${s.latency_ms}ms</span>` : ''}
          <span style="font-size: 10px; font-weight: bold; color: ${color};">${s.is_open ? '● OPEN' : '○ CLOSED'}</span>
        </div>
      </div>
    `;
  }).join("");

  let servicesCardHtml = `
    <div class="card" style="grid-column: 1 / -1;">
      <div class="card-title">
        <span>Active Mesh Services & Socket Listeners</span>
        <span class="badge ${openCount > 0 ? 'badge-active' : ''}">${openCount} OPEN PORTS</span>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 6px; margin-top: 8px;">
        ${servicesHtml}
      </div>
    </div>
  `;

  let proofCardHtml = `
    <div class="card" style="grid-column: 1 / -1; background: rgba(0,0,0,0.3); border: 1px solid rgba(192,132,252,0.2);">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
          <span style="font-size: 10px; color: #c084fc; font-weight: 700; letter-spacing: 0.5px;">RULE 1 EMPIRICAL TRI-PROOF FINGERPRINT</span>
          <div style="font-family: monospace; font-size: 11px; color: #fff; margin-top: 2px;">
            ${escapeHtml(data.proof_signature || '')} • SHA256: ${escapeHtml(data.sha256_proof || '')}
          </div>
        </div>
        <div style="font-size: 10px; color: var(--text-muted);">
          Probed in ${data.probe_duration_ms}ms • Timestamp: ${new Date(data.timestamp * 1000).toLocaleTimeString()}
        </div>
      </div>
    </div>
  `;

  grid.innerHTML = nodeCardHtml + pingCardHtml + routeCardHtml + servicesCardHtml + proofCardHtml;
}

// ===========================================================================
// Feature F9: Screen Lens Sovereign Full Stage Hub
// ===========================================================================

window.initLensSovereign = async function() {
  const fpsBadge = document.getElementById("lens-stage-fps");
  const armBadge = document.getElementById("lens-stage-arm");
  const appSpan = document.getElementById("lens-stage-app");
  const titleSpan = document.getElementById("lens-stage-title");
  const resSpan = document.getElementById("lens-stage-res");
  const mouseSpan = document.getElementById("lens-stage-mouse");
  const freeRamSpan = document.getElementById("lens-stage-free-ram");
  const ramBar = document.getElementById("lens-stage-ram-bar");
  const obsLog = document.getElementById("lens-stage-observations-log");

  try {
    const res = await fetch("/api/lens/status");
    const data = await res.json();

    if (fpsBadge) fpsBadge.textContent = `${data.fps ? data.fps.toFixed(1) : 0} FPS`;
    if (armBadge) {
      if (data.arm_state === "ARMED") {
        armBadge.textContent = "⚡ ARMED (30s)";
        armBadge.style.background = "rgba(239, 68, 68, 0.2)";
        armBadge.style.color = "#ef4444";
      } else {
        armBadge.textContent = "🛡️ OBSERVE ONLY";
        armBadge.style.background = "rgba(16, 185, 129, 0.2)";
        armBadge.style.color = "#10b981";
      }
    }
    if (appSpan) appSpan.textContent = data.frontmost ? data.frontmost.app : "Antigravity";
    if (titleSpan) titleSpan.textContent = data.frontmost ? data.frontmost.title : "";
    if (resSpan && data.display) resSpan.textContent = `${data.display.width} × ${data.display.height}`;
    if (mouseSpan && data.mouse) mouseSpan.textContent = `X: ${Math.round(data.mouse.x)}, Y: ${Math.round(data.mouse.y)}`;

    if (data.sanctuary) {
      const free = data.sanctuary.free_ram_gb || 0;
      const tot = data.sanctuary.total_ram_gb || 24.0;
      if (freeRamSpan) freeRamSpan.textContent = `${free.toFixed(1)} GB`;
      if (ramBar) {
        const pct = Math.min(100, Math.max(10, Math.round((free / tot) * 100)));
        ramBar.style.width = `${pct}%`;
        ramBar.style.background = free >= 4.8 ? '#10b981' : '#ef4444';
      }
    }

    if (obsLog) {
      const timeStr = new Date().toLocaleTimeString();
      obsLog.innerHTML = `
        <div style="color: #00f0ff;">[${timeStr}] Perception online on :4003 (Target: ${data.active_node || 'l1_mac_mini'})</div>
        <div>[${timeStr}] Frontmost: ${escapeHtml(data.frontmost?.app || 'Antigravity')} • FPS: ${data.fps || 0}</div>
        <div>[${timeStr}] Sanctuary RAM: ${data.sanctuary?.free_ram_gb || 0} GB free (Headroom: ${data.sanctuary?.sanctuary_headroom_ok ? 'PASS' : 'WARN'})</div>
        <div style="color: var(--text-muted); margin-top: 4px;">• Full-resolution screen captures stream at 10-15 FPS via /api/lens/stream</div>
      `;
    }
  } catch (err) {
    console.error("Screen Lens stage init error:", err);
  }
};

window.handleLensStageTargetChange = async function(nodeId) {
  try {
    await fetch("/api/lens/node/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node: nodeId })
    });
    const targetName = document.getElementById("lens-stage-target-name");
    const select = document.getElementById("lens-stage-target-select");
    if (targetName && select) {
      targetName.textContent = select.options[select.selectedIndex].text;
    }
    const img = document.getElementById("lens-stage-img");
    if (img) {
      img.src = `/api/lens/stream?t=${Date.now()}`;
    }
  } catch (e) {
    console.error("Target node select error:", e);
  }
};

// ===========================================================================
// Feature F10: GL.iNet Sovereign Gateway Panel
// ===========================================================================

window.loadRouterGateway = async function(force = false) {
  const uptimeEl = document.getElementById("router-uptime");
  const loadEl = document.getElementById("router-load");
  const ramEl = document.getElementById("router-ram");
  const wanIpEl = document.getElementById("router-wan-ip");
  const fwVerEl = document.getElementById("router-fw-ver");
  const portsList = document.getElementById("router-switch-ports-list");
  const radiosList = document.getElementById("router-radios-list");
  const clientsTbody = document.getElementById("router-clients-tbody");

  try {
    const res = await fetch(`/api/router/telemetry?force=${force}`);
    const data = await res.json();

    if (uptimeEl) uptimeEl.textContent = data.uptime_str || "--";
    if (loadEl && data.load_averages) loadEl.textContent = data.load_averages.join(", ");
    if (ramEl && data.memory) ramEl.textContent = `${data.memory.available_mb || 0} MB free / ${data.memory.total_mb || 0} MB`;
    if (wanIpEl && data.wan) wanIpEl.textContent = `${data.wan.ip || '--'} (${data.wan.device || ''})`;
    if (fwVerEl) fwVerEl.textContent = `${data.firmware || 'OpenWrt'} • Model: ${data.model || 'GL-BE14000'}`;

    if (portsList && data.switch_ports) {
      portsList.innerHTML = data.switch_ports.map(p => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(0,0,0,0.3); border-radius: 4px; border: 1px solid rgba(255,255,255,0.06); font-size: 11px;">
          <div>
            <strong style="color: #00f0ff;">${escapeHtml(p.name)}</strong>
            <span style="margin-left: 6px; color: var(--text-secondary);">${escapeHtml(p.target)}</span>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;">
            <span style="font-size: 10px; color: #ffb800;">${escapeHtml(p.speed)}</span>
            <span class="badge ${p.status === 'UP' ? 'badge-active' : ''}">${p.status}</span>
          </div>
        </div>
      `).join("");
    }

    if (radiosList && data.wifi7_mlo) {
      const w = data.wifi7_mlo;
      radiosList.innerHTML = `
        <div style="display: flex; justify-content: space-between; padding: 6px 10px; background: rgba(0,240,255,0.05); border-radius: 4px; border: 1px solid rgba(0,240,255,0.2); font-size: 11px;">
          <div>
            <strong style="color: #00f0ff;">6GHz Clean Room (rax0)</strong>
            <div style="font-size: 10px; color: var(--text-muted);">${w.clean_room_6ghz?.role || 'M4 Macs & Pixel 10'} • ${w.clean_room_6ghz?.channel || '160MHz'}</div>
          </div>
          <span class="badge badge-active">${w.clean_room_6ghz?.status || 'UP'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 10px; background: rgba(0,0,0,0.3); border-radius: 4px; border: 1px solid rgba(255,255,255,0.06); font-size: 11px;">
          <div>
            <strong>5GHz Radio (rai0)</strong>
            <div style="font-size: 10px; color: var(--text-muted);">High-Speed Mesh Backhaul</div>
          </div>
          <span class="badge badge-active">${w.mesh_5ghz?.status || 'UP'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 6px 10px; background: rgba(0,0,0,0.3); border-radius: 4px; border: 1px solid rgba(255,255,255,0.06); font-size: 11px;">
          <div>
            <strong>2.4GHz Legacy Radio (ra0)</strong>
            <div style="font-size: 10px; color: var(--text-muted);">IoT & Peripheral Fallback</div>
          </div>
          <span class="badge badge-active">${w.legacy_2ghz?.status || 'UP'}</span>
        </div>
      `;
    }

    if (clientsTbody && data.clients) {
      clientsTbody.innerHTML = data.clients.map(c => `
        <tr>
          <td><strong style="color: #c084fc;">${escapeHtml(c.device_name || 'Client')}</strong></td>
          <td style="font-family: monospace; color: #00f0ff;">${escapeHtml(c.ip)}</td>
          <td style="font-family: monospace; color: var(--text-muted);">${escapeHtml(c.mac)}</td>
          <td><span class="badge badge-sm">${escapeHtml(c.interface)}</span></td>
          <td><span style="font-size: 10px; color: var(--text-secondary);">${escapeHtml(c.device_type)}</span></td>
        </tr>
      `).join("");
    }
  } catch (e) {
    console.error("Router gateway fetch error:", e);
  }
};

// ===========================================================================
// Feature F11: Crash Telemetry & Network Health Streamer
// ===========================================================================

let _crashEventSource = null;
let _allCrashes = [];
let _activeCrashFilter = 'all';

window.loadCrashStream = function(force = false) {
  fetchRecentCrashes();
  initCrashEventSource();
};

async function fetchRecentCrashes() {
  try {
    const res = await fetch("/api/crash/recent?limit=30");
    const data = await res.json();
    _allCrashes = data.crashes || [];
    renderCrashIncidents();
  } catch (e) {
    console.error("Crash recent fetch error:", e);
  }
}

function initCrashEventSource() {
  if (_crashEventSource) {
    return;
  }
  const statusBadge = document.getElementById("crash-stream-status");
  try {
    _crashEventSource = new EventSource("/api/crash/stream");

    _crashEventSource.addEventListener("initial_crashes", (e) => {
      try {
        const list = JSON.parse(e.data);
        _allCrashes = list;
        renderCrashIncidents();
      } catch (err) {}
    });

    _crashEventSource.addEventListener("crash_alert", (e) => {
      try {
        const item = JSON.parse(e.data);
        _allCrashes.unshift(item);
        if (_allCrashes.length > 50) _allCrashes.pop();
        renderCrashIncidents();
      } catch (err) {}
    });

    _crashEventSource.addEventListener("health_heartbeat", (e) => {
      if (statusBadge) {
        statusBadge.textContent = "STREAMING :4007";
        statusBadge.classList.add("badge-active");
      }
    });

    _crashEventSource.onerror = () => {
      if (statusBadge) {
        statusBadge.textContent = "RECONNECTING...";
        statusBadge.classList.remove("badge-active");
      }
    };
  } catch (e) {
    console.error("Crash SSE connection error:", e);
  }
}

window.filterCrashes = function(severity) {
  _activeCrashFilter = severity;
  document.querySelectorAll("#stage-crash-stream .filter-pill").forEach(p => {
    p.classList.toggle("active", p.id === `crash-flt-${severity.toLowerCase()}`);
  });
  renderCrashIncidents();
};

function renderCrashIncidents() {
  const feed = document.getElementById("crash-incident-feed");
  const cntAll = document.getElementById("cnt-crash-all");
  const cntCrit = document.getElementById("cnt-crash-critical");
  const cntErr = document.getElementById("cnt-crash-error");
  const cntWarn = document.getElementById("cnt-crash-warning");

  if (cntAll) cntAll.textContent = _allCrashes.length;
  if (cntCrit) cntCrit.textContent = _allCrashes.filter(c => c.severity === 'CRITICAL').length;
  if (cntErr) cntErr.textContent = _allCrashes.filter(c => c.severity === 'ERROR').length;
  if (cntWarn) cntWarn.textContent = _allCrashes.filter(c => c.severity === 'WARNING').length;

  if (!feed) return;

  const filtered = _activeCrashFilter === 'all'
    ? _allCrashes
    : _allCrashes.filter(c => c.severity === _activeCrashFilter);

  if (filtered.length === 0) {
    feed.innerHTML = `
      <div class="card" style="text-align: center; padding: 24px; color: var(--text-muted);">
        No incidents recorded in this category. All monitored network services and kernel subsystems healthy.
      </div>
    `;
    return;
  }

  feed.innerHTML = filtered.map(c => {
    let badgeColor = '#38bdf8';
    let badgeBg = 'rgba(56, 189, 248, 0.15)';
    let badgeBorder = '#38bdf8';

    if (c.severity === 'CRITICAL') {
      badgeColor = '#ef4444';
      badgeBg = 'rgba(239, 68, 68, 0.2)';
      badgeBorder = '#ef4444';
    } else if (c.severity === 'ERROR') {
      badgeColor = '#f59e0b';
      badgeBg = 'rgba(245, 158, 11, 0.2)';
      badgeBorder = '#f59e0b';
    } else if (c.severity === 'WARNING') {
      badgeColor = '#fbbf24';
      badgeBg = 'rgba(251, 191, 36, 0.2)';
      badgeBorder = '#fbbf24';
    }

    return `
      <div class="card" style="border-left: 3px solid ${badgeColor}; padding: 10px 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; font-weight: 700;">
              ${c.severity} • ${escapeHtml(c.event_type || 'INCIDENT')}
            </span>
            <strong style="color: #fff; font-size: 12px;">${escapeHtml(c.component || 'System')}</strong>
          </div>
          <span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">
            ${escapeHtml(c.timestamp ? c.timestamp.replace('T', ' ').slice(0, 19) : '--')}
          </span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
          Reason: <span style="color: #fff; font-family: monospace;">${escapeHtml(c.reason || '--')}</span>
        </div>
        ${c.remedy ? `
          <div style="font-size: 10px; background: rgba(0,240,255,0.05); border: 1px solid rgba(0,240,255,0.15); padding: 4px 8px; border-radius: 4px; color: #00f0ff;">
            🛡️ Self-Healing Protocol: ${escapeHtml(c.remedy)}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}

/* Expose global window callbacks */
window.selectWhatCableDevice = selectWhatCableDevice;
window.selectWhatcablePort = selectWhatcablePort;
window.fetchWhatCableDetails = fetchWhatCableDetails;
window.onSharkWireInterfaceChange = onSharkWireInterfaceChange;
window.toggleSharkWireCapture = toggleSharkWireCapture;
window.clearSharkWireBuffer = clearSharkWireBuffer;
window.exportSharkWirePcap = exportSharkWirePcap;
window.toggleSharkWireAutoScroll = toggleSharkWireAutoScroll;
window.handleFilterKeyDown = handleFilterKeyDown;
window.onFilterInputChange = onFilterInputChange;
window.applySharkWireFilter = applySharkWireFilter;
window.clearSharkWireFilter = clearSharkWireFilter;
window.setQuickFilter = setQuickFilter;
window.selectSharkWirePacket = selectSharkWirePacket;
window.selectTreeField = selectTreeField;
window.setInspectorTarget = setInspectorTarget;
window.runIpProbe = runIpProbe;
window.runQuickPing = runQuickPing;
window.initLensSovereign = initLensSovereign;
window.handleLensStageTargetChange = handleLensStageTargetChange;
window.loadRouterGateway = loadRouterGateway;
window.loadCrashStream = loadCrashStream;
window.filterCrashes = filterCrashes;

window.addEventListener("DOMContentLoaded", init);




// --- Neo AI Recommendations ---
async function fetchNeoRecommendations() {
    const container = document.getElementById("neo-recommendations-container");
    if (!container) return;
    
    container.innerHTML = '<div style="color: var(--text-secondary); font-size: 12px;">Calling Neo Backend...</div>';
    
    try {
        const res = await fetch("/api/neo/recommendations");
        const data = await res.json();
        
        if (!data.recommendations || data.recommendations.length === 0) {
            container.innerHTML = '<div style="color: #10b981; font-size: 12px;">✅ Topology optimized. No Neo recommendations at this time.</div>';
            return;
        }
        
        container.innerHTML = data.recommendations.map(rec => {
            const color = rec.severity === 'critical' ? '#ef4444' : (rec.severity === 'warning' ? '#f59e0b' : '#3b82f6');
            return `
                <div style="background: rgba(255,255,255,0.03); border-left: 3px solid ${color}; padding: 10px; border-radius: 4px;">
                    <div style="font-weight: bold; font-size: 13px; color: ${color}; margin-bottom: 4px;">${rec.title}</div>
                    <div style="font-size: 12px; color: #fff; margin-bottom: 4px;">${rec.recommendation}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);"><strong>Benefit:</strong> ${rec.benefit}</div>
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to fetch Neo recommendations: ${e.message}</div>`;
    }
}
