---
title: "Android Auto In-Vehicle Voice Coding & Multi-Device Mesh Transport"
tags: [lauburu, android_auto, voice_coding, stt, tts, whisper, kokoro, mesh, hardware]
truth_audited: true
audit_swarm_verified: "2026-09-01"
audit_swarm_engine: "local_llamacpp_rpc+cloud_frontier"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 🚗 Android Auto In-Vehicle Voice Coding & Multi-Device Mesh Transport

The **Android Auto AGI Hands-Free Voice Coding Agent** (`com.lauburu.androidauto.agi`) delivers an automotive-safe, distraction-free voice coding HUD to vehicle head units connected to the Lauburu 7/8-node physical mesh.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 IN-CAR VOICE CODING & MULTI-DEVICE PATTERN                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Voice Ingress (STT): Driver speaks coding directives. Captured via mic  │
│    and transcribed by Faster-Whisper Turbo / Tensor G5 NPU.                 │
│ 2. Mesh Dispatch: Directives route over Tailscale (100.x.y.z) to M4 Mac     │
│    Mini Orchestrator (Port 8081 llama.cpp / Port 4000 Hub / Port 8765).     │
│ 3. Spoken Egress (TTS): Agent summarizes test results and git diffs via     │
│    neural voice (Kokoro-82M / Edge-TTS / macOS say / Android TTS) with      │
│    AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK in-cabin audio ducking.               │
│ 4. Glanceable HUD Card: Android Auto screen renders a 4-row PaneTemplate    │
│    (Directive, Status, Diff: +14 -2, Tests: 100% PASS) with tap actions.    │
│ 5. Single Projection Host: Connected Android node projects to head unit     │
│    while pulling telemetry from all 8 mesh devices.                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎙️ 1. Optimal Speech Pipeline Architecture (STT & TTS)

| Pipeline Component | Primary Engine | Fallback Engine | Latency SLA | Key Role |
| :--- | :--- | :--- | :--- | :--- |
| **STT (Speech-to-Text)** | `faster-whisper` (`tiny.en` / `whisper-large-v3-turbo`) | Android `SpeechRecognizer` (Tensor G5 NPU) | **< 200 ms** | Transcribes spoken programming directives and AST names. |
| **TTS (Text-to-Speech)** | `Kokoro-82M` / `edge-tts` (Neural Studio) | Native macOS `say` / Android `TextToSpeech` | **< 1.0 s** | Synthesizes natural, human-like diff explanations and test summaries. |
| **Voice Bridge Daemon** | AsyncIO WebSocket (`ws://100.119.199.76:8765`) | Direct TCP socket | **< 5 ms RTT** | High-throughput 16kHz PCM audio streaming bridge. |
| **Audio Focus Controller** | `AudioFocusRequestCompat` | System AudioManager | **Immediate** | Ducks cabin media volume by 80% during agent speech. |

---

## 📱 2. Android Auto Jetpack Architecture (`androidx.car.app`)

- **Package Name:** `com.lauburu.androidauto.agi`
- **CarAppService:** `com.lauburu.androidauto.agi.service.LauburuCarAppService`
- **Session:** `VoiceCodingSession`
- **HUD Screen Hierarchy:**
  1. `VoiceCodingHudScreen`: Main 4-row glanceable HUD (`PaneTemplate`) with voice listener trigger and confirm action.
  2. `DiffDetailScreen`: Full diff viewing with syntax-colored summary and line breakdown.
  3. `TestResultScreen`: Real-time pass/fail breakdown across 8 mesh nodes.
  4. `DirectivesListScreen`: Selection list of standard voice actions.

---

## 🚀 3. Canonical CLI & Automation Tooling

```bash
# 1. Run full in-car voice coding simulation loop
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/automotive/voice_venv/bin/python \
  /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/in_car_voice_coder.py --demo

# 2. Run single voice directive prompt
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/automotive/voice_venv/bin/python \
  /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/in_car_voice_coder.py \
  --prompt "What is the status of the 8-device physical mesh?"

# 3. Launch Desktop Head Unit (DHU) port forwarding
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/automotive/android_auto_voice_coder/launch_dhu.sh

# 4. Execute 126-test E2E verification suite
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/automotive/android_auto_voice_coder && ./test_e2e_suite.sh --all

# 5. Build & deploy APK to connected device via wireless ADB
./deploy_to_pixel.sh 100.84.40.95:5555
```

---

## 🏛️ 4. Tri-Vault Synchronization

- **Obsidian Vault:** `05_Hardware_Mesh/Android_Auto_Voice_Coding.md`
- **PySpark / LoRA Data Lake:** `data/lora_datasets/in_car_voice_coding_actions.jsonl`
- **GitHub Monorepo:** `01_apps/automotive/android_auto_voice_coder` & `06_scripts_and_tooling/automation/in_car_voice_coder.py`

