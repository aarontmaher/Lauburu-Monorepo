import 'package:flutter/material.dart';
import '../models/inbox_models.dart';
import '../services/omni_ai_triage_service.dart';
import '../services/omni_inbox_service.dart';

class InboxThreadDetailScreen extends StatefulWidget {
  final InboxThread thread;
  final OmniInboxService inboxService;
  final OmniAiTriageService? triageService;

  const InboxThreadDetailScreen({
    super.key,
    required this.thread,
    required this.inboxService,
    this.triageService,
  });

  @override
  State<InboxThreadDetailScreen> createState() => _InboxThreadDetailScreenState();
}

class _InboxThreadDetailScreenState extends State<InboxThreadDetailScreen> {
  late InboxThread _currentThread;
  final TextEditingController _composerController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<String> _smartReplies = [];
  bool _isLoadingReplies = false;

  @override
  void initState() {
    super.initState();
    _currentThread = widget.thread;
    widget.inboxService.markAsRead(_currentThread.id);

    // Collect initial suggested replies from latest incoming message
    _loadInitialSmartReplies();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom();
    });
  }

  void _loadInitialSmartReplies() {
    // Check if the latest message has suggested replies
    for (final msg in _currentThread.messages.reversed) {
      if (!msg.isOutgoing && msg.suggestedReplies.isNotEmpty) {
        _smartReplies = List.from(msg.suggestedReplies);
        break;
      }
    }

    // If empty and triageService is provided, attempt to generate them
    if (_smartReplies.isEmpty && widget.triageService != null) {
      _fetchAiSmartReplies();
    }
  }

  Future<void> _fetchAiSmartReplies() async {
    if (widget.triageService == null) return;
    setState(() => _isLoadingReplies = true);

    try {
      final replies = await widget.triageService!.generateSmartReplies(
        channel: _currentThread.channel,
        recentMessages: _currentThread.messages
            .map((m) => {
                  'sender': m.senderName,
                  'text': m.text,
                })
            .toList(),
      );
      if (mounted) {
        setState(() {
          _smartReplies = replies;
          _isLoadingReplies = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingReplies = false);
      }
    }
  }

  @override
  void dispose() {
    _composerController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSend() async {
    final text = _composerController.text.trim();
    if (text.isEmpty) return;

    _composerController.clear();
    await widget.inboxService.sendMessage(_currentThread.id, text);

    final updated = widget.inboxService.getThreadById(_currentThread.id);
    if (updated != null && mounted) {
      setState(() {
        _currentThread = updated;
        _smartReplies = [];
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Widget _buildChannelBadge(InboxChannel channel) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: channel.badgeColor.withAlpha(45),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: channel.badgeColor, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(channel.icon, size: 12, color: channel.badgeColor),
          const SizedBox(width: 4),
          Text(
            channel.displayName,
            style: TextStyle(
              color: channel.badgeColor,
              fontWeight: FontWeight.bold,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPriorityBadge(InboxPriority priority) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: priority.color.withAlpha(45),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: priority.color, width: 1),
      ),
      child: Text(
        priority.displayName,
        style: TextStyle(
          color: priority.color,
          fontWeight: FontWeight.bold,
          fontSize: 11,
        ),
      ),
    );
  }

  Widget _buildRichCard(Map<String, dynamic> cardData) {
    final type = cardData['type']?.toString() ?? '';

    if (type == 'gumtree_pickup') {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.green.shade900.withAlpha(60),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.greenAccent.shade700, width: 1.2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.security, color: Colors.greenAccent, size: 16),
                const SizedBox(width: 6),
                Text(
                  'SAFE MARKETPLACE TRANSACTION',
                  style: TextStyle(
                    color: Colors.greenAccent.shade400,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              cardData['item']?.toString() ?? '',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 4),
            Text(
              'Price: ${cardData['price']}',
              style: TextStyle(color: Colors.amber.shade400, fontWeight: FontWeight.w600),
            ),
            Text(
              'Location: ${cardData['location']}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              'Meeting Time: ${cardData['timeProposed']}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
      );
    }

    if (type == 'subliminator_b2b') {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.deepPurple.shade900.withAlpha(60),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.purpleAccent, width: 1.2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.factory_outlined, color: Colors.purpleAccent, size: 16),
                const SizedBox(width: 6),
                const Text(
                  'B2B PRODUCTION SPECIFICATION',
                  style: TextStyle(
                    color: Colors.purpleAccent,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Parcel: ${cardData['parcelId']}',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 4),
            Text(
              'Specs: ${cardData['specs']}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
            Text(
              'Facility: ${cardData['manufacturingFacility']}',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ],
        ),
      );
    }

    if (type == 'shopify_order') {
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.teal.shade900.withAlpha(60),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.tealAccent, width: 1.2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.local_shipping_outlined, color: Colors.tealAccent, size: 16),
                const SizedBox(width: 6),
                Text(
                  'SHOPIFY ORDER STATUS',
                  style: TextStyle(
                    color: Colors.tealAccent.shade400,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              cardData['orderNumber']?.toString() ?? '',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(height: 4),
            Text(
              cardData['product']?.toString() ?? '',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            Text(
              'Status: ${cardData['status']} (${cardData['carrier']})',
              style: TextStyle(color: Colors.amber.shade400, fontSize: 12),
            ),
          ],
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _buildMessageBubble(InboxMessage message) {
    final isMe = message.isOutgoing;
    final timeStr =
        '${message.timestamp.hour.toString().padLeft(2, '0')}:${message.timestamp.minute.toString().padLeft(2, '0')}';

    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isMe ? Colors.blue.shade700 : Colors.grey.shade800,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isMe ? 16 : 4),
            bottomRight: Radius.circular(isMe ? 4 : 16),
          ),
        ),
        child: Column(
          crossAxisAlignment:
              isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            if (!isMe)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  message.senderName,
                  style: TextStyle(
                    color: Colors.blue.shade200,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
              ),
            Text(
              message.text,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
            if (message.richCardData != null)
              _buildRichCard(message.richCardData!),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  timeStr,
                  style: TextStyle(color: Colors.white.withAlpha(150), fontSize: 10),
                ),
                if (isMe) ...[
                  const SizedBox(width: 4),
                  Icon(
                    message.status == MessageStatus.read
                        ? Icons.done_all
                        : Icons.done,
                    size: 12,
                    color: message.status == MessageStatus.read
                        ? Colors.lightBlueAccent
                        : Colors.white70,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final messages = List<InboxMessage>.from(_currentThread.messages)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: _currentThread.channel.badgeColor,
              child: Text(
                _currentThread.contactName.isNotEmpty
                    ? _currentThread.contactName[0].toUpperCase()
                    : 'U',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  fontSize: 15,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _currentThread.contactName,
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    _currentThread.contactAddress,
                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          Center(child: _buildPriorityBadge(_currentThread.priority)),
          const SizedBox(width: 6),
          Center(child: _buildChannelBadge(_currentThread.channel)),
          const SizedBox(width: 12),
        ],
      ),
      body: Column(
        children: [
          // Thread Messages List
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: messages.length,
              itemBuilder: (context, index) {
                return _buildMessageBubble(messages[index]);
              },
            ),
          ),

          // Smart Reply Chips Bar (Above Composer)
          if (_isLoadingReplies)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 6.0),
              child: SizedBox(
                height: 24,
                width: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            )
          else if (_smartReplies.isNotEmpty)
            Container(
              height: 46,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              color: Colors.grey.shade900.withAlpha(180),
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _smartReplies.length,
                separatorBuilder: (context, index) => const SizedBox(width: 6),
                itemBuilder: (context, index) {
                  final reply = _smartReplies[index];
                  return ActionChip(
                    key: Key('smart_reply_chip_$index'),
                    backgroundColor: Colors.blueGrey.shade800,
                    side: BorderSide(color: Colors.blueAccent.shade400, width: 0.8),
                    label: Text(
                      reply,
                      style: const TextStyle(fontSize: 12, color: Colors.white),
                    ),
                    onPressed: () {
                      setState(() {
                        _composerController.text = reply;
                      });
                    },
                  );
                },
              ),
            ),

          // Composer Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.grey.shade900,
              border: Border(top: BorderSide(color: Colors.grey.shade800)),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  IconButton(
                    key: const Key('voice_dictation_button'),
                    icon: const Icon(Icons.mic, color: Colors.blueAccent),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Silero VAD Voice Dictation activated'),
                        ),
                      );
                    },
                  ),
                  Expanded(
                    child: TextField(
                      key: const Key('message_composer_input'),
                      controller: _composerController,
                      decoration: const InputDecoration(
                        hintText: 'Type a reply...',
                        hintStyle: TextStyle(color: Colors.grey, fontSize: 14),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 8),
                      ),
                      onSubmitted: (_) => _handleSend(),
                    ),
                  ),
                  IconButton(
                    key: const Key('message_send_button'),
                    icon: const Icon(Icons.send, color: Colors.blueAccent),
                    onPressed: _handleSend,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
