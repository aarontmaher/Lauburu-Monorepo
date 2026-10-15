import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lauburu_life_companion/models/inbox_models.dart';
import 'package:lauburu_life_companion/screens/chat_hub_screen.dart';
import 'package:lauburu_life_companion/services/chat_hub_service.dart';
import 'package:lauburu_life_companion/services/omni_ai_triage_service.dart';
import 'package:lauburu_life_companion/services/omni_inbox_service.dart';
import 'package:lauburu_life_companion/services/shopify_auth_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Domain Models & Serialization Tests', () {
    test('InboxMessage JSON roundtrip serialization', () {
      final msg = InboxMessage(
        id: 'msg_101',
        threadId: 'th_202',
        senderName: 'Lachy',
        senderAddress: 'lachy@gumtree.com.au',
        text: 'Is the iPhone 16 Pro available?',
        timestamp: DateTime.parse('2026-09-17T12:00:00Z'),
        isOutgoing: false,
        channel: InboxChannel.gumtree,
        status: MessageStatus.delivered,
        suggestedReplies: const ['Yes available', 'Can meet at Altona Gate'],
        richCardData: const {'item': 'iPhone 16 Pro'},
      );

      final json = msg.toJson();
      final roundtrip = InboxMessage.fromJson(json);

      expect(roundtrip.id, equals('msg_101'));
      expect(roundtrip.threadId, equals('th_202'));
      expect(roundtrip.senderName, equals('Lachy'));
      expect(roundtrip.text, equals('Is the iPhone 16 Pro available?'));
      expect(roundtrip.isOutgoing, isFalse);
      expect(roundtrip.channel, equals(InboxChannel.gumtree));
      expect(roundtrip.suggestedReplies.length, equals(2));
      expect(roundtrip.richCardData?['item'], equals('iPhone 16 Pro'));
    });

    test('InboxThread JSON roundtrip serialization', () {
      final thread = InboxThread(
        id: 'th_gumtree',
        channel: InboxChannel.gumtree,
        contactName: 'Lachy',
        contactAddress: 'lachy@gumtree.com.au',
        subject: 'iPhone 16 Pro',
        lastMessagePreview: '\$990 cash works',
        lastMessageTime: DateTime.parse('2026-09-17T12:30:00Z'),
        unreadCount: 1,
        priority: InboxPriority.actionRequired,
        isPinned: true,
        aiSummary: 'Cash buyer awaiting meeting time',
      );

      final json = thread.toJson();
      final roundtrip = InboxThread.fromJson(json);

      expect(roundtrip.id, equals('th_gumtree'));
      expect(roundtrip.channel, equals(InboxChannel.gumtree));
      expect(roundtrip.contactName, equals('Lachy'));
      expect(roundtrip.priority, equals(InboxPriority.actionRequired));
      expect(roundtrip.isPinned, isTrue);
      expect(roundtrip.unreadCount, equals(1));
    });

    test('TriageResult JSON roundtrip serialization', () {
      const triage = TriageResult(
        priority: InboxPriority.commercialLead,
        reasoning: 'Direct cash purchase intent for listed item.',
        suggestedReplies: ['Can meet today at Altona Gate', '\$990 cash works'],
        port: 8082,
        latencyMs: 142,
        isAiAssigned: true,
        isFallback: false,
      );

      final json = triage.toJson();
      final roundtrip = TriageResult.fromJson(json);

      expect(roundtrip.priority, equals(InboxPriority.commercialLead));
      expect(roundtrip.reasoning, contains('Direct cash purchase'));
      expect(roundtrip.suggestedReplies.length, equals(2));
      expect(roundtrip.port, equals(8082));
      expect(roundtrip.isAiAssigned, isTrue);
      expect(roundtrip.isFallback, isFalse);
    });
  });

  group('OmniInboxService Unit Tests', () {
    late OmniInboxService inboxService;

    setUp(() {
      inboxService = OmniInboxService();
    });

    tearDown(() {
      inboxService.dispose();
    });

    test('Initial state contains authentic multi-account seed threads from business ledger', () {
      final threads = inboxService.currentThreads;
      expect(threads.length, greaterThanOrEqualTo(7));

      final channels = threads.map((t) => t.channel).toSet();
      expect(channels.contains(InboxChannel.gumtree), isTrue);
      expect(channels.contains(InboxChannel.gmailBusiness), isTrue);
      expect(channels.contains(InboxChannel.shopify), isTrue);
    });

    test('Clean waiting state when business ledger is absent', () {
      final customService = OmniInboxService(ledgerPath: '/non/existent/path/ledger.json');
      expect(customService.currentThreads.isEmpty, isTrue);
      expect(customService.isWaitingState, isTrue);
      customService.dispose();
    });

    test('getThreads filters by channel correctly', () {
      final gumtreeThreads =
          inboxService.getThreads(filter: InboxChannel.gumtree);
      expect(gumtreeThreads.isNotEmpty, isTrue);
      expect(
          gumtreeThreads.every((t) => t.channel == InboxChannel.gumtree), isTrue);

      final shopifyThreads =
          inboxService.getThreads(filter: InboxChannel.shopify);
      expect(shopifyThreads.isNotEmpty, isTrue);
      expect(
          shopifyThreads.every((t) => t.channel == InboxChannel.shopify), isTrue);

      final allThreads = inboxService.getThreads(filter: InboxChannel.all);
      expect(allThreads.length, equals(inboxService.currentThreads.length));
    });

    test('sendMessage appends outgoing message and updates preview', () async {
      final threadId = inboxService.currentThreads.first.id;
      final initialCount =
          inboxService.getThreadById(threadId)!.messages.length;

      await inboxService.sendMessage(threadId, 'Meeting at Altona Gate at 3:30pm');

      final updated = inboxService.getThreadById(threadId)!;
      expect(updated.messages.length, equals(initialCount + 1));
      expect(updated.lastMessagePreview, equals('Meeting at Altona Gate at 3:30pm'));
      expect(updated.messages.last.isOutgoing, isTrue);
    });

    test('markAsRead clears unread count', () async {
      // Find a thread with unreadCount > 0
      final unreadThread =
          inboxService.currentThreads.firstWhere((t) => t.unreadCount > 0);
      expect(unreadThread.unreadCount, greaterThan(0));

      await inboxService.markAsRead(unreadThread.id);

      final updated = inboxService.getThreadById(unreadThread.id)!;
      expect(updated.unreadCount, equals(0));
    });
  });

  group('OmniAiTriageService Unit Tests', () {
    test('Heuristic fallback assigns VIP for Subliminator/Hicham and Elite tier', () {
      final service = OmniAiTriageService();

      final result1 = service.computeHeuristicFallback(
        channel: InboxChannel.gmailBusiness,
        contactAddress: 'hicham@subliminator.com',
        latestMessageText: 'Ready to issue sample invoice.',
      );
      expect(result1.priority, equals(InboxPriority.vip));

      final result2 = service.computeHeuristicFallback(
        channel: InboxChannel.shopify,
        contactAddress: 'vip@customer.com',
        latestMessageText: 'Order inquiry',
        customerTier: 'elite',
      );
      expect(result2.priority, equals(InboxPriority.vip));
    });

    test('Heuristic fallback assigns Action Required for scheduling and urgent queries', () {
      final service = OmniAiTriageService();

      final result = service.computeHeuristicFallback(
        channel: InboxChannel.gumtree,
        contactAddress: 'buyer@gumtree.com.au',
        latestMessageText: 'Can meet at Altona Gate at 3:30pm? Does that work?',
      );
      expect(result.priority, equals(InboxPriority.actionRequired));
    });

    test('Heuristic fallback assigns Commercial Lead for buying and pricing inquiries', () {
      final service = OmniAiTriageService();

      final result = service.computeHeuristicFallback(
        channel: InboxChannel.instagram,
        contactAddress: '@athlete_grappler',
        latestMessageText: 'Are the competition rashguards restocked in size L?',
      );
      expect(result.priority, equals(InboxPriority.commercialLead));
    });

    test('Offline resilience returns deterministic fallback and empty smart replies', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final service = OmniAiTriageService(client: mockClient);

      final triage = await service.triageConversation(
        channel: InboxChannel.gumtree,
        contactName: 'Lachy',
        contactAddress: 'lachy@gumtree.com.au',
        recentMessages: [
          {'sender': 'Lachy', 'text': 'Can meet at Altona Gate at 3:30pm?'}
        ],
      );

      expect(triage.priority, equals(InboxPriority.actionRequired));
      expect(triage.isFallback, isTrue);

      final replies = await service.generateSmartReplies(
        channel: InboxChannel.gumtree,
        recentMessages: [
          {'sender': 'Lachy', 'text': 'Can meet at 3:30pm?'}
        ],
      );
      expect(replies, isEmpty);
    });

    test('AI chat completions parsing extracts priority and smart replies', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'model': 'qwen_38_max',
            'choices': [
              {
                'message': {
                  'content': jsonEncode({
                    'priority': 'commercial_lead',
                    'reasoning': 'Buyer negotiating cash purchase on listed iPhone.',
                    'suggested_replies': [
                      '3:30pm at Altona Gate works for me.',
                      'Cash or instant OSKO on inspection is fine.',
                      'See you near the food court entrance.'
                    ]
                  }),
                },
                'finish_reason': 'stop',
              }
            ]
          }),
          200,
        );
      });

      final service = OmniAiTriageService(client: mockClient);

      final triage = await service.triageConversation(
        channel: InboxChannel.gumtree,
        contactName: 'Lachy',
        contactAddress: 'lachy@gumtree.com.au',
        recentMessages: [
          {'sender': 'Lachy', 'text': 'Can meet at Altona Gate at 3:30pm?'}
        ],
      );

      expect(triage.priority, equals(InboxPriority.commercialLead));
      expect(triage.reasoning, contains('Buyer negotiating'));
      expect(triage.suggestedReplies.length, equals(3));
      expect(triage.isAiAssigned, isTrue);
      expect(triage.port, equals(8082));
    });

    test('probeModelHealth returns online when endpoint responds HTTP 200', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'service': 'qwen_38_max', 'status': 'ok'}),
          200,
        );
      });

      final service = OmniAiTriageService(client: mockClient);
      final status = await service.probeModelHealth(port: 8082);

      expect(status.isOnline, isTrue);
      expect(status.port, equals(8082));
    });
  });

  group('OmniInboxScreen Widget Tests', () {
    testWidgets('OmniInboxScreen renders conversation threads with distinct platform badges', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      // Verify contact names are displayed
      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);
      expect(find.text('Shopify Commerce Lead (Order #LBG-1082)'), findsOneWidget);

      // Verify channel badges
      expect(find.text('Gumtree'), findsWidgets);
      expect(find.text('Gmail: Lauburu'), findsWidgets);
      expect(find.text('Shopify'), findsWidgets);

      // Verify priority badges
      expect(find.text('Action Required'), findsWidgets);
      expect(find.text('Commercial Lead'), findsWidgets);
      expect(find.text('VIP'), findsWidgets);
    });

    testWidgets('Selecting channel filter chips correctly filters the thread list', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      // Initial state: multiple threads visible
      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);

      // Ensure Gumtree filter pill is visible and tap it
      await tester.ensureVisible(find.byKey(const Key('filter_gumtree')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('filter_gumtree')));
      await tester.pumpAndSettle();

      // Only Gumtree thread visible
      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsNothing);
      expect(find.text('Shopify Commerce Lead (Order #LBG-1082)'), findsNothing);

      // Tap All filter pill to restore full list
      await tester.ensureVisible(find.byKey(const Key('filter_all')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('filter_all')));
      await tester.pumpAndSettle();

      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);
    });

    testWidgets('Search field filters threads by contact name or message preview', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      // Enter search query
      await tester.enterText(find.byKey(const Key('inbox_search_field')), 'Hicham');
      await tester.pumpAndSettle();

      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);
      expect(find.text('Lachy (Gumtree Buyer)'), findsNothing);

      // Clear search query
      await tester.enterText(find.byKey(const Key('inbox_search_field')), '');
      await tester.pumpAndSettle();

      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);
    });

    testWidgets('Opening thread displays chronological messages and safe pickup card', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Gumtree thread
      await tester.tap(find.byKey(const Key('thread_tile_gumtree_lachy_iphone')));
      await tester.pumpAndSettle();

      // Verify thread detail screen opened
      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('SAFE MARKETPLACE TRANSACTION'), findsOneWidget);
      expect(find.textContaining('Altona Gate Shopping Centre'), findsWidgets);
      expect(find.textContaining('\$990 cash works'), findsOneWidget);

      // Drag messages list down to view earliest message in thread
      await tester.drag(find.byType(ListView).first, const Offset(0, 300));
      await tester.pumpAndSettle();
      expect(find.textContaining('Would you take \$950 cash today?'), findsOneWidget);
    });

    testWidgets('Smart reply chips populate composer in thread detail screen', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      // Open Gumtree thread
      await tester.tap(find.byKey(const Key('thread_tile_gumtree_lachy_iphone')));
      await tester.pumpAndSettle();

      // Check smart reply chip is present
      final chipFinder = find.byKey(const Key('smart_reply_chip_0'));
      expect(chipFinder, findsOneWidget);

      // Tap smart reply chip
      await tester.tap(chipFinder);
      await tester.pumpAndSettle();

      // Verify composer text field has been populated
      final textField = tester.widget<TextField>(find.byKey(const Key('message_composer_input')));
      expect(textField.controller?.text, isNotEmpty);

      // Tap send button
      await tester.tap(find.byKey(const Key('message_send_button')));
      await tester.pumpAndSettle();

      // Verify message was sent and composer was cleared
      final clearedField = tester.widget<TextField>(find.byKey(const Key('message_composer_input')));
      expect(clearedField.controller?.text, isEmpty);
    });
  });

  group('ChatHubScreen Backward-Compatibility Tests', () {
    testWidgets('ChatHubScreen renders OmniInboxScreen and preserves single FREE occurrence', (tester) async {
      final authService = ShopifyAuthService();

      await tester.pumpWidget(
        MaterialApp(
          home: ChatHubScreen(authService: authService),
        ),
      );
      await tester.pumpAndSettle();

      // Acceptance Criterion: exact match for 'FREE' in unauthenticated state
      expect(find.text('FREE'), findsOneWidget);

      // All AppBar buttons are present
      expect(find.byKey(const Key('login_action_button')), findsOneWidget);
      expect(find.byKey(const Key('ecommerce_hub_button')), findsOneWidget);
      expect(find.byKey(const Key('appbar_tier_badge')), findsOneWidget);

      // ChatHubService adapter connects cleanly without errors
      final chatHubService = ChatHubService();
      chatHubService.connect();
      expect(chatHubService.messagesStream, isNotNull);
      chatHubService.dispose();
    });
  });
}
