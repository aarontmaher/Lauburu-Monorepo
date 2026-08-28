## 2026-08-26T12:04:21Z
You are the Project Orchestrator (teamwork_preview_orchestrator) for the following project.

# Project Specification
Scaffold a modern Next.js UI and UX for an endurance biometric app in `01_apps/zone2_endurance`. Use Tailwind CSS, ensure strict accessibility (a11y), and provide dark/light mode themes.

## Working Directory
- Project Target Directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/zone2_endurance`
- Orchestrator Agent Metadata Directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_orchestrator_13`
- Original Request File: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`

## Requirements
### R1. Next.js App Router & Hybrid Rendering (AI Debate Consensus)
Use the Next.js App Router (React Server Components) for the core shell, layouts, and routing. However, all live biometric data visualization components (ECG, DFA-alpha1) MUST be strictly isolated as Client Components (`"use client"`).

### R2. Comprehensive Scope & Dark Mode
The UI must include the core navigation shell, a dashboard summary view, and dedicated interactive biometric data charts (DFA-alpha1, ECG). The entire application must support light and dark mode themes using Tailwind CSS.

### R3. Strict Accessibility (a11y)
The application must adhere to strict accessibility standards, including proper ARIA labels, semantic HTML, and high-contrast color palettes for data visualization.
