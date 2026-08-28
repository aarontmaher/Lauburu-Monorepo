/**
 * Test Helpers & Component Loader for Canonical Port E2E Test Suite
 * Version: 3.0.0-CANONICAL
 * Supports opaque-box React SSR rendering, DOM inspection, text normalization, and zero-mock assertions.
 */

import esbuild from 'esbuild';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import React from 'react';
import { renderToString } from 'react-dom/server';
import assert from 'node:assert/strict';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '../..');
const BUNDLE_DIR = path.resolve(ROOT_DIR, 'node_modules/.test_bundle_cache');

// Ensure bundle cache directory exists
if (!fs.existsSync(BUNDLE_DIR)) {
  fs.mkdirSync(BUNDLE_DIR, { recursive: true });
}

const moduleCache = new Map();

/**
 * Compiles and imports a React component or module using esbuild
 * @param {string} relativePath - Relative path from canonical_port root
 * @returns {Promise<any>} Imported module
 */
export async function loadComponent(relativePath) {
  if (moduleCache.has(relativePath)) {
    return moduleCache.get(relativePath);
  }

  const srcPath = path.resolve(ROOT_DIR, relativePath);
  const baseName = path.basename(relativePath, path.extname(relativePath));
  const outPath = path.resolve(BUNDLE_DIR, `${baseName}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}.js`);

  esbuild.buildSync({
    entryPoints: [srcPath],
    outfile: outPath,
    bundle: true,
    format: 'esm',
    external: ['react', 'react-dom', 'react-dom/server'],
    loader: {
      '.jsx': 'jsx',
      '.js': 'js',
      '.ts': 'ts',
      '.tsx': 'tsx',
      '.css': 'empty'
    }
  });

  const imported = await import(outPath);
  moduleCache.set(relativePath, imported);
  return imported;
}

/**
 * Renders a React component to an HTML string
 * @param {React.ComponentType} Component
 * @param {object} props
 * @returns {string} Rendered HTML string
 */
export function render(Component, props = {}) {
  assert(Component, 'Component must not be undefined or null');
  return renderToString(React.createElement(Component, props));
}

/**
 * Normalizes HTML string to plain text for robust text assertions
 * Strips comments, tags, extra whitespace and decodes standard entities.
 * @param {string} html
 * @returns {string} Clean plain text
 */
export function normalizeText(html) {
  return html
    .replace(/<!--[\s\S]*?-->/g, '') // remove HTML comments
    .replace(/<[^>]+>/g, ' ')       // remove HTML tags
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x2B07;/g, '⬇')
    .replace(/&#x2B06;/g, '⬆')
    .replace(/\s+/g, ' ')           // normalize whitespace
    .trim();
}

/**
 * Assert that HTML contains specified string or matches regex
 * @param {string} html
 * @param {string|RegExp} pattern
 * @param {string} [message]
 */
export function assertContains(html, pattern, message) {
  if (pattern instanceof RegExp) {
    assert(pattern.test(html), message || `Expected HTML to match regex: ${pattern}`);
  } else {
    assert(html.includes(pattern), message || `Expected HTML to contain string: "${pattern}"`);
  }
}

/**
 * Assert that normalized text content of HTML contains specified string or matches regex
 * @param {string} html
 * @param {string|RegExp} pattern
 * @param {string} [message]
 */
export function assertTextContains(html, pattern, message) {
  const text = normalizeText(html);
  if (pattern instanceof RegExp) {
    assert(pattern.test(text), message || `Expected text "${text.slice(0, 100)}..." to match regex: ${pattern}`);
  } else {
    assert(text.includes(pattern), message || `Expected text "${text.slice(0, 100)}..." to contain string: "${pattern}"`);
  }
}

/**
 * Assert that HTML does NOT contain specified string or regex
 * @param {string} html
 * @param {string|RegExp} pattern
 * @param {string} [message]
 */
export function assertNotContains(html, pattern, message) {
  if (pattern instanceof RegExp) {
    assert(!pattern.test(html), message || `Expected HTML NOT to match regex: ${pattern}`);
  } else {
    assert(!html.includes(pattern), message || `Expected HTML NOT to contain string: "${pattern}"`);
  }
}

/**
 * Create a lightweight Test Runner Suite
 */
export function createTestSuite(suiteName) {
  const tests = [];
  let passedCount = 0;
  let failedCount = 0;

  return {
    test(testName, fn) {
      tests.push({ name: testName, fn });
    },
    async run() {
      console.log(`\n======================================================================`);
      console.log(`  RUNNING SUITE: ${suiteName}`);
      console.log(`======================================================================`);

      const results = [];
      for (const t of tests) {
        const t0 = performance.now();
        try {
          await t.fn();
          const duration = (performance.now() - t0).toFixed(2);
          console.log(`  ✓ [PASS] ${t.name} (${duration}ms)`);
          passedCount++;
          results.push({ name: t.name, status: 'PASS', durationMs: duration });
        } catch (err) {
          const duration = (performance.now() - t0).toFixed(2);
          console.error(`  ✗ [FAIL] ${t.name} (${duration}ms)`);
          console.error(`     Error: ${err.message}`);
          if (err.stack) {
            console.error(`     ${err.stack.split('\n').slice(1, 4).join('\n     ')}`);
          }
          failedCount++;
          results.push({ name: t.name, status: 'FAIL', error: err.message, durationMs: duration });
        }
      }

      console.log(`----------------------------------------------------------------------`);
      console.log(`  SUMMARY: ${passedCount} Passed, ${failedCount} Failed (Total: ${tests.length})`);
      console.log(`======================================================================\n`);

      return {
        suiteName,
        total: tests.length,
        passed: passedCount,
        failed: failedCount,
        results
      };
    }
  };
}
