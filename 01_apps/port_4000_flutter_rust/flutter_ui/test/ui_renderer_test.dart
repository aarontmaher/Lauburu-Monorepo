import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';
import 'package:lauburu_port4000_flutter/src/ui/ecg_live_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/spatial_tatami_canvas.dart';
import 'package:lauburu_port4000_flutter/src/ui/readiness_gauge.dart';
import 'package:lauburu_port4000_flutter/src/ui/zone2_indicator.dart';
import 'package:lauburu_port4000_flutter/src/ui/video_filming_panel.dart';
import 'package:lauburu_port4000_flutter/src/ui/sensor_control_panel.dart';
import 'package:lauburu_port4000_flutter/src/ui/shopify_tier_card.dart';

void main() {
  group('UI Renderer & Canvas Component Tests', () {
    test('DashboardScreenRenderer generates complete zero-mock SPA HTML with canvas elements', () {
      const renderer = DashboardScreenRenderer(width: 1100, height: 850);
      final html = renderer.renderDynamicDashboardHtml();

      expect(html, contains('id="canvas-ecg"'));
      expect(html, contains('id="canvas-tatami"'));
      expect(html, contains('id="canvas-video"'));
      expect(html, contains('connectPixelBluetooth'));
      expect(html, contains('/ws/telemetry'));
      expect(html, contains('/ws/spatial'));
      expect(html, contains('0% MOCK DATA'));
      expect(html, contains('>--<'));
    });

    test('EcgLiveCanvasRenderer renders SVG waveform and resting waiting state', () {
      const renderer = EcgLiveCanvasRenderer(width: 480, height: 200);

      final emptySvg = renderer.renderSvgWaveform([]);
      expect(emptySvg, contains('WAITING FOR 512Hz SENSOR STREAM...'));

      final flatlineSvg = renderer.renderSvgWaveform([0.0, 0.0, 0.0], heartRate: 0.0);
      expect(flatlineSvg, contains('ECG 512Hz | -- BPM'));

      final activeSvg = renderer.renderSvgWaveform([0.1, 1.2, -0.4, 0.0], heartRate: 142.0, isQrs: true);
      expect(activeSvg, contains('ECG 512Hz | 142 BPM'));
      expect(activeSvg, contains('#FF0055'));
    });

    test('SpatialTatamiCanvasRenderer renders 3D tatami mat in resting and active states', () {
      const renderer = SpatialTatamiCanvasRenderer(width: 540, height: 320);

      final restingSvg = renderer.renderSvgSpatialMap(
        heartRate: 0.0,
        rmssd: 0.0,
        alpha1: 0.0,
        submissionRisk: 0.0,
        currentTechnique: 'Standby / Mat Empty',
      );
      expect(restingSvg, contains('3D TATAMI'));
      expect(restingSvg, contains('Standby / Mat Empty'));
      expect(restingSvg, contains('-- BPM'));

      final activeSvg = renderer.renderSvgSpatialMap(
        heartRate: 145.0,
        rmssd: 34.2,
        alpha1: 0.72,
        submissionRisk: 85.0,
        currentTechnique: 'Ashi Garami Heel Hook',
      );
      expect(activeSvg, contains('145 BPM'));
      expect(activeSvg, contains('CRITICAL TORQUE'));
    });

    test('ReadinessGaugeRenderer displays standby and active scores accurately', () {
      const renderer = ReadinessGaugeRenderer(size: 180);

      final standbyGauge = renderer.renderSvgGauge(0.0, 0.0, 0.0);
      expect(standbyGauge, contains('-- %'));
      expect(standbyGauge, contains('STANDBY / DISCONNECTED'));

      final activeGauge = renderer.renderSvgGauge(85.0, 42.0, 130.0);
      expect(activeGauge, contains('85%'));
      expect(activeGauge, contains('PRIME READINESS'));
    });

    test('Zone2IndicatorRenderer displays resting and active thresholds', () {
      const renderer = Zone2IndicatorRenderer(width: 320, height: 140);

      final resting = renderer.renderSvgIndicator(0.0, 'Resting / Disconnected');
      expect(resting, contains('α1 = --'));
      expect(resting, contains('Resting / Disconnected'));

      final active = renderer.renderSvgIndicator(0.74, 'Zone 2: Optimal Aerobic');
      expect(active, contains('α1 = 0.74'));
      expect(active, contains('Zone 2: Optimal Aerobic'));
    });

    test('VideoFilmingPanelRenderer renders video reticle HUD', () {
      const renderer = VideoFilmingPanelRenderer(width: 440, height: 320);

      final standby = renderer.renderSvgVideoPanel(
        isCameraActive: false,
        fps: 0.0,
        landmarksCount: 0,
        heartRate: 0.0,
      );
      expect(standby, contains('CAMERA STANDBY'));
      expect(standby, contains('-- BPM'));

      final active = renderer.renderSvgVideoPanel(
        isCameraActive: true,
        fps: 60.0,
        landmarksCount: 33,
        heartRate: 135.0,
      );
      expect(active, contains('LIVE CAMERA ACTIVE'));
      expect(active, contains('135 BPM'));
      expect(active, contains('33/33 Joints Tracked'));
    });

    test('SensorControlPanelRenderer and ShopifyTierCardRenderer render cleanly', () {
      const sensorRenderer = SensorControlPanelRenderer(width: 320);
      final sensorSvg = sensorRenderer.renderSvgPanel(BiometricTelemetry.initial(), true);
      expect(sensorSvg, contains('SENSOR &amp; INGESTION CONTROL'));
      expect(sensorSvg, contains('DISCONNECTED'));
      expect(sensorSvg, contains('RUST FFI NATIVE'));

      const shopifyRenderer = ShopifyTierCardRenderer(width: 320);
      final shopifySvg = shopifyRenderer.renderSvgCard(ShopifyMembership.fromCode(1));
      expect(shopifySvg, contains('PRO ATHLETE'));
      expect(shopifySvg, contains('50000 GFLOPS'));
    });
  });
}
