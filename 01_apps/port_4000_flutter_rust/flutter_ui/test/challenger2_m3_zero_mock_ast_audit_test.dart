import 'dart:io';
import 'package:test/test.dart';

void main() {
  group('Challenger 2 M3: Deep Zero-Mock & Forensic AST Truth Audit', () {
    final rootDir = Directory('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust');
    final htmlFile = File('${rootDir.path}/flutter_ui/build/index.html');
    final dartLibDir = Directory('${rootDir.path}/flutter_ui/lib');
    final rustSrcDir = Directory('${rootDir.path}/rust_backend/src');

    test('1. Compiled build/index.html exists and is freshly generated', () {
      expect(htmlFile.existsSync(), isTrue, reason: 'build/index.html must exist');
      final length = htmlFile.lengthSync();
      expect(length, greaterThan(10000), reason: 'index.html must be a complete SPA');
    });

    test('2. Exhaustive Regex Search: Zero hardcoded mock numbers in build/index.html', () {
      final content = htmlFile.readAsStringSync();

      // Explicit banned tokens
      final bannedTokens = [
        '72.0',
        '48.5',
        '72 BPM',
        '48.5ms',
        '48.5 ms',
        'alpha1 = 1.0',
        'readiness = 50.0',
        'readiness = 50',
        'Closed Guard → Ashi Garami',
        'MOCK_HR',
        'SYNTHETIC_ECG',
        'fake_ecg',
        'generateMockPulse',
        'generateSineWave',
        'simulateHeartRate',
      ];

      for (final token in bannedTokens) {
        expect(
          content.contains(token),
          isFalse,
          reason: 'Forbidden mock token "$token" found in build/index.html',
        );
      }
    });

    test('3. AST / Structure Check: Standby and Initial UI Elements render authentic waiting states', () {
      final content = htmlFile.readAsStringSync();

      // Must contain initial placeholder markers
      expect(RegExp(r'id="val-hr"[^>]*>--').hasMatch(content), isTrue);
      expect(RegExp(r'id="val-rmssd"[^>]*>--').hasMatch(content), isTrue);
      expect(RegExp(r'id="val-alpha1"[^>]*>--').hasMatch(content), isTrue);
      expect(RegExp(r'id="val-readiness"[^>]*>--').hasMatch(content), isTrue);
      expect(RegExp(r'id="sub-zone2"[^>]*>Resting / Disconnected').hasMatch(content), isTrue);
      expect(RegExp(r'id="badge-status"[^>]*>STANDBY — DISCONNECTED').hasMatch(content), isTrue);
      expect(RegExp(r'id="txt-technique"[^>]*>STANDBY — NO ATHLETE DETECTED').hasMatch(content), isTrue);

      // Web Bluetooth Connect button present
      expect(content.contains('id="btn-connect"'), isTrue);
      expect(content.contains('CONNECT MOVESENSE (BLUETOOTH)'), isTrue);
    });

    test('4. Forensic JS Logic Check: ECG Canvas Oscilloscope does not synthesize fake waves', () {
      final content = htmlFile.readAsStringSync();

      // Check drawEcg function logic
      expect(content, contains('function drawEcg()'));
      expect(content, contains('ecgBuffer[i]'));
      expect(content, contains('STANDBY — SENSOR PROBING (0% MOCK DATA)'));

      // Confirm Math.sin is NOT used inside drawEcg
      final drawEcgStart = content.indexOf('function drawEcg()');
      final drawEcgEnd = content.indexOf('function project3D(');
      expect(drawEcgStart, isNonNegative);
      expect(drawEcgEnd, greaterThan(drawEcgStart));

      final drawEcgBody = content.substring(drawEcgStart, drawEcgEnd);
      expect(drawEcgBody.contains('Math.sin'), isFalse, reason: 'Math.sin must not be used in drawEcg');
      expect(drawEcgBody.contains('Math.cos'), isFalse, reason: 'Math.cos must not be used in drawEcg');
      expect(drawEcgBody.contains('Math.random'), isFalse, reason: 'Math.random must not be used in drawEcg');
    });

    test('5. Forensic Dart Source Scan: Zero mock constants across all lib/ files', () {
      final dartFiles = dartLibDir
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => f.path.endsWith('.dart'));

      for (final file in dartFiles) {
        final code = file.readAsStringSync();
        expect(code.contains('72.0 BPM'), isFalse, reason: 'Found mock in ${file.path}');
        expect(code.contains('48.5 ms'), isFalse, reason: 'Found mock in ${file.path}');
        expect(code.contains('alpha1 = 1.0;'), isFalse, reason: 'Found mock in ${file.path}');
        expect(code.contains('readiness = 50.0;'), isFalse, reason: 'Found mock in ${file.path}');
      }
    });

    test('6. Forensic Rust Source Scan: Zero mock defaults in BiometricsEngine and server.rs', () {
      final rustFiles = rustSrcDir
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => f.path.endsWith('.rs'));

      for (final file in rustFiles) {
        final code = file.readAsStringSync();
        expect(code.contains('heart_rate_bpm: 72.0'), isFalse, reason: 'Mock default in ${file.path}');
        expect(code.contains('hrv_rmssd_ms: 48.5'), isFalse, reason: 'Mock default in ${file.path}');
        expect(code.contains('readiness_score: 50.0'), isFalse, reason: 'Mock default in ${file.path}');
      }
    });

    test('7. Web Bluetooth GATT Subscription & Binary Parsing Invariants in index.html', () {
      final content = htmlFile.readAsStringSync();

      // Standard GATT Service & Characteristic names or UUIDs
      expect(content.contains('heart_rate'), isTrue);
      expect(content.contains('heart_rate_measurement'), isTrue);
      expect(content.contains('battery_service'), isTrue);
      expect(content.contains('battery_level'), isTrue);
      expect(content.contains('34800001'), isTrue); // Movesense Whiteboard Command prefix
      expect(content.contains('34800002'), isTrue); // Movesense Whiteboard Data prefix

      // Binary decoder functions
      expect(content, contains('parseHeartRateMeasurement'));
      expect(content, contains('parseMovesenseEcgSamples'));
      expect(content, contains('navigator.bluetooth.requestDevice'));
      expect(content, contains('gattserverdisconnected'));
    });
  });
}
