// 01_apps/port_4000_flutter_rust/flutter_ui/lib/services/omnichannel_knowledge_client.dart
// =========================================================================================
// Flutter Client for Screen Lens Omnichannel Knowledge Engine & Voice Coding IDE.
// Connects to:
// - Knowledge Hub: http://127.0.0.1:4004/api/knowledge
// - Telemetry Hub: http://127.0.0.1:4001/api/telemetry
// - Live MJPEG Screen Stream: http://127.0.0.1:4003/stream.mjpg

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class OmnichannelSearchResult {
  final String query;
  final int totalMatches;
  final List<dynamic> chromeResearch;
  final List<dynamic> personalTasks;
  final List<dynamic> antigravityChats;
  final List<dynamic> monorepoArchitecture;

  OmnichannelSearchResult({
    required this.query,
    required this.totalMatches,
    required this.chromeResearch,
    required this.personalTasks,
    required this.antigravityChats,
    required this.monorepoArchitecture,
  });

  factory OmnichannelSearchResult.fromJson(Map<String, dynamic> json) {
    return OmnichannelSearchResult(
      query: json['query'] ?? '',
      totalMatches: json['total_matches'] ?? 0,
      chromeResearch: json['chrome_research'] ?? [],
      personalTasks: json['personal_tasks'] ?? [],
      antigravityChats: json['antigravity_chats'] ?? [],
      monorepoArchitecture: json['monorepo_architecture'] ?? [],
    );
  }
}

class OmnichannelKnowledgeClient {
  final String baseUrl;
  final http.Client _client;

  OmnichannelKnowledgeClient({
    this.baseUrl = 'http://127.0.0.1:4004',
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// High-speed query across Chrome KB, Antigravity chats, LifeOps, and Monorepo
  Future<OmnichannelSearchResult> search(String query) async {
    final uri = Uri.parse('$baseUrl/api/knowledge/search?q=${Uri.encodeComponent(query)}');
    final response = await _client.get(uri).timeout(const Duration(seconds: 2));

    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(response.body);
      return OmnichannelSearchResult.fromJson(data);
    } else {
      throw Exception('Failed to search omnichannel knowledge hub: ${response.statusCode}');
    }
  }

  /// Fetches the unified executive digest
  Future<Map<String, dynamic>> getDigest() async {
    final uri = Uri.parse('$baseUrl/api/knowledge/digest');
    final response = await _client.get(uri).timeout(const Duration(seconds: 2));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to fetch omnichannel digest: ${response.statusCode}');
    }
  }

  /// Voice command dispatcher translating speech transcripts to AST injection actions
  Map<String, dynamic> parseVoiceCommand(String transcript) {
    final text = transcript.trim().toLowerCase();
    if (text.startsWith('search ') || text.startsWith('find ')) {
      final q = transcript.replaceFirst(RegExp(r'^(search|find)\s+', caseSensitive: false), '');
      return {'command': 'SEARCH', 'query': q};
    } else if (text.startsWith('def ') || text.startsWith('create function ')) {
      final name = transcript.replaceFirst(RegExp(r'^(def|create function)\s+', caseSensitive: false), '').trim();
      return {'command': 'DEFINE_FUNCTION', 'name': name};
    } else if (text.contains('verify') || text.contains('proof')) {
      return {'command': 'VERIFY_TRI_PROOF'};
    }
    return {'command': 'RAW_VOICE_NOTE', 'text': transcript};
  }

  void dispose() {
    _client.close();
  }
}
