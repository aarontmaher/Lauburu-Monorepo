import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

class BleManager {
  final String targetDeviceNamePrefix = "Movesense";
  // Official Movesense MDS Service UUIDs
  final Guid mdsServiceUuid = Guid("34802252-7185-4d5d-b431-630e7050e8f0");
  final Guid mdsCommandCharacteristicUuid = Guid("34800001-7185-4d5d-b431-630e7050e8f0");
  final Guid mdsDataCharacteristicUuid = Guid("34800002-7185-4d5d-b431-630e7050e8f0");
  
  BluetoothDevice? _device;
  StreamSubscription? _scanSub;
  StreamSubscription? _dataSub;
  StreamSubscription? _connectionStateSub;

  final StreamController<List<int>> _dataStreamController = StreamController.broadcast();
  Stream<List<int>> get dataStream => _dataStreamController.stream;

  final StreamController<String> _statusStreamController = StreamController.broadcast();
  Stream<String> get statusStream => _statusStreamController.stream;

  bool _isIntentionalDisconnect = false;

  Future<void> startScanning() async {
    _statusStreamController.add("Scanning for Movesense HR+...");
    print("[BLE_MANAGER] Scanning for Movesense HR+...");
    
    if (await FlutterBluePlus.adapterState.first == BluetoothAdapterState.off) {
      _statusStreamController.add("Bluetooth is off.");
      print("[BLE_MANAGER] Bluetooth is off.");
      return;
    }

    _isIntentionalDisconnect = false;
    Set<String> ignoredDeviceIds = {};

    var connectedDevices = await FlutterBluePlus.connectedSystemDevices;
    
    _statusStreamController.add("Found ${connectedDevices.length} connected system devices.");
    print("[BLE_MANAGER] Found ${connectedDevices.length} connected system devices.");
    await Future.delayed(const Duration(seconds: 2));

    for (var device in connectedDevices) {
      String name = device.platformName.isNotEmpty ? device.platformName : device.advName;
      _statusStreamController.add("Checking device: '$name'");
      print("[BLE_MANAGER] Checking device: '$name'");
      await Future.delayed(const Duration(seconds: 1));

      if (name.toLowerCase().contains('movesense')) {
        _statusStreamController.add("Found already connected (name: '$name'). Connecting...");
        print("[BLE_MANAGER] Found already connected (name: '$name'). Connecting...");
        bool success = await _connectToDevice(device);
        if (success) {
           return;
        } else {
           _statusStreamController.add("Skipping $name (No MDS service)");
           print("[BLE_MANAGER] Skipping $name (No MDS service)");
           _isIntentionalDisconnect = true;
           ignoredDeviceIds.add(device.remoteId.toString());
           await device.disconnect();
           _isIntentionalDisconnect = false;
        }
      }
    }

    bool isConnecting = false;
    _statusStreamController.add("Scanning for new devices...");
    print("[BLE_MANAGER] Scanning for new devices...");

    _scanSub = FlutterBluePlus.scanResults.listen((results) async {
      if (isConnecting) return;
      for (ScanResult r in results) {
        String name = r.device.platformName.isNotEmpty ? r.device.platformName : r.device.advName;
        print("[FBP-SCAN] Scanned device: '$name' [${r.device.remoteId}] - Services: ${r.advertisementData.serviceUuids}");
        
        if (ignoredDeviceIds.contains(r.device.remoteId.toString())) continue;
        
        if (name.toLowerCase().contains('movesense')) {
          isConnecting = true;
          _statusStreamController.add("Found $name. Connecting...");
          print("[BLE_MANAGER] Found $name. Connecting...");
          await FlutterBluePlus.stopScan();
          bool success = await _connectToDevice(r.device);
          if (success) {
            break;
          } else {
            _statusStreamController.add("Skipping $name (No MDS service)");
            print("[BLE_MANAGER] Skipping $name (No MDS service)");
            _isIntentionalDisconnect = true;
            ignoredDeviceIds.add(r.device.remoteId.toString());
            await r.device.disconnect();
            _isIntentionalDisconnect = false;
            isConnecting = false;
            // Resume scanning
            _statusStreamController.add("Scanning for new devices...");
            print("[BLE_MANAGER] Scanning for new devices...");
            await FlutterBluePlus.startScan(timeout: const Duration(seconds: 15));
          }
        }
      }
    });

    await FlutterBluePlus.startScan(timeout: const Duration(seconds: 15));
  }

  Future<void> stopScanning() async {
    await FlutterBluePlus.stopScan();
    _scanSub?.cancel();
  }

  Future<bool> _connectToDevice(BluetoothDevice device) async {
    try {
      await device.connect(license: License.nonprofit, autoConnect: false);
      _device = device;
      
      _connectionStateSub = device.connectionState.listen((BluetoothConnectionState state) {
        if (state == BluetoothConnectionState.disconnected && !_isIntentionalDisconnect) {
          _statusStreamController.add("Disconnected");
          print("[BLE_MANAGER] Disconnected");
        }
      });

      _statusStreamController.add("Connected to ${device.remoteId}. Discovering services...");
      print("[BLE_MANAGER] Connected to ${device.remoteId}. Discovering services...");
      
      List<BluetoothService> services = await device.discoverServices();
      for (BluetoothService service in services) {
        if (service.uuid == mdsServiceUuid) {
          BluetoothCharacteristic? dataChar;
          BluetoothCharacteristic? cmdChar;
          
          for (BluetoothCharacteristic characteristic in service.characteristics) {
            if (characteristic.uuid == mdsDataCharacteristicUuid) {
              dataChar = characteristic;
            }
            if (characteristic.uuid == mdsCommandCharacteristicUuid) {
              cmdChar = characteristic;
            }
          }
          
          if (dataChar != null) {
            await dataChar.setNotifyValue(true);
            _dataSub = dataChar.lastValueStream.listen((value) {
              if (value.isNotEmpty) {
                _dataStreamController.add(value);
              }
            });
            
            if (cmdChar != null) {
              // Subscribe to /Meas/ECG/512
              // Movesense standard REST-over-GATT subscribe request
              // Request type 1 (Subscribe), reference ID 99, path '/Meas/ECG/512'
              List<int> ecgCommand = [1, 99] + '/Meas/ECG/512'.codeUnits;
              await cmdChar.write(ecgCommand, withoutResponse: false);
            }
            
            _statusStreamController.add("Subscribed to ECG stream via GATT!");
            print("[BLE_MANAGER] Subscribed to ECG stream via GATT!");
            return true;
          }
        }
      }
      _statusStreamController.add("ECG Service not found. Found: ${services.map((s) => s.uuid.toString()).join(', ')}");
      print("[BLE_MANAGER] ECG Service not found. Found: ${services.map((s) => s.uuid.toString()).join(', ')}");
      return false;
    } catch (e) {
      _statusStreamController.add("Connection Error: $e");
      print("[BLE_MANAGER] Connection Error: $e");
      return false;
    }
  }

  Future<void> disconnect() async {
    if (_device != null) {
      List<BluetoothService> services = await _device!.discoverServices();
      for (BluetoothService service in services) {
        if (service.uuid == mdsServiceUuid) {
          for (BluetoothCharacteristic characteristic in service.characteristics) {
             if (characteristic.uuid == mdsCommandCharacteristicUuid) {
                // Stop command
                List<int> stopCommand = [2, 99];
                try {
                  await characteristic.write(stopCommand, withoutResponse: false);
                } catch (_) {}
             }
          }
        }
      }
    }

    await _dataSub?.cancel();
    await _connectionStateSub?.cancel();
    if (_device != null) {
      await _device!.disconnect();
    }
    _statusStreamController.add("Disconnected");
    print("[BLE_MANAGER] Disconnected");
  }
}
