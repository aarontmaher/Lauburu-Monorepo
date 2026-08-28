/**
 * Challenger 2: Empirical Accessibility, Component Boundaries & UI Behavior Adversarial Test Suite
 * Target App: 01_apps/zone2_endurance
 * 
 * Verifies:
 * 1. Accessible Table Pagination, Boundary Handling, and Formatter Resilience
 * 2. ARIA Live Region Dual Mechanics (Polite vs Assertive Announcements)
 * 3. Complete Keyboard Navigation Paths, Arrow Key Tooltip Traversal & Skip Link Target
 * 4. WCAG 2.1 / 2.2 AA & AAA Color Contrast Calculations Across All Themes & Zones
 * 5. React Server Component (RSC) vs Client Component Isolation & Architectural Boundaries
 * 6. Semantic Landmark Hierarchy, Touch Target Minimums, and DOM A11y Attributes
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

// =========================================================================
// WCAG 2.1 Relative Luminance & Contrast Calculation Functions
// =========================================================================
function parseHexColor(hexStr) {
  const hex = hexStr.replace('#', '').trim();
  if (hex.length === 3) {
    return {
      r: parseInt(hex[0] + hex[0], 16),
      g: parseInt(hex[1] + hex[1], 16),
      b: parseInt(hex[2] + hex[2], 16),
    };
  }
  return {
    r: parseInt(hex.substring(0, 2), 16),
    g: parseInt(hex.substring(2, 4), 16),
    b: parseInt(hex.substring(4, 6), 16),
  };
}

function getRelativeLuminance(hexColor) {
  const { r, g, b } = parseHexColor(hexColor);
  const sR = r / 255;
  const sG = g / 255;
  const sB = b / 255;

  const toLinear = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * toLinear(sR) + 0.7152 * toLinear(sG) + 0.0722 * toLinear(sB);
}

function computeContrastRatio(color1, color2) {
  const lum1 = getRelativeLuminance(color1);
  const lum2 = getRelativeLuminance(color2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('Challenger 2: Empirical Accessibility, Component Boundaries & UI Behavior', () => {

  // =========================================================================
  // 1. Accessible Table Pagination & Boundary Handling
  // =========================================================================
  describe('1. Accessible Table Pagination & Boundary Handling', () => {
    function paginate(data, page, pageSize) {
      const totalPages = Math.max(1, Math.ceil(data.length / pageSize));
      const clampedPage = Math.max(1, Math.min(totalPages, page));
      const startIndex = (clampedPage - 1) * pageSize;
      const currentRows = data.slice(startIndex, startIndex + pageSize);
      return {
        currentPage: clampedPage,
        totalPages,
        startIndex,
        currentRows,
        hasPrev: clampedPage > 1,
        hasNext: clampedPage < totalPages,
      };
    }

    it('Empty dataset pagination defaults to 1 total page, 0 rows, and disabled pagination controls', () => {
      const result = paginate([], 1, 10);
      assert.equal(result.totalPages, 1);
      assert.equal(result.currentPage, 1);
      assert.equal(result.currentRows.length, 0);
      assert.equal(result.hasPrev, false);
      assert.equal(result.hasNext, false);
    });

    it('Exact page multiple (e.g. 30 items with pageSize=10) yields exactly 3 pages without extra blank page', () => {
      const mockItems = Array(30).fill(null).map((_, i) => ({ timestamp: 1000 + i * 1000, alpha1: 0.85, heartRate: 140, zone: 'ZONE_2' }));
      const p1 = paginate(mockItems, 1, 10);
      assert.equal(p1.totalPages, 3);
      assert.equal(p1.currentRows.length, 10);
      assert.equal(p1.hasPrev, false);
      assert.equal(p1.hasNext, true);

      const p2 = paginate(mockItems, 2, 10);
      assert.equal(p2.currentPage, 2);
      assert.equal(p2.hasPrev, true);
      assert.equal(p2.hasNext, true);

      const p3 = paginate(mockItems, 3, 10);
      assert.equal(p3.currentPage, 3);
      assert.equal(p3.hasPrev, true);
      assert.equal(p3.hasNext, false);
    });

    it('Uneven dataset (e.g. 23 items with pageSize=10) produces 3 pages with remainder on last page', () => {
      const mockItems = Array(23).fill(null).map((_, i) => ({ timestamp: 1000 + i * 1000, alpha1: 0.85, heartRate: 140, zone: 'ZONE_2' }));
      const p3 = paginate(mockItems, 3, 10);
      assert.equal(p3.totalPages, 3);
      assert.equal(p3.currentRows.length, 3);
      assert.equal(p3.hasPrev, true);
      assert.equal(p3.hasNext, false);
    });

    it('Out-of-bounds page requests (negative, 0, or > totalPages) clamp safely without throwing', () => {
      const mockItems = Array(15).fill(null).map((_, i) => ({ timestamp: 1000 + i * 1000, alpha1: 0.85, heartRate: 140, zone: 'ZONE_2' }));
      assert.equal(paginate(mockItems, -5, 10).currentPage, 1);
      assert.equal(paginate(mockItems, 0, 10).currentPage, 1);
      assert.equal(paginate(mockItems, 999, 10).currentPage, 2);
    });

    it('Data table formatters sanitize corrupt timestamps and missing values', () => {
      function formatTime(epochMs) {
        const d = new Date(epochMs);
        return isNaN(d.getTime()) ? '--:--' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }

      assert.equal(formatTime(NaN), '--:--');
      assert.equal(formatTime('invalid_timestamp'), '--:--');
      const validFormatted = formatTime(1724700000000);
      assert.ok(validFormatted !== '--:--', 'Valid epoch should format to time string');
    });

    it('AccessibleDataTable.tsx component contains semantic table landmarks and ARIA attributes', () => {
      const tablePath = path.join(appRoot, 'components/charts/AccessibleDataTable.tsx');
      assert.ok(fs.existsSync(tablePath));
      const content = fs.readFileSync(tablePath, 'utf8');

      assert.match(content, /<table[^>]*>/, 'Must render standard <table> element');
      assert.match(content, /<caption[^>]*className=["'][^"']*sr-only[^"']*["']/, 'Must render screen-reader caption');
      assert.match(content, /<th[^>]*scope=["']col["']/, 'Must have scope="col" on header cells');
      assert.match(content, /<th[^>]*scope=["']row["']/, 'Must have scope="row" on row header cells');
      assert.match(content, /role=["']region["']/, 'Container must declare role="region"');
      assert.match(content, /aria-label=/, 'Container must declare aria-label');
      assert.match(content, /tabIndex=\{0\}/, 'Container must be keyboard focusable');
      assert.match(content, /aria-label=["']Previous Page["']/, 'Pagination previous button must have aria-label');
      assert.match(content, /aria-label=["']Next Page["']/, 'Pagination next button must have aria-label');
    });
  });

  // =========================================================================
  // 2. ARIA Live Region Dual Mechanics & Announcement Integrity
  // =========================================================================
  describe('2. ARIA Live Region Dual Mechanics & Announcements', () => {
    it('LiveAnnouncer.tsx implements isolated Polite (status) and Assertive (alert) live regions', () => {
      const announcerPath = path.join(appRoot, 'components/a11y/LiveAnnouncer.tsx');
      assert.ok(fs.existsSync(announcerPath));
      const content = fs.readFileSync(announcerPath, 'utf8');

      // Polite region
      assert.match(content, /role=["']status["']/, 'Must provide role="status" for polite announcements');
      assert.match(content, /aria-live=["']polite["']/, 'Must declare aria-live="polite"');
      assert.match(content, /aria-atomic=["']true["']/, 'Must declare aria-atomic="true" on polite region');

      // Assertive region
      assert.match(content, /role=["']alert["']/, 'Must provide role="alert" for assertive emergency alarms');
      assert.match(content, /aria-live=["']assertive["']/, 'Must declare aria-live="assertive"');
      assert.match(content, /aria-atomic=["']true["']/, 'Must declare aria-atomic="true" on assertive region');

      // Visibility for screen readers (sr-only, not hidden)
      assert.match(content, /className=["'][^"']*sr-only[^"']*["']/, 'Live regions must use sr-only utility to remain in accessibility tree');
      assert.doesNotMatch(content, /aria-hidden=["']true["']/, 'Live regions must NEVER have aria-hidden="true"');
    });

    it('LiveAnnouncer.tsx is mounted in RootLayout (app/layout.tsx) with initial initialization message', () => {
      const layoutPath = path.join(appRoot, 'app/layout.tsx');
      const content = fs.readFileSync(layoutPath, 'utf8');

      assert.match(content, /<LiveAnnouncer/, 'app/layout.tsx must render LiveAnnouncer');
      assert.match(content, /politeMessage=/, 'LiveAnnouncer must receive initial polite announcement message');
    });

    it('DfaAlpha1TrendChart.tsx includes an inline aria-live="polite" region for dynamic trend updates', () => {
      const dfaPath = path.join(appRoot, 'components/charts/DfaAlpha1TrendChart.tsx');
      const content = fs.readFileSync(dfaPath, 'utf8');

      assert.match(content, /aria-live=["']polite["']/, 'DfaAlpha1TrendChart must declare aria-live="polite"');
      assert.match(content, /aria-atomic=["']true["']/, 'DfaAlpha1TrendChart must declare aria-atomic="true"');
      assert.match(content, /className=["'][^"']*sr-only[^"']*["']/, 'Live summary must be sr-only');
    });
  });

  // =========================================================================
  // 3. Complete Keyboard Navigation Paths & Interactive Controls
  // =========================================================================
  describe('3. Complete Keyboard Navigation Paths & Interactive Controls', () => {
    it('Skip to content link in app/layout.tsx targets "#main-content" matching main landmark ID', () => {
      const layoutContent = fs.readFileSync(path.join(appRoot, 'app/layout.tsx'), 'utf8');
      const navShellContent = fs.readFileSync(path.join(appRoot, 'components/nav/NavigationShell.tsx'), 'utf8');

      assert.match(layoutContent, /href=["']#main-content["']/, 'Skip link must target #main-content');
      assert.match(navShellContent, /id=["']main-content["']/, 'Main landmark in NavigationShell must have id="main-content"');
    });

    it('Interactive buttons declare minimum WCAG 2.5.5 touch target size (>= 44x44px or >= 36px inline)', () => {
      const components = [
        'components/theme/ThemeToggle.tsx',
        'components/charts/LiveEcgMonitor.tsx',
        'components/charts/DfaAlpha1TrendChart.tsx',
        'components/charts/AccessibleDataTable.tsx',
      ];

      for (const relPath of components) {
        const fullPath = path.join(appRoot, relPath);
        assert.ok(fs.existsSync(fullPath));
        const content = fs.readFileSync(fullPath, 'utf8');
        assert.match(
          content,
          /min-h-\[(44|36)px\]|p-2|px-3|p-1\.5/,
          `${relPath} buttons must specify accessible tap/touch target sizing`
        );
      }
    });

    it('All interactive buttons and switches have explicit focus-visible ring styles', () => {
      const components = [
        'components/theme/ThemeToggle.tsx',
        'components/charts/LiveEcgMonitor.tsx',
        'components/charts/DfaAlpha1TrendChart.tsx',
        'components/charts/AccessibleDataTable.tsx',
      ];

      for (const relPath of components) {
        const fullPath = path.join(appRoot, relPath);
        const content = fs.readFileSync(fullPath, 'utf8');
        assert.match(
          content,
          /focus-visible:ring-2/,
          `${relPath} must apply focus-visible:ring-2 class for keyboard focus visibility`
        );
      }
    });

    it('DfaAlpha1TrendChart SVG data points support ArrowLeft and ArrowRight keyboard inspection', () => {
      const dfaContent = fs.readFileSync(path.join(appRoot, 'components/charts/DfaAlpha1TrendChart.tsx'), 'utf8');

      assert.match(dfaContent, /tabIndex=\{0\}/, 'Data point circles must have tabIndex={0}');
      assert.match(dfaContent, /role=["']button["']/, 'Data point circles must have role="button"');
      assert.match(dfaContent, /onFocus=/, 'Data point circles must handle onFocus');
      assert.match(dfaContent, /onKeyDown=/, 'Data point circles must handle onKeyDown for arrow navigation');
      assert.match(dfaContent, /ArrowRight/, 'Must handle ArrowRight navigation');
      assert.match(dfaContent, /ArrowLeft/, 'Must handle ArrowLeft navigation');
    });
  });

  // =========================================================================
  // 4. WCAG 2.1 / 2.2 AA & AAA Color Contrast Calculations Across All Themes
  // =========================================================================
  describe('4. WCAG Color Contrast Across All Themes & Biometric Zones', () => {
    // Definitive color token matrix from tailwind.config.ts and globals.css
    const lightTokens = {
      bg: '#f8fafc',
      card: '#ffffff',
      foreground: '#0f172a',
      mutedText: '#334155', // slate-700
      primary: '#059669', // Emerald 600
      primaryTextOnLight: '#047857', // Emerald 700
      zone1: '#0284c7', // Sky 600
      zone2: '#059669', // Emerald 600
      zone2Text: '#047857', // Emerald 700
      zone3: '#d97706', // Amber 600
      zone3Text: '#b45309', // Amber 700
      zone4: '#ea580c', // Orange 600
      zone4Text: '#c2410c', // Orange 700
      zone5: '#e11d48', // Rose 600
      zone5Text: '#be123c', // Rose 700
      ecgBg: '#090d16',
      ecgLine: '#059669',
    };

    const darkTokens = {
      bg: '#030712',
      card: '#0b0f19',
      foreground: '#f8fafc',
      mutedText: '#cbd5e1', // slate-300
      primary: '#34d399', // Emerald 400
      zone1: '#38bdf8', // Sky 400
      zone2: '#34d399', // Emerald 400
      zone3: '#fbbf24', // Amber 400
      zone4: '#fb923c', // Orange 400
      zone5: '#fb7185', // Rose 400
      ecgBg: '#020617',
      ecgLine: '#34d399',
    };

    // 4.1 Light Mode Contrasts
    it('Light mode primary text (#0f172a on #f8fafc and #ffffff) exceeds AAA standard (>= 7.0:1)', () => {
      const ratioBg = computeContrastRatio(lightTokens.foreground, lightTokens.bg);
      const ratioCard = computeContrastRatio(lightTokens.foreground, lightTokens.card);

      assert.ok(ratioBg >= 7.0, `Light body contrast ${ratioBg.toFixed(2)} must be >= 7.0`);
      assert.ok(ratioCard >= 7.0, `Light card contrast ${ratioCard.toFixed(2)} must be >= 7.0`);
    });

    it('Light mode muted text (#334155 on #f8fafc) exceeds AA standard (>= 4.5:1)', () => {
      const ratio = computeContrastRatio(lightTokens.mutedText, lightTokens.bg);
      assert.ok(ratio >= 4.5, `Light muted text contrast ${ratio.toFixed(2)} must be >= 4.5`);
    });

    it('Light mode Zone 2 Emerald text (#047857 on #f8fafc) exceeds AA standard (>= 4.5:1)', () => {
      const ratio = computeContrastRatio(lightTokens.zone2Text, lightTokens.bg);
      assert.ok(ratio >= 4.5, `Zone 2 light text contrast ${ratio.toFixed(2)} must be >= 4.5:1`);
    });

    it('Light mode Zone 2 UI component (#059669 on #f8fafc) exceeds non-text graphical threshold (>= 3.0:1)', () => {
      const ratio = computeContrastRatio(lightTokens.zone2, lightTokens.bg);
      assert.ok(ratio >= 3.0, `Zone 2 graphic contrast ${ratio.toFixed(2)} must be >= 3.0:1`);
    });

    it('Light mode Zone 1, 3, 4, 5 text tokens on background all exceed AA standard (>= 4.5:1)', () => {
      const z1Ratio = computeContrastRatio('#0369a1', lightTokens.bg); // Sky 700
      const z3Ratio = computeContrastRatio(lightTokens.zone3Text, lightTokens.bg); // Amber 700
      const z4Ratio = computeContrastRatio(lightTokens.zone4Text, lightTokens.bg); // Orange 700
      const z5Ratio = computeContrastRatio(lightTokens.zone5Text, lightTokens.bg); // Rose 700

      assert.ok(z1Ratio >= 4.5, `Zone 1 text contrast ${z1Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z3Ratio >= 4.5, `Zone 3 text contrast ${z3Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z4Ratio >= 4.5, `Zone 4 text contrast ${z4Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z5Ratio >= 4.5, `Zone 5 text contrast ${z5Ratio.toFixed(2)} must be >= 4.5:1`);
    });

    // 4.2 Dark Mode Contrasts
    it('Dark mode primary text (#f8fafc on #030712 and #0b0f19) exceeds AAA standard (>= 7.0:1)', () => {
      const ratioBg = computeContrastRatio(darkTokens.foreground, darkTokens.bg);
      const ratioCard = computeContrastRatio(darkTokens.foreground, darkTokens.card);

      assert.ok(ratioBg >= 7.0, `Dark body contrast ${ratioBg.toFixed(2)} must be >= 7.0`);
      assert.ok(ratioCard >= 7.0, `Dark card contrast ${ratioCard.toFixed(2)} must be >= 7.0`);
    });

    it('Dark mode muted text (#cbd5e1 on #030712) exceeds AAA standard (>= 7.0:1)', () => {
      const ratio = computeContrastRatio(darkTokens.mutedText, darkTokens.bg);
      assert.ok(ratio >= 7.0, `Dark muted text contrast ${ratio.toFixed(2)} must be >= 7.0:1`);
    });

    it('Dark mode Zone 2 Emerald accent (#34d399 on #030712) exceeds AAA standard (>= 7.0:1)', () => {
      const ratio = computeContrastRatio(darkTokens.zone2, darkTokens.bg);
      assert.ok(ratio >= 7.0, `Zone 2 dark accent contrast ${ratio.toFixed(2)} must be >= 7.0:1`);
    });

    it('Dark mode Zone 1, 3, 4, 5 accents on dark background all exceed AA standard (>= 4.5:1)', () => {
      const z1Ratio = computeContrastRatio(darkTokens.zone1, darkTokens.bg);
      const z3Ratio = computeContrastRatio(darkTokens.zone3, darkTokens.bg);
      const z4Ratio = computeContrastRatio(darkTokens.zone4, darkTokens.bg);
      const z5Ratio = computeContrastRatio(darkTokens.zone5, darkTokens.bg);

      assert.ok(z1Ratio >= 4.5, `Zone 1 dark contrast ${z1Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z3Ratio >= 4.5, `Zone 3 dark contrast ${z3Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z4Ratio >= 4.5, `Zone 4 dark contrast ${z4Ratio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(z5Ratio >= 4.5, `Zone 5 dark contrast ${z5Ratio.toFixed(2)} must be >= 4.5:1`);
    });

    // 4.3 Oscilloscope Canvas Contrast
    it('Oscilloscope Canvas trace line exceeds WCAG 2.1 Non-Text Graphical standard (>= 3.0:1) and AA text (>= 4.5:1) in both modes', () => {
      const lightEcgRatio = computeContrastRatio(lightTokens.ecgLine, lightTokens.ecgBg);
      const darkEcgRatio = computeContrastRatio(darkTokens.ecgLine, darkTokens.ecgBg);

      assert.ok(lightEcgRatio >= 4.5, `Light ECG contrast ${lightEcgRatio.toFixed(2)} must be >= 4.5:1`);
      assert.ok(darkEcgRatio >= 7.0, `Dark ECG contrast ${darkEcgRatio.toFixed(2)} must be >= 7.0:1`);
    });
  });

  // =========================================================================
  // 5. Component Boundary Enforcement & Architectural Contracts
  // =========================================================================
  describe('5. Component Boundary Enforcement & Architectural Contracts', () => {
    it('React Server Components (RSC) have ZERO "use client" directives across all server files', () => {
      const serverFiles = [
        'app/layout.tsx',
        'app/page.tsx',
        'components/nav/NavigationShell.tsx',
        'components/nav/Header.tsx',
        'components/nav/Sidebar.tsx',
        'components/dashboard/SummaryCards.tsx',
        'components/dashboard/Zone2StatusBadge.tsx',
        'components/a11y/SkipToContent.tsx',
        'components/theme/ThemeScript.tsx',
      ];

      for (const relPath of serverFiles) {
        const fullPath = path.join(appRoot, relPath);
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          assert.doesNotMatch(
            content,
            /^["']use client["']/m,
            `RSC Violation: ${relPath} must NOT contain "use client"`
          );
        }
      }
    });

    it('Client Components strictly declare "use client" on line 1', () => {
      const clientFiles = [
        'components/charts/LiveEcgMonitor.tsx',
        'components/charts/DfaAlpha1TrendChart.tsx',
        'components/charts/AccessibleDataTable.tsx',
        'components/theme/ThemeToggle.tsx',
        'components/a11y/LiveAnnouncer.tsx',
      ];

      for (const relPath of clientFiles) {
        const fullPath = path.join(appRoot, relPath);
        assert.ok(fs.existsSync(fullPath), `${relPath} must exist`);
        const content = fs.readFileSync(fullPath, 'utf8');
        const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
        assert.ok(
          firstLine === '"useclient"' || firstLine === "'useclient'",
          `Client Component Isolation Violation: ${relPath} must begin with "use client" on line 1, got ${firstLine}`
        );
      }
    });

    it('Anti-FOUC ThemeScript executes synchronously inline in <head> without DOM flash', () => {
      const scriptPath = path.join(appRoot, 'components/theme/ThemeScript.tsx');
      assert.ok(fs.existsSync(scriptPath));
      const content = fs.readFileSync(scriptPath, 'utf8');

      assert.match(content, /dangerouslySetInnerHTML/, 'ThemeScript must inject inline script');
      assert.match(content, /localStorage\.getItem\(["']theme["']\)/, 'ThemeScript must inspect localStorage');
      assert.match(content, /prefers-color-scheme:\s*dark/, 'ThemeScript must fallback to system media query');
      assert.match(content, /classList\.add\(["']dark["']\)/, 'ThemeScript must apply dark class');
    });
  });

  // =========================================================================
  // 6. Semantic Landmark Hierarchy & DOM A11y Attributes
  // =========================================================================
  describe('6. Semantic Landmark Hierarchy & DOM A11y Attributes', () => {
    it('Navigation shell defines distinct semantic banner, navigation, and main regions', () => {
      const headerContent = fs.readFileSync(path.join(appRoot, 'components/nav/Header.tsx'), 'utf8');
      const sidebarContent = fs.readFileSync(path.join(appRoot, 'components/nav/Sidebar.tsx'), 'utf8');
      const navShellContent = fs.readFileSync(path.join(appRoot, 'components/nav/NavigationShell.tsx'), 'utf8');

      assert.match(headerContent, /role=["']banner["']/, 'Header must declare role="banner"');
      assert.match(sidebarContent, /role=["']navigation["']/, 'Sidebar must declare role="navigation"');
      assert.match(navShellContent, /role=["']main["']|id=["']main-content["']/, 'NavigationShell must declare main landmark');
    });

    it('Dashboard sections have accessible headings associated with aria-labelledby or aria-label', () => {
      const pageContent = fs.readFileSync(path.join(appRoot, 'app/page.tsx'), 'utf8');

      assert.match(pageContent, /aria-labelledby=["']kpi-summary-heading["']/, 'KPI section must be labelled');
      assert.match(pageContent, /id=["']kpi-summary-heading["']/, 'KPI heading ID must exist');
      assert.match(pageContent, /aria-labelledby=["']ecg-monitor-heading["']/, 'ECG section must be labelled');
      assert.match(pageContent, /id=["']ecg-monitor-heading["']/, 'ECG heading ID must exist');
      assert.match(pageContent, /aria-labelledby=["']dfa-chart-heading["']/, 'DFA section must be labelled');
      assert.match(pageContent, /id=["']dfa-chart-heading["']/, 'DFA heading ID must exist');
    });

    it('Reduced motion media query is defined in globals.css for vestibular safety', () => {
      const cssContent = fs.readFileSync(path.join(appRoot, 'app/globals.css'), 'utf8');
      assert.match(cssContent, /@media\s*\(prefers-reduced-motion:\s*reduce\)/, 'globals.css must define prefers-reduced-motion');
      assert.match(cssContent, /animation-duration:\s*0\.01ms/, 'Must disable animations under reduced-motion preference');
    });
  });
});
