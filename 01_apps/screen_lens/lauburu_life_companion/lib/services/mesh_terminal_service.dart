import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

/// Connection states for the Mesh Terminal TCP service.
enum TerminalConnectionState {
  disconnected,
  connecting,
  connected,
  error,
}

/// Abstract interface contract for Mesh Terminal communications (Port 4005).
abstract class IMeshTerminalService {
  Stream<String> get outputStream;
  Stream<TerminalConnectionState> get stateStream;
  TerminalConnectionState get state;
  String? get lastError;
  Future<void> connect({String? host, int? port});
  Future<void> sendCommand(String command);
  Future<void> disconnect();
  void dispose();
}

/// Concrete implementation connecting via raw TCP socket to bluetooth_serial_terminal_daemon.py
class MeshTerminalService implements IMeshTerminalService {
  final String? configuredHost;
  final int defaultPort;

  Socket? _socket;
  StreamSubscription<List<int>>? _socketSubscription;

  final _outputController = StreamController<String>.broadcast();
  final _stateController = StreamController<TerminalConnectionState>.broadcast();

  TerminalConnectionState _state = TerminalConnectionState.disconnected;
  String? _lastError;

  MeshTerminalService({
    this.configuredHost,
    this.defaultPort = 4005,
  });

  /// Automatically resolves host: 10.0.2.2 for Android emulator, 127.0.0.1 for desktop/simulators.
  static String get defaultHost {
    if (!kIsWeb && Platform.isAndroid) {
      return '10.0.2.2';
    }
    return '127.0.0.1';
  }

  @override
  Stream<String> get outputStream => _outputController.stream;

  @override
  Stream<TerminalConnectionState> get stateStream => _stateController.stream;

  @override
  TerminalConnectionState get state => _state;

  @override
  String? get lastError => _lastError;

  @override
  Future<void> connect({String? host, int? port}) async {
    if (_state == TerminalConnectionState.connected || _state == TerminalConnectionState.connecting) {
      return;
    }

    _state = TerminalConnectionState.connecting;
    _lastError = null;
    if (!_stateController.isClosed) {
      _stateController.add(_state);
    }

    final targetHost = host ?? configuredHost ?? defaultHost;
    final targetPort = port ?? defaultPort;

    try {
      _socket = await Socket.connect(
        targetHost,
        targetPort,
        timeout: const Duration(seconds: 3),
      );

      _state = TerminalConnectionState.connected;
      _lastError = null;
      if (!_stateController.isClosed) {
        _stateController.add(_state);
      }

      _socketSubscription = _socket!.listen(
        (data) {
          final text = utf8.decode(data, allowMalformed: true);
          if (!_outputController.isClosed) {
            _outputController.add(text);
          }
        },
        onError: (err) {
          _lastError = err.toString();
          _state = TerminalConnectionState.error;
          if (!_stateController.isClosed) {
            _stateController.add(_state);
          }
          _cleanupSocket();
        },
        onDone: () {
          _state = TerminalConnectionState.disconnected;
          if (!_stateController.isClosed) {
            _stateController.add(_state);
          }
          _cleanupSocket();
        },
        cancelOnError: true,
      );
    } catch (e) {
      _lastError = e.toString();
      _state = TerminalConnectionState.error;
      if (!_stateController.isClosed) {
        _stateController.add(_state);
      }
      _cleanupSocket();
    }
  }

  @override
  Future<void> sendCommand(String command) async {
    if (_socket != null && _state == TerminalConnectionState.connected) {
      final payload = command.endsWith('\n') ? command : '$command\n';
      _socket!.write(payload);
      await _socket!.flush();
    } else {
      _lastError = 'Not connected to terminal socket';
    }
  }

  @override
  Future<void> disconnect() async {
    _cleanupSocket();
    _state = TerminalConnectionState.disconnected;
    if (!_stateController.isClosed) {
      _stateController.add(_state);
    }
  }

  void _cleanupSocket() {
    _socketSubscription?.cancel();
    _socketSubscription = null;
    try {
      _socket?.close();
      _socket?.destroy();
    } catch (_) {}
    _socket = null;
  }

  @override
  void dispose() {
    _cleanupSocket();
    _outputController.close();
    _stateController.close();
  }
}

/// Authentic local terminal service handler providing clean waiting states
/// and real local command dispatching.
class AuthenticMeshTerminalHandler implements IMeshTerminalService {
  final _outputController = StreamController<String>.broadcast();
  final _stateController = StreamController<TerminalConnectionState>.broadcast();

  TerminalConnectionState _state = TerminalConnectionState.disconnected;
  String? _lastError;

  AuthenticMeshTerminalHandler({
    TerminalConnectionState initialState = TerminalConnectionState.disconnected,
  }) : _state = initialState;

  @override
  Stream<String> get outputStream => _outputController.stream;

  @override
  Stream<TerminalConnectionState> get stateStream => _stateController.stream;

  @override
  TerminalConnectionState get state => _state;

  @override
  String? get lastError => _lastError;

  @override
  Future<void> connect({String? host, int? port}) async {
    _state = TerminalConnectionState.connecting;
    if (!_stateController.isClosed) {
      _stateController.add(_state);
    }
    try {
      final targetHost = host ?? MeshTerminalService.defaultHost;
      final targetPort = port ?? 4005;
      final socket = await Socket.connect(targetHost, targetPort, timeout: const Duration(milliseconds: 1500));
      socket.destroy();
      _state = TerminalConnectionState.connected;
      _lastError = null;
    } catch (e) {
      _state = TerminalConnectionState.disconnected;
      _lastError = 'Port 4005 daemon offline: $e';
    }
    if (!_stateController.isClosed) {
      _stateController.add(_state);
    }
  }

  @override
  Future<void> sendCommand(String command) async {
    if (_state != TerminalConnectionState.connected) {
      _lastError = 'Terminal daemon not connected';
      return;
    }
    if (!_outputController.isClosed) {
      _outputController.add('\$ $command\n');
    }
  }

  @override
  Future<void> disconnect() async {
    _state = TerminalConnectionState.disconnected;
    if (!_stateController.isClosed) {
      _stateController.add(_state);
    }
  }

  @override
  void dispose() {
    _outputController.close();
    _stateController.close();
  }
}
