import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

class BTService {
  StreamSubscription? _scanSubscription;
  BluetoothDevice? _device;
  BluetoothCharacteristic? _rxCharacteristic;

  // Nordic UART Service (NUS)
  final String serviceUuid = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
  final String rxUuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

  Future<void> listenForJsonPayloads(Function(String) onPayload) async {
    // Start scanning
    onPayload('{"status": "scanning", "message": "Scanning for BLE NUS devices..."}');
    
    // Listen to scan results
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) async {
      for (ScanResult r in results) {
        if (r.advertisementData.serviceUuids.contains(Guid(serviceUuid)) ||
            r.device.platformName.toLowerCase().contains("movesense")) {
          // Found device, stop scanning
          FlutterBluePlus.stopScan();
          _device = r.device;
          onPayload('{"status": "connecting", "message": "Found ${r.device.platformName}"}');
          
          await _connectToDevice(onPayload);
          break;
        }
      }
    });

    await FlutterBluePlus.startScan(timeout: const Duration(seconds: 15));
  }

  Future<void> _connectToDevice(Function(String) onPayload) async {
    if (_device == null) return;
    
    try {
      await _device!.connect(license: License.nonprofit);
      onPayload('{"status": "connected", "message": "Connected to ${_device!.remoteId}"}');

      // Discover services
      List<BluetoothService> services = await _device!.discoverServices();
      for (BluetoothService service in services) {
        if (service.uuid.toString() == serviceUuid) {
          for (BluetoothCharacteristic c in service.characteristics) {
            if (c.uuid.toString() == rxUuid) {
              _rxCharacteristic = c;
              await c.setNotifyValue(true);
              
              // Listen for data
              c.onValueReceived.listen((value) {
                String strValue = String.fromCharCodes(value);
                onPayload('{"cell_type": "telemetry", "payload": "$strValue"}');
              });
              
              onPayload('{"status": "listening", "message": "Bound to RX Characteristic"}');
            }
          }
        }
      }
    } catch (e) {
      onPayload('{"status": "error", "message": "$e"}');
    }
  }

  void disconnect() {
    _scanSubscription?.cancel();
    _device?.disconnect();
  }
}
