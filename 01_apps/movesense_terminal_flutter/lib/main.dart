import 'dart:async';
import 'package:flutter/material.dart';
import 'ble_manager.dart';
import 'tcp_isolate.dart';
import 'shopify_service.dart';

void main() {
  runApp(const MovesenseTerminalApp());
}

class MovesenseTerminalApp extends StatelessWidget {
  const MovesenseTerminalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Movesense Terminal Lauburu',
      theme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: Colors.tealAccent,
        scaffoldBackgroundColor: const Color(0xFF121212),
        colorScheme: const ColorScheme.dark(
          primary: Colors.tealAccent,
          secondary: Colors.cyanAccent,
        ),
        useMaterial3: true,
      ),
      home: const TerminalHome(),
    );
  }
}

class TerminalHome extends StatefulWidget {
  const TerminalHome({super.key});

  @override
  State<TerminalHome> createState() => _TerminalHomeState();
}

class _TerminalHomeState extends State<TerminalHome> {
  final BleManager _bleManager = BleManager();
  final TcpIsolateManager _tcpManager = TcpIsolateManager();
  final ShopifyService _shopifyService = ShopifyService();

  final TextEditingController _ipController = TextEditingController(text: '100.119.199.76');
  final TextEditingController _portController = TextEditingController(text: '19003');
  
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  String _statusMessage = 'Idle';
  String _tcpStatus = 'Disconnected';
  int _bytesReceived = 0;
  
  bool _isLoggingIn = false;
  String _loginError = '';
  String? _accessToken;
  List<String> _customerTags = [];

  bool get _hasPro => _customerTags.contains('lauburu_pro');
  bool get _hasElite => _customerTags.contains('lauburu_elite');
  
  StreamSubscription? _bleStatusSub;
  StreamSubscription? _bleDataSub;

  @override
  void initState() {
    super.initState();
    _bleStatusSub = _bleManager.statusStream.listen((status) {
      setState(() {
        _statusMessage = status;
      });
    });

    _bleDataSub = _bleManager.dataStream.listen((data) {
      setState(() {
        _bytesReceived += data.length;
      });
      if (_tcpManager.isReady) {
        _tcpManager.sendData(data);
      }
    });
  }

  @override
  void dispose() {
    _bleStatusSub?.cancel();
    _bleDataSub?.cancel();
    _bleManager.disconnect();
    _tcpManager.stop();
    _ipController.dispose();
    _portController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _loginShopify() async {
    setState(() {
      _isLoggingIn = true;
      _loginError = '';
    });
    try {
      final token = await _shopifyService.login(_emailController.text, _passwordController.text);
      if (token != null) {
        final tags = await _shopifyService.getCustomerTags(token);
        setState(() {
          _accessToken = token;
          _customerTags = tags;
        });
      }
    } catch (e) {
      setState(() {
        _loginError = e.toString();
      });
    } finally {
      setState(() {
        _isLoggingIn = false;
      });
    }
  }

  void _logoutShopify() {
    setState(() {
      _accessToken = null;
      _customerTags = [];
      _emailController.clear();
      _passwordController.clear();
    });
  }

  Future<void> _connectTcp() async {
    final ip = _ipController.text;
    final port = int.tryParse(_portController.text) ?? 19003;
    
    setState(() {
      _tcpStatus = 'Connecting to $ip:$port...';
    });

    try {
      await _tcpManager.start(ip, port);
      setState(() {
        _tcpStatus = 'Connected to $ip:$port';
      });
    } catch (e) {
      setState(() {
        _tcpStatus = 'TCP Error: $e';
      });
    }
  }

  void _disconnectTcp() {
    _tcpManager.stop();
    setState(() {
      _tcpStatus = 'Disconnected';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Movesense Terminal Lauburu'),
        centerTitle: true,
        backgroundColor: Colors.black87,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: [
            // TCP Configuration
            Card(
              color: const Color(0xFF1E1E1E),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('L1/L3 Host TCP Configuration', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: TextField(
                            controller: _ipController,
                            decoration: const InputDecoration(labelText: 'IP Address', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 1,
                          child: TextField(
                            controller: _portController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(labelText: 'Port', border: OutlineInputBorder()),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        ElevatedButton(
                          onPressed: _tcpManager.isReady ? _disconnectTcp : _connectTcp,
                          child: Text(_tcpManager.isReady ? 'Disconnect TCP' : 'Connect TCP'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('TCP Status: $_tcpStatus', style: TextStyle(color: _tcpManager.isReady ? Colors.greenAccent : Colors.redAccent)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // BLE Configuration
            Card(
              color: const Color(0xFF1E1E1E),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Movesense BLE Ingestion (512Hz ECG)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        ElevatedButton.icon(
                          onPressed: () {
                            _bleManager.startScanning();
                          },
                          icon: const Icon(Icons.bluetooth_searching),
                          label: const Text('Scan & Connect'),
                        ),
                        ElevatedButton.icon(
                          onPressed: () {
                            _bleManager.disconnect();
                          },
                          icon: const Icon(Icons.bluetooth_disabled),
                          label: const Text('Disconnect'),
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent.withValues(alpha: 0.2)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text('BLE Status: $_statusMessage', style: const TextStyle(color: Colors.cyanAccent)),
                    const SizedBox(height: 8),
                    Text('Bytes Ingested: $_bytesReceived', style: const TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Shopify Billing & Features Configuration
            Card(
              color: const Color(0xFF1E1E1E),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Shopify Membership Features', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 12),
                    if (_accessToken == null) ...[
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _emailController,
                              decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder()),
                              keyboardType: TextInputType.emailAddress,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: _passwordController,
                              decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder()),
                              obscureText: true,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (_loginError.isNotEmpty) 
                        Text(_loginError, style: const TextStyle(color: Colors.redAccent)),
                      Align(
                        alignment: Alignment.centerRight,
                        child: ElevatedButton(
                          onPressed: _isLoggingIn ? null : _loginShopify,
                          child: _isLoggingIn ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Login'),
                        ),
                      ),
                    ] else ...[
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(child: Text('Logged in. Tags: ${_customerTags.join(", ")}', style: const TextStyle(color: Colors.greenAccent))),
                          TextButton(onPressed: _logoutShopify, child: const Text('Logout'))
                        ],
                      ),
                      const SizedBox(height: 16),
                      // Feature Gating
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          border: Border.all(color: _hasPro ? Colors.tealAccent : Colors.grey),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(_hasPro ? Icons.lock_open : Icons.lock, color: _hasPro ? Colors.tealAccent : Colors.grey),
                            const SizedBox(width: 8),
                            const Expanded(child: Text('Readiness Feature (Requires lauburu_pro)', style: TextStyle(fontWeight: FontWeight.bold))),
                            ElevatedButton(
                              onPressed: _hasPro ? () {} : null,
                              child: const Text('Access'),
                            )
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          border: Border.all(color: _hasElite ? Colors.tealAccent : Colors.grey),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(_hasElite ? Icons.lock_open : Icons.lock, color: _hasElite ? Colors.tealAccent : Colors.grey),
                            const SizedBox(width: 8),
                            const Expanded(child: Text('Trend Analysis (Requires lauburu_elite)', style: TextStyle(fontWeight: FontWeight.bold))),
                            ElevatedButton(
                              onPressed: _hasElite ? () {} : null,
                              child: const Text('Access'),
                            )
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 32),
            
            // Branding
            Center(
              child: Text(
                'LAUBURU ECOSYSTEM',
                style: TextStyle(letterSpacing: 4, color: Colors.tealAccent.withValues(alpha: 0.5), fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
