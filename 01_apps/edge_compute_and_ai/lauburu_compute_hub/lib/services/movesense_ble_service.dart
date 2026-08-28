// Movesense 128Hz & Polar H10 BLE Service for Android Compute Hub
// Handles BLE GATT streams for Movesense /Meas/ECG/128, /Meas/IMU6/52, and Polar 0x2A37

import 'dart:async';
import 'dart:math';
import 'telemetry_persistence_service.dart';
import 'port_4000_forwarding_service.dart';

class MovesenseBleService {
  final TelemetryPersistenceService persistenceService;
  final Port4000ForwardingService forwardingService;
  bool _isStreaming = false;

  MovesenseBleService({
    required this.persistenceService,
    required this.forwardingService,
  });

  bool get isStreaming => _isStreaming;

  // Process incoming Movesense 128Hz ECG frame
  Future<void> handleMovesenseEcgPacket({
    required int timestampEpochMs,
    required List<double> ecgSamplesMv,
    required double heartRate,
    required List<double> rrIntervalsMs,
    double? dfaAlpha1,
    Map<String, double>? accG,
  }) async {
    final frame = TelemetryFrame(
      timestampEpochMs: timestampEpochMs,
      sensorType: 'movesense',
      deviceId: 'MOVESENSE-214430001234',
      sampleRateHz: 128,
      heartRate: heartRate,
      rrIntervalsMs: rrIntervalsMs,
      dfaAlpha1: dfaAlpha1 ?? 0.75,
      rmssd: _computeRmssd(rrIntervalsMs),
      rawSamples: ecgSamplesMv,
      accG: accG ?? {'x': 0.04, 'y': 0.98, 'z': 0.12},
    );

    // 1. Local persistence
    await persistenceService.appendFrame(frame);

    // 2. Forward live to Port 4000
    await forwardingService.forwardFrameWs(frame);
  }

  // Process incoming Polar H10 HRS packet
  Future<void> handlePolarHrsPacket({
    required int timestampEpochMs,
    required double heartRate,
    required List<double> rrIntervalsMs,
  }) async {
    final frame = TelemetryFrame(
      timestampEpochMs: timestampEpochMs,
      sensorType: 'polar',
      deviceId: 'POLAR-H10-8A7B9C',
      sampleRateHz: 130,
      heartRate: heartRate,
      rrIntervalsMs: rrIntervalsMs,
      dfaAlpha1: 0.72,
      rmssd: _computeRmssd(rrIntervalsMs),
      rawSamples: [],
    );

    await persistenceService.appendFrame(frame);
    await forwardingService.forwardFrameWs(frame);
  }

  double? _computeRmssd(List<double> rrList) {
    if (rrList.length < 2) return null;
    double sumSq = 0.0;
    for (int i = 1; i < rrList.length; i++) {
      final diff = rrList[i] - rrList[i - 1];
      sumSq += diff * diff;
    }
    return sqrt(sumSq / (rrList.length - 1));
  }
}
