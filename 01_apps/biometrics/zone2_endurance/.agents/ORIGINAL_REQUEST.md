# Original User Request

## 2026-08-26T12:23:39Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Execute the requirements via the teamwork multi-agent system.
> Requested team: Full team

Scaffold a modern Next.js UI and UX for an endurance biometric app. Use Tailwind, ensure strict accessibility (a11y), and provide dark/light mode themes.

Working directory: ~/DFS_UNIFIED/Lauburu-Monorepo/01_apps/zone2_endurance

## Requirements

### R1. Next.js App Router & Hybrid Rendering (AI Debate Consensus)
Use the Next.js App Router (React Server Components) for the core shell, layouts, and routing. However, all live biometric data visualization components (ECG, DFA-alpha1) MUST be strictly isolated as Client Components (`"use client"`).

### R2. Comprehensive Scope & Dark Mode
The UI must include the core navigation shell, a dashboard summary view, and dedicated interactive biometric data charts (DFA-alpha1, ECG). The entire application must support light and dark mode themes using Tailwind CSS.

### R3. Strict Accessibility (a11y)
The application must adhere to strict accessibility standards, including proper ARIA labels, semantic HTML, and high-contrast color palettes for data visualization.

## Acceptance Criteria

### Architecture & Rendering
- [ ] Root layouts and static navigation elements are React Server Components (do not have `"use client"`).
- [ ] Biometric chart components are explicitly marked with `"use client"`.

### UI Scope
- [ ] A responsive navigation shell exists.
- [ ] A dashboard view exists with placeholder layout for biometric summaries.
- [ ] Dedicated UI components exist for ECG and DFA-alpha1 visualizations.
- [ ] Dark mode toggle works and tailwind `dark:` classes are applied correctly.

### Accessibility
- [ ] All interactive elements are keyboard navigable.
- [ ] Data visualization placeholders include appropriate screen-reader descriptions.
