import 'package:flutter/material.dart';
import '../models/ecommerce_models.dart';
import '../services/ecommerce_ai_service.dart';
import '../services/mesh_terminal_service.dart';
import '../services/shopify_auth_service.dart';
import '../widgets/ai_status_badge.dart';
import '../widgets/mesh_terminal_sheet.dart';

class EcommerceHubScreen extends StatefulWidget {
  final EcommerceAiService? aiService;
  final ShopifyAuthService? authService;
  final IMeshTerminalService? terminalService;

  const EcommerceHubScreen({
    super.key,
    this.aiService,
    this.authService,
    this.terminalService,
  });

  @override
  State<EcommerceHubScreen> createState() => _EcommerceHubScreenState();
}

class _EcommerceHubScreenState extends State<EcommerceHubScreen> {
  late final EcommerceAiService _aiService;
  late final IMeshTerminalService _terminalService;
  late final bool _ownsTerminalService;
  List<CommerceCatalogItem> _catalog = [];
  List<CommerceCatalogItem> _filteredCatalog = [];
  List<AiModelStatus> _meshStatuses = [];
  EcommerceMetrics? _metrics;
  CommerceCatalogItem? _selectedItem;

  /// Rule 1 Zero-Mock waiting state
  String _generatedAdCopy = '--';
  bool _isGeneratingAdCopy = false;
  bool _isProbingMesh = false;
  bool _isLoadingMetrics = false;
  bool _isCheckingOut = false;
  String _selectedCategory = 'All';
  late final ShopifyAuthService _authService;

  @override
  void initState() {
    super.initState();
    _aiService = widget.aiService ?? EcommerceAiService();
    _authService = widget.authService ?? ShopifyAuthService();
    _terminalService = widget.terminalService ?? MeshTerminalService();
    _ownsTerminalService = widget.terminalService == null;
    _catalog = _aiService.getCanonicalCatalog();
    _filteredCatalog = _catalog;
    if (_catalog.isNotEmpty) {
      _selectedItem = _catalog.first;
    }

    _meshStatuses = [
      const AiModelStatus(
        port: 8082,
        modelName: 'Qwen 3.8 Max (Master)',
        isOnline: false,
        statusMessage: 'Pending probe',
        latencyMs: -1,
      ),
      const AiModelStatus(
        port: 8083,
        modelName: 'llama-server 7B (Metal)',
        isOnline: false,
        statusMessage: 'Pending probe',
        latencyMs: -1,
      ),
    ];

    _probeMeshHealth();
    // Do not auto-load metrics synchronously so initial waiting state '--' is verified by tests
  }

  @override
  void dispose() {
    if (widget.aiService == null) {
      _aiService.dispose();
    }
    if (_ownsTerminalService) {
      _terminalService.dispose();
    }
    super.dispose();
  }

  Future<void> _probeMeshHealth() async {
    if (_isProbingMesh) return;
    setState(() => _isProbingMesh = true);

    try {
      final statuses = await _aiService.probeMeshHealth();
      if (mounted) {
        setState(() {
          _meshStatuses = statuses;
          _isProbingMesh = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isProbingMesh = false);
      }
    }
  }

  Future<void> _loadMetrics() async {
    if (_isLoadingMetrics) return;
    setState(() => _isLoadingMetrics = true);

    try {
      final metrics = await _aiService.analyzeStorefrontMetrics();
      if (mounted) {
        setState(() {
          _metrics = metrics;
          _isLoadingMetrics = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingMetrics = false);
      }
    }
  }

  Future<void> _generateAdCopy() async {
    if (_selectedItem == null || _isGeneratingAdCopy) return;

    setState(() => _isGeneratingAdCopy = true);

    try {
      final copy = await _aiService.generateAdCopy(_selectedItem!);
      if (mounted) {
        setState(() {
          _generatedAdCopy = copy;
          _isGeneratingAdCopy = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _generatedAdCopy = '--';
          _isGeneratingAdCopy = false;
        });
      }
    }
  }

  void _selectAndGenerateCopy(CommerceCatalogItem item) {
    setState(() {
      _selectedItem = item;
    });
    _generateAdCopy();
  }

  Future<void> _checkoutItem(CommerceCatalogItem item) async {
    if (_isCheckingOut) return;
    setState(() => _isCheckingOut = true);
    
    try {
      // 1. Send checkout telemetry to Port 8082
      await _aiService.sendTransactionTelemetry(item, 'checkout_initiated');
      
      // 2. Create Shopify Cart & Get Checkout URL using authentic item variant
      final variantId = item.shopifyVariantId ?? 'gid://shopify/ProductVariant/${item.id}';
      final checkoutUrl = await _authService.createCartAndCheckout(variantId);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Checkout created! URL: $checkoutUrl')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Checkout failed: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isCheckingOut = false);
      }
    }
  }

  void _filterCategory(String category) {
    setState(() {
      _selectedCategory = category;
      if (category == 'All') {
        _filteredCatalog = _catalog;
      } else {
        _filteredCatalog = _catalog.where((item) => item.category == category).toList();
      }
    });
  }

  void _openMeshTerminalSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => MeshTerminalSheet(terminalService: _terminalService),
    );
  }

  @override
  Widget build(BuildContext context) {
    final categories = ['All', ...{..._catalog.map((e) => e.category)}];

    return Scaffold(
      appBar: AppBar(
        title: const Text('E-Commerce Hub'),
        actions: [
          IconButton(
            key: const Key('open_mesh_terminal_button'),
            icon: const Icon(Icons.terminal),
            tooltip: 'Mesh Bluetooth Terminal',
            onPressed: () => _openMeshTerminalSheet(context),
          ),
          IconButton(
            key: const Key('refresh_hub_button'),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Hub & Telemetry',
            onPressed: () {
              _probeMeshHealth();
              _loadMetrics();
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('terminal_fab'),
        icon: const Icon(Icons.terminal),
        label: const Text('Terminal'),
        onPressed: () => _openMeshTerminalSheet(context),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. AI Mesh Telemetry Status Bar
            AiMeshStatusBar(
              statuses: _meshStatuses,
              onRefresh: _probeMeshHealth,
            ),
            const SizedBox(height: 16),

            // 2. Storefront Metrics Card
            _buildStorefrontMetricsCard(),
            const SizedBox(height: 16),

            // 3. AI Ad Copy Generator Card
            _buildAdCopyCard(),
            const SizedBox(height: 20),

            // 4. Commercial Catalog Header & Category Filters
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Commercial Catalog (${_filteredCatalog.length} Items)',
                  key: const Key('catalog_section_title'),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: categories.map((cat) {
                  final isSelected = cat == _selectedCategory;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: ChoiceChip(
                      label: Text(cat),
                      selected: isSelected,
                      onSelected: (_) => _filterCategory(cat),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 12),

            // 5. Catalog Item Cards
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _filteredCatalog.length,
              itemBuilder: (context, index) {
                final item = _filteredCatalog[index];
                final isSelected = item.id == _selectedItem?.id;
                return _buildCatalogCard(item, isSelected);
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStorefrontMetricsCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    Icon(Icons.analytics_outlined, color: Colors.indigoAccent),
                    SizedBox(width: 8),
                    Text(
                      'Storefront & Compute Metrics',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  key: const Key('evaluate_metrics_button'),
                  onPressed: _loadMetrics,
                  icon: const Icon(Icons.sync_alt, size: 16),
                  label: const Text('Evaluate Metrics'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    textStyle: const TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _buildMetricTile(
                    label: 'Total Capital',
                    value: _metrics?.formattedCapital ?? '--',
                    key: 'metrics_capital',
                    icon: Icons.account_balance_wallet_outlined,
                    color: Colors.green.shade700,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    label: 'Pay by Compute',
                    value: _metrics?.formattedPayByCompute ?? '--',
                    key: 'metrics_pay_by_compute',
                    icon: Icons.memory_outlined,
                    color: Colors.blue.shade700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _buildMetricTile(
                    label: 'Settled Fiat Reserve',
                    value: _metrics?.formattedFiatReserve ?? '--',
                    key: 'metrics_fiat_reserve',
                    icon: Icons.security_outlined,
                    color: Colors.amber.shade900,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    label: 'OpenRouter Credits',
                    value: _metrics?.formattedOpenRouterCredits ?? '--',
                    key: 'metrics_openrouter_credits',
                    icon: Icons.cloud_done_outlined,
                    color: Colors.purple.shade700,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    label: 'Catalog Items',
                    value: _metrics != null ? '${_metrics!.catalogCount}' : '--',
                    key: 'metrics_catalog_count',
                    icon: Icons.inventory_2_outlined,
                    color: Colors.blueGrey.shade800,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required String key,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withAlpha(20),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(fontSize: 10, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            key: Key(key),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAdCopyCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    Icon(Icons.auto_awesome, color: Colors.amber),
                    SizedBox(width: 8),
                    Text(
                      'AI E-Commerce Copywriter',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  key: const Key('generate_ad_button'),
                  onPressed: _isGeneratingAdCopy ? null : _generateAdCopy,
                  icon: const Icon(Icons.flash_on, size: 16),
                  label: const Text('Generate Ad Copy'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.amber.shade800,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              _selectedItem != null ? 'Selected: ${_selectedItem!.title}' : 'Select a product below',
              key: const Key('selected_product_text'),
              style: TextStyle(fontSize: 12, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 12),
            Container(
              key: const Key('ad_copy_result_container'),
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: _isGeneratingAdCopy
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.symmetric(vertical: 16.0),
                        child: CircularProgressIndicator(
                          key: Key('ad_copy_loading_indicator'),
                        ),
                      ),
                    )
                  : Text(
                      _generatedAdCopy,
                      key: const Key('ad_copy_text'),
                      style: TextStyle(
                        fontSize: 13,
                        height: 1.4,
                        fontFamily: _generatedAdCopy == '--' ? null : 'Courier',
                        color: _generatedAdCopy == '--' ? Colors.grey : Colors.black87,
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCatalogCard(CommerceCatalogItem item, bool isSelected) {
    return Card(
      key: Key('catalog_item_${item.id}'),
      margin: const EdgeInsets.symmetric(vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: isSelected ? const BorderSide(color: Colors.blueAccent, width: 2) : BorderSide.none,
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          setState(() => _selectedItem = item);
        },
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.title,
                          key: Key('item_title_${item.id}'),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: Colors.blue.withAlpha(25),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                item.category,
                                style: TextStyle(fontSize: 10, color: Colors.blue.shade900),
                              ),
                            ),
                            Text(
                              'by ${item.vendor}',
                              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        item.formattedPrice,
                        key: Key('item_price_${item.id}'),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.green),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        item.status,
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade700),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                item.description,
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    key: Key('generate_ad_button_${item.id}'),
                    onPressed: () => _selectAndGenerateCopy(item),
                    icon: const Icon(Icons.auto_awesome, size: 14),
                    label: const Text('Generate Copy', style: TextStyle(fontSize: 12)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton.icon(
                    key: Key('checkout_button_${item.id}'),
                    onPressed: _isCheckingOut ? null : () => _checkoutItem(item),
                    icon: const Icon(Icons.shopping_cart_checkout, size: 14),
                    label: const Text('Checkout', style: TextStyle(fontSize: 12)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green.shade600,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
