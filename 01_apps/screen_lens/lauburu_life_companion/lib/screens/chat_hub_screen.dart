import 'package:flutter/material.dart';
import '../services/chat_hub_service.dart';
import '../services/omni_inbox_service.dart';
import '../services/shopify_auth_service.dart';
import 'omni_inbox_screen.dart';

export 'omni_inbox_screen.dart';

/// Backward-compatible wrapper for ChatHubScreen.
/// Preserves constructor arguments, AppBar action keys, and profile modal keys
/// while rendering the modern OmniInboxScreen.
class ChatHubScreen extends StatelessWidget {
  final ShopifyAuthService? authService;
  final ChatHubService? chatHubService;
  final OmniInboxService? omniInboxService;

  const ChatHubScreen({
    super.key,
    this.authService,
    this.chatHubService,
    this.omniInboxService,
  });

  @override
  Widget build(BuildContext context) {
    return OmniInboxScreen(
      authService: authService,
      inboxService: omniInboxService,
      legacyChatService: chatHubService,
    );
  }
}
