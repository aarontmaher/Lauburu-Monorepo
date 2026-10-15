// Readiness Gauge & Biometric Indicators Component

import 'theme.dart';

class ReadinessGaugeRenderer {
  final double size;

  const ReadinessGaugeRenderer({this.size = 180.0});

  String renderSvgGauge(double score, double rmssd, double heartRate) {
    final isStandby = score <= 0.0 || heartRate <= 0.0;
    final clampedScore = score.clamp(0.0, 100.0);
    final circumference = 2 * 3.14159 * 70.0;
    final strokeDashoffset = isStandby ? circumference : circumference - (circumference * clampedScore / 100.0);

    String scoreColor = '#00FFCC'; // Green/Cyan optimal
    String stateLabel = 'PRIME READINESS';
    if (isStandby) {
      scoreColor = '#64748B';
      stateLabel = 'STANDBY / DISCONNECTED';
    } else if (clampedScore < 40.0) {
      scoreColor = '#FF0055'; // Red fatigued
      stateLabel = 'HIGH FATIGUE';
    } else if (clampedScore < 70.0) {
      scoreColor = '#FFD700'; // Yellow moderate
      stateLabel = 'MODERATE RECOVERY';
    }

    final scoreDisplay = isStandby ? '-- %' : '${clampedScore.toStringAsFixed(0)}%';
    final hrDisplay = heartRate > 0 ? heartRate.toStringAsFixed(0) : '--';
    final rmssdDisplay = rmssd > 0 ? '${rmssd.toStringAsFixed(1)}ms' : '-- ms';

    return '''
<svg width="$size" height="$size" viewBox="0 0 180 180" xmlns="http://www.w3.org/2000/svg">
  <circle cx="90" cy="90" r="70" stroke="#1E293B" stroke-width="12" fill="none"/>
  <circle cx="90" cy="90" r="70" stroke="$scoreColor" stroke-width="12" fill="none"
          stroke-linecap="round"
          stroke-dasharray="$circumference"
          stroke-dashoffset="$strokeDashoffset"
          transform="rotate(-90 90 90)"/>
  
  <text x="90" y="80" text-anchor="middle" fill="#FFFFFF" font-size="${isStandby ? 26 : 32}" font-weight="900" font-family="${LauburuTypography.fontFamily}">
    $scoreDisplay
  </text>
  <text x="90" y="102" text-anchor="middle" fill="$scoreColor" font-size="10" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    $stateLabel
  </text>
  <text x="90" y="120" text-anchor="middle" fill="#94A3B8" font-size="9" font-family="${LauburuTypography.fontFamily}">
    HRV: $rmssdDisplay | HR: $hrDisplay
  </text>
</svg>
''';
  }
}
