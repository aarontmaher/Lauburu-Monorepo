// Lauburu Lean Compute Hub Satellite Entrypoint
// Dedicated to 128Hz Movesense GATT and Polar H10 telemetry streaming & Port 4000 forwarding

import 'package:flutter/material.dart';
import 'services/telemetry_persistence_service.dart';
import 'services/port_4000_forwarding_service.dart';
import 'services/movesense_ble_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const LauburuComputeHubApp());
}

class LauburuComputeHubApp extends StatelessWidget {
  const LauburuComputeHubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lauburu Compute Hub',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0D1117),
        colorScheme: const ColorScheme.dark(
          primary: Colors.cyanAccent,
          secondary: Colors.tealAccent,
        ),
      ),
      home: const ComputeHubHomeScreen(),
    );
  }
}

class ComputeHubHomeScreen extends StatefulWidget {
  const ComputeHubHomeScreen({super.key});

  @override
  State<ComputeHubHomeScreen> createState() => _ComputeHubHomeScreenState();
}

class _ComputeHubHomeScreenState extends State<ComputeHubHomeScreen> {
  late final TelemetryPersistenceService _persistenceService;
  late final Port4000ForwardingService _forwardingService;
  late final MovesenseBleService _bleService;

  @override
  void initState() {
    super.initState();
    _persistenceService = TelemetryPersistenceService();
    _forwardingService = Port4000ForwardingService(persistenceService: _persistenceService);
    _bleService = MovesenseBleService(
      persistenceService: _persistenceService,
      forwardingService: _forwardingService,
    );
    _bleService.startStreaming();
  }

  @override
  void dispose() {
    _bleService.stopStreaming();
    _forwardingService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('LAUBURU COMPUTE HUB (LEAN SATELLITE)'),
        backgroundColor: const Color(0xFF161B22),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.sensors, color: Colors.cyanAccent, size: 48),
            const SizedBox(height: 16),
            const Text(
              'Movesense 128Hz & Polar Ingestion Engine',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Text(
              'Port 4000 Forwarding: ${_forwardingService.httpBaseUrl}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.green.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.greenAccent),
              ),
              child: const Text(
                'LIVE BLE INGESTION ACTIVE',
                style: TextStyle(color: Colors.greenAccent, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
