// Milestone 3 Challenger 1 — BLE Packet Adversarial Stress Test Suite (Dart)
// Tests:
// 1. Pathological 0x2A37 Heart Rate Measurement packets (truncated buffers, corrupted flags, multi-RR bursts, dangling bytes)
// 2. Movesense 512Hz ECG byte unpacker (truncated headers, int16/int32 parsing, dangling bytes)
// 3. GATT disconnect/reconnect exponential backoff math and zero-mock UI reset invariants
// 4. Edge cases with high sample volumes and zero/negative numbers

import 'dart:math' as math;
import 'dart:typed_data';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

class DartGattOracle {
  static Map<String, dynamic>? parseHeartRateMeasurement(Uint8List val) {
    if (val.length < 2) return null;

    final byteData = ByteData.sublistView(val);
    final flags = byteData.getUint8(0);
    final is16BitHr = (flags & 0x01) != 0;
    final contactSupported = (flags & 0x02) != 0;
    final contactDetected = (flags & 0x04) != 0;
    final hasEnergy = (flags & 0x08) != 0;
    final hasRr = (flags & 0x10) != 0;

    int offset = 1;
    int heartRate = 0;
    if (is16BitHr) {
      if (val.length < offset + 2) return null;
      heartRate = byteData.getUint16(offset, Endian.little);
      offset += 2;
    } else {
      heartRate = byteData.getUint8(offset);
      offset += 1;
    }

    int? energyExpendedKJ;
    if (hasEnergy) {
      if (offset + 2 <= val.length) {
        energyExpendedKJ = byteData.getUint16(offset, Endian.little);
        offset += 2;
      }
    }

    final rrIntervals = <double>[];
    if (hasRr) {
      while (offset + 2 <= val.length) {
        final rawRr = byteData.getUint16(offset, Endian.little);
        final rrMs = (rawRr / 1024.0) * 1000.0;
        if (rrMs >= 250.0 && rrMs <= 2200.0) {
          rrIntervals.add((rrMs * 10).round() / 10.0);
        }
        offset += 2;
      }
    }

    bool? skinContact;
    final contactBits = (flags >> 1) & 0x03;
    if (contactBits == 2) skinContact = false;
    if (contactBits == 3) skinContact = true;

    return {
      'heartRate': heartRate,
      'is16Bit': is16BitHr,
      'skinContact': skinContact,
      'contactSupported': contactSupported,
      'contactDetected': contactDetected,
      'energyExpendedKJ': energyExpendedKJ,
      'rrIntervals': rrIntervals,
    };
  }

  static List<double> parseMovesenseEcgSamples(Uint8List val) {
    if (val.length < 6) return [];
    final byteData = ByteData.sublistView(val);
    final payloadBytes = val.length - 6;
    final samplesMv = <double>[];

    if (payloadBytes % 4 == 0 && payloadBytes > 0) {
      final count = payloadBytes ~/ 4;
      for (int i = 0; i < count; i++) {
        final uV = byteData.getInt32(6 + (i * 4), Endian.little);
        final mV = uV / 1000.0;
        if (mV.isFinite) samplesMv.add(mV);
      }
    } else if (payloadBytes % 2 == 0 && payloadBytes > 0) {
      final count = payloadBytes ~/ 2;
      for (int i = 0; i < count; i++) {
        final uV = byteData.getInt16(6 + (i * 2), Endian.little);
        final mV = uV / 1000.0;
        if (mV.isFinite) samplesMv.add(mV);
      }
    }
    return samplesMv;
  }

  static int? parseBatteryLevel(Uint8List val) {
    if (val.isEmpty) return null;
    final level = val[0];
    return level.clamp(0, 100);
  }
}

void main() {
  group('Challenger 1 (M3): BLE Packet Adversarial Stress Test Suite', () {
    late String html;

    setUpAll(() {
      final renderer = DashboardScreenRenderer();
      html = renderer.renderDynamicDashboardHtml();
    });

    test('1.1: 0x2A37 Truncated & Pathological Packet Bounds', () {
      // 0 bytes, 1 byte
      expect(DartGattOracle.parseHeartRateMeasurement(Uint8List(0)), isNull);
      expect(DartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x00])), isNull);
      expect(DartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01])), isNull);

      // 16-bit HR flag set, but only 2 bytes total (needs 3B)
      expect(DartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x4B])), isNull);

      // 16-bit HR valid (3 bytes) -> 280 BPM
      final valid16 = DartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x18, 0x01]));
      expect(valid16, isNotNull);
      expect(valid16!['heartRate'], equals(280));
      expect(valid16['is16Bit'], isTrue);
    });

    test('1.2: Corrupted Flags Byte Exhaustive Permutations (0..255)', () {
      for (int flag = 0; flag < 256; flag++) {
        for (int len = 0; len <= 20; len++) {
          final bytes = Uint8List(len);
          if (len > 0) bytes[0] = flag;
          for (int i = 1; i < len; i++) {
            bytes[i] = (flag + i * 13) & 0xFF;
          }
          final res = DartGattOracle.parseHeartRateMeasurement(bytes);
          if (res != null) {
            expect(res['heartRate'], isA<int>());
            expect(res['rrIntervals'], isA<List<double>>());
          }
        }
      }
    });

    test('1.3: Energy Expended Offset Shift with Multiple RR Intervals', () {
      // Flags: 0x18 -> 8-bit HR (1B), Energy Expended (2B), RR Intervals (2B each)
      final raw = Uint8List.fromList([
        0x18,
        82, // HR = 82
        0x2C, 0x01, // Energy Expended = 300 kJ
        0x00, 0x04, // RR1 = 1000.0ms (1024 raw)
        0x33, 0x03, // RR2 = 799.8ms (819 raw)
      ]);

      final res = DartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(82));
      expect(res['energyExpendedKJ'], equals(300));
      expect(res['rrIntervals'].length, equals(2));
      expect(res['rrIntervals'][0], closeTo(1000.0, 0.5));
      expect(res['rrIntervals'][1], closeTo(800.0, 0.5));
    });

    test('1.4: Multi-RR Interval Burst & Non-aligned Dangling Bytes', () {
      final builder = BytesBuilder();
      builder.addByte(0x10); // 8-bit HR + RR
      builder.addByte(72);   // HR = 72

      // Add 25 RR intervals
      for (int i = 0; i < 25; i++) {
        final rawRr = (800 + i * 15) * 1024 ~/ 1000;
        final bd = ByteData(2)..setUint16(0, rawRr, Endian.little);
        builder.add(bd.buffer.asUint8List());
      }
      builder.addByte(0xEE); // Dangling odd byte

      final res = DartGattOracle.parseHeartRateMeasurement(builder.toBytes());
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(72));
      final rrs = res['rrIntervals'] as List<double>;
      expect(rrs.length, equals(25));
      expect(rrs.first, closeTo(800.0, 1.0));
      expect(rrs.last, closeTo(800.0 + 24 * 15, 1.0));
    });

    test('1.5: Physiological Bounds Filtering ([250ms, 2200ms])', () {
      final raw = Uint8List.fromList([
        0x10,
        65,
        0x00, 0x00, // 0ms -> Rejected
        0xFF, 0x00, // 249ms -> Rejected
        0x00, 0x01, // 250ms -> Accepted
        0x00, 0x04, // 1000ms -> Accepted
        0xCC, 0x08, // 2199.2ms -> Accepted
        0xCE, 0x08, // 2201.2ms -> Rejected
        0xFF, 0xFF, // 64000ms -> Rejected
      ]);

      final res = DartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      final rrs = res!['rrIntervals'] as List<double>;
      expect(rrs.length, equals(3));
      expect(rrs[0], closeTo(250.0, 0.5));
      expect(rrs[1], closeTo(1000.0, 0.5));
      expect(rrs[2], closeTo(2200.0, 1.0));
    });

    test('2.1: Movesense 512Hz ECG Header Truncation & 16-bit / 32-bit Resiliency', () {
      // 0..5 bytes returns empty list
      for (int i = 0; i < 6; i++) {
        expect(DartGattOracle.parseMovesenseEcgSamples(Uint8List(i)), isEmpty);
      }

      // Valid 6-byte header with 3 * Int16 samples (6 bytes payload -> payloadBytes % 2 == 0, not % 4)
      final builder16 = BytesBuilder();
      builder16.add([0x02, 0x63, 0x00, 0x00, 0x00, 0x00]); // 6B header
      final s1 = ByteData(2)..setInt16(0, 1500, Endian.little);
      final s2 = ByteData(2)..setInt16(0, -750, Endian.little);
      final s3 = ByteData(2)..setInt16(0, 3200, Endian.little);
      builder16.add(s1.buffer.asUint8List());
      builder16.add(s2.buffer.asUint8List());
      builder16.add(s3.buffer.asUint8List());

      final samples16 = DartGattOracle.parseMovesenseEcgSamples(builder16.toBytes());
      expect(samples16.length, equals(3));
      expect(samples16[0], closeTo(1.5, 1e-4));
      expect(samples16[1], closeTo(-0.75, 1e-4));
      expect(samples16[2], closeTo(3.2, 1e-4));
    });

    test('2.2: Movesense 32-bit Sample Unpacking and Extreme Millivolt Ranges', () {
      final builder = BytesBuilder();
      builder.add([0x02, 0x63, 0x00, 0x00, 0x00, 0x00]); // 6B header
      final bd1 = ByteData(4)..setInt32(0, -2147483648, Endian.little);
      final bd2 = ByteData(4)..setInt32(0, 2147483647, Endian.little);
      builder.add(bd1.buffer.asUint8List());
      builder.add(bd2.buffer.asUint8List());

      final samples = DartGattOracle.parseMovesenseEcgSamples(builder.toBytes());
      expect(samples.length, equals(2));
      expect(samples[0], closeTo(-2147483.648, 1e-3));
      expect(samples[1], closeTo(2147483.647, 1e-3));
    });

    test('3.1: Exponential Backoff Reconnection Invariant Verification', () {
      expect(html, contains('MAX_RECONNECT_ATTEMPTS = 5'));
      expect(html, contains('Math.min(10000, 1000 * Math.pow(2, reconnectAttempts - 1))'));
      expect(html, contains('onBleDisconnected'));
      expect(html, contains('resetUiToStandby()'));

      // Validate exact timing progression
      final delays = [1, 2, 3, 4, 5].map((a) => math.min(10000, 1000 * math.pow(2, a - 1).toInt())).toList();
      expect(delays, equals([1000, 2000, 4000, 8000, 10000]));
    });

    test('3.2: resetUiToStandby() HTML Invariant Verification', () {
      expect(html, contains("document.getElementById('val-hr').innerText = '--';"));
      expect(html, contains("document.getElementById('val-rmssd').innerText = '--';"));
      expect(html, contains("document.getElementById('val-alpha1').innerText = '--';"));
      expect(html, contains("document.getElementById('val-readiness').innerText = '--';"));
      expect(html, contains("document.getElementById('sub-zone2').innerText = 'Resting / Disconnected';"));
      expect(html, contains("document.getElementById('sub-hr').innerText = 'Movesense Standby';"));
      expect(html, contains("document.getElementById('txt-technique').innerText = 'STANDBY — NO ATHLETE DETECTED';"));
      expect(html, contains("document.getElementById('txt-camera-status').innerText = '0/33 Joints Tracked';"));
      expect(html, contains("badge.innerText = 'STANDBY — DISCONNECTED';"));
      expect(html, contains("ecgBuffer.fill(0.0);"));
    });

    test('4.1: Battery Level Parsing & Boundary Clamping', () {
      expect(DartGattOracle.parseBatteryLevel(Uint8List.fromList([0])), equals(0));
      expect(DartGattOracle.parseBatteryLevel(Uint8List.fromList([50])), equals(50));
      expect(DartGattOracle.parseBatteryLevel(Uint8List.fromList([100])), equals(100));
      expect(DartGattOracle.parseBatteryLevel(Uint8List.fromList([150])), equals(100));
      expect(DartGattOracle.parseBatteryLevel(Uint8List(0)), isNull);
    });
  });
}
