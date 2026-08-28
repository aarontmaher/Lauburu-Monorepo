# 03_biometrics_and_telemetry — DSP Pipelines & Medical-Grade Telemetry

## Scope & Zero-Mock Standard
Houses signal processing (DSP) algorithms converting raw sensor streams into validated physiological biomarkers. **Strictly 0% mock or simulated data.**

## Signal Processing Modules
1. `movesense_ecg_128hz/`: Pan-Tompkins QRS detector, R-R interval extraction, and HRV time/frequency domain calculation (RMSSD, SDNN, pNN50, LF/HF).
2. `optical_ppg_dsp/`: 5-minute phone camera optical photoplethysmography (PPG) pulse wave analysis and autonomic recovery scoring.
3. `dfa_alpha1_thresholds/`: Detrended Fluctuation Analysis (DFA-alpha1) dynamic correlation coefficients determining real-time aerobic (0.75) and anaerobic (0.50) thresholds.
4. `sleep_polysomnography/`: Overnight multi-sensor sleep architecture staging (Deep Slow-Wave, REM, Light, Latency) and autonomic circadian rhythm recovery modeling.


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-03-biometrics-dsp`
- **Assigned Model Tier:** `BioMistral 7B (Q8_0) / DeepSeek-R1-32B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-03-biometrics-dsp/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
