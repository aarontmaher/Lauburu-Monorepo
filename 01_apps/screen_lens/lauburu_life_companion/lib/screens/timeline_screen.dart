import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class TimelineScreen extends StatefulWidget {
  const TimelineScreen({super.key});

  @override
  State<TimelineScreen> createState() => _TimelineScreenState();
}

class _TimelineScreenState extends State<TimelineScreen> {
  List<Map<String, dynamic>> _events = [];
  Map<String, dynamic>? _audioStatus;
  bool _isLoading = true;
  String? _selectedDeviceFilter;

  final List<String> _companionUrls = [
    'http://127.0.0.1:3036',
    'http://100.119.199.76:3036',
    'http://192.168.8.230:3036',
  ];

  final List<String> _hubUrls = [
    'http://192.168.8.230:18899',
    'http://100.119.199.76:18899',
    'http://127.0.0.1:18899',
  ];

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadTimeline(),
      _loadAudioStatus(),
    ]);
  }

  Future<void> _loadAudioStatus() async {
    for (final base in _hubUrls) {
      try {
        final res = await http.get(Uri.parse('$base/api/audio/status')).timeout(const Duration(seconds: 2));
        if (res.statusCode == 200) {
          setState(() {
            _audioStatus = jsonDecode(res.body);
          });
          return;
        }
      } catch (_) {}
    }
  }

  Future<void> _loadTimeline() async {
    // 1. First attempt to load authentic captures from Screen Life Companion (Port 3036)
    for (final base in _companionUrls) {
      try {
        final url = '$base/api/live_timeline?limit=100';
        final res = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 2));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final List<dynamic> raw = data['captures'] ?? [];
          if (raw.isNotEmpty) {
            final mapped = raw.map((c) {
              final ms = (c['unix_ts_ms'] as num?)?.toInt() ?? 
                         (c['timestamp'] != null ? DateTime.tryParse(c['timestamp'].toString())?.millisecondsSinceEpoch : null) ?? 
                         DateTime.now().millisecondsSinceEpoch;
              final app = (c['active_app_name'] as String?) ?? 'Mac_Node';
              final win = (c['active_window_title'] as String?) ?? '';
              final snip = (c['ocr_snippet'] as String?) ?? '';
              final conf = (c['ocr_confidence_avg'] as num?)?.toDouble() ?? 1.0;
              return <String, dynamic>{
                'timestamp': ms,
                'device_id': 'L1_Mac_Node',
                'event_type': 'Screen OCR (${(conf * 100).toInt()}%)',
                'element_text': snip,
                'window_title': win.isNotEmpty ? '$app: $win' : app,
                'audio_transcript': null,
              };
            }).toList();
            setState(() {
              _events = mapped;
              _isLoading = false;
            });
            return;
          }
        }
      } catch (_) {}
    }

    // 2. Fallback to mesh hub events (Port 18899)
    for (final base in _hubUrls) {
      try {
        final url = _selectedDeviceFilter == null
            ? '$base/api/timeline/events?limit=100'
            : '$base/api/timeline/events?limit=100&device_id=$_selectedDeviceFilter';
        final res = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 2));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          final List<dynamic> raw = data['events'] ?? [];
          setState(() {
            _events = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
            _isLoading = false;
          });
          return;
        }
      } catch (_) {}
    }

    setState(() {
      _isLoading = false;
    });
  }

  Color _getDeviceColor(String deviceId) {
    if (deviceId.contains('L1') || deviceId.contains('Mac_Node')) return Colors.cyanAccent;
    if (deviceId.contains('L5') || deviceId.contains('Air')) return Colors.lightBlueAccent;
    if (deviceId.contains('L2') || deviceId.contains('Pro')) return Colors.deepPurpleAccent;
    if (deviceId.contains('L6') || deviceId.contains('Pixel')) return Colors.greenAccent;
    if (deviceId.contains('L7') || deviceId.contains('S20')) return Colors.orangeAccent;
    if (deviceId.contains('L8') || deviceId.contains('Linux')) return Colors.amberAccent;
    return Colors.tealAccent;
  }

  String _formatDeviceName(String deviceId) {
    if (deviceId.contains('L1')) return '🖥️ Mac Mini M4';
    if (deviceId.contains('L5')) return '💻 MacBook Air M4';
    if (deviceId.contains('L2')) return '💻 MacBook Pro i7';
    if (deviceId.contains('L6')) return '📱 Pixel 10 Pro XL';
    if (deviceId.contains('L7')) return '📱 Galaxy S20+';
    if (deviceId.contains('L8')) return '🐧 Linux Head Hub';
    return deviceId;
  }

  @override
  Widget build(BuildContext context) {
    final winner = _audioStatus?['current_winner'] as String?;
    final activeDevices = (_audioStatus?['active_devices'] as Map<String, dynamic>?) ?? {};

    return Scaffold(
      appBar: AppBar(
        title: const Text('Omnipresent Mesh Timeline'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => _isLoading = true);
              _loadAll();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // 🎙️ Ambient Audio Mesh Status Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.black45,
            child: Row(
              children: [
                const Icon(Icons.mic, color: Colors.greenAccent, size: 24),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        winner != null ? 'Active Mic: ${_formatDeviceName(winner)}' : 'Awaiting Voice Detection...',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      Text(
                        'Acoustic Election: ${activeDevices.length} node(s) listening',
                        style: const TextStyle(fontSize: 11, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
                if (winner != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.greenAccent, width: 1),
                    ),
                    child: const Text('STREAMING', style: TextStyle(color: Colors.greenAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                  )
              ],
            ),
          ),
          
          // Device Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('All Mesh Devices'),
                  selected: _selectedDeviceFilter == null,
                  onSelected: (_) {
                    setState(() {
                      _selectedDeviceFilter = null;
                      _isLoading = true;
                    });
                    _loadTimeline();
                  },
                ),
                const SizedBox(width: 8),
                for (final dev in ['L1_Mac_Node', 'L5_MacBook_Air', 'L2_MacBook_Pro', 'L6_Pixel_10_Edge', 'L7_Samsung_S20', 'L8_Linux_Mini'])
                  Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: FilterChip(
                      label: Text(_formatDeviceName(dev)),
                      selected: _selectedDeviceFilter == dev,
                      onSelected: (selected) {
                        setState(() {
                          _selectedDeviceFilter = selected ? dev : null;
                          _isLoading = true;
                        });
                        _loadTimeline();
                      },
                    ),
                  ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Events Stream List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _events.isEmpty
                    ? const Center(child: Text('No events recorded across mesh devices yet.'))
                    : ListView.builder(
                        itemCount: _events.length,
                        itemBuilder: (context, index) {
                          final event = _events[index];
                          final date = DateTime.fromMillisecondsSinceEpoch(event['timestamp'] as int);
                          final deviceId = (event['device_id'] as String?) ?? 'L1_Mac_Node';
                          final type = event['event_type'] as String;
                          final text = event['element_text'] as String?;
                          final window = event['window_title'] as String?;
                          final transcript = event['audio_transcript'] as String?;

                          final isAudio = transcript != null && transcript.isNotEmpty;

                          return Card(
                            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            child: Padding(
                              padding: const EdgeInsets.all(12.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Top Row: Device Badge + Timestamp
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: _getDeviceColor(deviceId).withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: _getDeviceColor(deviceId), width: 0.8),
                                        ),
                                        child: Text(
                                          _formatDeviceName(deviceId),
                                          style: TextStyle(color: _getDeviceColor(deviceId), fontSize: 11, fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Icon(
                                        isAudio
                                            ? Icons.record_voice_over
                                            : type.toLowerCase().contains('button') || type.toLowerCase().contains('click')
                                                ? Icons.mouse
                                                : Icons.keyboard,
                                        size: 16,
                                        color: isAudio ? Colors.greenAccent : Colors.white70,
                                      ),
                                      const Spacer(),
                                      Text(
                                        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}:${date.second.toString().padLeft(2, '0')}',
                                        style: const TextStyle(fontSize: 11, color: Colors.white54),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),

                                  // Event Content
                                  if (isAudio) ...[
                                    Container(
                                      width: double.infinity,
                                      padding: const EdgeInsets.all(10),
                                      decoration: BoxDecoration(
                                        color: Colors.green.withValues(alpha: 0.08),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: Colors.green.withValues(alpha: 0.3)),
                                      ),
                                      child: Text(
                                        '🎙️ "$transcript"',
                                        style: const TextStyle(fontSize: 13, fontStyle: FontStyle.italic, color: Colors.greenAccent),
                                      ),
                                    ),
                                  ] else ...[
                                    if (window != null && window.isNotEmpty)
                                      Text(
                                        window,
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                      ),
                                    if (text != null && text.isNotEmpty) ...[
                                      const SizedBox(height: 4),
                                      Container(
                                        width: double.infinity,
                                        padding: const EdgeInsets.all(8),
                                        decoration: BoxDecoration(
                                          color: Colors.grey.withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          text,
                                          style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                                        ),
                                      ),
                                    ],
                                    Text(
                                      type,
                                      style: const TextStyle(fontSize: 11, color: Colors.white54),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
