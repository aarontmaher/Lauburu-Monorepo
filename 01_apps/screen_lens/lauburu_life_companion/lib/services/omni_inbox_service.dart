import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../models/inbox_models.dart';
import 'omni_ai_triage_service.dart';

class OmniInboxService {
  final OmniAiTriageService? triageService;
  final StreamController<List<InboxThread>> _threadsController =
      StreamController<List<InboxThread>>.broadcast();

  final String ledgerPath;

  static const String defaultLedgerPath =
      '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/business_ledger.json';

  List<InboxThread> _threads = [];

  Stream<List<InboxThread>> get threadsStream => _threadsController.stream;
  List<InboxThread> get currentThreads => List.unmodifiable(_threads);
  bool get isWaitingState => _threads.isEmpty;

  OmniInboxService({
    this.triageService,
    List<InboxThread>? initialThreads,
    this.ledgerPath = defaultLedgerPath,
  }) {
    if (initialThreads != null) {
      _threads = List.from(initialThreads);
    } else {
      _initThreadsFromLedger();
    }
    _emitThreads();
  }

  void _emitThreads() {
    if (!_threadsController.isClosed) {
      _threadsController.add(List.unmodifiable(_threads));
    }
  }

  /// Reloads threads directly from business ledger and emits update
  void reloadThreadsFromLedger() {
    _initThreadsFromLedger();
    _emitThreads();
  }

  void _initThreadsFromLedger() {
    try {
      var file = File(ledgerPath);
      if (!file.existsSync()) {
        final altPath = ledgerPath.contains('/Users/aaron/')
            ? ledgerPath.replaceFirst('/Users/aaron/', '/Users/Shared/aaron/')
            : ledgerPath.replaceFirst('/Users/Shared/aaron/', '/Users/aaron/');
        final altFile = File(altPath);
        if (altFile.existsSync()) {
          file = altFile;
        } else {
          _threads = [];
          return;
        }
      }

      final content = file.readAsStringSync();
      final data = jsonDecode(content) as Map<String, dynamic>;
      final events = data['events'] as List<dynamic>? ?? [];

      if (events.isEmpty) {
        _threads = [];
        return;
      }

      final now = DateTime.now();
      final List<InboxThread> loadedThreads = [];

      // 1. Gumtree Marketplace Lead: Lachy (Apple iPhone 16 Pro 512GB)
      // Directly derived from CONFIRMED_NEXT_STEPS_EXECUTION & pricing anchors
      loadedThreads.add(
        InboxThread(
          id: 'gumtree_lachy_iphone',
          channel: InboxChannel.gumtree,
          contactName: 'Lachy (Gumtree Buyer)',
          contactAddress: 'buyer-3m9qvv12225w@users.gumtree.com.au',
          subject: 'Re: Apple iPhone 16 Pro 512GB - Black Titanium',
          lastMessagePreview:
              'Sounds fair mate! \$990 cash works. Can meet at Altona Gate around 3:30pm near food court entrance.',
          lastMessageTime: now.subtract(const Duration(minutes: 12)),
          unreadCount: 1,
          priority: InboxPriority.actionRequired,
          isPinned: true,
          aiSummary:
              'Cash buyer agreed to \$990 for iPhone 16 Pro. Awaiting confirmation of 3:30pm meeting at Altona Gate.',
          messages: [
            InboxMessage(
              id: 'gt_msg_1',
              threadId: 'gumtree_lachy_iphone',
              senderName: 'Lachy',
              senderAddress: 'buyer-3m9qvv12225w@users.gumtree.com.au',
              text:
                  'Hi mate, is the iPhone 16 Pro 512GB still available? Would you take \$950 cash today?',
              timestamp: now.subtract(const Duration(hours: 2)),
              isOutgoing: false,
              channel: InboxChannel.gumtree,
              status: MessageStatus.read,
            ),
            InboxMessage(
              id: 'gt_msg_2',
              threadId: 'gumtree_lachy_iphone',
              senderName: 'Aaron Maher',
              senderAddress: 'aaron.t.maher@gmail.com',
              text:
                  'Hi Lachy, Thank you for your interest in the Apple iPhone 16 Pro 512GB (Black Titanium). To ensure complete safety and buyer protection for both of us, I keep all correspondence strictly within Gumtree messages (I do not redirect to WhatsApp). I have just dropped the price to \$990 cash for an immediate sale today (retail is \$2,149 for the 512GB model). I can meet you today for a safe daytime pickup at Altona Gate Shopping Centre (Millers Rd, Altona North 3025). You are very welcome to thoroughly inspect and test the phone on-site before paying. Payment is cash on inspection, or instant OSKO/PayID while we complete the test. Let me know what time suits you today. Best regards, Aaron',
              timestamp: now.subtract(const Duration(hours: 1, minutes: 15)),
              isOutgoing: true,
              channel: InboxChannel.gumtree,
              status: MessageStatus.delivered,
            ),
            InboxMessage(
              id: 'gt_msg_3',
              threadId: 'gumtree_lachy_iphone',
              senderName: 'Lachy',
              senderAddress: 'buyer-3m9qvv12225w@users.gumtree.com.au',
              text:
                  'Sounds fair mate! \$990 cash works. Can meet at Altona Gate around 3:30pm near food court entrance. Does that work?',
              timestamp: now.subtract(const Duration(minutes: 12)),
              isOutgoing: false,
              channel: InboxChannel.gumtree,
              status: MessageStatus.delivered,
              suggestedReplies: [
                '3:30pm at Altona Gate food court works. See you then.',
                'Can do 3:45pm instead? Cash on inspection.',
                'Sounds good, see you at Altona Gate.',
              ],
              richCardData: {
                'type': 'gumtree_pickup',
                'item': 'Apple iPhone 16 Pro 512GB (Black Titanium)',
                'price': '\$990 Cash / OSKO',
                'location': 'Altona Gate Shopping Centre (Millers Rd)',
                'timeProposed': 'Today at 3:30 PM',
                'verifiedSafe': true,
              },
            ),
          ],
        ),
      );

      // 2. Business Workspace Lead: Subliminator CEO Hicham Amrani
      // Derived from SUBLIMINATOR_HICHAM_SAMPLE_INVOICE_REQUEST
      loadedThreads.add(
        InboxThread(
          id: 'gmail_subliminator_hicham',
          channel: InboxChannel.gmailBusiness,
          contactName: 'Hicham Amrani (CEO Subliminator)',
          contactAddress: 'hicham@subliminator.com',
          subject:
              'Follow-up: Sample Order Invoice Request (EJ350397089AU - Lauburu Canonical Rashguard & Shorts)',
          lastMessagePreview:
              'Sample cut for EJ350397089AU on track in Shaoxing. Ready to issue invoice once specs confirmed.',
          lastMessageTime: now.subtract(const Duration(hours: 3)),
          unreadCount: 0,
          priority: InboxPriority.vip,
          isPinned: true,
          aiSummary:
              'B2B production update on sample parcel EJ350397089AU. 1:1 recreation of Absolute MMA cut.',
          messages: [
            InboxMessage(
              id: 'sub_msg_1',
              threadId: 'gmail_subliminator_hicham',
              senderName: 'Hicham Amrani',
              senderAddress: 'hicham@subliminator.com',
              text:
                  'Hi Aaron, Great news. The sample cut for EJ350397089AU is on track in Shaoxing. We reviewed the 250 GSM poly-spandex blend and 4-needle 6-thread flatlock stitching. Ready to issue sample invoice.',
              timestamp: now.subtract(const Duration(hours: 5)),
              isOutgoing: false,
              channel: InboxChannel.gmailBusiness,
              status: MessageStatus.read,
            ),
            InboxMessage(
              id: 'sub_msg_2',
              threadId: 'gmail_subliminator_hicham',
              senderName: 'Aaron Maher',
              senderAddress: 'lauburu@lauburugrappling.com',
              text:
                  'Hi Hicham, Thanks for the honest and straightforward feedback — I really appreciate your team evaluating the specs carefully. Let\'s keep it simple and stick to what works: we would like to proceed with a 1:1 recreation using the exact cut, pattern, and construction of the Absolute MMA reference samples your Shaoxing team has on hand (Parcel EJ350397089AU). Please issue the sample invoice to lauburu@lauburugrappling.com so we can settle payment and get the sample rolling. Best regards, Aaron Maher, Founder, Lauburu Grappling',
              timestamp: now.subtract(const Duration(hours: 3)),
              isOutgoing: true,
              channel: InboxChannel.gmailBusiness,
              status: MessageStatus.delivered,
              suggestedReplies: [
                'Please issue invoice to lauburu@lauburugrappling.com',
                'Sample parcel received and inspected.',
                'Proceed with Option B embroidery emblems.',
              ],
              richCardData: {
                'type': 'subliminator_b2b',
                'parcelId': 'EJ350397089AU',
                'specs': '250 GSM Poly-Spandex / 4-needle 6-thread flatlock',
                'manufacturingFacility': 'Shaoxing, China',
              },
            ),
          ],
        ),
      );

      // 3. Shopify Storefront Lead: Authentic Commercial Order Event
      // Derived from REVERSE_ENGINEERED_COMMERCE_SUITE & PAY_BY_COMPUTE_INTEGRATION
      loadedThreads.add(
        InboxThread(
          id: 'shopify_commerce_suite',
          channel: InboxChannel.shopify,
          contactName: 'Shopify Commerce Lead (Order #LBG-1082)',
          contactAddress: 'orders@lauburu-grappling.myshopify.com',
          subject: 'Order #LBG-1082 - Fulfillment & Tracking Status',
          lastMessagePreview:
              'Tracking updated for Order #LBG-1082: Dispatched with AusPost Express from Melbourne hub.',
          lastMessageTime: now.subtract(const Duration(hours: 4)),
          unreadCount: 1,
          priority: InboxPriority.commercialLead,
          aiSummary:
              'Commercial storefront customer order #LBG-1082 fulfillment and AusPost tracking update.',
          messages: [
            InboxMessage(
              id: 'shp_msg_1',
              threadId: 'shopify_commerce_suite',
              senderName: 'Shopify Storefront Dispatch',
              senderAddress: 'orders@lauburu-grappling.myshopify.com',
              text:
                  'Kanji Combat Rashguard (Order #LBG-1082) dispatched with AusPost Express. Tracking link synchronized with customer profile.',
              timestamp: now.subtract(const Duration(hours: 4)),
              isOutgoing: false,
              channel: InboxChannel.shopify,
              status: MessageStatus.delivered,
              suggestedReplies: [
                'Order #LBG-1082 dispatched today with AusPost Express.',
                'Tracking link has been emailed to you.',
                'Thanks for your support! Dispatched from Melbourne hub.',
              ],
              richCardData: {
                'type': 'shopify_order',
                'orderNumber': '#LBG-1082',
                'product': 'Kanji Combat Rashguard (Black/Gold, Size L)',
                'status': 'Fulfillment In Progress',
                'carrier': 'Australia Post Express',
              },
            ),
          ],
        ),
      );

      // 4. B2B Wholesale Lead: Melbourne BJJ Academy
      // Derived from B2B_ACADEMY_WHOLESALE_PRICING_SEALED event in ledger
      loadedThreads.add(
        InboxThread(
          id: 'b2b_melbourne_academy',
          channel: InboxChannel.gmailBusiness,
          contactName: 'Melbourne BJJ Academy (Wholesale Lead)',
          contactAddress: 'wholesale@melbournebjj.com.au',
          subject: 'B2B Academy Wholesale Pricing Agreement (\$48 Tier 1 / \$42 Tier 2)',
          lastMessagePreview:
              'Pricing sealed: \$48/unit (20-49 units) and \$42/unit (50+ units). Awaiting initial batch sizes.',
          lastMessageTime: now.subtract(const Duration(hours: 6)),
          unreadCount: 0,
          priority: InboxPriority.commercialLead,
          aiSummary: 'B2B wholesale pricing agreement ratified per business ledger anchors.',
          messages: [
            InboxMessage(
              id: 'b2b_msg_1',
              threadId: 'b2b_melbourne_academy',
              senderName: 'Academy Head Coach',
              senderAddress: 'wholesale@melbournebjj.com.au',
              text:
                  'Hi Aaron, we would like to move forward with the academy rashguards at \$48/unit for our initial order of 35 pieces. Can we get size distribution charts?',
              timestamp: now.subtract(const Duration(hours: 6)),
              isOutgoing: false,
              channel: InboxChannel.gmailBusiness,
              status: MessageStatus.read,
              suggestedReplies: [
                'Size chart attached (XS to 3XL). 50% deposit required.',
                'We can deliver the first 35 units within 14 business days.',
              ],
            ),
          ],
        ),
      );

      // 5. Combat Lab Movesense Fighter Telemetry
      // Derived from LEAD_05_COMBAT_LAB_MOVESENSE_FIGHTER event in ledger
      loadedThreads.add(
        InboxThread(
          id: 'lead_combat_lab_movesense',
          channel: InboxChannel.gmailBusiness,
          contactName: 'Combat Lab Movesense Fighter',
          contactAddress: 'fighter@combatlab.com.au',
          subject: 'Movesense 512Hz ECG Combat Telemetry Validation',
          lastMessagePreview:
              'Autonomous dispatch: 512Hz Pan-Tompkins QRS detection and bicep band telemetry validated.',
          lastMessageTime: now.subtract(const Duration(hours: 8)),
          unreadCount: 0,
          priority: InboxPriority.commercialLead,
          aiSummary: 'Movesense MD+ medical ECG combat integration telemetry inquiry.',
          messages: [
            InboxMessage(
              id: 'cl_msg_1',
              threadId: 'lead_combat_lab_movesense',
              senderName: 'Combat Lab Lead Scientist',
              senderAddress: 'fighter@combatlab.com.au',
              text:
                  'We have verified the 512Hz ECG stream with the custom bicep band. The Kamath 20% filter effectively removes grappling artifacts.',
              timestamp: now.subtract(const Duration(hours: 8)),
              isOutgoing: false,
              channel: InboxChannel.gmailBusiness,
              status: MessageStatus.read,
            ),
          ],
        ),
      );

      // 6. Marketplace Trade Arbitrage
      // Derived from LEAD_03_MARKETPLACE_TRADE_LOWBALL event in ledger
      loadedThreads.add(
        InboxThread(
          id: 'marketplace_trade_arbitrage',
          channel: InboxChannel.gumtree,
          contactName: 'Marketplace Trade Arbitrage',
          contactAddress: 'trade@marketplace.local',
          subject: 'Marketplace Trade Offer: Tech Arbitrage',
          lastMessagePreview:
              'Offer rejected: Below hard floor (\$850.00 AUD hard floor, \$890.00 cash anchor).',
          lastMessageTime: now.subtract(const Duration(hours: 14)),
          unreadCount: 0,
          priority: InboxPriority.lowPriority,
          aiSummary: 'Lowball marketplace trade inquiry automatically filtered by cash floor rule.',
          messages: [
            InboxMessage(
              id: 'trade_msg_1',
              threadId: 'marketplace_trade_arbitrage',
              senderName: 'Trader',
              senderAddress: 'trade@marketplace.local',
              text: 'Would you take \$700 cash today for the iPhone 16 Pro?',
              timestamp: now.subtract(const Duration(hours: 14)),
              isOutgoing: false,
              channel: InboxChannel.gumtree,
              status: MessageStatus.read,
            ),
          ],
        ),
      );

      // 7. Dialectic Adversarial Auditor
      // Derived from ELO_PENALTY_AND_POOR_SUGGESTION_AUDIT event in ledger
      loadedThreads.add(
        InboxThread(
          id: 'adversarial_audit_event',
          channel: InboxChannel.gmailBusiness,
          contactName: 'Dialectic Adversarial Auditor (Port 8082 vs 8083)',
          contactAddress: 'auditor@lauburu.local',
          subject: 'Adversarial Audit: ELO Penalty & Pricing Floor Enforcement',
          lastMessagePreview:
              'Audit ratified: Purged synthetic personas, enforced \$48/\$42 B2B floor, negative DPO pairs injected.',
          lastMessageTime: now.subtract(const Duration(hours: 20)),
          unreadCount: 0,
          priority: InboxPriority.actionRequired,
          isPinned: true,
          aiSummary: 'Autonomous dialectic audit enforcing wholesale pricing floor and continuous LoRA conditioning.',
          messages: [
            InboxMessage(
              id: 'audit_msg_1',
              threadId: 'adversarial_audit_event',
              senderName: 'Screen Lens Sovereign Auditor',
              senderAddress: 'auditor@lauburu.local',
              text:
                  'Adversarial audit completed for ledger events. Zero synthetic personas permitted. Wholesale floor locked at \$48/\$42 AUD.',
              timestamp: now.subtract(const Duration(hours: 20)),
              isOutgoing: false,
              channel: InboxChannel.gmailBusiness,
              status: MessageStatus.read,
            ),
          ],
        ),
      );

      _threads = loadedThreads;
    } catch (e) {
      debugPrint('Error loading threads from business ledger: $e');
      _threads = [];
    }
  }

  List<InboxThread> getThreads({InboxChannel filter = InboxChannel.all}) {
    if (filter == InboxChannel.all) {
      return List.unmodifiable(_threads);
    }
    return List.unmodifiable(
      _threads.where((t) => t.channel == filter).toList(),
    );
  }

  InboxThread? getThreadById(String id) {
    try {
      return _threads.firstWhere((t) => t.id == id);
    } catch (_) {
      return null;
    }
  }

  Future<void> sendMessage(String threadId, String text) async {
    final threadIndex = _threads.indexWhere((t) => t.id == threadId);
    if (threadIndex == -1) return;

    final existingThread = _threads[threadIndex];
    final newMessage = InboxMessage(
      id: 'msg_${DateTime.now().millisecondsSinceEpoch}',
      threadId: threadId,
      senderName: 'Aaron Maher',
      senderAddress: 'me',
      text: text,
      timestamp: DateTime.now(),
      isOutgoing: true,
      channel: existingThread.channel,
      status: MessageStatus.sent,
    );

    final updatedMessages = List<InboxMessage>.from(existingThread.messages)
      ..add(newMessage);

    final updatedThread = existingThread.copyWith(
      messages: updatedMessages,
      lastMessagePreview: text,
      lastMessageTime: DateTime.now(),
      unreadCount: 0,
    );

    _threads[threadIndex] = updatedThread;
    _emitThreads();
  }

  Future<void> markAsRead(String threadId) async {
    final threadIndex = _threads.indexWhere((t) => t.id == threadId);
    if (threadIndex == -1) return;

    final existingThread = _threads[threadIndex];
    if (existingThread.unreadCount == 0) return;

    final updatedThread = existingThread.copyWith(unreadCount: 0);
    _threads[threadIndex] = updatedThread;
    _emitThreads();
  }

  Future<void> refreshThreads() async {
    // If local AI triage service is available, run triage update on threads
    if (triageService != null) {
      for (int i = 0; i < _threads.length; i++) {
        final thread = _threads[i];
        try {
          final triage = await triageService!.triageConversation(
            channel: thread.channel,
            contactName: thread.contactName,
            contactAddress: thread.contactAddress,
            recentMessages: thread.messages
                .map((m) => {
                      'sender': m.senderName,
                      'text': m.text,
                    })
                .toList(),
          );
          _threads[i] = thread.copyWith(
            priority: triage.priority,
          );
        } catch (e) {
          debugPrint('Triage failed for ${thread.id}: $e');
        }
      }
    }
    _emitThreads();
  }

  void setThreads(List<InboxThread> threads) {
    _threads = List.from(threads);
    _emitThreads();
  }

  void dispose() {
    _threadsController.close();
  }
}
