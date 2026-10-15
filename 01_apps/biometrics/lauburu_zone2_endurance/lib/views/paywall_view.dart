import 'package:flutter/material.dart';
import '../services/revenuecat_entitlement_service.dart';

class PaywallView extends StatelessWidget {
  final RevenueCatEntitlementService entitlementService;
  
  const PaywallView({super.key, required this.entitlementService});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.lock_outline, size: 80, color: Colors.blueAccent),
              const SizedBox(height: 24),
              const Text(
                'Zone 2 Endurance Pro',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 16),
              const Text(
                'Unlock 512Hz ECG Streaming, DFA-alpha1 threshold detection, and Zone 2 coaching.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white70, fontSize: 16),
              ),
              const SizedBox(height: 48),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueAccent,
                  minimumSize: const Size(double.infinity, 56),
                ),
                onPressed: () {
                  entitlementService.purchaseDigitalPro();
                },
                child: const Text('Upgrade via App Store / Play Store', style: TextStyle(color: Colors.white)),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () {}, // e.g., open webview to Shopify
                child: const Text('Bought the Hardware Kit? Restore Purchases', style: TextStyle(color: Colors.blueAccent)),
              )
            ],
          ),
        ),
      ),
    );
  }
}
