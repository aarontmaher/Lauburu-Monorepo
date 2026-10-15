# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "httpx",
# ]
# ///

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import urllib.request
    import json
    import time
    from pathlib import Path
    return json, mo, time, urllib, Path


@app.cell
def __(mo):
    mo.md(
        """
        # 🛡️ Screen Lens • Unified Live Tri-Audit & Terminal Telemetry Hub
        > **Single-Source Live Dashboard:** Integrating **Port 4003 Live Screen Stream**, real-time TUI terminal telemetry, and live Tri-Proof verification into an interactive reactive workspace.
        """
    )
    return


@app.cell
def __(mo):
    # Embedded Port 4003 Live Screen Stream Card
    stream_widget = mo.Html(
        """
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-family: monospace;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block;"></span>
                    <strong style="color: #f8fafc; font-size: 13px;">LIVE RETINA SCREEN BROADCAST</strong>
                    <span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;">10-15 FPS</span>
                </div>
                <span style="color: #38bdf8; font-size: 12px;">http://localhost:4003/stream.mjpg</span>
            </div>
            <div style="background: #000; border-radius: 8px; overflow: hidden; border: 1px solid #334155; text-align: center;">
                <img src="http://localhost:4003/stream.mjpg" alt="Screen Lens Live Stream" style="width: 100%; height: auto; display: block; border-radius: 8px;" />
            </div>
        </div>
        """
    )
    return (stream_widget,)


@app.cell
def __(json, mo, urllib):
    # Fetch live Tri-Audit process data
    try:
        req = urllib.request.urlopen("http://127.0.0.1:4003/api/triaudit/live", timeout=2.0)
        tri_audit_data = json.loads(req.read().decode())
    except Exception as e:
        tri_audit_data = {"error": str(e), "overall_verdict": "UNAVAILABLE"}

    verdict = tri_audit_data.get("overall_verdict", "AUDITING")
    badge_color = "#10b981" if verdict == "VERIFIED_PASS" else "#f59e0b"

    p1 = tri_audit_data.get("proof_1_actuation", {})
    p2 = tri_audit_data.get("proof_2_checksum", {})
    p3 = tri_audit_data.get("proof_3_visual", {})

    tri_audit_ui = mo.Html(
        f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px; font-family: monospace; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <strong style="color: #818cf8; font-size: 14px;">🛡️ LIVE TRI-AUDIT PROCESS MONITOR</strong>
                    <span style="background: rgba(16, 185, 129, 0.2); color: {badge_color}; border: 1px solid {badge_color}; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;">{verdict}</span>
                </div>
                <span style="color: #94a3b8; font-size: 11px;">Cardinal Law #1 & Rule 5 Interceptor</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
                <!-- Gate 1 -->
                <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="color: #e2e8f0; font-size: 12px;">1. Proof 1 (Actuation)</strong>
                        <span style="color: #34d399; font-weight: bold; font-size: 10px;">{p1.get('status', '--')}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 11px; margin-bottom: 8px;">{p1.get('description', '--')}</div>
                </div>
                <!-- Gate 2 -->
                <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="color: #e2e8f0; font-size: 12px;">2. Proof 2 (Checksum)</strong>
                        <span style="color: #34d399; font-weight: bold; font-size: 10px;">{p2.get('status', '--')}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 11px; margin-bottom: 8px;">{p2.get('description', '--')}</div>
                </div>
                <!-- Gate 3 -->
                <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="color: #e2e8f0; font-size: 12px;">3. Proof 3 (Visual)</strong>
                        <span style="color: #34d399; font-weight: bold; font-size: 10px;">{p3.get('status', '--')}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 11px; margin-bottom: 8px;">{p3.get('description', '--')}</div>
                </div>
            </div>
        </div>
        """
    )
    return (tri_audit_ui,)


@app.cell
def __(json, mo, urllib):
    # Fetch live TUI and terminal telemetry
    try:
        req = urllib.request.urlopen("http://127.0.0.1:4003/api/telemetry/live", timeout=2.0)
        telem = json.loads(req.read().decode())
    except Exception as e:
        telem = {"error": str(e), "terminal_logs": []}

    logs_html = "<br>".join(telem.get("terminal_logs", ["No logs available."]))
    speeds = telem.get("model_speeds", {})

    tui_widget = mo.Html(
        f"""
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px; font-family: monospace; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <strong style="color: #38bdf8; font-size: 13px;">⚡ LIVE TUI TERMINAL & INFERENCE SPEED TELEMETRY</strong>
                <span style="color: #10b981; font-size: 11px; font-weight: bold;">Mach RAM: {telem.get('mach_ram', {}).get('available_gb', '--')} GB</span>
            </div>
            <!-- Log Console -->
            <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; font-size: 11px; color: #34d399; height: 160px; overflow-y: auto; line-height: 1.5; margin-bottom: 10px;">
                {logs_html}
            </div>
            <!-- Speed Matrix -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size: 11px; text-align: center;">
                <div style="background: #020617; padding: 6px; border-radius: 6px; border: 1px solid #1e293b;"><span style="color: #94a3b8;">SmolLM2-135M:</span> <b style="color: #38bdf8;">{speeds.get('smollm2_135m', '--')}</b></div>
                <div style="background: #020617; padding: 6px; border-radius: 6px; border: 1px solid #1e293b;"><span style="color: #94a3b8;">SmolVLM-2.2B:</span> <b style="color: #c084fc;">{speeds.get('smolvlm_2b', '--')}</b></div>
                <div style="background: #020617; padding: 6px; border-radius: 6px; border: 1px solid #1e293b;"><span style="color: #94a3b8;">Gemma-2-2B:</span> <b style="color: #fbbf24;">{speeds.get('gemma_2b', '--')}</b></div>
                <div style="background: #020617; padding: 6px; border-radius: 6px; border: 1px solid #1e293b;"><span style="color: #94a3b8;">Qwen-2.5-7B:</span> <b style="color: #34d399;">{speeds.get('qwen_7b', '--')}</b></div>
            </div>
        </div>
        """
    )
    return (tui_widget,)


@app.cell
def __(mo, stream_widget, tui_widget, tri_audit_ui):
    # Compose unified interactive layout
    mo.vstack([
        stream_widget,
        tui_widget,
        tri_audit_ui
    ], gap=1)
    return


if __name__ == "__main__":
    app.run()
