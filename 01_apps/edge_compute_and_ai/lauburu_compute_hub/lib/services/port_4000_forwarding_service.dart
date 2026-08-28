// Port 4000 Live Forwarding Service for Pixel Android Engine
// Pushes real-time 128Hz Movesense/Polar frames to Port 4000 Hub

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'telemetry_persistence_service.dart';

class Port4000ForwardingService {
  final String host;
  final int port;
  String? sessionToken;
  final TelemetryPersistenceService? persistenceService;
  final HttpClient _httpClient = HttpClient();
  WebSocket? _webSocket;
  bool _isConnected = false;

  Port4000ForwardingService({
    this.host = '127.0.0.1',
    this.port = 4000,
    this.sessionToken,
    this.persistenceService,
  });

  String get httpBaseUrl => 'http://$host:$port';
  String get wsUrl => 'ws://$host:$port/ws/telemetry';

  Future<bool> forwardFrameHttp(TelemetryFrame frame) async {
    try {
      final request = await _httpClient.postUrl(
        Uri.parse('$httpBaseUrl/api/sensors/ingest'),
      );
      request.headers.set('Content-Type', 'application/json');

      final payload = {
        'session_token': sessionToken,
        'sensor_type': frame.sensorType,
        'heart_rate': frame.heartRate,
        'rr_intervals_ms': frame.rrIntervalsMs ?? [],
        'rmssd': frame.rmssd,
        'dfa_alpha1': frame.dfaAlpha1,
        'ecg_mv': frame.rawSamples ?? [],
        'acc_g': frame.accG,
        'epoch_ms': frame.timestampEpochMs,
      };

      request.add(utf8.encode(jsonEncode(payload)));
      final response = await request.close();
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> connectWebSocket() async {
    try {
      _webSocket = await WebSocket.connect(wsUrl);
      _isConnected = true;
      _webSocket!.listen(
        (data) {},
        onDone: () {
          _isConnected = false;
        },
        onError: (_) {
          _isConnected = false;
        },
      );
      return true;
    } catch (_) {
      _isConnected = false;
      return false;
    }
  }

  Future<bool> forwardFrameWs(TelemetryFrame frame) async {
    if (!_isConnected || _webSocket == null) {
      final connected = await connectWebSocket();
      if (!connected) return await forwardFrameHttp(frame);
    }

    try {
      final payload = {
        'action': 'push_tick',
        'session_token': sessionToken,
        'tick': {
          'epoch_ms': frame.timestampEpochMs,
          'sensor_type': frame.sensorType,
          'hr_bpm': frame.heartRate,
          'rr_ms': frame.rrIntervalsMs,
          'rmssd': frame.rmssd,
          'dfa_alpha1': frame.dfaAlpha1,
          'ecg_sample': frame.rawSamples?.isNotEmpty == true ? frame.rawSamples!.first : null,
          'accel': frame.accG,
        }
      };
      _webSocket!.add(jsonEncode(payload));
      return true;
    } catch (_) {
      return await forwardFrameHttp(frame);
    }
  }

  void dispose() {
    _webSocket?.close();
    _httpClient.close();
  }
}
