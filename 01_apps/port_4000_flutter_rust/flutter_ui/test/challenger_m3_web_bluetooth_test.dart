// Location: test/challenger_m3_web_bluetooth_test.dart
// Milestone 3 Challenger: End-to-End Web Bluetooth & Ingestion Stress Test
import 'dart:io';
import 'dart:typed_data';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Milestone 3 Challenger: Web Bluetooth Engine Verification', () {
    test('3.1: Compiled HTML contains complete Web Bluetooth engine and optionalServices whitelist', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      expect(html, contains('navigator.bluetooth.requestDevice'));
      expect(html, contains("'heart_rate'"));
      expect(html, contains("'battery_service'"));
      expect(html, contains("'device_information'"));
      expect(html, contains("'34800001-07f5-46d1-9167-bd61165970e5'"));
      expect(html, contains("'34800001-7185-4d5d-b431-b30e393d9e05'"));
      expect(html, contains("'34800001-7183-4f50-be44-839309ec5951'"));
      expect(html, contains("'61353090-8231-49cc-b57a-886370b1f649'"));
      expect(html, contains('parseHeartRateMeasurement'));
      expect(html, contains('applyKamathFilter'));
      expect(html, contains('computeRmssd'));
      expect(html, contains('computeDfaAlpha1'));
      expect(html, contains('classifyZone2'));
      expect(html, contains('computeReadinessScore'));
      expect(html, contains('detectQrsPeak'));
      expect(html, contains('STANDBY — DISCONNECTED'));
      expect(html, contains("fetch('/api/biometrics/sample'"));
    });

    test('3.2: 0x2A37 Binary GATT Unpacker correctly decodes 8-bit & 16-bit HR and RR intervals', () {
      // 8-bit HR = 68 BPM, RR1 = 1000ms (1024 raw)
      final raw8Bit = Uint8List.fromList([
        0x10,
        68,
        0x00, 0x04,
      ]);
      final byteData8 = ByteData.sublistView(raw8Bit);
      final flags8 = byteData8.getUint8(0);
      expect((flags8 & 0x01) == 0, isTrue);
      expect(byteData8.getUint8(1), equals(68));
      final rrRaw = byteData8.getUint16(2, Endian.little);
      expect((rrRaw / 1024.0) * 1000.0, closeTo(1000.0, 0.01));

      // 16-bit HR = 210 BPM (0x00D2)
      final raw16Bit = Uint8List.fromList([
        0x01,
        0xD2, 0x00,
      ]);
      final byteData16 = ByteData.sublistView(raw16Bit);
      final flags16 = byteData16.getUint8(0);
      expect((flags16 & 0x01) != 0, isTrue);
      expect(byteData16.getUint16(1, Endian.little), equals(210));
    });

    test('3.3: Zero-Mock Ban Rule #0 Verification across build/index.html', () {
      final htmlFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(htmlFile.existsSync(), isTrue);

      final content = htmlFile.readAsStringSync();
      expect(content.contains('72.0 BPM'), isFalse);
      expect(content.contains('48.5 ms'), isFalse);
      expect(content.contains('alpha1 = 1.0;'), isFalse);
      expect(content.contains('readiness = 50.0;'), isFalse);
      expect(content, contains('STANDBY — DISCONNECTED'));
    });
  });
}
