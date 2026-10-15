// Zone 2 Aerobic Threshold (DFA-alpha1) & Metabolic Coach Component

import 'theme.dart';

class Zone2IndicatorRenderer {
  final double width;
  final double height;

  const Zone2IndicatorRenderer({this.width = 320.0, this.height = 140.0});

  String renderSvgIndicator(double alpha1, String statusText) {
    // Normal aerobic range: alpha1 between 0.50 (LT2) and 0.75 (LT1)
    // alpha1 > 0.75 = Zone 1 / Under aerobic threshold
    // 0.50 <= alpha1 <= 0.75 = Zone 2
    // alpha1 < 0.50 = Zone 3-5 Anaerobic
    final isStandby = alpha1 <= 0.0;
    final markerPos = isStandby
        ? 20.0
        : (((1.5 - alpha1) / 1.2).clamp(0.0, 1.0) * (width - 40.0) + 20.0);
    final alpha1Display = isStandby ? '--' : alpha1.toStringAsFixed(2);

    return '''
<svg width="$width" height="$height" viewBox="0 0 $width $height" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#131B2A" rx="8" stroke="#334155" stroke-width="1"/>

  <!-- Title -->
  <text x="16" y="24" fill="#00FFCC" font-size="12" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    DFA-ALPHA 1 ZONE 2 AEROBIC COACH
  </text>
  <text x="${width - 16}" y="24" text-anchor="end" fill="#FFFFFF" font-size="13" font-weight="900" font-family="${LauburuTypography.fontFamily}">
    α1 = $alpha1Display
  </text>

  <!-- Zone Spectrum Gradient Bar -->
  <defs>
    <linearGradient id="zone-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00FF88"/>
      <stop offset="35%" stop-color="#00FFCC"/>
      <stop offset="65%" stop-color="#FFD700"/>
      <stop offset="100%" stop-color="#FF0055"/>
    </linearGradient>
  </defs>

  <rect x="20" y="44" width="${width - 40}" height="14" fill="url(#zone-grad)" rx="7"/>

  <!-- Target Zone 2 Window Outline (LT1 to LT2) -->
  <rect x="${width * 0.35}" y="42" width="${width * 0.30}" height="18" fill="none" stroke="#FFFFFF" stroke-width="2" rx="4" stroke-dasharray="3 2"/>

  <!-- Dynamic Value Cursor -->
  <circle cx="$markerPos" cy="51" r="9" fill="#0A0E17" stroke="#00FFCC" stroke-width="3"/>
  <circle cx="$markerPos" cy="51" r="4" fill="#00FFCC"/>

  <!-- Labels -->
  <text x="20" y="74" fill="#94A3B8" font-size="9" font-family="${LauburuTypography.fontFamily}">Z1 (α1 > 0.85)</text>
  <text x="${width * 0.5}" y="74" text-anchor="middle" fill="#00FFCC" font-size="9" font-weight="bold" font-family="${LauburuTypography.fontFamily}">ZONE 2 TARGET</text>
  <text x="${width - 20}" y="74" text-anchor="end" fill="#FF0055" font-size="9" font-family="${LauburuTypography.fontFamily}">Z4/5 (α1 &lt; 0.50)</text>

  <!-- Real-time Status Card -->
  <rect x="20" y="90" width="${width - 40}" height="36" fill="#1E293B" rx="6"/>
  <text x="32" y="112" fill="#FFFFFF" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    STATUS: <tspan fill="#00FFCC">$statusText</tspan>
  </text>
</svg>
''';
  }
}
