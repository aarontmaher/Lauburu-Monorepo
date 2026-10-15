import 'package:flutter_test/flutter_test.dart';
import 'package:movesense_terminal_flutter/main.dart';

void main() {
  testWidgets('App builds smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MovesenseTerminalApp());
    expect(find.text('Movesense Terminal Lauburu'), findsOneWidget);
  });
}
