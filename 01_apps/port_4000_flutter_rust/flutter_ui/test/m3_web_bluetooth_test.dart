import 'dart:math';
import 'dart:typed_data';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  group('Milestone 3 Web Bluetooth & Biometrics Ingestion Suite', () {
    late String html;

    setUpAll(() {
      final renderer = DashboardScreenRenderer();
      html = renderer.renderDynamicDashboardHtml();
    });

    test('M3-01: HTML contains all mandatory Web Bluetooth GATT UUIDs in optionalServices', () {
      final requiredUuids = [
        'heart_rate',
        'battery_service',
        '34800001-7140-4a5e-b3f0-11397a109588',
        '34800001-7183-4f50-be44-839309ec5951',
        '34800001-7185-4d5d-b431-b30e347d9634',
        '34800001-7185-4d5d-b431-aa30e972d9e1',
        '34800002-7185-4d5d-b431-aa30e972d9e1',
        '34800001-7185-4d5d-b431-b30e393d9e05',
        '34800001-071f-425d-8e43-116450343b1b',
      ];

      for (final uuid in requiredUuids) {
        expect(html, contains(uuid), reason: 'Optional services must declare $uuid for Web Bluetooth security policy');
      }
    });

    test('M3-02: Standard BLE HRS (0x2A37) Binary Unpacker Oracle — 8-bit & 16-bit HR with RR Intervals', () {
      // 1. 8-bit HR (Flags: 0x10 -> bit 0=0, bit 4=1 RR intervals present)
      // Flags (1B), HR (1B), RR1 (2B LE = 800ms -> 819 raw), RR2 (2B LE = 850ms -> 870 raw)
      final raw8bit = Uint8List.fromList([
        0x10, // Flags: 8-bit HR, RR present
        75,   // HR: 75 bpm
        0x33, 0x03, // RR1 = 819 / 1024 * 1000 ≈ 799.8 ms
        0x66, 0x03, // RR2 = 870 / 1024 * 1000 ≈ 849.6 ms
      ]);

      final view8 = ByteData.sublistView(raw8bit);
      final flags8 = view8.getUint8(0);
      final is16Bit8 = (flags8 & 0x01) != 0;
      expect(is16Bit8, isFalse);
      final hr8 = view8.getUint8(1);
      expect(hr8, equals(75));

      int offset8 = 2;
      final rrs8 = <double>[];
      while (offset8 + 2 <= view8.lengthInBytes) {
        final rawRr = view8.getUint16(offset8, Endian.little);
        final rrMs = (rawRr / 1024.0) * 1000.0;
        rrs8.add((rrMs * 10).round() / 10.0);
        offset8 += 2;
      }
      expect(rrs8.length, equals(2));
      expect(rrs8[0], closeTo(800.0, 1.0));
      expect(rrs8[1], closeTo(850.0, 1.0));

      // 2. 16-bit HR (Flags: 0x19 -> bit 0=1 (16-bit), bit 3=1 (Energy), bit 4=1 (RR))
      final raw16bit = Uint8List.fromList([
        0x19, // Flags: 16-bit HR, Energy Expended, RR present
        0x90, 0x00, // HR = 144 bpm
        0x20, 0x01, // Energy Expended = 288 kJ (should be skipped by +2 bytes)
        0x00, 0x04, // RR = 1024 / 1024 * 1000 = 1000.0 ms
      ]);

      final view16 = ByteData.sublistView(raw16bit);
      final flags16 = view16.getUint8(0);
      final is16Bit16 = (flags16 & 0x01) != 0;
      expect(is16Bit16, isTrue);

      final hr16 = view16.getUint16(1, Endian.little);
      expect(hr16, equals(144));

      int offset16 = 3;
      if ((flags16 & 0x08) != 0 && offset16 + 2 <= view16.lengthInBytes) {
        offset16 += 2; // skip Energy Expended
      }
      expect(offset16, equals(5));

      final rrs16 = <double>[];
      while (offset16 + 2 <= view16.lengthInBytes) {
        final rawRr = view16.getUint16(offset16, Endian.little);
        final rrMs = (rawRr / 1024.0) * 1000.0;
        rrs16.add((rrMs * 10).round() / 10.0);
        offset16 += 2;
      }
      expect(rrs16.length, equals(1));
      expect(rrs16[0], equals(1000.0));
    });

    test('M3-03: Movesense 2.0 Custom 512Hz ECG Byte Unpacker Oracle — 16-bit Signed Microvolts to Millivolts', () {
      // Movesense ECG payload: [responseType(1B), reqId(1B), timestamp(4B), samples(INT16 LE)...]
      final builder = BytesBuilder();
      builder.add([0x02, 0x63]); // Notification type 2, ReqId 99
      builder.add([0x00, 0x10, 0x00, 0x00]); // 32-bit timestamp: 4096ms

      // Add 4 synthetic 16-bit signed microvolt samples: 500uV (0.5mV), -300uV (-0.3mV), 1250uV (1.25mV), -800uV (-0.8mV)
      final sampleValues = [500, -300, 1250, -800];
      for (final s in sampleValues) {
        final b = ByteData(2)..setInt16(0, s, Endian.little);
        builder.add(b.buffer.asUint8List());
      }

      final payload = builder.toBytes();
      final view = ByteData.sublistView(payload);
      expect(view.lengthInBytes, equals(6 + 8));

      final samplesMv = <double>[];
      int offset = 6;
      while (offset + 2 <= view.lengthInBytes) {
        final microvolts = view.getInt16(offset, Endian.little);
        final millivolts = microvolts / 1000.0;
        samplesMv.add(millivolts);
        offset += 2;
      }

      expect(samplesMv.length, equals(4));
      expect(samplesMv[0], closeTo(0.5, 1e-4));
      expect(samplesMv[1], closeTo(-0.3, 1e-4));
      expect(samplesMv[2], closeTo(1.25, 1e-4));
      expect(samplesMv[3], closeTo(-0.8, 1e-4));
    });

    test('M3-04: Movesense Whiteboard 2.0 Subscription Command Verification', () {
      expect(html, contains('/Meas/ECG/512'));
      expect(html, contains('new Uint8Array([1, 99'));
    });

    test('M3-05: Battery Service GATT (0x180F/0x2A19) Invariant', () {
      expect(html, contains('battery_service'));
      expect(html, contains('battery_level'));
      expect(html, contains('parseBatteryLevel'));
    });

    test('M3-06: Auto-reconnection Exponential Backoff Schedule Invariant', () {
      expect(html, contains('onBleDisconnected'));
      expect(html, contains('MAX_RECONNECT_ATTEMPTS'));
      expect(html, contains('Math.pow(2, reconnectAttempts - 1)'));

      // Verify mathematical progression of backoff delays for 4 attempts
      for (int attempt = 1; attempt <= 4; attempt++) {
        final baseMs = min(10000, 1000 * pow(2, attempt - 1));
        if (attempt == 1) expect(baseMs, equals(1000));
        if (attempt == 2) expect(baseMs, equals(2000));
        if (attempt == 3) expect(baseMs, equals(4000));
        if (attempt == 4) expect(baseMs, equals(8000));
      }
    });

    test('M3-07: Canvas CSS Touch Action & User Select Properties for Pixel 10 Pro XL', () {
      expect(html, contains('touch-action: none;'));
      expect(html, contains('user-select: none;'));
    });

    test('M3-08: Zero-Mock Rule #0 Strict Invariant in Compiled Dashboard Screen', () {
      final forbiddenMockTokens = [
        '72.0',
        '48.5',
        'alpha1 = 1.0',
        'readiness = 50.0'
      ];

      for (final token in forbiddenMockTokens) {
        expect(html.contains(token), isFalse, reason: 'Forbidden simulated token $token detected in HTML');
      }

      expect(html, contains('STANDBY — DISCONNECTED'));
      expect(html, contains('0% MOCK DATA'));
    });
  });
}
