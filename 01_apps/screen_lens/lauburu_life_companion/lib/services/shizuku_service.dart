import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

/// Execution result returned by Shizuku privileged shell execution.
class ShizukuExecutionResult {
  final int exitCode;
  final String stdout;
  final String stderr;
  final int durationMs;

  const ShizukuExecutionResult({
    required this.exitCode,
    required this.stdout,
    required this.stderr,
    required this.durationMs,
  });

  bool get isSuccess => exitCode == 0;

  factory ShizukuExecutionResult.fromMap(Map<dynamic, dynamic> map) {
    return ShizukuExecutionResult(
      exitCode: (map['exitCode'] as num?)?.toInt() ?? -1,
      stdout: (map['stdout'] as String?) ?? '',
      stderr: (map['stderr'] as String?) ?? '',
      durationMs: (map['durationMs'] as num?)?.toInt() ?? 0,
    );
  }

  factory ShizukuExecutionResult.fromJson(Map<String, dynamic> json) {
    return ShizukuExecutionResult(
      exitCode: (json['exit_code'] ?? json['exitCode'] as num?)?.toInt() ?? -1,
      stdout: (json['stdout'] as String?) ?? '',
      stderr: (json['stderr'] as String?) ?? '',
      durationMs: (json['duration_ms'] ?? json['durationMs'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'exitCode': exitCode,
      'stdout': stdout,
      'stderr': stderr,
      'durationMs': durationMs,
      'isSuccess': isSuccess,
    };
  }

  @override
  String toString() {
    return 'ShizukuExecutionResult(exitCode: $exitCode, isSuccess: $isSuccess, durationMs: ${durationMs}ms)';
  }
}

/// ShizukuService provides privileged Android shell access via:
/// 1. Native Shizuku Binder IPC via MethodChannel (`ai.lauburu.companion/shizuku`) on Android.
/// 2. Remote HTTP/WebSocket connection to the Termux Shizuku MCP server on Port 8089 for macOS/iOS.
class ShizukuService {
  static const MethodChannel _defaultChannel =
      MethodChannel('ai.lauburu.companion/shizuku');

  final MethodChannel _channel;
  final String? remoteEndpoint;
  final String? authKey;
  final http.Client _client;

  ShizukuService({
    MethodChannel? channel,
    this.remoteEndpoint,
    this.authKey,
    http.Client? client,
  })  : _channel = channel ?? _defaultChannel,
        _client = client ?? http.Client();

  bool get isAndroid =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  bool get isRemote => remoteEndpoint != null && remoteEndpoint!.isNotEmpty;

  /// Check if Shizuku binder / MCP server is reachable and active.
  Future<bool> isAvailable() async {
    if (isRemote) {
      try {
        final uri = Uri.parse('$remoteEndpoint/health');
        final response = await _client.get(uri).timeout(const Duration(seconds: 3));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return data['status'] == 'healthy' || data['available'] == true;
        }
        return false;
      } catch (_) {
        return false;
      }
    }

    if (!isAndroid) {
      return false;
    }

    try {
      final res = await _channel.invokeMethod<bool>('isAvailable');
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  Map<String, String> get _authHeaders {
    final map = <String, String>{};
    if (authKey != null && authKey!.isNotEmpty) {
      map['X-Lauburu-Sovereign-Key'] = authKey!;
    }
    return map;
  }

  /// Check if Shizuku privileged permission (moe.shizuku.manager.permission.API_V23) is granted.
  Future<bool> hasPermission() async {
    if (isRemote) {
      try {
        final uri = Uri.parse('$remoteEndpoint/api/shizuku/status');
        final response =
            await _client.get(uri, headers: _authHeaders).timeout(const Duration(seconds: 3));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return data['permission_granted'] == true;
        }
        return false;
      } catch (_) {
        return false;
      }
    }

    if (!isAndroid) {
      return false;
    }

    try {
      final res = await _channel.invokeMethod<bool>('hasPermission');
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Request Shizuku permission dialog on device.
  Future<bool> requestPermission() async {
    if (isRemote) {
      // Remote clients cannot pop native OS permission dialogs directly
      return hasPermission();
    }

    if (!isAndroid) {
      return false;
    }

    try {
      final res = await _channel.invokeMethod<bool>('requestPermission');
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Get UID of the Shizuku server process (expected: 2000 for shell, 0 for root).
  Future<int?> getUid() async {
    if (isRemote) {
      try {
        final uri = Uri.parse('$remoteEndpoint/api/shizuku/status');
        final response =
            await _client.get(uri, headers: _authHeaders).timeout(const Duration(seconds: 3));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return (data['uid'] as num?)?.toInt();
        }
        return null;
      } catch (_) {
        return null;
      }
    }


    if (!isAndroid) {
      return null;
    }

    try {
      return await _channel.invokeMethod<int>('getUid');
    } catch (_) {
      return null;
    }
  }

  /// Execute an arbitrary shell command through privileged Shizuku Binder or Termux rish.
  Future<ShizukuExecutionResult> executeCommand(
    String command, {
    Duration timeout = const Duration(seconds: 10),
  }) async {
    if (isRemote) {
      final sw = Stopwatch()..start();
      try {
        final uri = Uri.parse('$remoteEndpoint/api/shizuku/exec');
        final headers = <String, String>{
          'Content-Type': 'application/json',
        };
        if (authKey != null) {
          headers['X-Lauburu-Sovereign-Key'] = authKey!;
        }
        final body = jsonEncode({
          'command': command,
          'timeout_sec': timeout.inSeconds,
        });

        final response = await _client
            .post(uri, headers: headers, body: body)
            .timeout(timeout + const Duration(seconds: 2));

        sw.stop();
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return ShizukuExecutionResult.fromJson(data);
        } else {
          return ShizukuExecutionResult(
            exitCode: -response.statusCode,
            stdout: '',
            stderr: 'HTTP error ${response.statusCode}: ${response.body}',
            durationMs: sw.elapsedMilliseconds,
          );
        }
      } catch (e) {
        sw.stop();
        return ShizukuExecutionResult(
          exitCode: -1,
          stdout: '',
          stderr: 'Remote Shizuku execution error: $e',
          durationMs: sw.elapsedMilliseconds,
        );
      }
    }

    if (!isAndroid) {
      return const ShizukuExecutionResult(
        exitCode: -1,
        stdout: '',
        stderr: 'Shizuku requires Android runtime or configured remoteEndpoint',
        durationMs: 0,
      );
    }

    try {
      final res = await _channel.invokeMethod<Map<dynamic, dynamic>>(
        'executeCommand',
        {
          'command': command,
          'timeoutMs': timeout.inMilliseconds,
        },
      );
      if (res != null) {
        return ShizukuExecutionResult.fromMap(res);
      }
      return const ShizukuExecutionResult(
        exitCode: -1,
        stdout: '',
        stderr: 'Empty response from Shizuku MethodChannel',
        durationMs: 0,
      );
    } on PlatformException catch (e) {
      return ShizukuExecutionResult(
        exitCode: -1,
        stdout: '',
        stderr: 'PlatformException: ${e.message}',
        durationMs: 0,
      );
    } catch (e) {
      return ShizukuExecutionResult(
        exitCode: -1,
        stdout: '',
        stderr: 'Exception: $e',
        durationMs: 0,
      );
    }
  }

  /// Inject touch tap event at coordinate (x, y).
  Future<bool> injectTap(int x, int y) async {
    if (isRemote) {
      final res = await executeCommand('input tap $x $y');
      return res.isSuccess;
    }

    if (!isAndroid) return false;

    try {
      final res = await _channel.invokeMethod<bool>('injectTap', {'x': x, 'y': y});
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Inject Android keycode event (e.g. 3=Home, 4=Back, 26=Power).
  Future<bool> injectKey(int keyCode) async {
    if (isRemote) {
      final res = await executeCommand('input keyevent $keyCode');
      return res.isSuccess;
    }

    if (!isAndroid) return false;

    try {
      final res = await _channel.invokeMethod<bool>('injectKey', {'keyCode': keyCode});
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Inject swipe/drag gesture.
  Future<bool> injectSwipe(
    int x1,
    int y1,
    int x2,
    int y2, {
    int durationMs = 300,
  }) async {
    if (isRemote) {
      final res = await executeCommand('input swipe $x1 $y1 $x2 $y2 $durationMs');
      return res.isSuccess;
    }

    if (!isAndroid) return false;

    try {
      final res = await _channel.invokeMethod<bool>('injectSwipe', {
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'durationMs': durationMs,
      });
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Type text into active input focus.
  Future<bool> injectText(String text) async {
    final escaped = text.replaceAll("'", "'\\''");
    if (isRemote) {
      final res = await executeCommand("input text '$escaped'");
      return res.isSuccess;
    }

    if (!isAndroid) return false;

    try {
      final res = await _channel.invokeMethod<bool>('injectText', {'text': text});
      return res ?? false;
    } catch (_) {
      return false;
    }
  }

  /// Capture active screen frame as base64 PNG data.
  Future<String?> screencap({bool asBase64 = true}) async {
    if (isRemote) {
      try {
        final uri = Uri.parse('$remoteEndpoint/api/shizuku/screencap');
        final headers = <String, String>{};
        if (authKey != null) {
          headers['X-Lauburu-Sovereign-Key'] = authKey!;
        }
        final response = await _client.get(uri, headers: headers).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          return data['image_base64'] as String?;
        }
      } catch (_) {
        return null;
      }
    }

    // Local execution via base64 encoded screencap
    final res = await executeCommand('screencap -p | base64');
    if (res.isSuccess && res.stdout.isNotEmpty) {
      return res.stdout.replaceAll('\n', '').replaceAll('\r', '').trim();
    }
    return null;
  }

  /// Query the currently focused window / top activity package name.
  Future<String?> getActiveApp() async {
    final res = await executeCommand('dumpsys window displays | grep -E "mCurrentFocus|mFocusedApp"');
    if (res.isSuccess && res.stdout.isNotEmpty) {
      return res.stdout.trim();
    }
    return null;
  }

  /// Privileged runtime permission grant without user prompt.
  Future<bool> grantPermission(String packageName, String permission) async {
    final res = await executeCommand('pm grant $packageName $permission');
    return res.isSuccess;
  }

  /// Query battery telemetry (voltage, temperature, percentage).
  Future<Map<String, dynamic>> getBatteryInfo() async {
    final res = await executeCommand('dumpsys battery');
    if (!res.isSuccess) {
      return {'status': 'unavailable', 'error': res.stderr};
    }

    final data = <String, dynamic>{'status': 'ok'};
    final lines = res.stdout.split('\n');
    for (final rawLine in lines) {
      final line = rawLine.trim();
      if (line.contains(':')) {
        final parts = line.split(':');
        final key = parts[0].trim();
        final value = parts.sublist(1).join(':').trim();
        final numVal = num.tryParse(value);
        data[key] = numVal ?? value;
      }
    }
    return data;
  }

  /// Query device telemetry (memory, uptime, load).
  Future<Map<String, dynamic>> getTelemetry() async {
    final memRes = await executeCommand('cat /proc/meminfo');
    final uptimeRes = await executeCommand('uptime');

    return {
      'status': 'ok',
      'uptime': uptimeRes.stdout.trim(),
      'meminfo_available': memRes.isSuccess,
      'is_android': isAndroid,
      'is_remote': isRemote,
    };
  }

  void dispose() {
    _client.close();
  }
}
