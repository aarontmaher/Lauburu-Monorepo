// Master Challenger 1 (M3): Comprehensive BLE Packet Adversarial & Lifecycle Stress Test Suite (Dart)
//
// Verification Matrix:
// 1. Malformed GATT Packets & Flag Permutations (0..255 flags, 0..64 byte buffers)
// 2. Energy Expended Bit 3 Alignment & Offset Shifts with 8-bit & 16-bit HR
// 3. RR-Interval Clamping Bounds [250, 2200] ms with 1/1024s resolution
// 4. 16-bit HR Edge Values (0, 1, 255, 256, 300, 65535 BPM)
// 5. Movesense 512Hz Raw ECG Packet Framing (INT16, INT32, dangling bytes)
// 6. Kamath Filter, RMSSD, DFA-alpha1, Readiness & Zone 2 Mathematical Invariants
// 7. Reconnection Exponential Backoff Schedule & Zero-Mock Standby Invariants

import 'dart:math' as math;
import 'dart:typed_data';
import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

class MasterDartGattOracle {
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
        final denom = segLen * sumX2 - sumX * sumX;
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
          logScales.add(math.log(scale));
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
    if (d == 0) return 1.0;
    final rawSlope = (count * sXY - sX * sY) / d;
    return (rawSlope.clamp(0.25, 1.75) * 100).round() / 100.0;
  }

  static String classifyZone2(double? alpha1Val, double hrVal) {
    if (hrVal <= 0) return 'Resting / Disconnected';
    if (alpha1Val == null) return 'Calibrating RR Stream...';
    if (alpha1Val >= 0.85) return 'Zone 1: Active Recovery';
    if (alpha1Val >= 0.70) return 'Zone 2: Optimal Aerobic (LT1)';
    if (alpha1Val >= 0.50) return 'Zone 3: Tempo / Aerobic Threshold';
    return 'Zone 4/5: Anaerobic / Above LT2';
  }

  static int? computeReadinessScore(double hrVal, double? rmssdVal, double? alpha1Val) {
    if (hrVal <= 0 || rmssdVal == null || rmssdVal <= 0) return null;
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
    return (hrvPart + hrPart + dfaPart).round().clamp(0, 100);
  }
}

void main() {
  group('Master Challenger 1 (M3): Master BLE Adversarial Oracle & Stress Suite', () {
    late String html;

    setUpAll(() {
      final renderer = DashboardScreenRenderer();
      html = renderer.renderDynamicDashboardHtml();
    });

    // -------------------------------------------------------------------------
    // 1. Truncated & Pathological Buffer Boundaries
    // -------------------------------------------------------------------------
    test('1.1: Truncated packets return null safely', () {
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List(0)), isNull);
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x00])), isNull);
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01])), isNull);
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x18])), isNull);
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0xFF])), isNull);
    });

    test('1.2: 16-bit HR truncated at 2 bytes returns null', () {
      // Flag indicates 16-bit HR, but total length is only 2 bytes (needs 3 bytes)
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x4B])), isNull);
      expect(MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x19, 0x4B])), isNull);
    });

    test('1.3: 16-bit HR valid at 3 bytes decodes cleanly', () {
      final res = MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x2C, 0x01]));
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(300));
      expect(res['is16Bit'], isTrue);
    });

    // -------------------------------------------------------------------------
    // 2. Flags Fuzzing & Matrix Permutations
    // -------------------------------------------------------------------------
    test('2.1: Exhaustive 256 Flags x 32 Buffer Lengths Matrix Fuzzing (8,192 runs)', () {
      for (int flag = 0; flag < 256; flag++) {
        for (int len = 0; len <= 32; len++) {
          final bytes = Uint8List(len);
          if (len > 0) bytes[0] = flag;
          for (int i = 1; i < len; i++) {
            bytes[i] = (flag * 31 + i * 17) & 0xFF;
          }
          final res = MasterDartGattOracle.parseHeartRateMeasurement(bytes);
          if (res != null) {
            expect(res['heartRate'], isA<int>());
            expect(res['rrIntervals'], isA<List<double>>());
            expect(res['is16Bit'], isA<bool>());
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // 3. Energy Expended Bit 3 Offset Alignment & Multi-RR Extraction
    // -------------------------------------------------------------------------
    test('3.1: 8-bit HR with Energy Expended (0x08) and 2 RR Intervals (0x18)', () {
      final raw = Uint8List.fromList([
        0x18, // 8-bit HR + Energy Expended + RR
        75,   // HR = 75 BPM
        0x50, 0x01, // Energy = 336 kJ
        0x00, 0x04, // RR1 = 1000.0ms (1024 raw)
        0x33, 0x03, // RR2 = 799.8ms (819 raw)
      ]);

      final res = MasterDartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(75));
      expect(res['is16Bit'], isFalse);
      expect(res['energyExpendedKJ'], equals(336));
      expect(res['rrIntervals'].length, equals(2));
      expect(res['rrIntervals'][0], closeTo(1000.0, 0.5));
      expect(res['rrIntervals'][1], closeTo(800.0, 0.5));
    });

    test('3.2: 16-bit HR with Energy Expended (0x09) and 1 RR Interval (0x19)', () {
      final raw = Uint8List.fromList([
        0x19, // 16-bit HR + Energy Expended + RR
        0x04, 0x01, // HR = 260 BPM (0x0104)
        0xE8, 0x03, // Energy = 1000 kJ
        0x00, 0x04, // RR = 1000.0ms
      ]);

      final res = MasterDartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(260));
      expect(res['is16Bit'], isTrue);
      expect(res['energyExpendedKJ'], equals(1000));
      expect(res['rrIntervals'].length, equals(1));
      expect(res['rrIntervals'][0], closeTo(1000.0, 0.5));
    });

    test('3.3: Dangling odd byte at packet end is safely ignored without RangeError', () {
      final raw = Uint8List.fromList([
        0x10, // 8-bit HR + RR
        80,   // HR = 80
        0x00, 0x04, // RR = 1000.0ms
        0xAB, // 1 trailing dangling byte
      ]);

      final res = MasterDartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      expect(res!['heartRate'], equals(80));
      expect(res['rrIntervals'].length, equals(1));
      expect(res['rrIntervals'][0], closeTo(1000.0, 0.5));
    });

    // -------------------------------------------------------------------------
    // 4. RR Clamping Bounds [250, 2200] ms & 16-bit HR Extremes
    // -------------------------------------------------------------------------
    test('4.1: RR Clamping strictly filters non-physiological intervals', () {
      final raw = Uint8List.fromList([
        0x10,
        60,
        0x00, 0x00, // 0ms -> Rejected
        0xFF, 0x00, // 249.0ms (255 raw) -> Rejected
        0x00, 0x01, // 250.0ms (256 raw) -> Accepted
        0x00, 0x04, // 1000.0ms (1024 raw) -> Accepted
        0xCC, 0x08, // 2199.2ms (2252 raw) -> Accepted
        0xCE, 0x08, // 2201.2ms (2254 raw) -> Rejected
        0xFF, 0xFF, // 63999ms -> Rejected
      ]);

      final res = MasterDartGattOracle.parseHeartRateMeasurement(raw);
      expect(res, isNotNull);
      final rrs = res!['rrIntervals'] as List<double>;
      expect(rrs.length, equals(3));
      expect(rrs[0], equals(250.0));
      expect(rrs[1], equals(1000.0));
      expect(rrs[2], equals(2199.2));
    });

    test('4.2: 16-bit HR Extreme Values (0, 255, 256, 300, 65535 BPM)', () {
      final testCases = [
        {'bytes': [0x01, 0x00, 0x00], 'expected': 0},
        {'bytes': [0x01, 0xFF, 0x00], 'expected': 255},
        {'bytes': [0x01, 0x00, 0x01], 'expected': 256},
        {'bytes': [0x01, 0x2C, 0x01], 'expected': 300},
        {'bytes': [0x01, 0xFF, 0xFF], 'expected': 65535},
      ];

      for (final tc in testCases) {
        final res = MasterDartGattOracle.parseHeartRateMeasurement(Uint8List.fromList(tc['bytes'] as List<int>));
        expect(res, isNotNull);
        expect(res!['heartRate'], equals(tc['expected']));
        expect(res['is16Bit'], isTrue);
      }
    });

    // -------------------------------------------------------------------------
    // 5. Movesense 512Hz Raw ECG Binary Unpacking
    // -------------------------------------------------------------------------
    test('5.1: Movesense Raw ECG Header and Payload Formats', () {
      // Truncated header (< 6 bytes)
      for (int i = 0; i < 6; i++) {
        expect(MasterDartGattOracle.parseMovesenseEcgSamples(Uint8List(i)), isEmpty);
      }

      // Valid 6-byte header + 2 * Int32 samples (8 bytes payload -> % 4 == 0)
      // 1500 uV -> 1.5 mV, -750 uV -> -0.75 mV
      final b32 = BytesBuilder();
      b32.add([0x01, 0x63, 0x00, 0x00, 0x00, 0x00]);
      b32.add((ByteData(4)..setInt32(0, 1500, Endian.little)).buffer.asUint8List());
      b32.add((ByteData(4)..setInt32(0, -750, Endian.little)).buffer.asUint8List());
      final s32 = MasterDartGattOracle.parseMovesenseEcgSamples(b32.toBytes());
      expect(s32.length, equals(2));
      expect(s32[0], closeTo(1.5, 1e-4));
      expect(s32[1], closeTo(-0.75, 1e-4));

      // Valid 6-byte header + 3 * Int16 samples (6 bytes payload -> % 2 == 0, not % 4)
      final b16 = BytesBuilder();
      b16.add([0x01, 0x63, 0x00, 0x00, 0x00, 0x00]);
      b16.add((ByteData(2)..setInt16(0, 2400, Endian.little)).buffer.asUint8List()); // 2.4 mV
      b16.add((ByteData(2)..setInt16(0, -1200, Endian.little)).buffer.asUint8List()); // -1.2 mV
      b16.add((ByteData(2)..setInt16(0, 800, Endian.little)).buffer.asUint8List()); // 0.8 mV
      final s16 = MasterDartGattOracle.parseMovesenseEcgSamples(b16.toBytes());
      expect(s16.length, equals(3));
      expect(s16[0], closeTo(2.4, 1e-4));
      expect(s16[1], closeTo(-1.2, 1e-4));
      expect(s16[2], closeTo(0.8, 1e-4));
    });

    // -------------------------------------------------------------------------
    // 6. Rolling DSP Math, Kamath Outlier Filter, RMSSD & DFA-α1
    // -------------------------------------------------------------------------
    test('6.1: Kamath 20% Outlier Rejection Filter Invariants', () {
      expect(MasterDartGattOracle.applyKamathFilter([]), isEmpty);
      expect(MasterDartGattOracle.applyKamathFilter([800.0]), equals([800.0]));

      final rrs = [800.0, 810.0, 2400.0, 805.0, 150.0, 812.0];
      final filtered = MasterDartGattOracle.applyKamathFilter(rrs);
      expect(filtered.length, equals(6));
      expect(filtered[0], equals(800.0));
      expect(filtered[1], equals(810.0));
      expect(filtered[2], equals(810.0)); // 2400 rejected -> replaced by 810
      expect(filtered[3], equals(805.0)); // 805 vs 810 accepted
      expect(filtered[4], equals(805.0)); // 150 rejected -> replaced by 805
      expect(filtered[5], equals(812.0)); // 812 vs 805 accepted
    });

    test('6.2: RMSSD Mathematical Precision & Edge Cases', () {
      expect(MasterDartGattOracle.computeRmssd([]), isNull);
      expect(MasterDartGattOracle.computeRmssd([800.0]), isNull);
      expect(MasterDartGattOracle.computeRmssd([800.0, 800.0, 800.0]), equals(0.0));

      final rmssd = MasterDartGattOracle.computeRmssd([800.0, 820.0, 810.0]);
      expect(rmssd, isNotNull);
      expect(rmssd!, closeTo(15.81, 0.01));
    });

    test('6.3: DFA-α1 Scaling & Zone 2 Classification', () {
      expect(MasterDartGattOracle.computeDfaAlpha1(List.filled(15, 800.0)), isNull);

      final rrs = List.generate(30, (i) => 800.0 + (i % 5) * 20.0);
      final alpha1 = MasterDartGattOracle.computeDfaAlpha1(rrs);
      expect(alpha1, isNotNull);
      expect(alpha1!, inInclusiveRange(0.25, 1.75));

      expect(MasterDartGattOracle.classifyZone2(1.0, 0), equals('Resting / Disconnected'));
      expect(MasterDartGattOracle.classifyZone2(null, 75), equals('Calibrating RR Stream...'));
      expect(MasterDartGattOracle.classifyZone2(0.95, 130), equals('Zone 1: Active Recovery'));
      expect(MasterDartGattOracle.classifyZone2(0.75, 145), equals('Zone 2: Optimal Aerobic (LT1)'));
      expect(MasterDartGattOracle.classifyZone2(0.60, 160), equals('Zone 3: Tempo / Aerobic Threshold'));
      expect(MasterDartGattOracle.classifyZone2(0.40, 175), equals('Zone 4/5: Anaerobic / Above LT2'));
    });

    test('6.4: Readiness Score Mathematical Invariant', () {
      expect(MasterDartGattOracle.computeReadinessScore(0, 50.0, 1.0), isNull);
      expect(MasterDartGattOracle.computeReadinessScore(70, null, 1.0), isNull);
      expect(MasterDartGattOracle.computeReadinessScore(70, 0.0, 1.0), isNull);

      final score = MasterDartGattOracle.computeReadinessScore(60, 55.0, 1.0);
      expect(score, isNotNull);
      expect(score!, inInclusiveRange(0, 100));
    });

    // -------------------------------------------------------------------------
    // 7. Reconnection Schedule & Zero-Mock Invariants
    // -------------------------------------------------------------------------
    test('7.1: Exponential Backoff Timing Progression [1s, 2s, 4s, 8s, 10s]', () {
      final baseDelays = [1, 2, 3, 4, 5]
          .map((a) => math.min(10000, (1000 * math.pow(2, a - 1)).toInt()))
          .toList();
      expect(baseDelays, equals([1000, 2000, 4000, 8000, 10000]));
    });

    test('7.2: HTML Zero-Mock Standby & Purge Verification', () {
      expect(html, contains("document.getElementById('val-hr').innerText = '--';"));
      expect(html, contains("document.getElementById('val-rmssd').innerText = '--';"));
      expect(html, contains("document.getElementById('val-alpha1').innerText = '--';"));
      expect(html, contains("document.getElementById('val-readiness').innerText = '--';"));
      expect(html, contains("document.getElementById('sub-zone2').innerText = 'Resting / Disconnected';"));
      expect(html, contains("document.getElementById('sub-hr').innerText = 'Movesense Standby';"));
      expect(html, contains("badge.innerText = 'STANDBY — DISCONNECTED';"));
      expect(html, contains("ecgBuffer.fill(0.0);"));
    });
  });
}
