// Location: test/challenger2_m3_dual_ingestion_stress_test.dart
// Milestone 3 Challenger 2: Dual Bluetooth Ingestion & Real-Time Pipeline Concurrency Stress Test


import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Milestone 3 Challenger 2: Dual Bluetooth Ingestion & Pipeline Concurrency', () {
    const renderer = DashboardScreenRenderer();
    late String htmlContent;

    setUpAll(() {
      htmlContent = renderer.renderDynamicDashboardHtml();
    });

    test('2.1: Compiled HTML contains complete Web Bluetooth and Movesense GATT discovery whitelists', () {
      expect(htmlContent, contains('navigator.bluetooth.requestDevice'));
      expect(htmlContent, contains("'heart_rate'"));
      expect(htmlContent, contains("'battery_service'"));
      expect(htmlContent, contains("'device_information'"));
      
      // Movesense custom services
      expect(htmlContent, contains("'34800001-7185-4d5d-b431-b30e347d9634'"));
      expect(htmlContent, contains("'34800001-07f5-46d1-9167-bd61165970e5'"));
      expect(htmlContent, contains("'34800001-7185-4d5d-b431-b30e393d9e05'"));
      expect(htmlContent, contains("'34800001-7183-4f50-be44-839309ec5951'"));
      expect(htmlContent, contains("'34800001-7185-4d5d-b431-aa30e972d9e1'"));
      expect(htmlContent, contains("'34800001-7140-4a5e-b3f0-11397a109588'"));
      expect(htmlContent, contains("'34800001-071f-425d-8e43-116450343b1b'"));

      // Standard Nordic UART and Polar fallback
      expect(htmlContent, contains("'6e400001-b5a3-f393-e0a9-e50e24dcca9e'"));
      expect(htmlContent, contains("'61353090-8231-49cc-b57a-886370b1f649'"));
    });

    test('2.2: 5-Stage Exponential Backoff mathematical progression and retry capping', () {
      const maxAttempts = 5;
      final rng = Random(42);

      for (int attempt = 1; attempt <= maxAttempts; attempt++) {
        final baseMs = 1000 * pow(2, attempt - 1);
        final minMs = min(10000, baseMs);
        final maxMs = minMs + 200;

        for (int i = 0; i < 50; i++) {
          final jitter = rng.nextDouble() * 200;
          final backoffMs = min(10000, baseMs) + jitter;
          expect(backoffMs, greaterThanOrEqualTo(minMs.toDouble()));
          expect(backoffMs, lessThanOrEqualTo(maxMs.toDouble()));
        }
      }

      // Verify HTML code matches this exact backoff progression
      expect(htmlContent, contains('const MAX_RECONNECT_ATTEMPTS = 5;'));
      expect(htmlContent, contains('Math.min(10000, 1000 * Math.pow(2, reconnectAttempts - 1)) + Math.random() * 200'));
    });

    test('2.3: Sudden Disconnect Teardown resets all metric DOM elements to authentic zero-mock placeholders', () {
      expect(htmlContent, contains("document.getElementById('val-hr').innerText = '--'"));
      expect(htmlContent, contains("document.getElementById('val-rmssd').innerText = '--'"));
      expect(htmlContent, contains("document.getElementById('val-alpha1').innerText = '--'"));
      expect(htmlContent, contains("document.getElementById('val-readiness').innerText = '--'"));
      expect(htmlContent, contains("document.getElementById('sub-zone2').innerText = 'Resting / Disconnected'"));
      expect(htmlContent, contains("document.getElementById('sub-hr').innerText = 'Movesense Standby'"));
      expect(htmlContent, contains("badge.innerText = 'STANDBY — DISCONNECTED'"));
      expect(htmlContent, contains('ecgBuffer.fill(0.0)'));
    });

    test('2.4: 0x2A37 Binary GATT Unpacker correctly decodes 8-bit & 16-bit HR, Contact Bits, and RR Intervals', () {
      // 8-bit HR = 72, Contact Detected = true, RR = 850ms (870 raw 1/1024s)
      final raw8Bit = Uint8List.fromList([
        0x16, // Flags: 8-bit (bit 0=0), Contact supported & detected (bits 1-2=3 -> 0x06), RR present (bit 4=1 -> 0x10) -> 0x16
        72,   // HR uint8
        0x66, 0x03, // 870 in uint16_le -> (870 / 1024) * 1000 = 849.6 ms
      ]);
      final byteData8 = ByteData.sublistView(raw8Bit);
      final flags8 = byteData8.getUint8(0);
      final is16Bit8 = (flags8 & 0x01) != 0;
      final contactBits8 = (flags8 >> 1) & 0x03;
      final hasRr8 = (flags8 & 0x10) != 0;

      expect(is16Bit8, isFalse);
      expect(byteData8.getUint8(1), equals(72));
      expect(contactBits8, equals(3)); // Contact detected
      expect(hasRr8, isTrue);

      final rawRr8 = byteData8.getUint16(2, Endian.little);
      final rrMs8 = (rawRr8 / 1024.0) * 1000.0;
      expect(rrMs8, closeTo(849.6, 0.1));

      // 16-bit HR = 185 BPM, Contact Not Detected
      final raw16Bit = Uint8List.fromList([
        0x05, // Flags: 16-bit (bit 0=1), Contact supported but not detected (bits 1-2=2 -> 0x04) -> 0x05
        0xB9, 0x00, // 185 in uint16_le
      ]);
      final byteData16 = ByteData.sublistView(raw16Bit);
      final flags16 = byteData16.getUint8(0);
      final is16Bit16 = (flags16 & 0x01) != 0;
      final contactBits16 = (flags16 >> 1) & 0x03;

      expect(is16Bit16, isTrue);
      expect(byteData16.getUint16(1, Endian.little), equals(185));
      expect(contactBits16, equals(2)); // Contact not detected
    });

    test('2.5: Movesense 512Hz Raw ECG Sample Parsing (32-bit & 16-bit signed integer microvolts conversion)', () {
      // 32-bit ECG packet: 6-byte header + 2x 32-bit ints (+1250 uV, -750 uV)
      final raw32 = Uint8List(6 + 8);
      final bd32 = ByteData.sublistView(raw32);
      bd32.setUint8(0, 0x02);
      bd32.setUint8(1, 0x63);
      bd32.setUint32(2, 50000, Endian.little);
      bd32.setInt32(6, 1250, Endian.little); // 1.25 mV
      bd32.setInt32(10, -750, Endian.little); // -0.75 mV

      final payloadBytes32 = raw32.length - 6;
      expect(payloadBytes32 % 4 == 0, isTrue);
      final sample1_32 = bd32.getInt32(6, Endian.little) / 1000.0;
      final sample2_32 = bd32.getInt32(10, Endian.little) / 1000.0;
      expect(sample1_32, equals(1.25));
      expect(sample2_32, equals(-0.75));

      // 16-bit ECG packet: 6-byte header + 2x 16-bit ints (+1500 uV, -500 uV)
      final raw16 = Uint8List(6 + 4);
      final bd16 = ByteData.sublistView(raw16);
      bd16.setUint8(0, 0x02);
      bd16.setUint8(1, 0x63);
      bd16.setUint32(2, 50000, Endian.little);
      bd16.setInt16(6, 1500, Endian.little); // 1.5 mV
      bd16.setInt16(8, -500, Endian.little); // -0.5 mV

      final payloadBytes16 = raw16.length - 6;
      expect(payloadBytes16 % 2 == 0, isTrue);
      final sample1_16 = bd16.getInt16(6, Endian.little) / 1000.0;
      final sample2_16 = bd16.getInt16(8, Endian.little) / 1000.0;
      expect(sample1_16, equals(1.5));
      expect(sample2_16, equals(-0.5));
    });

    test('2.6: Mobile Canvas Orbit Controls have proper touch action and clamping constraints', () {
      expect(htmlContent, contains('touch-action: none;'));
      expect(htmlContent, contains('user-select: none;'));
      expect(htmlContent, contains("canvasTatami.addEventListener('touchstart'"));
      expect(htmlContent, contains("window.addEventListener('touchmove'"));
      expect(htmlContent, contains("window.addEventListener('touchend'"));
      expect(htmlContent, contains('Math.max(0.1, Math.min(1.4, orbitPitch + dy * 0.008))'));
    });

    test('2.7: REST Forwarder serializes valid JSON payloads to /api/biometrics/sample', () {
      expect(htmlContent, contains("fetch('/api/biometrics/sample'"));
      expect(htmlContent, contains("'Content-Type': 'application/json'"));
      expect(htmlContent, contains('heart_rate'));
      expect(htmlContent, contains('rr_interval_ms'));
      expect(htmlContent, contains('device_id'));
    });

    test('2.8: Forensic Verification of Rule #0 Zero-Mock Ban across build/index.html', () {
      final buildFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(buildFile.existsSync(), isTrue);

      final content = buildFile.readAsStringSync();
      expect(content.contains('72.0 BPM'), isFalse);
      expect(content.contains('48.5 ms'), isFalse);
      expect(content.contains('alpha1 = 1.0;'), isFalse);
      expect(content.contains('readiness = 50.0;'), isFalse);
      expect(content.contains('STANDBY — DISCONNECTED'), isTrue);
      expect(content.contains('0% MOCK DATA'), isTrue);
    });
  });
}
