import 'package:flutter/material.dart';
import 'views/ble_handoff_onboarding_view.dart';
import 'services/compute_hub_connection_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lauburu Zone 2 Endurance',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: BleHandoffOnboardingView(
        hubService: ComputeHubConnectionService(),
      ),
    );
  }
}
