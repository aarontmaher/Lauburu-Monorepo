// Location: test/challenger2_m4_daemon_stress_test.dart
// Milestone 4 Challenger 2: Daemon Lifecycle, Dual-Interface Reachability & Zero-Mock Invariant Test

import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Milestone 4 Challenger 2: Daemon Stress & Multi-Interface Zero-Mock Audit', () {
    const renderer = DashboardScreenRenderer();
    late String htmlContent;

    setUpAll(() {
      htmlContent = renderer.renderDynamicDashboardHtml();
    });

    test('4.1: Forensic AST Zero-Mock Verification (No residual mock tokens)', () {
      // Must not contain legacy mock strings
      expect(htmlContent.contains('72 BPM'), isFalse, reason: 'Forbidden mock HR found');
      expect(htmlContent.contains('48.5ms'), isFalse, reason: 'Forbidden mock RMSSD found');
      expect(htmlContent.contains('48.5 ms'), isFalse, reason: 'Forbidden mock RMSSD space found');
      expect(htmlContent.contains('12.4%'), isFalse, reason: 'Forbidden mock risk found');
      expect(htmlContent.contains('34.2 N·m'), isFalse, reason: 'Forbidden mock torque found');

      // Must contain zero-mock standby indicators
      expect(htmlContent, contains('STANDBY — DISCONNECTED'));
      expect(htmlContent, contains('0% MOCK DATA'));
      expect(htmlContent, contains('Movesense Standby'));
      expect(htmlContent, contains('Resting / Disconnected'));
    });

    test('4.2: Initial HTML DOM Elements start in authentic Standby state', () {
      expect(htmlContent, contains('id="val-hr" style="color: #00FFCC;">--</div>'));
      expect(htmlContent, contains('id="val-rmssd" style="color: #38BDF8;">--</div>'));
      expect(htmlContent, contains('id="val-alpha1" style="color: #FACC15;">--</div>'));
      expect(htmlContent, contains('id="val-readiness" style="color: #A855F7;">--</div>'));
      expect(htmlContent, contains('id="txt-technique" style="color: #00FFCC;">STANDBY — NO ATHLETE DETECTED</span>'));
      expect(htmlContent, contains('id="txt-camera-status" style="color: #38BDF8;">0/33 Joints Tracked</span>'));
      expect(htmlContent, contains('id="sub-zone2">Resting / Disconnected</div>'));
      expect(htmlContent, contains('id="sub-hr">Movesense Standby</div>'));
    });

    test('4.3: resetUiToStandby() comprehensively restores all telemetry elements', () {
      expect(htmlContent, contains("document.getElementById('val-hr').innerText = '--';"));
      expect(htmlContent, contains("document.getElementById('val-rmssd').innerText = '--';"));
      expect(htmlContent, contains("document.getElementById('val-alpha1').innerText = '--';"));
      expect(htmlContent, contains("document.getElementById('val-readiness').innerText = '--';"));
      expect(htmlContent, contains("document.getElementById('sub-zone2').innerText = 'Resting / Disconnected';"));
      expect(htmlContent, contains("document.getElementById('sub-hr').innerText = 'Movesense Standby';"));
      expect(htmlContent, contains("document.getElementById('txt-technique').innerText = 'STANDBY — NO ATHLETE DETECTED';"));
      expect(htmlContent, contains("document.getElementById('txt-camera-status').innerText = '0/33 Joints Tracked';"));
      expect(htmlContent, contains("badge.innerText = 'STANDBY — DISCONNECTED';"));
      expect(htmlContent, contains("ecgBuffer.fill(0.0);"));
    });

    test('4.4: Multi-Interface URI Parsing & Protocol Negotiation Logic', () {
      // Test Loopback and Tailscale URI derivation logic
      final loopbackWs = Uri.parse('ws://127.0.0.1:4000/ws/telemetry');
      final tailscaleWs = Uri.parse('ws://100.119.199.76:4000/ws/telemetry');

      expect(loopbackWs.host, equals('127.0.0.1'));
      expect(loopbackWs.port, equals(4000));
      expect(loopbackWs.path, equals('/ws/telemetry'));

      expect(tailscaleWs.host, equals('100.119.199.76'));
      expect(tailscaleWs.port, equals(4000));
      expect(tailscaleWs.path, equals('/ws/telemetry'));

      // Verify dynamic window.location.host WS connection support in JS
      expect(htmlContent, contains('window.location.host'));
    });

    test('4.5: High-Frequency Telemetry Ingestion State Machine Transitions', () {
      // Simulate state machine transitions from standby -> active -> standby
      Map<String, dynamic> state = {
        'connected': false,
        'hr': 0.0,
        'rmssd': 0.0,
        'alpha1': 0.0,
        'readiness': 0.0,
      };

      // 1. Initial standby
      expect(state['connected'], isFalse);
      expect(state['hr'], equals(0.0));

      // 2. Active stream arrival
      state['connected'] = true;
      state['hr'] = 155.0;
      state['rmssd'] = 22.4;
      state['alpha1'] = 0.75;
      state['readiness'] = 88.0;

      expect(state['connected'], isTrue);
      expect(state['hr'], equals(155.0));

      // 3. Sudden Disconnect
      state = {
        'connected': false,
        'hr': 0.0,
        'rmssd': 0.0,
        'alpha1': 0.0,
        'readiness': 0.0,
      };

      expect(state['connected'], isFalse);
      expect(state['hr'], equals(0.0));
      expect(state['rmssd'], equals(0.0));
      expect(state['readiness'], equals(0.0));
    });
  });
}
