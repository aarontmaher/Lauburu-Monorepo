import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lauburu_life_companion/screens/ecommerce_hub_screen.dart';
import 'package:lauburu_life_companion/services/mesh_terminal_service.dart';
import 'package:lauburu_life_companion/widgets/mesh_terminal_sheet.dart';
import 'helpers/mock_mesh_terminal_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Milestone M7: Commerce Hub Bluetooth Serial Terminal Integration Tests', () {
    late MockMeshTerminalService mockService;

    setUp(() {
      mockService = MockMeshTerminalService(initialState: TerminalConnectionState.connected);
    });

    tearDown(() {
      mockService.dispose();
    });

    testWidgets('EcommerceHubScreen AppBar terminal button opens MeshTerminalSheet', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(terminalService: mockService),
        ),
      );
      await tester.pumpAndSettle();

      final terminalButton = find.byKey(const Key('open_mesh_terminal_button'));
      expect(terminalButton, findsOneWidget);

      await tester.tap(terminalButton);
      await tester.pumpAndSettle();

      expect(find.byType(MeshTerminalSheet), findsOneWidget);
      expect(find.text('Mesh Bluetooth Serial Terminal'), findsOneWidget);
    });

    testWidgets('EcommerceHubScreen terminal FAB opens MeshTerminalSheet', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(terminalService: mockService),
        ),
      );
      await tester.pumpAndSettle();

      final terminalFab = find.byKey(const Key('terminal_fab'));
      expect(terminalFab, findsOneWidget);

      await tester.tap(terminalFab);
      await tester.pumpAndSettle();

      expect(find.byType(MeshTerminalSheet), findsOneWidget);
    });

    testWidgets('MeshTerminalSheet renders header, buttons, and status badge', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Mesh Bluetooth Serial Terminal'), findsOneWidget);
      expect(find.byKey(const Key('terminal_status_badge')), findsOneWidget);
      expect(find.text('Connected (Port 4005)'), findsOneWidget);
      expect(find.byKey(const Key('terminal_reconnect_button')), findsOneWidget);
      expect(find.byKey(const Key('terminal_close_button')), findsOneWidget);
    });

    testWidgets('MeshTerminalSheet renders all 5 quick-action macro chips with keys', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('macro_status')), findsOneWidget);
      expect(find.byKey(const Key('macro_audit')), findsOneWidget);
      expect(find.byKey(const Key('macro_devices')), findsOneWidget);
      expect(find.byKey(const Key('macro_movesense')), findsOneWidget);
      expect(find.byKey(const Key('macro_clear')), findsOneWidget);

      expect(find.text('[status]'), findsOneWidget);
      expect(find.text('[audit]'), findsOneWidget);
      expect(find.text('[devices]'), findsOneWidget);
      expect(find.text('[movesense]'), findsOneWidget);
      expect(find.text('[clear]'), findsOneWidget);
    });

    testWidgets('Tapping macro chips sends expected commands and renders terminal responses', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 1. Tap [status]
      await tester.tap(find.byKey(const Key('macro_status')));
      await tester.pumpAndSettle();
      expect(mockService.sentCommands, contains('status'));
      expect(find.textContaining('LAUBURU MESH NODE STATUS'), findsOneWidget);
      expect(find.textContaining('Mac Mini M4 Pro'), findsOneWidget);

      // 2. Tap [devices]
      await tester.tap(find.byKey(const Key('macro_devices')));
      await tester.pumpAndSettle();
      expect(mockService.sentCommands, contains('devices'));
      expect(find.textContaining('DEVICE TELEMETRY STREAM'), findsOneWidget);
      expect(find.textContaining('RAM: 24.0 GB'), findsOneWidget);

      // 3. Tap [movesense]
      await tester.tap(find.byKey(const Key('macro_movesense')));
      await tester.pumpAndSettle();
      expect(mockService.sentCommands, contains('movesense'));
      expect(find.textContaining('Movesense 261030002013'), findsOneWidget);

      // 4. Tap [audit]
      await tester.tap(find.byKey(const Key('macro_audit')));
      await tester.pumpAndSettle();
      expect(mockService.sentCommands, contains('audit'));
      expect(find.textContaining('MASTER APP AUDITOR REPORT'), findsOneWidget);

      // 5. Tap [clear] -> clears output buffer
      await tester.tap(find.byKey(const Key('macro_clear')));
      await tester.pumpAndSettle();
      expect(mockService.sentCommands, contains('clear'));
      expect(find.textContaining('LAUBURU MESH NODE STATUS'), findsNothing);
    });

    testWidgets('Command input field sends command via send button and clears input', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final inputField = find.byKey(const Key('terminal_input_field'));
      expect(inputField, findsOneWidget);

      await tester.enterText(inputField, 'uname -a');
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('terminal_send_button')));
      await tester.pumpAndSettle();

      expect(mockService.sentCommands, contains('uname -a'));
      expect(find.textContaining('uname -a: executed'), findsOneWidget);
      expect(tester.widget<TextField>(inputField).controller?.text, isEmpty);
    });

    testWidgets('Command input field sends command on keyboard submit', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final inputField = find.byKey(const Key('terminal_input_field'));
      await tester.enterText(inputField, 'uptime');
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(mockService.sentCommands, contains('uptime'));
      expect(find.textContaining('uptime: executed'), findsOneWidget);
    });

    testWidgets('ANSI escape codes are sanitized from terminal output', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Emit raw ANSI escape chunk
      mockService.emitOutput('\x1B[1;32mGREEN TEXT\x1B[0m and \x1B[31mRED TEXT\x1B[0m\n');
      await tester.pumpAndSettle();

      // The text is rendered without escape characters
      expect(find.textContaining('GREEN TEXT and RED TEXT'), findsOneWidget);
      expect(find.textContaining('\x1B[1;32m'), findsNothing);
    });

    testWidgets('Connection state transitions update status badge', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Initial state: connected
      expect(find.text('Connected (Port 4005)'), findsOneWidget);

      // Transition to connecting
      mockService.emitState(TerminalConnectionState.connecting);
      await tester.pumpAndSettle();
      expect(find.text('Connecting...'), findsOneWidget);

      // Transition to error
      mockService.emitState(TerminalConnectionState.error, error: 'Connection refused');
      await tester.pumpAndSettle();
      expect(find.text('Connection Error'), findsOneWidget);

      // Transition to disconnected
      mockService.emitState(TerminalConnectionState.disconnected);
      await tester.pumpAndSettle();
      expect(find.text('Disconnected'), findsOneWidget);
    });

    testWidgets('Tapping reconnect button triggers connect() on terminal service', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MeshTerminalSheet(terminalService: mockService),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Disconnect service
      mockService.emitState(TerminalConnectionState.disconnected);
      await tester.pumpAndSettle();
      expect(find.text('Disconnected'), findsOneWidget);

      // Tap reconnect button
      await tester.tap(find.byKey(const Key('terminal_reconnect_button')));
      await tester.pumpAndSettle();

      expect(find.text('Connected (Port 4005)'), findsOneWidget);
    });

    testWidgets('Close button dismisses the modal bottom sheet', (tester) async {
      tester.view.physicalSize = const Size(1200, 1800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: EcommerceHubScreen(terminalService: mockService),
        ),
      );
      await tester.pumpAndSettle();

      // Open sheet
      await tester.tap(find.byKey(const Key('open_mesh_terminal_button')));
      await tester.pumpAndSettle();
      expect(find.byType(MeshTerminalSheet), findsOneWidget);

      // Tap close button
      await tester.tap(find.byKey(const Key('terminal_close_button')));
      await tester.pumpAndSettle();

      // Sheet dismissed
      expect(find.byType(MeshTerminalSheet), findsNothing);
    });

    test('MeshTerminalService host auto-detection and defaults', () {
      expect(MeshTerminalService.defaultHost, isNotEmpty);
      final service = MeshTerminalService();
      expect(service.defaultPort, equals(4005));
      expect(service.state, equals(TerminalConnectionState.disconnected));
      expect(service.lastError, isNull);
    });
  });
}
