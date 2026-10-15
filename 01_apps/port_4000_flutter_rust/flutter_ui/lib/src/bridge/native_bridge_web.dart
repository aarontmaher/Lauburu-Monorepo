import '../models/biometrics_model.dart';

class LauburuNativeBridge {
  static LauburuNativeBridge? _instance;
  
  bool get isFfiLoaded => false; // Always false on Web

  factory LauburuNativeBridge({String? customDylibPath}) {
    _instance ??= LauburuNativeBridge._internal();
    return _instance!;
  }

  LauburuNativeBridge._internal();

  int initCore() {
    return -1;
  }

  Map<String, dynamic> processSample(double sample) {
    // Pure Dart fallback calculation (authentic zero resting state)
    return {
      'is_qrs_peak': false,
      'filtered_val': sample,
      'integrated_val': sample * sample,
      'heart_rate_bpm': 0.0,
      'rr_interval_ms': 0.0,
      'rmssd_ms': 0.0,
      'sdnn_ms': 0.0,
      'pnn50_percent': 0.0,
    };
  }

  double getReadinessScore() {
    return 0.0;
  }

  double getHrvRmssd() {
    return 0.0;
  }

  double getDfaAlpha1() {
    return 0.0;
  }

  ShopifyMembership verifyShopifyToken(String token, {String customerId = 'athlete'}) {
    // Deterministic fallback
    if (token.startsWith('lauburu_pro_')) {
      return ShopifyMembership.fromCode(1, customerId: customerId);
    } else if (token.startsWith('lauburu_mesh_') || token.startsWith('node_')) {
      return ShopifyMembership.fromCode(2, customerId: customerId);
    }
    return ShopifyMembership.fromCode(0, customerId: customerId);
  }

  BiometricTelemetry getTelemetrySnapshot() {
    return BiometricTelemetry.initial();
  }
}
