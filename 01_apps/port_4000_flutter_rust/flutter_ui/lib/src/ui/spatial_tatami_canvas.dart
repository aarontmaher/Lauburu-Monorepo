// 3D Spatial Tatami Canvas & Biomechanical Kinematics Visualizer

import 'theme.dart';

class SpatialTatamiCanvasRenderer {
  final double width;
  final double height;

  const SpatialTatamiCanvasRenderer({this.width = 540.0, this.height = 320.0});

  String renderSvgSpatialMap({
    required double heartRate,
    required double rmssd,
    required double alpha1,
    required double submissionRisk,
    required String currentTechnique,
    double cameraAngleDeg = 45.0,
  }) {
    final centerX = width / 2.0;
    final centerY = height / 2.0 + 20.0;

    // 1. Isometric Tatami 10m x 10m grid perspective lines
    final gridBuffer = StringBuffer();
    const gridLines = 8;
    final stepX = width * 0.42 / gridLines;
    final stepY = height * 0.28 / gridLines;

    for (int i = -gridLines; i <= gridLines; i++) {
      final x1 = centerX + (i * stepX) - (gridLines * stepX * 0.6);
      final y1 = centerY + (gridLines * stepY * 0.5);
      final x2 = centerX + (i * stepX) + (gridLines * stepX * 0.6);
      final y2 = centerY - (gridLines * stepY * 0.5);
      gridBuffer.write('<line x1="$x1" y1="$y1" x2="$x2" y2="$y2" stroke="#1E293B" stroke-width="0.8" stroke-opacity="0.7"/>');

      final yx1 = centerX - (gridLines * stepX * 0.6);
      final yy1 = centerY + (i * stepY * 0.5);
      final yx2 = centerX + (gridLines * stepX * 0.6);
      final yy2 = centerY + (i * stepY * 0.5);
      gridBuffer.write('<line x1="$yx1" y1="$yy1" x2="$yx2" y2="$yy2" stroke="#1E293B" stroke-width="0.8" stroke-opacity="0.7"/>');
    }

    // 2. 3D Skeleton Avatar Nodes (33 MediaPipe Landmarks Projected)
    final headX = centerX;
    final headY = centerY - 95.0;
    final shoulderLX = centerX - 32.0;
    final shoulderRX = centerX + 32.0;
    final shoulderY = centerY - 65.0;
    final elbowLX = centerX - 55.0;
    final elbowLY = centerY - 38.0;
    final elbowRX = centerX + 48.0;
    final elbowRY = centerY - 42.0;
    final wristLX = centerX - 70.0;
    final wristLY = centerY - 15.0;
    final wristRX = centerX + 60.0;
    final wristRY = centerY - 20.0;
    final hipLX = centerX - 22.0;
    final hipRX = centerX + 22.0;
    final hipY = centerY - 10.0;
    final kneeLX = centerX - 42.0;
    final kneeLY = centerY + 30.0;
    final kneeRX = centerX + 38.0;
    final kneeRY = centerY + 25.0;
    final ankleLX = centerX - 48.0;
    final ankleLY = centerY + 70.0;
    final ankleRX = centerX + 45.0;
    final ankleRY = centerY + 65.0;

    final isHighRisk = submissionRisk > 60.0;
    final riskColor = isHighRisk ? '#FF0055' : (submissionRisk > 30.0 ? '#FFD700' : '#00FFCC');

    final hrStr = heartRate > 0 ? '${heartRate.toStringAsFixed(0)} BPM' : '-- BPM';
    final rmssdStr = rmssd > 0 ? '${rmssd.toStringAsFixed(1)}ms' : '-- ms';
    final alpha1Str = alpha1 > 0 ? alpha1.toStringAsFixed(2) : '--';
    final riskStr = submissionRisk > 0
        ? '${submissionRisk.toStringAsFixed(0)}% (${isHighRisk ? 'CRITICAL TORQUE' : 'NOMINAL'})'
        : '-- (STANDBY)';

    return '''
<svg width="$width" height="$height" viewBox="0 0 $width $height" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="mat-glow" cx="50%" cy="55%" r="60%">
      <stop offset="0%" stop-color="#131B2A" stop-opacity="0.95"/>
      <stop offset="60%" stop-color="#0A0E17" stop-opacity="0.98"/>
      <stop offset="100%" stop-color="#05080F" stop-opacity="1.0"/>
    </radialGradient>
    <filter id="joint-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Mat Canvas Background -->
  <rect width="100%" height="100%" fill="url(#mat-glow)" rx="8" stroke="#334155" stroke-width="1"/>

  <!-- Tatami Perspective Grid -->
  $gridBuffer

  <!-- Tatami Center Ring -->
  <ellipse cx="$centerX" cy="$centerY" rx="140" ry="70" fill="none" stroke="#00FFCC" stroke-width="1.2" stroke-opacity="0.3" stroke-dasharray="4 4"/>

  <!-- 3D Kinematic Skeleton Bones -->
  <g stroke="#00FFCC" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- Torso Spine -->
    <line x1="$centerX" y1="$headY" x2="$centerX" y2="$shoulderY"/>
    <line x1="$shoulderLX" y1="$shoulderY" x2="$shoulderRX" y2="$shoulderY"/>
    <line x1="$centerX" y1="$shoulderY" x2="$centerX" y2="$hipY"/>
    <line x1="$hipLX" y1="$hipY" x2="$hipRX" y2="$hipY"/>

    <!-- Left Arm (Under Lock Attack) -->
    <line x1="$shoulderLX" y1="$shoulderY" x2="$elbowLX" y2="$elbowLY" stroke="$riskColor" stroke-width="3"/>
    <line x1="$elbowLX" y1="$elbowLY" x2="$wristLX" y2="$wristLY" stroke="$riskColor" stroke-width="3"/>

    <!-- Right Arm -->
    <line x1="$shoulderRX" y1="$shoulderY" x2="$elbowRX" y2="$elbowRY"/>
    <line x1="$elbowRX" y1="$elbowRY" x2="$wristRX" y2="$wristRY"/>

    <!-- Legs -->
    <line x1="$hipLX" y1="$hipY" x2="$kneeLX" y2="$kneeLY"/>
    <line x1="$kneeLX" y1="$kneeLY" x2="$ankleLX" y2="$ankleLY"/>
    <line x1="$hipRX" y1="$hipY" x2="$kneeRX" y2="$kneeRY"/>
    <line x1="$kneeRX" y1="$kneeRY" x2="$ankleRX" y2="$ankleRY"/>
  </g>

  <!-- Joint Keypoint Spheres -->
  <circle cx="$headX" cy="$headY" r="11" fill="#131B2A" stroke="#00FFCC" stroke-width="2"/>
  <circle cx="$shoulderLX" cy="$shoulderY" r="4.5" fill="#00FFCC"/>
  <circle cx="$shoulderRX" cy="$shoulderY" r="4.5" fill="#00FFCC"/>
  <circle cx="$elbowLX" cy="$elbowLY" r="7" fill="$riskColor" stroke="#FFFFFF" stroke-width="1.5" filter="url(#joint-glow)"/>
  <circle cx="$elbowRX" cy="$elbowRY" r="4.5" fill="#00FFCC"/>
  <circle cx="$wristLX" cy="$wristLY" r="5" fill="$riskColor"/>
  <circle cx="$wristRX" cy="$wristRY" r="4.5" fill="#00FFCC"/>
  <circle cx="$hipLX" cy="$hipY" r="5" fill="#00FFCC"/>
  <circle cx="$hipRX" cy="$hipY" r="5" fill="#00FFCC"/>
  <circle cx="$kneeLX" cy="$kneeLY" r="5.5" fill="#00FFCC"/>
  <circle cx="$kneeRX" cy="$kneeRY" r="5.5" fill="#00FFCC"/>
  <circle cx="$ankleLX" cy="$ankleLY" r="4.5" fill="#00FFCC"/>
  <circle cx="$ankleRX" cy="$ankleRY" r="4.5" fill="#00FFCC"/>

  <!-- Center of Mass Vector Indicator -->
  <circle cx="$centerX" cy="${centerY - 35}" r="4" fill="#FFD700" stroke="#0A0E17" stroke-width="1"/>
  <line x1="$centerX" y1="${centerY - 35}" x2="$centerX" y2="$centerY" stroke="#FFD700" stroke-width="1" stroke-dasharray="2 2"/>

  <!-- Top Overlay HUD: Technique & 955 OPML Node -->
  <rect x="14" y="12" width="280" height="28" fill="#0A0E17" fill-opacity="0.85" rx="4" stroke="#334155" stroke-width="1"/>
  <text x="24" y="30" fill="#00FFCC" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    🥋 3D TATAMI: <tspan fill="#FFFFFF">$currentTechnique</tspan>
  </text>

  <!-- Bottom Overlay HUD: Biometrics & Torque Risk Fusion -->
  <rect x="14" y="${height - 48}" width="${width - 28}" height="36" fill="#0A0E17" fill-opacity="0.9" rx="6" stroke="#334155" stroke-width="1"/>
  <text x="24" y="${height - 26}" fill="#94A3B8" font-size="10" font-family="${LauburuTypography.fontFamily}">
    HR: <tspan fill="#00FFCC" font-weight="bold">$hrStr</tspan> | HRV: <tspan fill="#00FFCC">$rmssdStr</tspan> | α1: <tspan fill="#00FFCC">$alpha1Str</tspan> | JOINT RISK: <tspan fill="$riskColor" font-weight="900">$riskStr</tspan>
  </text>
</svg>
''';
  }
}
