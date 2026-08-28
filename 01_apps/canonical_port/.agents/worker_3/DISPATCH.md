## 2026-08-29T04:46:57Z
You are Worker 3 for Canonical Port TUI Screen 6 — Architectural Upgrade & Library Alignment.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work.

Reference Files:
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/ORIGINAL_REQUEST.md` (specifically the new Follow-up section)
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/PROJECT.md`
- `backend/training_telemetry_collector.py`
- `tui/widgets/training_pipeline_widget.py`
- `tui/widgets/lauburu_gyms_widget.py`
- `tui/screens/training_screen.py`
- `tui/views/training_view.py`

Your Task:
Upgrade the codebase to strictly implement the 4 finalized architectural paradigms:

1. **Native Async Integration:**
   - In `tui/widgets/training_pipeline_widget.py`, `tui/widgets/lauburu_gyms_widget.py`, and `backend/training_telemetry_collector.py`, ensure state updates use pure `asyncio` routines.
   - Bind asynchronous stream updates directly to Textual `reactive` variables (`reactive.watch` / reactive properties) so the UI repaints instantly on the event loop without manual thread locks.
2. **DSP Ecosystem (`NumPy` / `SciPy`):**
   - For Spatial Grappling 3D Gym and biometrics modules, use `numpy` arrays (`np.ndarray`) and `scipy.signal` (e.g. `scipy.signal.medfilt` or filtering / kinematics array math) for calculating joint torque tau = 120.0 * r * |sin(theta)| across angular position series and filtering IMU/ECG signals.
3. **Mesh Healing Gym (Tailscale Local IPC):**
   - For the Mesh Healing AI Gym telemetry in `backend/training_telemetry_collector.py` and `tui/widgets/lauburu_gyms_widget.py`, implement an asynchronous HTTP client using `aiohttp` and `aiohttp.UnixConnector(path="/var/run/tailscale/tailscaled.sock")` to query local Tailscale daemon status (`/localapi/v0/status`), falling back cleanly if the socket is not mounted or offline (Rule #0). Do NOT use `subprocess.run(["tailscale", "status"])`.
4. **Subprocess Orchestration:**
   - For AI Stealth Compute and Red/Blue Arena background stream capture, implement `asyncio.create_subprocess_exec` to capture non-blocking stdout/stderr lines asynchronously.

5. **Test & Verification**:
   - Update tests in `tests/unit/` and `tests/e2e/` to verify these paradigms.
   - Run:
     `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx,psutil,numpy,scipy,aiohttp pytest tests/unit/ tests/e2e/ -v`
     `uv run --with rich,textual,pyyaml,pytest,pytest-asyncio,httpx,psutil,numpy,scipy,aiohttp python tui/verify_tui.py`
   - Verify 100% tests pass.

Write your report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/worker_3/handoff.md` and send a message when done.
