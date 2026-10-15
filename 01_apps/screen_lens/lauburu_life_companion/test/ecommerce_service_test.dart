import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lauburu_life_companion/models/ecommerce_models.dart';
import 'package:lauburu_life_companion/services/ecommerce_ai_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Acceptance Criterion 33: Local E-Commerce Models Integration & Zero API Timeouts', () {
    test('Port 8082 Primary Master 200 OK inference succeeds without fallback', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082 && request.url.path == '/v1/chat/completions') {
          return http.Response(
            jsonEncode({
              'id': 'chatcmpl-master-001',
              'model': 'qwen_38_max',
              'choices': [
                {
                  'index': 0,
                  'finish_reason': 'stop',
                  'message': {
                    'role': 'assistant',
                    'content': 'Unleash your true submission power with the Canonical Short Sleeve Rashguard.',
                  },
                }
              ],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      final service = EcommerceAiService(client: mockClient);
      final result = await service.queryInference(prompt: 'Generate ad copy for rashguard');

      expect(result.port, equals(8082));
      expect(result.isFallback, isFalse);
      expect(result.modelId, equals('qwen_38_max'));
      expect(result.content, contains('Canonical Short Sleeve Rashguard'));
      expect(result.finishReason, equals('stop'));
      expect(result.latencyMs, greaterThanOrEqualTo(0));
    });

    test('Port 8082 HTTP 503 Host Sanctuary protect triggers resilient failover to Port 8083 Metal Worker', () async {
      final mockClient = MockClient((request) async {
        // Port 8082 returns 503 Service Unavailable (e.g. Host Sanctuary Rule 3 Headroom Protection)
        if (request.url.port == 8082 && request.url.path == '/v1/chat/completions') {
          return http.Response(
            jsonEncode({
              'error': {
                'message': 'Model qwen_38_max is currently OFFLINE to protect Host Sanctuary.',
                'type': 'model_offline',
              }
            }),
            503,
            headers: {'content-type': 'application/json'},
          );
        }

        // Port 8083 Metal Worker handles failover successfully
        if (request.url.port == 8083 && request.url.path == '/v1/chat/completions') {
          return http.Response(
            jsonEncode({
              'id': 'chatcmpl-metal-002',
              'model': 'llama-server-7b-metal',
              'choices': [
                {
                  'index': 0,
                  'finish_reason': 'stop',
                  'message': {
                    'role': 'assistant',
                    'content': 'Engineered for the mat. Built to outlast. High-compression durable fight shorts.',
                  },
                }
              ],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }

        return http.Response('Not Found', 404);
      });

      final service = EcommerceAiService(client: mockClient);
      final result = await service.queryInference(prompt: 'Generate ad copy for fight shorts');

      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
      expect(result.modelId, equals('llama-server-7b-metal'));
      expect(result.content, contains('High-compression durable fight shorts'));
      expect(result.finishReason, equals('stop'));
    });

    test('Network error on Port 8082 fails over seamlessly to Port 8083', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          throw http.ClientException('Connection refused on 127.0.0.1:8082');
        }
        if (request.url.port == 8083 && request.url.path == '/v1/chat/completions') {
          return http.Response(
            jsonEncode({
              'id': 'chatcmpl-metal-003',
              'model': 'llama-server-7b',
              'choices': [
                {
                  'index': 0,
                  'finish_reason': 'stop',
                  'message': {
                    'role': 'assistant',
                    'content': 'Tactical EDC Backpack with waterproof cordura.',
                  },
                }
              ],
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      final service = EcommerceAiService(client: mockClient);
      final result = await service.queryInference(prompt: 'Generate ad copy for backpack');

      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
      expect(result.content, contains('Tactical EDC Backpack'));
    });

    test('Rule 1 Zero-Mock Truth Invariant: When both ports fail, returns clean waiting state ("--")', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException('Network unreachable');
      });

      final service = EcommerceAiService(client: mockClient);
      final result = await service.queryInference(prompt: 'Any query');

      expect(result.content, equals('--'));
      expect(result.modelId, equals('offline'));
      expect(result.finishReason, equals('mesh_offline'));
      expect(result.isFallback, isTrue);
    });

    test('Strict probe timeout of 1,500ms correctly marks model as offline', () async {
      final mockClient = MockClient((request) async {
        // Delay beyond 1,500ms probe timeout
        await Future.delayed(const Duration(milliseconds: 1600));
        return http.Response('{"status": "ok"}', 200);
      });

      final service = EcommerceAiService(client: mockClient);
      final status = await service.probeModelHealth(port: 8082);

      expect(status.isOnline, isFalse);
      expect(status.statusMessage, contains('Probe timed out (>1500ms)'));
      expect(status.port, equals(8082));
    });

    test('Strict inference timeout of 15,000ms triggers failover without unhandled crash', () async {
      final mockClient = MockClient((request) async {
        if (request.url.port == 8082) {
          // Exceeds 15,000ms inference timeout
          await Future.delayed(const Duration(milliseconds: 16000));
          return http.Response('{}', 200);
        }
        if (request.url.port == 8083) {
          return http.Response(
            jsonEncode({
              'choices': [
                {
                  'message': {'content': 'Fallback response after primary timeout'}
                }
              ]
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('Not Found', 404);
      });

      final service = EcommerceAiService(client: mockClient);
      final result = await service.queryInference(prompt: 'Test query');

      expect(result.port, equals(8083));
      expect(result.isFallback, isTrue);
      expect(result.content, equals('Fallback response after primary timeout'));
    });
  });

  group('Canonical 18-Item Commercial Catalog Verification', () {
    test('Catalog contains exactly 18 canonical items matching monorepo standards', () {
      final service = EcommerceAiService();
      final catalog = service.getCanonicalCatalog();

      expect(catalog.length, equals(18));

      // Validate all items have complete non-empty metadata
      for (final item in catalog) {
        expect(item.id, isNotEmpty);
        expect(item.title, isNotEmpty);
        expect(item.category, isNotEmpty);
        expect(item.priceAud, greaterThan(0));
        expect(item.vendor, isNotEmpty);
        expect(item.status, isNotEmpty);
        expect(item.description, isNotEmpty);
      }

      // Verify key flagship items
      final rashguard = catalog.firstWhere((i) => i.id == 'item_01');
      expect(rashguard.title, equals('Lauburu Canonical Short Sleeve Rashguard'));
      expect(rashguard.priceAud, equals(97.50));
      expect(rashguard.category, equals('Combat Uniform'));

      final fightShorts = catalog.firstWhere((i) => i.id == 'item_02');
      expect(fightShorts.title, equals('Lauburu Canonical No-Gi Pro Fight Shorts'));
      expect(fightShorts.priceAud, equals(90.00));

      final combatSet = catalog.firstWhere((i) => i.id == 'item_03');
      expect(combatSet.title, equals('Lauburu Canonical Combat Uniform Set'));
      expect(combatSet.priceAud, equals(172.50));

      final iphone = catalog.firstWhere((i) => i.id == 'item_13');
      expect(iphone.title, contains('iPhone 16 Pro'));
      expect(iphone.priceAud, equals(1150.00));
      expect(iphone.category, equals('Tech Arbitrage'));

      final movesense = catalog.firstWhere((i) => i.id == 'item_14');
      expect(movesense.title, contains('Movesense MD+'));
      expect(movesense.priceAud, equals(170.00));
      expect(movesense.category, equals('Biometrics Hardware'));

      final payByCompute = catalog.firstWhere((i) => i.id == 'item_18');
      expect(payByCompute.title, contains('Pay by Compute'));
      expect(payByCompute.priceAud, equals(0.80));
      expect(payByCompute.category, equals('Inference Compute'));
    });
  });

  group('Domain Models Serialization & Deserialization', () {
    test('CommerceCatalogItem roundtrip JSON serialization', () {
      const item = CommerceCatalogItem(
        id: 'item_test',
        title: 'Test Combat Rashguard',
        category: 'Combat Uniform',
        priceAud: 99.95,
        vendor: 'Subliminator',
        status: 'Live on Storefront',
        description: 'Test description',
        symbolScale: '80px',
      );

      final json = item.toJson();
      final fromJson = CommerceCatalogItem.fromJson(json);

      expect(fromJson.id, equals(item.id));
      expect(fromJson.title, equals(item.title));
      expect(fromJson.category, equals(item.category));
      expect(fromJson.priceAud, equals(item.priceAud));
      expect(fromJson.vendor, equals(item.vendor));
      expect(fromJson.status, equals(item.status));
      expect(fromJson.description, equals(item.description));
      expect(fromJson.symbolScale, equals(item.symbolScale));
      expect(fromJson.formattedPrice, equals('\$99.95 AUD'));
    });

    test('EcommerceMetrics roundtrip JSON serialization', () {
      const metrics = EcommerceMetrics(
        capitalAud: 14315.00,
        payByComputeAud: 3800.00,
        fiatReserveAud: 10515.00,
        openRouterCredits: 262.0,
        catalogCount: 18,
      );

      final json = metrics.toJson();
      final fromJson = EcommerceMetrics.fromJson(json);

      expect(fromJson.capitalAud, equals(14315.00));
      expect(fromJson.payByComputeAud, equals(3800.00));
      expect(fromJson.fiatReserveAud, equals(10515.00));
      expect(fromJson.openRouterCredits, equals(262.0));
      expect(fromJson.catalogCount, equals(18));
      expect(fromJson.formattedCapital, equals('\$14315.00 AUD'));
    });

    test('AiModelStatus roundtrip JSON serialization', () {
      const status = AiModelStatus(
        port: 8082,
        modelName: 'qwen_38_max',
        isOnline: true,
        statusMessage: 'ONLINE (200)',
        latencyMs: 142,
      );

      final json = status.toJson();
      final fromJson = AiModelStatus.fromJson(json);

      expect(fromJson.port, equals(8082));
      expect(fromJson.modelName, equals('qwen_38_max'));
      expect(fromJson.isOnline, isTrue);
      expect(fromJson.statusMessage, equals('ONLINE (200)'));
      expect(fromJson.latencyMs, equals(142));
    });

    test('AiInferenceResult roundtrip JSON serialization', () {
      const result = AiInferenceResult(
        content: 'Exclusive 20% discount on BJJ rashguards.',
        modelId: 'qwen_38_max',
        port: 8082,
        latencyMs: 250,
        finishReason: 'stop',
        isFallback: false,
      );

      final json = result.toJson();
      final fromJson = AiInferenceResult.fromJson(json);

      expect(fromJson.content, equals(result.content));
      expect(fromJson.modelId, equals(result.modelId));
      expect(fromJson.port, equals(result.port));
      expect(fromJson.latencyMs, equals(result.latencyMs));
      expect(fromJson.finishReason, equals(result.finishReason));
      expect(fromJson.isFallback, isFalse);
    });
  });

  group('High-Level E-Commerce AI Workflows', () {
    test('generateAdCopy calls inference and returns generated ad copy', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'choices': [
              {
                'message': {
                  'content': 'Headline: Elite Protection.\nBenefit 1: Compression.\nBenefit 2: Durability.\nCTA: Shop Now.'
                }
              }
            ]
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = EcommerceAiService(client: mockClient);
      final catalog = service.getCanonicalCatalog();
      final copy = await service.generateAdCopy(catalog.first);

      expect(copy, contains('Elite Protection'));
      expect(copy, contains('CTA: Shop Now'));
    });

    test('analyzeStorefrontMetrics returns canonical ledger figures', () async {
      final service = EcommerceAiService();
      final metrics = await service.analyzeStorefrontMetrics();

      expect(metrics.capitalAud, equals(14315.00));
      expect(metrics.payByComputeAud, equals(3800.00));
      expect(metrics.fiatReserveAud, equals(10515.00));
      expect(metrics.openRouterCredits, equals(262.0));
      expect(metrics.catalogCount, equals(18));
    });
  });
}
