// High-Performance ECG Waveform Visualizer Component

import 'theme.dart';

class EcgLiveCanvasRenderer {
  final double width;
  final double height;

  const EcgLiveCanvasRenderer({required this.width, required this.height});

  String renderSvgWaveform(List<double> buffer, {bool isQrs = false, double heartRate = 0.0}) {
    final bufferLen = buffer.length;
    if (bufferLen < 2) {
      return '<svg width="$width" height="$height" xmlns="http://www.w3.org/2000/svg">'
          '<rect width="100%" height="100%" fill="#0A0E17"/>'
          '<text x="50%" y="50%" fill="#64748B" font-family="monospace" text-anchor="middle">WAITING FOR 512Hz SENSOR STREAM...</text>'
          '</svg>';
    }

    final pathBuffer = StringBuffer();
    final gridBuffer = StringBuffer();

    // 1. Render medical grid (30mm x 30mm grid lines)
    const gridStepX = 25.0;
    const gridStepY = 25.0;

    for (double x = 0; x < width; x += gridStepX) {
      gridBuffer.write('<line x1="$x" y1="0" x2="$x" y2="$height" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.6"/>');
    }
    for (double y = 0; y < height; y += gridStepY) {
      gridBuffer.write('<line x1="0" y1="$y" x2="$width" y2="$y" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.6"/>');
    }

    // 2. Render ECG signal path
    final midY = height / 2.0;
    final scaleY = height / 4.0;
    final dx = width / (bufferLen - 1);

    for (int i = 0; i < bufferLen; i++) {
      final x = i * dx;
      final y = (midY - (buffer[i] * scaleY)).clamp(4.0, height - 4.0);
      if (i == 0) {
        pathBuffer.write('M $x $y ');
      } else {
        pathBuffer.write('L $x $y ');
      }
    }

    final glowColor = isQrs ? '#FF0055' : '#00FFCC';
    final strokeColor = isQrs ? '#FF0055' : '#00FFCC';
    final hrDisplay = heartRate > 0 ? '${heartRate.toStringAsFixed(0)} BPM' : '-- BPM';

    return '''
<svg width="$width" height="$height" viewBox="0 0 $width $height" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="ecg-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <linearGradient id="grid-fade" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0A0E17" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#131B2A" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#0A0E17" stop-opacity="0.9"/>
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="url(#grid-fade)" rx="8"/>

  <!-- Medical Oscilloscope Grid -->
  $gridBuffer

  <!-- ECG Waveform Glow -->
  <path d="${pathBuffer.toString()}" fill="none" stroke="$glowColor" stroke-width="3" stroke-opacity="0.4" filter="url(#ecg-glow)"/>
  <!-- ECG Main Trace -->
  <path d="${pathBuffer.toString()}" fill="none" stroke="$strokeColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>

  <!-- Telemetry Badge Header -->
  <rect x="12" y="10" width="160" height="24" fill="#0A0E17" fill-opacity="0.8" rx="4" stroke="#334155" stroke-width="1"/>
  <circle cx="22" cy="22" r="4" fill="${isQrs ? '#FF0055' : '#00FFCC'}"/>
  <text x="32" y="26" fill="#FFFFFF" font-size="11" font-family="${LauburuTypography.fontFamily}" font-weight="bold">ECG 512Hz | $hrDisplay</text>

  <!-- Sweep Line Scanner -->
  <line x1="${width - 15}" y1="4" x2="${width - 15}" y2="${height - 4}" stroke="#00FFCC" stroke-width="1.5" stroke-opacity="0.8" stroke-dasharray="2 2"/>
</svg>
''';
  }
}
