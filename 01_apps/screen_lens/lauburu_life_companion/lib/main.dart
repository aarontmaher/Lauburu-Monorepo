import 'package:flutter/material.dart';
import 'screens/ecommerce_hub_screen.dart';
import 'screens/omni_inbox_screen.dart';
import 'screens/timeline_screen.dart';
import 'services/mesh_audio_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Launch UI immediately so window renders instantly
  runApp(const LauburuLifeCompanionApp());

  // Non-blocking initialization of ambient mesh audio service
  try {
    final meshAudio = MeshAudioService();
    await meshAudio.initialize();
    meshAudio.startMonitoring();
  } catch (e) {
    debugPrint('MeshAudioService init non-fatal error: $e');
  }
}

class LauburuLifeCompanionApp extends StatelessWidget {
  const LauburuLifeCompanionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Life Companion Lauburu',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;
  
  final List<Widget> _screens = [
    const OmniInboxScreen(),
    const EcommerceHubScreen(),
    const TimelineScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.chat),
            label: 'Hub',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.shopping_cart),
            label: 'E-Commerce',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history),
            label: 'Timeline',
          ),
        ],
      ),
    );
  }
}
