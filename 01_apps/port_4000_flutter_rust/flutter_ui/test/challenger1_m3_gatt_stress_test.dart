// Milestone 3 Adversarial Challenger 1 — Empirical GATT Unpacker Stress Suite
// Evaluates HRS 0x2A37 and Movesense 512Hz ECG unpackers under pathological payloads,
// variable-length frames, energy expended offset shifts, dangling bytes, and 512Hz sample floods.

import 'dart:math' as math;
import 'dart:typed_data';
import 'package:test/test.dart';

/// Complete Reference GATT Oracle for Bluetooth SIG HRS (0x2A37) & Movesense 2.0
class FullGattOracle {
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

  static List<double> parseMovesenseEcgSamples(Uint8List bytes) {
    if (bytes.length < 6) return [];
    final byteData = ByteData.sublistView(bytes);
    final samplesMv = <double>[];

    // Resilient byte offset iteration: handles dangling odd bytes gracefully
    int offset = 6;
    while (offset + 2 <= bytes.length) {
      final uV = byteData.getInt16(offset, Endian.little);
      final mV = uV / 1000.0;
      if (mV.isFinite) samplesMv.add(mV);
      offset += 2;
    }
    return samplesMv;
  }
}

void main() {
  group('Challenger 1 M3: HRS 0x2A37 Binary Unpacker Empirical Stress', () {
    test('1.1: Pathological & Truncated HRS Packets', () {
      // 0 bytes
      expect(FullGattOracle.parseHeartRateMeasurement(Uint8List(0)), isNull);

      // 1 byte (flags only, missing HR)
      expect(FullGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x00])), isNull);
      expect(FullGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01])), isNull);

      // 2 bytes with 16-bit HR flag (needs 3 bytes minimum)
      expect(FullGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x4B])), isNull);

      // 3 bytes with 16-bit HR flag -> Valid (HR = 280 BPM)
      final valid16 = FullGattOracle.parseHeartRateMeasurement(Uint8List.fromList([0x01, 0x18, 0x01]));
      expect(valid16, isNotNull);
      expect(valid16!['heartRate'], equals(280));
      expect(valid16['is16Bit'], isTrue);
    });

    test('1.2: Variable Length Packets with 0..10 RR Intervals and Dangling Bytes', () {
      for (int numRr = 0; numRr <= 10; numRr++) {
        final builder = BytesBuilder();
        builder.addByte(0x10); // 8-bit HR + RR present
        builder.addByte(70);   // 70 BPM

        for (int i = 0; i < numRr; i++) {
          final rawRr = (800 + i * 10) * 1024 ~/ 1000;
          final bd = ByteData(2)..setUint16(0, rawRr, Endian.little);
          builder.add(bd.buffer.asUint8List());
        }

        // Add optional dangling 1-byte
        builder.addByte(0xEE);

        final parsed = FullGattOracle.parseHeartRateMeasurement(builder.toBytes());
        expect(parsed, isNotNull);
        expect(parsed!['heartRate'], equals(70));
        expect(parsed['rrIntervals'].length, equals(numRr));
      }
    });

    test('1.3: Energy Expended Offset Shift (Flags 0x18 and 0x19)', () {
      // Flags = 0x18 (8-bit HR + Energy Expended + RR)
      // HR = 75, Energy = 500 kJ (0x01F4), RR = 800ms (819 raw = 0x0333)
      final raw = Uint8List.fromList([
        0x18,
        75,
        0xF4, 0x01,
        0x33, 0x03,
      ]);

      final parsed = FullGattOracle.parseHeartRateMeasurement(raw);
      expect(parsed, isNotNull);
      expect(parsed!['heartRate'], equals(75));
      expect(parsed['energyExpendedKJ'], equals(500));
      expect(parsed['rrIntervals'].length, equals(1));
      expect(parsed['rrIntervals'][0], closeTo(800.0, 1.0));
    });

    test('1.4: Kamath Physiological Window Bound Invariants ([250ms, 2200ms])', () {
      final raw = Uint8List.fromList([
        0x10,
        60,
        // RR 1: 0ms -> Rejected
        0x00, 0x00,
        // RR 2: 249ms (255 raw) -> Rejected
        0xFF, 0x00,
        // RR 3: 250ms (256 raw) -> Accepted
        0x00, 0x01,
        // RR 4: 1000ms (1024 raw) -> Accepted
        0x00, 0x04,
        // RR 5: 2199.2ms (2252 raw) -> Accepted
        0xCC, 0x08,
        // RR 6: 2201.2ms (2254 raw) -> Rejected
        0xCE, 0x08,
        // RR 7: 63999ms (0xFFFF) -> Rejected
        0xFF, 0xFF,
      ]);

      final parsed = FullGattOracle.parseHeartRateMeasurement(raw);
      expect(parsed, isNotNull);
      final rrs = parsed!['rrIntervals'] as List<double>;
      expect(rrs.length, equals(3));
      expect(rrs[0], closeTo(250.0, 0.5));
      expect(rrs[1], closeTo(1000.0, 0.5));
      expect(rrs[2], closeTo(2200.0, 1.0));
    });

    test('1.5: High-Throughput Packet Flood (50,000 rapid packets)', () {
      final sw = Stopwatch()..start();
      for (int i = 0; i < 50000; i++) {
        final raw = Uint8List.fromList([
          0x10,
          (i % 100) + 50,
          0x00, 0x04, // 1000ms
          0x33, 0x03, // 800ms
        ]);
        final res = FullGattOracle.parseHeartRateMeasurement(raw);
        expect(res, isNotNull);
      }
      sw.stop();
      expect(sw.elapsedMilliseconds, lessThan(1000), reason: '50,000 packets must be unpacked in < 1 second');
    });
  });

  group('Challenger 1 M3: Movesense 512Hz ECG Unpacker Empirical Stress', () {
    test('2.1: Pathological & Truncated Movesense Headers (< 6 bytes)', () {
      for (int len = 0; len < 6; len++) {
        final truncated = Uint8List(len);
        expect(FullGattOracle.parseMovesenseEcgSamples(truncated), isEmpty);
      }
    });

    test('2.2: Extreme Microvolt Values and Accurate Millivolt Scaling', () {
      final builder = BytesBuilder();
      builder.add([0x02, 0x63, 0x00, 0x00, 0x00, 0x00]); // 6-byte header

      // Samples:
      // -32768 uV (-32.768 mV)
      // +32767 uV (+32.767 mV)
      // 0 uV (0.0 mV)
      // 1500 uV (1.5 mV)
      // -750 uV (-0.75 mV)
      final testValues = [-32768, 32767, 0, 1500, -750];
      for (final v in testValues) {
        final bd = ByteData(2)..setInt16(0, v, Endian.little);
        builder.add(bd.buffer.asUint8List());
      }

      final samples = FullGattOracle.parseMovesenseEcgSamples(builder.toBytes());
      expect(samples.length, equals(5));
      expect(samples[0], closeTo(-32.768, 1e-4));
      expect(samples[1], closeTo(32.767, 1e-4));
      expect(samples[2], closeTo(0.0, 1e-4));
      expect(samples[3], closeTo(1.5, 1e-4));
      expect(samples[4], closeTo(-0.75, 1e-4));
    });

    test('2.3: Dangling Odd Byte Handling', () {
      final builder = BytesBuilder();
      builder.add([0x02, 0x63, 0x00, 0x00, 0x00, 0x00]); // 6-byte header
      builder.add([0xDC, 0x05]); // 1500 uV (1.5 mV)
      builder.addByte(0xAA);     // 1 dangling byte

      final samples = FullGattOracle.parseMovesenseEcgSamples(builder.toBytes());
      expect(samples.length, equals(1));
      expect(samples[0], closeTo(1.5, 1e-4));
    });

    test('2.4: 512Hz Circular Ring Buffer Flood (100,000 samples)', () {
      const bufferSize = 512;
      final ringBuffer = Float32List(bufferSize);
      int writeIdx = 0;

      final sw = Stopwatch()..start();
      for (int packet = 0; packet < 6250; packet++) {
        // 16 samples per packet = 6250 * 16 = 100,000 samples
        final builder = BytesBuilder();
        builder.add([0x02, 0x63, 0x00, 0x00, 0x00, 0x00]);
        for (int s = 0; s < 16; s++) {
          final uV = (math.sin((packet * 16 + s) * 0.1) * 1200).round();
          final bd = ByteData(2)..setInt16(0, uV, Endian.little);
          builder.add(bd.buffer.asUint8List());
        }

        final samples = FullGattOracle.parseMovesenseEcgSamples(builder.toBytes());
        for (final smp in samples) {
          ringBuffer[writeIdx] = smp;
          writeIdx = (writeIdx + 1) % bufferSize;
        }
      }
      sw.stop();

      expect(ringBuffer.length, equals(512));
      expect(sw.elapsedMilliseconds, lessThan(1000), reason: '100k samples in < 1s');
    });
  });
}
