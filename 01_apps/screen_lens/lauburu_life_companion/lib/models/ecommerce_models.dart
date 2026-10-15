/// Represents an item in the unified 18-item canonical commercial catalog.
class CommerceCatalogItem {
  final String id;
  final String title;
  final String category;
  final double priceAud;
  final String vendor;
  final String status;
  final String description;
  final String? symbolScale;
  final String? shopifyVariantId;

  const CommerceCatalogItem({
    required this.id,
    required this.title,
    required this.category,
    required this.priceAud,
    required this.vendor,
    required this.status,
    required this.description,
    this.symbolScale,
    this.shopifyVariantId,
  });

  String get formattedPrice => '\$${priceAud.toStringAsFixed(2)} AUD';

  CommerceCatalogItem copyWith({
    String? id,
    String? title,
    String? category,
    double? priceAud,
    String? vendor,
    String? status,
    String? description,
    String? symbolScale,
    String? shopifyVariantId,
  }) {
    return CommerceCatalogItem(
      id: id ?? this.id,
      title: title ?? this.title,
      category: category ?? this.category,
      priceAud: priceAud ?? this.priceAud,
      vendor: vendor ?? this.vendor,
      status: status ?? this.status,
      description: description ?? this.description,
      symbolScale: symbolScale ?? this.symbolScale,
      shopifyVariantId: shopifyVariantId ?? this.shopifyVariantId,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'category': category,
      'price_aud': priceAud,
      'vendor': vendor,
      'status': status,
      'description': description,
      if (symbolScale != null) 'symbol_scale': symbolScale,
      if (shopifyVariantId != null) 'shopify_variant_id': shopifyVariantId,
    };
  }

  factory CommerceCatalogItem.fromJson(Map<String, dynamic> json) {
    return CommerceCatalogItem(
      id: (json['id'] ?? json['Product'] ?? '').toString(),
      title: (json['title'] ?? json['Product'] ?? '').toString(),
      category: (json['category'] ?? json['Category'] ?? 'General').toString(),
      priceAud: (json['price_aud'] ?? json['priceAud'] ?? json['Price_AUD'] ?? 0.0) is num
          ? (json['price_aud'] ?? json['priceAud'] ?? json['Price_AUD'] ?? 0.0).toDouble()
          : double.tryParse((json['price_aud'] ?? json['priceAud'] ?? json['Price_AUD'] ?? '0').toString()) ?? 0.0,
      vendor: (json['vendor'] ?? json['Vendor'] ?? 'Lauburu').toString(),
      status: (json['status'] ?? json['Status'] ?? 'Active').toString(),
      description: (json['description'] ?? json['Symbol_Scale'] ?? json['symbol_scale'] ?? '').toString(),
      symbolScale: json['symbol_scale'] ?? json['Symbol_Scale'],
      shopifyVariantId: json['shopify_variant_id']?.toString(),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CommerceCatalogItem &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          title == other.title &&
          priceAud == other.priceAud;

  @override
  int get hashCode => id.hashCode ^ title.hashCode ^ priceAud.hashCode;
}

/// Represents enterprise storefront & compute ledger metrics.
class EcommerceMetrics {
  final double capitalAud;
  final double payByComputeAud;
  final double fiatReserveAud;
  final double openRouterCredits;
  final int catalogCount;
  final int lifetimeEloEarned;
  final int completedMilestonesCount;
  final int transactionCount;
  final bool isWaitingState;

  const EcommerceMetrics({
    required this.capitalAud,
    required this.payByComputeAud,
    required this.fiatReserveAud,
    required this.openRouterCredits,
    required this.catalogCount,
    this.lifetimeEloEarned = 0,
    this.completedMilestonesCount = 0,
    this.transactionCount = 0,
    this.isWaitingState = false,
  });

  /// Rule 1 Zero-Mock waiting state when authentic ledger is unreachable.
  factory EcommerceMetrics.waitingState() {
    return const EcommerceMetrics(
      capitalAud: 0.0,
      payByComputeAud: 0.0,
      fiatReserveAud: 0.0,
      openRouterCredits: 0.0,
      catalogCount: 0,
      lifetimeEloEarned: 0,
      completedMilestonesCount: 0,
      transactionCount: 0,
      isWaitingState: true,
    );
  }

  String get formattedCapital => isWaitingState ? '--' : '\$${capitalAud.toStringAsFixed(2)} AUD';
  String get formattedPayByCompute => isWaitingState ? '--' : '\$${payByComputeAud.toStringAsFixed(2)} AUD';
  String get formattedFiatReserve => isWaitingState ? '--' : '\$${fiatReserveAud.toStringAsFixed(2)} AUD';
  String get formattedOpenRouterCredits => isWaitingState ? '--' : '${openRouterCredits.toStringAsFixed(0)} Credits';
  String get formattedElo => isWaitingState ? '--' : '$lifetimeEloEarned ELO';

  EcommerceMetrics copyWith({
    double? capitalAud,
    double? payByComputeAud,
    double? fiatReserveAud,
    double? openRouterCredits,
    int? catalogCount,
    int? lifetimeEloEarned,
    int? completedMilestonesCount,
    int? transactionCount,
    bool? isWaitingState,
  }) {
    return EcommerceMetrics(
      capitalAud: capitalAud ?? this.capitalAud,
      payByComputeAud: payByComputeAud ?? this.payByComputeAud,
      fiatReserveAud: fiatReserveAud ?? this.fiatReserveAud,
      openRouterCredits: openRouterCredits ?? this.openRouterCredits,
      catalogCount: catalogCount ?? this.catalogCount,
      lifetimeEloEarned: lifetimeEloEarned ?? this.lifetimeEloEarned,
      completedMilestonesCount: completedMilestonesCount ?? this.completedMilestonesCount,
      transactionCount: transactionCount ?? this.transactionCount,
      isWaitingState: isWaitingState ?? this.isWaitingState,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'capital_aud': capitalAud,
      'pay_by_compute_aud': payByComputeAud,
      'fiat_reserve_aud': fiatReserveAud,
      'open_router_credits': openRouterCredits,
      'catalog_count': catalogCount,
      'lifetime_elo_earned': lifetimeEloEarned,
      'completed_milestones_count': completedMilestonesCount,
      'transaction_count': transactionCount,
      'is_waiting_state': isWaitingState,
    };
  }

  factory EcommerceMetrics.fromJson(Map<String, dynamic> json) {
    final isWaiting = json['is_waiting_state'] == true;
    return EcommerceMetrics(
      capitalAud: (json['capital_aud'] ?? json['capitalAud'] ?? json['total_capital_aud'] ?? 0.0) is num
          ? (json['capital_aud'] ?? json['capitalAud'] ?? json['total_capital_aud'] ?? 0.0).toDouble()
          : double.tryParse((json['capital_aud'] ?? json['capitalAud'] ?? json['total_capital_aud'] ?? '0').toString()) ?? 0.0,
      payByComputeAud: (json['pay_by_compute_aud'] ?? json['payByComputeAud'] ?? 0.0) is num
          ? (json['pay_by_compute_aud'] ?? json['payByComputeAud'] ?? 0.0).toDouble()
          : double.tryParse((json['pay_by_compute_aud'] ?? json['payByComputeAud'] ?? '0').toString()) ?? 0.0,
      fiatReserveAud: (json['fiat_reserve_aud'] ?? json['fiatReserveAud'] ?? json['settled_fiat_reserve_aud'] ?? 0.0) is num
          ? (json['fiat_reserve_aud'] ?? json['fiatReserveAud'] ?? json['settled_fiat_reserve_aud'] ?? 0.0).toDouble()
          : double.tryParse((json['fiat_reserve_aud'] ?? json['fiatReserveAud'] ?? json['settled_fiat_reserve_aud'] ?? '0').toString()) ?? 0.0,
      openRouterCredits: (json['open_router_credits'] ?? json['openRouterCredits'] ?? json['available_openrouter_credits'] ?? 0.0) is num
          ? (json['open_router_credits'] ?? json['openRouterCredits'] ?? json['available_openrouter_credits'] ?? 0.0).toDouble()
          : double.tryParse((json['open_router_credits'] ?? json['openRouterCredits'] ?? json['available_openrouter_credits'] ?? '0').toString()) ?? 0.0,
      catalogCount: (json['catalog_count'] ?? json['catalogCount'] ?? 0) is int
          ? (json['catalog_count'] ?? json['catalogCount'] ?? 0) as int
          : int.tryParse((json['catalog_count'] ?? json['catalogCount'] ?? '0').toString()) ?? 0,
      lifetimeEloEarned: (json['lifetime_elo_earned'] ?? json['lifetimeEloEarned'] ?? 0) is int
          ? (json['lifetime_elo_earned'] ?? json['lifetimeEloEarned'] ?? 0) as int
          : int.tryParse((json['lifetime_elo_earned'] ?? json['lifetimeEloEarned'] ?? '0').toString()) ?? 0,
      completedMilestonesCount: (json['completed_milestones_count'] ?? json['completedMilestonesCount'] ?? 0) is int
          ? (json['completed_milestones_count'] ?? json['completedMilestonesCount'] ?? 0) as int
          : int.tryParse((json['completed_milestones_count'] ?? json['completedMilestonesCount'] ?? '0').toString()) ?? 0,
      transactionCount: (json['transaction_count'] ?? json['transactionCount'] ?? 0) is int
          ? (json['transaction_count'] ?? json['transactionCount'] ?? 0) as int
          : int.tryParse((json['transaction_count'] ?? json['transactionCount'] ?? '0').toString()) ?? 0,
      isWaitingState: isWaiting,
    );
  }
}

/// Represents the health and telemetry of a local AI model endpoint.
class AiModelStatus {
  final int port;
  final String modelName;
  final bool isOnline;
  final String statusMessage;
  final int latencyMs;

  const AiModelStatus({
    required this.port,
    required this.modelName,
    required this.isOnline,
    required this.statusMessage,
    required this.latencyMs,
  });

  AiModelStatus copyWith({
    int? port,
    String? modelName,
    bool? isOnline,
    String? statusMessage,
    int? latencyMs,
  }) {
    return AiModelStatus(
      port: port ?? this.port,
      modelName: modelName ?? this.modelName,
      isOnline: isOnline ?? this.isOnline,
      statusMessage: statusMessage ?? this.statusMessage,
      latencyMs: latencyMs ?? this.latencyMs,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'port': port,
      'model_name': modelName,
      'is_online': isOnline,
      'status_message': statusMessage,
      'latency_ms': latencyMs,
    };
  }

  factory AiModelStatus.fromJson(Map<String, dynamic> json) {
    return AiModelStatus(
      port: (json['port'] ?? 8082) as int,
      modelName: (json['model_name'] ?? json['modelName'] ?? 'Unknown Model').toString(),
      isOnline: (json['is_online'] ?? json['isOnline'] ?? false) as bool,
      statusMessage: (json['status_message'] ?? json['statusMessage'] ?? '').toString(),
      latencyMs: (json['latency_ms'] ?? json['latencyMs'] ?? -1) as int,
    );
  }
}

/// Result of an e-commerce local AI inference query.
class AiInferenceResult {
  final String content;
  final String modelId;
  final int port;
  final int latencyMs;
  final String finishReason;
  final bool isFallback;

  const AiInferenceResult({
    required this.content,
    required this.modelId,
    required this.port,
    required this.latencyMs,
    required this.finishReason,
    required this.isFallback,
  });

  AiInferenceResult copyWith({
    String? content,
    String? modelId,
    int? port,
    int? latencyMs,
    String? finishReason,
    bool? isFallback,
  }) {
    return AiInferenceResult(
      content: content ?? this.content,
      modelId: modelId ?? this.modelId,
      port: port ?? this.port,
      latencyMs: latencyMs ?? this.latencyMs,
      finishReason: finishReason ?? this.finishReason,
      isFallback: isFallback ?? this.isFallback,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'content': content,
      'model_id': modelId,
      'port': port,
      'latency_ms': latencyMs,
      'finish_reason': finishReason,
      'is_fallback': isFallback,
    };
  }

  factory AiInferenceResult.fromJson(Map<String, dynamic> json) {
    return AiInferenceResult(
      content: (json['content'] ?? '--').toString(),
      modelId: (json['model_id'] ?? json['modelId'] ?? 'unknown').toString(),
      port: (json['port'] ?? 8082) as int,
      latencyMs: (json['latency_ms'] ?? json['latencyMs'] ?? -1) as int,
      finishReason: (json['finish_reason'] ?? json['finishReason'] ?? 'stop').toString(),
      isFallback: (json['is_fallback'] ?? json['isFallback'] ?? false) as bool,
    );
  }

  /// Clean zero-mock offline result representing waiting state.
  factory AiInferenceResult.offline({int port = 8082, String message = '--'}) {
    return AiInferenceResult(
      content: message,
      modelId: 'offline',
      port: port,
      latencyMs: -1,
      finishReason: 'mesh_offline',
      isFallback: true,
    );
  }
}
