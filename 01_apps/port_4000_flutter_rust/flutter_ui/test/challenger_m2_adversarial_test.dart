import 'dart:io';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';
import 'package:lauburu_port4000_flutter/src/ui/ecg_live_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/spatial_tatami_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/readiness_gauge.dart';
import 'package:lauburu_port4000_flutter/src/ui/zone2_indicator.dart';
import 'package:lauburu_port4000_flutter/src/ui/video_filming_panel.dart';

void main() {
  group('Adversarial Challenger M2 — Frontend Zero-Mock DOM & Canvas Stress', () {
    test('Initial DOM Invariants: Strict verification of authentic waiting states and zero mock data', () {
      const renderer = DashboardScreenRenderer(width: 1100, height: 850);
      final html = renderer.renderDynamicDashboardHtml();

      // 1. Initial DOM Element States
      expect(html, contains('id="val-hr" style="color: #00FFCC;">--</div>'),
          reason: 'Heart rate initial state must be --');
      expect(html, contains('id="val-rmssd" style="color: #38BDF8;">--</div>'),
          reason: 'HRV RMSSD initial state must be --');
      expect(html, contains('id="val-alpha1" style="color: #FACC15;">--</div>'),
          reason: 'DFA-alpha1 initial state must be --');
      expect(html, contains('id="val-readiness" style="color: #A855F7;">--</div>'),
          reason: 'Readiness initial state must be --');
      expect(html, contains('STANDBY — DISCONNECTED'),
          reason: 'Status badge must display STANDBY — DISCONNECTED');
      expect(html, contains('STANDBY — NO ATHLETE DETECTED'),
          reason: 'Technique banner must display STANDBY — NO ATHLETE DETECTED');
      expect(html, contains('Resting / Disconnected'),
          reason: 'Zone 2 sub-label must display Resting / Disconnected');
      expect(html, contains('Movesense Standby'),
          reason: 'Device sub-label must display Movesense Standby');
      expect(html, contains('0% MOCK DATA'),
          reason: '0% MOCK DATA badge must be present');
      expect(html, contains('3D TATAMI MAT READY — 0% MOCK DATA'),
          reason: '3D Tatami canvas must indicate 0% mock standby');
      expect(html, contains('STANDBY — SENSOR PROBING (0% MOCK DATA)'),
          reason: 'ECG oscilloscope must indicate 0% mock standby');

      // 2. Zero-Mock Banned Tokens
      final bannedTokens = [
        '72.0',
        '72 BPM',
        '48.5',
        '48.5ms',
        'alpha1 = 1.0',
        'readiness = 50.0',
        'Closed Guard → Ashi Garami',
        'Math.sin(Date.now()',
        'Math.sin(i / 10)',
      ];

      for (final token in bannedTokens) {
        expect(html.contains(token), isFalse, reason: 'Banned mock token detected: $token');
      }
    });

    test('ECG Canvas Renderer Stress: Pathological and extreme float inputs stay bounded', () {
      const renderer = EcgLiveCanvasRenderer(width: 480, height: 200);

      // Empty & single sample buffers
      expect(renderer.renderSvgWaveform([]), contains('WAITING FOR 512Hz SENSOR STREAM...'));
      expect(renderer.renderSvgWaveform([0.5]), contains('WAITING FOR 512Hz SENSOR STREAM...'));

      // Flatline zeros buffer (300 samples)
      final zeros = List<double>.filled(300, 0.0);
      final flatlineSvg = renderer.renderSvgWaveform(zeros, heartRate: 0.0);
      expect(flatlineSvg, contains('ECG 512Hz | -- BPM'));
      expect(flatlineSvg, contains('M 0.0 100.0')); // Center baseline at height 200 / 2 = 100.0

      // Extreme float spikes (checking clamping logic [4.0, height - 4.0])
      final extremeBuffer = [1000.0, -1000.0, 5000.0, -5000.0, 0.0];
      final extremeSvg = renderer.renderSvgWaveform(extremeBuffer, heartRate: 150.0, isQrs: true);
      expect(extremeSvg, contains('ECG 512Hz | 150 BPM'));
      expect(extremeSvg, contains('#FF0055')); // QRS active glow
      expect(extremeSvg, contains('M 0.0 4.0')); // Clamped to upper bound
      expect(extremeSvg, contains('L 120.0 196.0')); // Clamped to lower bound (200 - 4 = 196)

      // High-density 2,000-sample buffer stress
      final denseBuffer = List<double>.generate(2000, (i) => (i % 2 == 0 ? 0.2 : -0.2));
      final denseSvg = renderer.renderSvgWaveform(denseBuffer, heartRate: 120.0);
      expect(denseSvg, contains('ECG 512Hz | 120 BPM'));
      expect(denseSvg, contains('width="480.0" height="200.0"'));
    });

    test('3D Tatami Kinematics Stress: Extreme coordinate scaling and risk thresholds', () {
      const renderer = SpatialTatamiCanvasRenderer(width: 540, height: 320);

      // Resting zero state
      final resting = renderer.renderSvgSpatialMap(
        heartRate: 0.0,
        rmssd: 0.0,
        alpha1: 0.0,
        submissionRisk: 0.0,
        currentTechnique: 'Standby / Mat Empty',
      );
      expect(resting, contains('🥋 3D TATAMI: <tspan fill="#FFFFFF">Standby / Mat Empty</tspan>'));
      expect(resting, contains('HR: <tspan fill="#00FFCC" font-weight="bold">-- BPM</tspan>'));
      expect(resting, contains('JOINT RISK: <tspan fill="#00FFCC" font-weight="900">-- (STANDBY)</tspan>'));

      // Warning torque threshold (30% - 60%)
      final warning = renderer.renderSvgSpatialMap(
        heartRate: 130.0,
        rmssd: 45.0,
        alpha1: 0.82,
        submissionRisk: 45.0,
        currentTechnique: 'Kimura Setup',
      );
      expect(warning, contains('#FFD700')); // Warning gold color
      expect(warning, contains('45% (NOMINAL)'));

      // Critical torque threshold (>60%)
      final critical = renderer.renderSvgSpatialMap(
        heartRate: 175.0,
        rmssd: 18.2,
        alpha1: 0.55,
        submissionRisk: 88.0,
        currentTechnique: 'Inside Heel Hook Breaking Mechanism',
      );
      expect(critical, contains('#FF0055')); // Critical red color
      expect(critical, contains('CRITICAL TORQUE'));
      expect(critical, contains('175 BPM'));
    });

    test('Gauge & Indicator Subsystems: Standby and active boundary guarantees', () {
      // Readiness gauge
      const gaugeRenderer = ReadinessGaugeRenderer(size: 180);
      final standbyGauge = gaugeRenderer.renderSvgGauge(0.0, 0.0, 0.0);
      expect(standbyGauge, contains('-- %'));
      expect(standbyGauge, contains('STANDBY / DISCONNECTED'));

      final highReadiness = gaugeRenderer.renderSvgGauge(95.0, 50.0, 140.0);
      expect(highReadiness, contains('95%'));
      expect(highReadiness, contains('PRIME READINESS'));

      // Zone 2 indicator
      const zoneRenderer = Zone2IndicatorRenderer(width: 320, height: 140);
      final restingZone = zoneRenderer.renderSvgIndicator(0.0, 'Resting / Disconnected');
      expect(restingZone, contains('α1 = --'));
      expect(restingZone, contains('Resting / Disconnected'));

      final activeZone = zoneRenderer.renderSvgIndicator(0.76, 'Zone 2: Optimal Aerobic');
      expect(activeZone, contains('α1 = 0.76'));
      expect(activeZone, contains('Zone 2: Optimal Aerobic'));

      // Video filming panel
      const videoRenderer = VideoFilmingPanelRenderer(width: 440, height: 320);
      final standbyVideo = videoRenderer.renderSvgVideoPanel(
        isCameraActive: false,
        fps: 0.0,
        landmarksCount: 0,
        heartRate: 0.0,
      );
      expect(standbyVideo, contains('CAMERA STANDBY'));
      expect(standbyVideo, contains('-- BPM'));
      expect(standbyVideo, contains('0/33 Joints Tracked'));
    });

    test('Compiled build/index.html is bit-for-bit synchronized with DashboardScreenRenderer', () {
      final file = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(file.existsSync(), isTrue, reason: 'build/index.html must exist');

      final compiledContent = file.readAsStringSync().trim();
      final renderedContent = const DashboardScreenRenderer().renderDynamicDashboardHtml().trim();

      expect(compiledContent, equals(renderedContent),
          reason: 'build/index.html must match DashboardScreenRenderer output exactly');
    });
  });
}
