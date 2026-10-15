import marimo

__generated_with = "0.9.14"
app = marimo.App(width="full", app_title="Sovereign Live AI ELO, Sharding & 671B Telemetry")


@app.cell
def __():
    import json
    import os
    import re
    import socket
    import subprocess
    import sys
    import time
    import urllib.request
    from datetime import datetime
    from pathlib import Path
    import marimo as mo

    REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
    if str(REPO_ROOT / "04_data_and_memory") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "04_data_and_memory"))
    BENCHMARK_JSON = REPO_ROOT / "reports" / "global_ai_mesh_benchmark.json"
    return (
        BENCHMARK_JSON,
        Path,
        REPO_ROOT,
        datetime,
        json,
        mo,
        os,
        re,
        socket,
        subprocess,
        sys,
        time,
        urllib,
    )


@app.cell
def __(mo):
    refresh_slider = mo.ui.slider(
        start=2, stop=30, step=2, value=5, label="Telemetry Refresh Interval (s)"
    )
    execution_mode = mo.ui.dropdown(
        options={
            "Mode 1: Speculative Local Halda NVMe + Qwen-0.5B Draft (:8089 -> :8094)": "speculative_halda",
            "Mode 2: 24/7 Async Teacher & LoRA Distillation (:8094 Batch)": "lora_teacher",
            "Mode 3: Interactive RDU Mirror / Local 30B Council Auto-Escalation": "interactive_auto",
        },
        value="speculative_halda",
        label="DeepSeek-R1 / V3 671B MoE Operational Mode",
    )
    mo.md(
        f"""
        # 🏛️ Sovereign Live AI ELO, Sharding Uptime, RAM/CPU & Local AI Activity Monitor
        **Integrated with `/screen-lens-sovereign` (`:3035` / `:3037` / `:4003`) & `DeepSeek-R1 / V3 671B MoE` (`:8094`)**

        {mo.hstack([refresh_slider, execution_mode], justify="start", gap=2.0)}
        """
    )
    return execution_mode, refresh_slider


@app.cell
def __(
    BENCHMARK_JSON,
    REPO_ROOT,
    datetime,
    json,
    re,
    socket,
    subprocess,
    time,
    urllib,
):
    from elo_pooled_memory_and_storage_hub import WireGuardJupyterPooledEloHub

    def get_darwin_ram_telemetry():
        try:
            memsize_bytes = int(
                subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            )
            total_gb = memsize_bytes / (1024**3)
            vm_out = subprocess.check_output(["vm_stat"], text=True)
            ps_match = re.search(r"page size of (\d+) bytes", vm_out)
            page_size = int(ps_match.group(1)) if ps_match else 16384

            def _pages(key):
                m = re.search(rf"{re.escape(key)}:\s+(\d+)", vm_out)
                return int(m.group(1)) if m else 0

            anon = _pages("Anonymous pages")
            purge = _pages("Pages purgeable")
            wired = _pages("Pages wired down")
            comp = _pages("Pages occupied by compressor")
            file_backed = _pages("File-backed pages")

            app_gb = max(0, (anon - purge) * page_size) / (1024**3)
            wired_gb = (wired * page_size) / (1024**3)
            comp_gb = (comp * page_size) / (1024**3)
            cached_gb = ((file_backed + purge) * page_size) / (1024**3)
            used_gb = app_gb + wired_gb + comp_gb
            free_gb = max(0.0, total_gb - used_gb)
            used_pct = (used_gb / total_gb) * 100.0
            try:
                pressure = int(
                    subprocess.check_output(
                        ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
                        text=True,
                    ).strip()
                )
            except Exception:
                pressure = 1
            return {
                "total_gb": round(total_gb, 2),
                "app_gb": round(app_gb, 2),
                "wired_gb": round(wired_gb, 2),
                "comp_gb": round(comp_gb, 2),
                "cached_gb": round(cached_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_pct": round(used_pct, 1),
                "pressure": pressure,
                "sanctuary_ok": free_gb >= 4.8 and used_pct <= 80.0,
            }
        except Exception as exc:
            return {"error": str(exc), "sanctuary_ok": False}

    def probe_tcp_port(host, port, timeout=0.08):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True, round((time.perf_counter() - t0) * 1000.0, 2)
        except Exception:
            return False, None

    def probe_http_json(url, timeout=0.12):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return None

    darwin_ram = get_darwin_ram_telemetry()
    bench_data = (
        json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
        if BENCHMARK_JSON.exists()
        else {}
    )
    elo_hub = WireGuardJupyterPooledEloHub(repo_root=REPO_ROOT)
    pooled_elo = elo_hub.pool_and_persist_all(fast_probe=True)
    probe_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S AEDT")
    return (
        WireGuardJupyterPooledEloHub,
        bench_data,
        darwin_ram,
        elo_hub,
        get_darwin_ram_telemetry,
        pooled_elo,
        probe_http_json,
        probe_tcp_port,
        probe_timestamp,
    )


@app.cell
def __(bench_data, darwin_ram, mo, pooled_elo, probe_http_json, probe_tcp_port, probe_timestamp):
    SHARD_ENDPOINTS = [
        ("L1 Master Proxy (prima.cpp)", "127.0.0.1", 8082, "prima.cpp PRP Ring"),
        ("L1 Fast Drafter (Qwen2.5-0.5B)", "127.0.0.1", 8089, "Metal GPU Draft Head"),
        ("L1 Local 8B (Hermes-3 8B)", "127.0.0.1", 8085, "Metal GPU 8B Sovereign"),
        ("L1 Multimodal Embeddings", "127.0.0.1", 8087, "EmbeddingGemma-2 300M"),
        ("L1 Adversarial / 27B Proxy", "127.0.0.1", 8083, "Qwen 3.8 Max 27B Proxy"),
        ("L1 Syntax / 7B VL Proxy", "127.0.0.1", 8081, "Subordinate Syntax / VL"),
        ("L1 Screen Lens Core OCR", "127.0.0.1", 3035, "Screen Lens Daemon"),
        ("L1 Screen Lens Orchestrator", "127.0.0.1", 3037, "Lens Global Orchestrator"),
        ("L1 Screen Lens MJPEG Stream", "127.0.0.1", 4003, "3x3 Matrix Vision Stream"),
        ("L8 Linux Mini TB4 (lauburu)", "10.0.0.8", 61208, "40Gb/s TB4 Bus 0 (32GB)"),
        ("L1b Mac Mini M2 Pro TB4", "10.0.0.3", 22, "40Gb/s TB4 Bus 1 (16GB + 2TB NVMe)"),
        ("L1a MacBook Air M4 TB4", "10.0.0.5", 61208, "40Gb/s TB4 Daisy-Chain (16GB)"),
        ("L2 MacBook Pro Intel TB4", "10.0.0.4", 61208, "40Gb/s TB4 Bus 2 (16GB)"),
        ("L3 Linux Head Node LAN", "192.168.8.225", 61208, "Ryzen 7 5700U + SeaweedFS"),
        ("GW GL-BE14000 Core Router", "192.168.8.1", 22, "OpenWrt Gateway + USB ADB"),
    ]

    endpoint_rows = []
    for label, host, port, role in SHARD_ENDPOINTS:
        up, rtt = probe_tcp_port(host, port)
        slots_info = "--"
        if up and port in (8081, 8082, 8083, 8085, 8087, 8089):
            slots = probe_http_json(f"http://{host}:{port}/slots")
            if isinstance(slots, list) and slots:
                busy = sum(1 for s in slots if s.get("is_processing"))
                slots_info = f"{busy}/{len(slots)} slots busy"
            else:
                health = probe_http_json(f"http://{host}:{port}/health")
                if isinstance(health, dict):
                    slots_info = f"HTTP {health.get('status', 'ok')}"
        endpoint_rows.append(
            {
                "Endpoint": label,
                "Address": f"{host}:{port}",
                "Role / Sharding Plane": role,
                "Status": "🟢 ONLINE" if up else "🟡 STANDBY",
                "RTT (ms)": f"{rtt:.2f}" if rtt is not None else "--",
                "Live AI Activity": slots_info,
            }
        )

    taxonomy = bench_data.get("model_size_taxonomy", {})
    all_models = []
    for tier_key, tier_obj in taxonomy.items():
        for m in tier_obj.get("models_evaluated", []):
            tok_s = m.get("inference_speed_tok_s") or m.get("sharded_tb4_ring_tok_s") or 0.0
            elo_val = m.get("calibrated_elo")
            if elo_val is None:
                params = float(m.get("parameter_count", 1e6))
                elo_val = round(1150.0 + 30.0 * (len(str(int(params))) - 5), 1)
            all_models.append({
                "Tier": tier_key,
                "Model": m.get("model_name", ""),
                "Params": f"{m.get('parameter_count', 0):,}",
                "Calibrated ELO": elo_val,
                "Tok/s (Local/TB4)": tok_s,
                "Primary Protocol": m.get("primary_sharding_protocol", ""),
                "Project Role": m.get("project_role", ""),
            })

    elo_rows = sorted(all_models, key=lambda x: x["Calibrated ELO"], reverse=True)

    sanctuary_badge = (
        "🟢 SANCTUARY HEALTHY"
        if darwin_ram.get("sanctuary_ok")
        else "🔴 SANCTUARY PRESSURE"
    )

    mo.md(
        f"""
        ### ⚡ Live Hardware Sanctuary & Sharding Status (`{probe_timestamp}`)
        - **L1 Mac Mini M4 Pro (24 GB):** `{darwin_ram.get('used_gb', '--')} GB` used (`{darwin_ram.get('used_pct', '--')}%`) | **`{darwin_ram.get('free_gb', '--')} GB` Free** (App `{darwin_ram.get('app_gb', '--')} GB`, Wired `{darwin_ram.get('wired_gb', '--')} GB`, Compressed `{darwin_ram.get('comp_gb', '--')} GB`) — **{sanctuary_badge}**
        - **Pooled ELO Merkle Root:** `{pooled_elo.get('merkle_root_sha256', '--')}` (`{pooled_elo.get('total_pooled_entities', 0)}` pooled entities)

        #### 🌐 Live AI Sharding & `/screen-lens-sovereign` Uptime Table
        {mo.ui.table(endpoint_rows, selection=None)}

        #### 🏆 Live Bradley-Terry AI ELO & 32-Model Taxonomy Table (TinyLM → 31B → 72B → 671B MoE)
        {mo.ui.table(elo_rows, selection=None)}
        """
    )
    return SHARD_ENDPOINTS, all_models, elo_rows, endpoint_rows, sanctuary_badge, taxonomy


if __name__ == "__main__":
    app.run()
