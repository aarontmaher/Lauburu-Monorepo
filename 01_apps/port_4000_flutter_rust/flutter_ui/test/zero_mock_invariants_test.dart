import 'dart:io';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';
import 'package:lauburu_port4000_flutter/src/bridge/native_bridge.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Zero-Mock Verification & Rule #0 Invariants', () {
    test('BiometricTelemetry.initial() contains 0% mock data', () {
      final initial = BiometricTelemetry.initial();
      expect(initial.connected, isFalse);
      expect(initial.heartRateBpm, 0.0);
      expect(initial.rrIntervalMs, 0.0);
      expect(initial.hrvRmssdMs, 0.0);
      expect(initial.hrvSdnnMs, 0.0);
      expect(initial.pnn50Percent, 0.0);
      expect(initial.dfaAlpha1, 0.0);
      expect(initial.readinessScore, 0.0);
      expect(initial.latestEcgSample, 0.0);
      expect(initial.qrsPeakDetected, isFalse);
      expect(initial.ppgCalibrated, isFalse);
    });

    test('BiometricTelemetry.fromJson with empty map has no mock fallbacks', () {
      final empty = BiometricTelemetry.fromJson({});
      expect(empty.connected, isFalse);
      expect(empty.heartRateBpm, 0.0);
      expect(empty.dfaAlpha1, 0.0);
      expect(empty.readinessScore, 0.0);
      expect(empty.hrvRmssdMs, 0.0);
      expect(empty.zone2Status, 'Resting / Disconnected');
    });

    test('LauburuNativeBridge pure Dart fallback contains no mock constants', () {
      final bridge = LauburuNativeBridge();
      final sampleOut = bridge.processSample(0.0);
      expect(sampleOut['heart_rate_bpm'], 0.0);
      expect(sampleOut['rr_interval_ms'], 0.0);
      expect(sampleOut['rmssd_ms'], 0.0);
      expect(sampleOut['is_qrs_peak'], isFalse);

      if (!bridge.isFfiLoaded) {
        expect(bridge.getReadinessScore(), 0.0);
        expect(bridge.getHrvRmssd(), 0.0);
        expect(bridge.getDfaAlpha1(), 0.0);
      }
    });

    test('DashboardScreenRenderer generates clean HTML with zero mock tokens', () {
      final renderer = const DashboardScreenRenderer(width: 1100, height: 850);
      final html = renderer.renderDynamicDashboardHtml();

      // Verify no mock numbers exist
      expect(html.contains('72.0'), isFalse, reason: 'Contains hardcoded 72.0 BPM');
      expect(html.contains('48.5'), isFalse, reason: 'Contains hardcoded 48.5 ms RMSSD');
      expect(html.contains('alpha1 = 1.0;'), isFalse, reason: 'Contains hardcoded alpha1 = 1.0');
      expect(html.contains('readiness = 50.0;'), isFalse, reason: 'Contains hardcoded readiness = 50.0');
      expect(html.contains('Closed Guard → Ashi Garami'), isFalse, reason: 'Contains hardcoded technique');

      // Verify authentic waiting state elements exist
      expect(html.contains('id="val-hr" style="color: #00FFCC;">--</div>'), isTrue);
      expect(html.contains('id="val-rmssd" style="color: #38BDF8;">--</div>'), isTrue);
      expect(html.contains('id="val-alpha1" style="color: #FACC15;">--</div>'), isTrue);
      expect(html.contains('id="val-readiness" style="color: #A855F7;">--</div>'), isTrue);
      expect(html.contains('STANDBY — DISCONNECTED'), isTrue);
      expect(html.contains('0% MOCK DATA'), isTrue);
      expect(html.contains('3D TATAMI MAT READY — 0% MOCK DATA'), isTrue);
      expect(html.contains('connectPixelBluetooth()'), isTrue);
      expect(html.contains('/ws/telemetry'), isTrue);
      expect(html.contains('/ws/spatial'), isTrue);
    });

    test('Compiled build/index.html is synchronized and passes Truth Audit', () {
      final file = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      if (file.existsSync()) {
        final content = file.readAsStringSync();
        expect(content.contains('72.0'), isFalse);
        expect(content.contains('48.5'), isFalse);
        expect(content.contains('alpha1 = 1.0;'), isFalse);
        expect(content.contains('readiness = 50.0;'), isFalse);
        expect(content.contains('Closed Guard → Ashi Garami'), isFalse);
        expect(content.contains('id="val-hr" style="color: #00FFCC;">--</div>'), isTrue);
        expect(content.contains('0% MOCK DATA'), isTrue);
      }
    });
  });
}
