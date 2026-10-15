import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:lauburu_life_companion/models/customer_profile.dart';
import 'package:lauburu_life_companion/services/session_storage.dart';
import 'package:lauburu_life_companion/services/shopify_auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('CustomerTier & CustomerProfile Data Models', () {
    test('CustomerTier maps tags correctly', () {
      expect(CustomerTier.fromTags(['lauburu_elite', 'bjj']), equals(CustomerTier.elite));
      expect(CustomerTier.fromTags(['lauburu_pro', 'striking']), equals(CustomerTier.pro));
      expect(CustomerTier.fromTags(['general_customer']), equals(CustomerTier.free));
      expect(CustomerTier.fromTags([]), equals(CustomerTier.free));
    });

    test('CustomerTier maps strings correctly', () {
      expect(CustomerTier.fromString('elite'), equals(CustomerTier.elite));
      expect(CustomerTier.fromString('pro'), equals(CustomerTier.pro));
      expect(CustomerTier.fromString('free'), equals(CustomerTier.free));
      expect(CustomerTier.fromString(null), equals(CustomerTier.free));
    });

    test('CustomerProfile serializes and deserializes accurately', () {
      final profile = CustomerProfile(
        id: 'gid://shopify/Customer/1001',
        email: 'athlete@lauburu.ai',
        firstName: 'Aaron',
        lastName: 'Maher',
        tags: ['lauburu_pro'],
        tier: CustomerTier.pro,
        createdAt: DateTime(2026, 1, 1),
        orderCount: 3,
      );

      final json = profile.toJson();
      final reconstructed = CustomerProfile.fromJson(json);

      expect(reconstructed.id, equals(profile.id));
      expect(reconstructed.email, equals(profile.email));
      expect(reconstructed.fullName, equals('Aaron Maher'));
      expect(reconstructed.tier, equals(CustomerTier.pro));
      expect(reconstructed.tags, contains('lauburu_pro'));
      expect(reconstructed.orderCount, equals(3));
    });

    test('AuthSession serializes and deserializes accurately', () {
      final profile = CustomerProfile(
        id: 'gid://shopify/Customer/1002',
        email: 'elite@lauburu.ai',
        firstName: 'Master',
        lastName: 'Grappler',
        tags: ['lauburu_elite'],
        tier: CustomerTier.elite,
      );

      final session = AuthSession(
        accessToken: 'shpat_live_token_12345',
        expiresAt: DateTime.now().add(const Duration(days: 30)),
        profile: profile,
      );

      final jsonStr = session.toJsonString();
      final reconstructed = AuthSession.fromJsonString(jsonStr);

      expect(reconstructed.accessToken, equals(session.accessToken));
      expect(reconstructed.profile.tier, equals(CustomerTier.elite));
      expect(reconstructed.isExpired, isFalse);
    });
  });

  group('ShopifyAuthService Unit Tests', () {
    late PreferencesSessionStorage storage;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      storage = PreferencesSessionStorage();
    });

    test('login with valid credentials captures token and fetches pro profile', () async {
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        // Verify headers
        expect(request.headers['X-Shopify-Storefront-Access-Token'], equals('a39ead89f7318e991105e64873b4e10e'));

        if (query.contains('customerAccessTokenCreate')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenCreate': {
                  'customerAccessToken': {
                    'accessToken': 'shpat_test_live_pro_token',
                    'expiresAt': '2026-10-01T00:00:00Z',
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
                  'id': 'gid://shopify/Customer/9901',
                  'email': 'pro.member@lauburu.ai',
                  'firstName': 'Pro',
                  'lastName': 'User',
                  'tags': ['lauburu_pro'],
                  'createdAt': '2026-01-01T00:00:00Z',
                  'orders': {
                    'edges': [
                      {'node': {'id': 'gid://shopify/Order/1'}}
                    ]
                  }
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authService = ShopifyAuthService(
        client: mockClient,
        storage: storage,
      );

      final session = await authService.login('pro.member@lauburu.ai', 'password123');

      expect(session, isNotNull);
      expect(session!.accessToken, equals('shpat_test_live_pro_token'));
      expect(session.profile.tier, equals(CustomerTier.pro));
      expect(session.profile.fullName, equals('Pro User'));
      expect(authService.isAuthenticated, isTrue);
      expect(authService.currentTier, equals(CustomerTier.pro));

      // Verify persistent storage
      final storedSession = await storage.loadSession();
      expect(storedSession, isNotNull);
      expect(storedSession!.accessToken, equals('shpat_test_live_pro_token'));
    });

    test('login with elite tier tags maps to CustomerTier.elite', () async {
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        if (query.contains('customerAccessTokenCreate')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenCreate': {
                  'customerAccessToken': {
                    'accessToken': 'shpat_elite_token',
                    'expiresAt': '2026-10-01T00:00:00Z',
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
                  'id': 'gid://shopify/Customer/9902',
                  'email': 'elite@lauburu.ai',
                  'tags': ['lauburu_elite', 'sponsor'],
                  'orders': {'edges': []}
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authService = ShopifyAuthService(client: mockClient, storage: storage);
      final session = await authService.login('elite@lauburu.ai', 'password123');

      expect(session, isNotNull);
      expect(session!.profile.tier, equals(CustomerTier.elite));
      expect(authService.currentTier, equals(CustomerTier.elite));
    });

    test('login with invalid credentials throws descriptive exception', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': {
              'customerAccessTokenCreate': {
                'customerAccessToken': null,
                'customerUserErrors': [
                  {
                    'code': 'UNIDENTIFIED_CUSTOMER',
                    'field': ['input'],
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

      expect(
        () => authService.login('unknown@test.com', 'wrongpassword'),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Unidentified customer'),
        )),
      );

      expect(authService.isAuthenticated, isFalse);
      expect(await storage.hasSession(), isFalse);
    });

    test('loginWithDevToken provides instant zero-mock verified session', () async {
      final authService = ShopifyAuthService(storage: storage);
      final session = await authService.loginWithDevToken('shpat_dev_aaron_tester');

      expect(session, isNotNull);
      expect(session!.accessToken, equals('shpat_dev_aaron_tester'));
      expect(session.profile.tier, equals(CustomerTier.pro));
      expect(session.profile.tags, contains('developer'));
      expect(authService.isAuthenticated, isTrue);

      // Verify persistent storage
      final storedSession = await storage.loadSession();
      expect(storedSession, isNotNull);
      expect(storedSession!.accessToken, equals('shpat_dev_aaron_tester'));
    });

    test('refreshSession successfully renews live token and updates storage', () async {
      // First save an active session
      final initialSession = AuthSession(
        accessToken: 'shpat_old_token_111',
        expiresAt: DateTime.now().add(const Duration(hours: 1)),
        profile: CustomerProfile(
          id: 'gid://shopify/Customer/111',
          email: 'renew@lauburu.ai',
          tags: ['lauburu_pro'],
          tier: CustomerTier.pro,
        ),
      );
      await storage.saveSession(initialSession);

      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        if (query.contains('customerAccessTokenRenew')) {
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenRenew': {
                  'customerAccessToken': {
                    'accessToken': 'shpat_renewed_token_222',
                    'expiresAt': '2026-11-01T00:00:00Z',
                  },
                  'userErrors': [],
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
                  'id': 'gid://shopify/Customer/111',
                  'email': 'renew@lauburu.ai',
                  'tags': ['lauburu_pro'],
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authService = ShopifyAuthService(client: mockClient, storage: storage);
      await authService.restoreSession();

      final renewed = await authService.refreshSession();
      expect(renewed, isNotNull);
      expect(renewed!.accessToken, equals('shpat_renewed_token_222'));

      final stored = await storage.loadSession();
      expect(stored!.accessToken, equals('shpat_renewed_token_222'));
    });

    test('logout deletes remote token and clears storage', () async {
      var deleteCalled = false;
      final mockClient = MockClient((request) async {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        final query = body['query'] as String;

        if (query.contains('customerAccessTokenDelete')) {
          deleteCalled = true;
          return http.Response(
            jsonEncode({
              'data': {
                'customerAccessTokenDelete': {
                  'deletedAccessToken': 'shpat_live_delete_token',
                  'deletedCustomerAccessTokenId': 'gid://shopify/CustomerAccessToken/123',
                  'userErrors': [],
                }
              }
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authService = ShopifyAuthService(client: mockClient, storage: storage);
      final initialSession = AuthSession(
        accessToken: 'shpat_live_delete_token',
        expiresAt: DateTime.now().add(const Duration(days: 10)),
        profile: CustomerProfile(id: '1', email: 'del@test.com', tags: [], tier: CustomerTier.free),
      );
      await storage.saveSession(initialSession);
      await authService.restoreSession();

      expect(authService.isAuthenticated, isTrue);

      final loggedOut = await authService.logout();
      expect(loggedOut, isTrue);
      expect(deleteCalled, isTrue);
      expect(authService.isAuthenticated, isFalse);
      expect(authService.currentSession, isNull);
      expect(await storage.hasSession(), isFalse);
    });
  });
}
