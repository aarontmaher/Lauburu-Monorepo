/**
 * Milestone 3: Client Biometric Visualizers & a11y Test Suite
 * 
 * Verifies:
 * 1. LiveEcgMonitor: Canvas 128Hz Oscilloscope, 640-sample ring buffer, sweep speed/gain controls, lead statuses, float sanitization
 * 2. DfaAlpha1TrendChart: Shaded [0.75, 1.00] Zone 2 corridor, 0.75 LT1 & 0.50 LT2 guides, Kamath 20% filter, tooltips & a11y
 * 3. AccessibleDataTable: Semantic <table>, <caption className="sr-only">, <th scope="col">, pagination, readable row format
 * 4. LiveAnnouncer: Dual polite/assertive ARIA live regions, sr-only, atomic updates
 * 5. App Integration: Root layout and dashboard page wiring with full dark mode & a11y support
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

describe('Milestone 3: Client Biometric Visualizers & a11y Specialist Tests', () => {

  describe('3.1 LiveEcgMonitor Component Verification', () => {
    const ecgPath = path.join(appRoot, 'components/charts/LiveEcgMonitor.tsx');

    it('LiveEcgMonitor.tsx exists and is marked with "use client" on line 1', () => {
      assert.ok(fs.existsSync(ecgPath), 'LiveEcgMonitor.tsx must exist in components/charts/');
      const content = fs.readFileSync(ecgPath, 'utf8');
      const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
      assert.ok(
        firstLine === '"useclient"' || firstLine === "'useclient'",
        `LiveEcgMonitor must start with "use client", got: ${firstLine}`
      );
    });

    it('Implements 640-sample circular ring buffer with float sanitization', () => {
      const content = fs.readFileSync(ecgPath, 'utf8');
      assert.match(content, /class\s+EcgSweepRingBuffer/, 'Must define EcgSweepRingBuffer class');
      assert.match(content, /Float32Array\(capacity\)/, 'Must use Float32Array for allocation efficiency');
      assert.match(content, /capacity:\s*number\s*=\s*640/, 'Default buffer capacity must be 640 samples (5.0s @ 128Hz)');
      assert.match(content, /Math\.max\(-5\.0,\s*Math\.min\(5\.0,\s*v\)\)/, 'Must clamp voltages to [-5.0, 5.0] mV');
    });

    it('Renders Canvas element with role="img", high-contrast trace, and accessible fallback text', () => {
      const content = fs.readFileSync(ecgPath, 'utf8');
      assert.match(content, /<canvas[^>]*role=["']img["']/, 'Canvas must declare role="img"');
      assert.match(content, /aria-label=/, 'Canvas must feature dynamic aria-label');
      assert.match(content, /#059669/, 'Must configure Emerald #059669 light trace color');
      assert.match(content, /#34d399/, 'Must configure Emerald #34d399 dark trace color');
      assert.match(content, /Real-time.*ECG.*oscilloscope/, 'Must include accessible inner text fallback');
    });

    it('Provides interactive controls: Pause/Resume, Sweep speed, Gain, Clear, and Table toggle', () => {
      const content = fs.readFileSync(ecgPath, 'utf8');
      assert.match(content, /aria-pressed=\{isPaused\}/, 'Pause button must have aria-pressed');
      assert.match(content, /Speed:/, 'Must provide sweep speed selector');
      assert.match(content, /Gain:/, 'Must provide gain sensitivity selector');
      assert.match(content, /min-h-\[44px\]/, 'Interactive controls must satisfy WCAG 44px touch target');
      assert.match(content, /focus-visible:ring-2/, 'Controls must feature high-visibility keyboard focus rings');
      assert.match(content, /AccessibleDataTable/, 'Must integrate AccessibleDataTable component');
    });

    it('Handles all standard Lead Statuses with distinct badges and ARIA labels', () => {
      const content = fs.readFileSync(ecgPath, 'utf8');
      assert.match(content, /Lead:\s*Optimal/, 'Must handle Optimal / Connected lead');
      assert.match(content, /Motion Artifact/, 'Must handle Noisy Motion lead');
      assert.match(content, /Dry Electrodes/, 'Must handle Poor Contact lead');
      assert.match(content, /Lead Off/, 'Must handle Lead Off / Off Body lead');
      assert.match(content, /Disconnected/, 'Must handle Disconnected lead');
    });
  });

  describe('3.2 DfaAlpha1TrendChart Component Verification', () => {
    const dfaPath = path.join(appRoot, 'components/charts/DfaAlpha1TrendChart.tsx');

    it('DfaAlpha1TrendChart.tsx exists and is marked with "use client" on line 1', () => {
      assert.ok(fs.existsSync(dfaPath), 'DfaAlpha1TrendChart.tsx must exist in components/charts/');
      const content = fs.readFileSync(dfaPath, 'utf8');
      const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
      assert.ok(
        firstLine === '"useclient"' || firstLine === "'useclient'",
        `DfaAlpha1TrendChart must start with "use client", got: ${firstLine}`
      );
    });

    it('Renders shaded [0.75, 1.00] Zone 2 corridor and 0.75 LT1 / 0.50 LT2 guidelines', () => {
      const content = fs.readFileSync(dfaPath, 'utf8');
      assert.match(content, /AEROBIC ZONE 2 CORRIDOR/, 'Must render Zone 2 corridor banner');
      assert.match(content, /LT1 Aerobic \(0\.75\)/, 'Must render LT1 0.75 threshold guideline');
      assert.match(content, /LT2 Anaerobic \(0\.50\)/, 'Must render LT2 0.50 threshold guideline');
      assert.match(content, /strokeDasharray=["']6 3["']|strokeDasharray=["']4 4["']/, 'Thresholds must use dashed guidelines');
    });

    it('Includes Kamath 2004 20% RR interval artifact filter indicator', () => {
      const content = fs.readFileSync(dfaPath, 'utf8');
      assert.match(content, /KAMATH_MAX_ARTIFACT_PCT/, 'Must reference Kamath 20% artifact threshold');
      assert.match(content, /Low Confidence/, 'Must display Low Confidence warning when artifact exceeds 20%');
      assert.match(content, /Kamath Filter Clean/, 'Must display clean filter badge when artifact is normal');
    });

    it('Implements accessible keyboard point inspection and tooltip', () => {
      const content = fs.readFileSync(dfaPath, 'utf8');
      assert.match(content, /role=["']button["']/, 'Data points must declare role="button"');
      assert.match(content, /tabIndex=\{0\}/, 'Data points must be focusable via tabIndex={0}');
      assert.match(content, /onKeyDown=/, 'Data points must support arrow key navigation');
      assert.match(content, /role=["']tooltip["']/, 'Hover/focus tooltip must declare role="tooltip"');
      assert.match(content, /aria-live=["']polite["']/, 'Screen reader summary must declare aria-live="polite"');
    });
  });

  describe('3.3 AccessibleDataTable Component Verification', () => {
    const tablePath = path.join(appRoot, 'components/charts/AccessibleDataTable.tsx');

    it('AccessibleDataTable.tsx exists and is marked with "use client" on line 1', () => {
      assert.ok(fs.existsSync(tablePath), 'AccessibleDataTable.tsx must exist in components/charts/');
      const content = fs.readFileSync(tablePath, 'utf8');
      const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
      assert.ok(
        firstLine === '"useclient"' || firstLine === "'useclient'",
        `AccessibleDataTable must start with "use client", got: ${firstLine}`
      );
    });

    it('Implements semantic HTML <table> with sr-only caption and <th scope="col"> headers', () => {
      const content = fs.readFileSync(tablePath, 'utf8');
      assert.match(content, /<table[^>]*>/, 'Must render semantic <table> element');
      assert.match(content, /<caption[^>]*className=["'][^"']*sr-only[^"']*["']/, 'Must include <caption className="sr-only">');
      assert.match(content, /<th[^>]*scope=["']col["']/, 'Must include <th scope="col"> column headers');
      assert.match(content, /<th[^>]*scope=["']row["']/, 'Must include <th scope="row"> row headers');
      assert.match(content, /Heart Rate \(BPM\)/, 'Must include Heart Rate header');
      assert.match(content, /DFA &alpha;1|DFA α1|DFA/, 'Must include DFA alpha-1 header');
      assert.match(content, /Physiological Zone/, 'Must include Zone header');
      assert.match(content, /Kamath Artifact %/, 'Must include Artifact header');
    });

    it('Provides accessible pagination controls', () => {
      const content = fs.readFileSync(tablePath, 'utf8');
      assert.match(content, /aria-label=["']Previous Page["']/, 'Must provide accessible Previous Page button');
      assert.match(content, /aria-label=["']Next Page["']/, 'Must provide accessible Next Page button');
      assert.match(content, /disabled=\{currentPage\s*<=\s*1\}/, 'Must handle disabled state for first page');
    });
  });

  describe('3.4 LiveAnnouncer Component Verification', () => {
    const announcerPath = path.join(appRoot, 'components/a11y/LiveAnnouncer.tsx');

    it('LiveAnnouncer.tsx exists and is marked with "use client" on line 1', () => {
      assert.ok(fs.existsSync(announcerPath), 'LiveAnnouncer.tsx must exist in components/a11y/');
      const content = fs.readFileSync(announcerPath, 'utf8');
      const firstLine = content.trim().split('\n')[0].replace(/[;\s]/g, '');
      assert.ok(
        firstLine === '"useclient"' || firstLine === "'useclient'",
        `LiveAnnouncer must start with "use client", got: ${firstLine}`
      );
    });

    it('Renders dual polite (status) and assertive (alert) ARIA live regions with sr-only styling', () => {
      const content = fs.readFileSync(announcerPath, 'utf8');
      assert.match(content, /aria-live=["']polite["']/, 'Must include polite ARIA live region');
      assert.match(content, /role=["']status["']/, 'Polite region must have role="status"');
      assert.match(content, /aria-live=["']assertive["']/, 'Must include assertive ARIA live region');
      assert.match(content, /role=["']alert["']/, 'Assertive region must have role="alert"');
      assert.match(content, /aria-atomic=["']true["']/, 'Live regions must declare aria-atomic="true"');
      assert.match(content, /className=["'][^"']*sr-only[^"']*["']/, 'Live regions must be styled with sr-only');
    });
  });

  describe('3.5 Full Application Dashboard Integration', () => {
    it('app/layout.tsx integrates LiveAnnouncer and NavigationShell as an RSC', () => {
      const layoutPath = path.join(appRoot, 'app/layout.tsx');
      const content = fs.readFileSync(layoutPath, 'utf8');
      assert.doesNotMatch(content, /^["']use client["']/m, 'app/layout.tsx must NOT contain "use client"');
      assert.match(content, /<LiveAnnouncer/, 'layout.tsx must render LiveAnnouncer');
      assert.match(content, /<NavigationShell/, 'layout.tsx must render NavigationShell');
    });

    it('app/page.tsx integrates SummaryCards, LiveEcgMonitor, and DfaAlpha1TrendChart as an RSC', () => {
      const pagePath = path.join(appRoot, 'app/page.tsx');
      const content = fs.readFileSync(pagePath, 'utf8');
      assert.doesNotMatch(content, /^["']use client["']/m, 'app/page.tsx must NOT contain "use client"');
      assert.match(content, /<SummaryCards/, 'page.tsx must render SummaryCards');
      assert.match(content, /<LiveEcgMonitor/, 'page.tsx must render LiveEcgMonitor');
      assert.match(content, /<DfaAlpha1TrendChart/, 'page.tsx must render DfaAlpha1TrendChart');
      assert.match(content, /<main[^>]*id=["']main-content["']/, 'page.tsx must have <main id="main-content">');
    });
  });
});
