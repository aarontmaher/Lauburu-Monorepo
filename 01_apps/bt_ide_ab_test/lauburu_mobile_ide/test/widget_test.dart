import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lauburu_mobile_ide/main.dart';

void main() {
  testWidgets('IDE Smoke Test', (WidgetTester tester) async {
    await tester.pumpWidget(LauburuBluetoothIDE());
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
