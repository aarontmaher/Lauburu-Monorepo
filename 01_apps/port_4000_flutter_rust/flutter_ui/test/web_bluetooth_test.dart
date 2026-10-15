// Web Bluetooth Movesense Ingestion & Binary Protocol Test Suite — Milestone 3
// Rigorous verification of Bluetooth SIG HRS (0x180D/0x2A37), Battery (0x180F/0x2A19),
// Movesense Custom 512Hz Raw ECG (34800001/34800002), Kamath Filtering, and Teardown.

import 'dart:io';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

/// Dart Mirror of JavaScript Web Bluetooth GATT Parser Engine
class WebBluetoothGattDecoder {
  static Map<String, dynamic>? parseHeartRateMeasurement(Uint8List bytes) {
    if (bytes.length < 2) return null;

    final byteData = ByteData.sublistView(bytes);
    final flags = byteData.getUint8(0);
    final is16Bit = (flags & 0x01) != 0;
    final contactSupported = (flags & 0x02) != 0;
    final contactDetected = (flags & 0x04) != 0;
    final hasEnergy = (flags & 0x08) != 0;
    final hasRr = (flags & 0x10) != 0;

    int offset = 1;
    int heartRate = 0;
    if (is16Bit) {
      if (bytes.length < offset + 2) return null;
      heartRate = byteData.getUint16(offset, Endian.little);
      offset += 2;
    } else {
      heartRate = byteData.getUint8(offset);
      offset += 1;
    }

    int? energyExpendedKJ;
    if (hasEnergy) {
      if (offset + 2 <= bytes.length) {
        energyExpendedKJ = byteData.getUint16(offset, Endian.little);
        offset += 2;
      }
    }

    final rrIntervals = <double>[];
    if (hasRr) {
      while (offset + 2 <= bytes.length) {
        final rawRr = byteData.getUint16(offset, Endian.little);
        final rrMs = (rawRr / 1024.0) * 1000.0;
        // Kamath physiological window filter (250ms - 2200ms)
        if (rrMs >= 250.0 && rrMs <= 2200.0) {
          rrIntervals.add(double.parse(rrMs.toStringAsFixed(1)));
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
      'is16Bit': is16Bit,
      'skinContact': skinContact,
      'contactSupported': contactSupported,
      'contactDetected': contactDetected,
      'energyExpendedKJ': energyExpendedKJ,
      'rrIntervals': rrIntervals,
    };
  }

  static int? parseBatteryLevel(Uint8List bytes) {
    if (bytes.isEmpty) return null;
    final val = bytes[0];
    return val.clamp(0, 100);
  }

  static List<double> parseMovesenseEcgSamples(Uint8List bytes, {bool is16Bit = false}) {
    if (bytes.length < 6) return [];
    final byteData = ByteData.sublistView(bytes);
    final payloadBytes = bytes.length - 6;
    final samplesMv = <double>[];

    if (!is16Bit && payloadBytes % 4 == 0 && payloadBytes > 0) {
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

  static List<double> applyKamathFilter(List<double> rrList) {
    if (rrList.length < 2) return List<double>.from(rrList);
    final clean = <double>[rrList[0]];
    for (int i = 1; i < rrList.length; i++) {
      final prev = clean.last;
      final curr = rrList[i];
      if (prev > 0 && ((curr - prev).abs() / prev) <= 0.20) {
        clean.add(curr);
      } else {
        clean.add(prev);
      }
    }
    return clean;
  }

  static double? computeRmssd(List<double> rrList) {
    if (rrList.length < 2) return null;
    double sumSq = 0.0;
    for (int i = 1; i < rrList.length; i++) {
      final diff = rrList[i] - rrList[i - 1];
      sumSq += diff * diff;
    }
    return math.sqrt(sumSq / (rrList.length - 1));
  }

  static double? computeDfaAlpha1(List<double> rrList) {
    final n = rrList.length;
    if (n < 16) return null;
    final mean = rrList.reduce((a, b) => a + b) / n;
    double cumsum = 0;
    final y = <double>[];
    for (int i = 0; i < n; i++) {
      cumsum += rrList[i] - mean;
      y.add(cumsum);
    }
    const scales = [4, 6, 8, 12, 16];
    final logScales = <double>[];
    final logFlucts = <double>[];
    for (final scale in scales) {
      if (scale >= n) continue;
      final segments = n ~/ scale;
      if (segments == 0) continue;
      double sumSqErr = 0;
      int totalPoints = 0;
      for (int s = 0; s < segments; s++) {
        final start = s * scale;
        final seg = y.sublist(start, start + scale);
        final segLen = seg.length;
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < segLen; i++) {
          sumX += i;
          sumY += seg[i];
          sumXY += i * seg[i];
          sumX2 += i * i;
        }
        final denom = (segLen * sumX2 - sumX * sumX);
        final slope = denom != 0 ? (segLen * sumXY - sumX * sumY) / denom : 0.0;
        final intercept = (sumY - slope * sumX) / segLen;
        for (int i = 0; i < segLen; i++) {
          final trend = slope * i + intercept;
          final diff = seg[i] - trend;
          sumSqErr += diff * diff;
          totalPoints++;
        }
      }
      if (totalPoints > 0) {
        final fluct = math.sqrt(sumSqErr / totalPoints);
        if (fluct > 1e-5) {
          logScales.add(math.log(scale.toDouble()));
          logFlucts.add(math.log(fluct));
        }
      }
    }
    if (logScales.length < 2) return null;
    double sX = 0, sY = 0, sXY = 0, sX2 = 0;
    final count = logScales.length;
    for (int i = 0; i < count; i++) {
      sX += logScales[i];
      sY += logFlucts[i];
      sXY += logScales[i] * logFlucts[i];
      sX2 += logScales[i] * logScales[i];
    }
    final d = count * sX2 - sX * sX;
    return d != 0 ? (count * sXY - sX * sY) / d : 1.0;
  }

  static double? computeReadinessScore(double? hrVal, double? rmssdVal, double? alpha1Val) {
    if (hrVal == null || hrVal <= 0 || rmssdVal == null || rmssdVal <= 0) return null;
    final hrvPart = ((rmssdVal - 15.0) / 65.0).clamp(0.0, 1.0) * 50.0;
    final hrPart = ((85.0 - hrVal) / 40.0).clamp(0.0, 1.0) * 30.0;
    double dfaPart = 5.0;
    if (alpha1Val != null) {
      if (alpha1Val >= 0.9 && alpha1Val <= 1.3) {
        dfaPart = 20.0;
      } else if (alpha1Val > 0.75) {
        dfaPart = 15.0;
      }
    }
    return (hrvPart + hrPart + dfaPart).clamp(0.0, 100.0);
  }

  static Uint8List createWhiteboardSubscriptionPacket(String path, {int refId = 0x01}) {
    final pathBytes = path.codeUnits;
    final packet = Uint8List(2 + pathBytes.length);
    packet[0] = 0x01; // WB Subscribe opcode
    packet[1] = refId;
    packet.setRange(2, packet.length, pathBytes);
    return packet;
  }
}

void main() {
  group('Web Bluetooth Movesense Ingestion (Milestone 3 Core)', () {
    test('1.1: Standard Bluetooth SIG 0x2A37 8-bit Heart Rate Parsing', () {
      // Flags = 0x00 (8-bit HR, no contact, no energy, no RR), HR = 75 BPM (0x4B)
      final raw = Uint8List.fromList([0x00, 0x4B]);
      final parsed = WebBluetoothGattDecoder.parseHeartRateMeasurement(raw);

      expect(parsed, isNotNull);
      expect(parsed!['heartRate'], equals(75));
      expect(parsed['is16Bit'], isFalse);
      expect(parsed['skinContact'], isNull);
      expect(parsed['energyExpendedKJ'], isNull);
      expect(parsed['rrIntervals'], isEmpty);
    });

    test('1.2: Standard Bluetooth SIG 0x2A37 16-bit Heart Rate Parsing (>255 BPM)', () {
      // Flags = 0x01 (16-bit HR, little endian), HR = 280 BPM (0x0118 -> [0x18, 0x01])
      final raw = Uint8List.fromList([0x01, 0x18, 0x01]);
      final parsed = WebBluetoothGattDecoder.parseHeartRateMeasurement(raw);

      expect(parsed, isNotNull);
      expect(parsed!['heartRate'], equals(280));
      expect(parsed['is16Bit'], isTrue);
      expect(parsed['rrIntervals'], isEmpty);
    });

    test('1.3: 0x2A37 Sensor Contact Bits Evaluation (Support & Detection)', () {
      // Flags = 0x06 (8-bit HR, Contact Supported & Detected: bits 1-2 = 0b11), HR = 68 BPM
      final contactOk = Uint8List.fromList([0x06, 0x44]);
      final parsedOk = WebBluetoothGattDecoder.parseHeartRateMeasurement(contactOk);
      expect(parsedOk!['skinContact'], isTrue);
      expect(parsedOk['heartRate'], equals(68));

      // Flags = 0x04 (8-bit HR, Contact Supported but NOT Detected: bits 1-2 = 0b10), HR = 65 BPM
      final noContact = Uint8List.fromList([0x04, 0x41]);
      final parsedNo = WebBluetoothGattDecoder.parseHeartRateMeasurement(noContact);
      expect(parsedNo!['skinContact'], isFalse);
    });

    test('1.4: 0x2A37 Dynamic Offset Parsing with Energy Expended and Multiple RR Intervals', () {
      // Flags = 0x19 (16-bit HR + Energy Expended + RR-Intervals)
      // Byte 0: 0x19
      // Bytes 1..2: HR = 144 BPM (0x0090 -> [0x90, 0x00])
      // Bytes 3..4: Energy = 420 kJ (0x01A4 -> [0xA4, 0x01])
      // Bytes 5..6: RR1 = 1024 raw (1000.0 ms -> [0x00, 0x04])
      // Bytes 7..8: RR2 = 819 raw (800.0 ms -> [0x33, 0x03])
      final raw = Uint8List.fromList([
        0x19,
        0x90, 0x00,
        0xA4, 0x01,
        0x00, 0x04,
        0x33, 0x03,
      ]);

      final parsed = WebBluetoothGattDecoder.parseHeartRateMeasurement(raw);
      expect(parsed, isNotNull);
      expect(parsed!['heartRate'], equals(144));
      expect(parsed['is16Bit'], isTrue);
      expect(parsed['energyExpendedKJ'], equals(420));
      expect(parsed['rrIntervals'].length, equals(2));
      expect(parsed['rrIntervals'][0], closeTo(1000.0, 0.5));
      expect(parsed['rrIntervals'][1], closeTo(799.8, 0.5));
    });

    test('1.5: Kamath Physiological RR Filter and Outlier Rejection', () {
      // Physiological bounds: 250ms (240 BPM) to 2200ms (27.2 BPM)
      // Raw with out-of-bounds RR values: 150ms (too short) and 3500ms (too long)
      // Flags = 0x10 (8-bit HR + RR)
      // HR = 60 (0x3C)
      // RR1 = 153 raw (~149.4ms -> filtered out)
      // RR2 = 1024 raw (1000.0ms -> kept)
      // RR3 = 3584 raw (~3500.0ms -> filtered out)
      final raw = Uint8List.fromList([
        0x10,
        0x3C,
        0x99, 0x00, // ~149.4ms
        0x00, 0x04, // 1000.0ms
        0x00, 0x0E, // ~3500.0ms
      ]);

      final parsed = WebBluetoothGattDecoder.parseHeartRateMeasurement(raw);
      expect(parsed, isNotNull);
      expect(parsed!['rrIntervals'].length, equals(1));
      expect(parsed['rrIntervals'][0], closeTo(1000.0, 0.1));

      // Test Kamath adjacent RR delta filter (<= 20% deviation)
      final ectopicRrs = [1000.0, 1020.0, 1500.0, 1010.0]; // 1500 is +47% ectopic spike
      final clean = WebBluetoothGattDecoder.applyKamathFilter(ectopicRrs);
      expect(clean[0], equals(1000.0));
      expect(clean[1], equals(1020.0));
      expect(clean[2], equals(1020.0)); // Spike replaced with previous valid beat
      expect(clean[3], equals(1010.0));
    });

    test('1.6: Standard Battery Service 0x180F / 0x2A19 Parsing', () {
      final normal = Uint8List.fromList([87]);
      expect(WebBluetoothGattDecoder.parseBatteryLevel(normal), equals(87));

      final zero = Uint8List.fromList([0]);
      expect(WebBluetoothGattDecoder.parseBatteryLevel(zero), equals(0));

      final hundred = Uint8List.fromList([100]);
      expect(WebBluetoothGattDecoder.parseBatteryLevel(hundred), equals(100));

      final empty = Uint8List(0);
      expect(WebBluetoothGattDecoder.parseBatteryLevel(empty), isNull);
    });

    test('1.7: Movesense Whiteboard 512Hz Raw ECG 32-bit Microvolt Sample Unpacking', () {
      // Notification Packet:
      // Byte 0: Opcode 0x02
      // Byte 1: RefId 0x99
      // Bytes 2..5: Timestamp uint32_le = 100000 ms (0x000186A0)
      // Bytes 6..9: Sample 1 int32_le = 1500 uV (1.500 mV) -> 0x000005DC
      // Bytes 10..13: Sample 2 int32_le = -800 uV (-0.800 mV) -> 0xFFFFFCDE
      // Bytes 14..17: Sample 3 int32_le = 2450 uV (2.450 mV) -> 0x00000992
      // Bytes 18..21: Sample 4 int32_le = 0 uV (0.000 mV) -> 0x00000000
      final byteData = ByteData(22);
      byteData.setUint8(0, 0x02);
      byteData.setUint8(1, 0x99);
      byteData.setUint32(2, 100000, Endian.little);
      byteData.setInt32(6, 1500, Endian.little);
      byteData.setInt32(10, -800, Endian.little);
      byteData.setInt32(14, 2450, Endian.little);
      byteData.setInt32(18, 0, Endian.little);

      final samples = WebBluetoothGattDecoder.parseMovesenseEcgSamples(byteData.buffer.asUint8List());
      expect(samples.length, equals(4));
      expect(samples[0], closeTo(1.500, 0.001));
      expect(samples[1], closeTo(-0.800, 0.001));
      expect(samples[2], closeTo(2.450, 0.001));
      expect(samples[3], closeTo(0.000, 0.001));
    });

    test('1.8: Movesense Whiteboard 512Hz Raw ECG 16-bit Compact Microvolt Sample Unpacking', () {
      // Notification Packet with 16-bit signed samples:
      // Byte 0: Opcode 0x02, Byte 1: RefId 0x01
      // Bytes 2..5: Timestamp uint32_le
      // Bytes 6..7: Sample 1 int16_le = 1200 uV (1.200 mV)
      // Bytes 8..9: Sample 2 int16_le = -500 uV (-0.500 mV)
      // Bytes 10..11: Sample 3 int16_le = 750 uV (0.750 mV)
      final byteData = ByteData(12);
      byteData.setUint8(0, 0x02);
      byteData.setUint8(1, 0x01);
      byteData.setUint32(2, 50000, Endian.little);
      byteData.setInt16(6, 1200, Endian.little);
      byteData.setInt16(8, -500, Endian.little);
      byteData.setInt16(10, 750, Endian.little);

      final samples = WebBluetoothGattDecoder.parseMovesenseEcgSamples(byteData.buffer.asUint8List());
      expect(samples.length, equals(3));
      expect(samples[0], closeTo(1.200, 0.001));
      expect(samples[1], closeTo(-0.500, 0.001));
      expect(samples[2], closeTo(0.750, 0.001));
    });

    test('1.8b: Movesense Whiteboard 512Hz Raw ECG 16-bit 4-Byte (2 Samples) Unpacking', () {
      // 4-byte payload with 2 16-bit samples (10 bytes total)
      final byteData = ByteData(10);
      byteData.setUint8(0, 0x02);
      byteData.setUint8(1, 0x01);
      byteData.setUint32(2, 50000, Endian.little);
      byteData.setInt16(6, 1200, Endian.little);
      byteData.setInt16(8, -500, Endian.little);

      final samples = WebBluetoothGattDecoder.parseMovesenseEcgSamples(byteData.buffer.asUint8List(), is16Bit: true);
      expect(samples.length, equals(2));
      expect(samples[0], closeTo(1.200, 0.001));
      expect(samples[1], closeTo(-0.500, 0.001));
    });

    test('1.9: Movesense Whiteboard Subscription Packet Construction', () {
      final packet = WebBluetoothGattDecoder.createWhiteboardSubscriptionPacket('/Meas/ECG/512', refId: 0x99);
      expect(packet[0], equals(0x01)); // WB Subscribe Opcode
      expect(packet[1], equals(0x99)); // Ref ID
      final pathStr = String.fromCharCodes(packet.sublist(2));
      expect(pathStr, equals('/Meas/ECG/512'));
    });

    test('1.10: Client HRV (RMSSD), DFA-alpha1, and Readiness Math Invariants', () {
      // Generate synthetic physiological regular intervals with slight variability (~800ms / 75 BPM)
      final rrs = List<double>.generate(60, (i) => 800.0 + (i % 5) * 10.0 - 20.0);
      final rmssd = WebBluetoothGattDecoder.computeRmssd(rrs);
      expect(rmssd, isNotNull);
      expect(rmssd!, greaterThan(0.0));
      expect(rmssd, lessThan(100.0));

      final alpha1 = WebBluetoothGattDecoder.computeDfaAlpha1(rrs);
      expect(alpha1, isNotNull);
      expect(alpha1!, greaterThan(0.2));
      expect(alpha1, lessThan(2.0));

      final readiness = WebBluetoothGattDecoder.computeReadinessScore(75.0, rmssd, alpha1);
      expect(readiness, isNotNull);
      expect(readiness!, inInclusiveRange(0.0, 100.0));
    });

    test('1.11: HTML DOM & Web Bluetooth Bindings Static Verification', () {
      const renderer = DashboardScreenRenderer();
      final html = renderer.renderDynamicDashboardHtml();

      // Ensure Dual Service Discovery Filters exist in requestDevice
      expect(html, contains("services: ['heart_rate']"));
      expect(html, contains("'0000180d-0000-1000-8000-00805f9b34fb'"));
      expect(html, contains("'34800001-7185-4d5d-b431-b30e347d9634'"));
      expect(html, contains("'battery_service'"));
      expect(html, contains("'0000180f-0000-1000-8000-00805f9b34fb'"));
      expect(html, contains("'device_information'"));

      // Ensure Characteristic UUIDs exist for raw 512Hz ECG Whiteboard
      expect(html, contains("'34800002-7185-4d5d-b431-b30e347d9634'"));
      expect(html, contains("'/Meas/ECG/512'"));

      // Ensure Disconnect Teardown Listener exists
      expect(html, contains("bleDevice.addEventListener('gattserverdisconnected', onBleDisconnected);"));
      expect(html, contains("function resetUiToStandby()"));
      expect(html, contains("STANDBY — DISCONNECTED"));
    });

    test('1.12: Zero-Mock Rule #0 Invariant in Recompiled build/index.html', () {
      final htmlFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(htmlFile.existsSync(), isTrue);

      final content = htmlFile.readAsStringSync();
      expect(content.contains('72.0'), isFalse);
      expect(content.contains('48.5'), isFalse);
      expect(content.contains('alpha1 = 1.0;'), isFalse);
      expect(content.contains('readiness = 50.0;'), isFalse);
      expect(content, contains('0% MOCK DATA'));
      expect(content, contains('STANDBY — DISCONNECTED'));
    });
  });
}
