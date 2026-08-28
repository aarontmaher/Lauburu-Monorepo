import 'dart:async';
import 'package:web_socket_channel/web_socket_channel.dart';

enum HubConnectionState { disconnected, connecting, connected, error }

class ComputeHubConnectionService {
  final _stateController = StreamController<HubConnectionState>.broadcast();
  HubConnectionState _currentState = HubConnectionState.disconnected;
  WebSocketChannel? _channel;

  // Candidate WebSocket endpoints for local loopback, Android ADB/Emulator, Tailscale VPN, and LAN Gateway
  final List<String> _candidateUrls = [
    'ws://127.0.0.1:8000/ws/ingest',
    'ws://10.0.2.2:8000/ws/ingest',
    'ws://100.93.158.96:8000/ws/ingest',
    'ws://100.101.39.98:8000/ws/ingest',
    'ws://192.168.8.224:8000/ws/ingest',
    'ws://127.0.0.1:8080/ws/telemetry?tenantId=default_tenant'
  ];

  Stream<HubConnectionState> get connectionState => _stateController.stream;
  HubConnectionState get currentState => _currentState;

  void _updateState(HubConnectionState state) {
    _currentState = state;
    _stateController.add(state);
  }

  Future<void> connectToHub() async {
    _updateState(HubConnectionState.connecting);
    
    for (final url in _candidateUrls) {
      try {
        final channel = WebSocketChannel.connect(Uri.parse(url));
        await channel.ready.timeout(const Duration(seconds: 3));
        
        _channel = channel;
        _updateState(HubConnectionState.connected);
        
        _channel!.stream.listen(
          (message) {
            // Process live BLE telemetry data from the compute hub broadcast
          },
          onDone: () {
            _updateState(HubConnectionState.disconnected);
          },
          onError: (error) {
            _updateState(HubConnectionState.error);
          },
          cancelOnError: true,
        );
        return; // Connected successfully!
      } catch (e) {
        // Try next candidate URL
      }
    }

    _updateState(HubConnectionState.error);
  }


  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _updateState(HubConnectionState.disconnected);
  }

  void dispose() {
    disconnect();
    _stateController.close();
  }
}
