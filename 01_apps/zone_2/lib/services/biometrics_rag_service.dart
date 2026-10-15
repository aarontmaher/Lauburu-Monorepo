import 'package:flutter/services.dart';

class BiometricsRagService {
  static const MethodChannel _channel = MethodChannel('com.lauburu.zone2/vector_db');

  /// Executes RAG purely on the edge device, bypassing Tailscale and the L1 Host.
  Future<String> queryLocalHistory(List<double> queryEmbedding) async {
    try {
      final String result = await _channel.invokeMethod('searchBiometrics', {
        'embedding': queryEmbedding,
      });
      return result;
    } on PlatformException catch (e) {
      return "Failed to query local DB: '${e.message}'.";
    }
  }
}
