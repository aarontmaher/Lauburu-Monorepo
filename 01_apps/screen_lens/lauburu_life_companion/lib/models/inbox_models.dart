import 'package:flutter/material.dart';

enum InboxChannel {
  all,
  gmailPersonal,
  gmailBusiness,
  sms,
  instagram,
  facebook,
  shopify,
  gumtree;

  String get displayName {
    switch (this) {
      case InboxChannel.all:
        return 'All Messages';
      case InboxChannel.gmailPersonal:
        return 'Gmail: Personal';
      case InboxChannel.gmailBusiness:
        return 'Gmail: Lauburu';
      case InboxChannel.sms:
        return 'SMS';
      case InboxChannel.instagram:
        return 'Instagram';
      case InboxChannel.facebook:
        return 'Messenger';
      case InboxChannel.shopify:
        return 'Shopify';
      case InboxChannel.gumtree:
        return 'Gumtree';
    }
  }

  Color get badgeColor {
    switch (this) {
      case InboxChannel.all:
        return Colors.blueGrey;
      case InboxChannel.gmailPersonal:
        return const Color(0xFFEA4335); // Red
      case InboxChannel.gmailBusiness:
        return const Color(0xFF7C4DFF); // Deep Purple
      case InboxChannel.sms:
        return const Color(0xFF00C853); // Emerald Green
      case InboxChannel.instagram:
        return const Color(0xFFE1306C); // Instagram Gradient Pink
      case InboxChannel.facebook:
        return const Color(0xFF1877F2); // Electric Blue
      case InboxChannel.shopify:
        return const Color(0xFF008060); // Shopify Green
      case InboxChannel.gumtree:
        return const Color(0xFF72EF36); // Gumtree Lime Green
    }
  }

  IconData get icon {
    switch (this) {
      case InboxChannel.all:
        return Icons.all_inbox;
      case InboxChannel.gmailPersonal:
        return Icons.mail_outline;
      case InboxChannel.gmailBusiness:
        return Icons.business_center_outlined;
      case InboxChannel.sms:
        return Icons.sms_outlined;
      case InboxChannel.instagram:
        return Icons.camera_alt_outlined;
      case InboxChannel.facebook:
        return Icons.chat_bubble_outline;
      case InboxChannel.shopify:
        return Icons.shopping_bag_outlined;
      case InboxChannel.gumtree:
        return Icons.storefront_outlined;
    }
  }

  static InboxChannel fromString(String val) {
    return InboxChannel.values.firstWhere(
      (e) => e.name.toLowerCase() == val.toLowerCase() || e.displayName.toLowerCase() == val.toLowerCase(),
      orElse: () => InboxChannel.all,
    );
  }
}

enum InboxPriority {
  actionRequired,
  commercialLead,
  vip,
  lowPriority;

  String get displayName {
    switch (this) {
      case InboxPriority.actionRequired:
        return 'Action Required';
      case InboxPriority.commercialLead:
        return 'Commercial Lead';
      case InboxPriority.vip:
        return 'VIP';
      case InboxPriority.lowPriority:
        return 'Low Priority';
    }
  }

  Color get color {
    switch (this) {
      case InboxPriority.actionRequired:
        return Colors.deepOrange;
      case InboxPriority.commercialLead:
        return Colors.amber.shade700;
      case InboxPriority.vip:
        return Colors.purple.shade600;
      case InboxPriority.lowPriority:
        return Colors.blueGrey.shade400;
    }
  }

  static InboxPriority fromString(String val) {
    switch (val.toLowerCase().replaceAll('-', '_').replaceAll(' ', '_')) {
      case 'action_required':
      case 'actionrequired':
        return InboxPriority.actionRequired;
      case 'commercial_lead':
      case 'commerciallead':
        return InboxPriority.commercialLead;
      case 'vip':
        return InboxPriority.vip;
      case 'low_priority':
      case 'lowpriority':
      default:
        return InboxPriority.lowPriority;
    }
  }
}

typedef TriagePriority = InboxPriority;

enum MessageStatus {
  sent,
  delivered,
  read,
  staged;

  String get displayName {
    switch (this) {
      case MessageStatus.sent:
        return 'Sent';
      case MessageStatus.delivered:
        return 'Delivered';
      case MessageStatus.read:
        return 'Read';
      case MessageStatus.staged:
        return 'Staged';
    }
  }

  static MessageStatus fromString(String val) {
    return MessageStatus.values.firstWhere(
      (e) => e.name.toLowerCase() == val.toLowerCase(),
      orElse: () => MessageStatus.delivered,
    );
  }
}

class InboxMessage {
  final String id;
  final String threadId;
  final String senderName;
  final String senderAddress;
  final String text;
  final DateTime timestamp;
  final bool isOutgoing;
  final InboxChannel channel;
  final MessageStatus status;
  final List<String> suggestedReplies;
  final String? mediaUrl;
  final Map<String, dynamic>? richCardData;

  const InboxMessage({
    required this.id,
    required this.threadId,
    required this.senderName,
    required this.senderAddress,
    required this.text,
    required this.timestamp,
    required this.isOutgoing,
    required this.channel,
    this.status = MessageStatus.delivered,
    this.suggestedReplies = const [],
    this.mediaUrl,
    this.richCardData,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'threadId': threadId,
      'senderName': senderName,
      'senderAddress': senderAddress,
      'text': text,
      'timestamp': timestamp.toIso8601String(),
      'isOutgoing': isOutgoing,
      'channel': channel.name,
      'status': status.name,
      'suggestedReplies': suggestedReplies,
      'mediaUrl': mediaUrl,
      'richCardData': richCardData,
    };
  }

  factory InboxMessage.fromJson(Map<String, dynamic> json) {
    return InboxMessage(
      id: json['id'] as String,
      threadId: json['threadId'] as String? ?? '',
      senderName: json['senderName'] as String? ?? '',
      senderAddress: json['senderAddress'] as String? ?? '',
      text: json['text'] as String? ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
      isOutgoing: json['isOutgoing'] as bool? ?? false,
      channel: json['channel'] != null
          ? InboxChannel.fromString(json['channel'] as String)
          : InboxChannel.all,
      status: json['status'] != null
          ? MessageStatus.fromString(json['status'] as String)
          : MessageStatus.delivered,
      suggestedReplies: (json['suggestedReplies'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      mediaUrl: json['mediaUrl'] as String?,
      richCardData: json['richCardData'] as Map<String, dynamic>?,
    );
  }

  InboxMessage copyWith({
    String? id,
    String? threadId,
    String? senderName,
    String? senderAddress,
    String? text,
    DateTime? timestamp,
    bool? isOutgoing,
    InboxChannel? channel,
    MessageStatus? status,
    List<String>? suggestedReplies,
    String? mediaUrl,
    Map<String, dynamic>? richCardData,
  }) {
    return InboxMessage(
      id: id ?? this.id,
      threadId: threadId ?? this.threadId,
      senderName: senderName ?? this.senderName,
      senderAddress: senderAddress ?? this.senderAddress,
      text: text ?? this.text,
      timestamp: timestamp ?? this.timestamp,
      isOutgoing: isOutgoing ?? this.isOutgoing,
      channel: channel ?? this.channel,
      status: status ?? this.status,
      suggestedReplies: suggestedReplies ?? this.suggestedReplies,
      mediaUrl: mediaUrl ?? this.mediaUrl,
      richCardData: richCardData ?? this.richCardData,
    );
  }
}

class InboxThread {
  final String id;
  final InboxChannel channel;
  final String contactName;
  final String contactAddress;
  final String? avatarUrl;
  final String subject;
  final String lastMessagePreview;
  final DateTime lastMessageTime;
  final int unreadCount;
  final InboxPriority priority;
  final bool isPinned;
  final List<InboxMessage> messages;
  final String? aiSummary;

  const InboxThread({
    required this.id,
    required this.channel,
    required this.contactName,
    required this.contactAddress,
    this.avatarUrl,
    required this.subject,
    required this.lastMessagePreview,
    required this.lastMessageTime,
    this.unreadCount = 0,
    this.priority = InboxPriority.lowPriority,
    this.isPinned = false,
    this.messages = const [],
    this.aiSummary,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'channel': channel.name,
      'contactName': contactName,
      'contactAddress': contactAddress,
      'avatarUrl': avatarUrl,
      'subject': subject,
      'lastMessagePreview': lastMessagePreview,
      'lastMessageTime': lastMessageTime.toIso8601String(),
      'unreadCount': unreadCount,
      'priority': priority.name,
      'isPinned': isPinned,
      'messages': messages.map((m) => m.toJson()).toList(),
      'aiSummary': aiSummary,
    };
  }

  factory InboxThread.fromJson(Map<String, dynamic> json) {
    return InboxThread(
      id: json['id'] as String,
      channel: json['channel'] != null
          ? InboxChannel.fromString(json['channel'] as String)
          : InboxChannel.all,
      contactName: json['contactName'] as String? ?? '',
      contactAddress: json['contactAddress'] as String? ?? '',
      avatarUrl: json['avatarUrl'] as String?,
      subject: json['subject'] as String? ?? '',
      lastMessagePreview: json['lastMessagePreview'] as String? ?? '',
      lastMessageTime: json['lastMessageTime'] != null
          ? DateTime.parse(json['lastMessageTime'] as String)
          : DateTime.now(),
      unreadCount: json['unreadCount'] as int? ?? 0,
      priority: json['priority'] != null
          ? InboxPriority.fromString(json['priority'] as String)
          : InboxPriority.lowPriority,
      isPinned: json['isPinned'] as bool? ?? false,
      messages: (json['messages'] as List<dynamic>?)
              ?.map((m) => InboxMessage.fromJson(m as Map<String, dynamic>))
              .toList() ??
          const [],
      aiSummary: json['aiSummary'] as String?,
    );
  }

  InboxThread copyWith({
    String? id,
    InboxChannel? channel,
    String? contactName,
    String? contactAddress,
    String? avatarUrl,
    String? subject,
    String? lastMessagePreview,
    DateTime? lastMessageTime,
    int? unreadCount,
    InboxPriority? priority,
    bool? isPinned,
    List<InboxMessage>? messages,
    String? aiSummary,
  }) {
    return InboxThread(
      id: id ?? this.id,
      channel: channel ?? this.channel,
      contactName: contactName ?? this.contactName,
      contactAddress: contactAddress ?? this.contactAddress,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      subject: subject ?? this.subject,
      lastMessagePreview: lastMessagePreview ?? this.lastMessagePreview,
      lastMessageTime: lastMessageTime ?? this.lastMessageTime,
      unreadCount: unreadCount ?? this.unreadCount,
      priority: priority ?? this.priority,
      isPinned: isPinned ?? this.isPinned,
      messages: messages ?? this.messages,
      aiSummary: aiSummary ?? this.aiSummary,
    );
  }
}

class TriageResult {
  final InboxPriority priority;
  final String reasoning;
  final List<String> suggestedReplies;
  final int port;
  final int latencyMs;
  final bool isAiAssigned;
  final bool isFallback;

  const TriageResult({
    required this.priority,
    required this.reasoning,
    required this.suggestedReplies,
    required this.port,
    required this.latencyMs,
    required this.isAiAssigned,
    required this.isFallback,
  });

  factory TriageResult.heuristicFallback({
    required InboxPriority priority,
    required String reasoning,
    List<String> suggestedReplies = const [],
  }) {
    return TriageResult(
      priority: priority,
      reasoning: reasoning,
      suggestedReplies: suggestedReplies,
      port: -1,
      latencyMs: 0,
      isAiAssigned: false,
      isFallback: true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'priority': priority.name,
      'reasoning': reasoning,
      'suggestedReplies': suggestedReplies,
      'port': port,
      'latencyMs': latencyMs,
      'isAiAssigned': isAiAssigned,
      'isFallback': isFallback,
    };
  }

  factory TriageResult.fromJson(Map<String, dynamic> json) {
    return TriageResult(
      priority: json['priority'] != null
          ? InboxPriority.fromString(json['priority'] as String)
          : InboxPriority.lowPriority,
      reasoning: json['reasoning'] as String? ?? '',
      suggestedReplies: (json['suggestedReplies'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      port: json['port'] as int? ?? -1,
      latencyMs: json['latencyMs'] as int? ?? 0,
      isAiAssigned: json['isAiAssigned'] as bool? ?? false,
      isFallback: json['isFallback'] as bool? ?? true,
    );
  }
}
