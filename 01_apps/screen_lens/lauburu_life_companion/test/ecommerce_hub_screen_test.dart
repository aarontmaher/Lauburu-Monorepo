import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lauburu_life_companion/screens/chat_hub_screen.dart';
import 'package:lauburu_life_companion/screens/ecommerce_hub_screen.dart';
import 'package:lauburu_life_companion/services/ecommerce_ai_service.dart';
import 'package:lauburu_life_companion/services/shopify_auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  EcommerceAiService createTestAiService({
    String generatedCopy = 'Generated Ad Copy: High Performance Combat Gear.',
    bool meshOnline = true,
  }) {
    final mockClient = MockClient((request) async {
      if (request.url.path == '/health') {
        if (!meshOnline) {
          throw http.ClientException('Offline');
        }
        return http.Response(
          jsonEncode({
            'service': request.url.port == 8082
                ? 'Decentralized prima.cpp Self-Healing Mesh'
                : 'llama-server metal'
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path == '/v1/chat/completions') {
        if (!meshOnline) {
          throw http.ClientException('Offline');
        }
        return http.Response(
          jsonEncode({
            'model': 'qwen_38_max',
            'choices': [
              {
                'message': {'content': generatedCopy},
                'finish_reason': 'stop',
              }
            ]
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response('{}', 200);
    });

    return EcommerceAiService(client: mockClient);
  }

  group('Acceptance Criterion 33: E-Commerce Hub Screen Widget Tests', () {
    testWidgets('Initial state displays clean Rule 1 Zero-Mock waiting states ("--")', (tester) async {
      final testService = createTestAiService();

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );

      // Initial pump without evaluating metrics
      expect(find.byKey(const Key('metrics_capital')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('metrics_capital'))).data, equals('--'));

      expect(find.byKey(const Key('metrics_pay_by_compute')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('metrics_pay_by_compute'))).data, equals('--'));

      expect(find.byKey(const Key('metrics_fiat_reserve')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('metrics_fiat_reserve'))).data, equals('--'));

      expect(find.byKey(const Key('metrics_openrouter_credits')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('metrics_openrouter_credits'))).data, equals('--'));

      expect(find.byKey(const Key('metrics_catalog_count')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('metrics_catalog_count'))).data, equals('--'));

      // Ad copy container initial state must be '--'
      expect(find.byKey(const Key('ad_copy_text')), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('ad_copy_text'))).data, equals('--'));
    });

    testWidgets('Renders canonical 18-item catalog list with accurate metadata', (tester) async {
      final testService = createTestAiService();

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('catalog_section_title')), findsOneWidget);
      expect(find.text('Commercial Catalog (18 Items)'), findsOneWidget);

      // Check item 01: Rashguard
      expect(find.byKey(const Key('catalog_item_item_01')), findsOneWidget);
      expect(find.byKey(const Key('item_title_item_01')), findsOneWidget);
      expect(find.text('Lauburu Canonical Short Sleeve Rashguard'), findsOneWidget);
      expect(find.text('\$97.50 AUD'), findsOneWidget);

      // Check item 02: Fight shorts
      expect(find.byKey(const Key('catalog_item_item_02')), findsOneWidget);
      expect(find.text('Lauburu Canonical No-Gi Pro Fight Shorts'), findsOneWidget);
      expect(find.text('\$90.00 AUD'), findsOneWidget);
    });

    testWidgets('Renders AI mesh health status badges for Port 8082 and Port 8083', (tester) async {
      final testService = createTestAiService(meshOnline: true);

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('ai_mesh_status_bar')), findsOneWidget);
      expect(find.byKey(const Key('ai_badge_8082')), findsOneWidget);
      expect(find.byKey(const Key('ai_badge_8083')), findsOneWidget);
      expect(find.text('Port 8082'), findsOneWidget);
      expect(find.text('Port 8083'), findsOneWidget);
    });

    testWidgets('Category filter chips correctly filter displayed catalog items', (tester) async {
      final testService = createTestAiService();

      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );
      await tester.pumpAndSettle();

      // Tap 'Streetwear' chip
      final streetwearChip = find.widgetWithText(ChoiceChip, 'Streetwear');
      await tester.ensureVisible(streetwearChip);
      await tester.tap(streetwearChip);
      await tester.pumpAndSettle();

      expect(find.text('Commercial Catalog (3 Items)'), findsOneWidget);
      expect(find.text('Heavyweight Fleece Pullover Hoodie'), findsOneWidget);
      expect(find.text('Unisex Heavyweight Fleece Joggers'), findsOneWidget);
      expect(find.text('Heavyweight Streetwear Boxy Tee'), findsOneWidget);
      // Combat uniform should not be in the filtered list
      expect(find.text('Lauburu Canonical Short Sleeve Rashguard'), findsNothing);

      // Tap 'All' chip to reset
      final allChip = find.widgetWithText(ChoiceChip, 'All');
      await tester.ensureVisible(allChip);
      await tester.tap(allChip);
      await tester.pumpAndSettle();
      expect(find.text('Commercial Catalog (18 Items)'), findsOneWidget);
    });

    testWidgets('Tapping "Evaluate Metrics" loads metrics and updates UI from "--" to real values', (tester) async {
      final testService = createTestAiService();

      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );
      await tester.pumpAndSettle();

      // Initial is '--'
      expect(tester.widget<Text>(find.byKey(const Key('metrics_capital'))).data, equals('--'));

      // Tap Evaluate Metrics
      final button = find.byKey(const Key('evaluate_metrics_button'));
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();

      // Metrics updated
      expect(tester.widget<Text>(find.byKey(const Key('metrics_capital'))).data, equals('\$14315.00 AUD'));
      expect(tester.widget<Text>(find.byKey(const Key('metrics_pay_by_compute'))).data, equals('\$3800.00 AUD'));
      expect(tester.widget<Text>(find.byKey(const Key('metrics_fiat_reserve'))).data, equals('\$10515.00 AUD'));
      expect(tester.widget<Text>(find.byKey(const Key('metrics_openrouter_credits'))).data, equals('262 Credits'));
      expect(tester.widget<Text>(find.byKey(const Key('metrics_catalog_count'))).data, equals('18'));
    });

    testWidgets('Tapping "Generate Ad Copy" triggers local AI and updates UI from "--" to copy', (tester) async {
      const generatedCopy = 'Hook: Zero-Compromise Combat Rashguard.\nBenefits:\n- Anti-odor\n- 4-way stretch';
      final testService = createTestAiService(generatedCopy: generatedCopy);

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(aiService: testService),
        ),
      );
      await tester.pumpAndSettle();

      // Initial state is '--'
      expect(tester.widget<Text>(find.byKey(const Key('ad_copy_text'))).data, equals('--'));

      // Tap Generate Ad Copy button
      await tester.tap(find.byKey(const Key('generate_ad_button')));
      await tester.pumpAndSettle();

      // Text updated to generated copy
      expect(tester.widget<Text>(find.byKey(const Key('ad_copy_text'))).data, equals(generatedCopy));
    });

    testWidgets('ChatHubScreen AppBar includes E-Commerce Hub navigation button that opens EcommerceHubScreen', (tester) async {
      final authService = ShopifyAuthService(
        client: MockClient((request) async => http.Response('{}', 200)),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService),
        ),
      );
      await tester.pumpAndSettle();

      // E-Commerce button is present in AppBar
      final ecommerceButton = find.byKey(const Key('ecommerce_hub_button'));
      expect(ecommerceButton, findsOneWidget);

      // Tap navigation button
      await tester.tap(ecommerceButton);
      await tester.pumpAndSettle();

      // EcommerceHubScreen is now open
      expect(find.text('E-Commerce Hub'), findsOneWidget);
      expect(find.byKey(const Key('ai_mesh_status_bar')), findsOneWidget);
    });
  });
}
