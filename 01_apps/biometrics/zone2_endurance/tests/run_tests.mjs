#!/usr/bin/env node
/**
 * Master E2E & Unit Test Suite Runner for Zone 2 Endurance App
 * 
 * Executes all 5 tiers of automated test suites:
 * - Tier 1: Feature Coverage (RSC boundaries, Client isolation, Biometric contracts, Tailwind, a11y)
 * - Tier 2: Boundary & Corner Cases (DFA-a1 extremes, Kamath 20% filter, LeadStatus disconnection)
 * - Tier 3: Cross-Feature Combinations (Theme switching + Chart tokens, Keyboard navigation)
 * - Tier 4: Real-World Scenarios (60-min endurance simulation, Pw:HR decoupling, 128Hz sweep buffer)
 * - Tier 5: Adversarial Hardening (Stress toggling, Packet re-ordering, Float sanitization, Zero-mock audit)
 */

import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

const testFiles = [
  'tests/m1_scaffolding.test.mjs',
  'tests/m2_navigation_dashboard.test.mjs',
  'tests/m3_biometric_visualizers.test.mjs',
  'tests/tier1_feature_coverage.test.mjs',
  'tests/tier2_boundary_corner.test.mjs',
  'tests/tier3_cross_feature.test.mjs',
  'tests/tier4_real_world_e2e.test.mjs',
  'tests/tier5_adversarial_stress.test.mjs',
  'tests/challenger_empirical_stress.test.mjs',
  'tests/challenger_a11y_ui_behavior.test.mjs',
];

console.log('\n======================================================================');
console.log('🏃 ZONE 2 ENDURANCE AUTOMATED TEST SUITE RUNNER');
console.log('======================================================================\n');

let totalPassed = 0;
let totalFailed = 0;
const results = [];

async function runTestFile(fileRelPath) {
  const fullPath = path.join(appRoot, fileRelPath);
  return new Promise((resolve) => {
    const startTime = Date.now();
    const proc = spawn(process.execPath, ['--test', fullPath], {
      cwd: appRoot,
      env: { ...process.env, FORCE_COLOR: '1' },
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      const durationMs = Date.now() - startTime;
      const passed = code === 0;
      
      // Parse subtest counts from TAP output if present
      const passMatches = (stdout.match(/ok \d+/g) || []).length;
      const failMatches = (stdout.match(/not ok \d+/g) || []).length;

      resolve({
        file: fileRelPath,
        passed,
        durationMs,
        passCount: passMatches,
        failCount: failMatches,
        stdout,
        stderr,
      });
    });
  });
}

async function main() {
  for (const testFile of testFiles) {
    process.stdout.write(`  ⏳ Running ${testFile.padEnd(42)} `);
    const res = await runTestFile(testFile);
    results.push(res);

    if (res.passed) {
      console.log(`[32m✔ PASS[0m (${res.durationMs}ms)`);
      totalPassed++;
    } else {
      console.log(`[31m✖ FAIL[0m (${res.durationMs}ms)`);
      console.error(res.stderr || res.stdout);
      totalFailed++;
    }
  }

  console.log('\n----------------------------------------------------------------------');
  console.log('📊 TEST EXECUTION SUMMARY MATRIX');
  console.log('----------------------------------------------------------------------');
  console.table(
    results.map((r) => ({
      'Test Suite / Tier': r.file,
      Status: r.passed ? 'PASSED 🟢' : 'FAILED 🔴',
      Duration: `${r.durationMs}ms`,
    }))
  );

  console.log('======================================================================');
  if (totalFailed === 0) {
    console.log(`[32m🎉 ALL TEST TIERS PASSED! (${totalPassed}/${testFiles.length} suites passed, 100% pass rate)[0m`);
    console.log('======================================================================\n');
    process.exit(0);
  } else {
    console.log(`[31m💥 TEST FAILURES DETECTED! (${totalFailed}/${testFiles.length} suites failed)[0m`);
    console.log('======================================================================\n');
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal error running tests:', err);
  process.exit(1);
});
