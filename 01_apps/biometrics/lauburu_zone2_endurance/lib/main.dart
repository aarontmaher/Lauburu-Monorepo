import 'package:flutter/material.dart';
import 'views/ble_handoff_onboarding_view.dart';
import 'views/paywall_view.dart';
import 'services/compute_hub_connection_service.dart';
import 'services/revenuecat_entitlement_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  final rcService = RevenueCatEntitlementService();
  await rcService.init();
  
  runApp(MyApp(rcService: rcService));
}

class MyApp extends StatefulWidget {
  final RevenueCatEntitlementService rcService;
  
  const MyApp({super.key, required this.rcService});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  @override
  void initState() {
    super.initState();
    widget.rcService.addListener(() {
      setState(() {});
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Zone 2 Endurance Lauburu',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: widget.rcService.isPro 
        ? BleHandoffOnboardingView(hubService: ComputeHubConnectionService())
        : PaywallView(entitlementService: widget.rcService),
    );
  }
}
