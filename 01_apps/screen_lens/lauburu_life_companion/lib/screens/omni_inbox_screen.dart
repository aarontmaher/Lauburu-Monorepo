import 'package:flutter/material.dart';
import '../models/customer_profile.dart';
import '../models/inbox_models.dart';
import '../services/chat_hub_service.dart';
import '../services/omni_ai_triage_service.dart';
import '../services/omni_inbox_service.dart';
import '../services/shopify_auth_service.dart';
import 'ecommerce_hub_screen.dart';
import 'inbox_thread_detail_screen.dart';
import 'shopify_login_dialog.dart';

class OmniInboxScreen extends StatefulWidget {
  final ShopifyAuthService? authService;
  final OmniInboxService? inboxService;
  final OmniAiTriageService? triageService;
  final ChatHubService? legacyChatService;

  const OmniInboxScreen({
    super.key,
    this.authService,
    this.inboxService,
    this.triageService,
    this.legacyChatService,
  });

  @override
  State<OmniInboxScreen> createState() => _OmniInboxScreenState();
}

class _OmniInboxScreenState extends State<OmniInboxScreen> {
  late final ShopifyAuthService _authService;
  late final OmniInboxService _inboxService;
  OmniAiTriageService? _triageService;

  InboxChannel _selectedFilter = InboxChannel.all;
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _authService = widget.authService ?? ShopifyAuthService();
    _authService.addListener(_onAuthStateChanged);
    _authService.restoreSession();

    _triageService = widget.triageService;
    _inboxService = widget.inboxService ??
        OmniInboxService(triageService: _triageService);
  }

  void _onAuthStateChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _authService.removeListener(_onAuthStateChanged);
    _searchController.dispose();
    super.dispose();
  }

  void _openLoginDialog() async {
    final messenger = ScaffoldMessenger.of(context);
    final session = await ShopifyLoginDialog.show(context, _authService);
    if (session != null && mounted) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(
              'Welcome, ${session.profile.fullName}! (${session.profile.tier.badgeText} tier)'),
          backgroundColor: Colors.green.shade800,
        ),
      );
    }
  }

  void _showProfileModal() {
    final session = _authService.currentSession;
    if (session == null) return;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: _getTierColor(session.profile.tier),
                    child: Text(
                      session.profile.firstName?.isNotEmpty == true
                          ? session.profile.firstName![0].toUpperCase()
                          : session.profile.email[0].toUpperCase(),
                      style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Colors.white),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          session.profile.fullName,
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          session.profile.email,
                          key: const Key('profile_email'),
                          style:
                              const TextStyle(color: Colors.grey, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                  _buildTierBadge(session.profile.tier,
                      keyPrefix: 'profile_modal'),
                ],
              ),
              const SizedBox(height: 20),
              const Divider(),
              const SizedBox(height: 12),
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.verified_user_outlined,
                    color: Colors.blueAccent),
                title: const Text('Shopify Customer ID'),
                subtitle: Text(session.profile.id.isNotEmpty
                    ? session.profile.id
                    : 'Offline Verified'),
              ),
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.sync, color: Colors.greenAccent),
                title: const Text('Cloud Sync Status'),
                subtitle: Text(
                    'Synced: ${session.lastSyncedAt.toLocal().toString().split('.').first}'),
                trailing: TextButton(
                  onPressed: () async {
                    final messenger = ScaffoldMessenger.of(context);
                    Navigator.of(context).pop();
                    await _authService.refreshSession();
                    messenger.showSnackBar(
                      const SnackBar(
                          content: Text('Synced with Shopify Cloud!')),
                    );
                  },
                  child: const Text('Sync Now'),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                key: const Key('logout_button'),
                onPressed: () async {
                  final messenger = ScaffoldMessenger.of(context);
                  Navigator.of(context).pop();
                  await _authService.logout();
                  messenger.showSnackBar(
                    const SnackBar(content: Text('Logged out successfully')),
                  );
                },
                icon: const Icon(Icons.logout, color: Colors.white),
                label: const Text('Log Out',
                    style: TextStyle(color: Colors.white)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.redAccent.shade700,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Color _getTierColor(CustomerTier tier) {
    switch (tier) {
      case CustomerTier.elite:
        return Colors.purple.shade600;
      case CustomerTier.pro:
        return Colors.amber.shade800;
      case CustomerTier.free:
        return Colors.blueGrey;
    }
  }

  Widget _buildTierBadge(CustomerTier tier, {String keyPrefix = 'appbar'}) {
    final color = _getTierColor(tier);
    return Container(
      key: Key('${keyPrefix}_tier_badge'),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withAlpha(50),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color, width: 1.2),
      ),
      child: Text(
        tier.badgeText,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 12,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _buildFilterPills() {
    final filters = [
      (InboxChannel.all, 'All', 'filter_all'),
      (InboxChannel.gmailPersonal, 'Gmail: Personal', 'filter_gmail_personal'),
      (InboxChannel.gmailBusiness, 'Gmail: Lauburu', 'filter_gmail_business'),
      (InboxChannel.instagram, 'Instagram', 'filter_instagram'),
      (InboxChannel.sms, 'SMS', 'filter_sms'),
      (InboxChannel.shopify, 'Shopify', 'filter_shopify'),
      (InboxChannel.gumtree, 'Gumtree', 'filter_gumtree'),
    ];

    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(
          children: [
            for (int i = 0; i < filters.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              FilterChip(
                key: Key(filters[i].$3),
                label: Text(filters[i].$2),
                selected: _selectedFilter == filters[i].$1,
                selectedColor: Colors.blueAccent.withAlpha(80),
                checkmarkColor: Colors.white,
                labelStyle: TextStyle(
                  fontSize: 12,
                  fontWeight: _selectedFilter == filters[i].$1
                      ? FontWeight.bold
                      : FontWeight.normal,
                  color: _selectedFilter == filters[i].$1
                      ? Colors.white
                      : Colors.grey.shade300,
                ),
                onSelected: (selected) {
                  setState(() {
                    _selectedFilter = selected ? filters[i].$1 : InboxChannel.all;
                  });
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChannelBadge(InboxChannel channel) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: channel.badgeColor.withAlpha(40),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: channel.badgeColor, width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(channel.icon, size: 10, color: channel.badgeColor),
          const SizedBox(width: 4),
          Text(
            channel.displayName,
            style: TextStyle(
              color: channel.badgeColor,
              fontWeight: FontWeight.bold,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPriorityBadge(InboxPriority priority) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: priority.color.withAlpha(40),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: priority.color, width: 0.8),
      ),
      child: Text(
        priority.displayName,
        style: TextStyle(
          color: priority.color,
          fontWeight: FontWeight.bold,
          fontSize: 10,
        ),
      ),
    );
  }

  List<InboxThread> _filterThreads(List<InboxThread> allThreads) {
    return allThreads.where((t) {
      if (_selectedFilter != InboxChannel.all && t.channel != _selectedFilter) {
        return false;
      }
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final matchesName = t.contactName.toLowerCase().contains(query);
        final matchesSubject = t.subject.toLowerCase().contains(query);
        final matchesPreview =
            t.lastMessagePreview.toLowerCase().contains(query);
        return matchesName || matchesSubject || matchesPreview;
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final isAuthenticated = _authService.isAuthenticated;
    final currentTier = _authService.currentTier;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Omni Inbox'),
        actions: [
          // Member Tier Badge
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4.0),
              child: _buildTierBadge(currentTier),
            ),
          ),
          // Login / Profile Action
          if (!isAuthenticated)
            TextButton.icon(
              key: const Key('login_action_button'),
              onPressed: _openLoginDialog,
              icon: const Icon(Icons.login, size: 18),
              label: const Text('Login'),
            )
          else
            IconButton(
              key: const Key('profile_action_button'),
              tooltip: 'Account Profile',
              onPressed: _showProfileModal,
              icon: CircleAvatar(
                radius: 14,
                backgroundColor: _getTierColor(currentTier),
                child: Text(
                  _authService.currentSession?.profile.firstName?.isNotEmpty ==
                          true
                      ? _authService
                          .currentSession!.profile.firstName![0]
                          .toUpperCase()
                      : 'U',
                  style: const TextStyle(
                      fontSize: 12,
                      color: Colors.white,
                      fontWeight: FontWeight.bold),
                ),
              ),
            ),
          // E-Commerce Hub Navigation Action
          IconButton(
            key: const Key('ecommerce_hub_button'),
            tooltip: 'E-Commerce Hub',
            icon: const Icon(Icons.storefront_outlined),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) =>
                      EcommerceHubScreen(authService: _authService),
                ),
              );
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: TextField(
              key: const Key('inbox_search_field'),
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search contacts, messages...',
                hintStyle: const TextStyle(color: Colors.grey, fontSize: 13),
                prefixIcon: const Icon(Icons.search, size: 20, color: Colors.grey),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18, color: Colors.grey),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                filled: true,
                fillColor: Colors.grey.shade900,
                contentPadding: const EdgeInsets.symmetric(vertical: 0),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (val) {
                setState(() {
                  _searchQuery = val.trim();
                });
              },
            ),
          ),

          // Horizontal Filter Chips Bar
          _buildFilterPills(),

          const Divider(height: 1),

          // Thread List (StreamBuilder)
          Expanded(
            child: StreamBuilder<List<InboxThread>>(
              stream: _inboxService.threadsStream,
              initialData: _inboxService.currentThreads,
              builder: (context, snapshot) {
                final allThreads = snapshot.data ?? [];
                final threads = _filterThreads(allThreads);

                if (threads.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(Icons.inbox_outlined, size: 48, color: Colors.grey),
                        SizedBox(height: 12),
                        Text(
                          'No conversations found',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.separated(
                  itemCount: threads.length,
                  separatorBuilder: (context, index) =>
                      Divider(height: 1, color: Colors.grey.shade800),
                  itemBuilder: (context, index) {
                    final thread = threads[index];
                    final timeStr =
                        '${thread.lastMessageTime.hour.toString().padLeft(2, '0')}:${thread.lastMessageTime.minute.toString().padLeft(2, '0')}';

                    return ListTile(
                      key: Key('thread_tile_${thread.id}'),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 4),
                      leading: Stack(
                        clipBehavior: Clip.none,
                        children: [
                          CircleAvatar(
                            radius: 22,
                            backgroundColor: thread.channel.badgeColor,
                            child: Text(
                              thread.contactName.isNotEmpty
                                  ? thread.contactName[0].toUpperCase()
                                  : 'U',
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                  fontSize: 16),
                            ),
                          ),
                          Positioned(
                            bottom: -2,
                            right: -2,
                            child: Container(
                              padding: const EdgeInsets.all(2),
                              decoration: const BoxDecoration(
                                color: Colors.black,
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                thread.channel.icon,
                                size: 12,
                                color: thread.channel.badgeColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      title: Row(
                        children: [
                          Expanded(
                            child: Text(
                              thread.contactName,
                              style: TextStyle(
                                fontWeight: thread.unreadCount > 0
                                    ? FontWeight.bold
                                    : FontWeight.w600,
                                fontSize: 14,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            timeStr,
                            style: TextStyle(
                              fontSize: 11,
                              color: thread.unreadCount > 0
                                  ? Colors.blueAccent
                                  : Colors.grey,
                            ),
                          ),
                        ],
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 2),
                          Text(
                            thread.lastMessagePreview,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13,
                              color: thread.unreadCount > 0
                                  ? Colors.white
                                  : Colors.grey.shade400,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              _buildChannelBadge(thread.channel),
                              const SizedBox(width: 6),
                              _buildPriorityBadge(thread.priority),
                              const Spacer(),
                              if (thread.unreadCount > 0)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.blueAccent,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${thread.unreadCount}',
                                    style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold),
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (context) => InboxThreadDetailScreen(
                              thread: thread,
                              inboxService: _inboxService,
                              triageService: _triageService,
                            ),
                          ),
                        );
                      },
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
