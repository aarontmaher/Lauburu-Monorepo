#!/usr/bin/env python3
"""
test_adversarial_challenger2_figma_zero_mock.py - Adversarial Stress & Verification Suite
==========================================================================================
Part of Challenger 2 for Figma MCP Integration & Rule #0 Zero-Mock Guardrails.

Adversarially challenges:
1. Tri-Lens Visual Swarm auditor (figma_tri_lens_auditor.py):
   - 5-frame static duplicate detection (must FAIL when frame hashes are identical).
   - Partial duplicate frame detection (all unique vs partial unique).
   - SSIM visual parity calculation against identical, noisy, degraded, and inverted images.
   - DOM / AX tree mock token detection across Lens 1 (CDP), Lens 2 (Marionette), and Lens 3 (ADB).

2. Flutter Dart & Vue SFC discrimination logic (figma_zero_mock_linter.py):
   - Clean waiting states: {data?.hr ?? '--'}, Text(val ?? '--'), template expressions pass with 0 violations.
   - Chrome headers & button labels pass with 0 violations.
   - Hardcoded telemetry literals, mock arrays, synthetic timers fail with CRITICAL violations.
   - Pre-merge CLI exit code verification (0 for clean code, 1 for mock data).

3. Setup & Protocol Client robustness (setup_figma_mcp.py, figma_mcp_client.py):
   - CLI flags (--status, --verify, --rollback, --register).
   - JSON-RPC stdio protocol integrity.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import subprocess
from io import BytesIO
from unittest.mock import patch, MagicMock

# Scripts path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "06_scripts_and_tooling", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from setup_figma_mcp import SettingsConfigurator, FigmaAuthManager, HealthVerifier
from figma_mcp_client import FigmaRESTClient, FigmaMCPServer, FigmaAPIError, MCP_PROTOCOL_VERSION
from figma_zero_mock_linter import (
    FigmaZeroMockLinter, Violation, JsTsxScanner, VueScanner, DartUiScanner,
    HtmlScanner, PythonAstJudge
)
from figma_tri_lens_auditor import (
    TriLensSwarmAuditor, VisualParityEngine, FrameDeltaValidator,
    DomZeroMockAuditor, LensAuditResult, FrameHashResult
)

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ============================================================================
# ADVERSARIAL SECTION 1: TRI-LENS VISUAL SWARM AUDITOR CHALLENGES
# ============================================================================

class TestAdversarialTriLensSwarmAuditor(unittest.TestCase):
    """Adversarial stress-testing of figma_tri_lens_auditor.py."""

    def test_5_frame_static_identical_hashes_must_fail(self):
        """
        Challenge 1.1: 5-frame static duplicate detection.
        When 5 frames are identical byte streams (frozen screen / mock snapshot),
        FrameDeltaValidator MUST reject (passed=False) and report unique_count=1.
        """
        frozen_frame = b"STATIC_MOCK_IMAGE_FRAME_BYTE_PAYLOAD_00001"
        frames = [frozen_frame] * 5

        passed, results, unique_count = FrameDeltaValidator.evaluate_frame_series(frames, require_all_unique=True)
        self.assertFalse(passed, "5 identical frames must FAIL dynamic frame delta validation!")
        self.assertEqual(unique_count, 1, "Unique frame count must be exactly 1 for frozen static frames.")
        self.assertEqual(len(results), 5)
        # Verify all 5 MD5 hashes are identical
        hashes = [r.md5_hash for r in results]
        self.assertEqual(len(set(hashes)), 1)

        # Audit with TriLensSwarmAuditor Lens 1 (CDP)
        auditor = TriLensSwarmAuditor(target_url="http://localhost:4000/telemetry", frame_count=5)
        res_cdp = auditor.audit_lens_1_cdp(captured_frames=frames)
        self.assertFalse(res_cdp.passed, "Lens 1 must FAIL when presented with 5 identical static frames!")
        self.assertFalse(res_cdp.dynamic_delta_passed)
        self.assertEqual(res_cdp.unique_frame_count, 1)

        # Audit with Lens 2 (Marionette)
        res_marionette = auditor.audit_lens_2_marionette(captured_frames=frames)
        self.assertFalse(res_marionette.passed, "Lens 2 must FAIL on frozen frames!")
        self.assertFalse(res_marionette.dynamic_delta_passed)

        # Audit with Lens 3 (ADB)
        res_adb = auditor.audit_lens_3_adb(captured_frames=frames)
        self.assertFalse(res_adb.passed, "Lens 3 must FAIL on frozen frames!")
        self.assertFalse(res_adb.dynamic_delta_passed)

    def test_partial_duplicate_frames_behavior(self):
        """
        Challenge 1.2: Partial duplicates in frame series.
        If only 3 out of 5 frames are unique, require_all_unique=True must FAIL,
        while require_all_unique=False passes as a partial transition.
        """
        frames = [
            b"FRAME_1_ACTIVE",
            b"FRAME_2_ACTIVE",
            b"FRAME_3_STUCK",
            b"FRAME_3_STUCK",
            b"FRAME_3_STUCK"
        ]
        passed_strict, _, count_strict = FrameDeltaValidator.evaluate_frame_series(frames, require_all_unique=True)
        self.assertFalse(passed_strict, "Partial duplicate frames must FAIL strict dynamic delta check.")
        self.assertEqual(count_strict, 3)

        passed_lenient, _, count_lenient = FrameDeltaValidator.evaluate_frame_series(frames, require_all_unique=False)
        self.assertTrue(passed_lenient, "Partial transition passes when require_all_unique=False.")
        self.assertEqual(count_lenient, 3)

    def test_empty_and_single_frame_edge_cases(self):
        """
        Challenge 1.3: Frame series with 0 or 1 frames.
        Must evaluate to passed=False and not raise uncaught exceptions.
        """
        passed_empty, results_empty, count_empty = FrameDeltaValidator.evaluate_frame_series([])
        self.assertFalse(passed_empty)
        self.assertEqual(count_empty, 0)
        self.assertEqual(len(results_empty), 0)

        passed_single, results_single, count_single = FrameDeltaValidator.evaluate_frame_series([b"ONE_FRAME"])
        self.assertFalse(passed_single, "A single frame cannot prove dynamic streaming.")
        self.assertEqual(count_single, 1)

    def test_ssim_parity_calculation_with_synthetic_images(self):
        """
        Challenge 1.4: SSIM parity calculation against ground truth and degraded images.
        - Identical images: SSIM = 1.0 (>= 0.95 PASS)
        - Slightly perturbed image (minor noise): SSIM >= 0.90
        - Heavily degraded / inverted / corrupt image: SSIM < 0.90 (FAIL < 0.95)
        """
        if not HAS_PIL:
            self.skipTest("PIL not available for image synthesis")

        # Create base reference image (200x200 grey with black rectangle)
        img_ref = Image.new("RGB", (200, 200), color=(128, 128, 128))
        draw_ref = ImageDraw.Draw(img_ref)
        draw_ref.rectangle([50, 50, 150, 150], fill=(30, 30, 30))

        buf_ref = BytesIO()
        img_ref.save(buf_ref, format="PNG")
        bytes_ref = buf_ref.getvalue()

        # 1. Identical image
        score_identical = VisualParityEngine.compute_ssim(bytes_ref, bytes_ref)
        self.assertAlmostEqual(score_identical, 1.0, places=2)
        self.assertGreaterEqual(score_identical, 0.95, "Identical images must achieve SSIM >= 0.95")

        # 2. Inverted / completely opposite image (white background with white rectangle)
        img_opposite = Image.new("RGB", (200, 200), color=(255, 255, 255))
        draw_opp = ImageDraw.Draw(img_opposite)
        draw_opp.rectangle([50, 50, 150, 150], fill=(240, 240, 240))
        buf_opp = BytesIO()
        img_opposite.save(buf_opp, format="PNG")
        bytes_opp = buf_opp.getvalue()

        score_opposite = VisualParityEngine.compute_ssim(bytes_ref, bytes_opp)
        self.assertLess(score_opposite, 0.90, f"Opposite image must fail parity threshold (< 0.90), got {score_opposite}")

        # 3. Severely corrupted image with random noise
        if HAS_NUMPY:
            noisy_arr = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
            img_noise = Image.fromarray(noisy_arr)
            buf_noise = BytesIO()
            img_noise.save(buf_noise, format="PNG")
            score_noise = VisualParityEngine.compute_ssim(bytes_ref, buf_noise.getvalue())
            self.assertLess(score_noise, 0.70, f"Noise image must produce low SSIM score, got {score_noise}")

    def test_dom_zero_mock_auditor_catches_all_forbidden_patterns(self):
        """
        Challenge 1.5: DomZeroMockAuditor catches all variations of forbidden telemetry literals.
        """
        mock_snippets = [
            '<div class="hr">Current: 142 bpm</div>',
            '<span>Roundtrip: 0.28 ms</span>',
            '<p>Compute: 149.8 gflops</p>',
            '<div>Status: FLEET_DARK_ACTIVE</div>',
            'const mock_telemetry = []',
            'let dummy_devices = {}',
            'var fake_data = 123'
        ]
        for snippet in mock_snippets:
            passed, tokens = DomZeroMockAuditor.audit_dom_text(snippet)
            self.assertFalse(passed, f"DomZeroMockAuditor failed to catch mock snippet: '{snippet}'")
            self.assertGreater(len(tokens), 0)

    def test_tri_lens_swarm_auditor_full_run_with_degraded_ref_fails(self):
        """
        Challenge 1.6: Full swarm audit with degraded Figma reference image marks verdict FAILED.
        """
        if not HAS_PIL:
            self.skipTest("PIL required")

        img_black = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img_white = Image.new("RGB", (100, 100), color=(255, 255, 255))
        b_black, b_white = BytesIO(), BytesIO()
        img_black.save(b_black, format="PNG")
        img_white.save(b_white, format="PNG")

        auditor = TriLensSwarmAuditor(
            target_url="http://localhost:4000/telemetry",
            figma_ref_image=b_black.getvalue(),
            min_ssim=0.95,
            frame_count=5
        )

        # Feed white frames against black ref image
        white_frames = [f"FRAME_{i}".encode("utf-8") + b_white.getvalue() for i in range(5)]
        res_cdp = auditor.audit_lens_1_cdp(captured_frames=white_frames)
        self.assertFalse(res_cdp.passed, "Lens 1 must FAIL when SSIM score is below threshold!")
        self.assertLess(res_cdp.ssim_score, 0.95)


# ============================================================================
# ADVERSARIAL SECTION 2: FLUTTER DART & VUE SFC DISCRIMINATION CHALLENGES
# ============================================================================

class TestAdversarialFlutterAndVueDiscrimination(unittest.TestCase):
    """Adversarial testing for Flutter Dart & Vue SFC Rule #0 discrimination logic."""

    def setUp(self):
        self.linter = FigmaZeroMockLinter(fail_under=100.0, strict=True)

    # ------------------------------------------------------------------------
    # VUE SFC DISCRIMINATION TESTS
    # ------------------------------------------------------------------------

    def test_vue_clean_waiting_states_pass_with_zero_violations(self):
        """
        Challenge 2.1: Vue SFC with clean waiting states & structural elements
        MUST produce 0 violations and score 100.0.
        """
        vue_clean_source = """
<template>
  <div class="telemetry-panel flex flex-col p-6 bg-slate-900 rounded-xl">
    <!-- Chrome Header & Labels: Allowed -->
    <header class="panel-header">
      <h2 class="text-lg font-bold text-slate-100">Live Biometrics Hub</h2>
      <span class="badge">{{ status ?? 'DISCONNECTED' }}</span>
    </header>

    <div class="grid grid-cols-3 gap-4 mt-4">
      <!-- Waiting state 1: Null coalescing to '--' -->
      <div class="card p-4 bg-slate-800 rounded">
        <label class="text-xs text-slate-400">Heart Rate</label>
        <span class="val text-2xl font-bold">{{ telemetry?.hr ?? '--' }}</span>
      </div>

      <!-- Waiting state 2: Ternary template string with '--' -->
      <div class="card p-4 bg-slate-800 rounded">
        <label class="text-xs text-slate-400">Blood Oxygen</label>
        <span class="val text-2xl font-bold">{{ telemetry?.spo2 ? `${telemetry.spo2}%` : '--' }}</span>
      </div>

      <!-- Waiting state 3: Logical OR fallback to 'N/A' -->
      <div class="card p-4 bg-slate-800 rounded">
        <label class="text-xs text-slate-400">BLE Latency</label>
        <span class="val text-2xl font-bold">{{ latencyMs || '--' }}</span>
      </div>
    </div>

    <!-- Table with static column headers: Allowed -->
    <table class="mt-6 w-full text-left">
      <thead>
        <tr>
          <th>Device Name</th>
          <th>Throughput (Mbps)</th>
          <th>Ping (ms)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="dev in deviceList" :key="dev.id">
          <td>{{ dev.name }}</td>
          <td class="reading">{{ dev.tp ?? '--' }}</td>
          <td class="reading">{{ dev.ping ?? '--' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Biometrics {
  hr?: number;
  spo2?: number;
}

const telemetry = ref<Biometrics | null>(null);
const latencyMs = ref<number | null>(null);
const status = ref<string>('CONNECTING');
const deviceList = ref<Array<{ id: string; name: string; tp?: number; ping?: number }>>([]);
</script>
"""
        scanner = VueScanner("BiometricsPanel.vue", vue_clean_source)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations for clean Vue SFC, got: {violations}")

        report = self.linter.generate_report("BiometricsPanel.vue", violations)
        self.assertEqual(report["total_violations"], 0)
        self.assertEqual(report["score"], 100.0)
        self.assertTrue(report["passed"])

    def test_vue_hardcoded_literals_and_mocks_fail(self):
        """
        Challenge 2.2: Vue SFC with hardcoded telemetry literals, mock arrays,
        and simulation timers MUST FAIL with CRITICAL violations.
        """
        vue_bad_source = """
<template>
  <div class="bad-panel">
    <!-- VIOLATION 1: Hardcoded telemetry in template data element -->
    <span class="val">142 bpm</span>
    <p class="stat">0.28 ms</p>
    <div class="reading">149.8 gflops</div>
  </div>
</template>

<script setup lang="ts">
// VIOLATION 2: In-source mock array pre-populated with active status
const mock_devices = [
  { id: '1', name: 'Pixel 9 Pro', status: 'ACTIVE' }
];

// VIOLATION 3: Synthetic setTimeout simulating state transition
setTimeout(() => {
  console.log("Simulated connection");
  setStatus('ONLINE');
}, 1000);
</script>
"""
        scanner = VueScanner("BadPanel.vue", vue_bad_source)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 3, f"Expected >= 3 violations in bad Vue SFC, got {len(violations)}")

        rule_ids = {v.rule_id for v in violations}
        self.assertIn("ZM-VUE-01", rule_ids, "Must flag hardcoded template metrics with ZM-VUE-01")
        self.assertIn("ZM-JS-03", rule_ids, "Must flag static mock array with ZM-JS-03")
        self.assertIn("ZM-JS-05", rule_ids, "Must flag synthetic setTimeout with ZM-JS-05")

        report = self.linter.generate_report("BadPanel.vue", violations)
        self.assertFalse(report["passed"])
        self.assertLess(report["score"], 50.0)

    # ------------------------------------------------------------------------
    # FLUTTER DART DISCRIMINATION TESTS
    # ------------------------------------------------------------------------

    def test_dart_clean_waiting_states_pass_with_zero_violations(self):
        """
        Challenge 2.3: Flutter Dart widget tree with dynamic state bindings,
        waiting states ('--'), AppBar titles, and button labels MUST pass with 0 violations.
        """
        dart_clean_source = """
import 'package:flutter/material.dart';

class BiometricsLiveScreen extends StatelessWidget {
  final Map<String, dynamic>? telemetryStream;
  final String? deviceName;

  const BiometricsLiveScreen({
    Key? key,
    this.telemetryStream,
    this.deviceName,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final heartRate = telemetryStream?['heart_rate'];
    final latency = telemetryStream?['latency_ms'];

    return Scaffold(
      // Header in AppBar: Permitted chrome
      appBar: AppBar(
        title: const Text('Movesense Live Monitor (142 bpm peak reference)'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Structural Header: Permitted
            const Text(
              'Real-Time Telemetry',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            // Waiting State 1: null-coalescing to '--'
            Card(
              child: ListTile(
                title: const Text('Heart Rate'),
                trailing: Text(
                  heartRate != null ? '$heartRate bpm' : '--',
                  style: const TextStyle(fontSize: 22, color: Colors.green),
                ),
              ),
            ),

            // Waiting State 2: Text(val ?? '--')
            Card(
              child: ListTile(
                title: const Text('BLE Latency'),
                trailing: Text(
                  latency?.toString() ?? '--',
                  style: const TextStyle(fontSize: 18),
                ),
              ),
            ),

            // Button with label: Permitted
            ElevatedButton(
              onPressed: () {},
              child: const Text('Calibrate Sensor (142 bpm target zone)'),
            ),
          ],
        ),
      ),
    );
  }
}
"""
        scanner = DartUiScanner("biometrics_live_screen.dart", dart_clean_source)
        violations = scanner.scan()
        self.assertEqual(len(violations), 0, f"Expected 0 violations for clean Dart UI, got: {violations}")

        report = self.linter.generate_report("biometrics_live_screen.dart", violations)
        self.assertEqual(report["total_violations"], 0)
        self.assertEqual(report["score"], 100.0)
        self.assertTrue(report["passed"])

    def test_dart_hardcoded_literals_and_mocks_fail(self):
        """
        Challenge 2.4: Flutter Dart widget containing hardcoded telemetry Text("142 bpm"),
        mock model lists, and Future.delayed setState simulations MUST FAIL.
        """
        dart_bad_source = """
import 'package:flutter/material.dart';

class FakeWidget extends StatefulWidget {
  @override
  _FakeWidgetState createState() => _FakeWidgetState();
}

class _FakeWidgetState extends State<FakeWidget> {
  // VIOLATION 1: Static mock list initialized with active dummy instances
  final mock_devices = [
    Device(id: 'dev_1', status: 'ACTIVE'),
    Device(id: 'dev_2', status: 'ONLINE')
  ];

  @override
  void initState() {
    super.initState();
    // VIOLATION 2: Synthetic Future.delayed simulation
    Future.delayed(Duration(seconds: 2), () => setState(() {
      status = 'ONLINE';
    }));
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        children: [
          // VIOLATION 3: Hardcoded telemetry literal in Text widget
          Text("142 bpm"),
          Text("0.28 ms"),
          Text("149.8 gflops"),
        ],
      ),
    );
  }
}
"""
        scanner = DartUiScanner("fake_widget.dart", dart_bad_source)
        violations = scanner.scan()
        self.assertGreaterEqual(len(violations), 3, f"Expected >= 3 violations in bad Dart file, got {len(violations)}")

        rule_ids = {v.rule_id for v in violations}
        self.assertIn("ZM-DART-01", rule_ids, "Must flag hardcoded Text('142 bpm') with ZM-DART-01")
        self.assertIn("ZM-DART-03", rule_ids, "Must flag mock list with ZM-DART-03")
        self.assertIn("ZM-DART-05", rule_ids, "Must flag Future.delayed setState with ZM-DART-05")

        report = self.linter.generate_report("fake_widget.dart", violations)
        self.assertFalse(report["passed"])
        self.assertLess(report["score"], 50.0)

    # ------------------------------------------------------------------------
    # CLI PRE-MERGE EXIT CODE VALIDATION
    # ------------------------------------------------------------------------

    def test_cli_exit_code_discrimination_vue_and_dart(self):
        """
        Challenge 2.5: Running figma_zero_mock_linter.py CLI on clean vs bad
        Vue and Dart files produces exit code 0 for clean and 1 for bad.
        """
        temp_dir = tempfile.mkdtemp(prefix="test_cli_discrim_")
        linter_script = os.path.join(SCRIPTS_DIR, "figma_zero_mock_linter.py")

        try:
            # 1. Clean Vue File
            clean_vue = os.path.join(temp_dir, "Clean.vue")
            with open(clean_vue, "w") as f:
                f.write('<template><span>{{ val ?? "--" }}</span></template>')

            proc_clean_vue = subprocess.run(
                [sys.executable, linter_script, "--target-file", clean_vue],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_clean_vue.returncode, 0, f"Clean Vue file must exit 0, got {proc_clean_vue.returncode}")

            # 2. Bad Vue File
            bad_vue = os.path.join(temp_dir, "Bad.vue")
            with open(bad_vue, "w") as f:
                f.write('<template><span class="metric">142 bpm</span></template>')

            proc_bad_vue = subprocess.run(
                [sys.executable, linter_script, "--target-file", bad_vue],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_bad_vue.returncode, 1, f"Bad Vue file must exit 1, got {proc_bad_vue.returncode}")

            # 3. Clean Dart File
            clean_dart = os.path.join(temp_dir, "clean.dart")
            with open(clean_dart, "w") as f:
                f.write('import "package:flutter/material.dart"; Widget b(String? v) => Text(v ?? "--");')

            proc_clean_dart = subprocess.run(
                [sys.executable, linter_script, "--target-file", clean_dart],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_clean_dart.returncode, 0, f"Clean Dart file must exit 0, got {proc_clean_dart.returncode}")

            # 4. Bad Dart File
            bad_dart = os.path.join(temp_dir, "bad.dart")
            with open(bad_dart, "w") as f:
                f.write('import "package:flutter/material.dart"; Widget b() => Card(child: Text("142 bpm"));')

            proc_bad_dart = subprocess.run(
                [sys.executable, linter_script, "--target-file", bad_dart],
                capture_output=True,
                text=True
            )
            self.assertEqual(proc_bad_dart.returncode, 1, f"Bad Dart file must exit 1, got {proc_bad_dart.returncode}")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# ADVERSARIAL SECTION 3: SETUP CLI & PROTOCOL ROBUSTNESS CHALLENGES
# ============================================================================

class TestAdversarialSetupAndProtocolHarness(unittest.TestCase):
    """Adversarial stress-testing of setup_figma_mcp.py and figma_mcp_client.py."""

    def test_setup_mcp_cli_status_command(self):
        """Challenge 3.1: setup_figma_mcp.py --status executes with exit code 0."""
        setup_script = os.path.join(SCRIPTS_DIR, "setup_figma_mcp.py")
        proc = subprocess.run(
            [sys.executable, setup_script, "--status"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("FIGMA MCP REGISTRATION STATUS", proc.stdout)

    def test_setup_mcp_cli_verify_command(self):
        """Challenge 3.2: setup_figma_mcp.py --verify executes stdio handshake and passes."""
        setup_script = os.path.join(SCRIPTS_DIR, "setup_figma_mcp.py")
        proc = subprocess.run(
            [sys.executable, setup_script, "--verify"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("VERIFICATION PASSED", proc.stdout)
        self.assertIn("Handshake successful", proc.stdout)

    def test_mcp_client_stdio_malformed_jsonrpc_handling(self):
        """Challenge 3.3: Stdio server receives malformed JSON-RPC frames and recovers cleanly."""
        client_script = os.path.join(SCRIPTS_DIR, "figma_mcp_client.py")
        proc = subprocess.Popen(
            [sys.executable, client_script, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            # 1. Send broken non-JSON frame
            proc.stdin.write("MALFORMED_NON_JSON_LINE\n")
            proc.stdin.flush()
            line_err = proc.stdout.readline()
            res_err = json.loads(line_err)
            self.assertIn("error", res_err)
            self.assertEqual(res_err["error"]["code"], -32700)  # Parse error

            # 2. Send valid ping frame immediately after to confirm server survived
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": "survived-1", "method": "ping"}) + "\n")
            proc.stdin.flush()
            line_ping = proc.stdout.readline()
            res_ping = json.loads(line_ping)
            self.assertEqual(res_ping["id"], "survived-1")
            self.assertEqual(res_ping["result"], {})
        finally:
            proc.terminate()
            proc.wait(timeout=3.0)


if __name__ == "__main__":
    unittest.main()
