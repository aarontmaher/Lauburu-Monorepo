---
title: "Rule 11: Screen Lens Default Automation & WAF Bypass Invariant"
tags: [lauburu, rule, screen_lens, uiautomator, automation, waf_bypass]
---

# 👁️ Rule 11: Screen Lens Default Automation & WAF Bypass Invariant

## 1. The Screen Lens Prime Directive
**Screen Lens (`/screen-lens-sovereign`) is hereby declared the MANDATORY DEFAULT AUTOMATION METHOD across the entire Lauburu project, network, and AI swarm ecosystem.**
All AI agents executing `/goal` instructions, performing E2E e-commerce interactions, scraping, or automated testing MUST default to Screen Lens over traditional desktop browser automation protocols.

## 2. Prohibition of Desktop CDP / Playwright on WAF-Protected Targets
- Traditional desktop automation (Chrome DevTools Protocol, Playwright, Selenium) is heavily fingerprinted by Cloudflare, Imperva, and modern WAFs (e.g., returning "Access Denied" on Gumtree).
- **Prohibition:** Agents MUST NOT attempt to brute-force desktop headless browsers against these targets.
- **Mandatory Fallback:** Agents MUST route all E2E automation through the Android Edge Nodes (L6 Pixel 10 Pro XL, L7 Samsung S20) via ADB TLS bridging.

## 3. The Native Android Hierarchy Bypass (`uiautomator`)
Screen Lens bypasses web application firewalls by relying on the native Android Accessibility Service UI hierarchy.
- Agents must extract screen state using: `adb shell uiautomator dump`
- Agents must actuate using: `adb shell input tap <x> <y>` and `adb shell input text "<string>"`
- The canonical wrapper for this operation is located at: `06_scripts_and_tooling/automation/screen_lens_automator.py`

## 4. Swarm-Wide `/goal` Enforcement
When the user invokes `/goal`, the swarm orchestrators (Cloud, Local, and Genetic) are strictly bound to this protocol. If a web interaction fails via desktop MCP, the orchestrator must instantly, and autonomously, pivot to the Screen Lens mobile automation plane without waiting for user approval.
