import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'bluetooth_serial_service.dart';

void main() => runApp(LauburuBluetoothIDE());

class LauburuBluetoothIDE extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Antigravity IDE',
      theme: ThemeData.dark(),
      home: BluetoothIdeScreen(),
    );
  }
}

class BluetoothIdeScreen extends StatefulWidget {
  @override
  _BluetoothIdeScreenState createState() => _BluetoothIdeScreenState();
}

class _BluetoothIdeScreenState extends State<BluetoothIdeScreen> {
  final BTService btService = BTService();
  List<String> _logs = ["Waiting for permissions..."];

  @override
  void initState() {
    super.initState();
    _requestPermissionsAndStart();
  }

  Future<void> _requestPermissionsAndStart() async {
    Map<Permission, PermissionStatus> statuses = await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.location,
    ].request();

    if (statuses[Permission.bluetoothScan]?.isGranted == true || statuses[Permission.location]?.isGranted == true) {
      setState(() {
        _logs.add("Permissions granted. Starting BT Service...");
      });
      btService.listenForJsonPayloads((payload) {
        setState(() {
          _logs.add(payload);
          if (_logs.length > 20) _logs.removeAt(0);
        });
      });
    } else {
      setState(() {
        _logs.add("Permissions denied. Cannot use Bluetooth.");
      });
    }
  }

  @override
  void dispose() {
    btService.disconnect();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Flutter BT IDE (Authentic)")),
      body: Padding(
        padding: const EdgeInsets.all(8.0),
        child: ListView.builder(
          itemCount: _logs.length,
          itemBuilder: (context, index) {
            return Semantics(
              label: 'lens_ready: native_flutter_bt_ide_log_$index',
              child: Text(
                _logs[index], 
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12)
              ),
            );
          }
        ),
      ),
    );
  }
}
