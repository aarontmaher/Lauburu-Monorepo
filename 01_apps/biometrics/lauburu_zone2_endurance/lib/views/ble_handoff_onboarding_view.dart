import 'package:flutter/material.dart';
import '../services/compute_hub_connection_service.dart';

// Assuming Modern Dark Glassmorphism design tokens are in a theme file.
// If they don't exist, these are placeholder implementations to satisfy the UI requirement.

class GlassCard extends StatelessWidget {
  final Widget child;
  const GlassCard({Key? key, required this.child}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.2)),
      ),
      padding: const EdgeInsets.all(24),
      child: child,
    );
  }
}

class AnimatedButton extends StatelessWidget {
  final VoidCallback onPressed;
  final String text;
  final bool isLoading;

  const AnimatedButton({
    Key? key,
    required this.onPressed,
    required this.text,
    this.isLoading = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: Colors.blueAccent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 32),
      ),
      onPressed: isLoading ? null : onPressed,
      child: isLoading 
        ? const SizedBox(
            height: 20, 
            width: 20, 
            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
          )
        : Text(text, style: const TextStyle(fontSize: 16, color: Colors.white)),
    );
  }
}

class AppTheme {
  static const Color backgroundDark = Color(0xFF121212);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Colors.white70;
}

class BleHandoffOnboardingView extends StatefulWidget {
  final ComputeHubConnectionService hubService;

  const BleHandoffOnboardingView({Key? key, required this.hubService}) : super(key: key);

  @override
  State<BleHandoffOnboardingView> createState() => _BleHandoffOnboardingViewState();
}

class _BleHandoffOnboardingViewState extends State<BleHandoffOnboardingView> {
  HubConnectionState _connectionState = HubConnectionState.disconnected;

  @override
  void initState() {
    super.initState();
    _connectionState = widget.hubService.currentState;
    widget.hubService.connectionState.listen((state) {
      if (mounted) {
        setState(() {
          _connectionState = state;
        });
      }
    });
  }

  void _handleConnect() {
    widget.hubService.connectToHub();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundDark,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.hub_outlined,
                  size: 80,
                  color: Colors.blueAccent,
                ),
                const SizedBox(height: 32),
                const Text(
                  'Connect to Compute Hub',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                const Text(
                  'For Modular Feature Independence, Lauburu Zone 2 Endurance routes all BLE telemetry through the central Compute Hub. Connect now to sync heart rate data.',
                  style: TextStyle(
                    fontSize: 16,
                    color: AppTheme.textSecondary,
                    height: 1.5,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 48),
                GlassCard(
                  child: Column(
                    children: [
                      _buildStatusIndicator(),
                      const SizedBox(height: 24),
                      AnimatedButton(
                        text: _connectionState == HubConnectionState.connected 
                            ? 'Connected' 
                            : 'Initialize Connection',
                        isLoading: _connectionState == HubConnectionState.connecting,
                        onPressed: _connectionState == HubConnectionState.connected
                            ? () {} // Move to next onboarding step
                            : _handleConnect,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIndicator() {
    IconData icon;
    Color color;
    String text;

    switch (_connectionState) {
      case HubConnectionState.connected:
        icon = Icons.check_circle;
        color = Colors.greenAccent;
        text = 'Compute Hub Connected';
        break;
      case HubConnectionState.connecting:
        icon = Icons.sync;
        color = Colors.orangeAccent;
        text = 'Establishing Handshake...';
        break;
      case HubConnectionState.error:
        icon = Icons.error_outline;
        color = Colors.redAccent;
        text = 'Connection Failed';
        break;
      case HubConnectionState.disconnected:
      default:
        icon = Icons.sensors_off;
        color = Colors.white54;
        text = 'Hub Disconnected';
        break;
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(width: 12),
        Text(
          text,
          style: TextStyle(
            color: color,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
