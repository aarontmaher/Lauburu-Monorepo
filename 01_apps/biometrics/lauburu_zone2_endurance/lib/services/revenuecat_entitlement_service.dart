import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:purchases_flutter/purchases_flutter.dart';

class RevenueCatEntitlementService extends ChangeNotifier {
  static const String _appleApiKey = 'test_bOWjTnipgNvbGzDAIUmFNRBBhIb';
  static const String _googleApiKey = 'mock_rc_google_api_key';
  
  bool _isPro = false;
  bool get isPro => _isPro;

  Future<void> init() async {
    if (kIsWeb) return; // RevenueCat does not support web via purchases_flutter easily without custom setup

    await Purchases.setLogLevel(LogLevel.debug);

    PurchasesConfiguration configuration;
    if (Platform.isAndroid) {
      configuration = PurchasesConfiguration(_googleApiKey);
    } else if (Platform.isIOS) {
      configuration = PurchasesConfiguration(_appleApiKey);
    } else {
      return;
    }
    
    await Purchases.configure(configuration);
    
    // Listen for changes in purchaser info
    Purchases.addCustomerInfoUpdateListener((customerInfo) {
      _updateEntitlementStatus(customerInfo);
    });

    try {
      CustomerInfo customerInfo = await Purchases.getCustomerInfo();
      _updateEntitlementStatus(customerInfo);
    } catch (e) {
      debugPrint("Failed to fetch customer info: $e");
    }
  }

  void _updateEntitlementStatus(CustomerInfo customerInfo) {
    // Check if the user has active pro_tier (hardware bundle/iOS sub)
    final bool hasPro = customerInfo.entitlements.all['pro_tier']?.isActive == true;
    
    if (_isPro != hasPro) {
      _isPro = hasPro;
      notifyListeners();
    }
  }
  
  Future<bool> purchaseDigitalPro() async {
    try {
      // In a real app, you would fetch offerings and pass a specific package
      // Here we stub it to simulate the faceid/google pay flow
      debugPrint("Presenting native paywall...");
      // Simulate success for now if they had offerings:
      // final customerInfo = await Purchases.purchasePackage(package);
      // _updateEntitlementStatus(customerInfo);
      return false; // stub
    } catch (e) {
      debugPrint("Purchase failed: $e");
      return false;
    }
  }
}
