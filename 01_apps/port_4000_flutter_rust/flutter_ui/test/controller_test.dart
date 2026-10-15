import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/state/hub_state_controller.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';

void main() {
  group('HubStateController Reactive Stream Tests', () {
    test('Controller emits initial zero-mock baseline and ingests live samples', () async {
      final controller = HubStateController();

      // 1. Verify Zero-Mock Initial State
      expect(controller.currentTelemetry.connected, isFalse);
      expect(controller.currentTelemetry.heartRateBpm, 0.0);
      expect(controller.currentTelemetry.dfaAlpha1, 0.0);
      expect(controller.currentTelemetry.readinessScore, 0.0);
      expect(controller.currentTelemetry.zone2Status, 'Resting / Disconnected');

      // 2. Test Live Sample Ingestion
      final telemetryFuture = controller.telemetryStream.firstWhere((t) => t.latestEcgSample == 1.5);
      final bufferFuture = controller.ecgBufferStream.firstWhere((b) => b.isNotEmpty);

      controller.ingestSample(1.5, isConnected: true);

      final telemetry = await telemetryFuture;
      expect(telemetry.connected, isTrue);
      expect(telemetry.sampleRateHz, 512.0);
      expect(telemetry.latestEcgSample, 1.5);

      final buffer = await bufferFuture;
      expect(buffer.isNotEmpty, isTrue);
      expect(buffer.last, 1.5);

      // 3. Test Shopify Token Update
      controller.updateShopifyToken('lauburu_pro_athlete_token');
      expect(controller.currentMembership.tier, ShopifyTier.proAthlete);

      // 4. Test Lifecycle
      controller.startTelemetryStream();
      expect(controller.isRunning, isTrue);

      controller.dispose();
      expect(controller.isRunning, isFalse);
    });
  });
}
