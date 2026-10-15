import 'dart:io';
import 'package:test/test.dart';

void main() {
  group('Forensic Zero-Mock Truth Audit Gate', () {
    test('Compiled build/index.html contains zero hardcoded synthetic mock constants', () {
      final htmlFile = File('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html');
      expect(htmlFile.existsSync(), isTrue, reason: 'build/index.html must be generated before audit');

      final content = htmlFile.readAsStringSync();

      // Rule #0: Forbidden synthetic constants in initial HTML
      expect(content.contains('72.0'), isFalse, reason: 'Forbidden mock HR constant');
      expect(content.contains('48.5'), isFalse, reason: 'Forbidden mock HRV constant');
      expect(content.contains('72 BPM'), isFalse, reason: 'Forbidden mock HR text');
      expect(content.contains('48.5ms'), isFalse, reason: 'Forbidden mock HRV text');
      expect(content.contains('Closed Guard → Ashi Garami'), isFalse, reason: 'Forbidden mock technique');
      expect(content.contains('alpha1 = 1.0;'), isFalse, reason: 'Forbidden mock alpha1 assignment');
      expect(content.contains('readiness = 50.0;'), isFalse, reason: 'Forbidden mock readiness assignment');

      // Required zero-mock waiting state elements
      expect(content, contains('0% MOCK DATA'));
      expect(content, contains('STANDBY — DISCONNECTED'));
      expect(content, contains('3D TATAMI MAT READY — 0% MOCK DATA'));
      expect(content, contains('val-hr'));
      expect(content, contains('val-rmssd'));
      expect(content, contains('val-alpha1'));
      expect(content, contains('val-readiness'));
      expect(content, contains('canvas-ecg'));
      expect(content, contains('canvas-tatami'));
      expect(content, contains('canvas-video'));
    });
  });
}
