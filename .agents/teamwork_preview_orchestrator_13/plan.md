# Execution Plan: Next.js Endurance Biometrics App (`01_apps/zone2_endurance`)

## Objective
Scaffold and implement a modern Next.js UI/UX for an endurance biometric monitoring application in `01_apps/zone2_endurance`, strictly following React Server Component separation for static shell/navigation and `"use client"` for live biometric charts (ECG, DFA-alpha1), Tailwind CSS dark/light mode themes, and strict accessibility.

## Phased Approach

### Phase 0: Survey & Codebase Investigation
- Spawn 3 Explorers (including spec miners / codebase explorers) to investigate:
  1. Existing repository layout, root package.json, workspace configurations, shared packages, and dependencies in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` and `01_apps/`.
  2. Specification & Biometrics data shapes (ECG, DFA-alpha1, Zone 2 ranges, metrics formatting).
  3. Next.js App Router, Tailwind CSS 3/4 setup, and a11y standards (WCAG 2.1 AA, high-contrast themes, ARIA landmarks, screen-reader tables/descriptions).
- Synthesize findings into `PROJECT.md` with complete Feature Inventory and Milestones.

### Phase 1: Test Infrastructure & Dual-Track E2E Test Suite
- Create test harness / E2E verification tests checking:
  - Architecture: Server Components (no "use client" in layouts/static nav) vs Client Components ("use client" in ECG / DFA-alpha1 charts).
  - Scope: Navigation shell, dashboard summary cards, live charts.
  - Theming: Dark/light mode classes and CSS variables.
  - Accessibility: ARIA roles, tabindex, keyboard navigation, semantic HTML, screen reader labels.

### Phase 2: Implementation Milestones
- **M1: App Setup & Styling**: Next.js App Router config, TypeScript, Tailwind CSS, Theme Provider (Dark/Light with class or attribute toggle).
- **M2: RSC Core Shell & Dashboard**: `app/layout.tsx`, `app/page.tsx`, `components/nav/Navbar.tsx`, `components/dashboard/SummaryCards.tsx` (RSC).
- **M3: Client Biometric Visualizations**: `components/charts/EcgChart.tsx`, `components/charts/DfaAlpha1Chart.tsx` (marked `"use client"`, high contrast, accessible data descriptions, interactive controls).
- **M4: Accessibility & Theme Integration**: Keyboard traps/focus rings, skip links, semantic landmarks, high contrast palettes for dark/light modes.

### Phase 3: Verification, Adversarial Hardening & Review Gate
- Run Reviewers, Challengers, and Forensic Auditor across all acceptance criteria.
- Ensure 100% test pass with zero integrity violations.
- Prepare final handoff report.
