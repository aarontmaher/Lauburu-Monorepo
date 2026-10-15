import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/ecommerce_models.dart';
import '../models/inbox_models.dart';

/// Private Local AI Triage & Smart Reply Service
/// Connects to Sovereign Master Local Orchestrator (Port 8082 qwen_38_max)
/// with automatic failover to Port 8083 (Metal LLM Worker)
/// 100% localhost execution with zero cloud token leakage.
class OmniAiTriageService {
  final http.Client _client;
  final String primaryBaseUrl;
  final String fallbackBaseUrl;
  final int primaryPort;
  final int fallbackPort;

  static const Duration probeTimeout = Duration(milliseconds: 1500);
  static const Duration inferenceTimeout = Duration(milliseconds: 15000);

  OmniAiTriageService({
    http.Client? client,
    this.primaryBaseUrl = 'http://127.0.0.1:8082',
    this.fallbackBaseUrl = 'http://127.0.0.1:8083',
    this.primaryPort = 8082,
    this.fallbackPort = 8083,
  }) : _client = client ?? http.Client();

  void dispose() {
    _client.close();
  }

  /// Probes endpoint health bounded to 1,500ms
  Future<AiModelStatus> probeModelHealth({int? port}) async {
    final targetPort = port ?? primaryPort;
    final isPrimary = targetPort == primaryPort;
    final baseUrl = isPrimary ? primaryBaseUrl : fallbackBaseUrl;
    final defaultName =
        isPrimary ? 'Qwen 3.8 Max (Master)' : 'Metal LLM Worker (8083)';

    final stopwatch = Stopwatch()..start();
    try {
      final uri = Uri.parse('$baseUrl/health');
      final response = await _client.get(uri).timeout(probeTimeout);
      stopwatch.stop();

      if (response.statusCode == 200) {
        String resolvedName = defaultName;
        try {
          final decoded = jsonDecode(response.body);
          if (decoded is Map && decoded.containsKey('service')) {
            resolvedName = decoded['service'].toString();
          }
        } catch (_) {}

        return AiModelStatus(
          port: targetPort,
          modelName: resolvedName,
          isOnline: true,
          statusMessage: 'ONLINE (${response.statusCode})',
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      } else {
        return AiModelStatus(
          port: targetPort,
          modelName: defaultName,
          isOnline: false,
          statusMessage: 'HTTP ${response.statusCode}',
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      }
    } on TimeoutException {
      stopwatch.stop();
      return AiModelStatus(
        port: targetPort,
        modelName: defaultName,
        isOnline: false,
        statusMessage: 'Probe timed out (>1500ms)',
        latencyMs: 1500,
      );
    } catch (e) {
      stopwatch.stop();
      return AiModelStatus(
        port: targetPort,
        modelName: defaultName,
        isOnline: false,
        statusMessage: 'Offline: $e',
        latencyMs: -1,
      );
    }
  }

  /// Triage a conversation thread using Sovereign Port 8082 -> Port 8083 -> Heuristic fallback
  Future<TriageResult> triageConversation({
    required InboxChannel channel,
    required String contactName,
    required String contactAddress,
    required List<Map<String, String>> recentMessages,
    String? customerTier,
  }) async {
    final stopwatch = Stopwatch()..start();
    final systemPrompt = _buildTriageSystemPrompt();
    final userPrompt = _buildTriageUserPrompt(
      channel: channel,
      contactName: contactName,
      contactAddress: contactAddress,
      recentMessages: recentMessages,
      customerTier: customerTier,
    );

    // 1. Attempt Primary Port 8082 (Qwen 3.8 Max)
    try {
      final primaryUri = Uri.parse('$primaryBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'model': 'qwen_38_max',
        'messages': [
          {'role': 'system', 'content': systemPrompt},
          {'role': 'user', 'content': userPrompt},
        ],
        'temperature': 0.2,
        'max_tokens': 350,
      });

      final response = await _client
          .post(
            primaryUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      stopwatch.stop();

      if (response.statusCode == 200) {
        final parsed = _parseTriageResponse(
          response.body,
          port: primaryPort,
          latencyMs: stopwatch.elapsedMilliseconds,
          isFallback: false,
        );
        if (parsed != null) return parsed;
      }
    } catch (e) {
      debugPrint(
          'OmniAiTriage: Port $primaryPort failed ($e), falling over to Port $fallbackPort');
    }

    // 2. Attempt Fallback Port 8083 (Metal LLM Worker)
    stopwatch.reset();
    stopwatch.start();
    try {
      final fallbackUri = Uri.parse('$fallbackBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'model': 'qwen_38_max_abliterated',
        'messages': [
          {'role': 'system', 'content': systemPrompt},
          {'role': 'user', 'content': userPrompt},
        ],
        'temperature': 0.2,
        'max_tokens': 350,
      });

      final response = await _client
          .post(
            fallbackUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      stopwatch.stop();

      if (response.statusCode == 200) {
        final parsed = _parseTriageResponse(
          response.body,
          port: fallbackPort,
          latencyMs: stopwatch.elapsedMilliseconds,
          isFallback: true,
        );
        if (parsed != null) return parsed;
      }
    } catch (e) {
      debugPrint('OmniAiTriage: Port $fallbackPort failed ($e)');
    }

    // 3. Rule 1 Zero-Mock Heuristic Fallback
    final latestText = recentMessages.isNotEmpty
        ? (recentMessages.last['text'] ?? '')
        : '';
    return computeHeuristicFallback(
      channel: channel,
      contactAddress: contactAddress,
      latestMessageText: latestText,
      customerTier: customerTier,
    );
  }

  /// Generates 2-4 contextual smart reply chips in Aaron's authentic voice.
  /// When models are offline, returns empty list `[]` (Rule 1 Zero-Mock).
  Future<List<String>> generateSmartReplies({
    required InboxChannel channel,
    required List<Map<String, String>> recentMessages,
  }) async {
    final systemPrompt = '''
You are Aaron Maher, founder of Lauburu Grappling (Melbourne, Australia).
Generate 2 to 4 concise smart reply options in your authentic voice:
- Concise, direct Australian entrepreneur/grappler tone.
- Grounded in real details: safe pickup at Altona Gate, OSKO/PayID, sample invoices to lauburu@lauburugrappling.com, 1:1 Absolute MMA cuts.
- Zero corporate fluff, no emojis, no excessive pleasantries.
Output a JSON array of strings: ["reply1", "reply2", "reply3"]
''';

    final formattedMessages = recentMessages
        .map((m) => "${m['sender'] ?? 'User'}: ${m['text'] ?? ''}")
        .join('\n');
    final userPrompt = 'Channel: ${channel.name}\nMessages:\n$formattedMessages';

    // Attempt Primary Port 8082
    try {
      final primaryUri = Uri.parse('$primaryBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'model': 'qwen_38_max',
        'messages': [
          {'role': 'system', 'content': systemPrompt},
          {'role': 'user', 'content': userPrompt},
        ],
        'temperature': 0.3,
        'max_tokens': 150,
      });

      final response = await _client
          .post(
            primaryUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      if (response.statusCode == 200) {
        final replies = _extractRepliesFromJson(response.body);
        if (replies.isNotEmpty) return replies;
      }
    } catch (_) {}

    // Attempt Fallback Port 8083
    try {
      final fallbackUri = Uri.parse('$fallbackBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'model': 'qwen_38_max_abliterated',
        'messages': [
          {'role': 'system', 'content': systemPrompt},
          {'role': 'user', 'content': userPrompt},
        ],
        'temperature': 0.3,
        'max_tokens': 150,
      });

      final response = await _client
          .post(
            fallbackUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      if (response.statusCode == 200) {
        final replies = _extractRepliesFromJson(response.body);
        if (replies.isNotEmpty) return replies;
      }
    } catch (_) {}

    // Zero-mock: Return empty list when offline
    return const [];
  }

  /// Deterministic heuristic fallback when Sovereign local models are offline
  TriageResult computeHeuristicFallback({
    required InboxChannel channel,
    required String contactAddress,
    required String latestMessageText,
    String? customerTier,
  }) {
    final lowerAddress = contactAddress.toLowerCase();
    final lowerText = latestMessageText.toLowerCase();

    // 1. VIP Contact / Elite Partner Check
    if (lowerAddress.contains('hicham') ||
        lowerAddress.contains('subliminator') ||
        customerTier?.toLowerCase() == 'elite') {
      return TriageResult.heuristicFallback(
        priority: InboxPriority.vip,
        reasoning:
            'VIP contact / key manufacturing executive or elite tier member.',
      );
    }

    // 2. Action Required Check
    final actionKeywords = [
      'meet',
      'time',
      'where',
      'when',
      'today',
      'tomorrow',
      'asap',
      'urgent',
      'confirm',
      'invoice',
      'payment',
      'does that work',
      'can you',
      'available',
    ];
    for (final kw in actionKeywords) {
      if (lowerText.contains(kw)) {
        return TriageResult.heuristicFallback(
          priority: InboxPriority.actionRequired,
          reasoning:
              'Time-sensitive action or scheduling confirmation required.',
        );
      }
    }

    // 3. Commercial Lead Check
    final commercialKeywords = [
      'buy',
      'price',
      'cash',
      'offer',
      'order',
      'stock',
      'restock',
      'sample',
      'sponsor',
      'cost',
      'discount',
      'ship',
      'tracking',
    ];
    if (channel == InboxChannel.gumtree ||
        channel == InboxChannel.shopify ||
        commercialKeywords.any((kw) => lowerText.contains(kw))) {
      return TriageResult.heuristicFallback(
        priority: InboxPriority.commercialLead,
        reasoning: 'Commercial buying inquiry or order status question.',
      );
    }

    // 4. Low Priority Default
    return TriageResult.heuristicFallback(
      priority: InboxPriority.lowPriority,
      reasoning: 'Informational update or standard notification.',
    );
  }

  String _buildTriageSystemPrompt() {
    return '''
You are the Private Local AI Triage & Executive Assistant for Aaron Maher, founder of Lauburu Grappling (Melbourne, Australia).
You are running 100% locally on Sovereign Port 8082. Zero cloud leakage.

Analyze the conversation thread and return a valid JSON object with:
1. 'priority': exactly one of ['action_required', 'commercial_lead', 'vip', 'low_priority']
2. 'reasoning': a 1-sentence explanation of the triage classification
3. 'suggested_replies': an array of 2 to 4 concise smart reply options in Aaron's authentic voice.

Aaron's Voice Guidelines:
- Concise, direct, authentic Australian grappling entrepreneur/tech builder.
- Grounded in real details: Altona Gate pickup, OSKO/PayID, sample invoices to lauburu@lauburugrappling.com, 1:1 Absolute MMA cuts.
- Zero corporate fluff, no emojis, no excessive pleasantries, safe transaction posture.
- Output pure JSON only.
''';
  }

  String _buildTriageUserPrompt({
    required InboxChannel channel,
    required String contactName,
    required String contactAddress,
    required List<Map<String, String>> recentMessages,
    String? customerTier,
  }) {
    final buffer = StringBuffer();
    buffer.writeln('Channel: ${channel.name}');
    buffer.writeln('Contact Name: $contactName');
    buffer.writeln('Contact Address: $contactAddress');
    if (customerTier != null) buffer.writeln('Customer Tier: $customerTier');
    buffer.writeln('Recent Messages:');
    for (final m in recentMessages) {
      buffer.writeln('- ${m['sender'] ?? 'User'}: ${m['text'] ?? ''}');
    }
    buffer.writeln('\nProvide your JSON triage evaluation now:');
    return buffer.toString();
  }

  TriageResult? _parseTriageResponse(
    String responseBody, {
    required int port,
    required int latencyMs,
    required bool isFallback,
  }) {
    try {
      final decoded = jsonDecode(responseBody) as Map<String, dynamic>;
      final choices = decoded['choices'] as List? ?? [];
      if (choices.isEmpty) return null;

      final message =
          (choices[0] as Map<String, dynamic>)['message'] as Map<String, dynamic>? ??
              {};
      final content = message['content']?.toString() ?? '';

      // Extract JSON substring from content if wrapped in markdown code blocks
      String jsonStr = content.trim();
      if (jsonStr.startsWith('```json')) {
        jsonStr = jsonStr.substring(7);
      }
      if (jsonStr.startsWith('```')) {
        jsonStr = jsonStr.substring(3);
      }
      if (jsonStr.endsWith('```')) {
        jsonStr = jsonStr.substring(0, jsonStr.length - 3);
      }
      jsonStr = jsonStr.trim();

      final parsedJson = jsonDecode(jsonStr) as Map<String, dynamic>;
      final priorityStr = parsedJson['priority']?.toString() ?? 'low_priority';
      final reasoning = parsedJson['reasoning']?.toString() ?? '';
      final replies = (parsedJson['suggested_replies'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          <String>[];

      return TriageResult(
        priority: InboxPriority.fromString(priorityStr),
        reasoning: reasoning,
        suggestedReplies: replies,
        port: port,
        latencyMs: latencyMs,
        isAiAssigned: true,
        isFallback: isFallback,
      );
    } catch (e) {
      debugPrint('Error parsing AI triage response: $e');
      return null;
    }
  }

  List<String> _extractRepliesFromJson(String responseBody) {
    try {
      final decoded = jsonDecode(responseBody) as Map<String, dynamic>;
      final choices = decoded['choices'] as List? ?? [];
      if (choices.isEmpty) return const [];

      final message =
          (choices[0] as Map<String, dynamic>)['message'] as Map<String, dynamic>? ??
              {};
      String content = (message['content']?.toString() ?? '').trim();

      if (content.startsWith('```json')) {
        content = content.substring(7);
      }
      if (content.startsWith('```')) {
        content = content.substring(3);
      }
      if (content.endsWith('```')) {
        content = content.substring(0, content.length - 3);
      }
      content = content.trim();

      final parsed = jsonDecode(content);
      if (parsed is List) {
        return parsed.map((e) => e.toString()).toList();
      } else if (parsed is Map && parsed.containsKey('suggested_replies')) {
        final list = parsed['suggested_replies'] as List?;
        return list?.map((e) => e.toString()).toList() ?? const [];
      }
    } catch (_) {}
    return const [];
  }
}
