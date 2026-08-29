## 2026-08-29T09:37:33Z

You are a Worker agent for Milestone M1: Flagship Movesense Physiological Readiness Suite.
Your working directory is /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1/
Path to ORIGINAL_REQUEST.md: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/ORIGINAL_REQUEST.md
Path to PROJECT.md: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md
Path to Explorer 1 Survey Report: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_1/handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Task:
Build out 01_apps/biometrics/movesense_hub to 100% commercial completeness with modular sub-packages:
1. core/ (__init__.py, config.py, models.py): Config, state store, data contracts (RawEcgFrame, QrsDetectionResult, PttBloodPressure, SleepStagingResult, Zone2CardioResult), Rule #0 WAITING_FOR_SENSOR invariants.
2. dsp/ (__init__.py, pan_tompkins.py, hemodynamics_bp.py, sleep_scoring.py, zone2_coaching.py): 512Hz/128Hz 4th-order Butterworth bandpass (0.5-40Hz), 5-pt central derivative, squaring, 150ms MWI, dual adaptive threshold QRS detection, Kamath 2004 20% RR filter, microsecond RMSSD, DFA-alpha1 (s in [4, 16] beats), continuous Hughes-Bramwell PTT BP inversion (SBP, DBP, MAP), 30s epoch sleep staging (AWAKE/DEEP/REM/LIGHT) with nocturnal dipping % and 0-100 recovery score, auto workout classification, Uth-Sørensen VO2max and HRR LT1/LT2 thresholds.
3. transport/ (__init__.py, bleak_daemon.py, web_ble_bridge.py): Bleak GATT ingestion daemon for Movesense sensor serial 261030002013 (MDS 2.0 34800001-7185-4d5d-b431-b30e393d9e05 and SIG HRS 0x2A37), Web Bluetooth bridge.
4. presentation/ (__init__.py, tui.py, web_adapter.py): Native Textual TUI with responsive metric cards, Web-TUI adapter for Port 8088 /readiness route, Next.js Canvas oscilloscope PWA connector.
5. Package root __init__.py exporting top-level convenience functions and version.
6. Clean up temporary swap files in 01_apps/biometrics/movesense_hub.

Verification Requirements:
- Execute test suite: python3 -m pytest 03_biometrics_and_telemetry/tests/test_movesense_dsp_suite.py
- Verify modular package imports: python3 -c "import 01_apps.biometrics.movesense_hub as mhb; print(mhb.__version__)" or equivalent python import.
- Write your full report to /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_worker_m1/handoff.md.
Send a completion message when finished.
