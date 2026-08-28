# Project: Zone 2 Endurance Biometrics Next.js App (`01_apps/zone2_endurance`)

## Architecture
- **Framework**: Next.js App Router (React 18/19, TypeScript, Tailwind CSS).
- **Hybrid Rendering Paradigm**:
  - **Server Components (RSC)**: `app/layout.tsx`, `app/page.tsx`, `components/nav/NavigationShell.tsx`, `components/nav/Header.tsx`, `components/nav/Sidebar.tsx`, `components/dashboard/SummaryCards.tsx`, `components/dashboard/Zone2StatusBadge.tsx`. Zero-JS payload for static shell and initial layout.
  - **Client Components (`"use client"`)**: `components/charts/LiveEcgMonitor.tsx`, `components/charts/DfaAlpha1TrendChart.tsx`, `components/charts/AccessibleDataTable.tsx`, `components/theme/ThemeToggle.tsx`, `components/a11y/LiveAnnouncer.tsx`.
- **Theming**: Class-based Tailwind CSS (`darkMode: 'class'`), HSL CSS variables (`:root` / `.dark`), anti-FOUC synchronous theme injection in `<head>`.
- **Accessibility**: WCAG 2.1 AA / WCAG 2.2 AA compliant. Semantic ARIA landmarks (`banner`, `navigation`, `main`, `region`, `status`, `alert`), `focus-visible` keyboard rings with 2px offset, skip-to-content anchor (`#main-content`), `<AccessibleDataTable className="sr-only">` fallbacks for charts, and dual polite/assertive ARIA live regions.

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---------|-------------|-----------|--------|--------|
| 1 | Next.js App Router Root Layout (RSC) | Semantic root layout, HTML lang, anti-FOUC ThemeScript, skip link, no `"use client"`. | M2 | DONE | ORIGINAL_REQUEST §R1 |
| 2 | Responsive Navigation Shell (RSC) | Header, brand, desktop/mobile responsive sidebar navigation links, keyboard accessible. | M2 | DONE | ORIGINAL_REQUEST §R2 |
| 3 | Dashboard Summary View (RSC) | High-level workout summary cards (HR, Zone 2 duration, current DFA-a1, Aerobic Decoupling Pw:HR). | M2 | DONE | ORIGINAL_REQUEST §R2 |
| 4 | Live ECG Canvas Monitor (Client `"use client"`) | 128Hz canvas rendering, 640-sample circular ring buffer, 25 mm/s oscilloscope sweep, 5 lead statuses. | M3 | DONE | ORIGINAL_REQUEST §R1, Spec Miner |
| 5 | DFA-alpha1 Interactive Chart (Client `"use client"`) | Dynamic timeline, shaded [0.75, 1.00] Zone 2 corridor, 0.75 LT1 and 0.50 LT2 guides, Kamath 20% filter. | M3 | DONE | ORIGINAL_REQUEST §R1, Spec Miner |
| 6 | Tailwind Dark/Light Theme System | Class-based dark mode, CSS variables, high-contrast accessible tokens, interactive ThemeToggle button. | M1 | DONE | ORIGINAL_REQUEST §R2, Explorer 3 |
| 7 | Strict a11y & Screen Reader Support | ARIA landmark roles, focus visible rings, accessible chart data table fallbacks, ARIA live region announcer. | M3/M4 | DONE | ORIGINAL_REQUEST §R3, Explorer 3 |
| 8 | E2E Testing Suite (Tiers 1-4) | Comprehensive test harness validating RSC boundaries, Client Component isolation, theme switching, and a11y. | M_TEST / M4 | DONE | Project Pattern |
| 9 | Adversarial Coverage Hardening (Tier 5) | Stress tests for edge conditions (rapid theme toggling, buffer wrap-around, extreme biometric values). | M4 | DONE | Project Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M_TEST | E2E Testing Track | Test harness & comprehensive test suite (Tiers 1-5), published `TEST_READY.md` (51 tests) | None | DONE 🟢 |
| M1 | Next.js Scaffolding & Theme Engine | `package.json`, `tsconfig.json`, `tailwind.config.ts`, `globals.css`, ThemeProvider & ThemeToggle | None | DONE 🟢 |
| M2 | RSC Navigation Shell & Dashboard | `app/layout.tsx`, `app/page.tsx`, `components/nav/*`, `components/dashboard/*` (pure RSC) | M1 | DONE 🟢 |
| M3 | Client Biometric Visualizers & a11y Fallbacks | `LiveEcgMonitor.tsx`, `DfaAlpha1TrendChart.tsx`, AccessibleDataTable, LiveAnnouncer (`"use client"`) | M1, M2 | DONE 🟢 |
| M4 | Final E2E Test Suite Pass & Adversarial Hardening | 100% E2E test pass (10/10 suites), Tier 5 adversarial tests, Forensic Integrity Audit (CLEAN) | M_TEST, M3 | DONE 🟢 |

## Final Verification Summary
- `npm test` (`node tests/run_tests.mjs`): 10/10 suites passed (100% pass rate).
- `npm run typecheck` (`tsc --noEmit`): 0 errors.
- `npm run lint` (`next lint`): 0 warnings, 0 errors.
- `npm run build` (`next build`): Next.js 14.2 production build succeeded with static page optimization.
- Forensic Auditor Verdict: **`CLEAN`** (zero cheating, zero mock facades, genuine mathematical models).
- Independent Reviewers: 2/2 **`APPROVE`**.
- Adversarial Challengers: 2/2 **`APPROVE`**.
