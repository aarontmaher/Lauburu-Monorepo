import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:lauburu_life_companion/models/customer_profile.dart';
import 'package:lauburu_life_companion/screens/chat_hub_screen.dart';
import 'package:lauburu_life_companion/screens/shopify_login_dialog.dart';
import 'package:lauburu_life_companion/services/session_storage.dart';
import 'package:lauburu_life_companion/services/shopify_auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Acceptance Criterion 31: Shopify Login Widget & Auth Token Capture Test', () {
    late PreferencesSessionStorage storage;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      storage = PreferencesSessionStorage();
    });

    testWidgets('ChatHubScreen initial state shows FREE tier badge and Login button', (tester) async {
      final authService = ShopifyAuthService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('FREE'), findsWidgets);
      expect(find.byKey(const Key('login_action_button')), findsOneWidget);
      expect(find.byKey(const Key('profile_action_button')), findsNothing);
    });

    testWidgets('Login dialog validates empty input fields', (tester) async {
      final authService = ShopifyAuthService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ShopifyLoginDialog(authService: authService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Login button without entering email/password
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pumpAndSettle();

      expect(find.text('Please enter your email'), findsOneWidget);
      expect(find.text('Please enter your password'), findsOneWidget);
    });

    testWidgets('Login flow captures and stores Shopify Auth Token in persistent storage', (tester) async {
      const expectedToken = 'shpat_widget_test_token_7777';

      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        if (query.contains('customerAccessTokenCreate')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenCreate': {
                  'customerAccessToken': {
                    'accessToken': expectedToken,
                    'expiresAt': '2026-10-15T12:00:00Z',
                  },
                  'customerUserErrors': [],
                }
              }
            }),
            200,
          );
        } else if (query.contains('getCustomerProfile')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customer': {
                  'id': 'gid://shopify/Customer/7777',
                  'email': 'athlete@lauburu.ai',
                  'firstName': 'Aaron',
                  'lastName': 'Maher',
                  'tags': ['lauburu_pro'],
                  'createdAt': '2026-01-01T00:00:00Z',
                  'orders': {'edges': []},
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authService = ShopifyAuthService(client: mockClient, storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService),
        ),
      );
      await tester.pumpAndSettle();

      // 1. Verify initial unauthenticated state
      expect(find.byKey(const Key('login_action_button')), findsOneWidget);
      expect(find.text('FREE'), findsOneWidget);

      // 2. Open login dialog via app bar action
      await tester.tap(find.byKey(const Key('login_action_button')));
      await tester.pumpAndSettle();

      expect(find.text('Shopify Account Login'), findsOneWidget);
      expect(find.byKey(const Key('email_field')), findsOneWidget);
      expect(find.byKey(const Key('password_field')), findsOneWidget);

      // 3. Enter credentials
      await tester.enterText(find.byKey(const Key('email_field')), 'athlete@lauburu.ai');
      await tester.enterText(find.byKey(const Key('password_field')), 'securePass123');
      await tester.pumpAndSettle();

      // 4. Tap login submit button
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pumpAndSettle();

      // 5. Verify Auth Token Capture and Persistence (Acceptance Criterion 31)
      expect(authService.isAuthenticated, isTrue);
      expect(authService.currentSession?.accessToken, equals(expectedToken));
      expect(authService.currentSession?.profile.email, equals('athlete@lauburu.ai'));
      expect(authService.currentSession?.profile.tier, equals(CustomerTier.pro));

      // 6. Verify underlying SharedPreferences storage directly
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(PreferencesSessionStorage.keyAccessToken), equals(expectedToken));

      final storedSession = await storage.loadSession();
      expect(storedSession, isNotNull);
      expect(storedSession!.accessToken, equals(expectedToken));
      expect(storedSession.profile.fullName, equals('Aaron Maher'));

      // 7. Verify UI state update: AppBar shows PRO badge and profile button
      expect(find.text('PRO'), findsWidgets);
      expect(find.byKey(const Key('profile_action_button')), findsOneWidget);
      expect(find.byKey(const Key('login_action_button')), findsNothing);
    });

    testWidgets('Login error banner displays when credentials fail', (tester) async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': {
              'customerAccessTokenCreate': {
                'customerAccessToken': null,
                'customerUserErrors': [
                  {
                    'code': 'UNIDENTIFIED_CUSTOMER',
                    'message': 'Unidentified customer. Check your email and password.',
                  }
                ],
              }
            }
          }),
          200,
        );
      });

      final authService = ShopifyAuthService(client: mockClient, storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ShopifyLoginDialog(authService: authService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('email_field')), 'bad@test.com');
      await tester.enterText(find.byKey(const Key('password_field')), 'wrongpass');
      await tester.tap(find.byKey(const Key('login_button')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('error_banner')), findsOneWidget);
      expect(find.textContaining('Unidentified customer'), findsOneWidget);
      expect(authService.isAuthenticated, isFalse);
    });

    testWidgets('Developer quick-login captures dev token into persistent storage', (tester) async {
      final authService = ShopifyAuthService(storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('login_action_button')));
      await tester.pumpAndSettle();

      // Open dev mode section
      await tester.tap(find.byKey(const Key('toggle_dev_mode_button')));
      await tester.pumpAndSettle();

      // Tap Quick Dev Login button
      await tester.ensureVisible(find.byKey(const Key('dev_login_button')));
      await tester.tap(find.byKey(const Key('dev_login_button')));
      await tester.pumpAndSettle();

      expect(authService.isAuthenticated, isTrue);
      expect(authService.currentSession?.accessToken, equals('shpat_dev_aaron_pro'));
      expect(authService.currentTier, equals(CustomerTier.pro));

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(PreferencesSessionStorage.keyAccessToken), equals('shpat_dev_aaron_pro'));
    });
  });
}
