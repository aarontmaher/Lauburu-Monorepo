---
title: "Google Stitch 2.0: DESIGN.MD Standard Protocol"
tags: [lauburu, ui, stitch_2.0, front_end, architecture]
---

# 🎨 The DESIGN.MD UI Generation Protocol

In accordance with the Google Stitch 2.0 framework, all applications within the Lauburu Ecosystem (Multi-WAN Terminal, Movesense Apps, etc.) must abandon ad-hoc UI coding. Instead, the UI must be mapped out in a portable `DESIGN.MD` markdown specification.

This enables frontier AI swarms and the Sovereign Orchestrator to rapidly iterate on the "Infinite Canvas" of user flows before a single line of React/Tailwind/Flutter is written.

## Canonical `DESIGN.MD` Structure

Every UI project must contain a `DESIGN.MD` file at its root with the following structure:

```markdown
# App Name: [Name]

## 1. Global Theming & Tokens
- **Primary Color:** `#HEX`
- **Typography:** [Font Family]
- **Component Standard:** [React Tailwind | Flutter Material | Python Textual]

## 2. Multi-Screen Flow (Infinite Canvas)

### Screen: [Screen Name] (e.g., `TerminalDashboard`)
- **Route:** `/dashboard`
- **Purpose:** [What this screen does]
- **State/Props:** [Data it needs, e.g., `telemetryStream`]
- **Layout:**
  - Header: [Components]
  - Main Area: [Components]
  - Footer: [Components]

### Screen: [Screen Name]
...
```

## AI Generation Pipeline
1. The AI Orchestrator or human dictates the app requirements.
2. The UI Specialist AI generates/updates the `DESIGN.MD`.
3. The Coding Swarm parses `DESIGN.MD` and autonomously scaffolds the precise UI codebase.
4. The cycle continuously loops for optimization via `/boost` and `/frontier-swarm-consensus`.
