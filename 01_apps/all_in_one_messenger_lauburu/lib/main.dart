import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

void main() {
  runApp(const AllInOneMessenger());
}

class AllInOneMessenger extends StatelessWidget {
  const AllInOneMessenger({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Omni Messenger Lauburu',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const UnifiedInboxScreen(),
    );
  }
}

class UnifiedInboxScreen extends StatefulWidget {
  const UnifiedInboxScreen({super.key});

  @override
  State<UnifiedInboxScreen> createState() => _UnifiedInboxScreenState();
}

class _UnifiedInboxScreenState extends State<UnifiedInboxScreen> {
  List<dynamic> _messages = [];
  bool _isLoading = false;
  String _error = "";

  // Connects to the real Python Unified Bridge via the mesh
  Future<void> _fetchMessages() async {
    setState(() {
      _isLoading = true;
      _error = "";
    });

    try {
      // Try local port 5050 first, fallback to LAN IP
      http.Response response;
      try {
        response = await http.get(Uri.parse('http://127.0.0.1:5050/inbox')).timeout(const Duration(seconds: 2));
      } catch (_) {
        response = await http.get(Uri.parse('http://192.168.8.230:5050/inbox')).timeout(const Duration(seconds: 3));
      }
      
      if (response.statusCode == 200) {
        final decoded = json.decode(response.body);
        setState(() {
          if (decoded is Map && decoded.containsKey('messages')) {
            _messages = decoded['messages'];
          } else if (decoded is List) {
            _messages = decoded;
          }
        });
      } else {
        setState(() {
          _error = "Server Error: ${response.statusCode}";
        });
      }
    } catch (e) {
      setState(() {
        _error = "Waiting for Python Bridge on port 5050...";
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _fetchMessages();
  }

  IconData _getIconForPlatform(String platform) {
    final p = platform.toLowerCase();
    if (p.contains('email') || p.contains('workspace') || p.contains('gmail')) return Icons.email;
    if (p.contains('gumtree')) return Icons.storefront;
    if (p.contains('facebook')) return Icons.shopping_bag;
    if (p.contains('signal')) return Icons.message;
    if (p.contains('whatsapp')) return Icons.chat;
    return Icons.textsms;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Omni Messenger Lauburu'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchMessages,
          )
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _error.isNotEmpty
          ? Center(child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.cloud_off, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  Text(_error, textAlign: TextAlign.center, style: const TextStyle(color: Colors.redAccent)),
                  const SizedBox(height: 16),
                  const Text("Run 'real_unified_backend.py' on port 5050 to pipe unified feeds.", textAlign: TextAlign.center),
                ],
              ),
            ))
          : ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final triage = msg['triage'] as Map<String, dynamic>?;
                final priority = triage?['priority'] as String?;
                final content = msg['preview'] ?? msg['content'] ?? '';
                final isUrgent = priority?.contains('P0') == true || priority?.contains('P1') == true;

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: isUrgent ? Colors.redAccent.withValues(alpha: 0.2) : Theme.of(context).colorScheme.primaryContainer,
                      child: Icon(
                        _getIconForPlatform(msg['platform'] ?? ''),
                        color: isUrgent ? Colors.redAccent : Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    ),
                    title: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            msg['sender'] ?? 'Unknown Sender',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (priority != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: isUrgent ? Colors.red.withValues(alpha: 0.2) : Colors.blue.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              priority.split(' - ').first,
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: isUrgent ? Colors.redAccent : Colors.lightBlueAccent,
                              ),
                            ),
                          ),
                      ],
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(content, maxLines: 2, overflow: TextOverflow.ellipsis),
                        if (triage?['suggested_reply'] != null) ...[
                          const SizedBox(height: 6),
                          Text(
                            "💡 AI Suggestion: ${triage!['suggested_reply']}",
                            style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: Colors.greenAccent),
                          ),
                        ]
                      ],
                    ),
                    trailing: Text(
                      msg['timestamp'] ?? '',
                      style: const TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                    onTap: () {},
                  ),
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Open compose dialog supporting all protocols
        },
        child: const Icon(Icons.create),
      ),
    );
  }
}
