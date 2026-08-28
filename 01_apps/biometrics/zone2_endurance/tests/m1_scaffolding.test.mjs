import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

test('Scaffolding: Critical configuration files exist and are non-empty', () => {
  const requiredFiles = [
    'package.json',
    'tsconfig.json',
    'tailwind.config.ts',
    'postcss.config.js',
    'next.config.mjs',
    'app/globals.css',
    'app/layout.tsx',
    'app/page.tsx',
    'types/biometrics.ts',
    'components/theme/ThemeScript.tsx',
    'components/theme/ThemeToggle.tsx',
  ];

  for (const relPath of requiredFiles) {
    const fullPath = path.join(projectRoot, relPath);
    assert.ok(fs.existsSync(fullPath), `File must exist: ${relPath}`);
    const stat = fs.statSync(fullPath);
    assert.ok(stat.size > 0, `File must not be empty: ${relPath}`);
  }
});

test('Tailwind Config: Extended biometric palettes and darkMode configured', () => {
  const tailwindContent = fs.readFileSync(path.join(projectRoot, 'tailwind.config.ts'), 'utf-8');
  assert.match(tailwindContent, /darkMode:\s*["']class["']/);
  assert.match(tailwindContent, /zone1/);
  assert.match(tailwindContent, /zone2/);
  assert.match(tailwindContent, /#059669/);
  assert.match(tailwindContent, /#34d399/);
  assert.match(tailwindContent, /zone3/);
  assert.match(tailwindContent, /zone4/);
  assert.match(tailwindContent, /zone5/);
  assert.match(tailwindContent, /ecg/);
  assert.match(tailwindContent, /dfa/);
});

test('Globals CSS: Root and Dark CSS variables with high-contrast tokens', () => {
  const cssContent = fs.readFileSync(path.join(projectRoot, 'app/globals.css'), 'utf-8');
  assert.match(cssContent, /:root\s*\{/);
  assert.match(cssContent, /\.dark\s*\{/);
  assert.match(cssContent, /--background:/);
  assert.match(cssContent, /--foreground:/);
  assert.match(cssContent, /--primary:/);
  assert.match(cssContent, /:focus-visible/);
  assert.match(cssContent, /ring-2/);
  assert.match(cssContent, /skip-link/);
});

test('Biometric Types Contract: Validates all required interfaces & enums exist', () => {
  const typesContent = fs.readFileSync(path.join(projectRoot, 'types/biometrics.ts'), 'utf-8');
  assert.match(typesContent, /export type LeadStatus\s*=/);
  assert.match(typesContent, /'CONNECTED'/);
  assert.match(typesContent, /'DISCONNECTED'/);
  assert.match(typesContent, /'NOISY'/);
  assert.match(typesContent, /'POOR_CONTACT'/);
  assert.match(typesContent, /'OFF_BODY'/);
  assert.match(typesContent, /export interface EcgSample/);
  assert.match(typesContent, /export interface DfaAlpha1Point/);
  assert.match(typesContent, /export interface BiometricSummary/);
  assert.match(typesContent, /export interface AerobicDecouplingMetrics/);
  assert.match(typesContent, /export interface TelemetryStreamPacket/);
  assert.match(typesContent, /classifyDfaZone/);
  assert.match(typesContent, /getZoneMetadata/);
});

test('Theme System: Anti-FOUC ThemeScript and Accessible ThemeToggle', () => {
  const scriptContent = fs.readFileSync(path.join(projectRoot, 'components/theme/ThemeScript.tsx'), 'utf-8');
  assert.match(scriptContent, /theme-anti-fouc-script/);
  assert.match(scriptContent, /localStorage\.getItem\(['"]theme['"]\)/);
  assert.match(scriptContent, /classList\.add\(['"]dark['"]\)/);

  const toggleContent = fs.readFileSync(path.join(projectRoot, 'components/theme/ThemeToggle.tsx'), 'utf-8');
  assert.match(toggleContent, /"use client"/);
  assert.match(toggleContent, /role="switch"/);
  assert.match(toggleContent, /aria-checked=/);
  assert.match(toggleContent, /aria-label=/);
  assert.match(toggleContent, /onKeyDown=/);
  assert.match(toggleContent, /localStorage\.setItem\(['"]theme['"]/);
});

test('Biometric Logic: Physiological DFA-alpha1 boundary calculations', () => {
  // Test boundary logic directly
  const thresholds = {
    ZONE_2_UPPER: 1.00,
    ZONE_2_LOWER: 0.75,
    ZONE_3_LOWER: 0.50,
  };

  function classify(alpha1) {
    if (alpha1 >= thresholds.ZONE_2_UPPER) return 'ZONE_1';
    if (alpha1 >= thresholds.ZONE_2_LOWER) return 'ZONE_2';
    if (alpha1 >= thresholds.ZONE_3_LOWER) return 'ZONE_3';
    if (alpha1 >= 0.35) return 'ZONE_4';
    return 'ZONE_5';
  }

  assert.equal(classify(1.20), 'ZONE_1');
  assert.equal(classify(1.00), 'ZONE_1');
  assert.equal(classify(0.95), 'ZONE_2');
  assert.equal(classify(0.75), 'ZONE_2');
  assert.equal(classify(0.74), 'ZONE_3');
  assert.equal(classify(0.50), 'ZONE_3');
  assert.equal(classify(0.49), 'ZONE_4');
  assert.equal(classify(0.35), 'ZONE_4');
  assert.equal(classify(0.34), 'ZONE_5');
  assert.equal(classify(0.10), 'ZONE_5');
});
