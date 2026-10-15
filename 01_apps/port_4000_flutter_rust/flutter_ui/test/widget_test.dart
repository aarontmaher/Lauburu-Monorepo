import 'package:test/test.dart';
import 'package:lauburu_port4000_flutter/src/ui/dashboard_screen.dart';

void main() {
  test('Console Main Entrypoint & Renderer smoke test', () async {
    const renderer = DashboardScreenRenderer(width: 1100, height: 850);
    final html = renderer.renderDynamicDashboardHtml();
    expect(html, contains('Console Lauburu'));
    expect(html, contains('0% MOCK DATA'));
    expect(html, contains('STANDBY — DISCONNECTED'));
  });
}
