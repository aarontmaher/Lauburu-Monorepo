import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/ecommerce_models.dart';

/// Service for communicating with the Sovereign Local AI Hierarchy
/// (Port 8082 Sovereign Master Orchestrator, Port 8083 Metal LLM Worker)
/// with strict timeout boundaries, resilient failover, and zero-mock waiting states.
class EcommerceAiService {
  final http.Client _client;
  final String primaryBaseUrl;
  final String fallbackBaseUrl;
  final int primaryPort;
  final int fallbackPort;
  final String ledgerPath;

  static const String defaultLedgerPath =
      '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/business_ledger.json';

  /// Acceptance Criterion 33: Probe timeout bounded to 1,500ms
  static const Duration probeTimeout = Duration(milliseconds: 1500);

  /// Acceptance Criterion 33: Inference timeout bounded to 15,000ms
  static const Duration inferenceTimeout = Duration(milliseconds: 15000);

  EcommerceAiService({
    http.Client? client,
    this.primaryBaseUrl = 'http://127.0.0.1:8082',
    this.fallbackBaseUrl = 'http://127.0.0.1:8083',
    this.primaryPort = 8082,
    this.fallbackPort = 8083,
    this.ledgerPath = defaultLedgerPath,
  }) : _client = client ?? http.Client();

  void dispose() {
    _client.close();
  }

  /// Probes the health of a local AI model endpoint.
  /// Bounded to 1,500ms timeout to avoid UI freezes and API timeouts.
  Future<AiModelStatus> probeModelHealth({int? port}) {
    final targetPort = port ?? primaryPort;
    final isPrimary = targetPort == primaryPort;
    final baseUrl = isPrimary ? primaryBaseUrl : fallbackBaseUrl;
    final modelName = isPrimary ? 'Qwen 3.8 Max (Master)' : 'llama-server 7B (Metal)';

    return _probeUrl(baseUrl, targetPort, modelName);
  }

  Future<AiModelStatus> _probeUrl(String baseUrl, int port, String defaultModelName) async {
    final stopwatch = Stopwatch()..start();
    try {
      final uri = Uri.parse('$baseUrl/health');
      final response = await _client.get(uri).timeout(probeTimeout);
      stopwatch.stop();

      if (response.statusCode == 200) {
        String resolvedName = defaultModelName;
        try {
          final decoded = jsonDecode(response.body);
          if (decoded is Map && decoded.containsKey('service')) {
            resolvedName = decoded['service'].toString();
          }
        } catch (_) {}

        return AiModelStatus(
          port: port,
          modelName: resolvedName,
          isOnline: true,
          statusMessage: 'ONLINE (${response.statusCode})',
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      } else {
        return AiModelStatus(
          port: port,
          modelName: defaultModelName,
          isOnline: false,
          statusMessage: 'HTTP ${response.statusCode}',
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      }
    } on TimeoutException {
      stopwatch.stop();
      return AiModelStatus(
        port: port,
        modelName: defaultModelName,
        isOnline: false,
        statusMessage: 'Probe timed out (>1500ms)',
        latencyMs: 1500,
      );
    } catch (e) {
      stopwatch.stop();
      return AiModelStatus(
        port: port,
        modelName: defaultModelName,
        isOnline: false,
        statusMessage: 'Offline: $e',
        latencyMs: -1,
      );
    }
  }

  /// Probes both primary (Port 8082) and fallback (Port 8083) endpoints.
  Future<List<AiModelStatus>> probeMeshHealth() async {
    return Future.wait([
      probeModelHealth(port: primaryPort),
      probeModelHealth(port: fallbackPort),
    ]);
  }

  /// Executes OpenAI-compatible chat completion inference with resilient failover.
  /// Bounded to 15,000ms timeout per call to satisfy Acceptance Criterion 33.
  /// Failover chain: Port 8082 -> Port 8083 -> Clean Zero-Mock Waiting State ('--').
  Future<AiInferenceResult> queryInference({
    required String prompt,
    int maxTokens = 512,
    String? preferredModel,
  }) async {
    // 1. Attempt Primary Endpoint (Port 8082)
    final stopwatch = Stopwatch()..start();
    try {
      final primaryUri = Uri.parse('$primaryBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'model': preferredModel ?? 'qwen_38_max',
        'messages': [
          {'role': 'user', 'content': prompt}
        ],
        'max_tokens': maxTokens,
      });

      final response = await _client
          .post(
            primaryUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      stopwatch.stop();

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final choices = decoded['choices'] as List? ?? [];
        if (choices.isNotEmpty) {
          final first = choices[0] as Map<String, dynamic>;
          final message = first['message'] as Map<String, dynamic>? ?? {};
          final content = message['content']?.toString() ?? '--';
          final finishReason = first['finish_reason']?.toString() ?? 'stop';
          final modelId = decoded['model']?.toString() ?? 'qwen_38_max';

          return AiInferenceResult(
            content: content,
            modelId: modelId,
            port: primaryPort,
            latencyMs: stopwatch.elapsedMilliseconds,
            finishReason: finishReason,
            isFallback: false,
          );
        }
      } else {
        debugPrint(
          'Port $primaryPort returned HTTP ${response.statusCode} (e.g. 503 Host Sanctuary protect), failing over to Port $fallbackPort',
        );
      }
    } catch (e) {
      debugPrint('Port $primaryPort inference failed or timed out ($e), initiating failover to Port $fallbackPort');
    }

    // 2. Attempt Fallback Endpoint (Port 8083 Metal Worker)
    stopwatch.reset();
    stopwatch.start();
    try {
      final fallbackUri = Uri.parse('$fallbackBaseUrl/v1/chat/completions');
      final body = jsonEncode({
        'messages': [
          {'role': 'user', 'content': prompt}
        ],
        'max_tokens': maxTokens,
      });

      final response = await _client
          .post(
            fallbackUri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(inferenceTimeout);

      stopwatch.stop();

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final choices = decoded['choices'] as List? ?? [];
        if (choices.isNotEmpty) {
          final first = choices[0] as Map<String, dynamic>;
          final message = first['message'] as Map<String, dynamic>? ?? {};
          final content = message['content']?.toString() ?? '--';
          final finishReason = first['finish_reason']?.toString() ?? 'stop';
          final modelId = decoded['model']?.toString() ?? 'llama-server-7b';

          return AiInferenceResult(
            content: content,
            modelId: modelId,
            port: fallbackPort,
            latencyMs: stopwatch.elapsedMilliseconds,
            finishReason: finishReason,
            isFallback: true,
          );
        }
      }
    } catch (e) {
      debugPrint('Port $fallbackPort fallback inference also failed ($e)');
    }

    // 3. Both nodes offline: Return Rule 1 Zero-Mock Waiting State ('--')
    return AiInferenceResult.offline(port: fallbackPort, message: '--');
  }

  /// Generates direct-response e-commerce advertising copy for a catalog item.
  Future<String> generateAdCopy(CommerceCatalogItem item) async {
    final prompt =
        'Write a compelling high-converting e-commerce ad copy for this product:\n'
        'Title: ${item.title}\n'
        'Category: ${item.category}\n'
        'Price: ${item.formattedPrice}\n'
        'Vendor: ${item.vendor}\n'
        'Details: ${item.description}\n'
        'Format with a catchy hook headline, 3 key benefits, and a clear call to action.';

    final result = await queryInference(prompt: prompt, maxTokens: 300);
    return result.content;
  }

  /// Routes transaction telemetry to the e-commerce local AI training pipeline (Qwen 3.8 Max on Port 8082).
  Future<void> sendTransactionTelemetry(CommerceCatalogItem item, String action) async {
    final prompt = 'TELEMETRY_EVENT: {"action": "$action", "item_id": "${item.id}", "price": ${item.priceAud}, "timestamp": "${DateTime.now().toIso8601String()}"}';
    // Send to Port 8082 (Master)
    await queryInference(prompt: prompt, maxTokens: 50, preferredModel: 'qwen_38_max');
  }

  /// Evaluates storefront metrics against canonical ledger benchmarks.
  /// Reads directly from business_ledger.json per Rule #0.
  /// Returns a clean waiting state ('--') if the ledger file is unreadable.
  Future<EcommerceMetrics> analyzeStorefrontMetrics({String? customPath}) async {
    final path = customPath ?? ledgerPath;
    try {
      var file = File(path);
      if (!file.existsSync()) {
        final altPath = path.contains('/Users/aaron/')
            ? path.replaceFirst('/Users/aaron/', '/Users/Shared/aaron/')
            : path.replaceFirst('/Users/Shared/aaron/', '/Users/aaron/');
        final altFile = File(altPath);
        if (altFile.existsSync()) {
          file = altFile;
        } else {
          return EcommerceMetrics.waitingState();
        }
      }
      final raw = file.readAsStringSync();
      final data = jsonDecode(raw) as Map<String, dynamic>;

      final capital = (data['total_capital_aud'] as num?)?.toDouble() ?? 0.0;
      final credits = (data['available_openrouter_credits'] as num?)?.toDouble() ?? 0.0;
      final elo = (data['lifetime_elo_earned'] as num?)?.toInt() ?? 0;

      final milestones = data['completed_milestones'] as Map<String, dynamic>? ?? {};
      final payByComputeMilestone = milestones['PAY_BY_COMPUTE_INTEGRATION'] as Map<String, dynamic>?;
      final payByCompute = (payByComputeMilestone?['capital_granted_aud'] as num?)?.toDouble() ?? 0.0;
      final fiatReserve = capital - payByCompute;

      final transactions = data['transaction_history'] as List? ?? [];
      final catalog = getCanonicalCatalog();

      return EcommerceMetrics(
        capitalAud: capital,
        payByComputeAud: payByCompute,
        fiatReserveAud: fiatReserve,
        openRouterCredits: credits,
        catalogCount: catalog.length,
        lifetimeEloEarned: elo,
        completedMilestonesCount: milestones.length,
        transactionCount: transactions.length,
        isWaitingState: false,
      );
    } catch (e) {
      debugPrint('Error ingesting business_ledger.json: $e');
      return EcommerceMetrics.waitingState();
    }
  }

  /// Returns the canonical 18-item commercial catalog matching monorepo standards.
  List<CommerceCatalogItem> getCanonicalCatalog() {
    return const [
      CommerceCatalogItem(
        id: 'item_01',
        title: 'Lauburu Canonical Short Sleeve Rashguard',
        category: 'Combat Uniform',
        priceAud: 97.50,
        vendor: 'Subliminator',
        status: 'Live on Storefront',
        description: '80px Sternum (6.5cm) insignia, moisture-wicking compression fabric',
        symbolScale: '80px Sternum (6.5cm)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983577',
      ),
      CommerceCatalogItem(
        id: 'item_02',
        title: 'Lauburu Canonical No-Gi Pro Fight Shorts',
        category: 'Combat Uniform',
        priceAud: 90.00,
        vendor: 'Subliminator',
        status: 'Live on Storefront',
        description: '90px Lower Quad (7.5cm), 4-way stretch reinforced ripstop',
        symbolScale: '90px Lower Quad (7.5cm)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983578',
      ),
      CommerceCatalogItem(
        id: 'item_03',
        title: 'Lauburu Canonical Combat Uniform Set',
        category: 'Combat Bundle',
        priceAud: 172.50,
        vendor: 'Subliminator',
        status: 'Live on Storefront',
        description: 'Full Match Combo (Short Sleeve Rashguard + Pro Fight Shorts)',
        symbolScale: 'Full Match Combo',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983579',
      ),
      CommerceCatalogItem(
        id: 'item_04',
        title: 'Heavyweight Fleece Pullover Hoodie',
        category: 'Streetwear',
        priceAud: 127.50,
        vendor: 'ODMPOD',
        status: 'Live on Storefront',
        description: '120px Center Chest (10cm), 450gsm heavyweight organic cotton',
        symbolScale: '120px Center Chest (10cm)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983580',
      ),
      CommerceCatalogItem(
        id: 'item_05',
        title: 'Unisex Heavyweight Fleece Joggers',
        category: 'Streetwear',
        priceAud: 112.50,
        vendor: 'ODMPOD',
        status: 'Live on Storefront',
        description: '90px Left Thigh (Shrunk), relaxed tailored street fit',
        symbolScale: '90px Left Thigh (Shrunk)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983581',
      ),
      CommerceCatalogItem(
        id: 'item_06',
        title: 'Heavyweight Streetwear Boxy Tee',
        category: 'Streetwear',
        priceAud: 67.50,
        vendor: 'ODMPOD',
        status: 'Live on Storefront',
        description: '70px Left Chest Pocket, 280gsm combed cotton drop-shoulder',
        symbolScale: '70px Left Chest Pocket',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983582',
      ),
      CommerceCatalogItem(
        id: 'item_07',
        title: 'All-Over Print Crossbody Bag',
        category: 'Accessories',
        priceAud: 72.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: 'Center Panel Pattern, water-resistant cordura with adjustable strap',
        symbolScale: 'Center Panel Pattern',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983583',
      ),
      CommerceCatalogItem(
        id: 'item_08',
        title: 'All-Over Print Utility Backpack',
        category: 'Accessories',
        priceAud: 108.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: 'Stealth Black Monogram (#141414), 28L modular laptop compartment',
        symbolScale: 'Stealth Black Monogram (#141414)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983584',
      ),
      CommerceCatalogItem(
        id: 'item_09',
        title: 'All-Over Print Fanny Pack',
        category: 'Accessories',
        priceAud: 57.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: '75px Front Pouch, dual zippered EDC tactical pack',
        symbolScale: '75px Front Pouch',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983585',
      ),
      CommerceCatalogItem(
        id: 'item_10',
        title: 'Stainless Steel Insulated Water Bottle',
        category: 'Accessories',
        priceAud: 51.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: 'Laser-Etched Insignia, 750ml vacuum insulated 24h cold',
        symbolScale: 'Laser-Etched Insignia',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983586',
      ),
      CommerceCatalogItem(
        id: 'item_11',
        title: 'Embroidered Structured Snapback Hat',
        category: 'Accessories',
        priceAud: 54.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: '5.5cm 3D Puff Embroidery, wool-blend flat brim',
        symbolScale: '5.5cm 3D Puff Embroidery',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983587',
      ),
      CommerceCatalogItem(
        id: 'item_12',
        title: 'Geometric Insignia Die-Cut Sticker Pack',
        category: 'Accessories',
        priceAud: 21.00,
        vendor: 'Printful',
        status: 'Live on Storefront',
        description: '7.5cm Vinyl Die-Cut, UV-resistant matte weatherproof finish',
        symbolScale: '7.5cm Vinyl Die-Cut',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983588',
      ),
      CommerceCatalogItem(
        id: 'item_13',
        title: 'Apple iPhone 16 Pro 512GB Black Titanium',
        category: 'Tech Arbitrage',
        priceAud: 1150.00,
        vendor: 'Local Stock',
        status: 'Gumtree / eBay Live',
        description: 'Altona North Pickup (\$1,100 Floor), sealed in box with invoice',
        symbolScale: 'Altona North Pickup (\$1,100 Floor)',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983589',
      ),
      CommerceCatalogItem(
        id: 'item_14',
        title: 'Movesense MD+ Medical ECG Sensor',
        category: 'Biometrics Hardware',
        priceAud: 170.00,
        vendor: 'Movesense Oy',
        status: 'Hardware Stock',
        description: 'Zero-Out-Of-Pocket Invariant, 512Hz single-lead clinical ECG sensor',
        symbolScale: 'Zero-Out-Of-Pocket Invariant',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983590',
      ),
      CommerceCatalogItem(
        id: 'item_15',
        title: 'Custom Movesense Bicep ECG Band',
        category: 'Biometrics Wearable',
        priceAud: 59.00,
        vendor: 'Manufacturing Staged',
        status: 'BOM Cost \$12',
        description: 'Silver Fiber Compression, non-restrictive combat bicep strap',
        symbolScale: 'Silver Fiber Compression',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983591',
      ),
      CommerceCatalogItem(
        id: 'item_16',
        title: 'Combat Sports Preworkout (30 Servings)',
        category: 'Sports Nutrition',
        priceAud: 64.95,
        vendor: 'Contract Blender',
        status: 'FSANZ 2.9.4 Compliant',
        description: 'Contract Batch, clinical dosing of citrulline, beta-alanine & electrolytes',
        symbolScale: 'Contract Batch',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983592',
      ),
      CommerceCatalogItem(
        id: 'item_17',
        title: 'Lauburu Pro Coaching & Biometrics SaaS',
        category: 'Software SaaS',
        priceAud: 99.00,
        vendor: 'Lauburu Mesh',
        status: 'Active Recurring',
        description: '100% Private Telemetry, Pan-Tompkins DSP and recovery dashboard',
        symbolScale: '100% Private Telemetry',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983593',
      ),
      CommerceCatalogItem(
        id: 'item_18',
        title: 'Pay by Compute Inference Metering (1M Tokens)',
        category: 'Inference Compute',
        priceAud: 0.80,
        vendor: 'Port 8082 RPC',
        status: 'RPC Metered',
        description: '270W Mesh Offset, local quantized token inference offset',
        symbolScale: '270W Mesh Offset',
        shopifyVariantId: 'gid://shopify/ProductVariant/44917532983594',
      ),
    ];
  }
}

