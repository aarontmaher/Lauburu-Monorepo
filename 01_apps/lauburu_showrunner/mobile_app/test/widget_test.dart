import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:showrunner_lauburu/main.dart';

void main() {
  testWidgets('Lauburu Showrunner App initial render and Arena switch test', (WidgetTester tester) async {
    // Set desktop / tablet screen size for test environment
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // Build the Lauburu Showrunner app and trigger a frame.
    await tester.pumpWidget(const LauburuShowrunnerApp());
    await tester.pump(const Duration(milliseconds: 500));

    // Verify that the title header is rendered
    expect(find.text('LAUBURU 7-LAYER MESH'), findsOneWidget);

    // Verify that the hardware topology card is rendered
    expect(find.text('HARDWARE TOPOLOGY'), findsOneWidget);

    // Tap on TATAMI nav tab in the AppBar
    final arenaTab = find.text('TATAMI');
    expect(arenaTab, findsOneWidget);
    await tester.tap(arenaTab);
    await tester.pumpAndSettle();

    // Verify that the title header switches to TATAMI COMBAT ARENA
    expect(find.text('TATAMI COMBAT ARENA'), findsOneWidget);

    // Verify that the Tatami Combat Arena elements are present
    expect(find.text('MATSIDE CORNER COACH'), findsOneWidget);
    expect(find.text('START ROLL'), findsOneWidget);
  });
}
