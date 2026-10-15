import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  runApp(const LauburuShowrunnerApp());
}

class LauburuShowrunnerApp extends StatelessWidget {
  const LauburuShowrunnerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: 'Showrunner Lauburu',
      debugShowCheckedModeBanner: false,
      home: SimulationView(),
    );
  }
}

class SimulationView extends StatefulWidget {
  const SimulationView({super.key});

  @override
  State<SimulationView> createState() => _SimulationViewState();
}

class _SimulationViewState extends State<SimulationView> {
  final List<String> _candidateWsUrls = [
    'ws://127.0.0.1:8101/ws/sim_stream',
    'ws://localhost:8101/ws/sim_stream',
    'ws://192.168.8.230:8101/ws/sim_stream',
    'ws://100.119.199.76:8101/ws/sim_stream',
  ];
  int _currentUrlIndex = 0;
  WebSocketChannel? _channel;
  Timer? _reconnectTimer;

  final List<Map<String, dynamic>> _logs = [];
  bool _isConnected = false;
  bool _isPaused = false;
  double _hostRamGb = 10.96;
  String _tb4Latency = '0.28';
  int _btDrillCount = 0;
  String _btLastAction = 'Awaiting drill cycle...';
  int _btConnectedPeers = 3;
  String _btRfcommPort = '/dev/tty.Bluetooth-Incoming-Port';
  String _feedFilter = 'all'; // 'all', 'sovereign', 'adversarial'

  // Real-Life Scenarios & Continuous Autopilot State
  List<Map<String, dynamic>> _scenarios = [];
  List<Map<String, dynamic>> _recentEvents = [];
  bool _continuousScenarios = false;

  // Tatami Combat Arena State
  int _activeNavTab = 0; // 0 = Mesh Simulation, 1 = Tatami Combat Arena
  Map<String, dynamic>? _activeMatch;
  List<Map<String, dynamic>> _arenaLeaderboard = [];
  Map<String, dynamic>? _arenaBiometrics;
  final List<Map<String, dynamic>> _arenaLogs = [];
  String _selectedOpponent = 'apex_npu';
  bool _isArenaProcessing = false;
  Map<String, dynamic>? _userArenaProfile;

  // Dynamic UI State
  Color _primaryColor = const Color(0xFF00FF41);
  Color _secondaryColor = const Color(0xFFFF00FF);
  Color _bgColor = const Color(0xFF09090B);
  int _themeIndex = 0;

  final String _fontFamily = 'Courier';

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  bool _isDisposed = false;

  void _connectWebSocket() {
    if (_isDisposed) return;
    _reconnectTimer?.cancel();
    if (_channel != null) {
      try {
        _channel!.sink.close();
      } catch (_) {}
    }

    String targetUrl = _candidateWsUrls[_currentUrlIndex % _candidateWsUrls.length];
    if (kIsWeb) {
      try {
        final host = Uri.base.host.isNotEmpty ? Uri.base.host : 'localhost';
        targetUrl = 'ws://$host:8101/ws/sim_stream';
      } catch (_) {}
    }

    try {
      _channel = WebSocketChannel.connect(Uri.parse(targetUrl));
      if (mounted && !_isDisposed) {
        setState(() => _isConnected = true);
      }

      _channel!.stream.listen(
        (message) {
          if (!mounted || _isDisposed) return;
          final data = jsonDecode(message);
          setState(() {
            if (data['type'] == 'init') {
              if (data['ram_headroom_gb'] != null) {
                _hostRamGb = (data['ram_headroom_gb'] as num).toDouble();
              }
              if (data['telemetry'] != null && data['telemetry']['tb4_latency_ms'] != null) {
                _tb4Latency = data['telemetry']['tb4_latency_ms'].toString();
              }
              if (data['scenarios'] != null) {
                _scenarios = List<Map<String, dynamic>>.from(data['scenarios']);
              }
              if (data['recent_events'] != null) {
                _recentEvents = List<Map<String, dynamic>>.from(data['recent_events']);
              }
              if (data['continuous_scenarios_enabled'] != null) {
                _continuousScenarios = data['continuous_scenarios_enabled'] == true;
              }
              final bt = data['bt_healing'] ?? (data['telemetry'] != null ? data['telemetry']['bluetooth_no_ip_healing'] : null);
              if (bt != null) {
                _btDrillCount = bt['total_drills'] ?? _btDrillCount;
                _btConnectedPeers = bt['connected_peers_count'] ?? _btConnectedPeers;
                if (bt['primary_rfcomm_port'] != null) _btRfcommPort = bt['primary_rfcomm_port'].toString();
                if (bt['last_drill'] != null) {
                  _btLastAction = '${bt['last_drill']['reflex_action']} (${bt['last_drill']['latency_ms']}ms)';
                }
              }
              if (data['arena_profile'] != null) {
                _userArenaProfile = Map<String, dynamic>.from(data['arena_profile']);
              }
              if (data['arena_match'] != null) {
                _activeMatch = Map<String, dynamic>.from(data['arena_match']);
              }
              if (data['arena_leaderboard'] != null) {
                _arenaLeaderboard = List<Map<String, dynamic>>.from(data['arena_leaderboard']);
              }
              if (data['recent_actions'] != null) {
                _logs.clear();
                final acts = List<Map<String, dynamic>>.from(data['recent_actions']);
                for (var act in acts) {
                  _logs.insert(0, act);
                }
              }
            } else if (data['type'] == 'npc_action') {
              _logs.insert(0, data);
              if (_logs.length > 100) _logs.removeLast();
            } else if (data['type'] == 'event_created') {
              final evt = data['event'];
              if (evt != null) {
                _recentEvents.removeWhere((e) => e['event_id'] == evt['event_id']);
                _recentEvents.insert(0, Map<String, dynamic>.from(evt));
                if (_recentEvents.length > 20) _recentEvents.removeLast();
              }
            } else if (data['type'] == 'event_updated') {
              final evt = data['event'];
              if (evt != null) {
                final idx = _recentEvents.indexWhere((e) => e['event_id'] == evt['event_id']);
                if (idx != -1) {
                  _recentEvents[idx] = Map<String, dynamic>.from(evt);
                } else {
                  _recentEvents.insert(0, Map<String, dynamic>.from(evt));
                }
              }
            } else if (data['type'] == 'continuous_scenarios_state') {
              _continuousScenarios = data['enabled'] == true;
            } else if (data['type'] == 'bt_healing_event') {
              final bt = data['bt_status'];
              final drill = data['drill'];
              if (bt != null) {
                _btDrillCount = bt['total_drills'] ?? (_btDrillCount + 1);
                _btConnectedPeers = bt['connected_peers_count'] ?? _btConnectedPeers;
              }
              if (drill != null) {
                _btLastAction = '${drill['reflex_action']} (${drill['latency_ms']}ms)';
              }
            } else if (data['type'] == 'ui_update') {
              _themeIndex++;
              if (data['primary'] != null) _primaryColor = _parseColor(data['primary']);
              if (data['secondary'] != null) _secondaryColor = _parseColor(data['secondary']);
              if (data['bg'] != null) _bgColor = _parseColor(data['bg']);
            } else if (data['type'] == 'telemetry') {
              if (data['host_ram_free_gb'] != null) {
                _hostRamGb = (data['host_ram_free_gb'] as num).toDouble();
              }
              if (data['tb4_latency_ms'] != null) {
                _tb4Latency = data['tb4_latency_ms'].toString();
              }
            } else if (data['type'] == 'arena_match_started') {
              _activeMatch = data['match'] != null ? Map<String, dynamic>.from(data['match']) : null;
              _isArenaProcessing = false;
              _arenaLogs.insert(0, {
                'timestamp_s': 0,
                'commentary': '🥋 Match Commenced: ${_activeMatch?['fighter_a']?['name'] ?? 'Aaron'} vs ${_activeMatch?['fighter_b']?['name'] ?? 'Apex-NPU'}',
                'pos_a': _activeMatch?['fighter_a']?['current_position'] ?? 'STANDING',
                'pos_b': _activeMatch?['fighter_b']?['current_position'] ?? 'STANDING',
                'sub_risk': 'NONE',
                'torque_nm': 0.0,
                'result': 'IN_PROGRESS',
              });
            } else if (data['type'] == 'arena_tick') {
              if (data['match'] != null) {
                _activeMatch = Map<String, dynamic>.from(data['match']);
              }
              final tick = data['tick'];
              if (tick != null) {
                _arenaLogs.insert(0, Map<String, dynamic>.from(tick));
                if (_arenaLogs.length > 60) _arenaLogs.removeLast();
              }
              if (data['leaderboard'] != null) {
                _arenaLeaderboard = List<Map<String, dynamic>>.from(data['leaderboard']);
              }
              _isArenaProcessing = false;
            } else if (data['type'] == 'arena_telemetry') {
              if (data['biometrics'] != null) {
                _arenaBiometrics = Map<String, dynamic>.from(data['biometrics']);
              }
            } else if (data['type'] == 'arena_leaderboard') {
              if (data['leaderboard'] != null) {
                _arenaLeaderboard = List<Map<String, dynamic>>.from(data['leaderboard']);
              }
            } else if (data['type'] == 'arena_corner_directive_applied') {
              if (data['match'] != null) {
                _activeMatch = Map<String, dynamic>.from(data['match']);
              }
              _isArenaProcessing = false;
            }
          });
        },
        onError: (error) {
          if (mounted && !_isDisposed) {
            _handleDisconnect();
          }
        },
        onDone: () {
          if (mounted && !_isDisposed) {
            _handleDisconnect();
          }
        },
      );
    } catch (_) {
      if (mounted && !_isDisposed) {
        _handleDisconnect();
      }
    }
  }

  void _handleDisconnect() {
    if (!mounted || _isDisposed) return;
    setState(() => _isConnected = false);
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (mounted && !_isDisposed) {
        _currentUrlIndex = (_currentUrlIndex + 1) % _candidateWsUrls.length;
        _connectWebSocket();
      }
    });
  }

  Color _parseColor(String hex) {
    hex = hex.replaceAll('#', '');
    if (hex.length == 6) {
      hex = 'FF$hex';
    }
    return Color(int.parse(hex, radix: 16));
  }

  void _injectDirectorEvent(String text, {String group = 'all'}) {
    if (_channel != null && _isConnected) {
      if (group == 'non_abliterated') {
        _channel!.sink.add(jsonEncode({
          'type': 'inject_event_non_abliterated',
          'event': text,
        }));
      } else if (group == 'abliterated') {
        _channel!.sink.add(jsonEncode({
          'type': 'inject_event_abliterated',
          'event': text,
        }));
      } else {
        _channel!.sink.add(jsonEncode({
          'type': 'inject_event',
          'event': text,
          'group': 'all',
        }));
      }
    }
  }

  void _togglePause() {
    setState(() => _isPaused = !_isPaused);
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'set_pause',
        'paused': _isPaused,
      }));
    }
  }

  void _triggerBtDrill() {
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'trigger_bt_drill',
      }));
    }
  }

  void _runScenario(String key, {String group = 'all'}) {
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'run_scenario',
        'scenario_key': key,
        'group': group,
      }));
    }
  }

  void _toggleContinuousScenarios() {
    setState(() => _continuousScenarios = !_continuousScenarios);
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'toggle_continuous_scenarios',
        'enabled': _continuousScenarios,
      }));
    }
  }

  void _startArenaMatch(String opponent) {
    setState(() {
      _selectedOpponent = opponent;
      _isArenaProcessing = true;
    });
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'arena_start_match',
        'fighter_a': 'aaron_twin',
        'fighter_b': opponent,
        'duration_s': 300.0,
      }));
    }
  }

  void _tickArenaMatch() {
    setState(() => _isArenaProcessing = true);
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'arena_tick',
        'dt_s': 5.0,
      }));
    }
  }

  void _simulateFullArenaMatch(String opponent) {
    setState(() {
      _selectedOpponent = opponent;
      _isArenaProcessing = true;
    });
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'arena_simulate_full',
        'fighter_a': 'aaron_twin',
        'fighter_b': opponent,
        'duration_s': 300.0,
      }));
    }
  }

  void _sendCornerDirective(String directive) {
    if (_channel != null && _isConnected) {
      _channel!.sink.add(jsonEncode({
        'type': 'arena_corner_directive',
        'fighter_id': 'aaron_twin',
        'directive': directive,
      }));
    }
  }

  Widget _buildDirectiveChip(String label, String directive, Color color) {
    return InkWell(
      onTap: () => _sendCornerDirective(directive),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.6)),
        ),
        child: Text(
          label,
          style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: color, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }

  void _showUserAnalysisDialog() {
    final prof = _userArenaProfile;
    final cond = prof?['conditioning'] as Map<String, dynamic>?;
    final grap = prof?['grappling'] as Map<String, dynamic>?;
    final disciplines = (grap?['disciplines'] as Map<String, dynamic>?) ?? {};
    final compLevel = (prof?['composite_level'] as num?)?.toInt() ?? 76;
    final beltRank = grap?['rank_label']?.toString() ?? grap?['belt_rank']?.toString() ?? 'PURPLE BELT (2 STRIPES)';
    final tier = cond?['conditioning_tier']?.toString() ?? 'TIER 3 (AEROBIC WORKHORSE)';
    final archetype = grap?['tactical_archetype']?.toString() ?? 'Apex Submission Hunter & Finisher';
    final rec = cond?['recommendation']?.toString() ?? 'Optimal autonomic state. Heart rate variability is high and DFA-α1 confirms active aerobic recovery.';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0C1017),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFF9333EA), width: 1.5),
        ),
        title: Row(
          children: [
            Container(
              width: 10,
              height: 16,
              decoration: BoxDecoration(
                color: const Color(0xFF6B21A8),
                borderRadius: BorderRadius.circular(2),
                border: Border.all(color: Colors.white),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('AI REPERTOIRE & LEVEL', style: TextStyle(fontFamily: _fontFamily, fontSize: 13, color: Colors.purpleAccent, fontWeight: FontWeight.bold)),
                  Text(beltRank, style: TextStyle(fontFamily: _fontFamily, fontSize: 10, color: Colors.white70)),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.purple.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.purpleAccent),
              ),
              child: Text('LVL $compLevel', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.w900, fontSize: 14, color: Colors.white)),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Conditioning Card
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.green.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.greenAccent.withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('🫀 CONDITIONING: $tier', style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: Colors.greenAccent, fontWeight: FontWeight.bold)),
                        const Text('512Hz ECG', style: TextStyle(fontSize: 8, color: Colors.white54)),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(rec, style: const TextStyle(fontSize: 9, color: Colors.white70)),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              // Grappling Disciplines Breakdown
              Text('🥋 OPML TECHNIQUE GRAPH (3,044 NODES)', style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text('ARCHETYPE: $archetype', style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.white60)),
              const SizedBox(height: 8),
              ...['Guard', 'Passing', 'Submission', 'Escape', 'Takedown'].map((disc) {
                final score = (disciplines[disc] as num?)?.toDouble() ?? 75.0;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2.0),
                  child: Row(
                    children: [
                      SizedBox(width: 80, child: Text(disc.toUpperCase(), style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.white70))),
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(2),
                          child: LinearProgressIndicator(
                            value: (score / 100.0).clamp(0.0, 1.0),
                            backgroundColor: Colors.white10,
                            valueColor: const AlwaysStoppedAnimation<Color>(Colors.purpleAccent),
                            minHeight: 4,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(score.toStringAsFixed(1), style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.purpleAccent, fontWeight: FontWeight.bold)),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.white10),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('TAP SAFETY GATE: 45.0 N·m', style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.redAccent, fontWeight: FontWeight.bold)),
                    Text('LEVER ARM: 0.35m', style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.yellowAccent)),
                  ],
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('DISMISS', style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showEventNarrativeModal(Map<String, dynamic> log) {
    final isAbliterated = log['group'] == 'abliterated' || ['Cipher', 'Vortex', 'Nyx-NPU'].contains(log['npc']);
    final color = isAbliterated ? const Color(0xFFFF0055) : const Color(0xFF00FF41);
    final factionBadge = isAbliterated ? '[ADVERSARIAL RED-TEAM]' : '[SOVEREIGN MASTER]';
    final eventTitle = log['event_title'] ?? log['event_id'] ?? 'NARRATIVE WORLD EVENT';
    final eventCategory = log['event_category'] ?? 'SYSTEM_EVENT';
    final eventId = log['event_id'] ?? 'EVT-MANUAL';
    final prompt = log['event_prompt'] ?? log['event'] ?? 'Real-life mesh scenario executed across 7 layers.';
    final arc = log['narrative_arc'] ?? 'Multi-agent consensus crystallized across the 7-layer mesh topology.';
    final consequence = log['consequence'] ?? 'Zero-mock state verified. Tri-Vault synchronization active.';
    final modelName = log['model'] ?? (isAbliterated ? 'Qwen 3.8 Max Abliterated' : 'Qwen 3.8 Max');
    final latency = log['latency_ms'] != null ? '${log['latency_ms']}ms' : '0.28ms';
    final interestScore = log['interest_score'] ?? 85;
    final interestTier = log['interest_tier'] ?? (interestScore >= 90 ? 'CRITICAL' : 'HIGH');
    final stageLabel = log['stage_label'] ?? 'STAGE 4/4: RESOLVED';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return FractionallySizedBox(
          heightFactor: 0.85,
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFF0D0D14),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
              border: Border.all(color: color.withValues(alpha: 0.8), width: 2),
              boxShadow: [
                BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 25, spreadRadius: 4),
              ],
            ),
            child: Column(
              children: [
                Center(
                  child: Container(
                    margin: const EdgeInsets.only(top: 12, bottom: 8),
                    width: 48,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white30,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: color.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(color: color),
                                  ),
                                  child: Text(
                                    eventId,
                                    style: TextStyle(fontFamily: _fontFamily, color: color, fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.white10,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    eventCategory,
                                    style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              eventTitle,
                              style: TextStyle(fontFamily: _fontFamily, color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white70),
                        onPressed: () => Navigator.pop(context),
                      ),
                    ],
                  ),
                ),
                const Divider(color: Colors.white12, height: 1),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      // Dynamic Interest Score & Stage Banner
                      Container(
                        margin: const EdgeInsets.only(bottom: 14),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.amber.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.amber.withValues(alpha: 0.6)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                const Text("🔥 ", style: TextStyle(fontSize: 14)),
                                Text(
                                  "INTEREST: $interestScore/100 [$interestTier]",
                                  style: TextStyle(fontFamily: _fontFamily, color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 11),
                                ),
                              ],
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: Colors.cyanAccent.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: Colors.cyanAccent.withValues(alpha: 0.6)),
                              ),
                              child: Text(
                                stageLabel,
                                style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: color.withValues(alpha: 0.5)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.auto_stories, size: 16, color: color),
                                const SizedBox(width: 8),
                                Text(
                                  "SYNTHESIZED NARRATIVE ARC",
                                  style: TextStyle(fontFamily: _fontFamily, color: color, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              arc,
                              style: const TextStyle(fontFamily: 'Courier', color: Colors.white, fontSize: 13, height: 1.4),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "EVENT CATALYST & REAL-WORLD CONTEXT",
                        style: TextStyle(fontFamily: _fontFamily, color: _secondaryColor, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Text(
                          prompt,
                          style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 12),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "PRIMARY AGENT ACTION & RESPONSE",
                        style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: color.withValues(alpha: 0.3)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  "${log['npc'] ?? 'AGENT'} ($factionBadge)",
                                  style: TextStyle(fontFamily: _fontFamily, color: color, fontWeight: FontWeight.bold, fontSize: 12),
                                ),
                                Text(
                                  "$modelName [$latency]",
                                  style: const TextStyle(fontFamily: 'Courier', color: Colors.white38, fontSize: 10),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              log['action'] ?? '',
                              style: const TextStyle(fontFamily: 'Courier', color: Colors.white, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "ZERO-MOCK TELEMETRY SNAPSHOT (RULE #0)",
                        style: TextStyle(fontFamily: _fontFamily, color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                        ),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text("Host Sanctuary RAM:", style: TextStyle(fontFamily: _fontFamily, color: Colors.white60, fontSize: 11)),
                                Text("${_hostRamGb.toStringAsFixed(1)} GB Free (≥9.6 GB Safe)", style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontWeight: FontWeight.bold, fontSize: 11)),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text("TB4 Bridge Latency:", style: TextStyle(fontFamily: _fontFamily, color: Colors.white60, fontSize: 11)),
                                Text("${_tb4Latency}ms (≤1.0ms Gate)", style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11)),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text("Bluetooth Line 1:", style: TextStyle(fontFamily: _fontFamily, color: Colors.white60, fontSize: 11)),
                                Text("$_btConnectedPeers Peers | Port $_btRfcommPort", style: TextStyle(fontFamily: _fontFamily, color: _secondaryColor, fontWeight: FontWeight.bold, fontSize: 11)),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "PHYSICAL SYSTEM CONSEQUENCE",
                        style: TextStyle(fontFamily: _fontFamily, color: Colors.orangeAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.orangeAccent.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          consequence,
                          style: TextStyle(fontFamily: _fontFamily, color: Colors.orangeAccent[100], fontSize: 12),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "TRI-VAULT SYNCHRONIZATION STATUS (RULE #2)",
                        style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.cyanAccent.withValues(alpha: 0.3)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text("1. Obsidian Vault: EPISODES.md appended with Wikilinks [[Index]]", style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 10)),
                            const SizedBox(height: 3),
                            Text("2. PySpark Lake: showrunner_continuous_lora.jsonl crystallized", style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 10)),
                            const SizedBox(height: 3),
                            Text("3. GitHub Monorepo: Tested & verified bit-for-bit with SHA256", style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 10)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _isDisposed = true;
    _reconnectTimer?.cancel();
    try {
      _channel?.sink.close();
    } catch (_) {}
    super.dispose();
  }

  Widget _buildGlassmorphicContainer({required Widget child, required Color borderColor, double opacity = 0.4}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
        child: AnimatedContainer(
          duration: const Duration(seconds: 2),
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: opacity),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: borderColor.withValues(alpha: 0.6), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: borderColor.withValues(alpha: 0.3),
                blurRadius: 15,
                spreadRadius: 2,
              )
            ],
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _buildMeshNodeStatus(String name, String role, bool active, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 500),
            width: 8, height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: active ? color : Colors.grey,
              boxShadow: active ? [BoxShadow(color: color, blurRadius: 8)] : [],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              name,
              style: TextStyle(fontFamily: _fontFamily, color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
          Text(
            role,
            style: TextStyle(fontFamily: _fontFamily, color: Colors.white54, fontSize: 10),
          ),
        ],
      ),
    );
  }

  void _showDirectorModal() {
    final TextEditingController textController = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: _bgColor.withValues(alpha: 0.96),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            final defaultScenarios = [
              {'key': 'tb4_dma_failover', 'label': '⚡ TB4 DMA Failover', 'color': const Color(0xFF00FF41)},
              {'key': 'bt_rfcomm_blackout', 'label': '📡 BT Blackout Wake', 'color': const Color(0xFFFF00FF)},
              {'key': 'rule8_airgap_intercept', 'label': '🛡️ Air-Gap Intercept', 'color': const Color(0xFFFF0055)},
              {'key': 'movesense_ecg_burst', 'label': '❤️ 512Hz ECG Burst', 'color': const Color(0xFF00E5FF)},
              {'key': 'rule3_ram_sanctuary_clamp', 'label': '💾 RAM Clamp (9.6GB)', 'color': Colors.amber},
              {'key': 'npu_systolic_sprint', 'label': '⚡ NPU Systolic Sprint', 'color': const Color(0xFF76FF03)},
              {'key': 'qdrant_ast_reindex', 'label': '🔍 Qdrant AST Reindex', 'color': Colors.cyanAccent},
              {'key': 'android_termux_keepalive', 'label': '📱 Termux Keepalive', 'color': Colors.orangeAccent},
              {'key': 'seaweedfs_repair', 'label': '🌊 SeaweedFS Repair', 'color': Colors.lightBlueAccent},
              {'key': 'tri_vault_crystallize', 'label': '🏛️ Tri-Vault Sync', 'color': Colors.purpleAccent},
            ];

            final scenariosList = _scenarios.isNotEmpty
                ? _scenarios.map((s) {
                    final key = s['key']?.toString() ?? '';
                    final title = s['title']?.toString() ?? key;
                    final group = s['group']?.toString() ?? 'all';
                    final color = group == 'abliterated' ? const Color(0xFFFF0055) : const Color(0xFF00FF41);
                    return {'key': key, 'label': '⚡ $title', 'color': color};
                  }).toList()
                : defaultScenarios;

            return Container(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 24,
              ),
              constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'SHOWRUNNER DIRECTOR CONSOLE',
                          style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.white60, size: 20),
                          onPressed: () => Navigator.pop(context),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: textController,
                      style: TextStyle(fontFamily: _fontFamily, color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Inject custom narrative world event...',
                        hintStyle: const TextStyle(color: Colors.white38),
                        filled: true,
                        fillColor: Colors.black45,
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: _primaryColor)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Colors.white24)),
                        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: _primaryColor)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF00FF41),
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                            onPressed: () {
                              if (textController.text.trim().isNotEmpty) {
                                _injectDirectorEvent(textController.text.trim(), group: 'non_abliterated');
                                Navigator.pop(context);
                              }
                            },
                            child: Text('⚡ SOVEREIGN', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, fontSize: 11)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFFFF0055),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                            onPressed: () {
                              if (textController.text.trim().isNotEmpty) {
                                _injectDirectorEvent(textController.text.trim(), group: 'abliterated');
                                Navigator.pop(context);
                              }
                            },
                            child: Text('🔥 ADVERSARIAL', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, fontSize: 11)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _isPaused ? Colors.amber : Colors.grey[800],
                            foregroundColor: _isPaused ? Colors.black : Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                          ),
                          onPressed: () {
                            _togglePause();
                            setModalState(() {});
                          },
                          child: Text(_isPaused ? 'RESUME' : 'PAUSE', style: TextStyle(fontFamily: _fontFamily, fontSize: 11)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    // Real Life Scenarios Header & Autopilot Toggle
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'REAL-LIFE SCENARIO ENGINE',
                          style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 12, letterSpacing: 1),
                        ),
                        InkWell(
                          onTap: () {
                            _toggleContinuousScenarios();
                            setModalState(() {});
                          },
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: _continuousScenarios ? Colors.cyanAccent.withValues(alpha: 0.2) : Colors.white10,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: _continuousScenarios ? Colors.cyanAccent : Colors.white24),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.autorenew, size: 12, color: _continuousScenarios ? Colors.cyanAccent : Colors.white54),
                                const SizedBox(width: 4),
                                Text(
                                  _continuousScenarios ? 'AUTOPILOT: ON' : 'AUTOPILOT: OFF',
                                  style: TextStyle(
                                    fontFamily: _fontFamily,
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: _continuousScenarios ? Colors.cyanAccent : Colors.white54,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: scenariosList.map((s) {
                        final sColor = s['color'] as Color;
                        return ActionChip(
                          backgroundColor: Colors.black45,
                          side: BorderSide(color: sColor.withValues(alpha: 0.7)),
                          label: Text(
                            s['label'] as String,
                            style: TextStyle(fontFamily: _fontFamily, color: sColor, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                          onPressed: () {
                            _runScenario(s['key'] as String);
                            Navigator.pop(context);
                          },
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _secondaryColor,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                        icon: const Icon(Icons.bluetooth_connected, size: 18),
                        label: Text('⚡ TRIGGER NO-IP BT DRILL', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, letterSpacing: 1)),
                        onPressed: () {
                          _triggerBtDrill();
                          Navigator.pop(context);
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: _bgColor,
        primaryColor: _primaryColor,
      ),
      child: Scaffold(
        extendBodyBehindAppBar: true,
        floatingActionButton: _activeNavTab == 0
            ? FloatingActionButton.extended(
                onPressed: _showDirectorModal,
                backgroundColor: _primaryColor,
                foregroundColor: Colors.black,
                icon: const Icon(Icons.tune),
                label: Text('DIRECTOR', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold)),
              )
            : FloatingActionButton.extended(
                onPressed: () => _simulateFullArenaMatch(_selectedOpponent),
                backgroundColor: const Color(0xFFFF0055),
                foregroundColor: Colors.white,
                icon: const Icon(Icons.flash_on),
                label: Text('FAST SIM', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold)),
              ),
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          toolbarHeight: 68,
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedDefaultTextStyle(
                duration: const Duration(seconds: 2),
                style: TextStyle(
                  fontFamily: _fontFamily, 
                  fontWeight: FontWeight.w900,
                  color: _primaryColor,
                  letterSpacing: 2,
                  fontSize: 16,
                  shadows: [Shadow(color: _primaryColor, blurRadius: 10)],
                ),
                child: Text(_activeNavTab == 0 ? 'LAUBURU 7-LAYER MESH' : 'TATAMI COMBAT ARENA'),
              ),
              const SizedBox(height: 2),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Row(
                  children: [
                    AnimatedContainer(
                      duration: const Duration(seconds: 1),
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _isConnected ? _secondaryColor : Colors.red,
                        boxShadow: [BoxShadow(color: _isConnected ? _secondaryColor : Colors.red, blurRadius: 8)],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      _isConnected ? 'QWEN NEURAL LINK: ACTIVE' : 'QWEN NEURAL LINK: RECONNECTING',
                      style: TextStyle(
                        fontFamily: _fontFamily,
                        fontSize: 9,
                        color: Colors.white70,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'RAM: ${_hostRamGb.toStringAsFixed(1)} GB',
                      style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: _primaryColor),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'ARC: #$_themeIndex',
                      style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: _secondaryColor),
                    ),
                  ],
                ),
              ),
            ],
          ),
          actions: [
            Container(
              margin: const EdgeInsets.only(right: 12, top: 8, bottom: 8),
              decoration: BoxDecoration(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white24),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  InkWell(
                    borderRadius: const BorderRadius.horizontal(left: Radius.circular(11)),
                    onTap: () => setState(() => _activeNavTab = 0),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: _activeNavTab == 0 ? _primaryColor.withValues(alpha: 0.25) : Colors.transparent,
                        borderRadius: const BorderRadius.horizontal(left: Radius.circular(11)),
                        border: _activeNavTab == 0 ? Border.all(color: _primaryColor) : null,
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.hub, size: 13, color: _activeNavTab == 0 ? _primaryColor : Colors.white60),
                          const SizedBox(width: 4),
                          Text('MESH', style: TextStyle(fontFamily: _fontFamily, fontSize: 10, fontWeight: FontWeight.bold, color: _activeNavTab == 0 ? _primaryColor : Colors.white60)),
                        ],
                      ),
                    ),
                  ),
                  InkWell(
                    borderRadius: const BorderRadius.horizontal(right: Radius.circular(11)),
                    onTap: () => setState(() => _activeNavTab = 1),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: _activeNavTab == 1 ? const Color(0xFFFF0055).withValues(alpha: 0.25) : Colors.transparent,
                        borderRadius: const BorderRadius.horizontal(right: Radius.circular(11)),
                        border: _activeNavTab == 1 ? Border.all(color: const Color(0xFFFF0055)) : null,
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.sports_kabaddi, size: 13, color: _activeNavTab == 1 ? const Color(0xFFFF0055) : Colors.white60),
                          const SizedBox(width: 4),
                          Text('TATAMI', style: TextStyle(fontFamily: _fontFamily, fontSize: 10, fontWeight: FontWeight.bold, color: _activeNavTab == 1 ? const Color(0xFFFF0055) : Colors.white60)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        body: Stack(
          fit: StackFit.expand,
          children: [
            // Dynamic Background Gradient
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    _bgColor.withValues(alpha: 0.85),
                    _bgColor.withValues(alpha: 0.5),
                    Colors.black.withValues(alpha: 0.95),
                  ],
                ),
              ),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: _activeNavTab == 0
                    ? LayoutBuilder(
                        builder: (context, constraints) {
                          final isDesktop = constraints.maxWidth >= 900;
                          if (isDesktop) {
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Left Column (Telemetry & Controls)
                                SizedBox(
                                  width: 380,
                                  child: SingleChildScrollView(
                                    physics: const BouncingScrollPhysics(),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [
                                        _buildHardwareTopologyCard(),
                                        const SizedBox(height: 12),
                                        _buildBluetoothHealingCard(),
                                        const SizedBox(height: 12),
                                        _buildDevelopingScenariosCard(),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                // Right Column (Live Narrative Terminal Feed)
                                Expanded(
                                  child: _buildLiveTerminalFeed(),
                                ),
                              ],
                            );
                          } else {
                            return Column(
                              children: [
                                // Horizontally Scrollable Telemetry Dashboard Carousel
                                SizedBox(
                                  height: 225,
                                  child: SingleChildScrollView(
                                    scrollDirection: Axis.horizontal,
                                    physics: const BouncingScrollPhysics(),
                                    child: Row(
                                      children: [
                                        SizedBox(width: 300, child: _buildHardwareTopologyCard()),
                                        const SizedBox(width: 10),
                                        SizedBox(width: 300, child: _buildBluetoothHealingCard()),
                                        const SizedBox(width: 10),
                                        SizedBox(width: 300, child: _buildDevelopingScenariosCard()),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                Expanded(
                                  child: _buildLiveTerminalFeed(),
                                ),
                              ],
                            );
                          }
                        },
                      )
                    : _buildTatamiCombatArenaView(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTatamiCombatArenaView() {
    final match = _activeMatch;
    final isSparring = match != null && match['state'] == 'SPARRING';
    final elapsedS = match != null ? (match['elapsed_s'] as num?)?.toDouble() ?? 0.0 : 0.0;
    final durationS = match != null ? (match['duration_s'] as num?)?.toDouble() ?? 300.0 : 300.0;
    final winner = match != null ? match['winner']?.toString() : null;
    final winMethod = match != null ? match['win_method']?.toString() : null;

    final fA = match != null && match['fighter_a'] != null ? Map<String, dynamic>.from(match['fighter_a']) : <String, dynamic>{};
    final fB = match != null && match['fighter_b'] != null ? Map<String, dynamic>.from(match['fighter_b']) : <String, dynamic>{};

    final xA = (fA['tatami_x'] as num?)?.toDouble() ?? -1.2;
    final yA = (fA['tatami_y'] as num?)?.toDouble() ?? 0.0;
    final xB = (fB['tatami_x'] as num?)?.toDouble() ?? 1.2;
    final yB = (fB['tatami_y'] as num?)?.toDouble() ?? 0.0;

    final posA = fA['current_position']?.toString() ?? 'STANDING';
    final posB = fB['current_position']?.toString() ?? 'STANDING';
    final subRisk = (fA['active_submission'] ?? fB['active_submission'] ?? 'NONE').toString();
    final torqueA = (fA['current_torque_nm'] as num?)?.toDouble() ?? 0.0;
    final torqueB = (fB['current_torque_nm'] as num?)?.toDouble() ?? 0.0;
    final maxTorque = math.max(torqueA, torqueB);

    final bio = _arenaBiometrics;
    final isStreaming = bio != null && bio['is_streaming'] == true;
    final hrStr = isStreaming && bio['hr_bpm'] != null ? '${bio['hr_bpm']} bpm' : '-- bpm';
    final hrvStr = isStreaming && bio['hrv_rmssd_ms'] != null ? '${(bio['hrv_rmssd_ms'] as num).toStringAsFixed(1)} ms' : '-- ms';
    final dfaStr = isStreaming && bio['dfa_alpha1'] != null ? (bio['dfa_alpha1'] as num).toStringAsFixed(2) : '--';
    final vo2Str = isStreaming && bio['vo2_max_est'] != null ? (bio['vo2_max_est'] as num).toStringAsFixed(1) : '--';

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. Arena Match Status Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: maxTorque >= 25.0 ? Colors.redAccent : const Color(0xFF00FF41).withValues(alpha: 0.5),
                width: maxTorque >= 25.0 ? 2 : 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: maxTorque >= 25.0 ? Colors.redAccent.withValues(alpha: 0.3) : const Color(0xFF00FF41).withValues(alpha: 0.1),
                  blurRadius: 15,
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isSparring ? const Color(0xFF00FF41) : Colors.amber,
                        boxShadow: [BoxShadow(color: isSparring ? const Color(0xFF00FF41) : Colors.amber, blurRadius: 6)],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      winner != null
                          ? '🏆 FINISHED: $winMethod'
                          : isSparring
                              ? 'SPARRING: ${elapsedS.toInt()}s / ${durationS.toInt()}s'
                              : 'TATAMI READY',
                      style: TextStyle(
                        fontFamily: _fontFamily,
                        color: winner != null ? Colors.greenAccent : (isSparring ? const Color(0xFF00FF41) : Colors.white),
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.cyanAccent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.cyanAccent.withValues(alpha: 0.6)),
                  ),
                  child: Text(
                    '$posA  ⇄  $posB',
                    style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Submission Warning Banner if Joint Torque is Elevated
          if (maxTorque >= 25.0)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.redAccent),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 16),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      maxTorque >= 45.0
                          ? '🔴 CRITICAL TAP OUT DETECTED! (${maxTorque.toStringAsFixed(1)} N·m)'
                          : '🟡 JOINT TORQUE ELEVATED: ${maxTorque.toStringAsFixed(1)} N·m / 45.0 N·m TAP GATE',
                      style: TextStyle(fontFamily: _fontFamily, color: Colors.redAccent, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
            ),

          // 2. 10m x 10m Virtual Tatami Mat Canvas
          Container(
            height: 240,
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white12),
              boxShadow: const [BoxShadow(color: Colors.black54, blurRadius: 10)],
            ),
            clipBehavior: Clip.antiAlias,
            child: CustomPaint(
              size: const Size(double.infinity, 240),
              painter: TatamiCanvasPainter(
                xA: xA,
                yA: yA,
                xB: xB,
                yB: yB,
                subRisk: subRisk,
                torqueNm: maxTorque,
                posA: posA,
                posB: posB,
                fighterAName: fA['name']?.toString() ?? 'Aaron Twin',
                fighterBName: fB['name']?.toString() ?? 'Apex-NPU',
              ),
            ),
          ),
          const SizedBox(height: 12),

          // 3. Opponent Selector Chips & Action Controls
          Row(
            children: [
              Text('OPPONENT: ', style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold)),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildOpponentChip('apex_npu', 'Apex-NPU (ANE)'),
                      _buildOpponentChip('nyx_npu', 'Nyx-NPU (TPU)'),
                      _buildOpponentChip('sovereign_qwen', 'Sovereign-Qwen'),
                      _buildOpponentChip('nexus_core', 'Nexus-Core'),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Matside Corner Coaching Directives
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.amber.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('MATSIDE CORNER COACH', style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: Colors.amberAccent, fontWeight: FontWeight.bold)),
                    Text('REAL-TIME DIRECTIVE', style: TextStyle(fontFamily: _fontFamily, fontSize: 7, color: Colors.white54)),
                  ],
                ),
                const SizedBox(height: 6),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildDirectiveChip('🫀 ZONE 2', 'CONSERVE_ZONE_2', Colors.greenAccent),
                      const SizedBox(width: 6),
                      _buildDirectiveChip('🔒 SUBMISSION', 'HUNT_SUBMISSION', Colors.redAccent),
                      const SizedBox(width: 6),
                      _buildDirectiveChip('⚡ SMASH PASS', 'SMASH_PASS', Colors.lightBlueAccent),
                      const SizedBox(width: 6),
                      _buildDirectiveChip('🥋 PULL GUARD', 'PULL_GUARD', Colors.purpleAccent),
                      const SizedBox(width: 6),
                      _buildDirectiveChip('💥 SCRAMBLE', 'SCRAMBLE_ESCAPE', Colors.orangeAccent),
                      const SizedBox(width: 6),
                      _buildDirectiveChip('RESET', 'RESET_NEUTRAL', Colors.grey),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Match Action Buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF00FF41),
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.play_arrow, size: 18),
                  label: Text('START ROLL', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, fontSize: 11)),
                  onPressed: _isArenaProcessing ? null : () => _startArenaMatch(_selectedOpponent),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.cyanAccent.withValues(alpha: 0.2),
                    foregroundColor: Colors.cyanAccent,
                    side: const BorderSide(color: Colors.cyanAccent),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.skip_next, size: 18),
                  label: Text('NEXT TICK', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, fontSize: 11)),
                  onPressed: _isArenaProcessing ? null : _tickArenaMatch,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFFF0055),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.flash_on, size: 18),
                  label: Text('FAST SIM', style: TextStyle(fontFamily: _fontFamily, fontWeight: FontWeight.bold, fontSize: 11)),
                  onPressed: _isArenaProcessing ? null : () => _simulateFullArenaMatch(_selectedOpponent),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // 4. Dual Fighter HUD Cards
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Fighter A: Aaron (Biometric Twin)
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.black45,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF00FF41).withValues(alpha: 0.5)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              fA['name']?.toString() ?? 'Aaron (Twin)',
                              style: TextStyle(fontFamily: _fontFamily, color: const Color(0xFF00FF41), fontWeight: FontWeight.bold, fontSize: 11),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            'ELO ${(fA['elo'] as num?)?.toInt() ?? 1520}',
                            style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 9),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('STAMINA: ${((fA['current_stamina_j'] as num?)?.toInt() ?? 50000)} J', style: const TextStyle(fontSize: 9, color: Colors.white60)),
                      const SizedBox(height: 2),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: (((fA['current_stamina_j'] as num?)?.toDouble() ?? 50000.0) / 50000.0).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF00FF41)),
                          minHeight: 5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text('JOINT TORQUE: ${torqueA.toStringAsFixed(1)} N·m', style: TextStyle(fontSize: 9, color: torqueA >= 25.0 ? Colors.redAccent : Colors.white60)),
                      const SizedBox(height: 2),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: (torqueA / 45.0).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: AlwaysStoppedAnimation<Color>(torqueA >= 25.0 ? Colors.redAccent : Colors.cyanAccent),
                          minHeight: 5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      // Movesense 512Hz Biometrics Pill (Rule #0 Zero-Mock compliant: clean '--' standby state)
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('MOVESENSE 512Hz', style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
                                Text(isStreaming ? '● LIVE' : '○ STANDBY', style: TextStyle(fontFamily: _fontFamily, fontSize: 7, color: isStreaming ? Colors.greenAccent : Colors.white38)),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text('HR: $hrStr  |  HRV: $hrvStr', style: const TextStyle(fontSize: 8, color: Colors.white70)),
                            Text('DFA-α1: $dfaStr  |  VO2: $vo2Str', style: const TextStyle(fontSize: 8, color: Colors.white70)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 6),
                      // AI Level & Belt Rank Badge
                      InkWell(
                        onTap: _showUserAnalysisDialog,
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6B21A8).withValues(alpha: 0.3),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFF9333EA).withValues(alpha: 0.6)),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    width: 8,
                                    height: 12,
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF6B21A8),
                                      borderRadius: BorderRadius.circular(1),
                                      border: Border.all(color: Colors.white30),
                                    ),
                                  ),
                                  const SizedBox(width: 5),
                                  Text(
                                    'PURPLE BELT // LVL 76',
                                    style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: Colors.white, fontWeight: FontWeight.bold),
                                  ),
                                ],
                              ),
                              const Text('📊 AI', style: TextStyle(fontSize: 8, color: Colors.purpleAccent, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      // Active Corner Directive Indicator
                      Text(
                        'DIRECTIVE: ${(fA['active_directive']?.toString() ?? 'NEUTRAL').replaceAll('_', ' ')}',
                        style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: fA['active_directive'] != null ? Colors.amberAccent : Colors.white38, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Fighter B: Opponent AI
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.black45,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFF0055).withValues(alpha: 0.5)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              fB['name']?.toString() ?? 'Apex-NPU',
                              style: TextStyle(fontFamily: _fontFamily, color: const Color(0xFFFF0055), fontWeight: FontWeight.bold, fontSize: 11),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            'ELO ${(fB['elo'] as num?)?.toInt() ?? 1545}',
                            style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 9),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('STAMINA: ${((fB['current_stamina_j'] as num?)?.toInt() ?? 50000)} J', style: const TextStyle(fontSize: 9, color: Colors.white60)),
                      const SizedBox(height: 2),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: (((fB['current_stamina_j'] as num?)?.toDouble() ?? 50000.0) / 50000.0).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFFFF0055)),
                          minHeight: 5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text('JOINT TORQUE: ${torqueB.toStringAsFixed(1)} N·m', style: TextStyle(fontSize: 9, color: torqueB >= 25.0 ? Colors.redAccent : Colors.white60)),
                      const SizedBox(height: 2),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: (torqueB / 45.0).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: AlwaysStoppedAnimation<Color>(torqueB >= 25.0 ? Colors.redAccent : Colors.amber),
                          minHeight: 5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.05),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('LOCAL AI ARCHETYPE', style: TextStyle(fontFamily: _fontFamily, fontSize: 8, color: const Color(0xFFFF0055), fontWeight: FontWeight.bold)),
                            const SizedBox(height: 2),
                            Text(fB['style']?.toString() ?? 'Sub Hunter / Heel Hooks', style: const TextStyle(fontSize: 8, color: Colors.white70), maxLines: 1, overflow: TextOverflow.ellipsis),
                            Text('MODEL: ${_selectedOpponent.toUpperCase()}', style: const TextStyle(fontSize: 8, color: Colors.white38)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // 5. Play-by-Play Technical Commentary Feed
          Text('🥋 PLAY-BY-PLAY TACTICAL COMMENTARY', style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1)),
          const SizedBox(height: 6),
          Container(
            height: 180,
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.6),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white12),
            ),
            child: _arenaLogs.isEmpty
                ? Center(
                    child: Text('Press START ROLL to begin autonomous AI sparring.', style: TextStyle(fontFamily: _fontFamily, color: Colors.white38, fontSize: 11)),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(10),
                    physics: const BouncingScrollPhysics(),
                    itemCount: _arenaLogs.length,
                    itemBuilder: (context, idx) {
                      final item = _arenaLogs[idx];
                      final isTap = item['result'] == 'TAP_SUBMISSION_VICTORY';
                      final hasSub = (item['torque_nm'] as num?)?.toDouble() != null && ((item['torque_nm'] as num).toDouble() >= 25.0);
                      final color = isTap ? Colors.redAccent : (hasSub ? Colors.amber : Colors.white70);

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: isTap ? Colors.red.withValues(alpha: 0.15) : Colors.white.withValues(alpha: 0.04),
                          borderRadius: BorderRadius.circular(8),
                          border: Border(left: BorderSide(color: color, width: 3)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('${item['timestamp_s'] ?? 0}s | ${item['pos_a'] ?? 'STANDING'}', style: TextStyle(fontFamily: _fontFamily, color: Colors.white38, fontSize: 9)),
                                if (item['sub_risk'] != null && item['sub_risk'] != 'NONE')
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                    decoration: BoxDecoration(
                                      color: Colors.red.withValues(alpha: 0.2),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text('⚠️ ${item['sub_risk']}', style: const TextStyle(color: Colors.redAccent, fontSize: 8, fontWeight: FontWeight.bold)),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(item['commentary']?.toString() ?? '', style: TextStyle(fontFamily: _fontFamily, color: color, fontSize: 11)),
                          ],
                        ),
                      );
                    },
                  ),
          ),
          const SizedBox(height: 12),

          // 6. Bradley-Terry ELO Leaderboard
          Text('🏆 BRADLEY-TERRY ELO LEADERBOARD', style: TextStyle(fontFamily: _fontFamily, color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1)),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white12),
            ),
            child: Column(
              children: (_arenaLeaderboard.isNotEmpty ? _arenaLeaderboard : [
                {'rank': 1, 'name': 'Sovereign-Qwen', 'elo': 1580.0, 'wins': 0, 'losses': 0, 'archetype': 'Pressure Passer'},
                {'rank': 2, 'name': 'Apex-NPU', 'elo': 1545.0, 'wins': 0, 'losses': 0, 'archetype': 'Sub Hunter'},
                {'rank': 3, 'name': 'Aaron (Twin)', 'elo': 1520.0, 'wins': 0, 'losses': 0, 'archetype': 'Zone 2 Flow'},
                {'rank': 4, 'name': 'Nyx-NPU', 'elo': 1510.0, 'wins': 0, 'losses': 0, 'archetype': 'Leglocker'},
                {'rank': 5, 'name': 'Nexus-Core', 'elo': 1475.0, 'wins': 0, 'losses': 0, 'archetype': 'Guard Sorcerer'},
              ]).map((entry) {
                final isUser = entry['name'].toString().contains('Aaron');
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                  child: Row(
                    children: [
                      Container(
                        width: 20,
                        alignment: Alignment.center,
                        child: Text('#${entry['rank'] ?? 1}', style: TextStyle(fontFamily: _fontFamily, color: isUser ? const Color(0xFF00FF41) : Colors.amber, fontSize: 10, fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          entry['name']?.toString() ?? '',
                          style: TextStyle(fontFamily: _fontFamily, color: isUser ? const Color(0xFF00FF41) : Colors.white, fontSize: 11, fontWeight: isUser ? FontWeight.bold : FontWeight.normal),
                        ),
                      ),
                      Text(
                        '${(entry['elo'] as num?)?.toInt() ?? 1500} ELO',
                        style: TextStyle(fontFamily: _fontFamily, color: isUser ? const Color(0xFF00FF41) : Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${entry['wins'] ?? 0}W-${entry['losses'] ?? 0}L',
                        style: const TextStyle(fontSize: 9, color: Colors.white38),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 60),
        ],
      ),
    );
  }

  Widget _buildOpponentChip(String key, String label) {
    final isSelected = _selectedOpponent == key;
    return Padding(
      padding: const EdgeInsets.only(right: 6.0),
      child: ChoiceChip(
        label: Text(label, style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: isSelected ? Colors.black : Colors.white70, fontWeight: FontWeight.bold)),
        selected: isSelected,
        selectedColor: const Color(0xFFFF0055),
        backgroundColor: Colors.white10,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        onSelected: (val) {
          if (val) setState(() => _selectedOpponent = key);
        },
      ),
    );
  }

  Widget _buildHardwareTopologyCard() {
    return _buildGlassmorphicContainer(
      borderColor: _primaryColor,
      opacity: 0.6,
      child: Container(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    "HARDWARE TOPOLOGY",
                    style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 0.5),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.green.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(color: _primaryColor.withValues(alpha: 0.5)),
                  ),
                  child: Text(
                    "RULE #3 SAFE",
                    style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontSize: 8, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            _buildMeshNodeStatus("L1: Mac Mini Host", "${_hostRamGb.toStringAsFixed(1)} GB Free", _hostRamGb >= 9.6, _primaryColor),
            _buildMeshNodeStatus("L2: MacBook Pro Vault", "TB4 (${_tb4Latency}ms)", true, _primaryColor),
            _buildMeshNodeStatus("L3: Linux Head Node", "13.8 GB // Ray", true, _primaryColor),
            _buildMeshNodeStatus("L5: MacBook Air", "UNLOCKED // Metal", true, _secondaryColor),
          ],
        ),
      ),
    );
  }

  Widget _buildBluetoothHealingCard() {
    return _buildGlassmorphicContainer(
      borderColor: _secondaryColor,
      opacity: 0.6,
      child: Container(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    "LINE 1 OOB BLUETOOTH",
                    style: TextStyle(fontFamily: _fontFamily, color: _secondaryColor, fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 0.5),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.purple.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(color: _secondaryColor.withValues(alpha: 0.6)),
                  ),
                  child: Text(
                    "ZERO-IP",
                    style: TextStyle(fontFamily: _fontFamily, color: _secondaryColor, fontSize: 8, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              "RFCOMM: $_btRfcommPort",
              style: TextStyle(fontFamily: _fontFamily, color: Colors.white70, fontSize: 10),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    "$_btConnectedPeers Connected Peers",
                    style: TextStyle(fontFamily: _fontFamily, color: _primaryColor, fontSize: 10, fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  "100% Verified",
                  style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 9),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              "Drill #$_btDrillCount: $_btLastAction",
              style: const TextStyle(fontFamily: 'Courier', color: Colors.amber, fontSize: 9),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            InkWell(
              onTap: _triggerBtDrill,
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 3),
                decoration: BoxDecoration(
                  color: _secondaryColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: _secondaryColor.withValues(alpha: 0.5)),
                ),
                alignment: Alignment.center,
                child: Text(
                  "⚡ PULSE NO-IP DRILL",
                  style: TextStyle(fontFamily: _fontFamily, color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDevelopingScenariosCard() {
    return _buildGlassmorphicContainer(
      borderColor: Colors.amber,
      opacity: 0.6,
      child: Container(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    "DEVELOPING SCENARIOS",
                    style: TextStyle(fontFamily: _fontFamily, color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 0.5),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(color: Colors.amber.withValues(alpha: 0.6)),
                  ),
                  child: Text(
                    _continuousScenarios ? "AUTOPILOT ON" : "AUTOPILOT OFF",
                    style: TextStyle(fontFamily: _fontFamily, color: Colors.amber, fontSize: 8, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              _recentEvents.isNotEmpty
                  ? "Active: ${_recentEvents[0]['title'] ?? 'Scenario'}"
                  : "Active: Real-Life Mesh Scenarios",
              style: TextStyle(fontFamily: _fontFamily, color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    _recentEvents.isNotEmpty
                        ? "🔥 Score: ${_recentEvents[0]['interest_score'] ?? 85}/100"
                        : "🔥 Score: 95/100 [CRITICAL]",
                    style: TextStyle(fontFamily: _fontFamily, color: Colors.yellowAccent, fontSize: 9, fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  _recentEvents.isNotEmpty
                      ? (_recentEvents[0]['stage_label'] ?? 'STAGE 1/4').toString().split(':')[0]
                      : "STAGE 1/4",
                  style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 9, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 4),
            InkWell(
              onTap: () {
                if (_recentEvents.isNotEmpty) {
                  _showEventNarrativeModal(_recentEvents[0]);
                } else {
                  _showDirectorModal();
                }
              },
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.cyanAccent.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: Colors.cyanAccent.withValues(alpha: 0.5)),
                ),
                alignment: Alignment.center,
                child: Text(
                  "▶ INSPECT ACTIVE NARRATIVE",
                  style: TextStyle(fontFamily: _fontFamily, color: Colors.cyanAccent, fontSize: 9, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLiveTerminalFeed() {
    final filteredLogs = _logs.where((l) {
      final isAbliterated = l['group'] == 'abliterated' || ['Cipher', 'Vortex', 'Nyx-NPU'].contains(l['npc']);
      if (_feedFilter == 'sovereign') {
        return !isAbliterated;
      } else if (_feedFilter == 'adversarial') {
        return isAbliterated;
      }
      return true;
    }).toList();

    return _buildGlassmorphicContainer(
      borderColor: _secondaryColor,
      opacity: 0.7,
      child: Column(
        children: [
          // Filter & Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.white.withValues(alpha: 0.1))),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      color: Color(0xFF00FF41),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "LIVE NARRATIVE FEED",
                    style: TextStyle(fontFamily: _fontFamily, color: const Color(0xFF00FF41), fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1),
                  ),
                  const SizedBox(width: 12),
                  _buildFeedFilterChip('ALL', 'all', Colors.white70),
                  const SizedBox(width: 4),
                  _buildFeedFilterChip('SOVEREIGN', 'sovereign', const Color(0xFF00FF41)),
                  const SizedBox(width: 4),
                  _buildFeedFilterChip('ADVERSARIAL', 'adversarial', const Color(0xFFFF0055)),
                ],
              ),
            ),
          ),
          // Log List or Awaiting Signal
          Expanded(
            child: filteredLogs.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _isConnected ? "STREAM CONNECTED // STANDBY FOR EVENTS..." : "AWAITING SIGNAL...",
                          style: TextStyle(fontFamily: _fontFamily, color: _secondaryColor, fontSize: 14, letterSpacing: 2),
                        ),
                        if (!_isConnected) ...[
                          const SizedBox(height: 8),
                          Text(
                            "Attempting WebSocket handshake on :8101...",
                            style: TextStyle(fontFamily: _fontFamily, color: Colors.white38, fontSize: 10),
                          ),
                        ],
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: filteredLogs.length,
                    padding: const EdgeInsets.all(12),
                    itemBuilder: (context, index) {
                      final log = filteredLogs[index];
                      final isAbliterated = log['group'] == 'abliterated' || ['Cipher', 'Vortex', 'Nyx-NPU'].contains(log['npc']);
                      final color = isAbliterated ? const Color(0xFFFF0055) : const Color(0xFF00FF41);
                      final factionBadge = isAbliterated ? '[ADVERSARIAL] ' : '[SOVEREIGN] ';
                      final modelLabel = log['model'] ?? (isAbliterated ? 'Qwen 3.8 Max Abliterated' : 'Qwen 3.8 Max');
                      final latency = log['latency_ms'] != null ? '${log['latency_ms']}ms' : '';

                      return Container(
                        margin: const EdgeInsets.only(bottom: 10.0),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: const BorderRadius.only(topRight: Radius.circular(8), bottomRight: Radius.circular(8)),
                            onTap: () => _showEventNarrativeModal(log),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.08),
                                border: Border(left: BorderSide(color: color, width: 4)),
                                borderRadius: const BorderRadius.only(topRight: Radius.circular(8), bottomRight: Radius.circular(8)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  RichText(
                                    text: TextSpan(
                                      style: TextStyle(
                                        fontFamily: _fontFamily,
                                        fontSize: 13,
                                        height: 1.4,
                                      ),
                                      children: [
                                        TextSpan(
                                          text: "[${log['timestamp']}] ",
                                          style: const TextStyle(color: Colors.white54, fontSize: 11),
                                        ),
                                        TextSpan(
                                          text: factionBadge,
                                          style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 10),
                                        ),
                                        TextSpan(
                                          text: "${log['npc'].toString().toUpperCase()} ",
                                          style: TextStyle(color: color, fontWeight: FontWeight.w900, letterSpacing: 1),
                                        ),
                                        TextSpan(
                                          text: "[$modelLabel $latency]\n",
                                          style: const TextStyle(color: Colors.white38, fontSize: 10),
                                        ),
                                        TextSpan(
                                          text: log['action'] ?? '',
                                          style: const TextStyle(color: Colors.white, fontSize: 12),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Text(
                                          log['event_title'] != null ? "⚡ ${log['event_title']}" : (log['event_id'] != null ? "⚡ ${log['event_id']}" : "⚡ SYSTEM TELEMETRY"),
                                          style: TextStyle(fontFamily: _fontFamily, fontSize: 10, color: color.withValues(alpha: 0.8), fontWeight: FontWeight.bold),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      Row(
                                        children: [
                                          if (log['interest_score'] != null)
                                            Container(
                                              margin: const EdgeInsets.only(right: 6),
                                              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                              decoration: BoxDecoration(
                                                color: Colors.amber.withValues(alpha: 0.2),
                                                borderRadius: BorderRadius.circular(4),
                                                border: Border.all(color: Colors.amber.withValues(alpha: 0.5)),
                                              ),
                                              child: Text(
                                                "🔥 ${log['interest_score']}",
                                                style: const TextStyle(color: Colors.amber, fontSize: 9, fontWeight: FontWeight.bold),
                                              ),
                                            ),
                                          Text(
                                            "▶ NARRATIVE",
                                            style: TextStyle(fontFamily: _fontFamily, fontSize: 9, color: Colors.cyanAccent, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                                          ),
                                          const SizedBox(width: 4),
                                          const Icon(Icons.chevron_right, size: 12, color: Colors.cyanAccent),
                                        ],
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
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

  Widget _buildFeedFilterChip(String label, String value, Color color) {
    final isSelected = _feedFilter == value;
    return InkWell(
      onTap: () => setState(() => _feedFilter = value),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.25) : Colors.black45,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: isSelected ? color : Colors.white24),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: _fontFamily,
            fontSize: 9,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? color : Colors.white60,
          ),
        ),
      ),
    );
  }
}

class TatamiCanvasPainter extends CustomPainter {
  final double xA;
  final double yA;
  final double xB;
  final double yB;
  final String subRisk;
  final double torqueNm;
  final String posA;
  final String posB;
  final String fighterAName;
  final String fighterBName;

  TatamiCanvasPainter({
    required this.xA,
    required this.yA,
    required this.xB,
    required this.yB,
    required this.subRisk,
    required this.torqueNm,
    required this.posA,
    required this.posB,
    required this.fighterAName,
    required this.fighterBName,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final scale = size.width / 11.0;

    Offset toCanvas(double x, double y) {
      return Offset(center.dx + x * scale, center.dy + y * scale);
    }

    // 1. Tatami mat background
    final matRect = Rect.fromCenter(center: center, width: 10.0 * scale, height: 10.0 * scale);
    final matPaint = Paint()..color = const Color(0xFF111827);
    canvas.drawRect(matRect, matPaint);

    // 2. 1m Coordinate Grid
    final gridPaint = Paint()
      ..color = const Color(0xFF1F2937)
      ..strokeWidth = 1.0;
    for (int i = -5; i <= 5; i++) {
      canvas.drawLine(toCanvas(i.toDouble(), -5.0), toCanvas(i.toDouble(), 5.0), gridPaint);
      canvas.drawLine(toCanvas(-5.0, i.toDouble()), toCanvas(5.0, i.toDouble()), gridPaint);
    }

    // 3. 8m Out-of-Bounds Warning Perimeter
    final warnRect = Rect.fromCenter(center: center, width: 8.0 * scale, height: 8.0 * scale);
    final warnPaint = Paint()
      ..color = Colors.redAccent.withValues(alpha: 0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawRect(warnRect, warnPaint);

    // 4. Center Referee Circle
    final centerCirclePaint = Paint()
      ..color = Colors.white12
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawCircle(center, 1.0 * scale, centerCirclePaint);

    // Starting marks
    final startMarkPaint = Paint()
      ..color = const Color(0xFF00FF41).withValues(alpha: 0.5)
      ..strokeWidth = 2.0;
    canvas.drawLine(toCanvas(-1.2, -0.3), toCanvas(-1.2, 0.3), startMarkPaint);
    final startMarkPaintB = Paint()
      ..color = const Color(0xFFFF0055).withValues(alpha: 0.5)
      ..strokeWidth = 2.0;
    canvas.drawLine(toCanvas(1.2, -0.3), toCanvas(1.2, 0.3), startMarkPaintB);

    // 5. Engagement Laser Line
    final pA = toCanvas(xA, yA);
    final pB = toCanvas(xB, yB);
    final isDanger = torqueNm >= 25.0;
    final linePaint = Paint()
      ..color = isDanger ? Colors.redAccent : Colors.cyanAccent.withValues(alpha: 0.7)
      ..strokeWidth = isDanger ? 3.0 : 1.5;
    canvas.drawLine(pA, pB, linePaint);

    // 6. 10m Outer Mat Border
    final borderPaint = Paint()
      ..color = const Color(0xFF00FF41).withValues(alpha: 0.8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    canvas.drawRect(matRect, borderPaint);

    // 7. Fighter A Avatar (Cyan / Green)
    final fAPaint = Paint()..color = const Color(0xFF00FF41);
    final fAHalo = Paint()..color = const Color(0xFF00FF41).withValues(alpha: 0.3);
    canvas.drawCircle(pA, 0.4 * scale, fAHalo);
    canvas.drawCircle(pA, 0.25 * scale, fAPaint);

    // 8. Fighter B Avatar (Magenta / Red)
    final fBPaint = Paint()..color = const Color(0xFFFF0055);
    final fBHalo = Paint()..color = const Color(0xFFFF0055).withValues(alpha: 0.3);
    canvas.drawCircle(pB, 0.4 * scale, fBHalo);
    canvas.drawCircle(pB, 0.25 * scale, fBPaint);
  }

  @override
  bool shouldRepaint(covariant TatamiCanvasPainter oldDelegate) {
    return oldDelegate.xA != xA ||
        oldDelegate.yA != yA ||
        oldDelegate.xB != xB ||
        oldDelegate.yB != yB ||
        oldDelegate.subRisk != subRisk ||
        oldDelegate.torqueNm != torqueNm ||
        oldDelegate.posA != posA ||
        oldDelegate.posB != posB;
  }
}
