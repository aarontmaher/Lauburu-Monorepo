import 'dart:async';
import 'omni_inbox_service.dart';

class ChatMessage {
  final String sender;
  final String text;
  final DateTime timestamp;

  ChatMessage({
    required this.sender,
    required this.text,
    required this.timestamp,
  });
}

/// Backward-compatible ChatHubService adapter.
/// Replaces brittle dartzmq native dynamic library dependencies with
/// pure Dart reactive stream messaging tied to OmniInboxService.
class ChatHubService {
  final String address;
  final OmniInboxService? inboxService;
  StreamSubscription? _inboxSubscription;

  final StreamController<ChatMessage> _messagesController =
      StreamController<ChatMessage>.broadcast();
  Stream<ChatMessage> get messagesStream => _messagesController.stream;

  ChatHubService({
    this.address = 'tcp://127.0.0.1:5555',
    this.inboxService,
  });

  void connect() {
    // Listen to OmniInboxService if available to forward incoming messages
    final service = inboxService;
    if (service != null) {
      _inboxSubscription = service.threadsStream.listen((threads) {
        for (final thread in threads) {
          if (thread.messages.isNotEmpty) {
            final latest = thread.messages.last;
            if (!_messagesController.isClosed) {
              _messagesController.add(ChatMessage(
                sender: latest.senderName,
                text: latest.text,
                timestamp: latest.timestamp,
              ));
            }
          }
        }
      });
    }
  }

  void addMessage(ChatMessage message) {
    if (!_messagesController.isClosed) {
      _messagesController.add(message);
    }
  }

  void dispose() {
    _inboxSubscription?.cancel();
    _messagesController.close();
  }
}
