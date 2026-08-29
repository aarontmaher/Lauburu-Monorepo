# Original User Request

## Initial Request — 2026-08-29T19:01:50+10:00

Implement and deploy the Unified Lauburu Front-Facing App Architecture and Multi-Mode Game Arena, leveraging Cloud AIs strictly for zero-biometric frontend/PWA UI scaffolding, while locking 100% of physiological biometrics (Bicep 512Hz ECG, PTT blood pressure, PPG overnight sleep analysis, workout auto-detect, LT1/LT2, VO2max) to local Apple Silicon & Mesh hardware.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Integrity mode: development

## Requirements

### R1. Cloud-Assisted Frontend App & 100% Local Biometrics Airgap Division
- Use cloud AI schemas/prompts exclusively for frontend PWA scaffolding, Three.js 3D tatami rendering, TailwindCSS responsive components, and cross-platform Flutter/web templates.
- Enforce strict airgap health data protection: raw Movesense 512Hz ECG, PTT blood pressure, PPG sleep stages, and autonomic metrics execute 100% locally on Apple Silicon Metal GPU and mesh nodes (`127.0.0.1`).

### R2. Complete Movesense Physiological Readiness & Biofeedback Suite
- **Bicep ECG & 512Hz Pan-Tompkins DSP:** High-resolution QRS detection, microsecond R-R intervals, and RMSSD.
- **Pulse Transit Time (PTT) Continuous Blood Pressure:** Inversion model estimating real-time Systolic/Diastolic BP from ECG R-peak to optical PPG peak.
- **Overnight PPG Sleep Staging & Sleep Score:** Automated sleep scoring (0-100), Deep/REM/Light/Awake phase breakdown, and nocturnal autonomic recovery.
- **Auto Workout Detection & Cardiorespiratory Thresholds:** Real-time LT1 aerobic threshold (DFA-$\alpha_1 = 0.75$), LT2 anaerobic threshold (DFA-$\alpha_1 = 0.50$), and Heart Rate Ratio $VO_2\text{max}$ estimation ($15.3 \times \frac{\text{HR}_{\max}}{\text{HR}_{\text{rest}}}$).

### R3. SmolAgents Autonomous Python Code-Execution Arena & Multi-Mode Engine
- Equip faction leaders (Hermes 3 / Qwen 7B Red Lead, LuCI OpenWrt / Qwen Coder Blue Lead) with SmolAgents capability to write and execute sandboxed Python code directly.
- Implement 4 selectable game modes in the Canonical TUI:
  1. `EDGE_ORCHESTRATOR_CLASSIC` (Fast heuristic self-healing).
  2. `SMOLAGENTS_PYTHON_DUEL` (Direct Python code-generating agentic combat).
  3. `MULTI_MODEL_AGI_SWARM` (Unconstrained multi-specialist Genetic MoE routing).
  4. `AIRGAP_MESH_VS_CLOUD_CHAOS` (100% local mesh defending against external chaos).
- Transform the telemetry HUD to display active, plain-language **Tactical Objective Summaries** (`What is each team currently trying to do?`).

## Acceptance Criteria

### Biometric Accuracy & Local Airgap Verification
- [ ] Pan-Tompkins QRS detector processes 512Hz sample streams with $< 2\text{ms}$ latency and zero simulated packet injection.
- [ ] PTT blood pressure, overnight sleep score, LT1/LT2 thresholds, and $VO_2\text{max}$ compute accurately from real sensor logs and live BLE packets.
- [ ] Outbound network audit confirms zero biometric or personal health data packets are transmitted to public cloud APIs.

### SmolAgents Execution & Multi-Mode Verification
- [ ] Red and Blue Smolagents successfully generate, sandbox, and execute valid Python code blocks to inspect socket states and apply countermeasures.
- [ ] TUI HUD renders dynamic tactical objective summaries and switches seamlessly across all 4 game modes via hotkey selection.
