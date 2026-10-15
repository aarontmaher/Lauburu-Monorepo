import 'package:flutter/material.dart';
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
  String notebookState = "Waiting for JSON payload via Bluetooth...";

  @override
  void initState() {
    super.initState();
    btService.listenForJsonPayloads((payload) {
      setState(() {
        notebookState = "Rendered Cell: $payload";
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Flutter BT IDE (Variant 4)")),
      body: Center(
        child: Semantics(
          label: 'lens_ready: native_flutter_bt_ide',
          child: Text(notebookState, style: TextStyle(fontFamily: 'monospace')),
        ),
      ),
    );
  }
}
