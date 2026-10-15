import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:permission_handler/permission_handler.dart';

class MeshAudioService {
  static final MeshAudioService _instance = MeshAudioService._internal();
  factory MeshAudioService() => _instance;

  final AudioRecorder _audioRecorder = AudioRecorder();
  Timer? _amplitudeTimer;
  bool _isMonitoring = false;
  bool _isStreaming = false;

  double _currentAmplitude = -160.0;
  
  MeshAudioService._internal();

  Future<void> initialize() async {
    try {
      if (Platform.isAndroid || Platform.isIOS) {
        final status = await Permission.microphone.request();
        if (status != PermissionStatus.granted) {
          debugPrint('Microphone permission denied for Mesh Audio Service');
          return;
        }
      }
      
      // Foreground task initialization for Android
      if (Platform.isAndroid) {
        FlutterForegroundTask.init(
          androidNotificationOptions: AndroidNotificationOptions(
            channelId: 'mesh_audio_channel',
            channelName: 'Mesh Audio Handoff',
            channelDescription: 'Maintains 24/7 ambient mic election for the Lauburu Mesh',
            channelImportance: NotificationChannelImportance.LOW,
            priority: NotificationPriority.LOW,
          ),
          iosNotificationOptions: const IOSNotificationOptions(),
          foregroundTaskOptions: ForegroundTaskOptions(
            eventAction: ForegroundTaskEventAction.nothing(),
            autoRunOnBoot: true,
            allowWakeLock: true,
            allowWifiLock: true,
          ),
        );
        
        await FlutterForegroundTask.startService(
          notificationTitle: 'Lauburu Mic Active',
          notificationText: 'Monitoring ambient mesh amplitude',
        );
      }
    } catch (e) {
      debugPrint('MeshAudioService.initialize error: $e');
    }
  }

  Future<void> startMonitoring() async {
    if (_isMonitoring) return;
    
    try {
      if (await _audioRecorder.hasPermission()) {
        // Start recording to a null sink or a tiny circular buffer to get amplitude
        const config = RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: 16000,
          numChannels: 1,
        );
        
        // Start stream to continuously sample amplitude
        await _audioRecorder.startStream(config);
        
        _isMonitoring = true;
        _amplitudeTimer = Timer.periodic(const Duration(milliseconds: 500), (timer) async {
          final amplitude = await _audioRecorder.getAmplitude();
          _currentAmplitude = amplitude.current;
          _broadcastAmplitude();
        });
      }
    } catch (e) {
      debugPrint('MeshAudioService.startMonitoring error: $e');
    }
  }

  final List<String> _hubUrls = [
    'http://192.168.8.230:18899/api/audio/mesh_election',
    'http://100.119.199.76:18899/api/audio/mesh_election',
    'http://127.0.0.1:18899/api/audio/mesh_election',
  ];

  String _resolveDeviceId() {
    final host = Platform.localHostname.toLowerCase();
    if (Platform.isAndroid) {
      if (host.contains('s20') || host.contains('samsung') || host.contains('sm-g98')) {
        return 'L7_Samsung_S20';
      }
      return 'L6_Pixel_10_Edge';
    }
    if (Platform.isMacOS) {
      if (host.contains('air') || host.contains('252')) return 'L5_MacBook_Air';
      if (host.contains('pro')) return 'L2_MacBook_Pro';
      return 'L1_Mac_Node';
    }
    if (Platform.isLinux) return 'L8_Linux_Mini';
    return 'L1_Mac_Node';
  }

  Future<void> _broadcastAmplitude() async {
    final String deviceId = _resolveDeviceId();

    for (final url in _hubUrls) {
      try {
        final response = await http.post(
          Uri.parse(url),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'device_id': deviceId,
            'amplitude_db': _currentAmplitude,
            'timestamp': DateTime.now().toIso8601String(),
          }),
        ).timeout(const Duration(seconds: 1));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final winningDevice = data['winning_device'];

          if (winningDevice == deviceId && !_isStreaming) {
            _takeStreamLock();
          } else if (winningDevice != deviceId && _isStreaming) {
            _releaseStreamLock();
          }
          return;
        }
      } catch (_) {
        // Fallback to next IP in mesh matrix
      }
    }
  }

  void _takeStreamLock() {
    debugPrint('🎉 Mesh Election Won: Taking stream lock and streaming to Linux Head Node');
    _isStreaming = true;
    // Implement WebRTC or direct TCP streaming to 100.121.247.8 here
  }

  void _releaseStreamLock() {
    debugPrint('🛑 Mesh Election Lost: Releasing stream lock. Handoff successful.');
    _isStreaming = false;
  }

  void stop() {
    _amplitudeTimer?.cancel();
    _audioRecorder.stop();
    _isMonitoring = false;
    if (Platform.isAndroid) {
      FlutterForegroundTask.stopService();
    }
  }
}
