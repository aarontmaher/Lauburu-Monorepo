# 01_apps — Production Client Applications & Universal Edge AI

## Scope & Architecture
Contains all end-user and athlete-facing applications in the Lauburu Monorepo. Every app shares the **Universal On-Device Edge Specialist AI** embedded directly in the UI.

## Application Registry
1. `port_4000_hub/`: Central telemetry dashboard, Shopify membership tier manager ($0 Free, $19/mo Pro, Free Lifetime Crowdsourced Compute), and live readiness monitor.
2. `movesense_hub/`: 128Hz single-lead ECG and 9-DoF IMU medical-grade Bluetooth ingestion daemon and WebSockets broadcaster.
3. `zone2_endurance/`: Real-time DFA-alpha1 aerobic threshold (LT1/LT2) calculations and VO2max aerobic fatiguing coach.
4. `shopify_ai/`: Autonomous Shopify store manager, profitability scanner, and crowdsourced token redemption validator.
5. `spatial_grappling_3d/`: Three.js / WebGPU 3D spatial motion tracking arena driven by UWB anchors and multi-sensor IMU fusion.
6. `termux_edge_daemon/`: Headless background daemon running on Android edge nodes managing network health, local RAG vector caching, and Termux-to-AGI RPC bridging.

## Universal Edge AI Integration Protocol
- Every app embeds `edge_ai_sdk.js` or `EdgeAIService.kt`.
- Instant local RAG query resolution (<50ms).
- Automatic escalation to 7-Device Mesh AGI (`100.101.39.98:8081`) when prompt exceeds local context or requires deep multimodal reasoning.
- Cloud fallback to Gemini 3.7 Flash High / Gemini 3.1 Pro via Cloudflare tunnel.


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-01-apps-ecosystem`
- **Assigned Model Tier:** `Qwen 3.8 VL Max / DeepSeek-R1-32B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-01-apps-ecosystem/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
