// Location: test/web_bluetooth_gatt_test.dart
// Milestone 3 — Web Bluetooth GATT Parser & Protocol Invariants
import 'dart:typed_data';
import 'package:test/test.dart';

/// Pure Dart reference implementation of Bluetooth SIG HRS & BAS packet decoder
class HrsPacketResult {
  final int heartRate;
  final bool is16Bit;
  final bool? skinContact;
  final int? energyExpendedKJ;
  final List<double> rrIntervalsMs;

  const HrsPacketResult({
    required this.heartRate,
    required this.is16Bit,
    this.skinContact,
    this.energyExpendedKJ,
    required this.rrIntervalsMs,
  });
}

class HrsPacketParser {
  static HrsPacketResult? parse(Uint8List rawBytes) {
    if (rawBytes.length < 2) return null;
    final data = ByteData.sublistView(rawBytes);
    final flags = data.getUint8(0);

    final is16Bit = (flags & 0x01) != 0;
    int offset = 1;

    if (is16Bit && rawBytes.length < 3) return null;

    final heartRate = is16Bit ? data.getUint16(offset, Endian.little) : data.getUint8(offset);
    offset += is16Bit ? 2 : 1;

    bool? skinContact;
    final contactBits = (flags >> 1) & 0x03;
    if (contactBits == 2) skinContact = false;
    if (contactBits == 3) skinContact = true;

    int? energyExpended;
    if ((flags & 0x08) != 0) {
      if (offset + 2 <= rawBytes.length) {
        energyExpended = data.getUint16(offset, Endian.little);
        offset += 2;
      }
    }

    final rrIntervals = <double>[];
    if ((flags & 0x10) != 0) {
      while (offset + 2 <= rawBytes.length) {
        final rawRr = data.getUint16(offset, Endian.little);
        final rrMs = rawRr * (1000.0 / 1024.0);
        rrIntervals.add(rrMs);
        offset += 2;
      }
    }

    return HrsPacketResult(
      heartRate: heartRate,
      is16Bit: is16Bit,
      skinContact: skinContact,
      energyExpendedKJ: energyExpended,
      rrIntervalsMs: rrIntervals,
    );
  }

  static int? parseBattery(Uint8List rawBytes) {
    if (rawBytes.isEmpty) return null;
    final val = rawBytes[0];
    return val.clamp(0, 100);
  }
}

void main() {
  group('Milestone 3 — Web Bluetooth GATT Parser & Protocol Invariants', () {
    test('INV-1: 8-bit Heart Rate packet parsing', () {
      final packet = Uint8List.fromList([0x00, 0x48]); // 72 BPM
      final res = HrsPacketParser.parse(packet);
      expect(res, isNotNull);
      expect(res!.heartRate, 72);
      expect(res.is16Bit, isFalse);
      expect(res.skinContact, isNull);
      expect(res.rrIntervalsMs, isEmpty);
    });

    test('INV-2: 16-bit Heart Rate packet parsing (High BPM)', () {
      final packet = Uint8List.fromList([0x01, 0xE8, 0x03]); // 1000 BPM little-endian
      final res = HrsPacketParser.parse(packet);
      expect(res, isNotNull);
      expect(res!.heartRate, 1000);
      expect(res.is16Bit, isTrue);
    });

    test('INV-3 & INV-5: Sensor Contact & Energy Expended byte offset shift', () {
      final packet = Uint8List.fromList([0x0E, 0x50, 0x20, 0x01]); // 8-bit HR=80, Contact=true, EE=288 kJ
      final res = HrsPacketParser.parse(packet);
      expect(res, isNotNull);
      expect(res!.heartRate, 80);
      expect(res.skinContact, isTrue);
      expect(res.energyExpendedKJ, 288);
    });

    test('INV-4: Multiple RR-interval extraction (1/1024s resolution)', () {
      // Flags: 0x10 (8-bit HR, RR present), HR=75, RR1=1024 raw (1000ms), RR2=512 raw (500ms)
      final packet = Uint8List.fromList([0x10, 0x4B, 0x00, 0x04, 0x00, 0x02]);
      final res = HrsPacketParser.parse(packet);
      expect(res, isNotNull);
      expect(res!.heartRate, 75);
      expect(res.rrIntervalsMs.length, 2);
      expect(res.rrIntervalsMs[0], closeTo(1000.0, 0.01));
      expect(res.rrIntervalsMs[1], closeTo(500.0, 0.01));
    });

    test('INV-6: Battery Level parsing and boundary clamping', () {
      expect(HrsPacketParser.parseBattery(Uint8List.fromList([85])), 85);
      expect(HrsPacketParser.parseBattery(Uint8List.fromList([0])), 0);
      expect(HrsPacketParser.parseBattery(Uint8List.fromList([100])), 100);
      expect(HrsPacketParser.parseBattery(Uint8List.fromList([150])), 100); // Clamped
      expect(HrsPacketParser.parseBattery(Uint8List.fromList([])), isNull);
    });

    test('Pathological / Malformed Packets handled without exceptions', () {
      expect(HrsPacketParser.parse(Uint8List.fromList([])), isNull);
      expect(HrsPacketParser.parse(Uint8List.fromList([0x00])), isNull);
      expect(HrsPacketParser.parse(Uint8List.fromList([0x01, 0x50])), isNull); // 16-bit truncated
      
      // Odd trailing byte in RR sequence dropped safely
      final malformedRr = Uint8List.fromList([0x10, 0x4B, 0x00, 0x04, 0xFF]);
      final res = HrsPacketParser.parse(malformedRr);
      expect(res, isNotNull);
      expect(res!.rrIntervalsMs.length, 1);
      expect(res.rrIntervalsMs[0], closeTo(1000.0, 0.01));
    });
  });
}
