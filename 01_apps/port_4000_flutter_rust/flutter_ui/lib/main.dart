// Lauburu Port 4000 Console: Main Entrypoint & Bridge Orchestrator

import 'dart:io';
import 'src/bridge/native_bridge.dart';
import 'src/ui/dashboard_screen.dart';

void main(List<String> args) async {
  print('============================================================');
  print('🚀 LAUBURU PORT 4000 ZERO-MOCK CONSOLE BUILDER');
  print('============================================================');

  final bridge = LauburuNativeBridge();
  print('📡 Native Rust FFI Loaded: ${bridge.isFfiLoaded}');

  final renderer = const DashboardScreenRenderer(width: 1100, height: 850);
  final html = renderer.renderDynamicDashboardHtml();

  final outDir = Directory('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build');
  if (!outDir.existsSync()) {
    outDir.createSync(recursive: true);
  }
  final outFile = File('${outDir.path}/index.html');
  outFile.writeAsStringSync(html);
  print('✅ Live Zero-Mock Console HTML generated: ${outFile.path}');
  print('============================================================');
}
