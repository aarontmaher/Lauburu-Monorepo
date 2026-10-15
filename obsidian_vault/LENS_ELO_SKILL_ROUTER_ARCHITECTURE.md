# 🧠 Screen Lens Sovereign: Dynamic ELO Skill Router & Multi-Layer Hardware Integration

## 1. The Autonomous Skill ELO Governor
Screen Lens Sovereign acts as the top-level VLA (Vision-Language-Action) orchestrator. Instead of waiting for the user to type slash commands, Lens dynamically evaluates incoming ambiguous tasks (or complex visual states) and autonomously delegates them to internal skills based on a Bradley-Terry ELO Leaderboard.

*   **Autonomy Threshold (1600 ELO):** Any skill (e.g., `/deep-research`, `/closed-source-reverse-engineering`) that maintains an ELO rating above 1600 can be autonomously invoked by Lens without human intervention.
*   **Approval Threshold (<1600 ELO):** Skills below 1600 require Lens to pause and ask the user for approval via the TUI IDE before spinning up.
*   **Meritocratic Evolution:** Successful executions (verified by physical exit codes or pixel-perfect DOM diffs) earn ELO points. Failures or hallucination loops incur severe ELO penalties.

## 2. Hardware Topology & Mesh Delegation
When Screen Lens invokes a skill, it doesn't just run it blindly on the Mac Host. It strictly routes the execution across the 7-Layer hardware mesh to bypass bottlenecks and preserve host VRAM:

### Layer 7: Samsung Galaxy S20 (Dedicated UI Tester & Web Scraper)
*   **The Problem:** Cloudflare WAFs and bot-protection instantly block headless Playwright/Selenium browsers originating from macOS/Linux servers.
*   **The Integration:** When Lens autonomously triggers `/deep-research` or `/open-source-software-scout`, the execution is strictly routed to the **Samsung S20** via USB ADB `uiautomator`.
*   **Mechanism:** The S20 runs native Android Chrome. Lens pushes UI tap coordinates over ADB to navigate the real mobile web, rendering it mathematically impossible for external servers to flag the bot, as it originates from a physical mobile baseband/OS.

### The Ethernet Mesh (10G/2.5G Backbone)
*   **High-Speed Transport:** All telemetry and orchestrator subagent communications (e.g., the Tri-Orchestrator Swarm spawned by `/ai-debate`) occur over the GL-BE14000 Ethernet backbone.
*   **Workload Sharding:** The Mac Mini (L1) acts as the Master Orchestrator, but heavy parallel tasks are offloaded over Ethernet to the Linux Hub (L3).

### Layer 0: The Omnipresent Bluetooth Dongle
*   **The Ultimate Fallback:** If a swarm overloads a peripheral node and crashes its Tailscale/Ethernet interface, the Skill Router automatically fails over to the **Bluetooth Dongle**.
*   **OOB Resurrection:** Lens uses raw RFCOMM/L2CAP serial over Bluetooth to issue OOB (Out-Of-Band) magic packets and kernel resurrection scripts, ensuring that autonomous swarms (like `/teamwork-preview`) can never permanently sever a node from the mesh.
