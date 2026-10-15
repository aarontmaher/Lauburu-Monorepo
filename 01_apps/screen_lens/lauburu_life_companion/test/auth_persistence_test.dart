import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:lauburu_life_companion/models/customer_profile.dart';
import 'package:lauburu_life_companion/screens/chat_hub_screen.dart';
import 'package:lauburu_life_companion/services/session_storage.dart';
import 'package:lauburu_life_companion/services/shopify_auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Acceptance Criterion 32: Authentication State Persistence Across App Restarts', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('SessionStorage accurately writes and recovers session data', () async {
      final storage = PreferencesSessionStorage();

      final originalSession = AuthSession(
        accessToken: 'shpat_persistent_token_9999',
        expiresAt: DateTime.now().add(const Duration(days: 90)),
        profile: CustomerProfile(
          id: 'gid://shopify/Customer/9999',
          email: 'sovereign@lauburu.ai',
          firstName: 'Sovereign',
          lastName: 'User',
          tags: ['lauburu_pro', 'founder'],
          tier: CustomerTier.pro,
          orderCount: 5,
        ),
      );

      await storage.saveSession(originalSession);

      // Simulate process restart by creating a new storage instance
      final restartedStorage = PreferencesSessionStorage();
      final loadedSession = await restartedStorage.loadSession();

      expect(loadedSession, isNotNull);
      expect(loadedSession!.accessToken, equals('shpat_persistent_token_9999'));
      expect(loadedSession.profile.email, equals('sovereign@lauburu.ai'));
      expect(loadedSession.profile.fullName, equals('Sovereign User'));
      expect(loadedSession.profile.tier, equals(CustomerTier.pro));
      expect(loadedSession.profile.orderCount, equals(5));
      expect(loadedSession.isExpired, isFalse);
    });

    testWidgets('Authenticated state survives complete app restart and renders PRO tier', (tester) async {
      final storage = PreferencesSessionStorage();
      const testToken = 'shpat_restart_survivor_token_8888';

      // 1. Initial Session Launch: User logs in
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        if (query.contains('customerAccessTokenCreate')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenCreate': {
                  'customerAccessToken': {
                    'accessToken': testToken,
                    'expiresAt': '2027-01-01T00:00:00Z',
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
                  'id': 'gid://shopify/Customer/8888',
                  'email': 'athlete@lauburu.ai',
                  'firstName': 'Aaron',
                  'lastName': 'Maher',
                  'tags': ['lauburu_pro'],
                  'createdAt': '2026-01-01T00:00:00Z',
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final initialAuthService = ShopifyAuthService(client: mockClient, storage: storage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: initialAuthService),
        ),
      );
      await tester.pumpAndSettle();

      // Perform login in first session
      final session = await initialAuthService.login('athlete@lauburu.ai', 'validPassword');
      expect(session, isNotNull);
      expect(initialAuthService.isAuthenticated, isTrue);

      // Verify widget reflected the login
      await tester.pumpAndSettle();
      expect(find.text('PRO'), findsWidgets);
      expect(find.byKey(const Key('profile_action_button')), findsOneWidget);

      // 2. SIMULATE APP TERMINATION & RESTART
      // Clear widget tree and dispose old service
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      initialAuthService.dispose();

      // 3. New App Launch: Re-instantiate services from persistent storage
      final restartedStorage = PreferencesSessionStorage();
      final freshAuthService = ShopifyAuthService(client: mockClient, storage: restartedStorage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: freshAuthService),
        ),
      );
      await tester.pumpAndSettle();

      // 4. Verify that session state was restored automatically on launch
      expect(freshAuthService.isAuthenticated, isTrue);
      expect(freshAuthService.currentSession?.accessToken, equals(testToken));
      expect(freshAuthService.currentSession?.profile.fullName, equals('Aaron Maher'));
      expect(freshAuthService.currentTier, equals(CustomerTier.pro));

      // 5. Verify UI immediately renders authenticated PRO state
      expect(find.text('PRO'), findsWidgets);
      expect(find.byKey(const Key('profile_action_button')), findsOneWidget);
      expect(find.byKey(const Key('login_action_button')), findsNothing);
    });

    testWidgets('Logout state change persists across app restarts', (tester) async {
      final storage = PreferencesSessionStorage();
      final authService1 = ShopifyAuthService(storage: storage);

      // Seed with an active session
      await authService1.loginWithDevToken('shpat_dev_aaron_seed');
      expect(authService1.isAuthenticated, isTrue);

      // User performs logout
      await authService1.logout();
      expect(authService1.isAuthenticated, isFalse);

      // SIMULATE APP RESTART
      final restartedStorage = PreferencesSessionStorage();
      final authService2 = ShopifyAuthService(storage: restartedStorage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService2),
        ),
      );
      await tester.pumpAndSettle();

      // Verify unauthenticated state persisted
      expect(authService2.isAuthenticated, isFalse);
      expect(authService2.currentSession, isNull);
      expect(find.text('FREE'), findsWidgets);
      expect(find.byKey(const Key('login_action_button')), findsOneWidget);
    });

    testWidgets('Tier upgrade (PRO -> ELITE) persists across app restarts', (tester) async {
      final storage = PreferencesSessionStorage();

      // 1. Initially logged in as PRO
      final proSession = AuthSession(
        accessToken: 'shpat_tier_upgrade_token',
        expiresAt: DateTime.now().add(const Duration(days: 30)),
        profile: CustomerProfile(
          id: 'gid://shopify/Customer/555',
          email: 'champion@lauburu.ai',
          firstName: 'Grappler',
          tags: ['lauburu_pro'],
          tier: CustomerTier.pro,
        ),
      );
      await storage.saveSession(proSession);

      // 2. Cloud sync upgrades customer tags to ELITE
      final upgradedSession = proSession.copyWith(
        profile: proSession.profile.copyWith(
          tags: ['lauburu_elite'],
          tier: CustomerTier.elite,
        ),
      );
      await storage.saveSession(upgradedSession);

      // 3. SIMULATE APP RESTART
      final restartedStorage = PreferencesSessionStorage();
      final authService2 = ShopifyAuthService(storage: restartedStorage);

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService2),
        ),
      );
      await tester.pumpAndSettle();

      expect(authService2.isAuthenticated, isTrue);
      expect(authService2.currentTier, equals(CustomerTier.elite));
      expect(find.text('ELITE'), findsWidgets);
    });
  });
}
