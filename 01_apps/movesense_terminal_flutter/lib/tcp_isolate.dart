import 'dart:async';
import 'dart:io';
import 'dart:isolate';

class TcpIsolateManager {
  Isolate? _isolate;
  SendPort? _sendPort;
  ReceivePort? _receivePort;
  bool _isReady = false;

  bool get isReady => _isReady;

  Future<void> start(String host, int port) async {
    _receivePort = ReceivePort();
    _isolate = await Isolate.spawn(
      _tcpIsolateEntry,
      _receivePort!.sendPort,
    );

    final completer = Completer<void>();
    
    _receivePort!.listen((message) {
      if (message is SendPort) {
        _sendPort = message;
        _sendPort!.send({'cmd': 'connect', 'host': host, 'port': port});
      } else if (message is Map && message['status'] == 'connected') {
        _isReady = true;
        if (!completer.isCompleted) completer.complete();
      } else if (message is Map && message['status'] == 'error') {
        if (!completer.isCompleted) completer.completeError(message['error']);
      }
    });

    return completer.future;
  }

  void sendData(List<int> data) {
    if (_isReady && _sendPort != null) {
      _sendPort!.send({'cmd': 'send', 'data': data});
    }
  }

  void stop() {
    if (_isReady && _sendPort != null) {
      _sendPort!.send({'cmd': 'disconnect'});
      _receivePort?.close();
      _isolate?.kill();
      _isReady = false;
    }
  }
}

void _tcpIsolateEntry(SendPort sendPort) {
  final receivePort = ReceivePort();
  sendPort.send(receivePort.sendPort);

  Socket? socket;

  receivePort.listen((message) async {
    if (message is Map) {
      final cmd = message['cmd'];
      if (cmd == 'connect') {
        try {
          socket = await Socket.connect(message['host'], message['port']);
          socket!.setOption(SocketOption.tcpNoDelay, true);
          sendPort.send({'status': 'connected'});
        } catch (e) {
          sendPort.send({'status': 'error', 'error': e.toString()});
        }
      } else if (cmd == 'send' && socket != null) {
        final List<int> data = message['data'];
        socket!.add(data);
      } else if (cmd == 'disconnect') {
        socket?.close();
        receivePort.close();
      }
    }
  });
}
