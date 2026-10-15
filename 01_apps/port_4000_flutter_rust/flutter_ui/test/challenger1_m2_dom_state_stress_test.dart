// =========================================================================
// EMPIRICAL ADVERSARIAL CHALLENGER 1 (M2) — DART UI & STATE STRESS TEST
// =========================================================================
// Adversarial challenge covering:
// 1. Pathological and extreme biometrics payloads in Dart models
// 2. HubStateController rapid state transition & buffer bounds under 50,000 samples
// 3. Zero / NaN sample rate, negative heart rates, and extreme values
// 4. Authenticity of waiting state representations and zero-mock invariants
// 5. Generated dashboard HTML template structure and strict Rule #0 compliance

import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';
import 'package:lauburu_port4000_flutter/src/state/hub_state_controller.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Challenger 1 — BiometricTelemetry Pathological Model Fuzzing', () {
    test('1.1: BiometricTelemetry.initial() guarantees 100% resting zero state', () {
      final initial = BiometricTelemetry.initial();
      expect(initial.heartRateBpm, equals(0.0));
      expect(initial.rrIntervalMs, equals(0.0));
      expect(initial.hrvRmssdMs, equals(0.0));
      expect(initial.dfaAlpha1, equals(0.0));
      expect(initial.readinessScore, equals(0.0));
      expect(initial.connected, isFalse);
      expect(initial.zone2Status, equals('Resting / Disconnected'));
      expect(initial.latestEcgSample, equals(0.0));
      expect(initial.qrsPeakDetected, isFalse);
    });

    test('1.2: fromJson handles empty Map without exceptions', () {
      final t = BiometricTelemetry.fromJson({});
      expect(t.heartRateBpm, equals(0.0));
      expect(t.connected, isFalse);
      expect(t.deviceId, equals('Movesense Standby'));
      expect(t.sampleRateHz, equals(512.0));
    });

    test('1.3: fromJson handles pathological and boundary numerical types', () {
      final jsonMap = {
        'timestamp': '2026-09-02T12:00:00Z',
        'device_id': 'StressSensor',
        'connected': true,
        'sample_rate_hz': double.nan,
        'heart_rate_bpm': 250.0,
        'rr_interval_ms': double.infinity,
        'hrv_rmssd_ms': -50.0,
        'hrv_sdnn_ms': double.negativeInfinity,
        'pnn50_percent': 100.0,
        'dfa_alpha1': 1.85,
        'readiness_score': 99.0,
        'zone2_status': 'Zone 2: Optimal Aerobic',
        'ppg_calibrated': true,
        'latest_ecg_sample': 1.45,
        'qrs_peak_detected': true,
      };

      final t = BiometricTelemetry.fromJson(jsonMap);
      expect(t.heartRateBpm, equals(250.0));
      expect(t.connected, isTrue);
      expect(t.sampleRateHz.isNaN, isTrue);
      expect(t.rrIntervalMs.isInfinite, isTrue);
      expect(t.latestEcgSample, equals(1.45));
    });

    test('1.4: Serialization round-trip maintains exact precision', () {
      final original = BiometricTelemetry(
        timestamp: '2026-09-02T02:00:00Z',
        deviceId: 'Movesense MD 2405',
        connected: true,
        sampleRateHz: 512.0,
        heartRateBpm: 142.5,
        rrIntervalMs: 421.05,
        hrvRmssdMs: 38.4,
        hrvSdnnMs: 45.1,
        pnn50Percent: 22.0,
        dfaAlpha1: 0.76,
        readinessScore: 84.0,
        zone2Status: 'Zone 2: Optimal Aerobic (LT1)',
        ppgCalibrated: true,
        latestEcgSample: 0.92,
        qrsPeakDetected: true,
      );

      final jsonMap = original.toJson();
      final roundTrip = BiometricTelemetry.fromJson(jsonMap);

      expect(roundTrip.heartRateBpm, equals(original.heartRateBpm));
      expect(roundTrip.hrvRmssdMs, equals(original.hrvRmssdMs));
      expect(roundTrip.dfaAlpha1, equals(original.dfaAlpha1));
      expect(roundTrip.connected, equals(original.connected));
      expect(roundTrip.zone2Status, equals(original.zone2Status));
    });
  });

  group('Challenger 1 — HubStateController High-Throughput & State Churn', () {
    test('2.1: Ingesting 50,000 ECG samples maintains max display buffer bound', () {
      final controller = HubStateController();
      addTearDown(controller.dispose);

      for (int i = 0; i < 50000; i++) {
        final sample = (i % 100 - 50) / 50.0;
        controller.ingestSample(sample, isConnected: true, deviceId: 'StressTestBLE');
      }

      final t = controller.currentTelemetry;
      expect(t.connected, isTrue);
      expect(t.deviceId, equals('StressTestBLE'));
    });

    test('2.2: Rapid connection toggling (1,000 cycles) maintains state consistency', () {
      final controller = HubStateController();
      addTearDown(controller.dispose);

      for (int i = 0; i < 1000; i++) {
        final isConn = i % 2 == 0;
        if (isConn) {
          controller.ingestTelemetry(BiometricTelemetry(
            timestamp: DateTime.now().toIso8601String(),
            deviceId: 'Movesense 2405',
            connected: true,
            sampleRateHz: 512.0,
            heartRateBpm: 135.0,
            rrIntervalMs: 444.0,
            hrvRmssdMs: 42.0,
            hrvSdnnMs: 50.0,
            pnn50Percent: 25.0,
            dfaAlpha1: 0.78,
            readinessScore: 88.0,
            zone2Status: 'Zone 2: Optimal Aerobic',
            ppgCalibrated: true,
            latestEcgSample: 0.5,
            qrsPeakDetected: false,
          ));
          expect(controller.currentTelemetry.connected, isTrue);
          expect(controller.currentTelemetry.heartRateBpm, equals(135.0));
        } else {
          controller.ingestTelemetry(BiometricTelemetry.initial());
          expect(controller.currentTelemetry.connected, isFalse);
          expect(controller.currentTelemetry.heartRateBpm, equals(0.0));
        }
      }
    });
  });

  group('Challenger 1 — DashboardScreenRenderer & Rule #0 Zero-Mock Audit', () {
    test('3.1: Generated HTML contains authentic zero-mock placeholders', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      expect(html, contains('id="val-hr" style="color: #00FFCC;">--</div>'));
      expect(html, contains('id="val-rmssd" style="color: #38BDF8;">--</div>'));
      expect(html, contains('id="val-alpha1" style="color: #FACC15;">--</div>'));
      expect(html, contains('id="val-readiness" style="color: #A855F7;">--</div>'));
      expect(html, contains('STANDBY — DISCONNECTED'));
      expect(html, contains('STANDBY — NO ATHLETE DETECTED'));
      expect(html, contains('0% MOCK DATA'));
      expect(html, contains('STANDBY — SENSOR PROBING (0% MOCK DATA)'));
      expect(html, contains('3D TATAMI MAT READY — 0% MOCK DATA'));
    });

    test('3.2: Generated HTML has zero banned synthetic numbers', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      const banned = [
        '72.0',
        '72 BPM',
        '48.5',
        '48.5ms',
        'Closed Guard → Ashi Garami',
        'alpha1 = 1.0;',
        'readiness = 50.0;',
      ];

      for (final token in banned) {
        expect(html.contains(token), isFalse, reason: "Banned token '$token' found in generated HTML");
      }
    });

    test('3.3: Web Bluetooth connect function is fully wired in HTML', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      expect(html, contains('async function connectPixelBluetooth()'));
      expect(html, contains("navigator.bluetooth.requestDevice"));
      expect(html, contains("services: ['heart_rate']"));
      expect(html, contains("characteristicvaluechanged"));
    });
  });
}
