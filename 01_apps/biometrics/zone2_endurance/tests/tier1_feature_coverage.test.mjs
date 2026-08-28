/**
 * Tier 1: Feature Coverage Test Suite
 * 
 * Verifies:
 * 1. React Server Component (RSC) Boundaries (Zero 'use client' in server layouts/shells)
 * 2. Client Component Isolation (Explicit 'use client' on interactive components)
 * 3. Biometric Data Contracts, Physiological Thresholds & Zone Classification
 * 4. Tailwind CSS Dark/Light Mode Configuration & HSL CSS Variables
 * 5. Strict WCAG Accessibility (a11y) Attributes, Semantic Landmarks & Focus Rings
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

describe('Tier 1: Feature Coverage — Architecture & Boundaries', () => {

  describe('1.1 React Server Component (RSC) Boundaries', () => {
    it('Root layout (app/layout.tsx) must be a pure Server Component without "use client"', () => {
      const layoutPath = path.join(appRoot, 'app/layout.tsx');
      assert.ok(fs.existsSync(layoutPath), 'app/layout.tsx must exist');
      const content = fs.readFileSync(layoutPath, 'utf8');
      
      assert.doesNotMatch(content, /^["']use client["']/m, 'app/layout.tsx must NOT contain "use client" directive');
      assert.match(content, /export\s+default\s+function\s+RootLayout/, 'app/layout.tsx must export default RootLayout function');
      assert.match(content, /export\s+const\s+metadata/, 'app/layout.tsx should export static metadata');
    });

    it('Dashboard root page (app/page.tsx) must be a Server Component without "use client"', () => {
      const pagePath = path.join(appRoot, 'app/page.tsx');
      assert.ok(fs.existsSync(pagePath), 'app/page.tsx must exist');
      const content = fs.readFileSync(pagePath, 'utf8');
      
      assert.doesNotMatch(content, /^["']use client["']/m, 'app/page.tsx must NOT contain "use client" directive');
    });

    it('Server navigation shell and summary card components (if present) must NOT contain "use client"', () => {
      const serverComponentPaths = [
        path.join(appRoot, 'components/nav/NavigationShell.tsx'),
        path.join(appRoot, 'components/nav/Header.tsx'),
        path.join(appRoot, 'components/nav/Sidebar.tsx'),
        path.join(appRoot, 'components/dashboard/SummaryCards.tsx'),
        path.join(appRoot, 'components/dashboard/Zone2StatusBadge.tsx'),
      ];

      for (const compPath of serverComponentPaths) {
        if (fs.existsSync(compPath)) {
          const content = fs.readFileSync(compPath, 'utf8');
          assert.doesNotMatch(
            content,
            /^["']use client["']/m,
            `${path.relative(appRoot, compPath)} must be an RSC and not contain "use client"`
          );
        }
      }
    });
  });

  describe('1.2 Client Component Isolation', () => {
    it('ThemeToggle component must be explicitly marked with "use client" at line 1', () => {
      const togglePath = path.join(appRoot, 'components/theme/ThemeToggle.tsx');
      assert.ok(fs.existsSync(togglePath), 'components/theme/ThemeToggle.tsx must exist');
      const content = fs.readFileSync(togglePath, 'utf8');
      
      const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
      assert.ok(
        firstLine === '"useclient"' || firstLine === "'useclient'",
        `ThemeToggle.tsx must start with "use client" directive on line 1, got: ${firstLine}`
      );
    });

    it('Live Biometric Visualization and Interactive components (if present) must be marked with "use client"', () => {
      const clientComponentPaths = [
        path.join(appRoot, 'components/charts/LiveEcgMonitor.tsx'),
        path.join(appRoot, 'components/charts/DfaAlpha1TrendChart.tsx'),
        path.join(appRoot, 'components/a11y/LiveAnnouncer.tsx'),
        path.join(appRoot, 'components/telemetry/TelemetryProvider.tsx'),
      ];

      for (const compPath of clientComponentPaths) {
        if (fs.existsSync(compPath)) {
          const content = fs.readFileSync(compPath, 'utf8');
          const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
          assert.ok(
            firstLine === '"useclient"' || firstLine === "'useclient'",
            `${path.relative(appRoot, compPath)} must start with "use client", got: ${firstLine}`
          );
        }
      }
    });
  });

  describe('1.3 Biometric Data Contracts & Physiological Thresholds', () => {
    it('types/biometrics.ts must export authoritative physiological constants and types', () => {
      const typesPath = path.join(appRoot, 'types/biometrics.ts');
      assert.ok(fs.existsSync(typesPath), 'types/biometrics.ts must exist');
      const content = fs.readFileSync(typesPath, 'utf8');

      // Verify essential interfaces are declared
      assert.match(content, /export\s+type\s+LeadStatus/, 'Must export LeadStatus type');
      assert.match(content, /export\s+type\s+BiometricZone/, 'Must export BiometricZone type');
      assert.match(content, /export\s+interface\s+EcgSample/, 'Must export EcgSample interface');
      assert.match(content, /export\s+interface\s+DfaAlpha1Point/, 'Must export DfaAlpha1Point interface');
      assert.match(content, /export\s+interface\s+BiometricSummary/, 'Must export BiometricSummary interface');
      assert.match(content, /export\s+interface\s+AerobicDecouplingMetrics/, 'Must export AerobicDecouplingMetrics interface');
      assert.match(content, /export\s+const\s+BIOMETRIC_THRESHOLDS/, 'Must export BIOMETRIC_THRESHOLDS constant');
    });

    it('Physiological threshold values must match clinical endurance standards', () => {
      const typesPath = path.join(appRoot, 'types/biometrics.ts');
      const content = fs.readFileSync(typesPath, 'utf8');

      assert.match(content, /ZONE_2_UPPER:\s*1\.00/, 'ZONE_2_UPPER must be 1.00');
      assert.match(content, /ZONE_2_LOWER:\s*0\.75/, 'ZONE_2_LOWER (LT1) must be 0.75');
      assert.match(content, /ZONE_3_LOWER:\s*0\.50/, 'ZONE_3_LOWER (LT2) must be 0.50');
      assert.match(content, /KAMATH_MAX_ARTIFACT_PCT:\s*20\.0/, 'KAMATH_MAX_ARTIFACT_PCT must be 20.0%');
      assert.match(content, /DECOUPLING_DRIFT_THRESHOLD_PCT:\s*5\.0/, 'DECOUPLING_DRIFT_THRESHOLD_PCT must be 5.0%');
    });

    it('classifyDfaZone() must correctly map DFA-alpha1 ranges to physiological zones', () => {
      function classifyDfaZone(alpha1) {
        if (alpha1 >= 1.00) return 'ZONE_1';
        if (alpha1 >= 0.75) return 'ZONE_2';
        if (alpha1 >= 0.50) return 'ZONE_3';
        if (alpha1 >= 0.35) return 'ZONE_4';
        return 'ZONE_5';
      }

      assert.equal(classifyDfaZone(1.25), 'ZONE_1', '1.25 must be Zone 1 Recovery');
      assert.equal(classifyDfaZone(1.00), 'ZONE_1', '1.00 must be Zone 1 / Upper Z2 edge');
      assert.equal(classifyDfaZone(0.85), 'ZONE_2', '0.85 must be Zone 2 Aerobic Base');
      assert.equal(classifyDfaZone(0.75), 'ZONE_2', '0.75 must be Zone 2 (LT1 exact threshold)');
      assert.equal(classifyDfaZone(0.65), 'ZONE_3', '0.65 must be Zone 3 Tempo');
      assert.equal(classifyDfaZone(0.50), 'ZONE_3', '0.50 must be Zone 3 (LT2 exact threshold)');
      assert.equal(classifyDfaZone(0.42), 'ZONE_4', '0.42 must be Zone 4 Anaerobic Threshold');
      assert.equal(classifyDfaZone(0.28), 'ZONE_5', '0.28 must be Zone 5 VO2Max / Anaerobic');
    });

    it('getZoneMetadata() must return distinct high-contrast colors and descriptive labels', () => {
      const zones = ['ZONE_1', 'ZONE_2', 'ZONE_3', 'ZONE_4', 'ZONE_5'];
      
      const zoneMetadataMap = {
        ZONE_1: { label: 'Zone 1 (Recovery)', color: '#0284c7' },
        ZONE_2: { label: 'Zone 2 (Aerobic Base)', color: '#059669' },
        ZONE_3: { label: 'Zone 3 (Tempo)', color: '#d97706' },
        ZONE_4: { label: 'Zone 4 (Threshold)', color: '#ea580c' },
        ZONE_5: { label: 'Zone 5 (Anaerobic / VO2Max)', color: '#e11d48' },
      };

      for (const zone of zones) {
        const meta = zoneMetadataMap[zone];
        assert.ok(meta, `Metadata must exist for ${zone}`);
        assert.ok(meta.label.length > 0, `Label must not be empty for ${zone}`);
        assert.match(meta.color, /^#[0-9a-fA-F]{6}$/, `Color must be a valid hex code for ${zone}`);
      }
    });
  });

  describe('1.4 Tailwind CSS Dark/Light Configuration & Color Tokens', () => {
    it('tailwind.config.ts must be configured with darkMode: "class"', () => {
      const configPath = path.join(appRoot, 'tailwind.config.ts');
      assert.ok(fs.existsSync(configPath), 'tailwind.config.ts must exist');
      const content = fs.readFileSync(configPath, 'utf8');

      assert.match(content, /darkMode:\s*["']class["']/, 'tailwind.config.ts must have darkMode: "class"');
      assert.match(content, /zone1/, 'Must configure zone1 color tokens');
      assert.match(content, /zone2/, 'Must configure zone2 color tokens');
      assert.match(content, /zone3/, 'Must configure zone3 color tokens');
      assert.match(content, /zone4/, 'Must configure zone4 color tokens');
      assert.match(content, /zone5/, 'Must configure zone5 color tokens');
    });

    it('app/globals.css must define HSL custom properties for both :root and .dark', () => {
      const cssPath = path.join(appRoot, 'app/globals.css');
      assert.ok(fs.existsSync(cssPath), 'app/globals.css must exist');
      const content = fs.readFileSync(cssPath, 'utf8');

      // Verify :root variables
      assert.match(content, /:root\s*\{/, 'globals.css must declare :root selector');
      assert.match(content, /--background:/, 'globals.css must declare --background');
      assert.match(content, /--foreground:/, 'globals.css must declare --foreground');
      assert.match(content, /--primary:/, 'globals.css must declare --primary');
      assert.match(content, /--card:/, 'globals.css must declare --card');
      assert.match(content, /--border:/, 'globals.css must declare --border');
      assert.match(content, /--ecg-bg:/, 'globals.css must declare --ecg-bg');

      // Verify .dark variables
      assert.match(content, /\.dark\s*\{/, 'globals.css must declare .dark selector');
      assert.match(content, /\.dark[^{]*\{[^}]*--background:/s, '.dark must define dark --background');
      assert.match(content, /\.dark[^{]*\{[^}]*--foreground:/s, '.dark must define dark --foreground');
      assert.match(content, /\.dark[^{]*\{[^}]*--primary:/s, '.dark must define dark --primary');
    });
  });

  describe('1.5 Strict Accessibility (a11y) & Semantic Landmarks', () => {
    it('app/layout.tsx must set html lang="en" and provide an accessible skip link', () => {
      const layoutPath = path.join(appRoot, 'app/layout.tsx');
      const content = fs.readFileSync(layoutPath, 'utf8');

      assert.match(content, /<html[^>]*lang=["']en["']/, 'HTML root must have lang="en" attribute');
      assert.match(content, /href=["']#main-content["']/, 'Layout must include a skip link targeting #main-content');
      assert.match(content, /className=["'][^"']*skip-link[^"']*["']/, 'Skip link must have skip-link class');
    });

    it('app/page.tsx must provide a main element with id="main-content"', () => {
      const pagePath = path.join(appRoot, 'app/page.tsx');
      const content = fs.readFileSync(pagePath, 'utf8');

      assert.match(content, /<main[^>]*id=["']main-content["']/, 'Page must have <main id="main-content"> landmark');
    });

    it('components/theme/ThemeToggle.tsx must implement accessible switch role and WCAG touch targets', () => {
      const togglePath = path.join(appRoot, 'components/theme/ThemeToggle.tsx');
      const content = fs.readFileSync(togglePath, 'utf8');

      assert.match(content, /role=["']switch["']/, 'ThemeToggle must declare role="switch"');
      assert.match(content, /aria-checked=/, 'ThemeToggle must declare dynamic aria-checked attribute');
      assert.match(content, /aria-label=/, 'ThemeToggle must declare informative aria-label attribute');
      assert.match(content, /min-h-\[44px\]/, 'ThemeToggle must satisfy WCAG 2.5.5 minimum 44px height target');
      assert.match(content, /min-w-\[44px\]/, 'ThemeToggle must satisfy WCAG 2.5.5 minimum 44px width target');
      assert.match(content, /focus-visible:ring-2/, 'ThemeToggle must feature high-visibility keyboard focus ring');
      assert.match(content, /tabIndex=\{0\}|type=["']button["']/, 'ThemeToggle must be focusable');
    });

    it('app/globals.css must define high-contrast focus rings and accessible skip-link styles', () => {
      const cssPath = path.join(appRoot, 'app/globals.css');
      const content = fs.readFileSync(cssPath, 'utf8');

      assert.match(content, /\.skip-link/, 'globals.css must define .skip-link utility');
      assert.match(content, /:focus-visible/, 'globals.css must define :focus-visible rules');
    });
  });
});
