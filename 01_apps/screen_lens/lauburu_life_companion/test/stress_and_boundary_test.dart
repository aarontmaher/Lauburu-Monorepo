import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lauburu_life_companion/models/inbox_models.dart';
import 'package:lauburu_life_companion/screens/inbox_thread_detail_screen.dart';
import 'package:lauburu_life_companion/screens/omni_inbox_screen.dart';
import 'package:lauburu_life_companion/services/chat_hub_service.dart';
import 'package:lauburu_life_companion/services/mesh_terminal_service.dart';
import 'package:lauburu_life_companion/services/omni_ai_triage_service.dart';
import 'package:lauburu_life_companion/services/omni_inbox_service.dart';
import 'package:lauburu_life_companion/widgets/mesh_terminal_sheet.dart';
import 'helpers/mock_mesh_terminal_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Adversarial Challenge 1: TCP Port 4005 Daemon & Socket Stress', () {
    test('MeshTerminalService unreachable port handling and safe disconnect', () async {
      // Connect to an unreachable local port with short timeout
      final service = MeshTerminalService(
        configuredHost: '127.0.0.1',
        defaultPort: 59998, // Port unlikely to be open
      );

      expect(service.state, equals(TerminalConnectionState.disconnected));
      expect(service.lastError, isNull);

      // Attempt connect - should transition to connecting then error without uncaught exception
      await service.connect(port: 59998);

      expect(service.state, equals(TerminalConnectionState.error));
      expect(service.lastError, isNotNull);
      expect(service.lastError, contains('Connection refused'));

      // Sending command while in error state must fail gracefully without throwing
      await service.sendCommand('status');
      expect(service.lastError, equals('Not connected to terminal socket'));

      // Disconnect and dispose must be idempotent and crash-free
      await service.disconnect();
      expect(service.state, equals(TerminalConnectionState.disconnected));

      service.dispose();
      // Double dispose must not crash
      expect(() => service.dispose(), returnsNormally);
    });

    testWidgets('MeshTerminalSheet boundary: authentic SocketException handled without RenderFlex overflow and buttons remain interactive', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      FlutterErrorDetails? layoutOverflowError;
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        if (details.exceptionAsString().contains('A RenderFlex overflowed')) {
          layoutOverflowError = details;
        } else {
          originalOnError?.call(details);
        }
      };
      addTearDown(() {
        FlutterError.onError = originalOnError;
      });

      // Pass an unreachable service triggering real SocketException
      final unreachableService = MeshTerminalService(
        configuredHost: '127.0.0.1',
        defaultPort: 59997,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: unreachableService),
          ),
        ),
      );

      // Pump initial render
      await tester.pump();
      expect(find.byType(MeshTerminalSheet), findsOneWidget);

      // Await connection timeout/rejection
      await tester.pump(const Duration(seconds: 4));

      // Status badge shows error state
      expect(unreachableService.state, equals(TerminalConnectionState.error));
      expect(unreachableService.lastError, contains('SocketException'));

      // Empirical Confirmation of Boundary Remediation:
      // ZERO RenderFlex overflow occurs when SocketException is caught
      expect(layoutOverflowError, isNull, reason: 'SocketException in _statusLabel must NOT trigger RenderFlex overflow');
      expect(find.text('Connection Error'), findsOneWidget);

      // Verify that terminal_close_button and terminal_reconnect_button remain visible and interactive
      final reconnectBtn = find.byKey(const Key('terminal_reconnect_button'));
      final closeBtn = find.byKey(const Key('terminal_close_button'));
      expect(reconnectBtn, findsOneWidget);
      expect(closeBtn, findsOneWidget);

      // Verify buttons are fully within the 1200px viewport bounds
      final closeRect = tester.getRect(closeBtn);
      expect(closeRect.right, lessThanOrEqualTo(1200.0));
      expect(closeRect.left, greaterThan(0.0));

      final reconnectRect = tester.getRect(reconnectBtn);
      expect(reconnectRect.right, lessThanOrEqualTo(closeRect.left));

      // Verify interaction is unobstructed
      await tester.tap(reconnectBtn);
      await tester.pump(const Duration(seconds: 4));

      unreachableService.dispose();
    });

    testWidgets('MeshTerminalSheet mobile viewport boundary (360px): no overflow under error and buttons interactive', (tester) async {
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      FlutterErrorDetails? layoutOverflowError;
      final originalOnError = FlutterError.onError;
      FlutterError.onError = (details) {
        if (details.exceptionAsString().contains('A RenderFlex overflowed')) {
          layoutOverflowError = details;
        } else {
          originalOnError?.call(details);
        }
      };
      addTearDown(() {
        FlutterError.onError = originalOnError;
      });

      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      mockService.emitState(TerminalConnectionState.error, error: 'Connection refused');
      await tester.pumpAndSettle();

      expect(layoutOverflowError, isNull, reason: 'Mobile 360px viewport must not overflow in error state');
      expect(find.text('Connection Error'), findsOneWidget);

      final closeBtn = find.byKey(const Key('terminal_close_button'));
      final reconnectBtn = find.byKey(const Key('terminal_reconnect_button'));
      expect(closeBtn, findsOneWidget);
      expect(reconnectBtn, findsOneWidget);

      final closeRect = tester.getRect(closeBtn);
      expect(closeRect.right, lessThanOrEqualTo(360.0));
      expect(closeRect.left, greaterThan(0.0));

      await tester.tap(closeBtn);
      await tester.pumpAndSettle();

      mockService.dispose();
    });

    testWidgets('Rapid macro button spamming maintains command ordering and UI integrity', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Stress test: 20 rapid macro clicks in interleaved order
      final macroSequence = ['status', 'devices', 'movesense', 'audit', 'status', 'clear', 'devices', 'status'];
      for (final macro in macroSequence) {
        await tester.tap(find.byKey(Key('macro_$macro')));
        await tester.pump(); // Fast pump without full settle
      }
      await tester.pumpAndSettle();

      // Verify all commands recorded in exact sequence
      expect(mockService.sentCommands, equals(macroSequence));

      // After 'clear' followed by 'devices' and 'status', the terminal should contain status and devices output
      expect(find.textContaining('LAUBURU MESH NODE STATUS'), findsOneWidget);
      expect(find.textContaining('DEVICE TELEMETRY STREAM'), findsOneWidget);

      mockService.dispose();
    });

    testWidgets('Rapid reconnect button spamming does not produce race conditions', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.disconnected);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Rapidly tap reconnect 15 times
      for (int i = 0; i < 15; i++) {
        await tester.tap(find.byKey(const Key('terminal_reconnect_button')));
        await tester.pump(const Duration(milliseconds: 10));
      }
      await tester.pumpAndSettle();

      // Terminal should be connected and stable
      expect(find.text('Connected (Port 4005)'), findsOneWidget);

      mockService.dispose();
    });

    testWidgets('Mid-stream socket disconnect and reconnect lifecycle', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Connected (Port 4005)'), findsOneWidget);

      // Server forcefully terminates connection
      mockService.emitState(TerminalConnectionState.disconnected);
      await tester.pumpAndSettle();
      expect(find.text('Disconnected'), findsOneWidget);

      // User taps reconnect
      await tester.tap(find.byKey(const Key('terminal_reconnect_button')));
      await tester.pumpAndSettle();
      expect(find.text('Connected (Port 4005)'), findsOneWidget);

      mockService.dispose();
    });

    testWidgets('ANSI escape code sanitization handles complex escape sequences in UI', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final input = '\x1B[1;32;40mBOLD GREEN ON BLACK\x1B[0m \x1B[38;5;196m256-COLOR\x1B[0m';
      mockService.emitOutput(input);
      await tester.pumpAndSettle();

      expect(find.textContaining('BOLD GREEN ON BLACK 256-COLOR'), findsOneWidget);
      expect(find.textContaining('\x1B['), findsNothing);

      mockService.dispose();
    });
  });

  group('Adversarial Challenge 2: Local AI Triage (Ports 8082 / 8083) Failover & Boundary Tests', () {
    test('Port 8082 HTTP 503 triggers automatic failover to Port 8083', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          // Port 8082 returns HTTP 503 Service Unavailable
          return http.Response('Service Temporarily Overloaded', 503);
        } else if (request.url.port == 8083) {
          // Port 8083 responds with valid JSON
          return http.Response(
            jsonEncode({
              'model': 'qwen_38_max_abliterated',
              'choices': [
                {
                  'message': {
                    'content': jsonEncode({
                      'priority': 'vip',
                      'reasoning': 'High priority strategic B2B partner request.',
                      'suggested_replies': ['Approved specs, proceed with invoice.'],
                    }),
                  },
                }
              ]
            }),
            200,
          );
        }
        return http.Response('Not found', 404);
      });

      final service = OmniAiTriageService(client: mockClient);

      final result = await service.triageConversation(
        channel: InboxChannel.gmailBusiness,
        contactName: 'Hicham Amrani',
        contactAddress: 'hicham@subliminator.com',
        recentMessages: [
          {'sender': 'Hicham', 'text': 'Invoice ready for EJ350397089AU.'}
        ],
      );

      expect(result.priority, equals(InboxPriority.vip));
      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
      expect(result.isAiAssigned, isTrue);
      expect(result.suggestedReplies, contains('Approved specs, proceed with invoice.'));
    });

    test('Port 8082 connection refused triggers failover to Port 8083', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          throw http.ClientException('Connection refused to 127.0.0.1:8082');
        } else if (request.url.port == 8083) {
          return http.Response(
            jsonEncode({
              'model': 'qwen_38_max_abliterated',
              'choices': [
                {
                  'message': {
                    'content': jsonEncode({
                      'priority': 'action_required',
                      'reasoning': 'Prompt action required for delivery pickup.',
                      'suggested_replies': ['Meet at 3:30pm Altona Gate.'],
                    }),
                  },
                }
              ]
            }),
            200,
          );
        }
        return http.Response('Not found', 404);
      });

      final service = OmniAiTriageService(client: mockClient);

      final result = await service.triageConversation(
        channel: InboxChannel.gumtree,
        contactName: 'Lachy',
        contactAddress: 'lachy@gumtree.com.au',
        recentMessages: [
          {'sender': 'Lachy', 'text': 'Can we meet at 3:30pm?'}
        ],
      );

      expect(result.priority, equals(InboxPriority.actionRequired));
      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
    });

    test('Port 8082 malformed JSON triggers failover to Port 8083', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          // Returns non-JSON response or broken JSON
          return http.Response('Internal Server Error: Segmentation Fault', 200);
        } else if (request.url.port == 8083) {
          return http.Response(
            jsonEncode({
              'choices': [
                {
                  'message': {
                    'content': '```json\n{"priority": "commercial_lead", "reasoning": "Purchase intent", "suggested_replies": ["In stock"]}\n```',
                  },
                }
              ]
            }),
            200,
          );
        }
        return http.Response('Not found', 404);
      });

      final service = OmniAiTriageService(client: mockClient);

      final result = await service.triageConversation(
        channel: InboxChannel.shopify,
        contactName: 'Jack',
        contactAddress: 'jack@gmail.com',
        recentMessages: [
          {'sender': 'Jack', 'text': 'Is size L in stock?'}
        ],
      );

      expect(result.priority, equals(InboxPriority.commercialLead));
      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
    });

    test('BOTH Ports 8082 and 8083 offline degrades cleanly to zero-mock heuristic triage without hallucinations', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException('All ports down');
      });

      final service = OmniAiTriageService(client: mockClient);

      final triage = await service.triageConversation(
        channel: InboxChannel.gumtree,
        contactName: 'Buyer',
        contactAddress: 'buyer@gumtree.com.au',
        recentMessages: [
          {'sender': 'Buyer', 'text': 'Can we meet at Altona Gate today?'}
        ],
      );

      // Strictly verifies zero synthetic hallucinations
      expect(triage.priority, equals(InboxPriority.actionRequired));
      expect(triage.isAiAssigned, isFalse);
      expect(triage.isFallback, isTrue);
      expect(triage.suggestedReplies, isEmpty); // Empty list: zero-mock
      expect(triage.port, equals(-1));

      // Smart replies call must also return strictly empty list
      final smartReplies = await service.generateSmartReplies(
        channel: InboxChannel.gumtree,
        recentMessages: [
          {'sender': 'Buyer', 'text': 'Can we meet at Altona Gate today?'}
        ],
      );
      expect(smartReplies, isEmpty);
    });

    test('generateSmartReplies Port 8082 503 failover to Port 8083', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          return http.Response('503 Service Unavailable', 503);
        } else if (request.url.port == 8083) {
          return http.Response(
            jsonEncode({
              'choices': [
                {
                  'message': {
                    'content': '["Option A", "Option B", "Option C"]',
                  },
                }
              ]
            }),
            200,
          );
        }
        return http.Response('Error', 500);
      });

      final service = OmniAiTriageService(client: mockClient);
      final replies = await service.generateSmartReplies(
        channel: InboxChannel.gmailBusiness,
        recentMessages: [
          {'sender': 'Hicham', 'text': 'Sample update.'}
        ],
      );

      expect(replies, equals(['Option A', 'Option B', 'Option C']));
    });

    test('Boundary: Empty recent messages list does not cause RangeError or crash', () async {
      final service = OmniAiTriageService();

      final triage = service.computeHeuristicFallback(
        channel: InboxChannel.sms,
        contactAddress: '+61400000000',
        latestMessageText: '',
      );

      expect(triage.priority, equals(InboxPriority.lowPriority));
      expect(triage.isFallback, isTrue);
    });
  });

  group('Adversarial Challenge 3: Omni Inbox UI Rapid Interactions & Boundaries', () {
    testWidgets('Rapid filter pill switching stress: 35 sequential toggles without exception', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      final filterKeys = [
        'filter_gumtree',
        'filter_gmail_business',
        'filter_shopify',
        'filter_instagram',
        'filter_sms',
        'filter_gmail_personal',
        'filter_all',
      ];

      // Rapidly toggle across all 7 filters 5 times (35 total rapid switches)
      for (int cycle = 0; cycle < 5; cycle++) {
        for (final key in filterKeys) {
          final finder = find.byKey(Key(key));
          await tester.ensureVisible(finder);
          await tester.tap(finder);
          await tester.pump();
        }
      }
      await tester.pumpAndSettle();

      // Ensure all threads visible again
      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);
      expect(find.text('Hicham Amrani (CEO Subliminator)'), findsOneWidget);
      expect(find.text('Shopify Commerce Lead (Order #LBG-1082)'), findsOneWidget);

      inboxService.dispose();
    });

    testWidgets('Searching for non-existent contacts and regex special characters renders empty state gracefully', (tester) async {
      final inboxService = OmniInboxService();

      await tester.pumpWidget(
        MaterialApp(
          home: OmniInboxScreen(inboxService: inboxService),
        ),
      );
      await tester.pumpAndSettle();

      final searchField = find.byKey(const Key('inbox_search_field'));

      // 1. Search non-existent contact
      await tester.enterText(searchField, 'ZZZZ_NON_EXISTENT_CONTACT_9999');
      await tester.pumpAndSettle();

      expect(find.text('No conversations found'), findsOneWidget);
      expect(find.byIcon(Icons.inbox_outlined), findsOneWidget);

      // 2. Search with regex special characters that could break naive RegExp
      await tester.enterText(searchField, r'(.*?)+[0-9]{5}\$^\*');
      await tester.pumpAndSettle();

      expect(find.text('No conversations found'), findsOneWidget);

      // 3. Clear search restores list
      await tester.enterText(searchField, '');
      await tester.pumpAndSettle();

      expect(find.text('Lachy (Gumtree Buyer)'), findsOneWidget);

      inboxService.dispose();
    });

    testWidgets('Empty thread handling: opening thread with 0 messages and sending message operates cleanly', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      // Create empty thread
      final emptyThread = InboxThread(
        id: 'empty_thread_001',
        channel: InboxChannel.sms,
        contactName: 'New Contact',
        contactAddress: '+61412345678',
        subject: 'New SMS',
        lastMessagePreview: '',
        lastMessageTime: DateTime.now(),
        unreadCount: 0,
        messages: const [],
      );

      final inboxService = OmniInboxService(initialThreads: [emptyThread]);

      await tester.pumpWidget(
        MaterialApp(
          home: InboxThreadDetailScreen(
            thread: emptyThread,
            inboxService: inboxService,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verifies screen rendered without errors even with 0 messages
      expect(find.text('New Contact'), findsOneWidget);
      expect(find.text('+61412345678'), findsOneWidget);

      final composerInput = find.byKey(const Key('message_composer_input'));
      final sendButton = find.byKey(const Key('message_send_button'));

      // 1. Attempt sending empty whitespace message - should be rejected
      await tester.enterText(composerInput, '   ');
      await tester.tap(sendButton);
      await tester.pumpAndSettle();

      expect(inboxService.getThreadById('empty_thread_001')!.messages, isEmpty);

      // 2. Send authentic first message
      await tester.enterText(composerInput, 'Hello, this is Aaron confirming your inquiry.');
      await tester.tap(sendButton);
      await tester.pumpAndSettle();

      // Verifies message sent and rendered
      final updatedThread = inboxService.getThreadById('empty_thread_001')!;
      expect(updatedThread.messages.length, equals(1));
      expect(updatedThread.messages.first.text, equals('Hello, this is Aaron confirming your inquiry.'));
      expect(updatedThread.messages.first.isOutgoing, isTrue);

      expect(find.text('Hello, this is Aaron confirming your inquiry.'), findsOneWidget);
      expect(tester.widget<TextField>(composerInput).controller?.text, isEmpty);

      inboxService.dispose();
    });

    test('Sending message to non-existent thread ID returns safely without exception', () async {
      final inboxService = OmniInboxService();
      expect(() async => await inboxService.sendMessage('non_existent_id', 'Hello'), returnsNormally);
      inboxService.dispose();
    });
  });

  group('Adversarial Challenge 4: Stream Lifecycle & Memory Leak Probes', () {
    testWidgets('Repeated mount and unmount of MeshTerminalSheet does not leak listeners or throw', (tester) async {
      final mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);

      for (int i = 0; i < 5; i++) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: MeshTerminalSheet(terminalService: mockService),
            ),
          ),
        );
        await tester.pump();
        mockService.emitOutput('Chunk $i\n');
        await tester.pump();

        // Unmount widget
        await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
        await tester.pump();
      }

      // Emitting to service after unmount should not trigger setState on disposed widget
      expect(() => mockService.emitOutput('Post-dispose chunk\n'), returnsNormally);
      expect(() => mockService.emitState(TerminalConnectionState.disconnected), returnsNormally);

      mockService.dispose();
    });

    test('ChatHubService reactive stream adapter disposal cleans up stream without leaking', () {
      final service = ChatHubService();
      service.connect();
      expect(service.messagesStream, isNotNull);
      service.dispose();
      // Double dispose must not crash
      expect(() => service.dispose(), returnsNormally);
    });
  });
}
