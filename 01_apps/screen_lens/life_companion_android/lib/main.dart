import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  runApp(const MaterialApp(home: LifeCompanionApp(), debugShowCheckedModeBanner: false));
}

class LifeCompanionApp extends StatefulWidget {
  const LifeCompanionApp({Key? key}) : super(key: key);
  @override
  State<LifeCompanionApp> createState() => _LifeCompanionAppState();
}

class _LifeCompanionAppState extends State<LifeCompanionApp> {
  late final WebViewController controller;

  @override
  void initState() {
    super.initState();
    controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..loadRequest(Uri.parse('http://100.119.199.76:3036'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: WebViewWidget(controller: controller),
      ),
    );
  }
}
