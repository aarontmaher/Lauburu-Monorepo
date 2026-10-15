// Sensor Ingestion Control Panel Component

import '../models/biometrics_model.dart';
import 'theme.dart';

class SensorControlPanelRenderer {
  final double width;

  const SensorControlPanelRenderer({this.width = 320.0});

  String renderSvgPanel(BiometricTelemetry telemetry, bool isFfiActive) {
    final statusColor = telemetry.connected ? '#00FF88' : '#64748B';
    final statusLabel = telemetry.connected ? 'STREAMING ACTIVE' : 'DISCONNECTED';
    final bridgeLabel = isFfiActive ? 'RUST FFI NATIVE' : 'IPC / WEBSOCKET';

    return '''
<svg width="$width" height="150" viewBox="0 0 $width 150" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#131B2A" rx="8" stroke="#334155" stroke-width="1"/>

  <!-- Title -->
  <text x="16" y="24" fill="#94A3B8" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    SENSOR &amp; INGESTION CONTROL
  </text>

  <!-- Connection Status Badge -->
  <circle cx="22" cy="48" r="5" fill="$statusColor"/>
  <text x="34" y="52" fill="#FFFFFF" font-size="12" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    ${telemetry.deviceId}
  </text>
  <text x="${width - 16}" y="52" text-anchor="end" fill="$statusColor" font-size="10" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    $statusLabel
  </text>

  <!-- Metrics Row -->
  <rect x="16" y="68" width="${(width - 40) / 2}" height="32" fill="#1E293B" rx="4"/>
  <text x="24" y="82" fill="#64748B" font-size="8" font-family="${LauburuTypography.fontFamily}">SAMPLE RATE</text>
  <text x="24" y="94" fill="#00FFCC" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    ${telemetry.sampleRateHz.toStringAsFixed(0)} Hz
  </text>

  <rect x="${16 + (width - 40) / 2 + 8}" y="68" width="${(width - 40) / 2}" height="32" fill="#1E293B" rx="4"/>
  <text x="${24 + (width - 40) / 2 + 8}" y="82" fill="#64748B" font-size="8" font-family="${LauburuTypography.fontFamily}">PPG CALIBRATION</text>
  <text x="${24 + (width - 40) / 2 + 8}" y="94" fill="${telemetry.ppgCalibrated ? '#00FF88' : '#FFD700'}" font-size="11" font-weight="bold" font-family="${LauburuTypography.fontFamily}">
    ${telemetry.ppgCalibrated ? 'CALIBRATED' : '10s WINDOW'}
  </text>

  <!-- Bridge Engine Info -->
  <text x="16" y="125" fill="#94A3B8" font-size="9" font-family="${LauburuTypography.fontFamily}">
    Bridge Engine: <tspan fill="#00FFCC" font-weight="bold">$bridgeLabel</tspan>
  </text>
  <text x="16" y="140" fill="#64748B" font-size="8" font-family="${LauburuTypography.fontFamily}">
    Port 4000 Core | Pan-Tompkins Real-Time QRS
  </text>
</svg>
''';
  }
}
