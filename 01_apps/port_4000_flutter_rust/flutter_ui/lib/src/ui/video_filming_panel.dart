// Live Camera Video Filming & Pose Tracking Overlay Component

import 'theme.dart';

class VideoFilmingPanelRenderer {
  final double width;
  final double height;

  const VideoFilmingPanelRenderer({this.width = 440.0, this.height = 320.0});

  String renderSvgVideoPanel({
    required bool isCameraActive,
    required double fps,
    required int landmarksCount,
    required double heartRate,
  }) {
    final statusColor = isCameraActive ? '#00FF88' : '#FF0055';
    final statusText = isCameraActive ? 'LIVE CAMERA ACTIVE' : 'CAMERA STANDBY';
    final hrDisplay = heartRate > 0 ? '${heartRate.toStringAsFixed(0)} BPM' : '-- BPM';
    final hrDevice = heartRate > 0 ? 'Movesense BLE' : 'Movesense Standby';

    return '''
<svg width="$width" height="$height" viewBox="0 0 $width $height" xmlns="http://www.w3.org/2000/svg">
  <!-- Video Container Dark Viewport -->
  <rect width="100%" height="100%" fill="#060A10" rx="8" stroke="#334155" stroke-width="1"/>

  <!-- Simulated Video Frame / Scanlines -->
  <defs>
    <pattern id="scanlines" width="100" height="4" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="100" y2="0" stroke="#00FFCC" stroke-width="0.3" stroke-opacity="0.15"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#scanlines)" rx="8"/>

  <!-- Camera Reticle / Target Focus Box -->
  <rect x="40" y="35" width="${width - 80}" height="${height - 70}" fill="none" stroke="#00FFCC" stroke-width="1" stroke-opacity="0.3" stroke-dasharray="10 5" rx="4"/>

  <!-- Corner Brackets -->
  <path d="M 40 55 L 40 35 L 60 35" fill="none" stroke="#00FFCC" stroke-width="2"/>
  <path d="M ${width - 60} 35 L ${width - 40} 35 L ${width - 40} 55" fill="none" stroke="#00FFCC" stroke-width="2"/>
  <path d="M 40 ${height - 55} L 40 ${height - 35} L 60 ${height - 35}" fill="none" stroke="#00FFCC" stroke-width="2"/>
  <path d="M ${width - 60} ${height - 35} L ${width - 40} ${height - 35} L ${width - 40} ${height - 55}" fill="none" stroke="#00FFCC" stroke-width="2"/>

  <!-- Center Crosshair -->
  <line x1="${width / 2.0 - 15}" y1="${height / 2.0}" x2="${width / 2.0 + 15}" y2="${height / 2.0}" stroke="#00FFCC" stroke-width="1" stroke-opacity="0.5"/>
  <line x1="${width / 2.0}" y1="${height / 2.0 - 15}" x2="${width / 2.0}" y2="${height / 2.0 + 15}" stroke="#00FFCC" stroke-width="1" stroke-opacity="0.5"/>

  <!-- Top Video Metadata Badge -->
  <rect x="14" y="12" width="220" height="26" fill="#0A0E17" fill-opacity="0.85" rx="4" stroke="#334155" stroke-width="1"/>
  <circle cx="24" cy="25" r="4" fill="$statusColor"/>
  <text x="34" y="29" fill="#FFFFFF" font-size="10" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    $statusText (${fps.toStringAsFixed(0)} FPS)
  </text>

  <!-- Real-time Movesense Watermark HUD -->
  <rect x="${width - 150}" y="12" width="136" height="26" fill="#0A0E17" fill-opacity="0.85" rx="4" stroke="#334155" stroke-width="1"/>
  <text x="${width - 82}" y="29" text-anchor="middle" fill="#00FFCC" font-size="10" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    💓 $hrDisplay | $hrDevice
  </text>

  <!-- Landmark Mesh Counter Tag -->
  <rect x="14" y="${height - 38}" width="${width - 28}" height="26" fill="#0A0E17" fill-opacity="0.9" rx="4"/>
  <text x="24" y="${height - 21}" fill="#94A3B8" font-size="10" font-family="${LauburuTypography.fontFamily}">
    Pose Landmarker: <tspan fill="#00FFCC" font-weight="bold">$landmarksCount/33 Joints Tracked</tspan> | WebRTC Filming Ready
  </text>
</svg>
''';
  }
}
