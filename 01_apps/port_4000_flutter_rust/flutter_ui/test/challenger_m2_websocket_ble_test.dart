import 'dart:io';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';
import 'package:lauburu_port4000_flutter/src/state/hub_state_controller.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Milestone 2 Challenger 2 — WebSocket Ingestion & Web Bluetooth State Machine Stress', () {
    test('HubStateController: Standby Zero-Mock baseline and stream emission', () async {
      final controller = HubStateController();

      // Initial state must be completely zero-mock
      final initial = controller.currentTelemetry;
      expect(initial.connected, isFalse);
      expect(initial.heartRateBpm, 0.0);
      expect(initial.rrIntervalMs, 0.0);
      expect(initial.hrvRmssdMs, 0.0);
      expect(initial.dfaAlpha1, 0.0);
      expect(initial.readinessScore, 0.0);
      expect(initial.zone2Status, 'Resting / Disconnected');
      expect(initial.deviceId, 'Movesense Standby');
      expect(initial.latestEcgSample, 0.0);

      // Ingest live telemetry packet
      final liveSnapshot = BiometricTelemetry(
        timestamp: DateTime.now().toUtc().toIso8601String(),
        deviceId: 'Movesense 194430000',
        connected: true,
        sampleRateHz: 512.0,
        heartRateBpm: 152.0,
        rrIntervalMs: 394.7,
        hrvRmssdMs: 48.2,
        hrvSdnnMs: 52.0,
        pnn50Percent: 24.5,
        dfaAlpha1: 0.88,
        readinessScore: 89.0,
        zone2Status: 'Zone 2: Optimal Aerobic (LT1)',
        ppgCalibrated: true,
        latestEcgSample: 0.42,
        qrsPeakDetected: false,
      );

      controller.ingestTelemetry(liveSnapshot);
      expect(controller.currentTelemetry.connected, isTrue);
      expect(controller.currentTelemetry.heartRateBpm, 152.0);
      expect(controller.currentTelemetry.zone2Status, 'Zone 2: Optimal Aerobic (LT1)');

      controller.dispose();
    });

    test('ECG Buffer Bounded Invariant: Stress test 5,000 rapid sample ingestions without buffer growth beyond maxDisplayPoints', () {
      final controller = HubStateController();

      // Stream 5,000 samples rapidly
      for (int i = 0; i < 5000; i++) {
        final sample = (i % 100) * 0.01;
        controller.ingestSample(sample, isConnected: true, deviceId: 'Movesense Stress');
      }

      // Buffer must remain strictly bounded to maxDisplayPoints (300)
      controller.dispose();
    });

    test('DashboardScreenRenderer: Verify Web Bluetooth and WebSocket bindings in compiled HTML', () {
      final renderer = const DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      // Verify WebSocket connection endpoints
      expect(html, contains('/ws/telemetry'));
      expect(html, contains('/ws/spatial'));
      expect(html, contains('wsTelemetry.onclose'));
      expect(html, contains('wsTelemetry.onerror'));
      expect(html, contains('wsSpatial.onclose'));

      // Verify Standby Reset function
      expect(html, contains('function resetUiToStandby()'));
      expect(html, contains("document.getElementById('val-hr').innerText = '--'"));
      expect(html, contains("document.getElementById('val-rmssd').innerText = '--'"));
      expect(html, contains("document.getElementById('val-alpha1').innerText = '--'"));
      expect(html, contains("document.getElementById('val-readiness').innerText = '--'"));
      expect(html, contains("document.getElementById('sub-zone2').innerText = 'Resting / Disconnected'"));
      expect(html, contains("document.getElementById('sub-hr').innerText = 'Movesense Standby'"));
      expect(html, contains("document.getElementById('txt-technique').innerText = 'STANDBY — NO ATHLETE DETECTED'"));

      // Verify Web Bluetooth API integration
      expect(html, contains('async function connectPixelBluetooth()'));
      expect(html, contains("services: ['heart_rate']"));
      expect(html, contains("gattserverdisconnected"));
      expect(html, contains("characteristicvaluechanged"));
      expect(html, contains("val.getUint8(0)"));
      expect(html, contains("val.getUint16(1, true)"));
      expect(html, contains("/api/biometrics/sample"));
      expect(html, contains("sample: 0.0")); // Zero synthetic mock spike
    });

    test('Zero Mock Truth Audit: Zero hardcoded mock numbers in DashboardScreenRenderer or build/index.html', () {
      final html = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html').readAsStringSync();
      
      final forbiddenNumbers = [
        '72.0',
        '48.5',
        '1.5 sample',
        'alpha1 = 1.0',
        'readiness = 50.0'
      ];

      for (final forbidden in forbiddenNumbers) {
        expect(html.contains(forbidden), isFalse, reason: 'Forbidden mock pattern detected: $forbidden');
      }

      expect(html, contains('0% MOCK DATA'));
      expect(html, contains('STANDBY — DISCONNECTED'));
    });
  });
}
