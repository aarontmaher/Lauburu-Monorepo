// Empirical Adversarial Challenger 1 — Comprehensive Milestone 2 Stress Test Suite
// Rigorous verification of 512Hz Circular Ring Buffer, 3D Perspective Projection, and Zero-Mock Stability

import 'dart:io';
import 'dart:math' as math;
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';
import 'package:lauburu_port4000_flutter/src/state/hub_state_controller.dart';
import 'package:lauburu_port4000_flutter/src/ui/ecg_live_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/readiness_gauge.dart';
import 'package:lauburu_port4000_flutter/src/ui/spatial_tatami_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/video_filming_panel.dart';
import 'package:lauburu_port4000_flutter/src/ui/zone2_indicator.dart';

void main() {
  group('Adversarial Challenger 1: 512Hz Oscilloscope Circular Ring Buffer Stress', () {
    test('Ring Buffer Bounded Memory Invariant under 100,000 rapid sample bursts', () async {
      final controller = HubStateController();
      final receivedBuffers = <List<double>>[];
      
      final sub = controller.ecgBufferStream.listen((buf) {
        receivedBuffers.add(buf);
      });

      // Stream 100,000 raw samples at 512Hz burst rate
      for (int i = 0; i < 100000; i++) {
        final sample = (i % 512 == 0) ? 1.2 : (math.sin(i * 0.1) * 0.3);
        controller.ingestSample(sample, isConnected: true, deviceId: 'Movesense 512Hz Rig');
      }

      await Future<void>.delayed(const Duration(milliseconds: 20));

      // Buffer must never exceed maxDisplayPoints (300)
      expect(receivedBuffers.isNotEmpty, isTrue);
      for (final buf in receivedBuffers) {
        expect(buf.length, lessThanOrEqualTo(HubStateController.maxDisplayPoints));
      }
      expect(receivedBuffers.last.length, equals(HubStateController.maxDisplayPoints));

      sub.cancel();
      controller.dispose();
    });

    test('ECG Canvas Renderer handles degenerate, infinite, and NaN buffers gracefully', () {
      const renderer = EcgLiveCanvasRenderer(width: 500, height: 220);

      // 1. Zero and single sample buffers
      final emptySvg = renderer.renderSvgWaveform([]);
      expect(emptySvg, contains('WAITING FOR 512Hz SENSOR STREAM...'));

      final singleSvg = renderer.renderSvgWaveform([0.0]);
      expect(singleSvg, contains('WAITING FOR 512Hz SENSOR STREAM...'));

      // 2. All zeros flatline buffer (Rule #0 zero-mock standby)
      final flatline = List<double>.filled(512, 0.0);
      final flatlineSvg = renderer.renderSvgWaveform(flatline, heartRate: 0.0, isQrs: false);
      expect(flatlineSvg, contains('ECG 512Hz | -- BPM'));
      expect(flatlineSvg, contains('M 0.0 110.0')); // Center baseline (220 / 2 = 110.0)
      expect(flatlineSvg, contains('#00FFCC')); // Standby/nominal cyan

      // 3. Pathological extreme float inputs (+/-1e9, NaN, Subnormal)
      final pathological = [
        double.nan,
        double.infinity,
        double.negativeInfinity,
        1e12,
        -1e12,
        1e-30,
        -0.0,
        0.0,
      ];
      // Must not throw or crash
      final pathSvg = renderer.renderSvgWaveform(pathological, heartRate: 140.0, isQrs: true);
      expect(pathSvg, contains('ECG 512Hz | 140 BPM'));
      expect(pathSvg, contains('#FF0055')); // QRS active color
    });
  });

  group('Adversarial Challenger 1: 3D Perspective Projection & Spatial Kinematics Geometry', () {
    test('3D Tatami Canvas handles boundary and extreme torque states without overflow', () {
      const renderer = SpatialTatamiCanvasRenderer(width: 540, height: 320);

      // 1. Standby 0% mock state
      final standbySvg = renderer.renderSvgSpatialMap(
        heartRate: 0.0,
        rmssd: 0.0,
        alpha1: 0.0,
        submissionRisk: 0.0,
        currentTechnique: 'STANDBY — NO ATHLETE DETECTED',
      );
      expect(standbySvg, contains('HR: <tspan fill="#00FFCC" font-weight="bold">-- BPM</tspan>'));
      expect(standbySvg, contains('HRV: <tspan fill="#00FFCC">-- ms</tspan>'));
      expect(standbySvg, contains('α1: <tspan fill="#00FFCC">--</tspan>'));
      expect(standbySvg, contains('JOINT RISK: <tspan fill="#00FFCC" font-weight="900">-- (STANDBY)</tspan>'));
      expect(standbySvg, contains('STANDBY — NO ATHLETE DETECTED'));

      // 2. Nominal Torque State (0 < risk <= 30)
      final nominalSvg = renderer.renderSvgSpatialMap(
        heartRate: 135.0,
        rmssd: 55.0,
        alpha1: 0.85,
        submissionRisk: 22.0,
        currentTechnique: 'Guard Pass Setup',
      );
      expect(nominalSvg, contains('#00FFCC'));
      expect(nominalSvg, contains('22% (NOMINAL)'));
      expect(nominalSvg, contains('135 BPM'));

      // 3. Warning Torque State (30 < risk <= 60)
      final warningSvg = renderer.renderSvgSpatialMap(
        heartRate: 155.0,
        rmssd: 32.0,
        alpha1: 0.68,
        submissionRisk: 52.0,
        currentTechnique: 'Straight Ankle Lock Extension',
      );
      expect(warningSvg, contains('#FFD700'));
      expect(warningSvg, contains('52% (NOMINAL)'));

      // 4. Critical Torque State (risk > 60)
      final criticalSvg = renderer.renderSvgSpatialMap(
        heartRate: 182.0,
        rmssd: 14.5,
        alpha1: 0.45,
        submissionRisk: 94.0,
        currentTechnique: 'Inside Heel Hook Breaking Position',
      );
      expect(criticalSvg, contains('#FF0055'));
      expect(criticalSvg, contains('CRITICAL TORQUE'));
    });

    test('3D Perspective Projection Mathematical Invariant Oracle in Dart', () {
      // Direct simulation of the JavaScript project3D formula
      Map<String, double> project3D(double x, double y, double z, double cx, double cy, double orbitYaw, double orbitPitch) {
        final cosY = math.cos(orbitYaw);
        final sinY = math.sin(orbitYaw);
        final cosP = math.cos(orbitPitch);
        final sinP = math.sin(orbitPitch);

        final rx = x * cosY - z * sinY;
        final rz = x * sinY + z * cosY;
        final ry = y;

        const camDist = 5.5;
        final eyeZ = ry * sinP + (rz + camDist) * cosP;
        final eyeY = ry * cosP - (rz + camDist) * sinP;
        final eyeX = rx;

        const fov = 420.0;
        final scale = fov / (fov + eyeZ * 45.0);
        final screenX = cx + (eyeX * 60.0 * scale);
        final screenY = cy - (eyeY * 60.0 * scale);

        return {'x': screenX, 'y': screenY, 'z': eyeZ, 'scale': scale};
      }

      // Test across grid of pitch [0.1, 1.4] and yaw [0, 2*pi]
      for (double pitch = 0.1; pitch <= 1.4; pitch += 0.2) {
        for (double yaw = 0.0; yaw <= 2 * math.pi; yaw += 0.5) {
          // Test mat boundary corners (-4.5m to +4.5m)
          final corners = [
            [-4.5, 0.0, -4.5],
            [4.5, 0.0, -4.5],
            [4.5, 0.0, 4.5],
            [-4.5, 0.0, 4.5],
            [0.0, 1.8, 0.0], // Athlete head standing center
          ];

          for (final c in corners) {
            final res = project3D(c[0], c[1], c[2], 270.0, 160.0, yaw, pitch);
            expect(res['scale']!.isFinite, isTrue);
            expect(res['scale']!, greaterThan(0.0), reason: 'Scale must remain strictly positive in camera frustum');
            expect(res['x']!.isFinite, isTrue);
            expect(res['y']!.isFinite, isTrue);
          }
        }
      }
    });
  });

  group('Adversarial Challenger 1: Zero-Mock Rule #0 State Machine & Rapid Transitions', () {
    test('Rapid Disconnect / Reconnect Storms maintain 100% Zero-Mock integrity', () {
      final controller = HubStateController();

      for (int cycle = 0; cycle < 100; cycle++) {
        // 1. Ingest live frame
        final active = BiometricTelemetry(
          timestamp: DateTime.now().toUtc().toIso8601String(),
          deviceId: 'Movesense Stress Cycle $cycle',
          connected: true,
          sampleRateHz: 512.0,
          heartRateBpm: 120.0 + (cycle % 40),
          rrIntervalMs: 500.0,
          hrvRmssdMs: 40.0,
          hrvSdnnMs: 45.0,
          pnn50Percent: 18.0,
          dfaAlpha1: 0.80,
          readinessScore: 75.0,
          zone2Status: 'Zone 2: Optimal Aerobic (LT1)',
          ppgCalibrated: true,
          latestEcgSample: 0.5,
          qrsPeakDetected: false,
        );
        controller.ingestTelemetry(active);
        expect(controller.currentTelemetry.connected, isTrue);
        expect(controller.currentTelemetry.heartRateBpm, greaterThan(0.0));

        // 2. Abruptly disconnect
        final disconnected = BiometricTelemetry.initial();
        controller.ingestTelemetry(disconnected);
        expect(controller.currentTelemetry.connected, isFalse);
        expect(controller.currentTelemetry.heartRateBpm, equals(0.0));
        expect(controller.currentTelemetry.dfaAlpha1, equals(0.0));
        expect(controller.currentTelemetry.hrvRmssdMs, equals(0.0));
        expect(controller.currentTelemetry.readinessScore, equals(0.0));
        expect(controller.currentTelemetry.zone2Status, equals('Resting / Disconnected'));
      }

      controller.dispose();
    });

    test('Readiness Gauge, Zone 2 Indicator, and Video Panel handle zero-mock standby cleanly', () {
      // Readiness Gauge Standby
      const gauge = ReadinessGaugeRenderer(size: 180);
      final standbyGauge = gauge.renderSvgGauge(0.0, 0.0, 0.0);
      expect(standbyGauge, contains('-- %'));
      expect(standbyGauge, contains('STANDBY / DISCONNECTED'));
      expect(standbyGauge, contains('#64748B')); // Slate standby color
      expect(standbyGauge, isNot(contains('HIGH FATIGUE'))); // Must NOT flag fatigue on standby

      // Zone 2 Standby
      const zone2 = Zone2IndicatorRenderer(width: 320, height: 140);
      final standbyZone2 = zone2.renderSvgIndicator(0.0, 'Resting / Disconnected');
      expect(standbyZone2, contains('α1 = --'));
      expect(standbyZone2, contains('Resting / Disconnected'));

      // Video Filming Panel Standby
      const video = VideoFilmingPanelRenderer(width: 440, height: 320);
      final standbyVideo = video.renderSvgVideoPanel(
        isCameraActive: false,
        fps: 0.0,
        landmarksCount: 0,
        heartRate: 0.0,
      );
      expect(standbyVideo, contains('CAMERA STANDBY'));
      expect(standbyVideo, contains('0/33 Joints Tracked'));
      expect(standbyVideo, contains('💓 -- BPM | Movesense Standby'));
    });

    test('Forensic Source & HTML Zero-Mock Ban Rule #0 Verification', () {
      final htmlFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(htmlFile.existsSync(), isTrue);
      final html = htmlFile.readAsStringSync();

      // Rule #0 absolute bans
      final bannedTokens = [
        '72.0 BPM',
        '72 BPM',
        '48.5ms',
        '48.5 ms',
        'alpha1 = 1.0',
        'readiness = 50.0',
        '50% readiness',
        'Closed Guard → Ashi Garami', // Banned static fallback technique
      ];

      for (final banned in bannedTokens) {
        expect(html.contains(banned), isFalse, reason: 'Forbidden Rule #0 mock token found: $banned');
      }

      // Required zero-mock badges and placeholders
      expect(html, contains('0% MOCK DATA'));
      expect(html, contains('STANDBY — DISCONNECTED'));
      expect(html, contains('STANDBY — NO ATHLETE DETECTED'));
      expect(html, contains('STANDBY — SENSOR PROBING (0% MOCK DATA)'));
    });
  });
}
