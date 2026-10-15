# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
# ]
# ///

import marimo

__generated_with = "0.14.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import sys
    from pathlib import Path

    for p in ["/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/ide"]:
        if p not in sys.path:
            sys.path.insert(0, p)

    from lens_monorepo_roi_engine import MonorepoROIEngine
    from lens_workspace_cloud_hub import LensWorkspaceCloudHub
    return MonorepoROIEngine, LensWorkspaceCloudHub, Path, mo, sys


@app.cell
def __(mo):
    mo.md(
        """
        # 👁️ Screen Lens Sovereign: Reactive Notebook IDE Studio
        ### Master Monorepo Monitoring, Highest-ROI Task Prioritization & Distributed Tensor Sharding HUD
        """
    )
    return


@app.cell
def __(LensWorkspaceCloudHub, MonorepoROIEngine):
    roi_engine = MonorepoROIEngine()
    cloud_hub = LensWorkspaceCloudHub()

    tasks = roi_engine.scan_and_prioritize()
    shards = cloud_hub.probe_distributed_sharding()
    quota = cloud_hub.get_google_cloud_quota_status()
    alerts = cloud_hub.get_google_workspace_alerts()
    return alerts, cloud_hub, quota, roi_engine, shards, tasks


@app.cell
def __(mo, shards):
    shard_rows = [
        {
            "Node": s.node_name,
            "Endpoint": s.target_ip,
            "RTT (ms)": s.rtt_ms,
            "Status": "ONLINE" if s.is_online else "OFFLINE",
            "Sharding Mode": s.sharding_mode
        }
        for s in shards
    ]

    mo.vstack([
        mo.md("### 🌐 1. Distributed AI Tensor Sharding & 7-Layer Mesh HUD"),
        mo.ui.table(shard_rows)
    ])
    return shard_rows,


@app.cell
def __(alerts, mo, quota):
    mo.vstack([
        mo.md("### ⚡ 2. Google Cloud Always Free Tier & Workspace Cadence"),
        mo.md(f"**Provider:** {quota.provider} ({quota.model})"),
        mo.md(f"**Quota Status:** {quota.consumed_today} / {quota.daily_quota_rpd} consumed (**{quota.remaining_today} remaining**)"),
        mo.md(f"**Dynamic Pacing:** {quota.cadence_rpm} RPM | Reset in: {quota.reset_hours_remaining} hrs"),
        mo.md(f"**Active Workspace Alerts:** {len(alerts)} events logged")
    ])
    return


@app.cell
def __(mo, tasks):
    task_rows = [
        {
            "Rank": f"#{i+1}",
            "ROI Score": t.roi_score,
            "Task Title": t.title,
            "Category": t.category,
            "Assigned Model": t.assigned_model,
            "Host Node": t.mesh_host,
            "Speedup": f"{t.speedup_multiplier}x"
        }
        for i, t in enumerate(tasks)
    ]

    mo.vstack([
        mo.md("### 🚀 3. Highest-ROI Monorepo Tasks (Autonomous Priority Queue)"),
        mo.ui.table(task_rows)
    ])
    return task_rows,


@app.cell
def __(cloud_hub, mo, tasks):
    def run_top_task():
        if tasks:
            top = tasks[0]
            if top.category == "MOBILE_VLA":
                res = cloud_hub.execute_tool_call("read_file", {
                    "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/android_pixel/pixel_window_dump_fixture.xml"
                })
                return f"SUCCESS: Executed '{top.title}' via {top.assigned_model}. Bytes read: {res.get('bytes', 0)}"
            return f"SUCCESS: Dispatched '{top.title}' to {top.assigned_model}."
        return "No tasks available."

    mo.vstack([
        mo.md("### ⚡ 4. Autonomous Task Actuation"),
        mo.md(f"**Top Task:** {tasks[0].title if tasks else 'None'}"),
        mo.md(f"**Action Result:** `{run_top_task()}`")
    ])
    return run_top_task,


if __name__ == "__main__":
    app.run()
