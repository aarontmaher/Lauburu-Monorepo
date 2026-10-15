import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lauburu_life_companion/services/shizuku_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ShizukuExecutionResult Model Tests', () {
    test('Roundtrip serialization and properties', () {
      final res = ShizukuExecutionResult(
        exitCode: 0,
        stdout: 'uid=2000(shell) gid=2000(shell)',
        stderr: '',
        durationMs: 42,
      );

      expect(res.isSuccess, isTrue);
      expect(res.exitCode, equals(0));
      expect(res.stdout, contains('uid=2000'));
      expect(res.durationMs, equals(42));

      final map = res.toMap();
      final fromMap = ShizukuExecutionResult.fromMap(map);
      expect(fromMap.isSuccess, isTrue);
      expect(fromMap.stdout, equals(res.stdout));
      expect(fromMap.durationMs, equals(42));

      final fromJson = ShizukuExecutionResult.fromJson({
        'exit_code': 1,
        'stdout': '',
        'stderr': 'Permission denied',
        'duration_ms': 15,
      });
      expect(fromJson.isSuccess, isFalse);
      expect(fromJson.exitCode, equals(1));
      expect(fromJson.stderr, equals('Permission denied'));
      expect(fromJson.durationMs, equals(15));
    });
  });

  group('ShizukuService Native MethodChannel Tests', () {
    const channel = MethodChannel('ai.lauburu.companion/shizuku');
    final List<MethodCall> methodCalls = [];

    setUp(() {
      methodCalls.clear();
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (MethodCall call) async {
        methodCalls.add(call);
        switch (call.method) {
          case 'isAvailable':
            return true;
          case 'hasPermission':
            return true;
          case 'requestPermission':
            return true;
          case 'getUid':
            return 2000;
          case 'getVersion':
            return 13;
          case 'executeCommand':
            final cmd = call.arguments['command'] as String;
            if (cmd.startsWith('dumpsys battery')) {
              return {
                'exitCode': 0,
                'stdout': 'level: 95\ntemperature: 290\nvoltage: 4200\n',
                'stderr': '',
                'durationMs': 20,
              };
            } else if (cmd.startsWith('input tap')) {
              return {'exitCode': 0, 'stdout': '', 'stderr': '', 'durationMs': 5};
            } else if (cmd.startsWith('input keyevent')) {
              return {'exitCode': 0, 'stdout': '', 'stderr': '', 'durationMs': 5};
            } else if (cmd.startsWith('input swipe')) {
              return {'exitCode': 0, 'stdout': '', 'stderr': '', 'durationMs': 5};
            } else if (cmd.startsWith('input text')) {
              return {'exitCode': 0, 'stdout': '', 'stderr': '', 'durationMs': 5};
            } else if (cmd.contains('base64')) {
              return {
                'exitCode': 0,
                'stdout': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
                'stderr': '',
                'durationMs': 35,
              };
            }
            return {
              'exitCode': 0,
              'stdout': 'uid=2000(shell)\n',
              'stderr': '',
              'durationMs': 12,
            };
          case 'injectTap':
            return true;
          case 'injectKey':
            return true;
          case 'injectSwipe':
            return true;
          case 'injectText':
            return true;
          default:
            return null;
        }
      });
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, null);
    });

    test('isAvailable and hasPermission query channel on Android', () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      try {
        final service = ShizukuService(channel: channel);
        final available = await service.isAvailable();
        final permission = await service.hasPermission();
        final reqPermission = await service.requestPermission();
        final uid = await service.getUid();

        expect(available, isTrue);
        expect(permission, isTrue);
        expect(reqPermission, isTrue);
        expect(uid, equals(2000));
        expect(methodCalls.map((c) => c.method),
            containsAll(['isAvailable', 'hasPermission', 'requestPermission', 'getUid']));
      } finally {
        debugDefaultTargetPlatformOverride = null;
      }
    });

    test('executeCommand returns ShizukuExecutionResult', () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      try {
        final service = ShizukuService(channel: channel);
        final res = await service.executeCommand('id');

        expect(res.isSuccess, isTrue);
        expect(res.exitCode, equals(0));
        expect(res.stdout, contains('uid=2000'));
        expect(methodCalls.last.method, equals('executeCommand'));
        expect(methodCalls.last.arguments['command'], equals('id'));
      } finally {
        debugDefaultTargetPlatformOverride = null;
      }
    });

    test('injectTap, injectKey, injectSwipe, injectText invoke channel', () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      try {
        final service = ShizukuService(channel: channel);
        expect(await service.injectTap(500, 1000), isTrue);
        expect(await service.injectKey(3), isTrue); // Home
        expect(await service.injectSwipe(100, 200, 300, 400), isTrue);
        expect(await service.injectText('Hello World'), isTrue);

        final calls = methodCalls.map((c) => c.method).toList();
        expect(calls, contains('injectTap'));
        expect(calls, contains('injectKey'));
        expect(calls, contains('injectSwipe'));
        expect(calls, contains('injectText'));
      } finally {
        debugDefaultTargetPlatformOverride = null;
      }
    });

    test('getBatteryInfo parses battery properties', () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      try {
        final service = ShizukuService(channel: channel);
        final battery = await service.getBatteryInfo();

        expect(battery['status'], equals('ok'));
        expect(battery['level'], equals(95));
        expect(battery['temperature'], equals(290));
        expect(battery['voltage'], equals(4200));
      } finally {
        debugDefaultTargetPlatformOverride = null;
      }
    });

    test('screencap returns base64 string on Android', () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      try {
        final service = ShizukuService(channel: channel);
        final base64Img = await service.screencap();

        expect(base64Img, isNotNull);
        expect(base64Img, startsWith('iVBOR'));
      } finally {
        debugDefaultTargetPlatformOverride = null;
      }
    });
  });

  group('ShizukuService Remote MCP Bridge Tests (macOS / iOS)', () {
    test('Queries remote Termux Shizuku MCP server via REST', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response(
            jsonEncode({'status': 'healthy', 'available': true}),
            200,
            headers: {'content-type': 'application/json'},
          );
        } else if (request.url.path == '/api/shizuku/status') {
          expect(request.headers['X-Lauburu-Sovereign-Key'], equals('secret_key'));
          return http.Response(
            jsonEncode({
              'status': 'ok',
              'available': true,
              'permission_granted': true,
              'uid': 2000,
              'rish_present': true,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        } else if (request.url.path == '/api/shizuku/exec') {
          expect(request.headers['X-Lauburu-Sovereign-Key'], equals('secret_key'));
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          final cmd = body['command'] as String;
          return http.Response(
            jsonEncode({
              'exit_code': 0,
              'stdout': 'Command executed: $cmd',
              'stderr': '',
              'duration_ms': 25,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        } else if (request.url.path == '/api/shizuku/screencap') {
          return http.Response(
            jsonEncode({
              'status': 'ok',
              'image_base64': 'dGVzdF9wbmc=',
              'format': 'png',
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      final service = ShizukuService(
        remoteEndpoint: 'http://100.73.38.87:8089',
        authKey: 'secret_key',
        client: mockClient,
      );

      expect(service.isRemote, isTrue);

      final available = await service.isAvailable();
      expect(available, isTrue);

      final hasPerm = await service.hasPermission();
      expect(hasPerm, isTrue);

      final uid = await service.getUid();
      expect(uid, equals(2000));

      final execRes = await service.executeCommand('uname -a');
      expect(execRes.isSuccess, isTrue);
      expect(execRes.stdout, contains('Command executed: uname -a'));
      expect(execRes.durationMs, equals(25));

      final tapOk = await service.injectTap(100, 200);
      expect(tapOk, isTrue);

      final screencap = await service.screencap();
      expect(screencap, equals('dGVzdF9wbmc='));

      service.dispose();
    });

    test('Handles remote server failure gracefully without unhandled crashes', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Internal Server Error', 500);
      });

      final service = ShizukuService(
        remoteEndpoint: 'http://100.73.38.87:8089',
        client: mockClient,
      );

      final available = await service.isAvailable();
      expect(available, isFalse);

      final hasPerm = await service.hasPermission();
      expect(hasPerm, isFalse);

      final execRes = await service.executeCommand('id');
      expect(execRes.isSuccess, isFalse);
      expect(execRes.exitCode, equals(-500));
      expect(execRes.stderr, contains('HTTP error 500'));

      service.dispose();
    });
  });
}
