// Reactive Hub State Controller managing real-time ECG stream, FFI computation, and Port 4000 WebSocket.

import 'dart:async';
import '../bridge/native_bridge.dart';
import '../models/biometrics_model.dart';

enum ConnectionMode {
  nativeRustFfi,
  port4000WebSocket,
  liveBluetoothStream,
}

class HubStateController {
  final LauburuNativeBridge bridge;
  
  final _telemetryController = StreamController<BiometricTelemetry>.broadcast();
  final _ecgBufferController = StreamController<List<double>>.broadcast();
  final _membershipController = StreamController<ShopifyMembership>.broadcast();

  Stream<BiometricTelemetry> get telemetryStream => _telemetryController.stream;
  Stream<List<double>> get ecgBufferStream => _ecgBufferController.stream;
  Stream<ShopifyMembership> get membershipStream => _membershipController.stream;

  BiometricTelemetry _currentTelemetry = BiometricTelemetry.initial();
  BiometricTelemetry get currentTelemetry => _currentTelemetry;

  ShopifyMembership _currentMembership = ShopifyMembership.fromCode(2, customerId: 'mac_mini_host');
  ShopifyMembership get currentMembership => _currentMembership;

  final List<double> _ecgDisplayBuffer = [];
  static const int maxDisplayPoints = 300;

  Timer? _streamTimer;
  bool _isRunning = false;
  bool get isRunning => _isRunning;

  ConnectionMode _mode = ConnectionMode.nativeRustFfi;
  ConnectionMode get mode => _mode;

  HubStateController({LauburuNativeBridge? customBridge})
      : bridge = customBridge ?? LauburuNativeBridge() {
    _membershipController.add(_currentMembership);
    _telemetryController.add(_currentTelemetry);
  }

  /// Ingest a single raw ECG sample from live BLE or WebSocket stream
  void ingestSample(double rawSample, {bool isConnected = true, String deviceId = 'Movesense Standby'}) {
    // Process through Rust FFI Pan-Tompkins & DFA Engine
    final dspOutput = bridge.processSample(rawSample);
    final readiness = bridge.getReadinessScore();
    final rmssd = bridge.getHrvRmssd();
    final alpha1 = bridge.getDfaAlpha1();

    _ecgDisplayBuffer.add(rawSample);
    if (_ecgDisplayBuffer.length > maxDisplayPoints) {
      _ecgDisplayBuffer.removeAt(0);
    }
    _ecgBufferController.add(List<double>.from(_ecgDisplayBuffer));

    final isQrs = dspOutput['is_qrs_peak'] as bool? ?? false;
    final hr = (dspOutput['heart_rate_bpm'] as num?)?.toDouble() ?? 0.0;
    final rr = (dspOutput['rr_interval_ms'] as num?)?.toDouble() ?? 0.0;
    final sdnn = (dspOutput['sdnn_ms'] as num?)?.toDouble() ?? 0.0;
    final pnn50 = (dspOutput['pnn50_percent'] as num?)?.toDouble() ?? 0.0;

    String zone2 = 'Resting / Disconnected';
    if (hr > 0.0) {
      if (hr >= 110.0 && alpha1 >= 0.70) {
        zone2 = 'Zone 2: Optimal Aerobic (LT1)';
      } else if (hr >= 145.0) {
        zone2 = 'Zone 3: Tempo / Aerobic Threshold';
      } else {
        zone2 = 'Resting / Recovery';
      }
    }

    _currentTelemetry = BiometricTelemetry(
      timestamp: DateTime.now().toUtc().toIso8601String(),
      deviceId: deviceId,
      connected: isConnected,
      sampleRateHz: 512.0,
      heartRateBpm: hr,
      rrIntervalMs: rr,
      hrvRmssdMs: rmssd,
      hrvSdnnMs: sdnn,
      pnn50Percent: pnn50,
      dfaAlpha1: alpha1,
      readinessScore: readiness,
      zone2Status: zone2,
      ppgCalibrated: hr > 0.0,
      latestEcgSample: rawSample,
      qrsPeakDetected: isQrs,
    );

    _telemetryController.add(_currentTelemetry);
  }

  /// Ingest an entire telemetry snapshot (e.g. from Port 4000 WebSocket)
  void ingestTelemetry(BiometricTelemetry telemetry) {
    _currentTelemetry = telemetry;
    _ecgDisplayBuffer.add(telemetry.latestEcgSample);
    if (_ecgDisplayBuffer.length > maxDisplayPoints) {
      _ecgDisplayBuffer.removeAt(0);
    }
    _ecgBufferController.add(List<double>.from(_ecgDisplayBuffer));
    _telemetryController.add(_currentTelemetry);
  }

  /// Start passive telemetry polling stream against native bridge snapshot
  void startTelemetryStream({ConnectionMode mode = ConnectionMode.nativeRustFfi}) {
    if (_isRunning) return;
    _isRunning = true;
    _mode = mode;

    _streamTimer = Timer.periodic(const Duration(milliseconds: 50), (timer) {
      if (bridge.isFfiLoaded) {
        final snapshot = bridge.getTelemetrySnapshot();
        if (snapshot.connected) {
          ingestTelemetry(snapshot);
        }
      }
    });
  }

  void updateShopifyToken(String token) {
    _currentMembership = bridge.verifyShopifyToken(token);
    _membershipController.add(_currentMembership);
  }

  void stop() {
    _streamTimer?.cancel();
    _isRunning = false;
  }

  void dispose() {
    stop();
    _telemetryController.close();
    _ecgBufferController.close();
    _membershipController.close();
  }
}

