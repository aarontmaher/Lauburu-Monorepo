import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/models/biometrics_model.dart';

void main() {
  group('Biometrics Model Zero-Mock Tests', () {
    test('BiometricTelemetry.initial() complies with Rule #0 zero-mock contract', () {
      final initial = BiometricTelemetry.initial();
      expect(initial.connected, isFalse);
      expect(initial.sampleRateHz, 512.0);
      expect(initial.heartRateBpm, 0.0);
      expect(initial.rrIntervalMs, 0.0);
      expect(initial.hrvRmssdMs, 0.0);
      expect(initial.hrvSdnnMs, 0.0);
      expect(initial.pnn50Percent, 0.0);
      expect(initial.dfaAlpha1, 0.0);
      expect(initial.readinessScore, 0.0);
      expect(initial.zone2Status, 'Resting / Disconnected');
      expect(initial.ppgCalibrated, isFalse);
      expect(initial.latestEcgSample, 0.0);
      expect(initial.qrsPeakDetected, isFalse);
    });

    test('BiometricTelemetry JSON serialization roundtrip', () {
      final initial = BiometricTelemetry.initial();
      final json = initial.toJson();
      expect(json['sample_rate_hz'], 512.0);
      expect(json['connected'], isFalse);
      expect(json['heart_rate_bpm'], 0.0);
      expect(json['dfa_alpha1'], 0.0);
      expect(json['readiness_score'], 0.0);

      final reconstructed = BiometricTelemetry.fromJson(json);
      expect(reconstructed.deviceId, initial.deviceId);
      expect(reconstructed.connected, isFalse);
      expect(reconstructed.readinessScore, 0.0);
      expect(reconstructed.dfaAlpha1, 0.0);
      expect(reconstructed.heartRateBpm, 0.0);
    });

    test('ShopifyMembership tier parsing & feature validation', () {
      final pro = ShopifyMembership.fromCode(1, customerId: 'pro_athlete');
      expect(pro.tier, ShopifyTier.proAthlete);
      expect(pro.activeSubscription, isTrue);
      expect(pro.computeCreditsGflops, 50000);
      expect(pro.allowedFeatures, contains('512Hz Medical-Grade ECG'));
      expect(pro.tierName, contains('Pro Athlete'));

      final crowd = ShopifyMembership.fromCode(2, customerId: 'node_m4');
      expect(crowd.tier, ShopifyTier.crowdsourcedComputeLifetime);
      expect(crowd.activeSubscription, isTrue);
      expect(crowd.computeCreditsGflops, 999999);
      expect(crowd.allowedFeatures, contains('All Pro Features (Lifetime Free)'));
      expect(crowd.tierName, contains('Lifetime'));

      final free = ShopifyMembership.fromCode(0);
      expect(free.tier, ShopifyTier.freeCommunity);
      expect(free.activeSubscription, isFalse);
      expect(free.computeCreditsGflops, 100);
      expect(free.tierName, contains('Community'));
    });
  });
}
