import "dart:io";
import "package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart";

void main() {
  const renderer = DashboardScreenRenderer();
  final html = renderer.renderDynamicDashboardHtml();
  File("build/index.html").writeAsStringSync(html);
  print("Synchronized build/index.html: ${html.length} bytes");
}
