import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/bridge/native_bridge.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';

void main() {
  group('LauburuNativeBridge Zero-Mock Tests', () {
    test('Bridge initializes cleanly and provides resting zero metrics on standby', () {
      final bridge = LauburuNativeBridge();
      expect(bridge, isNotNull);

      final readiness = bridge.getReadinessScore();
      expect(readiness, greaterThanOrEqualTo(0.0));
      expect(readiness, lessThanOrEqualTo(100.0));

      final rmssd = bridge.getHrvRmssd();
      expect(rmssd, greaterThanOrEqualTo(0.0));

      final alpha1 = bridge.getDfaAlpha1();
      expect(alpha1, greaterThanOrEqualTo(0.0));
      expect(alpha1, lessThanOrEqualTo(2.0));

      final snapshot = bridge.getTelemetrySnapshot();
      expect(snapshot, isNotNull);
    });

    test('Bridge processSample handles zero sample and dynamic impulses', () {
      final bridge = LauburuNativeBridge();

      // Flatline sample
      final zeroResult = bridge.processSample(0.0);
      expect(zeroResult.containsKey('is_qrs_peak'), isTrue);
      expect(zeroResult.containsKey('heart_rate_bpm'), isTrue);

      // Dynamic impulse sample
      final impulseResult = bridge.processSample(1.5);
      expect(impulseResult.containsKey('is_qrs_peak'), isTrue);
      expect(impulseResult.containsKey('heart_rate_bpm'), isTrue);
    });

    test('Bridge verifyShopifyToken routes tokens accurately', () {
      final bridge = LauburuNativeBridge();

      final pro = bridge.verifyShopifyToken('lauburu_pro_token_123');
      expect(pro.tier, ShopifyTier.proAthlete);

      final crowd = bridge.verifyShopifyToken('lauburu_mesh_node_contributor');
      expect(crowd.tier, ShopifyTier.crowdsourcedComputeLifetime);

      final free = bridge.verifyShopifyToken('unrecognized_token');
      expect(free.tier, ShopifyTier.freeCommunity);
    });
  });
}
