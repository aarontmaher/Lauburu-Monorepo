# Project: Lauburu Life Companion Enhancement

## Architecture
The Lauburu Life Companion is a cross-platform (macOS / Android / Web) Flutter application backed by native OS persistence layers, local AI inference nodes (Sovereign Local AI Hierarchy on Ports 8081, 8082, 8083), the Shopify Storefront/Customer API for cloud-authenticated cross-device session synchronization, the True Omni Inbox messaging subsystem, and the Commerce Hub Bluetooth Serial Terminal bridge on TCP port 4005.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NATIVE SYSTEM PERSISTENCE (R1)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • macOS: ~/Library/LaunchAgents/com.lauburu.lifecompanion.plist             │
│   Direct non-forking execution of background daemon; silent boot.           │
│ • Android: AndroidManifest.xml RECEIVE_BOOT_COMPLETED & BootReceiver.kt     │
│   Silent background initialization without launching UI in foreground.     │
├─────────────────────────────────────────────────────────────────────────────┤
│                    FLUTTER APPLICATION ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Presentation:                                                             │
│   - lib/main.dart (Identifier-First Title: 'Life Companion Lauburu')        │
│   - lib/screens/omni_inbox_screen.dart (All-in-One Multi-Account Messages)  │
│   - lib/screens/inbox_thread_detail_screen.dart (Detail View, Smart Replies)│
│   - lib/screens/chat_hub_screen.dart (Backward-Compatible Wrapper Alias)    │
│   - lib/screens/shopify_login_dialog.dart (Customer Auth UI, Dev Fallback)  │
│   - lib/screens/ecommerce_hub_screen.dart (Catalog, AI Status, Ad Copy)     │
│   - lib/widgets/ai_status_badge.dart (Port 8082/8083/8081 Health)           │
│   - lib/widgets/mesh_terminal_sheet.dart (TCP 4005 Serial Terminal Modal)   │
│ • Domain & Models:                                                          │
│   - lib/models/customer_profile.dart (CustomerProfile, Tier: Free/Pro/Elite)│
│   - lib/models/ecommerce_models.dart (CatalogItem, Metrics, AiInference)    │
│   - lib/models/inbox_models.dart (InboxChannel, Priority, Messages, Threads)│
│ • Services:                                                                 │
│   - lib/services/session_storage.dart (SharedPreferences persistent store)  │
│   - lib/services/shopify_auth_service.dart (Storefront GraphQL + dev token)│
│   - lib/services/ecommerce_ai_service.dart (Port 8082/8083 Zero-Mock AI)   │
│   - lib/services/omni_inbox_service.dart (Reactive Stream, 7 Connectors)    │
│   - lib/services/omni_ai_triage_service.dart (Local AI Triage & Voice Chips)│
│   - lib/services/mesh_terminal_service.dart (TCP 4005 Socket Connection)   │
│   - lib/services/chat_hub_service.dart (Backward-Compatible Adapter)        │
├─────────────────────────────────────────────────────────────────────────────┤
│                       EXTERNAL & LOCAL SERVICES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Shopify Storefront API: https://lauburu-grappling.myshopify.com/api/      │
│ • Local AI Port 8082: Sovereign Master Orchestrator (qwen_38_max)           │
│ • Local AI Port 8083: Metal LLM Worker (qwen_38_max_abliterated / llama)   │
│ • Local AI Port 8081: Syntax Worker / Micro-Linter                          │
│ • TCP Port 4005 Daemon: bluetooth_serial_terminal_daemon.py (Zero EBUSY)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | macOS LaunchAgent Plist | Silent boot background daemon auto-start via LaunchAgent plist in ~/Library/LaunchAgents | M1 | ORIGINAL_REQUEST §R1 |
| 2 | macOS Boot Verification Script | Programmatic verification script checking plist validity, launchctl domain load, and port availability | M1 | ORIGINAL_REQUEST §Acceptance Criteria |
| 3 | Android Boot Completed Permission | AndroidManifest.xml RECEIVE_BOOT_COMPLETED permission declaration | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Android Boot Completed Receiver | Exported BootReceiver with intent filter and permission for boot handling | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Android AGP Compatibility | Build configuration ensuring clean compilation and lint pass on Android API 31-36 | M1 | Survey 1 |
| 6 | Shopify Storefront Auth Service | GraphQL customerAccessTokenCreate, renewal, and deletion service | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Shopify Customer Profile & Tier Query | Query customer tags to determine membership tier (Free/Pro/Elite) | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Persistent Session Storage | Token and profile storage via SharedPreferences surviving app restarts | M2 | ORIGINAL_REQUEST §R3 |
| 9 | Cross-Device Session Syncing | Canonical cloud sync using Shopify API as single source of truth | M2 | ORIGINAL_REQUEST §R3 |
| 10 | Shopify Customer Login UI | Login dialog/screen in Flutter app with validation and dev token support | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Life Companion App Bar & Badges | App bar integration with member tier badge and auth state management | M2 | Survey 2 |
| 12 | Sovereign Local AI Dual-Port Client | Resilient HTTP client querying Port 8082 with fallback to Port 8083 | M3 | ORIGINAL_REQUEST §R4 |
| 13 | Strict Timeout Boundaries | 1.5s probe timeout and 15s inference timeout to prevent API timeouts | M3 | ORIGINAL_REQUEST §Acceptance Criteria |
| 14 | Canonical E-Commerce Catalog | 18-item canonical commercial catalog models and query interface | M3 | ORIGINAL_REQUEST §R4 |
| 15 | AI Ad Copy Generation & Storefront Analytics | Workflow integrating local LLMs for ad copy and storefront metrics | M3 | ORIGINAL_REQUEST §R4 |
| 16 | E-Commerce Hub Screen | Flutter UI for catalog browsing, AI health badges, and copy generation | M3 | ORIGINAL_REQUEST §R4 |
| 17 | Zero-Mock Waiting States | Display authentic data or clean waiting state (`--`), never fake data | M3 | Rule 1 & Survey 3 |
| 18 | Rule 9 App Title Compliance | Flutter app title set to 'Life Companion Lauburu' | M2 | Rule 9 & Survey 2 |
| 19 | Comprehensive Unit & Widget Test Suites | Deterministic test harnesses for auth, persistence, and e-commerce | M4 | ORIGINAL_REQUEST §Acceptance Criteria |
| 20 | Opaque-Box E2E Test Suite | 4-tier E2E testing track suite derived from requirements | M4 | Dual Track Policy |
| 21 | True Omni Inbox Messaging UI | Main messages UI with search, channel filter pills, and badges | M5 | ORIGINAL_REQUEST 2026-09-17 §R1 |
| 22 | Multi-Account Data Models | InboxChannel, InboxPriority, InboxMessage, InboxThread models | M5 | ORIGINAL_REQUEST 2026-09-17 §R1 |
| 23 | Authentic Seed Ingestion Service | OmniInboxService aggregating 7 channels with reactive streams | M5 | ORIGINAL_REQUEST 2026-09-17 §R1 |
| 24 | Top Channel Filter Pills | Horizontal filter bar ([All], [Gmail], [Instagram], [SMS], [Shopify]) | M5 | ORIGINAL_REQUEST 2026-09-17 §R1 |
| 25 | Thread Detail View Screen | Detail chat view with incoming/outgoing bubbles and cards | M5 | ORIGINAL_REQUEST 2026-09-17 §R1 |
| 26 | ChatHubScreen Backward Compat Wrapper | Preserve ChatHubScreen as wrapper with all AppBar keys to keep 39 tests passing | M5 | Survey 1 Findings |
| 27 | Private Local AI Triage Service | OmniAiTriageService querying Sovereign Local AI with zero cloud leakage | M6 | ORIGINAL_REQUEST 2026-09-17 §R2 |
| 28 | Dual-Port Sovereign AI Triage | Query Port 8082 (qwen_38_max) with automatic failover to Port 8083 | M6 | ORIGINAL_REQUEST 2026-09-17 §R2 |
| 29 | Priority Triage Badges | Compute Action Required, Commercial Lead, VIP, Low Priority badges | M6 | ORIGINAL_REQUEST 2026-09-17 §R2 |
| 30 | Aaron's Voice Smart Replies | Contextual smart reply chip suggestions in composer matching Aaron's voice | M6 | ORIGINAL_REQUEST 2026-09-17 §R2 |
| 31 | Zero-Mock Offline Triage Fallback | Deterministic heuristic classifier and empty reply list when AI offline | M6 | Survey 2 & Rule 1 |
| 32 | Mesh Terminal Socket Service | MeshTerminalService managing TCP socket to port 4005 | M7 | ORIGINAL_REQUEST 2026-09-17 §R3 |
| 33 | Mesh Terminal Bottom Sheet | MeshTerminalSheet modal bottom sheet with console styling and autoscroll | M7 | ORIGINAL_REQUEST 2026-09-17 §R3 |
| 34 | TCP Port 4005 Gateway Integration | Mediate serial access via host daemon, preventing raw Bluetooth EBUSY | M7 | ORIGINAL_REQUEST 2026-09-17 §R3 |
| 35 | Quick-Action Macro Chips | Action chips for status, audit, devices, movesense, clear | M7 | ORIGINAL_REQUEST 2026-09-17 §R3 |
| 36 | ANSI Sanitization & Command Input | Monospace console with ANSI escape stripping and command input field | M7 | Survey 3 Findings |
| 37 | Ecommerce Hub Terminal Integration | AppBar button and FAB in ecommerce_hub_screen.dart to launch terminal | M7 | ORIGINAL_REQUEST 2026-09-17 §R3 |
| 38 | Omni Inbox Unit & Widget Tests | Test suite verifying channel filtering, badges, thread rendering | M8 | ORIGINAL_REQUEST 2026-09-17 §R4 |
| 39 | Mesh Terminal Widget Tests | Test suite verifying terminal sheet launch, macros, and socket streams | M7 | ORIGINAL_REQUEST 2026-09-17 §R4 |
| 40 | Cross-Platform Regression Verification | 100% test pass (89 Flutter tests + 50 E2E tests), flutter analyze zero issues | M8 | ORIGINAL_REQUEST 2026-09-17 §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Native Silent Boot Persistence | macOS LaunchAgent plist, verification script, AndroidManifest.xml, BootReceiver.kt | None | DONE |
| M2 | Shopify Login & Cross-Device Sync | pubspec.yaml dependencies, models, session storage, Shopify auth service, login UI, chat hub integration | None | DONE |
| M3 | Local E-Commerce Models Integration | E-commerce models, dual-port AI service, timeouts, hub screen, AI badges | M2 | DONE |
| M4 | 100% E2E Test Pass (Round 1) | Run opaque-box E2E test runner, pass 100% tests, adversarial audit | M1, M2, M3 | DONE |
| M5 | True Omni Inbox UI & Connectors (R1) | inbox_models.dart, omni_inbox_service.dart, omni_inbox_screen.dart, inbox_thread_detail_screen.dart, chat_hub_screen.dart backward-compat wrapper, main.dart route | M2, M3 | DONE |
| M6 | Private Local AI Triage & Smart Replies (R2) | omni_ai_triage_service.dart, priority badges, Aaron voice prompt & reply chips, zero-mock offline fallback, thread detail integration | M5 | DONE |
| M7 | Commerce Hub Bluetooth Serial Terminal (R3) | mesh_terminal_service.dart, mesh_terminal_sheet.dart, quick macro chips (status, audit, devices, movesense, clear), ecommerce_hub_screen.dart integration, RenderFlex overflow fix | M3 | DONE |
| M8 | Integration, Test Suites & Verification (R4) | omni_inbox_test.dart, mesh_terminal_sheet_test.dart, stress_and_boundary_test.dart (89 tests passing), 50 E2E tests, flutter analyze, multi-agent review & forensic audit | M5, M6, M7 | DONE |

## Interface Contracts

### M5 (Omni Inbox) ↔ Flutter Presentation
- `lib/models/inbox_models.dart`:
  - `enum InboxChannel { all, gmailPersonal, gmailBusiness, sms, instagram, facebook, shopify, gumtree }`
  - `enum InboxPriority { actionRequired, commercialLead, vip, lowPriority }`
  - `enum MessageStatus { sent, delivered, read, staged }`
  - `class InboxMessage { id, threadId, senderName, senderAddress, text, timestamp, isOutgoing, channel, status, suggestedReplies, richCardData }`
  - `class InboxThread { id, channel, contactName, contactAddress, avatarUrl, subject, lastMessagePreview, lastMessageTime, unreadCount, priority, isPinned, messages, aiSummary }`
- `lib/services/omni_inbox_service.dart`:
  - `Stream<List<InboxThread>> get threadsStream;`
  - `List<InboxThread> getThreads({InboxChannel filter = InboxChannel.all});`
  - `InboxThread? getThreadById(String id);`
  - `Future<void> sendMessage(String threadId, String text);`
  - `Future<void> markAsRead(String threadId);`
  - `Future<void> refreshThreads();`
- `lib/screens/chat_hub_screen.dart`:
  - Preserved constructor: `ChatHubScreen({Key? key, ShopifyAuthService? authService, ChatHubService? chatHubService, OmniInboxService? omniInboxService})`
  - Drop-in wrapper that renders `OmniInboxScreen`, preserving AppBar keys (`appbar_tier_badge`, `login_action_button`, `profile_action_button`, `ecommerce_hub_button`) and profile modal keys (`profile_email`, `profile_modal_tier_badge`, `logout_button`).
  - Constraint: Only the AppBar tier badge renders text `'FREE'` in unauthenticated state.

### M6 (Local AI Triage) ↔ Omni Inbox
- `lib/services/omni_ai_triage_service.dart`:
  - `Future<TriageResult> triageConversation({required InboxChannel channel, required String contactName, required String contactAddress, required List<Map<String, String>> recentMessages, String? customerTier})`
  - `TriageResult computeHeuristicFallback({required InboxChannel channel, required String contactAddress, required String latestMessageText, String? customerTier})`
  - `Future<List<String>> generateSmartReplies({required InboxChannel channel, required List<Map<String, String>> recentMessages})`
- HTTP Endpoint: `http://127.0.0.1:8082/v1/chat/completions` (failover to `http://127.0.0.1:8083`).
- Zero Cloud Leakage: 100% localhost; never calls external cloud APIs.

### M7 (Bluetooth Terminal) ↔ Ecommerce Hub
- `lib/services/mesh_terminal_service.dart`:
  - `abstract class IMeshTerminalService`
  - `Stream<String> get outputStream;`
  - `Stream<TerminalConnectionState> get stateStream;`
  - `TerminalConnectionState get state;`
  - `Future<void> connect({String? host, int? port});`
  - `Future<void> sendCommand(String command);`
  - `Future<void> disconnect();`
- TCP Endpoint: Host TCP port 4005 (`bluetooth_serial_terminal_daemon.py`).
- Macros: `status`, `audit`, `devices`, `movesense`, `clear`.
- `lib/widgets/mesh_terminal_sheet.dart`:
  - Modal bottom sheet rendered with monospace font, connection badge with `BoxConstraints(maxWidth: 140)`, Tooltip for full error strings, macro row, ANSI sanitization, autoscroll, and command input field.
- `lib/screens/ecommerce_hub_screen.dart`:
  - Accepts optional `terminalService` parameter; AppBar icon button (`open_mesh_terminal_button`) and FAB (`terminal_fab`).

## Code Layout
- `lib/`:
  - `lib/main.dart`
  - `lib/models/customer_profile.dart`
  - `lib/models/ecommerce_models.dart`
  - `lib/models/inbox_models.dart`
  - `lib/services/session_storage.dart`
  - `lib/services/shopify_auth_service.dart`
  - `lib/services/ecommerce_ai_service.dart`
  - `lib/services/omni_inbox_service.dart`
  - `lib/services/omni_ai_triage_service.dart`
  - `lib/services/mesh_terminal_service.dart`
  - `lib/services/chat_hub_service.dart`
  - `lib/screens/chat_hub_screen.dart`
  - `lib/screens/omni_inbox_screen.dart`
  - `lib/screens/inbox_thread_detail_screen.dart`
  - `lib/screens/shopify_login_dialog.dart`
  - `lib/screens/ecommerce_hub_screen.dart`
  - `lib/widgets/ai_status_badge.dart`
  - `lib/widgets/mesh_terminal_sheet.dart`
- `test/`:
  - `test/shopify_auth_service_test.dart`
  - `test/login_widget_test.dart`
  - `test/auth_persistence_test.dart`
  - `test/ecommerce_service_test.dart`
  - `test/ecommerce_hub_screen_test.dart`
  - `test/omni_inbox_test.dart`
  - `test/mesh_terminal_sheet_test.dart`
  - `test/stress_and_boundary_test.dart`
