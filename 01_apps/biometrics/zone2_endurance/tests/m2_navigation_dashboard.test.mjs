/**
 * Milestone 2: RSC Navigation Shell & Dashboard Component Verification Suite
 * 
 * Verifies:
 * 1. Pure React Server Component (RSC) isolation (Zero 'use client')
 * 2. Header semantic banner, branding, live status pill, and ThemeToggle embedding
 * 3. Sidebar semantic navigation landmark, accessible nav links, active state, and focus rings
 * 4. NavigationShell responsive integration with <main id="main-content" role="main" tabIndex={-1}>
 * 5. SkipToContent accessible keyboard skip link
 * 6. SummaryCards real-time metrics, HH:MM:SS accumulator, aerobic decoupling drift, and zero-mock sensor states
 * 7. Zone2StatusBadge high-contrast physiological tokens and corridor indicators
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

describe('Milestone 2: RSC Navigation Shell & Dashboard Telemetry Console', () => {

  describe('2.1 Pure React Server Component (RSC) Architecture', () => {
    const m2ServerComponents = [
      'components/a11y/SkipToContent.tsx',
      'components/nav/Header.tsx',
      'components/nav/Sidebar.tsx',
      'components/nav/NavigationShell.tsx',
      'components/dashboard/SummaryCards.tsx',
      'components/dashboard/Zone2StatusBadge.tsx',
    ];

    for (const relPath of m2ServerComponents) {
      it(`${relPath} must exist and strictly contain NO "use client" directive`, () => {
        const fullPath = path.join(appRoot, relPath);
        assert.ok(fs.existsSync(fullPath), `${relPath} must exist on disk`);
        const content = fs.readFileSync(fullPath, 'utf8');

        assert.doesNotMatch(
          content,
          /^["']use client["']/m,
          `${relPath} must be a pure React Server Component (RSC)`
        );
      });
    }
  });

  describe('2.2 Header Component (components/nav/Header.tsx)', () => {
    it('Implements semantic role="banner", branding, live status pill, and ThemeToggle', () => {
      const headerPath = path.join(appRoot, 'components/nav/Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf8');

      // Semantic Landmark
      assert.match(content, /role=["']banner["']/, 'Header must declare role="banner"');
      assert.match(content, /aria-label=["']Application Header["']/, 'Header must declare aria-label');

      // Branding
      assert.match(content, /Zone 2 Endurance Biometrics/, 'Header must feature default branding title');

      // Live Session Status Pill
      assert.match(content, /role=["']status["']/, 'Header must include live status region');
      assert.match(content, /animate-ping/, 'Header must render pulsing live telemetry indicator');

      // Embedded ThemeToggle
      assert.match(content, /import\s*\{\s*ThemeToggle\s*\}\s*from/, 'Header must import ThemeToggle');
      assert.match(content, /<ThemeToggle\s*\/>/, 'Header must render <ThemeToggle />');
    });
  });

  describe('2.3 Sidebar Component (components/nav/Sidebar.tsx)', () => {
    it('Implements semantic role="navigation", accessible nav items, active state, and focus rings', () => {
      const sidebarPath = path.join(appRoot, 'components/nav/Sidebar.tsx');
      const content = fs.readFileSync(sidebarPath, 'utf8');

      // Semantic Landmark
      assert.match(content, /role=["']navigation["']/, 'Sidebar must declare role="navigation"');
      assert.match(content, /aria-label=["']Main Navigation["']/, 'Sidebar must declare aria-label="Main Navigation"');

      // Required Nav Items
      assert.match(content, /label:\s*["']Dashboard["']/, 'Sidebar must include Dashboard item');
      assert.match(content, /label:\s*["']Live ECG["']/, 'Sidebar must include Live ECG item');
      assert.match(content, /label:\s*["']DFA-alpha1["']/, 'Sidebar must include DFA-alpha1 item');
      assert.match(content, /label:\s*["']Session History["']/, 'Sidebar must include Session History item');
      assert.match(content, /label:\s*["']Settings["']/, 'Sidebar must include Settings item');

      // Active state and keyboard focus rings
      assert.match(content, /aria-current=\{isActive\s*\?\s*["']page["']\s*:\s*undefined\}/, 'Sidebar must set dynamic aria-current="page"');
      assert.match(content, /focus-visible:ring-2/, 'Sidebar links must have high-visibility focus-visible rings');
    });
  });

  describe('2.4 NavigationShell Component (components/nav/NavigationShell.tsx)', () => {
    it('Orchestrates Header, Sidebar, and primary <main id="main-content" role="main" tabIndex={-1}>', () => {
      const shellPath = path.join(appRoot, 'components/nav/NavigationShell.tsx');
      const content = fs.readFileSync(shellPath, 'utf8');

      // Subcomponents
      assert.match(content, /<Header/, 'NavigationShell must render Header component');
      assert.match(content, /<Sidebar/, 'NavigationShell must render Sidebar component');

      // Main Landmark
      assert.match(content, /<main[^>]*id=["']main-content["']/, 'NavigationShell must render <main id="main-content">');
      assert.match(content, /role=["']main["']/, 'NavigationShell main container must declare role="main"');
      assert.match(content, /tabIndex=\{-1\}/, 'NavigationShell main container must have tabIndex={-1} for skip-link focusability');
    });
  });

  describe('2.5 SkipToContent Component (components/a11y/SkipToContent.tsx)', () => {
    it('Renders accessible anchor targeting #main-content with skip-link class', () => {
      const skipPath = path.join(appRoot, 'components/a11y/SkipToContent.tsx');
      const content = fs.readFileSync(skipPath, 'utf8');

      assert.match(content, /href=\{`#\$\{targetId\}`\}/, 'Skip link must target targetId');
      assert.match(content, /skip-link/, 'Skip link must apply .skip-link class');
    });
  });

  describe('2.6 Zone2StatusBadge Component (components/dashboard/Zone2StatusBadge.tsx)', () => {
    it('Renders high-contrast tokens, accessible status label, and target corridor hints', () => {
      const badgePath = path.join(appRoot, 'components/dashboard/Zone2StatusBadge.tsx');
      const content = fs.readFileSync(badgePath, 'utf8');

      assert.match(content, /role=["']status["']/, 'Zone2StatusBadge must declare role="status"');
      assert.match(content, /classifyDfaZone/, 'Zone2StatusBadge must support dynamic classification from DFA-alpha1');
      assert.match(content, /getZoneMetadata/, 'Zone2StatusBadge must retrieve zone styling metadata');
      assert.match(content, /showCorridorHint/, 'Zone2StatusBadge must support corridor hint display');
    });
  });

  describe('2.7 SummaryCards Component (components/dashboard/SummaryCards.tsx)', () => {
    it('Implements all 5 required real-time biometric metrics and zero-mock resilience', () => {
      const cardsPath = path.join(appRoot, 'components/dashboard/SummaryCards.tsx');
      const content = fs.readFileSync(cardsPath, 'utf8');

      // Semantic Section Landmark
      assert.match(content, /role=["']region["']/, 'SummaryCards must declare role="region"');
      assert.match(content, /aria-label=["']Biometric Summary Metrics["']/, 'SummaryCards must declare aria-label');

      // 5 Required Cards
      assert.match(content, /Heart Rate/, 'Must render Heart Rate card');
      assert.match(content, /DFA-&alpha;1 Fractal/, 'Must render DFA-alpha1 Fractal card');
      assert.match(content, /Zone 2 Duration/, 'Must render Zone 2 Duration card');
      assert.match(content, /Decoupling \(Pw:HR\)/, 'Must render Aerobic Decoupling card');
      assert.match(content, /Sensor Quality/, 'Must render Movesense Sensor Quality card');

      // Time accumulator format
      assert.match(content, /formatDuration/, 'Must implement HH:MM:SS duration formatting');

      // Decoupling drift check
      assert.match(content, /DECOUPLING_DRIFT_THRESHOLD_PCT/, 'Must reference 5.0% decoupling threshold');

      // Zero-mock placeholder when disconnected
      assert.match(content, /"--"/, 'Must render clean uninitialized indicators ("--") when sensor is disconnected');
    });
  });
});
