import 'dart:async';
import 'package:lauburu_life_companion/services/mesh_terminal_service.dart';

/// Test helper providing controlled stream responses for widget testing.
/// Isolated in test/ to satisfy Rule #0 (Zero-Mock in production lib/).
class MockMeshTerminalService implements IMeshTerminalService {
  final _outputController = StreamController<String>.broadcast();
  final _stateController = StreamController<TerminalConnectionState>.broadcast();

  TerminalConnectionState _state = TerminalConnectionState.disconnected;
  String? _lastError;
  final List<String> sentCommands = [];
  final bool autoRespond;

  MockMeshTerminalService({
    this.autoRespond = true,
    TerminalConnectionState initialState = TerminalConnectionState.connected,
  }) {
    _state = initialState;
  }

  @override
  Stream<String> get outputStream => _outputController.stream;

  @override
  Stream<TerminalConnectionState> get stateStream => _stateController.stream;

  @override
  TerminalConnectionState get state => _state;

  @override
  String? get lastError => _lastError;

  void emitOutput(String text) {
    if (!_outputController.isClosed) {
      _outputController.add(text);
    }
  }

  void emitState(TerminalConnectionState newState, {String? error}) {
    _state = newState;
    _lastError = error;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }

  void clearCommands() {
    sentCommands.clear();
  }

  @override
  Future<void> connect({String? host, int? port}) async {
    emitState(TerminalConnectionState.connecting);
    await Future.delayed(Duration.zero);
    emitState(TerminalConnectionState.connected);
    if (autoRespond) {
      emitOutput('\x1B[1;32m[LAUBURU SOVEREIGN BLUETOOTH SERIAL TERMINAL]\x1B[0m\nlauburu> ');
    }
  }

  @override
  Future<void> sendCommand(String command) async {
    final cleanCmd = command.trim();
    sentCommands.add(cleanCmd);
    if (!autoRespond) return;

    switch (cleanCmd) {
      case 'status':
        emitOutput('\n[LAUBURU MESH NODE STATUS - LIVE PROBES]\nL1: Mac Mini M4 Pro (HOST ACTIVE)\nL2: MacBook Pro (ONLINE)\nGW: GL.iNet Router (ONLINE)\nlauburu> ');
        break;
      case 'audit':
        emitOutput('\n[MASTER APP AUDITOR REPORT]\nAll systems operational. 0 regressions.\nlauburu> ');
        break;
      case 'devices':
        emitOutput('\n[LAUBURU BLUETOOTH TERMINAL - DEVICE TELEMETRY STREAM]\nRAM: 24.0 GB | ANE: 38 TOPS | Bat: 98% 4120mV\nlauburu> ');
        break;
      case 'movesense':
        emitOutput('\n🫀 Movesense 261030002013: Disconnected (-- BPM) | Status: STANDBY | Battery: -- | DSP: Bicep ECG (Kamath 20% Filter)\nlauburu> ');
        break;
      case 'clear':
        emitOutput('\x1B[2J\x1B[H\x1B[1;32mlauburu>\x1B[0m ');
        break;
      default:
        emitOutput('\n$cleanCmd: executed\nlauburu> ');
        break;
    }
  }

  @override
  Future<void> disconnect() async {
    emitState(TerminalConnectionState.disconnected);
  }

  @override
  void dispose() {
    _outputController.close();
    _stateController.close();
  }
}
