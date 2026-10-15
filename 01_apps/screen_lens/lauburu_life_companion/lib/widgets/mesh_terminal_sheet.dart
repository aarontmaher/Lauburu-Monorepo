import 'dart:async';
import 'package:flutter/material.dart';
import '../services/mesh_terminal_service.dart';

/// Modal bottom sheet providing an interactive Bluetooth Serial Terminal (TCP Port 4005)
/// with dark monospace console styling, live connection badge, 5 macro action chips,
/// autoscroll, ANSI sanitization, and command input.
class MeshTerminalSheet extends StatefulWidget {
  final IMeshTerminalService? terminalService;

  const MeshTerminalSheet({
    super.key,
    this.terminalService,
  });

  @override
  State<MeshTerminalSheet> createState() => _MeshTerminalSheetState();
}

class _MeshTerminalSheetState extends State<MeshTerminalSheet> {
  late final IMeshTerminalService _service;
  late final bool _ownsService;

  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  StreamSubscription<String>? _outputSubscription;
  StreamSubscription<TerminalConnectionState>? _stateSubscription;

  String _rawOutput = '';

  @override
  void initState() {
    super.initState();
    _ownsService = widget.terminalService == null;
    _service = widget.terminalService ?? MeshTerminalService();

    _outputSubscription = _service.outputStream.listen((chunk) {
      if (mounted) {
        setState(() {
          if (chunk.contains('\x1B[2J')) {
            _rawOutput = chunk.replaceAll('\x1B[2J', '').replaceAll('\x1B[H', '');
          } else {
            _rawOutput += chunk;
          }
        });
        _scrollToBottom();
      }
    });

    _stateSubscription = _service.stateStream.listen((_) {
      if (mounted) {
        setState(() {});
      }
    });

    if (_service.state == TerminalConnectionState.disconnected) {
      _service.connect();
    }
  }

  @override
  void dispose() {
    _outputSubscription?.cancel();
    _stateSubscription?.cancel();
    _scrollController.dispose();
    _inputController.dispose();
    if (_ownsService) {
      _service.dispose();
    }
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 80),
          curve: Curves.easeOut,
        );
      }
    });
  }

  /// Strip standard ANSI escape sequences for clean UI display.
  static String stripAnsi(String input) {
    return input.replaceAll(RegExp(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'), '');
  }

  void _reconnect() {
    _service.connect();
  }

  void _sendMacro(String macro) {
    if (macro == 'clear') {
      setState(() {
        _rawOutput = '';
      });
      _service.sendCommand('clear');
    } else {
      _service.sendCommand(macro);
    }
  }

  void _sendCommand() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;

    _inputController.clear();
    if (text == 'clear') {
      setState(() {
        _rawOutput = '';
      });
      _service.sendCommand('clear');
    } else {
      _service.sendCommand(text);
    }
  }

  Color get _badgeColor {
    switch (_service.state) {
      case TerminalConnectionState.connected:
        return Colors.greenAccent;
      case TerminalConnectionState.connecting:
        return Colors.amberAccent;
      case TerminalConnectionState.error:
        return Colors.redAccent;
      case TerminalConnectionState.disconnected:
        return Colors.grey;
    }
  }

  String get _statusLabel {
    switch (_service.state) {
      case TerminalConnectionState.connected:
        return 'Connected (Port 4005)';
      case TerminalConnectionState.connecting:
        return 'Connecting...';
      case TerminalConnectionState.error:
        return 'Connection Error';
      case TerminalConnectionState.disconnected:
        return 'Disconnected';
    }
  }

  @override
  Widget build(BuildContext context) {
    final cleanedOutput = stripAnsi(_rawOutput);
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      padding: EdgeInsets.only(bottom: bottomInset),
      decoration: const BoxDecoration(
        color: Color(0xFF0D1117),
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Drag handle
            Center(
              child: Container(
                margin: const EdgeInsets.symmetric(vertical: 8),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade700,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Header Row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 4.0),
              child: Row(
                children: [
                  const Icon(Icons.terminal, color: Colors.greenAccent, size: 22),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Mesh Bluetooth Serial Terminal',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  // Live Connection Status Badge
                  Tooltip(
                    message: _service.lastError ?? _statusLabel,
                    child: Container(
                      key: const Key('terminal_status_badge'),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: _badgeColor.withAlpha(35),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: _badgeColor.withAlpha(120)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: _badgeColor,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 5),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 140),
                            child: Text(
                              _statusLabel,
                              style: TextStyle(
                                fontSize: 11,
                                color: _badgeColor,
                                fontWeight: FontWeight.w600,
                              ),
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  // Reconnect button
                  IconButton(
                    key: const Key('terminal_reconnect_button'),
                    icon: const Icon(Icons.refresh, color: Colors.white70, size: 20),
                    tooltip: 'Reconnect to Port 4005',
                    onPressed: _reconnect,
                  ),
                  // Close button
                  IconButton(
                    key: const Key('terminal_close_button'),
                    icon: const Icon(Icons.close, color: Colors.white70, size: 20),
                    tooltip: 'Close Terminal',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            const Divider(color: Color(0xFF30363D), height: 1),

            // Quick-Action Macro Chips Row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildMacroChip('status', const Key('macro_status')),
                    const SizedBox(width: 8),
                    _buildMacroChip('audit', const Key('macro_audit')),
                    const SizedBox(width: 8),
                    _buildMacroChip('devices', const Key('macro_devices')),
                    const SizedBox(width: 8),
                    _buildMacroChip('movesense', const Key('macro_movesense')),
                    const SizedBox(width: 8),
                    _buildMacroChip('clear', const Key('macro_clear')),
                  ],
                ),
              ),
            ),

            const Divider(color: Color(0xFF30363D), height: 1),

            // Monospace Console Output Window
            Expanded(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF161B22),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF30363D)),
                ),
                child: SingleChildScrollView(
                  controller: _scrollController,
                  child: Text(
                    cleanedOutput.isEmpty
                        ? 'Connecting to bluetooth_serial_terminal_daemon.py on port 4005...\nlauburu> '
                        : cleanedOutput,
                    key: const Key('terminal_output_view'),
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      height: 1.35,
                      color: Color(0xFF58A6FF),
                    ),
                  ),
                ),
              ),
            ),

            const Divider(color: Color(0xFF30363D), height: 1),

            // Command Input Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
              child: Row(
                children: [
                  const Text(
                    'lauburu> ',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      color: Colors.greenAccent,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  Expanded(
                    child: TextField(
                      key: const Key('terminal_input_field'),
                      controller: _inputController,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        color: Colors.white,
                        fontSize: 13,
                      ),
                      cursorColor: Colors.greenAccent,
                      decoration: const InputDecoration(
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                        hintText: 'Enter command (e.g. status, devices, movesense)...',
                        hintStyle: TextStyle(color: Colors.white38, fontSize: 12),
                        border: InputBorder.none,
                      ),
                      onSubmitted: (_) => _sendCommand(),
                    ),
                  ),
                  IconButton(
                    key: const Key('terminal_send_button'),
                    icon: const Icon(Icons.send, color: Colors.greenAccent, size: 20),
                    tooltip: 'Send Command',
                    onPressed: _sendCommand,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMacroChip(String label, Key key) {
    return ActionChip(
      key: key,
      label: Text(
        '[$label]',
        style: const TextStyle(
          fontFamily: 'monospace',
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Colors.greenAccent,
        ),
      ),
      backgroundColor: const Color(0xFF21262D),
      side: const BorderSide(color: Color(0xFF30363D)),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      onPressed: () => _sendMacro(label),
    );
  }
}
