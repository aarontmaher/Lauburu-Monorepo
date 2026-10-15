// Models for Biometrics, ECG telemetry, Readiness, and Shopify Tier state.

class BiometricTelemetry {
  final String timestamp;
  final String deviceId;
  final bool connected;
  final double sampleRateHz;
  final double heartRateBpm;
  final double rrIntervalMs;
  final double hrvRmssdMs;
  final double hrvSdnnMs;
  final double pnn50Percent;
  final double dfaAlpha1;
  final double readinessScore;
  final String zone2Status;
  final bool ppgCalibrated;
  final double latestEcgSample;
  final bool qrsPeakDetected;

  const BiometricTelemetry({
    required this.timestamp,
    required this.deviceId,
    required this.connected,
    required this.sampleRateHz,
    required this.heartRateBpm,
    required this.rrIntervalMs,
    required this.hrvRmssdMs,
    required this.hrvSdnnMs,
    required this.pnn50Percent,
    required this.dfaAlpha1,
    required this.readinessScore,
    required this.zone2Status,
    required this.ppgCalibrated,
    required this.latestEcgSample,
    required this.qrsPeakDetected,
  });

  factory BiometricTelemetry.fromJson(Map<String, dynamic> json) {
    return BiometricTelemetry(
      timestamp: json['timestamp'] as String? ?? '',
      deviceId: json['device_id'] as String? ?? 'Movesense Standby',
      connected: json['connected'] as bool? ?? false,
      sampleRateHz: (json['sample_rate_hz'] as num?)?.toDouble() ?? 512.0,
      heartRateBpm: (json['heart_rate_bpm'] as num?)?.toDouble() ?? 0.0,
      rrIntervalMs: (json['rr_interval_ms'] as num?)?.toDouble() ?? 0.0,
      hrvRmssdMs: (json['hrv_rmssd_ms'] as num?)?.toDouble() ?? 0.0,
      hrvSdnnMs: (json['hrv_sdnn_ms'] as num?)?.toDouble() ?? 0.0,
      pnn50Percent: (json['pnn50_percent'] as num?)?.toDouble() ?? 0.0,
      dfaAlpha1: (json['dfa_alpha1'] as num?)?.toDouble() ?? 0.0,
      readinessScore: (json['readiness_score'] as num?)?.toDouble() ?? 0.0,
      zone2Status: json['zone2_status'] as String? ?? 'Resting / Disconnected',
      ppgCalibrated: json['ppg_calibrated'] as bool? ?? false,
      latestEcgSample: (json['latest_ecg_sample'] as num?)?.toDouble() ?? 0.0,
      qrsPeakDetected: json['qrs_peak_detected'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'timestamp': timestamp,
    'device_id': deviceId,
    'connected': connected,
    'sample_rate_hz': sampleRateHz,
    'heart_rate_bpm': heartRateBpm,
    'rr_interval_ms': rrIntervalMs,
    'hrv_rmssd_ms': hrvRmssdMs,
    'hrv_sdnn_ms': hrvSdnnMs,
    'pnn50_percent': pnn50Percent,
    'dfa_alpha1': dfaAlpha1,
    'readiness_score': readinessScore,
    'zone2_status': zone2Status,
    'ppg_calibrated': ppgCalibrated,
    'latest_ecg_sample': latestEcgSample,
    'qrs_peak_detected': qrsPeakDetected,
  };

  static BiometricTelemetry initial() {
    return BiometricTelemetry(
      timestamp: DateTime.now().toUtc().toIso8601String(),
      deviceId: 'Movesense Standby',
      connected: false,
      sampleRateHz: 512.0,
      heartRateBpm: 0.0,
      rrIntervalMs: 0.0,
      hrvRmssdMs: 0.0,
      hrvSdnnMs: 0.0,
      pnn50Percent: 0.0,
      dfaAlpha1: 0.0,
      readinessScore: 0.0,
      zone2Status: 'Resting / Disconnected',
      ppgCalibrated: false,
      latestEcgSample: 0.0,
      qrsPeakDetected: false,
    );
  }
}

enum ShopifyTier {
  freeCommunity,
  proAthlete,
  crowdsourcedComputeLifetime,
}

class ShopifyMembership {
  final ShopifyTier tier;
  final String customerId;
  final bool activeSubscription;
  final int computeCreditsGflops;
  final List<String> allowedFeatures;

  const ShopifyMembership({
    required this.tier,
    required this.customerId,
    required this.activeSubscription,
    required this.computeCreditsGflops,
    required this.allowedFeatures,
  });

  factory ShopifyMembership.fromCode(int code, {String customerId = 'athlete'}) {
    switch (code) {
      case 1:
        return ShopifyMembership(
          tier: ShopifyTier.proAthlete,
          customerId: customerId,
          activeSubscription: true,
          computeCreditsGflops: 50000,
          allowedFeatures: const [
            '512Hz Medical-Grade ECG',
            'Real-Time DFA-Alpha1 Zone 2 Coach',
            'Pan-Tompkins DSP Raw Stream',
            'Priority 7-Layer Mesh Sharding',
          ],
        );
      case 2:
        return ShopifyMembership(
          tier: ShopifyTier.crowdsourcedComputeLifetime,
          customerId: customerId,
          activeSubscription: true,
          computeCreditsGflops: 999999,
          allowedFeatures: const [
            'All Pro Features (Lifetime Free)',
            'Uncapped 512Hz Raw Data Pipeline',
            'Zero-Cost Mesh AI Inference',
            'Distributed Ring Worker Access',
          ],
        );
      default:
        return ShopifyMembership(
          tier: ShopifyTier.freeCommunity,
          customerId: customerId,
          activeSubscription: false,
          computeCreditsGflops: 100,
          allowedFeatures: const [
            'Basic Biometrics',
            '128Hz ECG Stream',
            'Local AI Offline RAG',
          ],
        );
    }
  }

  String get tierName {
    switch (tier) {
      case ShopifyTier.proAthlete:
        return r'Pro Athlete ($19/mo)';
      case ShopifyTier.crowdsourcedComputeLifetime:
        return r'Crowdsourced Lifetime Contributor ($0)';
      case ShopifyTier.freeCommunity:
        return r'Community Free Tier ($0)';
    }
  }
}
