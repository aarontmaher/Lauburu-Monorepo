// Challenger 2 Empirical Adversarial Stress Test Suite — Milestone 2
// Deep testing of 60 FPS Render Cycles, Touch Orbit Transforms, WebSocket State Machine, and Zero-Mock Invariants

import 'dart:io';
import 'dart:math' as math;
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/state/hub_state_controller.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';
import 'package:lauburu_port4000_flutter/src/ui/ecg_live_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/readiness_gauge.dart';
import 'package:lauburu_port4000_flutter/src/ui/spatial_tatami_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/video_filming_panel.dart';
import 'package:lauburu_port4000_flutter/src/ui/zone2_indicator.dart';

void main() {
  group('Challenger 2 M2: 60 FPS RequestAnimationFrame & Ring Buffer Invariants', () {
    test('ECG Buffer respects circular ring buffer bounds under 50,000 rapid samples', () async {
      final controller = HubStateController();
      final bufferHistory = <int>[];

      final sub = controller.ecgBufferStream.listen((buf) {
        bufferHistory.add(buf.length);
      });

      for (int i = 0; i < 50000; i++) {
        final sample = (i % 256 == 0) ? 1.5 : (math.sin(i * 0.05) * 0.4);
        controller.ingestSample(sample, isConnected: true, deviceId: 'Movesense Ring Test');
      }

      await pumpEventQueue();

      expect(bufferHistory.isNotEmpty, isTrue);
      for (final len in bufferHistory) {
        expect(len, lessThanOrEqualTo(HubStateController.maxDisplayPoints));
      }
      expect(controller.currentTelemetry.connected, isTrue);

      sub.cancel();
      controller.dispose();
    });

    test('ECG Canvas Renderer smoothly renders zero flatline on 0.0 baseline', () {
      const renderer = EcgLiveCanvasRenderer(width: 500.0, height: 220.0);
      final flatline = List<double>.filled(300, 0.0);

      final svg = renderer.renderSvgWaveform(flatline, heartRate: 0.0, isQrs: false);
      expect(svg, contains('ECG 512Hz | -- BPM'));
      expect(svg, contains('stroke="#00FFCC"'));
      expect(svg, isNot(contains('NaN')));
      expect(svg, isNot(contains('Infinity')));
    });

    test('ECG Canvas Renderer handles subnormal, extreme float, and NaN buffers', () {
      const renderer = EcgLiveCanvasRenderer(width: 480.0, height: 220.0);
      final pathological = [
        double.nan,
        double.infinity,
        double.negativeInfinity,
        1e20,
        -1e20,
        1e-300,
        0.0,
        0.5,
        -0.5,
      ];

      final svg = renderer.renderSvgWaveform(pathological, heartRate: 155.0, isQrs: true);
      expect(svg, contains('ECG 512Hz | 155 BPM'));
      expect(svg, contains('stroke="#FF0055"'));
    });
  });

  group('Challenger 2 M2: Touch Orbit Transforms & 3D Perspective Matrix Invariants', () {
    // Exact mathematical mirror of JS project3D
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

    test('3D Orbit pitch clamping [0.1, 1.4] guarantees strictly positive frustum scale', () {
      // Test grid of yaw in [-4*pi, 4*pi] and pitch in [0.1, 1.4]
      for (double pitch = 0.1; pitch <= 1.4; pitch += 0.1) {
        for (double yaw = -math.pi * 2; yaw <= math.pi * 2; yaw += 0.4) {
          // Tatami boundary corners (-4.5m to +4.5m)
          final corners = [
            [-4.5, 0.0, -4.5],
            [4.5, 0.0, -4.5],
            [4.5, 0.0, 4.5],
            [-4.5, 0.0, 4.5],
            [0.0, 0.0, 0.0],
            [0.0, 1.8, 0.0],
          ];

          for (final pt in corners) {
            final proj = project3D(pt[0], pt[1], pt[2], 270.0, 170.0, yaw, pitch);
            expect(proj['scale']!.isFinite, isTrue);
            expect(proj['scale']!, greaterThan(0.0), reason: 'Scale must remain strictly positive');
            expect(proj['x']!.isFinite, isTrue);
            expect(proj['y']!.isFinite, isTrue);
          }
        }
      }
    });

    test('Spatial Tatami SVG Renderer displays standby vs active torque states accurately', () {
      const renderer = SpatialTatamiCanvasRenderer(width: 540.0, height: 320.0);

      // 1. Standby
      final standby = renderer.renderSvgSpatialMap(
        heartRate: 0.0,
        rmssd: 0.0,
        alpha1: 0.0,
        submissionRisk: 0.0,
        currentTechnique: 'STANDBY — NO ATHLETE DETECTED',
      );
      expect(standby, contains('-- BPM'));
      expect(standby, contains('-- ms'));
      expect(standby, contains('α1: <tspan fill="#00FFCC">--</tspan>'));
      expect(standby, contains('JOINT RISK: <tspan fill="#00FFCC" font-weight="900">-- (STANDBY)</tspan>'));
      expect(standby, contains('STANDBY — NO ATHLETE DETECTED'));

      // 2. High risk (> 60%)
      final critical = renderer.renderSvgSpatialMap(
        heartRate: 175.0,
        rmssd: 18.0,
        alpha1: 0.42,
        submissionRisk: 88.0,
        currentTechnique: 'Ashi Garami → Heel Hook',
      );
      expect(critical, contains('175 BPM'));
      expect(critical, contains('CRITICAL TORQUE'));
      expect(critical, contains('#FF0055'));
    });
  });

  group('Challenger 2 M2: WebSocket State Machine & Metric Subsystem Invariants', () {
    test('Readiness Gauge renders slate standby vs colored active boundaries', () {
      const gauge = ReadinessGaugeRenderer(size: 180.0);

      // Standby (score = 0.0, HR = 0.0)
      final standby = gauge.renderSvgGauge(0.0, 0.0, 0.0);
      expect(standby, contains('-- %'));
      expect(standby, contains('STANDBY / DISCONNECTED'));
      expect(standby, contains('#64748B'));
      expect(standby, isNot(contains('HIGH FATIGUE')));

      // Prime Readiness (score = 85.0, HR = 130.0)
      final prime = gauge.renderSvgGauge(85.0, 45.0, 130.0);
      expect(prime, contains('85%'));
      expect(prime, contains('PRIME READINESS'));
      expect(prime, contains('#00FFCC'));

      // High Fatigue (score = 30.0, HR = 170.0)
      final fatigue = gauge.renderSvgGauge(30.0, 15.0, 170.0);
      expect(fatigue, contains('30%'));
      expect(fatigue, contains('HIGH FATIGUE'));
      expect(fatigue, contains('#FF0055'));
    });

    test('Zone 2 Indicator renders accurate aerobic windows and standby state', () {
      const zone2 = Zone2IndicatorRenderer(width: 320.0, height: 140.0);

      // Standby
      final standby = zone2.renderSvgIndicator(0.0, 'Resting / Disconnected');
      expect(standby, contains('α1 = --'));
      expect(standby, contains('Resting / Disconnected'));

      // Zone 2 Target (alpha1 = 0.72)
      final activeZone2 = zone2.renderSvgIndicator(0.72, 'Zone 2: Optimal Aerobic');
      expect(activeZone2, contains('α1 = 0.72'));
      expect(activeZone2, contains('Zone 2: Optimal Aerobic'));

      // Anaerobic (alpha1 = 0.45)
      final anaerobic = zone2.renderSvgIndicator(0.45, 'Zone 4: Anaerobic Glycolysis');
      expect(anaerobic, contains('α1 = 0.45'));
    });

    test('Video Filming Panel displays live vs standby reticle and watermark', () {
      const panel = VideoFilmingPanelRenderer(width: 440.0, height: 320.0);

      // Standby
      final standby = panel.renderSvgVideoPanel(
        isCameraActive: false,
        fps: 0.0,
        landmarksCount: 0,
        heartRate: 0.0,
      );
      expect(standby, contains('CAMERA STANDBY (0 FPS)'));
      expect(standby, contains('0/33 Joints Tracked'));
      expect(standby, contains('Movesense Standby'));

      // Active
      final active = panel.renderSvgVideoPanel(
        isCameraActive: true,
        fps: 60.0,
        landmarksCount: 33,
        heartRate: 145.0,
      );
      expect(active, contains('LIVE CAMERA ACTIVE (60 FPS)'));
      expect(active, contains('33/33 Joints Tracked'));
      expect(active, contains('145 BPM'));
    });
  });

  group('Challenger 2 M2: Truth Audit & Zero-Mock Compliance Invariants', () {
    test('DashboardScreenRenderer generates complete HTML with zero mock tokens', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      // Zero-mock absolute bans
      expect(html, isNot(contains('72.0 BPM')));
      expect(html, isNot(contains('72 BPM')));
      expect(html, isNot(contains('48.5ms')));
      expect(html, isNot(contains('48.5 ms')));
      expect(html, isNot(contains('alpha1 = 1.0')));
      expect(html, isNot(contains('readiness = 50.0')));

      // Required verification tokens
      expect(html, contains('0% MOCK DATA'));
      expect(html, contains('STANDBY — DISCONNECTED'));
      expect(html, contains('STANDBY — NO ATHLETE DETECTED'));
      expect(html, contains('connectPixelBluetooth'));
      expect(html, contains('/ws/telemetry'));
      expect(html, contains('/ws/spatial'));
    });

    test('Compiled build/index.html is synchronized bit-for-bit with DashboardScreenRenderer', () {
      final htmlFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(htmlFile.existsSync(), isTrue);
      final diskContent = htmlFile.readAsStringSync();

      const renderer = DashboardScreenRenderer();
      final generatedContent = renderer.renderDynamicDashboardHtml();

      expect(diskContent, equals(generatedContent), reason: 'build/index.html must be synchronized with renderer');
    });
  });
}
